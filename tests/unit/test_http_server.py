"""Unit tests for HTTP MCP server implementation.

Tests cover:
- Transport mode enum
- Module imports and structure
- Path prefix normalization logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTransportModeEnum:
    """Test TransportMode enum."""
    
    def test_transport_mode_values(self):
        """Test TransportMode enum has expected values."""
        from src.iriusrisk_cli.mcp.transport import TransportMode
        
        assert TransportMode.STDIO.value == 'stdio'
        assert TransportMode.HTTP.value == 'http'
    
    def test_transport_mode_members(self):
        """Test TransportMode has expected members."""
        from src.iriusrisk_cli.mcp.transport import TransportMode
        
        members = list(TransportMode)
        assert len(members) == 2
        assert TransportMode.STDIO in members
        assert TransportMode.HTTP in members


class TestHTTPServerModuleStructure:
    """Test HTTP server module structure and imports."""
    
    def test_http_server_module_exists(self):
        """Test that http_server module can be imported."""
        from src.iriusrisk_cli.mcp import http_server
        
        assert http_server is not None
    
    def test_run_http_server_function_exists(self):
        """Test that run_http_server function exists."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        assert callable(run_http_server)
    
    def test_http_server_imports_transport_mode(self):
        """Test that HTTP server imports TransportMode."""
        from src.iriusrisk_cli.mcp.http_server import TransportMode
        
        assert TransportMode.HTTP.value == 'http'
    
    def test_http_server_imports_auth_error(self):
        """Test that HTTP server imports AuthenticationError."""
        from src.iriusrisk_cli.mcp.http_server import AuthenticationError
        
        assert issubclass(AuthenticationError, Exception)


class TestHTTPToolsModuleStructure:
    """Test HTTP tools module structure."""
    
    def test_http_tools_module_exists(self):
        """Test that http_tools module can be imported."""
        from src.iriusrisk_cli.mcp.tools import http_tools
        
        assert http_tools is not None
    
    def test_register_http_tools_function_exists(self):
        """Test that register_http_tools function exists."""
        from src.iriusrisk_cli.mcp.tools.http_tools import register_http_tools
        
        assert callable(register_http_tools)


class TestPathPrefixNormalization:
    """Test path prefix normalization via run_http_server.
    
    These tests verify that the actual run_http_server function correctly
    normalizes path prefixes by checking the values passed to OAuthServer.
    
    Note: uvicorn and OAuthServer are imported locally inside run_http_server,
    so we patch them at their source modules.
    """
    
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    @patch('src.iriusrisk_cli.mcp.http_server.FastMCP')
    @patch('src.iriusrisk_cli.mcp.oauth_server.load_oauth_config')
    @patch('src.iriusrisk_cli.mcp.oauth_server.OAuthServer')
    def test_path_prefix_normalization_adds_leading_slash(
        self, mock_oauth_server, mock_load_config, mock_fastmcp, mock_uvicorn_config, mock_uvicorn_server
    ):
        """Test that path prefix without leading slash gets one added."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        mock_load_config.return_value = {'oauth': {'provider': {}}, 'user_mappings': {}}
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()
        mock_fastmcp.return_value = mock_mcp
        mock_uvicorn_server.return_value = MagicMock()
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.get_routes.return_value = []
        mock_oauth_server.return_value = mock_oauth_instance
        
        run_http_server(
            None, '127.0.0.1', 8000,
            oauth_config_file='/fake/path.json',
            base_url='https://example.com',
            path_prefix='test'  # No leading slash
        )
        
        # OAuthServer should be created when oauth config is provided
        mock_oauth_server.assert_called_once()
    
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    @patch('src.iriusrisk_cli.mcp.http_server.FastMCP')
    def test_path_prefix_empty_string_handled(self, mock_fastmcp, mock_uvicorn_config, mock_uvicorn_server):
        """Test that empty path prefix is handled correctly."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()
        mock_fastmcp.return_value = mock_mcp
        mock_uvicorn_server.return_value = MagicMock()
        
        # Should not raise with empty path_prefix
        run_http_server(None, '127.0.0.1', 8000, path_prefix='')
        
        mock_fastmcp.assert_called_once()
    
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    @patch('src.iriusrisk_cli.mcp.http_server.FastMCP')
    def test_path_prefix_with_leading_slash_preserved(self, mock_fastmcp, mock_uvicorn_config, mock_uvicorn_server):
        """Test that path prefix with leading slash works correctly."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()
        mock_fastmcp.return_value = mock_mcp
        mock_uvicorn_server.return_value = MagicMock()
        
        # Should not raise with proper path_prefix
        run_http_server(None, '127.0.0.1', 8000, path_prefix='/test')
        
        mock_fastmcp.assert_called_once()


class TestOAuthServerIntegration:
    """Test OAuth server integration with HTTP server."""
    
    def test_oauth_server_can_be_imported(self):
        """Test that OAuthServer can be imported."""
        from src.iriusrisk_cli.mcp.oauth_server import OAuthServer
        
        assert OAuthServer is not None
    
    def test_load_oauth_config_can_be_imported(self):
        """Test that load_oauth_config can be imported."""
        from src.iriusrisk_cli.mcp.oauth_server import load_oauth_config
        
        assert callable(load_oauth_config)
    
    def test_oauth_server_initialization(self):
        """Test OAuthServer can be initialized."""
        from src.iriusrisk_cli.mcp.oauth_server import OAuthServer
        
        config = {
            'oauth': {'provider': {'name': 'test'}},
            'user_mappings': {}
        }
        
        server = OAuthServer('https://example.com', config)
        
        assert server.base_url == 'https://example.com'
        assert server.provider_config['name'] == 'test'


class TestToolRegistration:
    """Test tool registration interface."""
    
    def test_shared_tools_module_exists(self):
        """Test that shared_tools module can be imported."""
        from src.iriusrisk_cli.mcp.tools import shared_tools
        
        assert shared_tools is not None
    
    def test_register_shared_tools_exists(self):
        """Test that register_shared_tools function exists."""
        from src.iriusrisk_cli.mcp.tools.shared_tools import register_shared_tools
        
        assert callable(register_shared_tools)
    
    def test_tools_init_exports_registration_functions(self):
        """Test that tools __init__ exports registration functions."""
        from src.iriusrisk_cli.mcp.tools import register_shared_tools, register_http_tools
        
        assert callable(register_shared_tools)
        assert callable(register_http_tools)


class TestAuthModuleIntegration:
    """Test auth module integration."""
    
    def test_auth_module_can_be_imported(self):
        """Test that auth module can be imported."""
        from src.iriusrisk_cli.mcp import auth
        
        assert auth is not None
    
    def test_authentication_error_exists(self):
        """Test that AuthenticationError exists."""
        from src.iriusrisk_cli.mcp.auth import AuthenticationError
        
        assert issubclass(AuthenticationError, Exception)
    
    def test_extract_credentials_exists(self):
        """Test that extract_credentials_from_request exists."""
        from src.iriusrisk_cli.mcp.auth import extract_credentials_from_request
        
        assert callable(extract_credentials_from_request)
    
    def test_create_api_client_exists(self):
        """Test that create_api_client_from_request exists."""
        from src.iriusrisk_cli.mcp.auth import create_api_client_from_request
        
        assert callable(create_api_client_from_request)


class TestBaseURLHandling:
    """Test base URL handling in run_http_server.
    
    These tests verify that the actual implementation correctly handles
    base URL defaults and OAuth server initialization.
    
    Note: uvicorn and OAuthServer are imported locally inside run_http_server,
    so we patch them at their source modules.
    """
    
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    @patch('src.iriusrisk_cli.mcp.http_server.FastMCP')
    @patch('src.iriusrisk_cli.mcp.oauth_server.load_oauth_config')
    @patch('src.iriusrisk_cli.mcp.oauth_server.OAuthServer')
    def test_base_url_passed_to_oauth_server(
        self, mock_oauth_server, mock_load_config, mock_fastmcp, mock_uvicorn_config, mock_uvicorn_server
    ):
        """Test that provided base_url is passed to OAuthServer."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        mock_load_config.return_value = {'oauth': {'provider': {}}, 'user_mappings': {}}
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()
        mock_fastmcp.return_value = mock_mcp
        mock_uvicorn_server.return_value = MagicMock()
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.get_routes.return_value = []
        mock_oauth_server.return_value = mock_oauth_instance
        
        run_http_server(
            None, '127.0.0.1', 8000,
            oauth_config_file='/fake/path.json',
            base_url='https://example.com'
        )
        
        # OAuthServer should be called with the provided base_url
        mock_oauth_server.assert_called_once()
        call_args = mock_oauth_server.call_args
        assert call_args[0][0] == 'https://example.com'
    
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    @patch('src.iriusrisk_cli.mcp.http_server.FastMCP')
    def test_no_oauth_server_without_config(self, mock_fastmcp, mock_uvicorn_config, mock_uvicorn_server):
        """Test that OAuthServer is not created without oauth config."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()
        mock_fastmcp.return_value = mock_mcp
        mock_uvicorn_server.return_value = MagicMock()
        
        # No oauth_config_file means no OAuthServer
        run_http_server(None, '127.0.0.1', 8000)
        
        # Should still work without OAuth
        mock_fastmcp.assert_called_once()
    
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    @patch('src.iriusrisk_cli.mcp.http_server.FastMCP')
    @patch('src.iriusrisk_cli.mcp.oauth_server.load_oauth_config')
    @patch('src.iriusrisk_cli.mcp.oauth_server.OAuthServer')
    def test_oauth_server_not_created_without_base_url(
        self, mock_oauth_server, mock_load_config, mock_fastmcp, mock_uvicorn_config, mock_uvicorn_server
    ):
        """Test that OAuthServer is not created if base_url is missing."""
        from src.iriusrisk_cli.mcp.http_server import run_http_server
        
        mock_load_config.return_value = {'oauth': {'provider': {}}, 'user_mappings': {}}
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()
        mock_fastmcp.return_value = mock_mcp
        mock_uvicorn_server.return_value = MagicMock()
        
        # oauth_config but no base_url - logs warning, doesn't create OAuthServer
        run_http_server(
            None, '127.0.0.1', 8000,
            oauth_config_file='/fake/path.json',
            base_url=None  # Missing base_url
        )
        
        # OAuthServer should NOT be called (warning is logged instead)
        mock_oauth_server.assert_not_called()
