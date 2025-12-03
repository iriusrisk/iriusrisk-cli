"""OAuth authentication bridge for MCP HTTP server.

This module provides a HACKY workaround for using OAuth with IriusRisk's API-key-based
authentication. It validates OAuth tokens and maps users to their IriusRisk credentials
using a static configuration file.

⚠️ WARNING: This is NOT production-ready OAuth. It's a bridge/hack to enable testing
with OAuth-requiring clients (ChatGPT, etc.) until IriusRisk backend supports OAuth natively.

Security concerns:
- Static user mappings in plaintext file
- API keys stored in config file
- No credential rotation
- Manual user management
"""

import logging
import json
import requests
from typing import Dict, Tuple, Optional
from pathlib import Path
import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class OAuthConfig:
    """OAuth configuration loaded from JSON file."""
    
    def __init__(self, config_file: str):
        """Load OAuth configuration from file.
        
        Args:
            config_file: Path to oauth_mapping.json
        """
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"OAuth config file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.oauth_settings = self.config.get('oauth', {})
        self.user_mappings = self.config.get('user_mappings', {})
        
        # Validate required fields
        if not self.oauth_settings:
            raise ValueError("OAuth config missing 'oauth' section")
        if not self.user_mappings:
            raise ValueError("OAuth config missing 'user_mappings' section")
        
        logger.info(f"Loaded OAuth config with {len(self.user_mappings)} user mappings")
    
    def get_provider_info(self) -> Dict:
        """Get OAuth provider configuration."""
        return self.oauth_settings.get('provider', {})
    
    def get_user_mapping(self, user_identifier: str) -> Optional[Dict]:
        """Get IriusRisk credentials for an OAuth user.
        
        Args:
            user_identifier: User email or ID from OAuth token
        
        Returns:
            Dict with iriusrisk_api_key and iriusrisk_hostname, or None
        """
        return self.user_mappings.get(user_identifier)


def validate_oauth_token_userinfo(token: str, oauth_config: OAuthConfig) -> Dict:
    """Validate OAuth token by calling userinfo endpoint.
    
    This method validates the token by calling the OAuth provider's userinfo endpoint.
    Works with any OAuth token format (not just JWT). This is what ChatGPT expects.
    
    Args:
        token: OAuth bearer token (any format)
        oauth_config: OAuth configuration
    
    Returns:
        User info from provider (includes user identifier)
    
    Raises:
        Exception: If token is invalid or userinfo call fails
    """
    provider = oauth_config.get_provider_info()
    
    # Get userinfo endpoint
    userinfo_url = provider.get('userinfo_url')
    if not userinfo_url:
        # Try discovery
        discovery_url = provider.get('discovery_url')
        if discovery_url:
            logger.info(f"Fetching userinfo URL from discovery: {discovery_url}")
            try:
                discovery = requests.get(discovery_url).json()
                userinfo_url = discovery.get('userinfo_endpoint')
            except Exception as e:
                logger.error(f"Failed to fetch discovery: {e}")
    
    if not userinfo_url:
        raise ValueError("No userinfo_url found in config or discovery")
    
    # Call userinfo endpoint with token
    logger.debug(f"Validating token via userinfo endpoint: {userinfo_url}")
    logger.debug(f"Token preview: {token[:50]}...")
    
    try:
        response = requests.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Log response details before raising error
        if response.status_code != 200:
            logger.error(f"Userinfo endpoint returned {response.status_code}")
            logger.error(f"Response body: {response.text[:200]}")
            logger.error(f"Token might be: expired, for wrong audience, or from different provider")
        
        response.raise_for_status()
        userinfo = response.json()
        
        logger.info(f"Token validated via userinfo for user: {userinfo.get(provider.get('user_claim', 'email'))}")
        return userinfo
    except requests.RequestException as e:
        logger.error(f"Userinfo endpoint call failed: {e}")
        logger.error(f"This usually means the token is not a Google token, is expired, or is for a different OAuth app")
        raise Exception(f"Token validation failed: {e}")


def validate_oauth_token_jwt(token: str, oauth_config: OAuthConfig) -> Dict:
    """Validate OAuth token using JWT validation (stateless, fast).
    
    This method validates the token's signature using the provider's public keys,
    verifies issuer and audience, and extracts user claims.
    Only works with JWT-format tokens.
    
    Args:
        token: OAuth bearer token (must be JWT format)
        oauth_config: OAuth configuration
    
    Returns:
        Decoded token claims (includes user identifier)
    
    Raises:
        jwt.InvalidTokenError: If token is invalid or not JWT format
        Exception: If validation fails
    """
    provider = oauth_config.get_provider_info()
    
    # Check if token looks like a JWT (has 3 parts separated by dots)
    if token.count('.') != 2:
        logger.warning(f"Token doesn't look like JWT (has {token.count('.')} dots, need 2). Falling back to userinfo.")
        return validate_oauth_token_userinfo(token, oauth_config)
    
    # Get JWKS URI (public keys)
    jwks_uri = provider.get('jwks_uri')
    if not jwks_uri:
        # Try discovery
        discovery_url = provider.get('discovery_url')
        if discovery_url:
            logger.info(f"Fetching JWKS URI from discovery: {discovery_url}")
            discovery = requests.get(discovery_url).json()
            jwks_uri = discovery.get('jwks_uri')
    
    if not jwks_uri:
        logger.warning("No jwks_uri found, falling back to userinfo validation")
        return validate_oauth_token_userinfo(token, oauth_config)
    
    # Validate token
    logger.debug(f"Validating JWT token using JWKS: {jwks_uri}")
    try:
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and validate
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            issuer=provider.get('issuer'),
            audience=provider.get('client_id'),
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True
            }
        )
        
        logger.info(f"Token validated successfully for user: {decoded.get(provider.get('user_claim', 'email'))}")
        return decoded
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}. Falling back to userinfo endpoint.")
        return validate_oauth_token_userinfo(token, oauth_config)


def validate_oauth_token_introspection(token: str, oauth_config: OAuthConfig) -> Dict:
    """Validate OAuth token using introspection endpoint (works with all providers).
    
    This method calls the provider's token introspection endpoint to validate
    the token. More flexible but requires network call per request.
    
    Args:
        token: OAuth bearer token
        oauth_config: OAuth configuration
    
    Returns:
        Token introspection response with user info
    
    Raises:
        Exception: If token is invalid or introspection fails
    """
    provider = oauth_config.get_provider_info()
    
    introspection_url = provider.get('token_introspection_url')
    if not introspection_url:
        raise ValueError("No token_introspection_url in config")
    
    # Call introspection endpoint
    logger.debug(f"Validating token via introspection: {introspection_url}")
    response = requests.post(
        introspection_url,
        auth=(provider.get('client_id'), provider.get('client_secret')),
        data={'token': token}
    )
    
    response.raise_for_status()
    token_info = response.json()
    
    if not token_info.get('active'):
        raise Exception("Token is not active")
    
    logger.info(f"Token validated via introspection for user: {token_info.get(provider.get('user_claim', 'email'))}")
    return token_info


def extract_user_from_token_unsafe(token: str, oauth_config: OAuthConfig) -> str:
    """Extract user from token without validation (UNSAFE - for testing only).
    
    Tries to decode JWT token without signature verification.
    If that fails and there's only one user in mappings, uses that user.
    Use only when you trust the source (e.g., ChatGPT already authenticated user).
    
    Args:
        token: OAuth bearer token (any format)
        oauth_config: OAuth configuration
    
    Returns:
        User identifier from token or single mapped user
    """
    provider = oauth_config.get_provider_info()
    user_claim = provider.get('user_claim', 'email')
    
    # Try to decode as JWT without verification
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        user = decoded.get(user_claim)
        if user:
            logger.warning(f"Extracted user '{user}' from token WITHOUT validation (unsafe mode)")
            return user
    except Exception as e:
        logger.debug(f"Token is not decodable as JWT: {e}")
    
    # Fallback for single-user setups: If only one user mapped, use them
    if len(oauth_config.user_mappings) == 1:
        user = list(oauth_config.user_mappings.keys())[0]
        logger.warning(f"⚠️ Using single mapped user '{user}' (token not decodable, single-user mode)")
        return user
    
    # Can't determine user
    raise Exception(
        f"Could not extract user from token. "
        f"Token is not a decodable JWT and there are {len(oauth_config.user_mappings)} mapped users. "
        f"For single-user testing, ensure only one user in user_mappings."
    )


def extract_user_from_oauth_token(token: str, oauth_config: OAuthConfig) -> str:
    """Extract user identifier from OAuth token.
    
    Args:
        token: OAuth bearer token
        oauth_config: OAuth configuration
    
    Returns:
        User identifier (email, user_id, etc.) from token
    
    Raises:
        Exception: If token validation fails
    """
    provider = oauth_config.get_provider_info()
    validation_method = provider.get('validation_method', 'jwt')
    
    # Validate token and get claims
    validation_method = provider.get('validation_method', 'jwt')
    
    # Check for skip_validation flag (for testing with ChatGPT)
    if provider.get('skip_validation', False):
        logger.warning("⚠️ Token validation SKIPPED (skip_validation=true in config)")
        return extract_user_from_token_unsafe(token, oauth_config)
    
    if validation_method == 'jwt':
        claims = validate_oauth_token_jwt(token, oauth_config)
    elif validation_method == 'introspection':
        claims = validate_oauth_token_introspection(token, oauth_config)
    elif validation_method == 'userinfo':
        claims = validate_oauth_token_userinfo(token, oauth_config)
    elif validation_method == 'none':
        logger.warning("⚠️ Token validation DISABLED (validation_method='none')")
        return extract_user_from_token_unsafe(token, oauth_config)
    else:
        raise ValueError(f"Unknown validation method: {validation_method}")
    
    # Extract user identifier
    user_claim = provider.get('user_claim', 'email')
    user_identifier = claims.get(user_claim)
    
    if not user_identifier:
        raise Exception(f"Token missing required claim: {user_claim}")
    
    return user_identifier


def create_api_client_from_oauth_token(token: str, oauth_config: OAuthConfig):
    """Create IriusRisk API client from OAuth token using static mapping.
    
    This is the main entry point for OAuth authentication. It:
    1. Validates the OAuth token
    2. Extracts user identifier
    3. Looks up user in static mapping
    4. Creates API client with mapped credentials
    
    Args:
        token: OAuth bearer token from request
        oauth_config: Loaded OAuth configuration
    
    Returns:
        IriusRiskApiClient instance configured with user's credentials
    
    Raises:
        Exception: If token invalid or user not in mapping
    """
    from ..api_client import IriusRiskApiClient
    from ..config import Config
    
    # Extract user from token
    user_identifier = extract_user_from_oauth_token(token, oauth_config)
    logger.info(f"OAuth user identified: {user_identifier}")
    
    # Look up user in static mapping
    user_mapping = oauth_config.get_user_mapping(user_identifier)
    if not user_mapping:
        logger.error(f"User {user_identifier} not found in OAuth mapping")
        available_users = list(oauth_config.user_mappings.keys())
        raise Exception(
            f"User '{user_identifier}' not authorized. "
            f"User must be added to oauth_mapping.json. "
            f"Configured users: {len(available_users)}"
        )
    
    # Check if user is enabled
    if not user_mapping.get('enabled', True):
        raise Exception(f"User '{user_identifier}' is disabled in OAuth mapping")
    
    # Get IriusRisk credentials from mapping
    api_key = user_mapping.get('iriusrisk_api_key')
    hostname = user_mapping.get('iriusrisk_hostname')
    
    if not api_key or not hostname:
        raise Exception(f"Incomplete IriusRisk credentials for user '{user_identifier}'")
    
    logger.info(f"Mapped OAuth user {user_identifier} to IriusRisk instance: {hostname}")
    
    # Create API client with mapped credentials
    config = Config()
    config._api_key = api_key
    config._hostname = hostname
    
    return IriusRiskApiClient(config)


def extract_oauth_token_from_request(request) -> Optional[str]:
    """Extract OAuth bearer token from HTTP request.
    
    Args:
        request: HTTP request object
    
    Returns:
        OAuth bearer token or None if not present
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header:
        return None
    
    if not auth_header.startswith("Bearer "):
        return None
    
    return auth_header[7:]  # Remove "Bearer " prefix


