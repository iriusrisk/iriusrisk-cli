"""Report repository for report data access."""

import logging
import time
from typing import Optional, Dict, List, Any

from .base_repository import BaseRepository
from ..utils.error_handling import IriusRiskError
from ..utils.project_resolution import is_uuid_format

logger = logging.getLogger(__name__)


class ReportRepository(BaseRepository):
    """Repository for report data access operations."""
    
    def get_by_id(self, report_id: str, **kwargs) -> Dict[str, Any]:
        """Get a report by ID.
        
        Args:
            report_id: Report ID
            **kwargs: Additional parameters
            
        Returns:
            Report data dictionary
            
        Raises:
            IriusRiskError: If report not found or API request fails
        """
        logger.debug(f"Attempted to get report by ID: {report_id}")
        # Reports are typically accessed through project context
        # This method is here for interface compliance but may not be commonly used
        logger.warning("Direct report access by ID not supported - use list_all() with project context")
        raise IriusRiskError("Reports should be accessed through project context using list_all()")
    
    def list_all(self, project_id: str) -> Dict[str, Any]:
        """List all reports for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary containing reports data
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Listing all reports for project '{project_id}'")
        
        try:
            response = self.api_client.get_project_reports(project_id)
            reports = self._extract_items_from_response(response)
            
            logger.debug(f"Retrieved {len(reports)} reports for project '{project_id}'")
            
            return {
                'reports': reports,
                'full_response': response
            }
            
        except Exception as e:
            # Don't log here - let the error handling layer handle it
            # to avoid duplicate error messages
            self._handle_error(e, f"retrieving reports for project '{project_id}'")
    
    def generate_report(self, project_id: str, report_type: str, 
                       report_format: str = 'pdf', standard: Optional[str] = None) -> str:
        """Generate a report and return operation ID.
        
        Args:
            project_id: Project UUID
            report_type: Type of report to generate
            report_format: Output format
            standard: Standard UUID for compliance reports
            
        Returns:
            Operation ID for tracking generation progress
            
        Raises:
            IriusRiskError: If report generation fails to start
        """
        logger.debug(f"Generating {report_type} report for project '{project_id}' in {report_format} format")
        if standard:
            logger.debug(f"Using standard: {standard}")
        
        try:
            operation_id = self.api_client.generate_report(
                project_id=project_id,
                report_type=report_type,
                format=report_format,
                standard=standard
            )
            logger.debug(f"Report generation started with operation ID: {operation_id}")
            return operation_id
            
        except Exception as e:
            # Don't log here - let the error handling layer handle it
            # to avoid duplicate error messages
            self._handle_error(e, f"starting generation of {report_type} report")
    
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get the status of an async operation.
        
        Args:
            operation_id: Operation ID to check
            
        Returns:
            Operation status data
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Checking status of operation '{operation_id}'")
        
        try:
            status_data = self.api_client.get_async_operation_status(operation_id)
            status = status_data.get('status', 'unknown')
            logger.debug(f"Operation '{operation_id}' status: {status}")
            return status_data
            
        except Exception as e:
            # Don't log here - let the error handling layer handle it
            # to avoid duplicate error messages
            self._handle_error(e, f"checking status of operation '{operation_id}'")
    
    def wait_for_completion(self, operation_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for an operation to complete.
        
        Args:
            operation_id: Operation ID to wait for
            timeout: Timeout in seconds
            
        Returns:
            Final operation status
            
        Raises:
            IriusRiskError: If operation fails or times out
        """
        logger.debug(f"Waiting for operation '{operation_id}' to complete (timeout: {timeout}s)")
        
        try:
            start_time = time.time()
            poll_count = 0
            
            while time.time() - start_time < timeout:
                status_response = self.get_operation_status(operation_id)
                status = status_response.get('status')
                poll_count += 1
                
                if status == 'finished-success':
                    elapsed = time.time() - start_time
                    logger.debug(f"Operation '{operation_id}' completed successfully after {elapsed:.1f}s ({poll_count} polls)")
                    return status_response
                elif status in ['finished-error', 'finished-failure', 'failed']:
                    error_msg = status_response.get('errorMessage', 'Unknown error')
                    logger.error(f"Operation '{operation_id}' failed: {error_msg}")
                    raise IriusRiskError(f"Report generation failed: {error_msg}")
                elif status in ['pending', 'in-progress']:
                    if poll_count % 10 == 0:  # Log every 20 seconds
                        elapsed = time.time() - start_time
                        logger.debug(f"Operation '{operation_id}' still {status} after {elapsed:.1f}s")
                    time.sleep(2)  # Poll every 2 seconds
                else:
                    logger.error(f"Operation '{operation_id}' has unknown status: {status}")
                    raise IriusRiskError(f"Unknown status: {status}")
            else:
                logger.error(f"Operation '{operation_id}' timed out after {timeout} seconds")
                raise IriusRiskError(f"Report generation timed out after {timeout} seconds")
                
        except IriusRiskError:
            raise
        except Exception as e:
            logger.error(f"Failed while waiting for operation '{operation_id}' to complete: {e}")
            self._handle_error(e, f"waiting for operation '{operation_id}' to complete")
    
    def download_report_content(self, download_url: str) -> bytes:
        """Download report content from URL.
        
        Args:
            download_url: URL to download from
            
        Returns:
            Report content as bytes
            
        Raises:
            IriusRiskError: If download fails
        """
        logger.debug(f"Downloading report content from URL: {download_url}")
        
        try:
            content = self.api_client.download_report_content_from_url(download_url)
            content_size = len(content) if content else 0
            logger.debug(f"Successfully downloaded report content ({content_size} bytes)")
            return content
            
        except Exception as e:
            # Don't log here - let the error handling layer handle it
            # to avoid duplicate error messages
            self._handle_error(e, f"downloading report from '{download_url}'")
    
    def get_report_types(self, project_id: str) -> Dict[str, Any]:
        """Get available report types for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary containing report types data
            
        Raises:
            IriusRiskError: If API request fails
        """
        try:
            response = self.api_client.get_report_types(project_id)
            report_types = self._extract_items_from_response(response)
            
            return {
                'report_types': report_types,
                'full_response': response
            }
            
        except Exception as e:
            self._handle_error(e, f"retrieving report types for project '{project_id}'")
    
    def get_standards(self, project_id: str) -> Dict[str, Any]:
        """Get available standards for compliance reports.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary containing standards data
            
        Raises:
            IriusRiskError: If API request fails
        """
        try:
            response = self.api_client.get_project_standards(project_id)
            standards = self._extract_items_from_response(response)
            
            return {
                'standards': standards,
                'full_response': response
            }
            
        except Exception as e:
            self._handle_error(e, f"retrieving standards for project '{project_id}'")
    
    def find_report_by_type_and_format(self, project_id: str, report_type: str, 
                                     report_format: str) -> Optional[Dict[str, Any]]:
        """Find the most recent report of a specific type and format.
        
        Args:
            project_id: Project UUID
            report_type: Type of report to find
            report_format: Format of report to find
            
        Returns:
            Report data or None if not found
            
        Raises:
            IriusRiskError: If API request fails
        """
        try:
            reports_data = self.list_all(project_id)
            reports = reports_data.get('reports', [])
            
            # Find the most recent report of the correct type and format
            for report in reports:
                if (report.get('reportType') == report_type and 
                    report.get('format') == report_format):
                    return report
            
            return None
            
        except Exception as e:
            self._handle_error(e, f"finding {report_type} report in {report_format} format")
    
    def resolve_standard_id(self, project_id: str, standard: str) -> str:
        """Resolve standard reference ID to UUID if needed.
        
        Args:
            project_id: Project UUID
            standard: Standard reference ID or UUID
            
        Returns:
            Standard UUID
            
        Raises:
            IriusRiskError: If standard not found
        """
        try:
            # If it looks like a UUID, use it directly
            if is_uuid_format(standard):
                return standard
            
            # It's likely a reference ID, look it up
            standards_data = self.get_standards(project_id)
            standards = standards_data.get('standards', [])
            
            for std in standards:
                if std.get('referenceId') == standard:
                    return std.get('id')
            
            # If not found, provide helpful error message
            available_standards = [f"{s.get('name')} ({s.get('referenceId')})" for s in standards]
            raise IriusRiskError(
                f"Standard '{standard}' not found.\n"
                f"Available standards: {', '.join(available_standards)}"
            )
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"resolving standard '{standard}'")
