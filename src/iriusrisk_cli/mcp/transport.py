"""Transport mode detection and configuration for MCP server."""

from enum import Enum


class TransportMode(Enum):
    """Supported MCP transport modes."""
    STDIO = "stdio"
    HTTP = "http"

