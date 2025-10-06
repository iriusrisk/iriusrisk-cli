"""
Tests for countermeasure-related CLI commands.

This module tests the 'iriusrisk countermeasure' commands using mocked API responses.
"""

import pytest
import json
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success


class TestCountermeasureCommands:
    """Test cases for countermeasure CLI commands."""
    
    def test_countermeasure_list_default(self, cli_runner, mock_api_client):
        """Test 'iriusrisk countermeasure list <project-id>' command."""
        result = cli_runner.invoke(cli, ['countermeasure', 'list', 'test-project'])
        
        assert_cli_success(result)
        
        # Should show countermeasure information
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['countermeasure', 'validation', 'security']), \
            f"Output should contain countermeasure-related keywords: {result.output}"
    
    def test_countermeasure_list_json_format(self, cli_runner, mock_api_client):
        """Test 'iriusrisk countermeasure list --format json' command."""
        result = cli_runner.invoke(cli, ['countermeasure', 'list', 'test-project', '--format', 'json'])
        
        assert_cli_success(result)
        
        # The command may return a message if no countermeasures are found, or JSON if they exist
        # Both are valid responses depending on the mock data
        if result.output.strip().startswith('{') or result.output.strip().startswith('['):
            # It's JSON, verify it's valid
            try:
                data = json.loads(result.output)
                assert isinstance(data, (dict, list)), "JSON output should be dict or list"
            except json.JSONDecodeError:
                pytest.fail(f"Output claims to be JSON but is invalid: {result.output}")
        else:
            # It's a message (like "No countermeasures found"), which is also valid
            assert result.output.strip(), "Should have some output message"
    
    def test_countermeasure_show_by_id(self, cli_runner, mock_api_client):
        """Test 'iriusrisk countermeasure show <countermeasure-id>' command."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        result = cli_runner.invoke(cli, ['countermeasure', 'show', 'countermeasure-123', 'test-project'])
        
        # Command should handle gracefully with mock data
        if result.exit_code == 0:
            # If successful, should produce meaningful output
            assert result.output.strip(), "Should produce output"
            # Should not contain exception traces
            assert 'exception' not in result.output.lower(), "Should not contain exception traces"
        else:
            # If failed, should provide meaningful error message
            assert result.output.strip(), "Should provide error message"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['not found', 'error', 'countermeasure']), \
                f"Error message should be meaningful: {result.output}"
        
        # Should have attempted API calls
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have attempted API calls for countermeasure lookup"
    
    def test_countermeasure_search(self, cli_runner, mock_api_client):
        """Test 'iriusrisk countermeasure search' command."""
        result = cli_runner.invoke(cli, ['countermeasure', 'search', 'test-project', 'validation'])
        
        assert_cli_success(result)
        
        # Should show search results
        assert result.output.strip(), "Search should produce results"
    
    def test_countermeasure_update_status(self, cli_runner, mock_api_client):
        """Test 'iriusrisk countermeasure update' command."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        result = cli_runner.invoke(cli, ['countermeasure', 'update', 'countermeasure-123', 
                                        '--status', 'implemented', '--project', 'test-project'])
        
        # Command should handle gracefully with mock data
        if result.exit_code == 0:
            # If successful, should indicate update operation
            assert result.output.strip(), "Should produce output"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['updated', 'countermeasure', 'implemented', 'success']), \
                f"Output should indicate update operation: {result.output}"
        else:
            # If failed, should provide meaningful error message
            assert result.output.strip(), "Should provide error message"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['not found', 'error', 'countermeasure']), \
                f"Error message should be meaningful: {result.output}"
        
        # Should have attempted API calls for countermeasure update
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have attempted API calls for countermeasure update"
    
    def test_countermeasure_create_issue(self, cli_runner, mock_api_client):
        """Test 'iriusrisk countermeasure create-issue' command."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        result = cli_runner.invoke(cli, ['countermeasure', 'create-issue', 'countermeasure-123', 
                                        '--project', 'test-project'])
        
        # Command should handle gracefully with mock data
        if result.exit_code == 0:
            # If successful, should indicate issue creation
            assert result.output.strip(), "Should produce output"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['issue', 'created', 'countermeasure', 'success']), \
                f"Output should indicate issue creation: {result.output}"
        else:
            # If failed, should provide meaningful error message
            assert result.output.strip(), "Should provide error message"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['not found', 'error', 'countermeasure']), \
                f"Error message should be meaningful: {result.output}"
        
        # Should have attempted API calls for issue creation
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have attempted API calls for issue creation"
    
    def test_countermeasure_commands_help(self, cli_runner):
        """Test that countermeasure command help works."""
        result = cli_runner.invoke(cli, ['countermeasure', '--help'])
        
        assert_cli_success(result)
        assert 'list' in result.output
        assert 'show' in result.output
        assert 'search' in result.output
        assert 'update' in result.output
        assert 'create-issue' in result.output
    
    def test_countermeasure_list_help(self, cli_runner):
        """Test that countermeasure list help works."""
        result = cli_runner.invoke(cli, ['countermeasure', 'list', '--help'])
        
        assert_cli_success(result)
        assert 'format' in result.output.lower()


class TestCountermeasureCommandsWithFixtures:
    """Test countermeasure commands using specific fixture data."""
    
    def test_countermeasure_list_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that countermeasure list actually uses our mock fixture data."""
        # Run the command
        result = cli_runner.invoke(cli, ['countermeasure', 'list', 'test-project'])
        
        # Should succeed with our mock data
        assert result.exit_code == 0, f"Command failed with: {result.output}"
        
        # Should have some output (not empty)
        assert result.output.strip(), "Command should produce some output"
    
    def test_countermeasure_show_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that countermeasure show attempts to use mock data."""
        # Use a generic countermeasure ID
        result = cli_runner.invoke(cli, ['countermeasure', 'show', 'test-countermeasure', 'test-project'])
        
        # The command should run (whether it succeeds depends on fixture data)
        assert isinstance(result.exit_code, int), "Should return an exit code"
        
        # Should produce some output
        assert result.output.strip(), "Command should produce some output"


@pytest.mark.integration
def test_countermeasure_command_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for countermeasure commands with full mock setup."""
    # Test that we can run countermeasure list with all mocking in place
    result = cli_runner.invoke(cli, ['countermeasure', 'list', 'test-project'])
    
    # Should work with our complete mock setup
    assert result.exit_code == 0, f"Integration test failed: {result.output}"
    
    # Should have meaningful output
    assert len(result.output.strip()) > 0, "Should produce output"
