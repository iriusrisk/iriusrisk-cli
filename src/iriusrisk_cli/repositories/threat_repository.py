"""Threat repository for threat data access."""

import logging
from typing import Optional, Dict, List, Any

from .base_repository import BaseRepository
from ..utils.lookup import find_threat_by_id
from ..utils.error_handling import IriusRiskError

logger = logging.getLogger(__name__)


class ThreatRepository(BaseRepository):
    """Repository for threat data access operations."""
    
    def get_by_id(self, threat_id: str, project_id: str) -> Dict[str, Any]:
        """Get a threat by ID within a project.
        
        Args:
            threat_id: Threat ID
            project_id: Project UUID
            
        Returns:
            Threat data dictionary
            
        Raises:
            IriusRiskError: If threat not found or API request fails
        """
        logger.debug(f"Retrieving threat '{threat_id}' from project '{project_id}'")
        
        try:
            # Get all threats and find the specific one (since individual threat API doesn't work)
            logger.debug(f"Fetching all threats from project '{project_id}' to find specific threat")
            response = self.api_client.get_threats(
                project_id=project_id,
                page=0,
                size=1000
            )
            
            # Handle different response formats
            all_threats_data = self._extract_items_from_response(response)
            logger.debug(f"Retrieved {len(all_threats_data)} threat components from API")
            
            # Find the specific threat
            logger.debug(f"Searching for threat '{threat_id}' in retrieved data")
            threat_data = find_threat_by_id(all_threats_data, threat_id)
            
            if not threat_data:
                logger.warning(f"Threat '{threat_id}' not found in project '{project_id}'")
                raise IriusRiskError(f"Threat '{threat_id}' not found")
            
            logger.debug(f"Successfully found threat '{threat_id}': {threat_data.get('name', 'Unknown')}")
            return threat_data
            
        except IriusRiskError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve threat '{threat_id}' from project '{project_id}': {e}")
            self._handle_error(e, f"retrieving threat '{threat_id}' from project '{project_id}'")
    
    def list_all(self, project_id: str, page: int = 0, size: int = 20,
                 risk_level: Optional[str] = None, status: Optional[str] = None,
                 custom_filter: Optional[str] = None) -> Dict[str, Any]:
        """List threats from a project with filtering options.
        
        Args:
            project_id: Project UUID
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
        logger.debug(f"Listing threats from project '{project_id}' - page: {page}, size: {size}")
        logger.debug(f"Filters - risk_level: {risk_level}, status: {status}")
        
        try:
            # Build filter expression
            filter_expr = custom_filter
            if not filter_expr:
                logger.debug("Building filter expression from parameters")
                filter_expr = self._build_threat_filter_expression(
                    risk_level=risk_level,
                    status=status
                )
            
            if filter_expr:
                logger.debug(f"Using filter expression: {filter_expr}")
            else:
                logger.debug("No filters applied - retrieving all threats")
            
            # Make API request
            logger.debug(f"Making API request for threats with page={page}, size={size}")
            response = self.api_client.get_threats(
                project_id=project_id,
                page=page,
                size=size,
                filter_expression=filter_expr
            )
            
            # Handle different response formats
            threats_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(threats_data)} threat components")
            logger.debug(f"Page info: {page_info}")
            
            return {
                'threats': threats_data,
                'page_info': page_info,
                'full_response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve threats from project '{project_id}': {e}")
            self._handle_error(e, f"retrieving threats from project '{project_id}'")
    
    def search(self, project_id: str, search_string: str, 
               page: int = 0, size: int = 20) -> Dict[str, Any]:
        """Search threats within a project.
        
        Args:
            project_id: Project UUID
            search_string: String to search for in threat names, descriptions, etc.
            page: Page number (0-based)
            size: Number of threats per page
            
        Returns:
            Dictionary containing search results and pagination info
            
        Raises:
            IriusRiskError: If search fails
        """
        logger.debug(f"Searching threats in project '{project_id}' for: '{search_string}'")
        
        try:
            # Make API request (using V2 API)
            logger.debug("Fetching all threats for client-side search filtering")
            response = self.api_client.get_threats(
                project_id=project_id,
                page=0,  # Get all threats for client-side filtering
                size=1000  # Large size to get all threats
            )
            
            # Handle different response formats
            all_threats_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(all_threats_data)} threat components for search")
            
            if not all_threats_data:
                logger.debug("No threats found in project - returning empty results")
                return {
                    'threats': [],
                    'page_info': {},
                    'full_response': response,
                    'search_string': search_string
                }
            
            # Apply client-side filtering for search
            logger.debug(f"Applying client-side search filter for '{search_string}'")
            threats_data = self._filter_threats_by_search(all_threats_data, search_string)
            
            logger.debug(f"Search returned {len(threats_data)} matching threat components")
            
            return {
                'threats': threats_data,
                'page_info': page_info,
                'full_response': response,
                'search_string': search_string
            }
            
        except Exception as e:
            logger.error(f"Failed to search threats for '{search_string}' in project '{project_id}': {e}")
            self._handle_error(e, f"searching threats for '{search_string}' in project '{project_id}'")
    
    def update_status(self, threat_id: str, status: str, 
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
        logger.debug(f"Updating threat '{threat_id}' to status '{status}'")
        logger.debug(f"Reason: {reason}, Comment provided: {bool(comment)}")
        
        try:
            # Validate that reason is provided when status is "accept"
            if status.lower() == 'accept' and not reason:
                logger.error("Accept status requires a reason but none provided")
                raise IriusRiskError("The 'accept' status requires a reason")
            
            # Update threat state
            logger.debug(f"Making API call to update threat state")
            response = self.api_client.update_threat_state(
                threat_id=threat_id,
                state_transition=status.lower(),
                reason=reason,
                comment=comment
            )
            
            logger.debug(f"Threat state update successful")
            
            result = {
                'threat_id': threat_id,
                'status': status,
                'reason': reason,
                'comment_created': False,
                'response': response
            }
            
            # Create separate comment if provided
            if comment:
                logger.debug(f"Creating separate comment for threat '{threat_id}'")
                try:
                    self.api_client.create_threat_comment(
                        threat_id=threat_id,
                        comment=comment
                    )
                    result['comment_created'] = True
                    logger.debug(f"Comment created successfully")
                except Exception as comment_error:
                    logger.warning(f"Failed to create comment: {comment_error}")
                    result['comment_error'] = str(comment_error)
            
            logger.debug(f"Threat update completed successfully")
            return result
            
        except IriusRiskError:
            raise
        except Exception as e:
            logger.error(f"Failed to update threat '{threat_id}' to status '{status}': {e}")
            self._handle_error(e, f"updating threat '{threat_id}' to status '{status}'")
    
    def _build_threat_filter_expression(self, search_string: Optional[str] = None,
                                      risk_level: Optional[str] = None,
                                      status: Optional[str] = None) -> Optional[str]:
        """Build a filter expression for threat API based on provided filters."""
        logger.debug("Building threat filter expression from parameters")
        filters = []
        
        if search_string:
            # Use contains operator for searching across multiple fields
            filter_part = f"'name'~'{search_string}':OR:'desc'~'{search_string}':OR:'ref'~'{search_string}'"
            filters.append(filter_part)
            logger.debug(f"Added search filter: {filter_part}")
        
        if risk_level:
            filter_part = f"'risk'='{risk_level.upper()}'"
            filters.append(filter_part)
            logger.debug(f"Added risk level filter: {filter_part}")
        
        if status:
            filter_part = f"'state'='{status}'"
            filters.append(filter_part)
            logger.debug(f"Added status filter: {filter_part}")
        
        if not filters:
            logger.debug("No filters to apply")
            return None
        
        # Join filters with AND
        result = ':AND:'.join(filters)
        logger.debug(f"Built complete threat filter expression: {result}")
        return result
    
    def _filter_threats_by_search(self, threats_data: List[Dict], search_string: str) -> List[Dict]:
        """Filter threats by search string using client-side filtering."""
        if not search_string:
            logger.debug("No search string provided - returning all threats")
            return threats_data
        
        logger.debug(f"Filtering {len(threats_data)} threat components by search string: '{search_string}'")
        search_lower = search_string.lower()
        filtered_components = []
        total_threats_found = 0
        
        for component in threats_data:
            use_cases = component.get('useCase', {})
            
            if isinstance(use_cases, dict):
                # Single use case
                filtered_threats = []
                threats_list = use_cases.get('threats', [])
                
                for threat in threats_list:
                    # Search in threat name, description, and reference ID
                    threat_name = threat.get('name', '').lower()
                    threat_desc = threat.get('desc', '').lower()
                    threat_ref = threat.get('ref', '').lower()
                    
                    if (search_lower in threat_name or 
                        search_lower in threat_desc or 
                        search_lower in threat_ref):
                        filtered_threats.append(threat)
                        total_threats_found += 1
                
                # If we found matching threats, create a new component with filtered threats
                if filtered_threats:
                    new_component = component.copy()
                    new_use_case = use_cases.copy()
                    new_use_case['threats'] = filtered_threats
                    new_component['useCase'] = new_use_case
                    filtered_components.append(new_component)
                    
            elif isinstance(use_cases, list):
                # Multiple use cases
                filtered_use_cases = []
                
                for use_case in use_cases:
                    filtered_threats = []
                    threats_list = use_case.get('threats', [])
                    
                    for threat in threats_list:
                        # Search in threat name, description, and reference ID
                        threat_name = threat.get('name', '').lower()
                        threat_desc = threat.get('desc', '').lower()
                        threat_ref = threat.get('ref', '').lower()
                        
                        if (search_lower in threat_name or 
                            search_lower in threat_desc or 
                            search_lower in threat_ref):
                            filtered_threats.append(threat)
                            total_threats_found += 1
                    
                    # If we found matching threats, add this use case
                    if filtered_threats:
                        new_use_case = use_case.copy()
                        new_use_case['threats'] = filtered_threats
                        filtered_use_cases.append(new_use_case)
                
                # If we found matching use cases, create a new component
                if filtered_use_cases:
                    new_component = component.copy()
                    new_component['useCase'] = filtered_use_cases
                    filtered_components.append(new_component)
        
        logger.debug(f"Search filtering completed: {len(filtered_components)} components with {total_threats_found} matching threats")
        return filtered_components
