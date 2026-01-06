"""Questionnaire-specific API client for IriusRisk API."""

from typing import Dict, Any, Optional

from .base_client import BaseApiClient
from ..config import Config


class QuestionnaireApiClient(BaseApiClient):
    """API client for questionnaire-specific operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the questionnaire API client.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)
    
    def get_project_questionnaire(self, project_id: str) -> Dict[str, Any]:
        """Get the project (architecture) questionnaire for a specific project.
        
        Args:
            project_id: Project UUID to get questionnaire for
            
        Returns:
            Project questionnaire response with questionnaire, conclusions, and outcomes
        """
        self.logger.info(f"Retrieving project questionnaire for project {project_id}")
        
        endpoint = f'/projects/{project_id}/questionnaire'
        result = self._make_request('GET', endpoint)
        
        # Log results
        if result:
            groups_count = len(result.get('questionnaire', {}).get('groups', []))
            self.logger.info(f"Retrieved project questionnaire with {groups_count} question groups")
        
        return result
    
    def get_component_questionnaire(self, component_id: str) -> Dict[str, Any]:
        """Get the questionnaire for a specific component.
        
        Args:
            component_id: Component UUID to get questionnaire for
            
        Returns:
            Component questionnaire response with questionnaire, conclusions, and outcomes
        """
        self.logger.info(f"Retrieving component questionnaire for component {component_id}")
        
        endpoint = f'/projects/components/{component_id}/questionnaire'
        result = self._make_request('GET', endpoint)
        
        # Log results
        if result:
            groups_count = len(result.get('questionnaire', {}).get('groups', []))
            self.logger.info(f"Retrieved component questionnaire with {groups_count} question groups")
        
        return result
    
    def get_all_component_questionnaires(
        self, 
        project_id: str,
        status: Optional[str] = None,
        page: int = 0,
        size: int = 1000
    ) -> Dict[str, Any]:
        """Get all component questionnaires for a project.
        
        Args:
            project_id: Project UUID to get component questionnaires for
            status: Optional filter by status (COMPLETED, INCOMPLETED)
            page: Page number (0-based)
            size: Number of items per page
            
        Returns:
            Paged response with component questionnaire summaries
        """
        self.logger.info(f"Retrieving all component questionnaires for project {project_id}")
        if status:
            self.logger.debug(f"Filtering by status: {status}")
        
        params = {
            'page': page,
            'size': size
        }
        
        if status:
            params['status'] = status
        
        endpoint = f'/projects/{project_id}/components/questionnaire'
        result = self._make_request('GET', endpoint, params=params)
        
        # Log results
        if result and '_embedded' in result and 'items' in result['_embedded']:
            questionnaire_count = len(result['_embedded']['items'])
            total_elements = result.get('page', {}).get('totalElements', 'unknown')
            self.logger.info(f"Retrieved {questionnaire_count} component questionnaires (total: {total_elements})")
        
        return result
    
    def update_project_questionnaire(
        self, 
        project_id: str, 
        questionnaire_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update the project questionnaire with answers.
        
        Args:
            project_id: Project UUID
            questionnaire_data: Questionnaire update request with steps and answers
            
        Returns:
            Updated questionnaire response
        """
        self.logger.info(f"Updating project questionnaire for project {project_id}")
        
        endpoint = f'/projects/{project_id}/questionnaire'
        
        try:
            result = self._make_request('POST', endpoint, json=questionnaire_data)
            self.logger.info(f"Successfully updated project questionnaire for project {project_id}")
            return result
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Project '{project_id}' not found"
                elif e.response.status_code == 400:
                    error_msg = f"Invalid questionnaire data: {e.response.text}"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"Failed to update project questionnaire: {error_msg}")
    
    def update_component_questionnaire(
        self, 
        component_id: str, 
        questionnaire_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a component questionnaire with answers.
        
        Args:
            component_id: Component UUID
            questionnaire_data: Questionnaire update request with steps and answers
            
        Returns:
            Updated questionnaire response
        """
        self.logger.info(f"Updating component questionnaire for component {component_id}")
        
        endpoint = f'/projects/components/{component_id}/questionnaire'
        
        try:
            result = self._make_request('POST', endpoint, json=questionnaire_data)
            self.logger.info(f"Successfully updated component questionnaire for component {component_id}")
            return result
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Component '{component_id}' not found"
                elif e.response.status_code == 400:
                    error_msg = f"Invalid questionnaire data: {e.response.text}"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"Failed to update component questionnaire: {error_msg}")
