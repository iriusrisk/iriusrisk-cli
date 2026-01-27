"""Threat-specific API client for IriusRisk API."""

from typing import Dict, Any, Optional

from .base_client import BaseApiClient
from ..config import Config


class ThreatApiClient(BaseApiClient):
    """API client for threat-specific operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the threat API client.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)
    
    def get_threats(self, 
                    project_id: str,
                    page: int = 0, 
                    size: int = 20, 
                    filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get threats for a specific project with optional filtering and pagination.
        
        Args:
            project_id: Project ID to get threats for
            page: Page number (0-based)
            size: Number of items per page
            filter_expression: Filter expression for server-side filtering
            
        Returns:
            Paged response with threats
        """
        # Log operation start
        self.logger.info(f"Retrieving threats for project {project_id} (page={page}, size={size})")
        if filter_expression:
            self.logger.debug(f"Using filter expression: {filter_expression}")
        
        params = {
            'page': page,
            'size': size
        }
        
        # Use V2 API threats query endpoint (POST with filter body)
        filter_body = {
            "filters": {
                "all": {
                    "states": ["expose", "partly-mitigate", "mitigate", "hidden"],
                    "libraries": [],
                    "componentTags": [],
                    "currentRisks": [],
                    "countermeasureProgressRanges": [],
                    "countermeasureTestStatuses": [],
                    "weaknessTestStatuses": [],
                    "components": [],
                    "useCases": [],
                    "owners": [],
                    "customFieldValues": []
                }
            }
        }
        
        result = self._make_request('POST', f'/projects/{project_id}/threats/query', params=params, json=filter_body)
        
        # Log results
        if result and '_embedded' in result and 'threats' in result['_embedded']:
            threat_count = len(result['_embedded']['threats'])
            total_elements = result.get('page', {}).get('totalElements', 'unknown')
            self.logger.info(f"Retrieved {threat_count} threats (total: {total_elements})")
        
        return result
    
    def get_threats_version(self, 
                           project_id: str,
                           version_id: str,
                           page: int = 0, 
                           size: int = 20) -> Dict[str, Any]:
        """Get threats for a specific project version.
        
        Args:
            project_id: Project ID to get threats for
            version_id: Version UUID
            page: Page number (0-based)
            size: Number of items per page
            
        Returns:
            Paged response with threats from the specified version
        """
        self.logger.info(f"Retrieving threats for project {project_id}, version {version_id}")
        
        params = {
            'page': page,
            'size': size,
            'version': version_id
        }
        
        filter_body = {
            "filters": {
                "all": {
                    "states": ["expose", "partly-mitigate", "mitigate", "hidden"],
                    "libraries": [],
                    "componentTags": [],
                    "currentRisks": [],
                    "countermeasureProgressRanges": [],
                    "countermeasureTestStatuses": [],
                    "weaknessTestStatuses": [],
                    "components": [],
                    "useCases": [],
                    "owners": [],
                    "customFieldValues": []
                }
            }
        }
        
        result = self._make_request('POST', f'/projects/{project_id}/threats/query', params=params, json=filter_body)
        
        if result and '_embedded' in result and 'threats' in result['_embedded']:
            threat_count = len(result['_embedded']['threats'])
            self.logger.info(f"Retrieved {threat_count} threats from version")
        
        return result
    
    def get_threat(self, project_id: str, threat_id: str) -> Dict[str, Any]:
        """Get a specific threat by ID within a project.
        
        Args:
            project_id: Project ID (not used in V2 API path but kept for compatibility)
            threat_id: Threat ID
            
        Returns:
            Threat data
        """
        # Use V2 API for threats endpoint - individual threats use direct path without project-id
        return self._make_request('GET', f'/projects/threats/{threat_id}')
    
    def update_threat_state(self, threat_id: str, state_transition: str, reason: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """Update the state of a threat.
        
        Args:
            threat_id: Threat ID (UUID)
            state_transition: New state transition (e.g., 'accept', 'mitigate', 'expose')
            reason: Optional reason for the state change
            comment: Optional detailed comment with implementation details
            
        Returns:
            Response data from the API
        """
        # Log operation start
        self.logger.info(f"Updating threat {threat_id} state to '{state_transition}'")
        if reason:
            self.logger.debug(f"Update reason: {reason}")
        if comment:
            self.logger.debug(f"Update comment provided (length: {len(comment)} chars)")
        
        endpoint = f"/projects/threats/{threat_id}/state"
        
        # Prepare request body
        body = {"stateTransition": state_transition}
        
        # Combine reason and comment into the reason field (IriusRisk API only supports reason)
        if reason or comment:
            combined_reason = ""
            if reason:
                combined_reason = reason
            if comment:
                if reason:
                    combined_reason += f"\n\nImplementation Details:\n{comment}"
                else:
                    combined_reason = comment
            body["reason"] = combined_reason
        
        try:
            result = self._make_request("PUT", endpoint, json=body)
            self.logger.info(f"Successfully updated threat {threat_id} state to '{state_transition}'")
            return result
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Threat '{threat_id}' not found"
                elif e.response.status_code == 400:
                    error_msg = f"Invalid state transition '{state_transition}' for threat '{threat_id}'"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"Failed to update threat state: {error_msg}")
    
    def create_threat_comment(self, threat_id: str, comment: str) -> Dict[str, Any]:
        """Create a comment for a threat.
        
        Args:
            threat_id: Threat ID (UUID)
            comment: Comment text (can include HTML)
            
        Returns:
            Response data from the API
        """
        endpoint = "/projects/threats/comments"
        
        body = {
            "threat": {
                "id": threat_id
            },
            "comment": comment
        }
        
        try:
            return self._make_request("POST", endpoint, json=body)
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Threat '{threat_id}' not found"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"Failed to create threat comment: {error_msg}")
