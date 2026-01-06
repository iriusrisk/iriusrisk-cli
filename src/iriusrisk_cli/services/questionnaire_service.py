"""Questionnaire service for handling questionnaire-related business logic."""

import logging
from typing import Optional, Dict, List, Any

from ..repositories.questionnaire_repository import QuestionnaireRepository
from ..utils.project_resolution import resolve_project_id_to_uuid
from ..utils.error_handling import handle_api_error, IriusRiskError

logger = logging.getLogger(__name__)


class QuestionnaireService:
    """Service for managing questionnaire operations."""
    
    def __init__(self, questionnaire_repository=None):
        """Initialize the questionnaire service.
        
        Args:
            questionnaire_repository: QuestionnaireRepository instance (required for dependency injection)
        """
        if questionnaire_repository is None:
            raise ValueError("QuestionnaireService requires a questionnaire_repository instance")
        self.questionnaire_repository = questionnaire_repository
    
    def get_project_questionnaire(self, project_id: str) -> Dict[str, Any]:
        """Get the project (architecture) questionnaire.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            Dictionary containing questionnaire data with groups, conclusions, and outcomes
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving project questionnaire for project '{project_id}'")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved to UUID: {final_project_id}")
        
        result = self.questionnaire_repository.get_project_questionnaire(
            project_id=final_project_id
        )
        
        groups_count = len(result.get('questionnaire', {}).get('groups', []))
        logger.info(f"Retrieved project questionnaire with {groups_count} question groups")
        
        return result
    
    def get_component_questionnaire(self, component_id: str) -> Dict[str, Any]:
        """Get the questionnaire for a specific component.
        
        Args:
            component_id: Component UUID
            
        Returns:
            Dictionary containing questionnaire data with groups, conclusions, and outcomes
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving component questionnaire for component '{component_id}'")
        
        result = self.questionnaire_repository.get_component_questionnaire(
            component_id=component_id
        )
        
        groups_count = len(result.get('questionnaire', {}).get('groups', []))
        logger.info(f"Retrieved component questionnaire with {groups_count} question groups")
        
        return result
    
    def get_all_component_questionnaires(
        self, 
        project_id: str,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all component questionnaire summaries for a project.
        
        Args:
            project_id: Project UUID or reference ID
            status: Optional filter by status (COMPLETED, INCOMPLETED)
            
        Returns:
            Dictionary containing component questionnaire summaries
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving all component questionnaires for project '{project_id}'")
        if status:
            logger.debug(f"Filtering by status: {status}")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved to UUID: {final_project_id}")
        
        result = self.questionnaire_repository.get_all_component_questionnaires(
            project_id=final_project_id,
            status=status
        )
        
        count = result.get('total_count', 0)
        logger.info(f"Retrieved {count} component questionnaire summaries")
        
        return result
    
    def get_all_component_questionnaires_detailed(
        self,
        project_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get full questionnaire data for all components in a project.
        
        This method first gets the list of components with questionnaires,
        then retrieves the full questionnaire for each one.
        
        Args:
            project_id: Project UUID or reference ID
            status: Optional filter by status (COMPLETED, INCOMPLETED)
            
        Returns:
            List of detailed component questionnaire data
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving detailed questionnaires for all components in project '{project_id}'")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved to UUID: {final_project_id}")
        
        # Get summary list of components with questionnaires
        summary = self.questionnaire_repository.get_all_component_questionnaires(
            project_id=final_project_id,
            status=status
        )
        
        component_summaries = summary.get('items', [])
        logger.debug(f"Found {len(component_summaries)} components with questionnaires")
        
        # Get full questionnaire for each component
        detailed_questionnaires = []
        for i, summary_item in enumerate(component_summaries):
            component_data = summary_item.get('component', {})
            component_id = component_data.get('id')
            component_name = component_data.get('name', 'Unknown')
            component_ref_id = component_data.get('ref', '')
            questionnaire_status = summary_item.get('status', 'UNKNOWN')
            
            if not component_id:
                logger.warning(f"Component summary missing ID, skipping: {summary_item}")
                continue
            
            logger.debug(f"({i+1}/{len(component_summaries)}) Fetching detailed questionnaire for component '{component_name}' ({component_id})")
            
            try:
                questionnaire_data = self.questionnaire_repository.get_component_questionnaire(
                    component_id=component_id
                )
                
                # Add metadata to the questionnaire
                detailed_entry = {
                    'componentId': component_id,
                    'componentName': component_name,
                    'componentReferenceId': component_ref_id,
                    'status': questionnaire_status,
                    'questionnaire': questionnaire_data.get('questionnaire', {}),
                    'conclusions': questionnaire_data.get('conclusions', []),
                    'outcomes': questionnaire_data.get('outcomes', {})
                }
                
                detailed_questionnaires.append(detailed_entry)
                
            except Exception as e:
                logger.warning(f"Failed to get questionnaire for component '{component_name}' ({component_id}): {e}")
                # Continue with other components even if one fails
                continue
        
        logger.info(f"Retrieved detailed questionnaires for {len(detailed_questionnaires)} components")
        return detailed_questionnaires
    
    def update_project_questionnaire(
        self, 
        project_id: str, 
        questionnaire_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update the project questionnaire with answers.
        
        Args:
            project_id: Project UUID or reference ID
            questionnaire_data: Questionnaire update request with steps and answers
            
        Returns:
            Updated questionnaire response
            
        Raises:
            IriusRiskError: If update fails or validation errors
        """
        logger.info(f"Updating project questionnaire for project '{project_id}'")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved to UUID: {final_project_id}")
        
        result = self.questionnaire_repository.update_project_questionnaire(
            project_id=final_project_id,
            questionnaire_data=questionnaire_data
        )
        
        logger.info(f"Successfully updated project questionnaire for project '{project_id}'")
        return result
    
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
        logger.info(f"Updating component questionnaire for component '{component_id}'")
        
        result = self.questionnaire_repository.update_component_questionnaire(
            component_id=component_id,
            questionnaire_data=questionnaire_data
        )
        
        logger.info(f"Successfully updated component questionnaire for component '{component_id}'")
        return result
