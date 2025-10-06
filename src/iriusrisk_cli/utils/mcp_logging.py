"""MCP-specific logging configuration.

This module provides logging setup specifically for the MCP (Model Context Protocol)
server, which has different requirements than standard CLI logging.
"""

import logging


def setup_mcp_logging(cli_ctx):
    """Set up MCP logging - silent unless --log-file specified, consistent with CLI logging.
    
    The MCP server requires special logging considerations:
    - MUST NOT write to stdout/stderr (corrupts MCP protocol communication)
    - Silent by default (no file logging unless explicitly requested)
    - When log file is specified, uses standard CLI logging levels
    
    Args:
        cli_ctx: CLI context containing logging configuration
    """
    import sys
    
    # Get logging config from CLI context
    logging_config = getattr(cli_ctx, 'logging_config', {})
    log_file = logging_config.get('log_file')
    debug = logging_config.get('debug', False)
    verbose = logging_config.get('verbose', False)
    log_level = logging_config.get('log_level')
    
    # Get the MCP logger
    mcp_logger = logging.getLogger('iriusrisk_cli.commands.mcp')
    
    if log_file:
        # User specified --log-file, respect their log level preferences
        # Determine log level from CLI flags
        if log_level:
            effective_level = log_level.upper()
        elif debug:
            effective_level = "DEBUG"
        elif verbose:
            effective_level = "INFO"
        else:
            effective_level = "INFO"  # Default when log file specified
            
        from .logging_config import setup_logging
        # This sets up the root logger, which our module logger inherits from
        setup_logging(
            log_level=effective_level,
            log_file=log_file,
            console_output=False,  # Never console output for MCP (stdout/stderr contamination)
            component="mcp"
        )
        mcp_logger.debug(f"MCP logging configured: level={effective_level}, file={log_file}")
    else:
        # SILENT - no logging at all unless critical error
        mcp_logger.setLevel(logging.CRITICAL + 1)  # Effectively silent
        if not mcp_logger.handlers:
            mcp_logger.addHandler(logging.NullHandler())
        
        # Also ensure root logger doesn't interfere
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            root_logger.addHandler(logging.NullHandler())
            root_logger.setLevel(logging.CRITICAL + 1)

