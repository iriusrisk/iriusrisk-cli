"""HTTP authentication handling for MCP server.

This module provides utilities for extracting and validating
IriusRisk API credentials from HTTP requests.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails or credentials are missing."""
    pass


def extract_credentials_from_request(request) -> Tuple[str, str]:
    """Extract IriusRisk credentials from HTTP request headers.
    
    Args:
        request: HTTP request object (Starlette Request or similar)
        
    Returns:
        Tuple of (api_key, hostname)
        
    Raises:
        AuthenticationError: If required headers are missing or invalid
    """
    if not request:
        raise AuthenticationError("No request context available")
    
    # Extract headers
    api_key = request.headers.get("X-IriusRisk-API-Key")
    hostname = request.headers.get("X-IriusRisk-Hostname")
    
    # Validate presence
    if not api_key:
        logger.error("Missing X-IriusRisk-API-Key header in request")
        raise AuthenticationError("Missing required header: X-IriusRisk-API-Key")
    
    if not hostname:
        logger.error("Missing X-IriusRisk-Hostname header in request")
        raise AuthenticationError("Missing required header: X-IriusRisk-Hostname")
    
    # Validate format
    api_key = api_key.strip()
    hostname = hostname.strip()
    
    if not api_key:
        raise AuthenticationError("X-IriusRisk-API-Key header is empty")
    
    if not hostname:
        raise AuthenticationError("X-IriusRisk-Hostname header is empty")
    
    if not hostname.startswith(("http://", "https://")):
        raise AuthenticationError(
            "X-IriusRisk-Hostname must be a complete URL (e.g., https://example.iriusrisk.com)"
        )
    
    logger.debug(f"Successfully extracted credentials for hostname: {hostname}")
    return api_key, hostname


def create_api_client_from_request(request):
    """Create a request-scoped IriusRisk API client from HTTP request.
    
    This function extracts credentials from the request headers and
    creates a new API client instance for this specific request.
    
    Args:
        request: HTTP request object
        
    Returns:
        IriusRiskApiClient instance configured with request credentials
        
    Raises:
        AuthenticationError: If authentication fails
    """
    from ..api_client import IriusRiskApiClient
    from ..config import Config
    
    api_key, hostname = extract_credentials_from_request(request)
    
    # Create a temporary config with the request credentials
    config = Config()
    config._api_key = api_key
    config._hostname = hostname
    
    # Create and return API client
    logger.debug("Creating request-scoped API client")
    return IriusRiskApiClient(config)

