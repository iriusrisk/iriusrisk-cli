"""Project repository for project data access."""

import logging
from typing import Optional, Dict, List, Any

from .base_repository import BaseRepository
from ..utils.error_handling import IriusRiskError

logger = logging.getLogger(__name__)


class ProjectRepository(BaseRepository):
    """Repository for project data access operations."""
    
    def get_by_id(self, project_id: str) -> Dict[str, Any]:
        """Get a project by UUID.
        
        Note: This method expects a UUID. If you have a reference ID, resolve it to UUID
        first using resolve_project_id_to_uuid() at the service layer.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Project data dictionary
            
        Raises:
            IriusRiskError: If project not found or API request fails
        """
        logger.debug(f"Retrieving project by UUID: {project_id}")
        
        try:
            project_data = self.api_client.get_project(project_id)
            logger.debug(f"Successfully retrieved project '{project_data.get('name', 'Unknown')}'")
            return project_data
                    
        except IriusRiskError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve project '{project_id}': {e}")
            self._handle_error(e, f"retrieving project '{project_id}'")
    
    def list_all(self, page: int = 0, size: int = 20, 
                 name: Optional[str] = None, tags: Optional[str] = None,
                 workflow_state: Optional[str] = None, archived: Optional[bool] = None,
                 blueprint: Optional[bool] = None, include_versions: bool = False,
                 custom_filter: Optional[str] = None) -> Dict[str, Any]:
        """List projects with filtering options.
        
        Args:
            page: Page number (0-based)
            size: Number of projects per page
            name: Filter by project name (partial match)
            tags: Filter by tags (space-separated)
            workflow_state: Filter by workflow state
            archived: Filter by archived status
            blueprint: Filter by blueprint status
            include_versions: Include version information
            custom_filter: Custom filter expression
            
        Returns:
            Dictionary containing projects data and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Listing projects - page: {page}, size: {size}, include_versions: {include_versions}")
        logger.debug(f"Filters - name: {name}, tags: {tags}, workflow_state: {workflow_state}, archived: {archived}, blueprint: {blueprint}")
        
        try:
            # Build filter expression
            filter_expr = custom_filter
            if not filter_expr:
                logger.debug("Building filter expression from individual parameters")
                filter_expr = self._build_filter_expression(
                    name=name, 
                    tags=tags, 
                    workflow_state=workflow_state,
                    archived=archived,
                    blueprint=blueprint
                )
            
            if filter_expr:
                logger.debug(f"Using filter expression: {filter_expr}")
            else:
                logger.debug("No filters applied - retrieving all projects")
            
            # Make API request
            logger.debug(f"Making API request for projects with page={page}, size={size}")
            response = self.api_client.get_projects(
                page=page,
                size=size,
                include_versions=include_versions,
                filter_expression=filter_expr
            )
            
            projects_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(projects_data)} projects")
            logger.debug(f"Page info: {page_info}")
            
            return {
                'projects': projects_data,
                'page_info': page_info,
                'full_response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve projects: {e}")
            self._handle_error(e, "retrieving projects")
    
    def search(self, search_string: str, page: int = 0, size: int = 20,
               include_versions: bool = False) -> Dict[str, Any]:
        """Search projects by name, ID, or description.
        
        Args:
            search_string: String to search for
            page: Page number (0-based)
            size: Number of projects per page
            include_versions: Include version information
            
        Returns:
            Dictionary containing search results and pagination info
            
        Raises:
            IriusRiskError: If search fails
        """
        logger.debug(f"Searching projects for: '{search_string}' (page: {page}, size: {size})")
        
        try:
            if not search_string.strip():
                logger.warning("Empty search string provided")
                raise IriusRiskError("Search string cannot be empty")
            
            # Build comprehensive search filter using OR conditions
            search_filters = [
                f"'name'~'{search_string}'",           # Search in name
                f"'referenceId'~'{search_string}'",    # Search in reference ID  
                f"'description'~'{search_string}'"     # Search in description
            ]
            
            # Combine with OR logic
            filter_expr = ':OR:'.join(search_filters)
            logger.debug(f"Built search filter expression: {filter_expr}")
            
            # Make API request with search filter
            logger.debug(f"Making API search request with filter")
            response = self.api_client.get_projects(
                page=page,
                size=size,
                include_versions=include_versions,
                filter_expression=filter_expr
            )
            
            projects_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Search returned {len(projects_data)} projects matching '{search_string}'")
            
            return {
                'projects': projects_data,
                'page_info': page_info,
                'full_response': response,
                'search_string': search_string
            }
            
        except IriusRiskError:
            raise
        except Exception as e:
            logger.error(f"Failed to search projects for '{search_string}': {e}")
            self._handle_error(e, f"searching projects for '{search_string}'")
    
    def get_artifacts(self, project_id: str, page: int = 0, size: int = 100) -> Dict[str, Any]:
        """Get project artifacts.
        
        Args:
            project_id: Project UUID
            page: Page number (0-based)
            size: Number of artifacts per page
            
        Returns:
            Dictionary containing artifacts data
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving artifacts for project '{project_id}' (page: {page}, size: {size})")
        
        try:
            response = self.api_client.get_project_artifacts(project_id, page=page, size=size)
            artifacts = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(artifacts)} artifacts for project '{project_id}'")
            
            return {
                'artifacts': artifacts,
                'page_info': page_info,
                'full_response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve artifacts for project '{project_id}': {e}")
            self._handle_error(e, f"retrieving artifacts for project '{project_id}'")
    
    def get_artifact_content(self, artifact_id: str, size: str = 'ORIGINAL') -> Dict[str, Any]:
        """Get artifact content.
        
        Args:
            artifact_id: Artifact UUID
            size: Image size ('ORIGINAL', 'PREVIEW', 'THUMBNAIL')
            
        Returns:
            Dictionary containing artifact content
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving content for artifact '{artifact_id}' (size: {size})")
        
        try:
            content = self.api_client.get_project_artifact_content(artifact_id, size=size.upper())
            logger.debug(f"Successfully retrieved artifact content for '{artifact_id}'")
            return content
            
        except Exception as e:
            logger.error(f"Failed to retrieve content for artifact '{artifact_id}': {e}")
            self._handle_error(e, f"retrieving content for artifact '{artifact_id}'")
    
    def _build_filter_expression(self, name: Optional[str] = None,
                               tags: Optional[str] = None,
                               workflow_state: Optional[str] = None,
                               archived: Optional[bool] = None,
                               blueprint: Optional[bool] = None) -> Optional[str]:
        """Build a filter expression for the API based on provided filters."""
        logger.debug("Building filter expression from parameters")
        filters = []
        
        if name:
            # Use contains operator for name matching
            filter_part = f"'name'~'{name}'"
            filters.append(filter_part)
            logger.debug(f"Added name filter: {filter_part}")
        
        if tags:
            # Filter by tags - assuming tags are space-separated in the API
            tag_list = tags.split()
            logger.debug(f"Processing {len(tag_list)} tags: {tag_list}")
            for tag in tag_list:
                filter_part = f"'tags'~'{tag}'"
                filters.append(filter_part)
                logger.debug(f"Added tag filter: {filter_part}")
        
        if workflow_state:
            filter_part = f"'workflowState.referenceId'='{workflow_state}'"
            filters.append(filter_part)
            logger.debug(f"Added workflow state filter: {filter_part}")
        
        if archived is not None:
            filter_part = f"'isArchived'={str(archived).lower()}"
            filters.append(filter_part)
            logger.debug(f"Added archived filter: {filter_part}")
        
        if blueprint is not None:
            filter_part = f"'isBlueprint'={str(blueprint).lower()}"
            filters.append(filter_part)
            logger.debug(f"Added blueprint filter: {filter_part}")
        
        if not filters:
            logger.debug("No filters to apply")
            return None
        
        # Join filters with AND
        result = ':AND:'.join(filters)
        logger.debug(f"Built complete filter expression: {result}")
        return result
