"""Issue tracker repository for issue tracker profile data access."""

import logging
from typing import Dict, Any

from .base_repository import BaseRepository
from ..utils.error_handling import IriusRiskError

logger = logging.getLogger(__name__)


class IssueTrackerRepository(BaseRepository):
    """Repository for issue tracker profile data access operations."""

    def get_by_id(self, profile_id: str, **kwargs) -> Dict[str, Any]:
        """Not supported — issue tracker profiles are accessed via get_issue_tracker_profiles."""
        raise IriusRiskError(
            "Issue tracker profiles should be accessed through get_issue_tracker_profiles()"
        )

    def list_all(self, **kwargs) -> Dict[str, Any]:
        """List all issue tracker profiles."""
        return self.get_issue_tracker_profiles()

    def get_issue_tracker_profiles(self) -> Dict[str, Any]:
        """Get all available issue tracker profiles.

        Returns:
            Dictionary with 'profiles' list and 'full_response'

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
            self._handle_error(e, "retrieving issue tracker profiles")

    def get_project_issue_trackers(self, project_id: str) -> Dict[str, Any]:
        """Get issue trackers configured for a specific project.

        Args:
            project_id: Project UUID

        Returns:
            Dictionary with 'trackers' list and 'full_response'

        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving issue trackers for project '{project_id}'")

        try:
            response = self.api_client.get_project_issue_trackers(project_id)
            trackers_data = self._extract_items_from_response(response)

            logger.debug(f"Retrieved {len(trackers_data)} issue trackers for project '{project_id}'")

            return {
                'trackers': trackers_data,
                'full_response': response
            }

        except Exception as e:
            self._handle_error(e, f"retrieving issue trackers for project '{project_id}'")
