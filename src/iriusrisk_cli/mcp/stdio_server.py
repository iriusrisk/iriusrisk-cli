"""Stdio MCP server implementation for IriusRisk CLI.

This module provides the stdio transport implementation for local
AI assistant integration (Claude Desktop, Cursor, etc.).
"""

import logging
import sys
from mcp.server.fastmcp import FastMCP
from .transport import TransportMode
from .tools import register_shared_tools, register_stdio_tools

logger = logging.getLogger(__name__)


def run_stdio_server(cli_ctx):
    """Run the MCP server in stdio mode (default local mode).
    
    Args:
        cli_ctx: CLI context with config and API client
    """
    logger.info("Starting IriusRisk MCP server in stdio mode")
    
    # Get config and API client from context
    config = cli_ctx.get_config()
    
    # Get API client from container
    from ..container import get_container
    from ..api_client import IriusRiskApiClient
    container = get_container()
    api_client = container.get(IriusRiskApiClient)
    
    # Initialize FastMCP server
    mcp_server = FastMCP("iriusrisk-cli")
    
    # Register tools for stdio mode
    logger.info("Registering stdio mode tools")
    register_shared_tools(mcp_server, api_client=api_client, transport_mode=TransportMode.STDIO)
    register_stdio_tools(mcp_server, api_client=api_client)
    
    # Run the server with stdio transport
    try:
        logger.info("MCP stdio server initialized successfully")
        mcp_server.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error running MCP stdio server: {e}")
        import click
        click.echo(f"Error starting MCP server: {e}", err=True)
        sys.exit(1)

