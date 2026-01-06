"""Questionnaire repository for questionnaire data access."""

import logging
from typing import Optional, Dict, List, Any

from .base_repository import BaseRepository
from ..utils.error_handling import IriusRiskError

logger = logging.getLogger(__name__)


class QuestionnaireRepository(BaseRepository):
    """Repository for questionnaire data access operations."""
    
    def get_project_questionnaire(self, project_id: str) -> Dict[str, Any]:
        """Get the project (architecture) questionnaire.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Project questionnaire data dictionary with questionnaire, conclusions, and outcomes
            
        Raises:
            IriusRiskError: If questionnaire not found or API request fails
        """
        logger.debug(f"Retrieving project questionnaire for project '{project_id}'")
        
        try:
            response = self.api_client.get_project_questionnaire(project_id=project_id)
            
            if not response:
                logger.warning(f"No questionnaire data found for project '{project_id}'")
                raise IriusRiskError(f"Project questionnaire for '{project_id}' not found")
            
            groups_count = len(response.get('questionnaire', {}).get('groups', []))
            logger.debug(f"Successfully retrieved project questionnaire with {groups_count} groups")
            return response
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"retrieving project questionnaire for project '{project_id}'")
    
    def get_component_questionnaire(self, component_id: str) -> Dict[str, Any]:
        """Get the questionnaire for a specific component.
        
        Args:
            component_id: Component UUID
            
        Returns:
            Component questionnaire data dictionary with questionnaire, conclusions, and outcomes
            
        Raises:
            IriusRiskError: If questionnaire not found or API request fails
        """
        logger.debug(f"Retrieving component questionnaire for component '{component_id}'")
        
        try:
            response = self.api_client.get_component_questionnaire(component_id=component_id)
            
            if not response:
                logger.warning(f"No questionnaire data found for component '{component_id}'")
                raise IriusRiskError(f"Component questionnaire for '{component_id}' not found")
            
            groups_count = len(response.get('questionnaire', {}).get('groups', []))
            logger.debug(f"Successfully retrieved component questionnaire with {groups_count} groups")
            return response
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"retrieving component questionnaire for component '{component_id}'")
    
    def get_all_component_questionnaires(
        self, 
        project_id: str,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all component questionnaire summaries for a project.
        
        Args:
            project_id: Project UUID
            status: Optional filter by status (COMPLETED, INCOMPLETED)
            
        Returns:
            Dictionary containing component questionnaire summaries
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving all component questionnaires for project '{project_id}'")
        if status:
            logger.debug(f"Filtering by status: {status}")
        
        try:
            # Get all component questionnaires with pagination
            all_items = []
            page = 0
            size = 1000
            
            while True:
                response = self.api_client.get_all_component_questionnaires(
                    project_id=project_id,
                    status=status,
                    page=page,
                    size=size
                )
                
                items = self._extract_items_from_response(response)
                if not items:
                    break
                
                all_items.extend(items)
                
                # Check if there are more pages
                page_info = self._extract_page_info(response)
                total_pages = page_info.get('totalPages', 1)
                if page + 1 >= total_pages:
                    break
                
                page += 1
            
            logger.debug(f"Retrieved {len(all_items)} component questionnaire summaries")
            
            return {
                'items': all_items,
                'total_count': len(all_items)
            }
            
        except Exception as e:
            self._handle_error(e, f"retrieving component questionnaires for project '{project_id}'")
    
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
            
        Raises:
            IriusRiskError: If update fails or validation errors
        """
        logger.debug(f"Updating project questionnaire for project '{project_id}'")
        
        try:
            response = self.api_client.update_project_questionnaire(
                project_id=project_id,
                questionnaire_data=questionnaire_data
            )
            
            logger.debug(f"Successfully updated project questionnaire")
            return response
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"updating project questionnaire for project '{project_id}'")
    
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
            
        Raises:
            IriusRiskError: If update fails or validation errors
        """
        logger.debug(f"Updating component questionnaire for component '{component_id}'")
        
        try:
            response = self.api_client.update_component_questionnaire(
                component_id=component_id,
                questionnaire_data=questionnaire_data
            )
            
            logger.debug(f"Successfully updated component questionnaire")
            return response
            
        except IriusRiskError:
            raise
        except Exception as e:
            self._handle_error(e, f"updating component questionnaire for component '{component_id}'")

