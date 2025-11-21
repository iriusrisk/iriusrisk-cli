"""MCP (Model Context Protocol) command for IriusRisk CLI."""

import click
import logging
from ..cli_context import pass_cli_context
from ..utils.mcp_logging import setup_mcp_logging

logger = logging.getLogger(__name__)


@click.command()
@click.option('--server', is_flag=True, help='Run as HTTP server (instead of stdio)')
@click.option('--host', default='127.0.0.1', help='Server host address (HTTP mode only)')
@click.option('--port', default=8000, type=int, help='Server port (HTTP mode only)')
@pass_cli_context
def mcp(cli_ctx, server, host, port):
    """Start MCP (Model Context Protocol) server for AI integration.
    
    This command starts an MCP server that provides tools for AI assistants
    to interact with IriusRisk CLI functionality.
    
    \\b
    Transport Modes:
      stdio (default): Local AI assistants (Claude Desktop, Cursor, etc.)
      --server:        HTTP server for remote AI assistant access
    
    \\b
    Examples:
      iriusrisk mcp                                    # Stdio mode (default)
      iriusrisk mcp --server                           # HTTP server on localhost:8000
      iriusrisk mcp --server --host 0.0.0.0 --port 9000  # Custom HTTP config
    
    \\b
    HTTP Mode Authentication:
      HTTP clients must provide credentials in request headers:
        X-IriusRisk-API-Key: your-api-key
        X-IriusRisk-Hostname: https://your-instance.iriusrisk.com
    
    The MCP server provides:
    - Project management and discovery
    - Threat model creation and analysis
    - Threat and countermeasure management
    - Security workflow automation
    
    This command is not intended for direct user interaction but rather
    for integration with AI systems that support MCP.
    """
    # Configure MCP logging based on CLI context
    setup_mcp_logging(cli_ctx)
    
    if server:
        # HTTP server mode
        logger.info(f"Starting IriusRisk MCP server in HTTP mode on {host}:{port}")
        from ..mcp.http_server import run_http_server
        run_http_server(cli_ctx, host, port)
            else:
        # Stdio mode (default)
        logger.info("Starting IriusRisk MCP server in stdio mode")
        from ..mcp.stdio_server import run_stdio_server
        run_stdio_server(cli_ctx)


if __name__ == "__main__":
    mcp()

