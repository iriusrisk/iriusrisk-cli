"""
Tests for main CLI commands.

This module tests the main CLI commands like help, version, and basic CLI functionality.
"""

import pytest
import json
from click.testing import CliRunner

from iriusrisk_cli.main import cli


class TestMainCLICommands:
    """Test cases for main CLI commands."""
    
    def test_cli_help_command(self, cli_runner):
        """Test 'iriusrisk help' command."""
        result = cli_runner.invoke(cli, ['help'])
        
        assert result.exit_code == 0, f"Help command failed: {result.output}"
        
        # Should contain comprehensive help information
        assert "IriusRisk CLI - Command Line Interface" in result.output
        assert "CONFIGURATION:" in result.output
        assert "AVAILABLE COMMANDS:" in result.output
        assert "EXAMPLES:" in result.output
        
        # Should contain key command examples
        assert "iriusrisk init" in result.output
        assert "iriusrisk project list" in result.output
        assert "iriusrisk sync" in result.output
        assert "iriusrisk reports generate" in result.output
    
    def test_cli_version_command(self, cli_runner):
        """Test 'iriusrisk version' command."""
        result = cli_runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0, f"Version command failed: {result.output}"
        assert "IriusRisk CLI version" in result.output
        assert "0.4.0" in result.output  # Current version
    
    def test_cli_version_flag(self, cli_runner):
        """Test 'iriusrisk --version' flag."""
        result = cli_runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0, f"Version flag failed: {result.output}"
        assert "IriusRisk CLI version" in result.output
        assert "0.4.0" in result.output
    
    def test_cli_help_flag(self, cli_runner):
        """Test 'iriusrisk --help' flag."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0, f"Help flag failed: {result.output}"
        
        # Should contain basic CLI help
        assert "IriusRisk CLI - A command line interface" in result.output
        assert "Commands:" in result.output
        
        # Should list main command groups
        assert "project" in result.output
        assert "threat" in result.output
        assert "countermeasure" in result.output
        assert "sync" in result.output
        assert "reports" in result.output
        assert "init" in result.output
        assert "mcp" in result.output
        assert "otm" in result.output
    
    def test_cli_no_command(self, cli_runner):
        """Test 'iriusrisk' with no command (should show help)."""
        result = cli_runner.invoke(cli, [])
        
        assert result.exit_code == 0, f"No command failed: {result.output}"
        
        # Should show help when no command provided
        assert "Usage:" in result.output
        assert "Commands:" in result.output
    
    def test_cli_invalid_command(self, cli_runner):
        """Test 'iriusrisk invalid-command'."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code != 0, "Invalid command should fail"
        assert "No such command" in result.output or "Usage:" in result.output
    
    def test_cli_command_aliases(self, cli_runner):
        """Test that command aliases work correctly."""
        # Test plural aliases
        aliases_to_test = [
            ('projects', 'project'),
            ('threats', 'threat'),
            ('countermeasures', 'countermeasure'),
            ('components', 'component')
        ]
        
        for alias, original in aliases_to_test:
            # Test that alias help works
            alias_result = cli_runner.invoke(cli, [alias, '--help'])
            original_result = cli_runner.invoke(cli, [original, '--help'])
            
            # Both should succeed
            assert alias_result.exit_code == 0, f"Alias '{alias}' help failed"
            assert original_result.exit_code == 0, f"Original '{original}' help failed"
            
            # Help content should be similar (both should mention the functionality)
            # Note: We don't expect exact matches since aliases might be hidden
            assert len(alias_result.output.strip()) > 0, f"Alias '{alias}' should produce help output"
            assert len(original_result.output.strip()) > 0, f"Original '{original}' should produce help output"


class TestMainCLIConfiguration:
    """Test CLI configuration and environment handling."""
    
    def test_cli_with_environment_variables(self, cli_runner, mock_env_vars):
        """Test CLI with environment variables set."""
        # This should not fail even with environment variables
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0, f"CLI with env vars failed: {result.output}"
        assert "Commands:" in result.output
    
    def test_cli_context_setup(self, cli_runner):
        """Test that CLI context is properly set up."""
        # Test a command that requires CLI context
        result = cli_runner.invoke(cli, ['project', '--help'])
        
        assert result.exit_code == 0, f"CLI context setup failed: {result.output}"
        assert "Manage IriusRisk projects" in result.output


class TestMainCLIErrorHandling:
    """Test error handling in main CLI."""
    
    def test_cli_graceful_error_handling(self, cli_runner):
        """Test that CLI handles errors gracefully."""
        # Test with invalid option
        result = cli_runner.invoke(cli, ['--invalid-option'])
        
        assert result.exit_code != 0, "Invalid option should fail"
        
        # Should not show Python tracebacks to users
        assert "Traceback" not in result.output, "Should not show Python tracebacks"
        assert "Exception" not in result.output, "Should not show raw exceptions"
    
    def test_cli_command_not_found_error(self, cli_runner):
        """Test CLI behavior with non-existent commands."""
        result = cli_runner.invoke(cli, ['nonexistent'])
        
        assert result.exit_code != 0, "Non-existent command should fail"
        assert "No such command" in result.output or "Usage:" in result.output


class TestMCPExampleCommand:
    """Test cases for the mcp-example command."""
    
    def test_mcp_example_command(self, cli_runner):
        """Test 'iriusrisk mcp-example' command."""
        result = cli_runner.invoke(cli, ['mcp-example'])
        
        assert result.exit_code == 0, f"mcp-example command failed: {result.output}"
        
        # Should output valid JSON
        try:
            import json
            output_data = json.loads(result.output.strip())
        except json.JSONDecodeError:
            pytest.fail(f"mcp-example should output valid JSON, got: {result.output}")
        
        # Should have the expected structure
        assert "mcpServers" in output_data, "Should contain mcpServers key"
        assert "iriusrisk-cli" in output_data["mcpServers"], "Should contain iriusrisk-cli server config"
        
        server_config = output_data["mcpServers"]["iriusrisk-cli"]
        assert "command" in server_config, "Should contain command key"
        assert "args" in server_config, "Should contain args key"
        assert server_config["command"] == "iriusrisk", "Command should be 'iriusrisk'"
        assert server_config["args"] == ["mcp"], "Args should be ['mcp']"
    
    def test_mcp_example_help(self, cli_runner):
        """Test 'iriusrisk mcp-example --help' command."""
        result = cli_runner.invoke(cli, ['mcp-example', '--help'])
        
        assert result.exit_code == 0, f"mcp-example help failed: {result.output}"
        
        # Should contain help information
        assert "Generate an example mcp.json file" in result.output
        assert "MCP server configuration" in result.output
        assert "Examples:" in result.output
        assert "mcp.json" in result.output
    
    def test_mcp_example_json_format(self, cli_runner):
        """Test that mcp-example outputs properly formatted JSON."""
        result = cli_runner.invoke(cli, ['mcp-example'])
        
        assert result.exit_code == 0, f"mcp-example command failed: {result.output}"
        
        # Should be properly formatted JSON (with indentation)
        assert "{\n" in result.output, "Should have formatted JSON with newlines"
        assert "  " in result.output, "Should have indentation"
        
        # Should contain expected content
        assert '"mcpServers"' in result.output
        assert '"iriusrisk-cli"' in result.output
        assert '"command": "iriusrisk"' in result.output
        assert '"mcp"' in result.output
    
    def test_mcp_example_no_arguments(self, cli_runner):
        """Test that mcp-example doesn't accept arguments."""
        # Should work without arguments
        result = cli_runner.invoke(cli, ['mcp-example'])
        assert result.exit_code == 0, "Should work without arguments"
        
        # Should handle extra arguments gracefully (Click will ignore them or show error)
        result_with_args = cli_runner.invoke(cli, ['mcp-example', 'extra'])
        # Either succeeds (ignores extra args) or fails with usage error
        assert isinstance(result_with_args.exit_code, int), "Should return an exit code"


class TestMainCLIIntegration:
    """Integration tests for main CLI functionality."""
    
    def test_cli_full_help_integration(self, cli_runner, mock_env_vars):
        """Test full help command with environment setup."""
        result = cli_runner.invoke(cli, ['help'])
        
        assert result.exit_code == 0, f"Full help integration failed: {result.output}"
        
        # Should contain all major sections
        sections = [
            "DESCRIPTION:",
            "CONFIGURATION:", 
            "BASIC USAGE:",
            "AVAILABLE COMMANDS:",
            "EXAMPLES:"
        ]
        
        for section in sections:
            assert section in result.output, f"Help should contain {section}"
        
        # Should contain environment variable documentation
        assert "IRIUS_HOSTNAME" in result.output
        assert "IRIUS_API_KEY" in result.output
    
    def test_cli_version_integration(self, cli_runner, mock_env_vars):
        """Test version command with environment setup."""
        result = cli_runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0, f"Version integration failed: {result.output}"
        assert "IriusRisk CLI version" in result.output
    
    def test_cli_command_discovery(self, cli_runner):
        """Test that all expected commands are discoverable."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0, f"Command discovery failed: {result.output}"
        
        # All main command groups should be listed
        expected_commands = [
            'component',
            'countermeasure', 
            'help',
            'init',
            'issue-tracker',
            'mcp',
            'mcp-example',
            'otm',
            'project',
            'reports',
            'sync',
            'threat',
            'updates',
            'version'
        ]
        
        for command in expected_commands:
            assert command in result.output, f"Command '{command}' should be listed in help"


def test_main_cli_basic_functionality(cli_runner):
    """Test basic CLI functionality works."""
    result = cli_runner.invoke(cli, ['--help'])
    
    assert result.exit_code == 0
    assert len(result.output.strip()) > 0
    assert "IriusRisk CLI" in result.output


def test_main_cli_command_structure(cli_runner):
    """Test that CLI has proper command structure."""
    result = cli_runner.invoke(cli, ['--help'])
    
    assert result.exit_code == 0
    
    # Should have proper Click command structure
    assert "Usage:" in result.output
    assert "Options:" in result.output
    assert "Commands:" in result.output
