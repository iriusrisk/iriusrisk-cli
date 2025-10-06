"""Countermeasure repository for countermeasure data access."""

import logging
from typing import Optional, Dict, List, Any

from .base_repository import BaseRepository
from ..utils.lookup import find_countermeasure_by_id
from ..utils.error_handling import IriusRiskError

logger = logging.getLogger(__name__)


class CountermeasureRepository(BaseRepository):
    """Repository for countermeasure data access operations."""
    
    def get_by_id(self, countermeasure_id: str, project_id: str) -> Dict[str, Any]:
        """Get a countermeasure by ID within a project.
        
        Args:
            countermeasure_id: Countermeasure ID
            project_id: Project UUID
            
        Returns:
            Countermeasure data dictionary
            
        Raises:
            IriusRiskError: If countermeasure not found or API request fails
        """
        logger.debug(f"Retrieving countermeasure '{countermeasure_id}' from project '{project_id}'")
        
        try:
            # Get all countermeasures and find the specific one (since individual countermeasure API doesn't work)
            logger.debug(f"Fetching all countermeasures from project '{project_id}' to find specific countermeasure")
            response = self.api_client.get_countermeasures(
                project_id=project_id,
                page=0,
                size=1000
            )
            
            # Handle different response formats
            all_countermeasures_data = self._extract_items_from_response(response)
            logger.debug(f"Retrieved {len(all_countermeasures_data)} countermeasures from API")
            
            # Find the specific countermeasure
            logger.debug(f"Searching for countermeasure '{countermeasure_id}' in retrieved data")
            countermeasure_data = find_countermeasure_by_id(all_countermeasures_data, countermeasure_id)
            
            if not countermeasure_data:
                logger.warning(f"Countermeasure '{countermeasure_id}' not found in project '{project_id}'")
                raise IriusRiskError(f"Countermeasure '{countermeasure_id}' not found")
            
            logger.debug(f"Successfully found countermeasure '{countermeasure_id}': {countermeasure_data.get('name', 'Unknown')}")
            return countermeasure_data
            
        except IriusRiskError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve countermeasure '{countermeasure_id}' from project '{project_id}': {e}")
            self._handle_error(e, f"retrieving countermeasure '{countermeasure_id}' from project '{project_id}'")
    
    def list_all(self, project_id: str, page: int = 0, size: int = 20,
                 risk_level: Optional[str] = None, status: Optional[str] = None,
                 custom_filter: Optional[str] = None) -> Dict[str, Any]:
        """List countermeasures from a project with filtering options.
        
        Args:
            project_id: Project UUID
            page: Page number (0-based)
            size: Number of countermeasures per page
            risk_level: Filter by risk level (HIGH, MEDIUM, LOW)
            status: Filter by countermeasure status
            custom_filter: Custom filter expression
            
        Returns:
            Dictionary containing countermeasures data and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Listing countermeasures from project '{project_id}' - page: {page}, size: {size}")
        logger.debug(f"Filters - risk_level: {risk_level}, status: {status}")
        
        try:
            # Build filter expression
            filter_expr = custom_filter
            if not filter_expr:
                logger.debug("Building filter expression from parameters")
                filter_expr = self._build_countermeasure_filter_expression(
                    risk_level=risk_level,
                    status=status
                )
            
            if filter_expr:
                logger.debug(f"Using filter expression: {filter_expr}")
            else:
                logger.debug("No filters applied - retrieving all countermeasures")
            
            # Make API request
            logger.debug(f"Making API request for countermeasures with page={page}, size={size}")
            response = self.api_client.get_countermeasures(
                project_id=project_id,
                page=page,
                size=size,
                filter_expression=filter_expr
            )
            
            # Handle different response formats
            countermeasures_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(countermeasures_data)} countermeasures")
            logger.debug(f"Page info: {page_info}")
            
            return {
                'countermeasures': countermeasures_data,
                'page_info': page_info,
                'full_response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve countermeasures from project '{project_id}': {e}")
            self._handle_error(e, f"retrieving countermeasures from project '{project_id}'")
    
    def search(self, project_id: str, search_string: str) -> Dict[str, Any]:
        """Search countermeasures within a project.
        
        Args:
            project_id: Project UUID
            search_string: String to search for in countermeasure names, descriptions, etc.
            
        Returns:
            Dictionary containing search results and pagination info
            
        Raises:
            IriusRiskError: If search fails
        """
        logger.debug(f"Searching countermeasures in project '{project_id}' for: '{search_string}'")
        
        try:
            # Make API request (using V2 API)
            logger.debug("Fetching all countermeasures for client-side search filtering")
            response = self.api_client.get_countermeasures(
                project_id=project_id,
                page=0,  # Get all countermeasures for client-side filtering
                size=1000  # Large size to get all countermeasures
            )
            
            # Handle different response formats
            all_countermeasures_data = self._extract_items_from_response(response)
            page_info = self._extract_page_info(response)
            
            logger.debug(f"Retrieved {len(all_countermeasures_data)} countermeasures for search")
            
            if not all_countermeasures_data:
                logger.debug("No countermeasures found in project - returning empty results")
                return {
                    'countermeasures': [],
                    'page_info': {},
                    'full_response': response,
                    'search_string': search_string
                }
            
            # Apply client-side filtering for search
            logger.debug(f"Applying client-side search filter for '{search_string}'")
            countermeasures_data = self._filter_countermeasures_by_search(all_countermeasures_data, search_string)
            
            logger.debug(f"Search returned {len(countermeasures_data)} matching countermeasures")
            
            return {
                'countermeasures': countermeasures_data,
                'page_info': page_info,
                'full_response': response,
                'search_string': search_string
            }
            
        except Exception as e:
            logger.error(f"Failed to search countermeasures for '{search_string}' in project '{project_id}': {e}")
            self._handle_error(e, f"searching countermeasures for '{search_string}' in project '{project_id}'")
    
    def update_status(self, countermeasure_id: str, status: str,
                     reason: Optional[str] = None,
                     comment: Optional[str] = None) -> Dict[str, Any]:
        """Update the status of a countermeasure.
        
        Args:
            countermeasure_id: Countermeasure UUID
            status: New status for the countermeasure
            reason: Reason for the status change
            comment: Detailed comment with implementation details
            
        Returns:
            Dictionary containing update result
            
        Raises:
            IriusRiskError: If update fails
        """
        logger.debug(f"Updating countermeasure '{countermeasure_id}' to status '{status}'")
        logger.debug(f"Reason: {reason}, Comment provided: {bool(comment)}")
        
        try:
            # Update countermeasure state
            logger.debug(f"Making API call to update countermeasure state")
            response = self.api_client.update_countermeasure_state(
                countermeasure_id=countermeasure_id,
                state_transition=status.lower(),
                reason=reason,
                comment=comment
            )
            
            logger.debug(f"Countermeasure state update successful")
            
            result = {
                'countermeasure_id': countermeasure_id,
                'status': status,
                'reason': reason,
                'comment_created': False,
                'response': response
            }
            
            # Create separate comment if provided (countermeasure state API doesn't support comments)
            if comment:
                logger.debug(f"Creating separate comment for countermeasure '{countermeasure_id}'")
                try:
                    self.api_client.create_countermeasure_comment(
                        countermeasure_id=countermeasure_id,
                        comment=comment
                    )
                    result['comment_created'] = True
                    logger.debug(f"Comment created successfully")
                except Exception as comment_error:
                    logger.warning(f"Failed to create comment: {comment_error}")
                    result['comment_error'] = str(comment_error)
            
            logger.debug(f"Countermeasure update completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update countermeasure '{countermeasure_id}' to status '{status}': {e}")
            self._handle_error(e, f"updating countermeasure '{countermeasure_id}' to status '{status}'")
    
    def create_issue(self, project_id: str, countermeasure_id: str,
                    issue_tracker_id: str) -> Dict[str, Any]:
        """Create an issue in the configured issue tracker for a countermeasure.
        
        Args:
            project_id: Project UUID
            countermeasure_id: Countermeasure UUID
            issue_tracker_id: Issue tracker ID
            
        Returns:
            Dictionary containing issue creation result
            
        Raises:
            IriusRiskError: If issue creation fails
        """
        logger.debug(f"Creating issue for countermeasure '{countermeasure_id}' in project '{project_id}'")
        logger.debug(f"Using issue tracker: {issue_tracker_id}")
        
        try:
            result = self.api_client.create_countermeasure_issue(
                project_id=project_id,
                countermeasure_id=countermeasure_id,
                issue_tracker_id=issue_tracker_id
            )
            logger.debug(f"Issue created successfully for countermeasure '{countermeasure_id}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create issue for countermeasure '{countermeasure_id}': {e}")
            self._handle_error(e, f"creating issue for countermeasure '{countermeasure_id}'")
    
    def get_issue_tracker_profiles(self) -> Dict[str, Any]:
        """Get available issue tracker profiles.
        
        Returns:
            Dictionary containing issue tracker profiles
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug("Retrieving issue tracker profiles")
        
        try:
            response = self.api_client.get_issue_tracker_profiles()
            profiles_data = self._extract_items_from_response(response)
            
            logger.debug(f"Retrieved {len(profiles_data)} issue tracker profiles")
            
            return {
                'profiles': profiles_data,
                'full_response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve issue tracker profiles: {e}")
            self._handle_error(e, "retrieving issue tracker profiles")
    
    def find_countermeasure_by_reference_or_uuid(self, project_id: str, 
                                               countermeasure_id: str) -> Optional[Dict[str, Any]]:
        """Find a countermeasure by reference ID or UUID.
        
        Args:
            project_id: Project UUID
            countermeasure_id: Countermeasure reference ID or UUID
            
        Returns:
            Countermeasure data or None if not found
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Finding countermeasure '{countermeasure_id}' by reference ID or UUID in project '{project_id}'")
        
        try:
            response = self.api_client.get_countermeasures(
                project_id=project_id,
                page=0,
                size=1000
            )
            
            all_countermeasures_data = self._extract_items_from_response(response)
            logger.debug(f"Retrieved {len(all_countermeasures_data)} countermeasures for search")
            
            # Find the countermeasure by reference ID or UUID
            for cm in all_countermeasures_data:
                if (cm.get('referenceId') == countermeasure_id or 
                    cm.get('id') == countermeasure_id):
                    logger.debug(f"Found countermeasure '{countermeasure_id}': {cm.get('name', 'Unknown')}")
                    return cm
            
            logger.debug(f"Countermeasure '{countermeasure_id}' not found in project '{project_id}'")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find countermeasure '{countermeasure_id}' in project '{project_id}': {e}")
            self._handle_error(e, f"finding countermeasure '{countermeasure_id}' in project '{project_id}'")
    
    def _build_countermeasure_filter_expression(self, search_string: Optional[str] = None,
                                              risk_level: Optional[str] = None,
                                              status: Optional[str] = None) -> Optional[str]:
        """Build a filter expression for countermeasure API based on provided filters."""
        logger.debug("Building countermeasure filter expression from parameters")
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
        logger.debug(f"Built complete countermeasure filter expression: {result}")
        return result
    
    def _filter_countermeasures_by_search(self, countermeasures_data: List[Dict], search_string: str) -> List[Dict]:
        """Filter countermeasures by search string using client-side filtering."""
        if not search_string:
            logger.debug("No search string provided - returning all countermeasures")
            return countermeasures_data
        
        logger.debug(f"Filtering {len(countermeasures_data)} countermeasures by search string: '{search_string}'")
        search_lower = search_string.lower()
        filtered_countermeasures = []
        
        for countermeasure in countermeasures_data:
            # Search in countermeasure name, description, and reference ID
            countermeasure_name = countermeasure.get('name', '').lower()
            countermeasure_desc = countermeasure.get('desc', '').lower()
            countermeasure_ref = countermeasure.get('ref', '').lower()
            
            if (search_lower in countermeasure_name or 
                search_lower in countermeasure_desc or 
                search_lower in countermeasure_ref):
                filtered_countermeasures.append(countermeasure)
        
        logger.debug(f"Search filtering completed: {len(filtered_countermeasures)} matching countermeasures")
        return filtered_countermeasures
