"""HTTP MCP server implementation for IriusRisk CLI.

This module provides the HTTP transport implementation with per-request
authentication and stateless operation.
"""

import logging
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route
from .transport import TransportMode
from .tools import register_shared_tools, register_http_tools
from .auth import AuthenticationError

logger = logging.getLogger(__name__)


def run_http_server(cli_ctx, host: str, port: int, oauth_config_file: str = None, 
                    path_prefix: str = "", base_url: str = None):
    """Run the MCP server in HTTP mode.
    
    Args:
        cli_ctx: CLI context (not used in HTTP mode as we get config from requests)
        host: Host address to bind to
        port: Port number to listen on
        oauth_config_file: Optional path to OAuth configuration file for OAuth mode
        path_prefix: Path prefix for all endpoints (e.g., "/test")
        base_url: Public base URL (e.g., "https://thedial.coffee/test") - required for OAuth
    """
    # Normalize path prefix
    if path_prefix and not path_prefix.startswith('/'):
        path_prefix = '/' + path_prefix
    path_prefix = path_prefix.rstrip('/') if path_prefix else ""
    
    # Load OAuth config and create OAuth server if provided
    oauth_server = None
    oauth_config = None
    if oauth_config_file:
        logger.info("Loading OAuth configuration")
        try:
            from .oauth_server import OAuthServer, load_oauth_config
            
            oauth_config = load_oauth_config(Path(oauth_config_file))
            user_count = len(oauth_config.get('user_mappings', {}))
            provider_name = oauth_config.get('oauth', {}).get('provider', {}).get('name', 'unknown')
            logger.info(f"Loaded OAuth config with {user_count} user mappings")
            logger.info(f"OAuth mode enabled with {user_count} mapped users")
            
            # Create OAuth server for handling OAuth flow
            if base_url:
                oauth_server = OAuthServer(base_url, oauth_config)
                logger.info(f"OAuth server initialized with base URL: {base_url}")
            else:
                logger.warning("OAuth config provided but no --base-url specified")
                logger.warning("OAuth flow endpoints will not be available")
                
        except Exception as e:
            logger.error(f"Failed to load OAuth config: {e}")
            import traceback
            traceback.print_exc()
            import click
            click.echo(f"Error loading OAuth config: {e}", err=True)
            sys.exit(1)
    else:
        logger.info("OAuth mode disabled - using direct API key authentication")
    
    logger.info(f"Starting IriusRisk MCP server in HTTP mode on {host}:{port}")
    if path_prefix:
        logger.info(f"Path prefix: {path_prefix}")
    
    # Initialize FastMCP server
    mcp_server = FastMCP("iriusrisk-cli-http")
    
    # Define a function to get API client from current request
    def get_api_client():
        """Get request-scoped API client from HTTP request headers."""
        try:
            context = mcp_server.get_context()
            request = context.request_context.request
            
            # Debug logging
            logger.debug("=== REQUEST AUTHENTICATION DEBUG ===")
            logger.debug(f"OAuth server active: {oauth_server is not None}")
            
            # If OAuth server is active, get credentials from validated token
            if oauth_server:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    token_info = oauth_server.validate_token(token)
                    
                    if token_info:
                        logger.debug("Token validated successfully.")
                        
                        # Create API client with IriusRisk credentials from mapping
                        from ..api_client import IriusRiskApiClient
                        from ..config import Config
                        
                        config = Config()
                        config._api_key = token_info['api_key']
                        config._hostname = token_info['hostname']
                        
                        return IriusRiskApiClient(config)
                    else:
                        raise AuthenticationError("Invalid or expired token")
                else:
                    raise AuthenticationError("Missing Bearer token")
            
            # Fallback to direct API key authentication
            from .auth import create_api_client_from_request
            return create_api_client_from_request(request)
            
        except Exception as e:
            logger.error(f"Failed to get API client from request: {e}")
            raise AuthenticationError(f"Failed to authenticate request: {e}")
    
    # Register tools for HTTP mode
    logger.info("Registering HTTP mode tools")
    register_shared_tools(mcp_server, api_client=None, transport_mode=TransportMode.HTTP)
    register_http_tools(mcp_server, get_api_client_func=get_api_client)
    
    # Get the MCP ASGI app
    mcp_app = mcp_server.streamable_http_app()
    
    # Build combined ASGI app
    # OAuth routes are handled by Starlette, MCP requests go to the MCP app
    oauth_routes = []
    
    if oauth_server:
        oauth_routes = oauth_server.get_routes()
        
        logger.info(f"OAuth endpoints registered:")
        logger.info(f"  OIDC Discovery: /.well-known/openid-configuration")
        logger.info(f"  OAuth Discovery: /.well-known/oauth-authorization-server")
        logger.info(f"  Protected Resource: /.well-known/oauth-protected-resource")
        logger.info(f"  Register: /oauth/register")
        logger.info(f"  Authorize: /oauth/authorize")
        logger.info(f"  Callback: /oauth/callback")
        logger.info(f"  Token: /oauth/token")
    
    oauth_app = Starlette(routes=oauth_routes) if oauth_routes else None
    logger.info("MCP endpoint: /mcp")
    
    # Store base_url for use in combined_app
    effective_base_url = base_url or f"http://{host}:{port}"
    
    # Create a simple ASGI router that dispatches based on path
    async def combined_app(scope, receive, send):
        logger.debug(f"combined_app called: type={scope['type']}, path={scope.get('path', 'N/A')}")
        
        if scope["type"] == "lifespan":
            # Let MCP app handle lifespan
            await mcp_app(scope, receive, send)
            return
        
        path = scope.get("path", "")
        
        # OAuth routes - handle these first (no auth required for OAuth discovery/flow)
        if oauth_app and (path.startswith("/oauth") or path.startswith("/.well-known")):
            logger.debug(f"Routing to OAuth app: {path}")
            await oauth_app(scope, receive, send)
            return
        
        # For MCP routes when OAuth is enabled, check authentication
        if oauth_server and scope["type"] == "http":
            # Check for Authorization header
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            
            # Build the protected resource metadata URL (RFC 9728)
            resource_metadata_url = f"{effective_base_url}/.well-known/oauth-protected-resource"
            www_authenticate = f'Bearer resource_metadata="{resource_metadata_url}"'
            
            # No Bearer token at all - return 401 to trigger OAuth flow
            if not auth_header.startswith("Bearer "):
                logger.info("No Bearer token - returning 401 to trigger OAuth flow")
                
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"www-authenticate", www_authenticate.encode()],
                        [b"access-control-allow-origin", b"*"],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "unauthorized", "error_description": "Missing Authorization header"}',
                })
                return
            
            # Has Bearer token - validate it
            token = auth_header[7:]  # Remove "Bearer " prefix
            token_info = oauth_server.validate_token(token)
            
            if not token_info:
                # Token is invalid - return 401
                logger.info(f"Invalid Bearer token - returning 401")
                
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"www-authenticate", www_authenticate.encode()],
                        [b"access-control-allow-origin", b"*"],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "invalid_token", "error_description": "Invalid or expired token"}',
                })
                return
            
            logger.debug("Token validated successfully")
        
        # Everything else goes to MCP app (it handles /mcp internally)
        await mcp_app(scope, receive, send)
    
    app = combined_app
    
    # Start the HTTP server
    try:
        logger.info("MCP HTTP server initialized successfully")
        logger.info(f"Server will listen on http://{host}:{port}")
        logger.info("Press Ctrl+C to stop the server")
        
        import uvicorn
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            timeout_graceful_shutdown=5
        )
        server = uvicorn.Server(config)
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping server...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running MCP HTTP server: {e}")
        import click
        click.echo(f"Error starting MCP HTTP server: {e}", err=True)
        sys.exit(1)
