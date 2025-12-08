"""MCP tools for IriusRisk CLI.

This module organizes tools into three categories:
- Shared tools: Available in both stdio and HTTP modes
- Stdio tools: Require filesystem access (stdio mode only)
- HTTP tools: Stateless tools for HTTP mode
"""

from .shared_tools import register_shared_tools
from .stdio_tools import register_stdio_tools
from .http_tools import register_http_tools

__all__ = [
    'register_shared_tools',
    'register_stdio_tools', 
    'register_http_tools',
]

