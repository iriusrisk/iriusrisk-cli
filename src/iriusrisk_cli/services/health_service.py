"""Health service for handling health-related business logic."""

from ..api.health_client import HealthApiClient


class HealthService:
    """Service for managing health operations."""
    
    def __init__(self, health_client: HealthApiClient):
        """Initialize the health service.
        
        Args:
            health_client: HealthApiClient instance
        """
        if health_client is None:
            raise ValueError("HealthService requires a health_client instance")
        
        self.health_client = health_client
    
    def check_health(self):
        """Check the health status of IriusRisk.
        
        Returns:
            dict: Health status information
        """
        return self.health_client.get_health()
    
    def get_instance_info(self):
        """Get instance information from IriusRisk.
        
        Returns:
            dict: Instance information
        """
        return self.health_client.get_info()
