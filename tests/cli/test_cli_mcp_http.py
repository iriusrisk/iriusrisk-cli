"""Tests for MCP HTTP mode CLI options.

Tests cover:
- --server flag for HTTP mode
- --host and --port options
- --oauth flag and --oauth-config option
- --base-url option for OAuth
- --path-prefix option
- Option validation and error handling
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from iriusrisk_cli.main import cli


class TestMCPHTTPModeOptions:
    """Test MCP HTTP mode CLI options."""
    
    def test_mcp_help_shows_server_option(self, cli_runner):
        """Test that --server option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--server' in result.output
        assert 'HTTP' in result.output
    
    def test_mcp_help_shows_host_option(self, cli_runner):
        """Test that --host option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--host' in result.output
    
    def test_mcp_help_shows_port_option(self, cli_runner):
        """Test that --port option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--port' in result.output
    
    def test_mcp_help_shows_oauth_option(self, cli_runner):
        """Test that --oauth option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--oauth' in result.output
    
    def test_mcp_help_shows_oauth_config_option(self, cli_runner):
        """Test that --oauth-config option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--oauth-config' in result.output
    
    def test_mcp_help_shows_base_url_option(self, cli_runner):
        """Test that --base-url option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--base-url' in result.output
    
    def test_mcp_help_shows_path_prefix_option(self, cli_runner):
        """Test that --path-prefix option is documented in help."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert result.exit_code == 0
        assert '--path-prefix' in result.output


class TestMCPHTTPServerMode:
    """Test MCP server mode with --server flag."""
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_server_flag_calls_http_server(self, mock_run_http, cli_runner):
        """Test that --server flag calls run_http_server."""
        result = cli_runner.invoke(cli, ['mcp', '--server'])
        
        assert result.exit_code == 0
        mock_run_http.assert_called_once()
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_server_default_host_port(self, mock_run_http, cli_runner):
        """Test default host and port values."""
        result = cli_runner.invoke(cli, ['mcp', '--server'])
        
        assert result.exit_code == 0
        call_args = mock_run_http.call_args
        assert call_args[0][1] == '127.0.0.1'  # host
        assert call_args[0][2] == 8000  # port
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_server_custom_host(self, mock_run_http, cli_runner):
        """Test custom host option."""
        result = cli_runner.invoke(cli, ['mcp', '--server', '--host', '0.0.0.0'])
        
        assert result.exit_code == 0
        call_args = mock_run_http.call_args
        assert call_args[0][1] == '0.0.0.0'
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_server_custom_port(self, mock_run_http, cli_runner):
        """Test custom port option."""
        result = cli_runner.invoke(cli, ['mcp', '--server', '--port', '9000'])
        
        assert result.exit_code == 0
        call_args = mock_run_http.call_args
        assert call_args[0][2] == 9000


class TestMCPOAuthOptions:
    """Test OAuth-related CLI options."""
    
    def test_oauth_without_config_shows_error(self, cli_runner):
        """Test that --oauth without --oauth-config shows error."""
        result = cli_runner.invoke(cli, ['mcp', '--server', '--oauth'])
        
        assert result.exit_code == 1
        assert '--oauth-config' in result.output or 'requires' in result.output.lower()
    
    def test_oauth_without_base_url_shows_error(self, cli_runner, tmp_path):
        """Test that --oauth without --base-url shows error."""
        # Create a dummy config file
        config_file = tmp_path / 'oauth.json'
        config_file.write_text('{"oauth": {}, "user_mappings": {}}')
        
        result = cli_runner.invoke(cli, [
            'mcp', '--server', '--oauth',
            '--oauth-config', str(config_file)
        ])
        
        assert result.exit_code == 1
        assert '--base-url' in result.output or 'requires' in result.output.lower()
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_oauth_with_all_required_options(self, mock_run_http, cli_runner, tmp_path):
        """Test OAuth with all required options succeeds."""
        # Create a dummy config file
        config_file = tmp_path / 'oauth.json'
        config_file.write_text('{"oauth": {}, "user_mappings": {}}')
        
        result = cli_runner.invoke(cli, [
            'mcp', '--server', '--oauth',
            '--oauth-config', str(config_file),
            '--base-url', 'https://example.com'
        ])
        
        assert result.exit_code == 0
        mock_run_http.assert_called_once()
        
        call_kwargs = mock_run_http.call_args
        assert str(config_file) in str(call_kwargs)
        assert 'https://example.com' in str(call_kwargs)
    
    def test_oauth_config_nonexistent_file(self, cli_runner):
        """Test error when oauth-config file doesn't exist."""
        result = cli_runner.invoke(cli, [
            'mcp', '--server', '--oauth',
            '--oauth-config', '/nonexistent/oauth.json',
            '--base-url', 'https://example.com'
        ])
        
        # Click validates file existence
        assert result.exit_code != 0


class TestMCPPathPrefixOption:
    """Test --path-prefix option."""
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_path_prefix_passed_to_server(self, mock_run_http, cli_runner):
        """Test that path prefix is passed to HTTP server."""
        result = cli_runner.invoke(cli, [
            'mcp', '--server', '--path-prefix', '/test'
        ])
        
        assert result.exit_code == 0
        call_kwargs = mock_run_http.call_args[1]
        assert call_kwargs['path_prefix'] == '/test'
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_path_prefix_default_empty(self, mock_run_http, cli_runner):
        """Test that path prefix defaults to empty string."""
        result = cli_runner.invoke(cli, ['mcp', '--server'])
        
        assert result.exit_code == 0
        call_kwargs = mock_run_http.call_args[1]
        assert call_kwargs['path_prefix'] == ''


class TestMCPStdioVsHTTPMode:
    """Test that stdio and HTTP modes are mutually exclusive."""
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_default_is_stdio_mode(self, mock_fastmcp, cli_runner):
        """Test that default (no --server) uses stdio mode."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_server.run.return_value = None
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        assert result.exit_code == 0
        mock_fastmcp.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_server_flag_uses_http_mode(self, mock_run_http, cli_runner):
        """Test that --server flag uses HTTP mode."""
        result = cli_runner.invoke(cli, ['mcp', '--server'])
        
        assert result.exit_code == 0
        mock_run_http.assert_called_once()


class TestMCPHTTPModeIntegration:
    """Integration tests for HTTP mode CLI."""
    
    @patch('iriusrisk_cli.mcp.http_server.run_http_server')
    def test_full_oauth_configuration(self, mock_run_http, cli_runner, tmp_path):
        """Test full OAuth configuration with all options."""
        config_file = tmp_path / 'oauth.json'
        config_file.write_text('{"oauth": {"provider": {}}, "user_mappings": {}}')
        
        result = cli_runner.invoke(cli, [
            'mcp', '--server',
            '--host', '0.0.0.0',
            '--port', '9000',
            '--oauth',
            '--oauth-config', str(config_file),
            '--base-url', 'https://api.example.com',
            '--path-prefix', '/v1'
        ])
        
        assert result.exit_code == 0
        mock_run_http.assert_called_once()
        
        call_args = mock_run_http.call_args
        # Positional args
        assert call_args[0][1] == '0.0.0.0'  # host
        assert call_args[0][2] == 9000  # port
        # Keyword args
        assert call_args[1]['oauth_config_file'] == str(config_file)
        assert call_args[1]['base_url'] == 'https://api.example.com'
        assert call_args[1]['path_prefix'] == '/v1'


class TestMCPHTTPHelpText:
    """Test that HTTP mode options have helpful descriptions."""
    
    def test_server_option_description(self, cli_runner):
        """Test --server option has meaningful description."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        # Should mention HTTP in description
        assert 'HTTP' in result.output
    
    def test_oauth_options_mention_authentication(self, cli_runner):
        """Test OAuth options mention authentication."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        # Should mention OAuth or authentication
        output_lower = result.output.lower()
        assert 'oauth' in output_lower or 'authentication' in output_lower
    
    def test_base_url_mentions_callbacks(self, cli_runner):
        """Test --base-url mentions OAuth callbacks."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        # Should mention callback or public URL
        output_lower = result.output.lower()
        assert 'callback' in output_lower or 'public' in output_lower or 'oauth' in output_lower

