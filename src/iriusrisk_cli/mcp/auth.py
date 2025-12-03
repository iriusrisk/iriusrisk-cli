"""HTTP authentication handling for MCP server.

This module provides utilities for extracting and validating
IriusRisk API credentials from HTTP requests.

Supports two authentication modes:
1. Direct API Key (via headers) - Default
2. OAuth Bridge (via Bearer token + static mapping) - Optional
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails or credentials are missing."""
    pass


def get_auth_mode(request) -> str:
    """Determine authentication mode from request headers.
    
    Args:
        request: HTTP request object
    
    Returns:
        'oauth' if Authorization header present, 'api_key' otherwise
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return 'oauth'
    return 'api_key'


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


def create_api_client_from_request(request, oauth_config=None):
    """Create a request-scoped IriusRisk API client from HTTP request.
    
    This function extracts credentials from the request headers and
    creates a new API client instance for this specific request.
    
    Supports two authentication modes:
    1. Direct API Key: Uses X-IriusRisk-API-Key and X-IriusRisk-Hostname headers
    2. OAuth Bridge: Uses Authorization Bearer token + static mapping (if oauth_config provided)
    
    Args:
        request: HTTP request object
        oauth_config: Optional OAuthConfig for OAuth mode
        
    Returns:
        IriusRiskApiClient instance configured with request credentials
        
    Raises:
        AuthenticationError: If authentication fails
    """
    from ..api_client import IriusRiskApiClient
    from ..config import Config
    
    # Determine authentication mode
    auth_mode = get_auth_mode(request)
    
    logger.info(f"Authentication mode detected: {auth_mode}, OAuth config provided: {oauth_config is not None}")
    
    if auth_mode == 'oauth' and oauth_config:
        # OAuth mode - validate token and map to IriusRisk credentials
        logger.info("Using OAuth authentication mode")
        
        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("OAuth mode enabled but no Bearer token found")
        
        token = auth_header[7:]  # Strip "Bearer "
        
        # First, check if this is one of our own tokens (from OAuth flow)
        from .oauth_server import get_token_user
        user_email = get_token_user(token)
        
        if user_email:
            # Token is valid and we have the user email
            logger.info(f"Token validated for user: {user_email}")
            
            # Get IriusRisk credentials from mapping
            user_mapping = oauth_config.user_mappings.get(user_email)
            if not user_mapping:
                raise AuthenticationError(f"User {user_email} not mapped to IriusRisk credentials")
            
            if not user_mapping.get("enabled", True):
                raise AuthenticationError(f"User {user_email} is disabled")
            
            # Create API client with mapped credentials
            from ..api_client import IriusRiskApiClient
            from ..config import Config
            
            config = Config()
            config._api_key = user_mapping["iriusrisk_api_key"]
            config._hostname = user_mapping["iriusrisk_hostname"]
            
            api_client = IriusRiskApiClient(config)
            logger.info("OAuth authentication successful")
            return api_client
        
        # If not our token, try the old OAuth validation path (for ChatGPT, etc.)
        try:
            from .oauth import create_api_client_from_oauth_token
            api_client = create_api_client_from_oauth_token(token, oauth_config)
            logger.info("OAuth authentication successful (external token)")
            return api_client
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            raise AuthenticationError(f"OAuth authentication failed: {e}")
    
    else:
        # Direct API key mode (default)
        logger.debug("Using direct API key authentication mode")
        
        # Even if OAuth is configured, still allow direct API key mode
        try:
            api_key, hostname = extract_credentials_from_request(request)
        except AuthenticationError as e:
            # If OAuth is enabled but this request has neither OAuth nor API keys
            if oauth_config:
                logger.error("OAuth mode enabled but request has neither Bearer token nor API key headers")
                raise AuthenticationError(
                    "Authentication required. Provide either: "
                    "(1) Authorization: Bearer <token> for OAuth, or "
                    "(2) X-IriusRisk-API-Key + X-IriusRisk-Hostname headers for direct access"
                )
            else:
                raise
        
        # Create a temporary config with the request credentials
        config = Config()
        config._api_key = api_key
        config._hostname = hostname
        
        # Create and return API client
        logger.debug(f"Creating request-scoped API client for hostname: {hostname}")
        api_client = IriusRiskApiClient(config)
        logger.debug(f"API client created successfully: {api_client is not None}")
        logger.debug(f"API client base_url: {api_client.base_url}")
        
        return api_client

