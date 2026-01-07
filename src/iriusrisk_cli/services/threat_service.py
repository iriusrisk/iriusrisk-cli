"""Threat service for handling threat-related business logic."""

import logging
from typing import Optional, Dict, List, Any

from ..repositories.threat_repository import ThreatRepository
from ..utils.project_resolution import resolve_project_id_to_uuid
from ..utils.error_handling import handle_api_error, IriusRiskError

logger = logging.getLogger(__name__)


class ThreatService:
    """Service for managing threat operations."""
    
    def __init__(self, threat_repository=None):
        """Initialize the threat service.
        
        Args:
            threat_repository: ThreatRepository instance (required for dependency injection)
        """
        if threat_repository is None:
            raise ValueError("ThreatService requires a threat_repository instance")
        self.threat_repository = threat_repository
    
    def list_threats(self, project_id: str, page: int = 0, size: int = 20,
                    risk_level: Optional[str] = None, status: Optional[str] = None,
                    custom_filter: Optional[str] = None) -> Dict[str, Any]:
        """List threats from a project with filtering options.
        
        Args:
            project_id: Project UUID or reference ID
            page: Page number (0-based)
            size: Number of threats per page
            risk_level: Filter by risk level (HIGH, MEDIUM, LOW)
            status: Filter by threat status
            custom_filter: Custom filter expression
            
        Returns:
            Dictionary containing threats data and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Listing threats for project '{project_id}' with filters: "
                    f"page={page}, size={size}, risk_level={risk_level}, status={status}")
        
        if custom_filter:
            logger.debug(f"Using custom filter: {custom_filter}")
        
        # Resolve project ID to UUID for V2 API
        logger.debug(f"Resolving project ID to UUID: {project_id}")
        final_project_id = resolve_project_id_to_uuid(project_id, self.threat_repository.api_client)
        logger.debug(f"Resolved to UUID: {final_project_id}")
        
        result = self.threat_repository.list_all(
            project_id=final_project_id,
            page=page,
            size=size,
            risk_level=risk_level,
            status=status,
            custom_filter=custom_filter
        )
        
        threats_count = len(result.get('threats', []))
        total_count = result.get('totalElements', 0)
        logger.info(f"Retrieved {threats_count} threats from project (page {page + 1}, {total_count} total)")
        
        return result
    
    def get_threat(self, project_id: str, threat_id: str) -> Dict[str, Any]:
        """Get a specific threat by ID.
        
        Args:
            project_id: Project UUID or reference ID
            threat_id: Threat ID
            
        Returns:
            Threat data dictionary
            
        Raises:
            IriusRiskError: If threat not found or API request fails
        """
        logger.debug(f"Retrieving threat '{threat_id}' from project '{project_id}'")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id, self.threat_repository.api_client)
        logger.debug(f"Resolved project to UUID: {final_project_id}")
        
        result = self.threat_repository.get_by_id(threat_id, final_project_id)
        
        threat_name = result.get('name', 'Unknown')
        threat_state = result.get('state', 'Unknown')
        risk_score = result.get('risk', 0)
        logger.info(f"Retrieved threat '{threat_name}' (ID: {threat_id}, state: {threat_state}, risk: {risk_score})")
        
        return result
    
    def search_threats(self, project_id: str, search_string: str, 
                      page: int = 0, size: int = 20) -> Dict[str, Any]:
        """Search threats within a project.
        
        Args:
            project_id: Project UUID or reference ID
            search_string: String to search for in threat names, descriptions, etc.
            page: Page number (0-based)
            size: Number of threats per page
            
        Returns:
            Dictionary containing search results and pagination info
            
        Raises:
            IriusRiskError: If search fails
        """
        logger.debug(f"Searching threats in project '{project_id}' with query: '{search_string}' "
                    f"(page={page}, size={size})")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id, self.threat_repository.api_client)
        logger.debug(f"Resolved project to UUID: {final_project_id}")
        
        result = self.threat_repository.search(
            project_id=final_project_id,
            search_string=search_string,
            page=page,
            size=size
        )
        
        threats_count = len(result.get('threats', []))
        total_count = result.get('totalElements', 0)
        logger.info(f"Search returned {threats_count} threats (page {page + 1}, {total_count} total)")
        
        return result
    
    def update_threat_status(self, threat_id: str, status: str, 
                           reason: Optional[str] = None, 
                           comment: Optional[str] = None) -> Dict[str, Any]:
        """Update the status of a threat.
        
        Args:
            threat_id: Threat UUID
            status: New status for the threat
            reason: Reason for the status change (required for "accept" status)
            comment: Detailed comment with implementation details
            
        Returns:
            Dictionary containing update result
            
        Raises:
            IriusRiskError: If update fails or validation errors
        """
        logger.info(f"Updating threat '{threat_id}' status to '{status}'")
        
        if reason:
            logger.debug(f"Update reason: {reason}")
        if comment:
            logger.debug(f"Update includes comment ({len(comment)} characters)")
        
        # Validate required fields
        if status == 'accept' and not reason:
            logger.warning("Status 'accept' requires a reason but none provided")
        
        result = self.threat_repository.update_status(
            threat_id=threat_id,
            status=status,
            reason=reason,
            comment=comment
        )
        
        logger.info(f"Successfully updated threat '{threat_id}' status to '{status}'")
        
        return result
    



