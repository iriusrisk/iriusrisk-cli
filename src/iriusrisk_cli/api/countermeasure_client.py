"""Countermeasure-specific API client for IriusRisk API."""

from typing import Dict, Any, Optional

from .base_client import BaseApiClient
from ..config import Config


class CountermeasureApiClient(BaseApiClient):
    """API client for countermeasure-specific operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the countermeasure API client.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)
    
    def get_countermeasures(self,
                           project_id: str,
                           page: int = 0,
                           size: int = 20,
                           filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get countermeasures for a specific project with optional filtering and pagination."""
        # Log operation start
        self.logger.info(f"Retrieving countermeasures for project {project_id} (page={page}, size={size})")
        if filter_expression:
            self.logger.debug(f"Using filter expression: {filter_expression}")
        
        params = {
            'page': page,
            'size': size
        }

        # Use V2 API countermeasures query endpoint (POST with filter body)
        filter_body = {
            "filters": {
                "all": {
                    "testResults": [],
                    "states": [],
                    "priorities": [],
                    "testExpiryDateStates": [],
                    "issueStates": [],
                    "owners": [],
                    "tags": [],
                    "customFieldValues": []
                },
                "any": {
                    "components": [],
                    "threats": [],
                    "useCases": []
                }
            }
        }

        result = self._make_request('POST', f'/projects/{project_id}/countermeasures/query', params=params, json=filter_body)
        
        # Log results
        if result and '_embedded' in result and 'countermeasures' in result['_embedded']:
            countermeasure_count = len(result['_embedded']['countermeasures'])
            total_elements = result.get('page', {}).get('totalElements', 'unknown')
            self.logger.info(f"Retrieved {countermeasure_count} countermeasures (total: {total_elements})")
        
        return result

    def get_countermeasure(self, project_id: str, countermeasure_id: str) -> Dict[str, Any]:
        """Get a specific countermeasure by ID within a project."""
        # Use V2 API for countermeasures endpoint - individual countermeasures use direct path without project-id
        return self._make_request('GET', f'/projects/countermeasures/{countermeasure_id}')
    
    def update_countermeasure_state(self, countermeasure_id: str, state_transition: str, reason: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """Update the state of a countermeasure.
        
        Args:
            countermeasure_id: Countermeasure ID (UUID)
            state_transition: New state transition (e.g., 'required', 'recommended', 'implemented', 'rejected', 'not-applicable')
            reason: Optional reason for the state change
            comment: Optional detailed comment with implementation details
            
        Returns:
            Response data from the API
        """
        # Log operation start
        self.logger.info(f"Updating countermeasure {countermeasure_id} state to '{state_transition}'")
        if reason:
            self.logger.debug(f"Update reason: {reason}")
        if comment:
            self.logger.debug(f"Update comment provided (length: {len(comment)} chars)")
        
        endpoint = f"/projects/countermeasures/{countermeasure_id}/state"
        
        # Prepare request body - countermeasures only support stateTransition
        body = {"stateTransition": state_transition}
        
        # Note: Based on API testing, countermeasures don't support reason/comment fields
        # The comments are stored in our local tracking but not sent to IriusRisk
        # This is a limitation of the IriusRisk countermeasure API
        
        try:
            result = self._make_request("PUT", endpoint, json=body)
            self.logger.info(f"Successfully updated countermeasure {countermeasure_id} state to '{state_transition}'")
            return result
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Countermeasure '{countermeasure_id}' not found"
                elif e.response.status_code == 400:
                    error_msg = f"Invalid state transition '{state_transition}' for countermeasure '{countermeasure_id}'"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"Failed to update countermeasure state: {error_msg}")
    
    def create_countermeasure_comment(self, countermeasure_id: str, comment: str) -> Dict[str, Any]:
        """Create a comment for a countermeasure.
        
        Args:
            countermeasure_id: Countermeasure ID (UUID)
            comment: Comment text (can include HTML)
            
        Returns:
            Response data from the API
        """
        endpoint = "/projects/countermeasures/comments"
        
        body = {
            "countermeasure": {
                "id": countermeasure_id
            },
            "comment": comment
        }
        
        try:
            return self._make_request("POST", endpoint, json=body)
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Countermeasure '{countermeasure_id}' not found"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"Failed to create countermeasure comment: {error_msg}")
    
    def create_countermeasure_issue(self, project_id: str, countermeasure_id: str, issue_tracker_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an issue in the configured issue tracker for a countermeasure.
        
        Args:
            project_id: Project UUID
            countermeasure_id: Countermeasure UUID
            issue_tracker_id: Optional issue tracker ID to use
            
        Returns:
            Issue creation response (may be empty if successful)
        """
        if issue_tracker_id:
            # Use bulk API to specify issue tracker (async operation)
            data = {
                'countermeasureIds': [countermeasure_id],
                'issueTrackerProfileId': issue_tracker_id
            }
            headers = {'X-Irius-Async': 'true'}  # This is an async operation
            return self._make_request('POST', f'/projects/{project_id}/countermeasures/create-issues/bulk', 
                                    json=data, headers=headers)
        else:
            # Use single countermeasure API (uses project's default issue tracker)
            return self._make_request('POST', f'/projects/countermeasures/{countermeasure_id}/create-issue', json={})
