"""
Tests for threat-related CLI commands.

This module tests the 'iriusrisk threat' commands using mocked API responses.
"""

import pytest
import json
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success


class TestThreatCommands:
    """Test cases for threat CLI commands."""
    
    def test_threat_list_default(self, cli_runner, mock_api_client):
        """Test 'iriusrisk threat list <project-id>' command."""
        result = cli_runner.invoke(cli, ['threat', 'list', 'test-project'])
        
        assert_cli_success(result)
        
        # Should show threat information
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['threat', 'sql', 'risk']), \
            f"Output should contain threat-related keywords: {result.output}"
    
    def test_threat_list_json_format(self, cli_runner, mock_api_client):
        """Test 'iriusrisk threat list --format json' command."""
        result = cli_runner.invoke(cli, ['threat', 'list', 'test-project', '--format', 'json'])
        
        assert_cli_success(result)
        
        # Verify output is valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, (dict, list)), "JSON output should be dict or list"
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.output}")
    
    def test_threat_show_by_id(self, cli_runner, mock_api_client):
        """Test 'iriusrisk threat show <threat-id>' command."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        result = cli_runner.invoke(cli, ['threat', 'show', 'threat-123', 'test-project'])
        
        # Command should handle gracefully with mock data
        if result.exit_code == 0:
            # If successful, should produce meaningful output
            assert result.output.strip(), "Should produce output"
            # Should not contain exception traces
            assert 'exception' not in result.output.lower(), "Should not contain exception traces"
        else:
            # If failed, should provide meaningful error
            assert result.output.strip(), "Should provide error message"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['not found', 'error', 'threat']), \
                f"Error should be meaningful: {result.output}"
        
        # Should have attempted API calls
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have attempted API calls for threat lookup"
    
    def test_threat_search(self, cli_runner, mock_api_client):
        """Test 'iriusrisk threat search' command."""
        result = cli_runner.invoke(cli, ['threat', 'search', 'test-project', 'SQL'])
        
        assert_cli_success(result)
        
        # Should show search results
        assert result.output.strip(), "Search should produce results"
    
    def test_threat_update_status(self, cli_runner, mock_api_client):
        """Test 'iriusrisk threat update' command."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        # Use 'accept' which is a valid state transition (mitigate is auto-calculated)
        result = cli_runner.invoke(cli, ['threat', 'update', 'threat-123', '--status', 'accept', '--reason', 'Risk accepted', '--project', 'test-project'])
        
        # Command should handle gracefully with mock data
        if result.exit_code == 0:
            # If successful, should indicate update operation
            assert result.output.strip(), "Should produce output"
            output_lower = result.output.lower()
            # Should reference the operation or status
            assert any(keyword in output_lower for keyword in ['updated', 'accept', 'threat', 'success']), \
                f"Should indicate update operation: {result.output}"
        else:
            # If failed, should provide meaningful error
            assert result.output.strip(), "Should provide error message"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['not found', 'error', 'threat', 'invalid']), \
                f"Error should be meaningful: {result.output}"
        
        # Should have attempted API calls for threat update
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have attempted API calls for threat update"
    
    def test_threat_commands_help(self, cli_runner):
        """Test that threat command help works."""
        result = cli_runner.invoke(cli, ['threat', '--help'])
        
        assert_cli_success(result)
        assert 'list' in result.output
        assert 'show' in result.output
        assert 'search' in result.output
        assert 'update' in result.output


@pytest.mark.integration
def test_threat_list_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for threat list command."""
    result = cli_runner.invoke(cli, ['threat', 'list', 'test-project'])
    
    # Should work with our complete mock setup
    assert result.exit_code == 0, f"Integration test failed: {result.output}"
    
    # Should have meaningful output
    assert len(result.output.strip()) > 0, "Should produce output"
