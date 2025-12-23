"""Version service for handling version-related business logic."""

import logging
import time
from typing import Optional, Dict, Any

from ..repositories.version_repository import VersionRepository
from ..repositories.report_repository import ReportRepository
from ..repositories.project_repository import ProjectRepository
from ..utils.project_resolution import resolve_project_id_to_uuid
from ..utils.error_handling import IriusRiskError
from ..exceptions import ResourceNotFoundError, APIError

logger = logging.getLogger(__name__)


class VersionService:
    """Service for managing project version operations."""
    
    def __init__(self, version_repository=None, report_repository=None, project_repository=None):
        """Initialize the version service.
        
        Args:
            version_repository: VersionRepository instance (required for dependency injection)
            report_repository: ReportRepository instance (for async operation polling)
            project_repository: ProjectRepository instance (for project state checks)
        """
        if version_repository is None:
            raise ValueError("VersionService requires a version_repository instance")
        if report_repository is None:
            raise ValueError("VersionService requires a report_repository instance")
        if project_repository is None:
            raise ValueError("VersionService requires a project_repository instance")
        
        self.version_repository = version_repository
        self.report_repository = report_repository
        self.project_repository = project_repository
    
    def list_versions(self, project_id: str, page: int = 0, size: int = 20) -> Dict[str, Any]:
        """List all versions for a project.
        
        Args:
            project_id: Project UUID or reference ID
            page: Page number (0-based)
            size: Number of versions per page
            
        Returns:
            Dictionary containing versions data and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Listing versions for project: {project_id}")
        
        # Resolve project ID to UUID
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved project ID to UUID: {final_project_id}")
        
        result = self.version_repository.list_all(
            project_id=final_project_id,
            page=page,
            size=size
        )
        
        versions_count = len(result.get('versions', []))
        total_count = result.get('page_info', {}).get('totalElements', 0)
        logger.info(f"Retrieved {versions_count} versions (page {page + 1}, {total_count} total)")
        
        return result
    
    def create_version(self, project_id: str, name: str, description: Optional[str] = None,
                      wait: bool = True, timeout: int = 300) -> Dict[str, Any]:
        """Create a version snapshot of a project.
        
        Args:
            project_id: Project UUID or reference ID
            name: Version name
            description: Optional version description
            wait: Whether to wait for async operation to complete
            timeout: Timeout in seconds for waiting
            
        Returns:
            Version creation response with operation details
            
        Raises:
            IriusRiskError: If API request fails or version creation fails
        """
        logger.debug(f"Creating version '{name}' for project: {project_id}")
        
        # Resolve project ID to UUID using our project repository's API client
        # This ensures we use the same configured client and get proper error handling
        final_project_id = resolve_project_id_to_uuid(project_id, self.project_repository.api_client)
        logger.debug(f"Resolved project ID to UUID: {final_project_id}")
        
        # Create version (async operation)
        result = self.version_repository.create(
            project_id=final_project_id,
            name=name,
            description=description,
            wait=True  # Always async
        )
        
        # If wait=True, poll for completion
        if wait and result.get('operationId'):
            operation_id = result['operationId']
            logger.info(f"Waiting for version creation to complete (operation: {operation_id})")
            
            final_result = self._wait_for_operation(operation_id, timeout)
            
            # After async operation completes, wait for project to unlock
            # The project may still be locked for a brief period even after the operation finishes
            logger.info("Version creation complete, waiting for project to unlock...")
            self._wait_for_project_unlock(final_project_id, timeout=60)
            
            return final_result
        
        logger.info(f"Version creation initiated: {result.get('id', 'unknown')}")
        return result
    
    def update_version(self, version_id: str, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Update version metadata.
        
        Args:
            version_id: Version UUID
            name: New version name
            description: New version description
            
        Returns:
            Updated version response
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Updating version {version_id}")
        
        result = self.version_repository.update(
            version_id=version_id,
            name=name,
            description=description
        )
        
        logger.info(f"Version {version_id} updated successfully")
        return result
    
    def compare_versions(self, project_id: str, source_version_id: str, target_version_id: str,
                        page: int = 0, size: int = 100,
                        filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Compare two project versions to see what changed.
        
        Args:
            project_id: Project UUID or reference ID (for context)
            source_version_id: Source version UUID
            target_version_id: Target version UUID
            page: Page number (0-based)
            size: Number of items per page
            filter_expression: Optional filter expression
            
        Returns:
            Dictionary containing version differences and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Comparing versions {source_version_id} -> {target_version_id}")
        
        result = self.version_repository.compare(
            source_version_id=source_version_id,
            target_version_id=target_version_id,
            page=page,
            size=size,
            filter_expression=filter_expression
        )
        
        changes_count = len(result.get('changes', []))
        total_count = result.get('page_info', {}).get('totalElements', 0)
        logger.info(f"Found {changes_count} changes (page {page + 1}, {total_count} total)")
        
        return result
    
    def _wait_for_operation(self, operation_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for an async operation to complete.
        
        Args:
            operation_id: Async operation ID
            timeout: Timeout in seconds
            
        Returns:
            Final operation result
            
        Raises:
            IriusRiskError: If operation fails or times out
        """
        logger.debug(f"Polling async operation {operation_id}")
        
        start_time = time.time()
        poll_interval = 2  # Start with 2 seconds
        max_poll_interval = 10  # Max 10 seconds between polls
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                raise IriusRiskError(
                    f"Operation {operation_id} timed out after {timeout} seconds"
                )
            
            # Check operation status
            try:
                status_response = self.report_repository.get_operation_status(operation_id)
                
                # The API returns 'status' field, not 'state'
                current_status = status_response.get('status', '').lower()
                logger.debug(f"Operation {operation_id} status: {current_status}")
                
                # IriusRisk async operations use 'finished-success' status
                if current_status == 'finished-success':
                    logger.info(f"Operation {operation_id} completed successfully")
                    return status_response
                elif current_status in ['failed', 'finished-error', 'finished-failure']:
                    error_msg = status_response.get('errorMessage', 'Unknown error')
                    raise IriusRiskError(
                        f"Operation {operation_id} failed: {error_msg}"
                    )
                elif current_status in ['pending', 'in-progress']:
                    # Still in progress, continue polling
                    logger.debug(f"Operation {operation_id} still in progress, waiting...")
                else:
                    # Unknown status
                    logger.warning(f"Operation {operation_id} has unknown status: {current_status}")
                
                # Wait before next poll
                time.sleep(poll_interval)
                
                # Increase poll interval gradually (exponential backoff)
                poll_interval = min(poll_interval * 1.5, max_poll_interval)
                
            except IriusRiskError:
                raise
            except Exception as e:
                logger.error(f"Error polling operation {operation_id}: {e}")
                raise IriusRiskError(
                    f"Failed to poll operation status: {e}"
                )
    
    def _wait_for_project_unlock(self, project_id: str, timeout: int = 60) -> None:
        """Wait for a project to be unlocked and ready for operations.
        
        After version creation or other async operations, the project may be temporarily
        locked. This method polls the project status until it's ready for use.
        
        Args:
            project_id: Project UUID
            timeout: Maximum time to wait in seconds
            
        Raises:
            IriusRiskError: If project doesn't unlock within timeout
        """
        logger.info(f"Waiting for project {project_id} to unlock...")
        start_time = time.time()
        poll_interval = 0.5  # Start with 500ms polling
        
        while time.time() - start_time < timeout:
            try:
                project_data = self.project_repository.get_by_id(project_id)
                
                # Check if project is ready
                operation = project_data.get('operation', 'none')
                is_locked = project_data.get('isThreatModelLocked', False)
                is_read_only = project_data.get('readOnly', False)
                
                logger.debug(f"Project status - operation: {operation}, locked: {is_locked}, readonly: {is_read_only}")
                
                # Project is ready if no active operation and not locked
                if operation == 'none' and not is_locked and not is_read_only:
                    elapsed = time.time() - start_time
                    logger.info(f"Project {project_id} is unlocked and ready (waited {elapsed:.1f}s)")
                    return
                
                # Still locked, wait before next check
                time.sleep(poll_interval)
                poll_interval = min(poll_interval * 1.5, 2.0)  # Max 2 second intervals
                
            except Exception as e:
                logger.warning(f"Error checking project status: {e}")
                time.sleep(poll_interval)
        
        # Timeout reached
        raise IriusRiskError(
            f"Project did not unlock within {timeout} seconds. "
            f"It may have pending changes in the IriusRisk UI that need to be confirmed or discarded."
        )

