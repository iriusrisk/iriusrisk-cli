"""Version-specific API client for IriusRisk API."""

from typing import Dict, Any, Optional
from .base_client import BaseApiClient
from ..config import Config


class VersionApiClient(BaseApiClient):
    """API client for project version operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the version API client.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)
    
    def get_versions(self, project_id: str, page: int = 0, size: int = 20) -> Dict[str, Any]:
        """Get all versions for a project with pagination.
        
        Args:
            project_id: Project UUID
            page: Page number (0-based)
            size: Number of items per page
            
        Returns:
            Paged response with versions
        """
        self.logger.info(f"Retrieving versions for project {project_id} (page={page}, size={size})")
        
        params = {
            'page': page,
            'size': size
        }
        
        result = self._make_request('GET', f'/projects/{project_id}/versions', params=params)
        
        # Log results
        if result and '_embedded' in result and 'items' in result['_embedded']:
            version_count = len(result['_embedded']['items'])
            total_elements = result.get('page', {}).get('totalElements', 'unknown')
            self.logger.info(f"Retrieved {version_count} versions (total: {total_elements})")
        
        return result
    
    def create_version(self, project_id: str, name: str, description: Optional[str] = None, x_irius_async: bool = True) -> Dict[str, Any]:
        """Create a version snapshot of a project.
        
        Args:
            project_id: Project UUID
            name: Version name
            description: Optional version description
            x_irius_async: Whether to use async operation
            
        Returns:
            Async operation response or version response
        """
        self.logger.info(f"Creating version '{name}' for project {project_id}")
        
        payload = {
            'name': name
        }
        
        if description:
            payload['description'] = description
        
        headers = {
            'X-Irius-Async': str(x_irius_async).lower()
        }
        
        result = self._make_request('POST', f'/projects/{project_id}/versions', json=payload, headers=headers)
        
        if result:
            self.logger.info(f"Version creation initiated: {result.get('id', 'unknown')}")
        
        return result
    
    def update_version(self, version_id: str, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Update version metadata.
        
        Args:
            version_id: Version UUID
            name: New version name
            description: New version description
            
        Returns:
            Updated version response
        """
        self.logger.info(f"Updating version {version_id}")
        
        payload = {
            'name': name
        }
        
        if description is not None:
            payload['description'] = description
        
        result = self._make_request('PUT', f'/projects/versions/{version_id}', json=payload)
        
        if result:
            self.logger.info(f"Version {version_id} updated successfully")
        
        return result
    
    def delete_version(self, version_id: str, x_irius_async: bool = True) -> Dict[str, Any]:
        """Delete a project version.
        
        Args:
            version_id: Version UUID
            x_irius_async: Whether to use async operation
            
        Returns:
            Async operation response or empty response
        """
        self.logger.info(f"Deleting version {version_id}")
        
        headers = {
            'X-Irius-Async': str(x_irius_async).lower()
        }
        
        result = self._make_request('DELETE', f'/projects/versions/{version_id}', headers=headers)
        
        self.logger.info(f"Version {version_id} deletion initiated")
        
        return result
    
    def restore_version(self, version_id: str, x_irius_async: bool = True) -> Dict[str, Any]:
        """Restore a project to a specific version.
        
        Args:
            version_id: Version UUID to restore
            x_irius_async: Whether to use async operation
            
        Returns:
            Async operation response
        """
        self.logger.info(f"Restoring project to version {version_id}")
        
        headers = {
            'X-Irius-Async': str(x_irius_async).lower()
        }
        
        result = self._make_request('POST', f'/projects/versions/{version_id}/restore', headers=headers)
        
        if result:
            self.logger.info(f"Version restoration initiated: {result.get('id', 'unknown')}")
        
        return result
    
    def create_project_from_version(self, version_id: str, name: str, reference_id: str, 
                                   description: Optional[str] = None, tags: Optional[str] = None,
                                   x_irius_async: bool = True) -> Dict[str, Any]:
        """Create a new project from a version snapshot.
        
        Args:
            version_id: Version UUID
            name: New project name
            reference_id: New project reference ID
            description: New project description
            tags: New project tags
            x_irius_async: Whether to use async operation
            
        Returns:
            Async operation response
        """
        self.logger.info(f"Creating new project from version {version_id}")
        
        payload = {
            'name': name,
            'referenceId': reference_id
        }
        
        if description:
            payload['description'] = description
        if tags:
            payload['tags'] = tags
        
        headers = {
            'X-Irius-Async': str(x_irius_async).lower()
        }
        
        result = self._make_request('POST', f'/projects/versions/{version_id}/create-project', 
                                   json=payload, headers=headers)
        
        if result:
            self.logger.info(f"Project creation from version initiated: {result.get('id', 'unknown')}")
        
        return result
    
    def compare_versions(self, source_version_id: str, target_version_id: str, 
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
            Paged response with version differences
        """
        self.logger.info(f"Comparing versions {source_version_id} -> {target_version_id}")
        
        payload = {
            'source': {
                'versionId': source_version_id
            },
            'target': {
                'versionId': target_version_id
            }
        }
        
        params = {
            'page': page,
            'size': size
        }
        
        if filter_expression:
            params['filter'] = filter_expression
        
        result = self._make_request('POST', '/projects/versions/compare/changes', 
                                   json=payload, params=params)
        
        # Log results
        if result and '_embedded' in result and 'changes' in result['_embedded']:
            change_count = len(result['_embedded']['changes'])
            total_elements = result.get('page', {}).get('totalElements', 'unknown')
            self.logger.info(f"Found {change_count} changes (total: {total_elements})")
        
        return result

