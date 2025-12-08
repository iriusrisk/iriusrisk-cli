"""
OAuth 2.0 Server for IriusRisk MCP.

Implements a full OAuth 2.0 server that:
1. Handles OAuth discovery (RFC 8414, RFC 9728)
2. Dynamic client registration (RFC 7591)
3. Authorization code flow with PKCE
4. Issues its own tokens
5. Maps authenticated users to IriusRisk API keys via oauth_mapping.json

Based on the working CoffeeMCP implementation.
"""
from __future__ import annotations
import secrets
import hashlib
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from urllib.parse import urlencode, quote
import httpx

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, RedirectResponse, HTMLResponse

logger = logging.getLogger(__name__)

# Token/session expiry
AUTH_CODE_EXPIRES_SECONDS = 600  # 10 minutes
ACCESS_TOKEN_EXPIRES_SECONDS = 31536000  # 1 year


class OAuthServer:
    """
    OAuth 2.0 server for IriusRisk MCP.
    
    Handles the full OAuth flow, issuing its own tokens and mapping
    authenticated users to IriusRisk API credentials.
    """
    
    def __init__(self, base_url: str, oauth_config: Dict[str, Any]):
        """
        Initialize OAuth server.
        
        Args:
            base_url: Public base URL (e.g., https://example.com/test)
            oauth_config: Loaded oauth_mapping.json config
        """
        self.base_url = base_url.rstrip('/')
        self.oauth_config = oauth_config
        self.provider_config = oauth_config.get('oauth', {}).get('provider', {})
        self.user_mappings = oauth_config.get('user_mappings', {})
        
        # In-memory storage (use Redis/DB for production)
        self.clients: Dict[str, Dict[str, Any]] = {}  # client_id -> client data
        self.auth_codes: Dict[str, Dict[str, Any]] = {}  # code -> auth data
        self.tokens: Dict[str, Dict[str, Any]] = {}  # token -> token data
        self.sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session data
        
        logger.info(f"OAuth server initialized with base_url: {self.base_url}")
        logger.info(f"Provider: {self.provider_config.get('name', 'unknown')}")
        logger.info(f"User mappings: {len(self.user_mappings)}")
    
    def _generate_session_id(self) -> str:
        return secrets.token_urlsafe(32)
    
    def _generate_client_id(self) -> str:
        return f"mcp_{secrets.token_urlsafe(16)}"
    
    def _generate_auth_code(self) -> str:
        return secrets.token_urlsafe(32)
    
    def _generate_access_token(self) -> str:
        return secrets.token_urlsafe(48)
    
    def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
        """Verify PKCE code challenge using timing-safe comparison."""
        if method == "S256":
            hash_digest = hashlib.sha256(code_verifier.encode()).digest()
            computed = base64.urlsafe_b64encode(hash_digest).decode().rstrip("=")
            return secrets.compare_digest(computed, code_challenge)
        elif method == "plain":
            return secrets.compare_digest(code_verifier, code_challenge)
        return False
    
    def get_user_iriusrisk_credentials(self, email: str) -> Optional[Dict[str, str]]:
        """
        Look up IriusRisk credentials for an authenticated user.
        
        Args:
            email: User's email address from OAuth
            
        Returns:
            Dict with 'api_key' and 'hostname' if user is mapped, None otherwise
        """
        mapping = self.user_mappings.get(email)
        if not mapping:
            logger.warning(f"No IriusRisk mapping for user: {email}")
            return None
        
        if not mapping.get('enabled', True):
            logger.warning(f"User mapping disabled for: {email}")
            return None
        
        return {
            'api_key': mapping.get('iriusrisk_api_key'),
            'hostname': mapping.get('iriusrisk_hostname')
        }
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate an access token and return user info + IriusRisk credentials.
        
        Returns:
            Dict with 'email', 'api_key', 'hostname' if valid, None otherwise
        """
        token_data = self.tokens.get(token)
        if not token_data:
            logger.debug(f"Token not found: {token[:20]}...")
            return None
        
        # Check expiry
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.utcnow() > expires_at:
            logger.debug(f"Token expired for user: {token_data.get('email')}")
            del self.tokens[token]
            return None
        
        email = token_data.get('email')
        credentials = self.get_user_iriusrisk_credentials(email)
        
        if not credentials:
            return None
        
        return {
            'email': email,
            'api_key': credentials['api_key'],
            'hostname': credentials['hostname']
        }
    
    # =========================================================================
    # OAuth Discovery Endpoints
    # =========================================================================
    
    async def authorization_server_metadata(self, request: Request) -> JSONResponse:
        """
        OAuth 2.0 Authorization Server Metadata (RFC 8414).
        
        GET /.well-known/oauth-authorization-server
        """
        return JSONResponse(self._get_oauth_metadata(), headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        })
    
    async def openid_configuration(self, request: Request) -> JSONResponse:
        """
        OpenID Connect Discovery (for clients that expect OIDC).
        
        GET /.well-known/openid-configuration
        
        Returns OAuth metadata with additional OIDC fields.
        """
        metadata = self._get_oauth_metadata()
        # Add OIDC-specific fields
        metadata.update({
            "userinfo_endpoint": f"{self.base_url}/oauth/userinfo",
            "scopes_supported": ["openid", "email", "profile"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
        })
        return JSONResponse(metadata, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        })
    
    def _get_oauth_metadata(self) -> dict:
        """Get base OAuth server metadata."""
        return {
            "issuer": self.base_url,
            "authorization_endpoint": f"{self.base_url}/oauth/authorize",
            "token_endpoint": f"{self.base_url}/oauth/token",
            "registration_endpoint": f"{self.base_url}/oauth/register",
            "grant_types_supported": ["authorization_code"],
            "response_types_supported": ["code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"]
        }
    
    async def protected_resource_metadata(self, request: Request) -> JSONResponse:
        """
        OAuth 2.0 Protected Resource Metadata (RFC 9728).
        
        GET /.well-known/oauth-protected-resource
        """
        return JSONResponse({
            "resource": f"{self.base_url}/mcp",
            "authorization_servers": [self.base_url]
        }, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        })
    
    # =========================================================================
    # Dynamic Client Registration (RFC 7591)
    # =========================================================================
    
    async def register_client(self, request: Request) -> JSONResponse:
        """
        OAuth 2.0 Dynamic Client Registration.
        
        POST /oauth/register
        """
        try:
            body = await request.json()
        except Exception:
            body = {}
        
        client_id = self._generate_client_id()
        issued_at = int(datetime.utcnow().timestamp())
        
        # Store client
        self.clients[client_id] = {
            "client_id": client_id,
            "client_name": body.get("client_name", "MCP Client"),
            "redirect_uris": body.get("redirect_uris", []),
            "grant_types": body.get("grant_types", ["authorization_code"]),
            "token_endpoint_auth_method": "none",
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Registered OAuth client: {client_id}")
        
        return JSONResponse({
            "client_id": client_id,
            "client_id_issued_at": issued_at,
            "client_secret_expires_at": 0,
            "redirect_uris": body.get("redirect_uris"),
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "client_name": body.get("client_name", "MCP Client")
        }, headers={
            "Access-Control-Allow-Origin": "*"
        })
    
    # =========================================================================
    # Authorization Code Flow
    # =========================================================================
    
    async def authorize(self, request: Request) -> Response:
        """
        OAuth 2.0 Authorization Endpoint.
        
        GET /oauth/authorize
        
        Redirects to Google for authentication, then issues our own auth code.
        """
        params = dict(request.query_params)
        
        response_type = params.get("response_type")
        client_id = params.get("client_id")
        redirect_uri = params.get("redirect_uri")
        state = params.get("state")
        code_challenge = params.get("code_challenge")
        code_challenge_method = params.get("code_challenge_method", "S256")
        
        # Validate
        if response_type != "code":
            return JSONResponse({"error": "unsupported_response_type"}, status_code=400)
        
        # Store auth request in session for callback
        session_id = self._generate_session_id()
        self.sessions[session_id] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Build Google OAuth URL
        google_client_id = self.provider_config.get('client_id')
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        
        google_params = {
            "client_id": google_client_id,
            "redirect_uri": f"{self.base_url}/oauth/callback",
            "response_type": "code",
            "scope": "openid email profile",
            "state": session_id,  # Use our session ID as state
            "access_type": "offline",
            "prompt": "consent"
        }
        
        google_url = f"{google_auth_url}?{urlencode(google_params)}"
        logger.info(f"Redirecting to Google OAuth: {google_url[:100]}...")
        
        return RedirectResponse(url=google_url)
    
    async def callback(self, request: Request) -> Response:
        """
        OAuth 2.0 Callback from Google.
        
        GET /oauth/callback
        
        Exchanges Google code for tokens, gets user info, then issues our auth code.
        """
        params = dict(request.query_params)
        
        google_code = params.get("code")
        session_id = params.get("state")  # Our session ID
        error = params.get("error")
        
        if error:
            logger.error(f"Google OAuth error: {error}")
            return HTMLResponse(f"<h1>Authentication Error</h1><p>{error}</p>", status_code=400)
        
        if not google_code or not session_id:
            return HTMLResponse("<h1>Invalid callback</h1>", status_code=400)
        
        # Get original auth request
        session = self.sessions.get(session_id)
        if not session:
            return HTMLResponse("<h1>Session expired</h1>", status_code=400)
        
        # Exchange Google code for tokens
        try:
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.provider_config.get('client_id'),
                        "client_secret": self.provider_config.get('client_secret'),
                        "code": google_code,
                        "grant_type": "authorization_code",
                        "redirect_uri": f"{self.base_url}/oauth/callback"
                    }
                )
                
                if token_response.status_code != 200:
                    logger.error(f"Google token exchange failed: {token_response.text}")
                    return HTMLResponse("<h1>Token exchange failed</h1>", status_code=400)
                
                tokens = token_response.json()
                google_access_token = tokens.get("access_token")
                
                # Get user info from Google
                userinfo_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {google_access_token}"}
                )
                
                if userinfo_response.status_code != 200:
                    logger.error(f"Failed to get user info: {userinfo_response.text}")
                    return HTMLResponse("<h1>Failed to get user info</h1>", status_code=400)
                
                user_info = userinfo_response.json()
                email = user_info.get("email")
                
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)
        
        # Check if user is in our mapping
        if email not in self.user_mappings:
            logger.warning(f"User not authorized: {email}")
            return HTMLResponse(
                f"<h1>Access Denied</h1>"
                f"<p>User {email} is not authorized to use IriusRisk MCP.</p>"
                f"<p>Please contact your administrator to request access.</p>",
                status_code=403
            )
        
        # Generate our own auth code
        auth_code = self._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(seconds=AUTH_CODE_EXPIRES_SECONDS)
        
        self.auth_codes[auth_code] = {
            "email": email,
            "client_id": session["client_id"],
            "redirect_uri": session["redirect_uri"],
            "code_challenge": session.get("code_challenge"),
            "code_challenge_method": session.get("code_challenge_method"),
            "expires_at": expires_at.isoformat(),
            "used": False
        }
        
        # Clean up session
        del self.sessions[session_id]
        
        # Redirect back to client with our auth code
        redirect_params = {"code": auth_code}
        if session.get("state"):
            redirect_params["state"] = session["state"]
        
        redirect_url = f"{session['redirect_uri']}?{urlencode(redirect_params)}"
        logger.info(f"OAuth complete for {email}, redirecting to client")
        
        return RedirectResponse(url=redirect_url)
    
    async def token(self, request: Request) -> JSONResponse:
        """
        OAuth 2.0 Token Endpoint.
        
        POST /oauth/token
        
        Exchanges our auth code for our access token.
        """
        # Parse form data
        form = await request.form()
        
        grant_type = form.get("grant_type")
        code = form.get("code")
        redirect_uri = form.get("redirect_uri")
        client_id = form.get("client_id")
        code_verifier = form.get("code_verifier")
        
        if grant_type != "authorization_code":
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
        
        # Look up auth code
        auth_code_data = self.auth_codes.get(code)
        if not auth_code_data:
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid authorization code"}, status_code=400)
        
        # Check expiry
        expires_at = datetime.fromisoformat(auth_code_data["expires_at"])
        if datetime.utcnow() > expires_at:
            return JSONResponse({"error": "invalid_grant", "error_description": "Authorization code expired"}, status_code=400)
        
        # Check if already used
        if auth_code_data.get("used"):
            return JSONResponse({"error": "invalid_grant", "error_description": "Authorization code already used"}, status_code=400)
        
        # Validate client_id
        if auth_code_data["client_id"] != client_id:
            return JSONResponse({"error": "invalid_grant", "error_description": "Client ID mismatch"}, status_code=400)
        
        # Validate redirect_uri
        if auth_code_data["redirect_uri"] != redirect_uri:
            return JSONResponse({"error": "invalid_grant", "error_description": "Redirect URI mismatch"}, status_code=400)
        
        # Verify PKCE if present
        if auth_code_data.get("code_challenge"):
            if not code_verifier:
                return JSONResponse({"error": "invalid_grant", "error_description": "Code verifier required"}, status_code=400)
            
            if not self._verify_pkce(
                code_verifier,
                auth_code_data["code_challenge"],
                auth_code_data.get("code_challenge_method", "S256")
            ):
                return JSONResponse({"error": "invalid_grant", "error_description": "Invalid code verifier"}, status_code=400)
        
        # Mark code as used
        auth_code_data["used"] = True
        
        # Generate access token
        access_token = self._generate_access_token()
        token_expires_at = datetime.utcnow() + timedelta(seconds=ACCESS_TOKEN_EXPIRES_SECONDS)
        
        self.tokens[access_token] = {
            "email": auth_code_data["email"],
            "client_id": client_id,
            "expires_at": token_expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Issued access token for user: {auth_code_data['email']}")
        
        return JSONResponse({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRES_SECONDS
        }, headers={
            "Access-Control-Allow-Origin": "*"
        })
    
    # =========================================================================
    # CORS Preflight Handlers
    # =========================================================================
    
    async def options_handler(self, request: Request) -> Response:
        """Handle CORS preflight requests."""
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "86400"
            }
        )
    
    def get_routes(self) -> List[Route]:
        """Get Starlette routes for OAuth endpoints."""
        return [
            # Discovery - both OAuth 2.0 and OpenID Connect
            Route("/.well-known/oauth-authorization-server", self.authorization_server_metadata, methods=["GET", "OPTIONS"]),
            Route("/.well-known/openid-configuration", self.openid_configuration, methods=["GET", "OPTIONS"]),
            Route("/.well-known/oauth-protected-resource", self.protected_resource_metadata, methods=["GET", "OPTIONS"]),
            
            # Registration
            Route("/oauth/register", self.register_client, methods=["POST"]),
            Route("/oauth/register", self.options_handler, methods=["OPTIONS"]),
            
            # Authorization flow
            Route("/oauth/authorize", self.authorize, methods=["GET"]),
            Route("/oauth/callback", self.callback, methods=["GET"]),
            Route("/oauth/token", self.token, methods=["POST"]),
            Route("/oauth/token", self.options_handler, methods=["OPTIONS"]),
        ]


def load_oauth_config(config_path: Path) -> Dict[str, Any]:
    """Load OAuth configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)
