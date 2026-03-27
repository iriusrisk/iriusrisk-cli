"""Issue tracker API client for IriusRisk API."""

from typing import Dict, Any, Optional

from .base_client import BaseApiClient
from ..config import Config


class IssueTrackerApiClient(BaseApiClient):
    """API client for issue tracker profile operations."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the issue tracker API client.

        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)

    def get_issue_tracker_profiles(self, page: int = 0, size: int = 9999) -> Dict[str, Any]:
        """Get all available issue tracker profiles.

        Args:
            page: Page number (0-based)
            size: Number of profiles per page

        Returns:
            Issue tracker profiles response with _embedded.items containing the profiles
        """
        params = {
            'page': page,
            'size': size
        }
        return self._make_request('GET', '/issue-tracker-profiles/summary', params=params)

    def get_project_issue_trackers(self, project_id: str, page: int = 0, size: int = 9999) -> Dict[str, Any]:
        """Get issue trackers configured for a specific project.

        Args:
            project_id: Project UUID
            page: Page number (0-based)
            size: Number of issue trackers per page

        Returns:
            Project issue trackers response with _embedded.items containing the trackers
        """
        params = {
            'page': page,
            'size': size
        }
        return self._make_request('GET', f'/projects/{project_id}/issue-trackers/summary', params=params)
