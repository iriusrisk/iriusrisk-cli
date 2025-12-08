"""MCP (Model Context Protocol) server implementation for IriusRisk CLI.

This module provides both stdio and HTTP transport modes for MCP integration.
"""

from .transport import TransportMode

__all__ = ['TransportMode']

