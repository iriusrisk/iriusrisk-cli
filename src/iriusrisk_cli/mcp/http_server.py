"""HTTP MCP server implementation for IriusRisk CLI.

This module provides the HTTP transport implementation with per-request
authentication and stateless operation.
"""

import logging
import sys
from mcp.server.fastmcp import FastMCP
from .transport import TransportMode
from .tools import register_shared_tools, register_http_tools
from .auth import create_api_client_from_request, AuthenticationError

logger = logging.getLogger(__name__)


def run_http_server(cli_ctx, host: str, port: int):
    """Run the MCP server in HTTP mode.
    
    Args:
        cli_ctx: CLI context (not used in HTTP mode as we get config from requests)
        host: Host address to bind to
        port: Port number to listen on
    """
    logger.info(f"Starting IriusRisk MCP server in HTTP mode on {host}:{port}")
    
    # Initialize FastMCP server
    mcp_server = FastMCP("iriusrisk-cli-http")
    
    #Define a function to get API client from current request
    def get_api_client():
        """Get request-scoped API client from HTTP request headers.
        
        This function extracts credentials from the current HTTP request
        and creates an API client for this specific request.
        
        Returns:
            IriusRiskApiClient instance
            
        Raises:
            AuthenticationError: If credentials are missing or invalid
        """
        # Get HTTP request from FastMCP context
        try:
            context = mcp_server.get_context()
            request = context.request_context.request
            return create_api_client_from_request(request)
        except Exception as e:
            logger.error(f"Failed to get API client from request: {e}")
            raise AuthenticationError(f"Failed to authenticate request: {e}")
    
    # Register tools for HTTP mode
    logger.info("Registering HTTP mode tools")
    register_shared_tools(mcp_server, api_client=None, transport_mode=TransportMode.HTTP)
    register_http_tools(mcp_server, get_api_client_func=get_api_client)
    
    # Start the HTTP server
    try:
        logger.info("MCP HTTP server initialized successfully")
        logger.info(f"Server will listen on http://{host}:{port}")
        logger.info("Press Ctrl+C to stop the server")
        
        # Get the ASGI app and run with uvicorn
        import uvicorn
        app = mcp_server.streamable_http_app()
        
        # Run uvicorn server
        uvicorn.run(app, host=host, port=port, log_level="info")
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping server...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running MCP HTTP server: {e}")
        import click
        click.echo(f"Error starting MCP HTTP server: {e}", err=True)
        sys.exit(1)

