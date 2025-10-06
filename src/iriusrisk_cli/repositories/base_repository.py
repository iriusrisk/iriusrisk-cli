"""Base repository class providing common data access patterns."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..utils.error_handling import handle_api_error, IriusRiskError


class BaseRepository(ABC):
    """Abstract base class for all repositories.
    
    Provides common data access patterns and error handling.
    All repositories should inherit from this class to ensure
    consistent behavior and testability.
    """
    
    def __init__(self, api_client=None):
        """Initialize the repository with an API client.
        
        Args:
            api_client: API client instance for data access
        """
        if api_client is None:
            raise ValueError(f"{self.__class__.__name__} requires an api_client instance")
        self.api_client = api_client
    
    def _handle_error(self, error: Exception, operation: str) -> None:
        """Handle API errors consistently across all repositories.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            
        Raises:
            IriusRiskError: Wrapped error with context
        """
        if isinstance(error, IriusRiskError):
            raise error
        raise handle_api_error(error, operation)
    
    def _extract_items_from_response(self, response: Any) -> List[Dict[str, Any]]:
        """Extract items from API response, handling different formats.
        
        Args:
            response: API response (could be list or HAL JSON)
            
        Returns:
            List of items from the response
        """
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return response.get('_embedded', {}).get('items', [])
        else:
            return []
    
    def _extract_page_info(self, response: Any) -> Dict[str, Any]:
        """Extract pagination info from API response.
        
        Args:
            response: API response
            
        Returns:
            Dictionary containing pagination information
        """
        if isinstance(response, dict):
            return response.get('page', {})
        else:
            return {}
    
    @abstractmethod
    def get_by_id(self, entity_id: str, **kwargs) -> Dict[str, Any]:
        """Get a single entity by ID.
        
        Args:
            entity_id: ID of the entity to retrieve
            **kwargs: Additional parameters specific to the repository
            
        Returns:
            Entity data dictionary
            
        Raises:
            IriusRiskError: If entity not found or API request fails
        """
        pass
    
    @abstractmethod
    def list_all(self, **kwargs) -> Dict[str, Any]:
        """List all entities with optional filtering.
        
        Args:
            **kwargs: Filtering and pagination parameters
            
        Returns:
            Dictionary containing entities and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        pass
