"""Countermeasure service for handling countermeasure-related business logic."""

import logging
from typing import Optional, Dict, List, Any

from ..repositories.countermeasure_repository import CountermeasureRepository
from ..utils.project_resolution import resolve_project_id_to_uuid
from ..utils.error_handling import handle_api_error, IriusRiskError

logger = logging.getLogger(__name__)


class CountermeasureService:
    """Service for managing countermeasure operations."""
    
    def __init__(self, countermeasure_repository=None):
        """Initialize the countermeasure service.
        
        Args:
            countermeasure_repository: CountermeasureRepository instance (required for dependency injection)
        """
        if countermeasure_repository is None:
            raise ValueError("CountermeasureService requires a countermeasure_repository instance")
        self.countermeasure_repository = countermeasure_repository
    
    def list_countermeasures(self, project_id: str, page: int = 0, size: int = 20,
                           risk_level: Optional[str] = None, status: Optional[str] = None,
                           custom_filter: Optional[str] = None) -> Dict[str, Any]:
        """List countermeasures from a project with filtering options.
        
        Args:
            project_id: Project UUID or reference ID
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
        logger.debug(f"Listing countermeasures for project '{project_id}' with filters: "
                    f"page={page}, size={size}, risk_level={risk_level}, status={status}")
        
        if custom_filter:
            logger.debug(f"Using custom filter: {custom_filter}")
        
        # Resolve project ID to UUID for V2 API
        logger.debug(f"Resolving project ID to UUID: {project_id}")
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved to UUID: {final_project_id}")
        
        result = self.countermeasure_repository.list_all(
            project_id=final_project_id,
            page=page,
            size=size,
            risk_level=risk_level,
            status=status,
            custom_filter=custom_filter
        )
        
        countermeasures_count = len(result.get('countermeasures', []))
        total_count = result.get('totalElements', 0)
        logger.info(f"Retrieved {countermeasures_count} countermeasures from project (page {page + 1}, {total_count} total)")
        
        return result
    
    def get_countermeasure(self, project_id: str, countermeasure_id: str) -> Dict[str, Any]:
        """Get a specific countermeasure by ID.
        
        Args:
            project_id: Project UUID or reference ID
            countermeasure_id: Countermeasure ID
            
        Returns:
            Countermeasure data dictionary
            
        Raises:
            IriusRiskError: If countermeasure not found or API request fails
        """
        logger.debug(f"Retrieving countermeasure '{countermeasure_id}' from project '{project_id}'")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved project to UUID: {final_project_id}")
        
        result = self.countermeasure_repository.get_by_id(countermeasure_id, final_project_id)
        
        countermeasure_name = result.get('name', 'Unknown')
        countermeasure_state = result.get('state', 'Unknown')
        priority = result.get('priority', {}).get('calculated', 'Unknown') if isinstance(result.get('priority'), dict) else 'Unknown'
        logger.info(f"Retrieved countermeasure '{countermeasure_name}' (ID: {countermeasure_id}, state: {countermeasure_state}, priority: {priority})")
        
        return result
    
    def search_countermeasures(self, project_id: str, search_string: str) -> Dict[str, Any]:
        """Search countermeasures within a project.
        
        Args:
            project_id: Project UUID or reference ID
            search_string: String to search for in countermeasure names, descriptions, etc.
            
        Returns:
            Dictionary containing search results and pagination info
            
        Raises:
            IriusRiskError: If search fails
        """
        logger.debug(f"Searching countermeasures in project '{project_id}' with query: '{search_string}'")
        
        # Resolve project ID to UUID for V2 API
        final_project_id = resolve_project_id_to_uuid(project_id)
        logger.debug(f"Resolved project to UUID: {final_project_id}")
        
        result = self.countermeasure_repository.search(
            project_id=final_project_id,
            search_string=search_string
        )
        
        countermeasures_count = len(result.get('countermeasures', []))
        total_count = result.get('totalElements', 0)
        logger.info(f"Search returned {countermeasures_count} countermeasures ({total_count} total)")
        
        return result
    
    def update_countermeasure_status(self, countermeasure_id: str, status: str,
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
        logger.info(f"Updating countermeasure '{countermeasure_id}' status to '{status}'")
        
        if reason:
            logger.debug(f"Update reason: {reason}")
        if comment:
            logger.debug(f"Update includes comment ({len(comment)} characters)")
        
        # Validate required fields for certain statuses
        if status == 'implemented' and not comment:
            logger.warning("Status 'implemented' typically requires a comment with implementation details")
        
        result = self.countermeasure_repository.update_status(
            countermeasure_id=countermeasure_id,
            status=status,
            reason=reason,
            comment=comment
        )
        
        logger.info(f"Successfully updated countermeasure '{countermeasure_id}' status to '{status}'")
        
        return result
    
    def create_countermeasure_issue(self, project_id: str, countermeasure_id: str,
                                  tracker: Optional[str] = None) -> Dict[str, Any]:
        """Create an issue in the configured issue tracker for a countermeasure.
        
        Args:
            project_id: Project UUID or reference ID
            countermeasure_id: Countermeasure reference ID or UUID
            tracker: Issue tracker name or ID (optional if default configured)
            
        Returns:
            Dictionary containing issue creation result
            
        Raises:
            IriusRiskError: If issue creation fails
        """
        logger.info(f"Creating issue for countermeasure '{countermeasure_id}' in project '{project_id}'")
        
        try:
            # Resolve project ID to UUID for V2 API
            logger.debug(f"Resolving project ID to UUID: {project_id}")
            final_project_id = resolve_project_id_to_uuid(project_id)
            logger.debug(f"Resolved to UUID: {final_project_id}")
            
            # Find the countermeasure by reference ID or UUID
            logger.debug(f"Looking up countermeasure: {countermeasure_id}")
            countermeasure_data = self.countermeasure_repository.find_countermeasure_by_reference_or_uuid(
                project_id=final_project_id,
                countermeasure_id=countermeasure_id
            )
            
            if not countermeasure_data:
                logger.error(f"Countermeasure '{countermeasure_id}' not found in project")
                raise IriusRiskError(f"Countermeasure '{countermeasure_id}' not found in project")
            
            countermeasure_uuid = countermeasure_data.get('id')
            countermeasure_name = countermeasure_data.get('name')
            logger.debug(f"Found countermeasure '{countermeasure_name}' (UUID: {countermeasure_uuid})")
            
            # Check if countermeasure already has an issue
            existing_issue_id = countermeasure_data.get('issueId')
            if existing_issue_id:
                logger.warning(f"Countermeasure '{countermeasure_id}' already has an existing issue: {existing_issue_id}")
                existing_issue_link = countermeasure_data.get('issueLink')
                existing_issue_state = countermeasure_data.get('issueState')
                
                # Determine issue tracker type from the link
                issue_tracker_type = "Unknown"
                if existing_issue_link:
                    if "visualstudio.com" in existing_issue_link:
                        issue_tracker_type = "Azure DevOps"
                    elif "atlassian.net" in existing_issue_link or "jira" in existing_issue_link.lower():
                        issue_tracker_type = "Jira"
                    elif "servicenow" in existing_issue_link.lower():
                        issue_tracker_type = "ServiceNow"
                
                logger.debug(f"Existing issue details: ID={existing_issue_id}, tracker={issue_tracker_type}, state={existing_issue_state}")
                
                raise IriusRiskError(
                    f"Countermeasure '{countermeasure_id}' already has an issue:\n"
                    f"Issue ID: {existing_issue_id}\n"
                    f"Issue Link: {existing_issue_link or 'N/A'}\n"
                    f"Issue State: {existing_issue_state or 'N/A'}\n"
                    f"Issue Tracker: {issue_tracker_type}\n"
                    f"Cannot create a new issue for a countermeasure that already has one."
                )
            
            # Handle issue tracker selection
            issue_tracker_id = None
            issue_tracker_name = None
            
            if tracker:
                logger.debug(f"Resolving specified issue tracker: {tracker}")
                # Get available issue tracker profiles to resolve name/ID
                profiles_response = self.countermeasure_repository.get_issue_tracker_profiles()
                profiles_data = profiles_response.get('profiles', [])
                logger.debug(f"Found {len(profiles_data)} available issue tracker profiles")
                
                # Find the tracker by name or ID
                selected_tracker = None
                for profile in profiles_data:
                    if (profile.get('id') == tracker or 
                        profile.get('name') == tracker):
                        selected_tracker = profile
                        break
                
                if not selected_tracker:
                    available_trackers = [f"{p.get('name')} (ID: {p.get('id')})" for p in profiles_data]
                    logger.error(f"Issue tracker '{tracker}' not found among available profiles")
                    raise IriusRiskError(
                        f"Issue tracker '{tracker}' not found.\n"
                        f"Available issue tracker profiles: {', '.join(available_trackers)}"
                    )
                
                issue_tracker_id = selected_tracker.get('id')
                issue_tracker_name = selected_tracker.get('name')
                logger.debug(f"Selected issue tracker: '{issue_tracker_name}' (ID: {issue_tracker_id})")
            else:
                logger.debug("No issue tracker specified, looking for default configuration")
                # Try to use default issue tracker from project config
                from ..utils.project import get_project_config
                config = get_project_config()
                if config and config.get('default_issue_tracker'):
                    default_tracker = config['default_issue_tracker']
                    issue_tracker_id = default_tracker.get('id')
                    issue_tracker_name = default_tracker.get('name')
                    logger.debug(f"Using default issue tracker: '{issue_tracker_name}' (ID: {issue_tracker_id})")
                else:
                    logger.error("No issue tracker specified and no default configured")
                    raise IriusRiskError(
                        "No issue tracker specified and no default configured. "
                        "Use --tracker to specify an issue tracker or run 'iriusrisk issue-tracker set-default' to configure a default."
                    )
            
            # Create the issue using the correct API
            logger.debug(f"Creating issue via API for countermeasure '{countermeasure_uuid}' using tracker '{issue_tracker_name}'")
            result = self.countermeasure_repository.create_issue(
                project_id=final_project_id,
                countermeasure_id=countermeasure_uuid,
                issue_tracker_id=issue_tracker_id
            )
            
            logger.info(f"Successfully created issue for countermeasure '{countermeasure_name}' using tracker '{issue_tracker_name}'")
            
            return {
                'countermeasure_id': countermeasure_id,
                'countermeasure_name': countermeasure_name,
                'issue_tracker_name': issue_tracker_name,
                'result': result
            }
            
        except IriusRiskError:
            raise
        except Exception as e:
            raise handle_api_error(e, f"creating issue for countermeasure '{countermeasure_id}'")
    



