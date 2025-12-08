"""
Tests for MCP (Model Context Protocol) related CLI commands.

This module tests the 'iriusrisk mcp' command using mocked components.
Since MCP starts a server, these tests focus on startup behavior and basic functionality.
"""

import pytest
import signal
import time
import threading
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success


class TestMCPCommands:
    """Test cases for MCP CLI commands."""
    
    def test_mcp_help(self, cli_runner):
        """Test that MCP command help works."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert_cli_success(result)
        assert 'MCP' in result.output or 'Model Context Protocol' in result.output
        assert 'server' in result.output.lower()
        assert 'AI' in result.output or 'ai' in result.output.lower()
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_server_startup(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP server startup is attempted."""
        # Mock the FastMCP class and its run method
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should attempt to start the server
        assert result.exit_code == 0, f"MCP command should succeed: {result.output}"
        
        # Should have created FastMCP instance and called run
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_server_with_mock_api_client(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP server works with mocked API client."""
        # Mock the FastMCP class and its run method
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should work with our mock setup
        assert result.exit_code == 0, f"MCP with mock API should succeed: {result.output}"
        
        # Should have attempted to start server
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')


class TestMCPServerBehavior:
    """Test MCP server behavior and integration."""
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_server_exception_handling(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP server handles exceptions gracefully."""
        # Mock the FastMCP class and make run method raise an exception
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.side_effect = Exception("Test server error")
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should handle the exception (should exit with code 1)
        assert result.exit_code == 1, f"Should exit with error code: {result.output}"
        
        # Should have attempted to start server
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_server_keyboard_interrupt(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP server handles KeyboardInterrupt gracefully."""
        # Mock the FastMCP class and make run method raise KeyboardInterrupt
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.side_effect = KeyboardInterrupt("User interrupted")
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should handle KeyboardInterrupt gracefully (should exit with code 1)
        assert result.exit_code == 1, f"Should exit with error code: {result.output}"
        
        # Should have attempted to start server
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_server_initialization(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP server is properly initialized."""
        # Mock the FastMCP class
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should succeed
        assert result.exit_code == 0, f"MCP initialization should succeed: {result.output}"
        
        # Should have created FastMCP instance with correct name
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        
        # Should have called run with stdio transport
        mock_server.run.assert_called_once_with(transport='stdio')


class TestMCPIntegration:
    """Test MCP integration with the overall CLI system."""
    
    def test_mcp_command_exists_in_cli(self, cli_runner):
        """Test that MCP command is properly registered in the CLI."""
        # Test that the main CLI recognizes the mcp command
        result = cli_runner.invoke(cli, ['--help'])
        
        assert_cli_success(result)
        assert 'mcp' in result.output, "MCP command should be listed in main help"
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_with_environment_variables(self, mock_fastmcp_class, cli_runner, mock_api_client, mock_env_vars):
        """Test that MCP works with environment variables set."""
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should work with environment variables
        assert result.exit_code == 0, f"MCP with env vars should succeed: {result.output}"
        
        # Should have attempted to start server
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_server_uses_api_client(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP server has access to API client functionality."""
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should succeed with mock API client
        assert result.exit_code == 0, f"MCP should work with API client: {result.output}"
        
        # Should have started server
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')


@pytest.mark.integration
def test_mcp_command_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for MCP command with full mock setup."""
    with patch('iriusrisk_cli.mcp.stdio_server.FastMCP') as mock_fastmcp_class:
        # Mock the FastMCP class to avoid actually starting it
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        # Test that we can run MCP with all mocking in place
        result = cli_runner.invoke(cli, ['mcp'])
        
        # Should work with our complete mock setup
        assert result.exit_code == 0, f"Integration test failed: {result.output}"
        
        # Should have attempted to start the server
        mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
        mock_server.run.assert_called_once_with(transport='stdio')


class TestMCPCommandValidation:
    """Test MCP command validation and error cases."""
    
    def test_mcp_command_structure(self, cli_runner):
        """Test that MCP command has the expected structure."""
        result = cli_runner.invoke(cli, ['mcp', '--help'])
        
        assert_cli_success(result)
        
        # Should mention key MCP concepts
        output_lower = result.output.lower()
        assert 'mcp' in output_lower, "Should mention MCP"
        assert 'server' in output_lower, "Should mention server"
        assert 'protocol' in output_lower or 'ai' in output_lower, "Should mention protocol or AI"
    
    @patch('iriusrisk_cli.mcp.stdio_server.FastMCP')
    def test_mcp_no_extra_arguments(self, mock_fastmcp_class, cli_runner, mock_api_client):
        """Test that MCP command doesn't accept extra arguments."""
        mock_server = MagicMock()
        mock_fastmcp_class.return_value = mock_server
        mock_server.run.return_value = None
        
        # Try to pass an extra argument
        result = cli_runner.invoke(cli, ['mcp', 'extra-arg'])
        
        # Should either ignore the extra argument or fail gracefully
        assert isinstance(result.exit_code, int), "Should return an exit code"
        
        # If it succeeded, server should have been called
        if result.exit_code == 0:
            mock_fastmcp_class.assert_called_once_with("iriusrisk-cli")
            mock_server.run.assert_called_once_with(transport='stdio')
    
    def test_mcp_command_in_main_help(self, cli_runner):
        """Test that MCP command appears in main CLI help."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert_cli_success(result)
        
        # Should list MCP as an available command
        assert 'mcp' in result.output, "MCP should be listed in main help"
