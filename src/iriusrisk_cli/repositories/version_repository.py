"""Version repository for version data access."""

import logging
from typing import Optional, Dict, Any

from .base_repository import BaseRepository
from ..utils.error_handling import IriusRiskError

logger = logging.getLogger(__name__)


class VersionRepository(BaseRepository):
    """Repository for project version data access operations."""
    
    def get_by_id(self, version_id: str) -> Dict[str, Any]:
        """Get a specific version by ID.
        
        Args:
            version_id: Version UUID
            
        Returns:
            Version data
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Getting version {version_id}")
        
        try:
            result = self.api_client.get_version(version_id=version_id)
            logger.debug(f"Retrieved version {version_id}")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"getting version '{version_id}'")
    
    def list_all(self, project_id: str, page: int = 0, size: int = 20) -> Dict[str, Any]:
        """List all versions for a project.
        
        Args:
            project_id: Project UUID
            page: Page number (0-based)
            size: Number of versions per page
            
        Returns:
            Dictionary containing versions data and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Listing versions for project {project_id} - page: {page}, size: {size}")
        
        try:
            response = self.api_client.get_versions(
                project_id=project_id,
                page=page,
                size=size
            )
            
            versions_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(versions_data)} versions from API")
            
            return {
                'versions': versions_data,
                'page_info': page_info,
                'full_response': response
            }
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"listing versions for project '{project_id}'")
    
    def create(self, project_id: str, name: str, description: Optional[str] = None, 
              wait: bool = True) -> Dict[str, Any]:
        """Create a version snapshot of a project.
        
        Args:
            project_id: Project UUID
            name: Version name
            description: Optional version description
            wait: Whether to use async operation
            
        Returns:
            Version creation response
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Creating version '{name}' for project {project_id}")
        
        try:
            result = self.api_client.create_version(
                project_id=project_id,
                name=name,
                description=description,
                x_irius_async=wait
            )
            
            logger.debug(f"Version creation initiated")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"creating version '{name}' for project '{project_id}'")
    
    def update(self, version_id: str, name: str, description: Optional[str] = None) -> Dict[str, Any]:
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
        
        try:
            result = self.api_client.update_version(
                version_id=version_id,
                name=name,
                description=description
            )
            
            logger.debug(f"Version updated successfully")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"updating version '{version_id}'")
    
    def delete(self, version_id: str, wait: bool = True) -> Dict[str, Any]:
        """Delete a project version.
        
        Args:
            version_id: Version UUID
            wait: Whether to use async operation
            
        Returns:
            Deletion response
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Deleting version {version_id}")
        
        try:
            result = self.api_client.delete_version(
                version_id=version_id,
                x_irius_async=wait
            )
            
            logger.debug(f"Version deletion initiated")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"deleting version '{version_id}'")
    
    def restore(self, version_id: str, wait: bool = True) -> Dict[str, Any]:
        """Restore a project to a specific version.
        
        Args:
            version_id: Version UUID to restore
            wait: Whether to use async operation
            
        Returns:
            Restoration response
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Restoring project to version {version_id}")
        
        try:
            result = self.api_client.restore_version(
                version_id=version_id,
                x_irius_async=wait
            )
            
            logger.debug(f"Version restoration initiated")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"restoring version '{version_id}'")
    
    def create_project_from_version(self, version_id: str, name: str, reference_id: str,
                                   description: Optional[str] = None, tags: Optional[str] = None,
                                   wait: bool = True) -> Dict[str, Any]:
        """Create a new project from a version snapshot.
        
        Args:
            version_id: Version UUID
            name: New project name
            reference_id: New project reference ID
            description: New project description
            tags: New project tags
            wait: Whether to use async operation
            
        Returns:
            Project creation response
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Creating new project from version {version_id}")
        
        try:
            result = self.api_client.create_project_from_version(
                version_id=version_id,
                name=name,
                reference_id=reference_id,
                description=description,
                tags=tags,
                x_irius_async=wait
            )
            
            logger.debug(f"Project creation from version initiated")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"creating project from version '{version_id}'")
    
    def compare(self, source_version_id: str, target_version_id: str,
               page: int = 0, size: int = 100,
               filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Compare two project versions to see what changed.
        
        Args:
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
        
        try:
            response = self.api_client.compare_versions(
                source_version_id=source_version_id,
                target_version_id=target_version_id,
                page=page,
                size=size,
                filter_expression=filter_expression
            )
            
            changes_data = self._extract_items_from_response(response, 'changes')
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(changes_data)} changes from comparison")
            
            return {
                'changes': changes_data,
                'page_info': page_info,
                'full_response': response
            }
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"comparing versions '{source_version_id}' and '{target_version_id}'")

