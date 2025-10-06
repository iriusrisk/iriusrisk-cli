"""Health API client for IriusRisk CLI."""

from .base_client import BaseApiClient


class HealthApiClient(BaseApiClient):
    """API client for health-related endpoints."""
    
    def get_health(self):
        """Get health status from IriusRisk.
        
        Returns:
            dict: Health status response
        """
        return self._make_request('GET', '/health')
    
    def get_info(self):
        """Get instance info from IriusRisk.
        
        Returns:
            dict: Instance info response
        """
        return self._make_request('GET', '/info')
