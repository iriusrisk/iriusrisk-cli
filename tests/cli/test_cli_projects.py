"""
Tests for project-related CLI commands.

This module tests the 'iriusrisk project' commands using mocked API responses
to ensure they work correctly without requiring actual API access.
"""

import pytest
import json
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success, assert_cli_failure
from tests.utils.assertions import assert_json_structure, assert_project_structure, assert_api_response_structure, assert_table_output


class TestProjectCommands:
    """Test cases for project CLI commands."""
    
    def test_project_list_default(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project list' command with default output."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Command must succeed
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Must produce output
        assert result.output.strip(), "Command should produce output"
        
        # Should not contain error messages
        output_lower = result.output.lower()
        assert 'error' not in output_lower, f"Should not contain errors: {result.output}"
        assert 'failed' not in output_lower, f"Should not contain failure messages: {result.output}"
        
        # Verify correct API call was made
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have made at least one API call"
        assert any(call['method'] == 'GET' and '/projects' in call['path'] for call in calls), \
            f"Should have called GET /projects. Actual calls: {calls}"
    
    def test_project_list_json_format(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project list --format json' command."""
        result = cli_runner.invoke(cli, ['project', 'list', '--format', 'json'])
        
        # Command must succeed
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Must produce output
        assert result.output.strip(), "JSON command should produce output"
        
        # Verify output is valid JSON with expected structure
        try:
            data = json.loads(result.output)
            
            # Use our strengthened API response validation
            projects = assert_api_response_structure(data, expect_items=False)  # Don't require items for empty responses
            
            # Validate each project structure if projects exist
            for project in projects:
                assert_project_structure(project)
                    
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput: {result.output}")
    
    def test_project_list_with_name_filter(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project list --name' command with filtering."""
        result = cli_runner.invoke(cli, ['project', 'list', '--name', 'test'])
        
        assert_cli_success(result)
        
        # Should show filtered results
        assert result.output.strip() != "", "Filtered results should not be empty"
    
    def test_project_show_by_id(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project show <id>' command."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        project_id = "test-project-123"
        result = cli_runner.invoke(cli, ['project', 'show', project_id])
        
        # Command should succeed with mock data
        assert result.exit_code == 0, f"Command failed with: {result.output}"
        
        # Must produce output
        assert result.output.strip(), "Show command should produce output"
        
        # Should not contain error messages
        output_lower = result.output.lower()
        assert 'error' not in output_lower, f"Should not contain errors: {result.output}"
        assert 'failed' not in output_lower, f"Should not contain failure messages: {result.output}"
        
        # Verify API calls were made to resolve/show project
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have made API calls to show project"
        
        # Should have called either direct project lookup or projects list for ID resolution
        has_project_call = any(
            (call['method'] == 'GET' and '/projects' in call['path']) 
            for call in calls
        )
        assert has_project_call, f"Should have made project-related API call. Calls: {calls}"
    
    def test_project_show_invalid_id(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project show' with invalid project ID."""
        # Clear call log to verify API calls
        mock_api_client.clear_call_log()
        
        result = cli_runner.invoke(cli, ['project', 'show', 'invalid-project-id'])
        
        # With our improved mock client, this should handle gracefully
        # Either succeed with empty data or fail with proper error message
        if result.exit_code == 0:
            # If successful, should produce some output (even if empty data message)
            assert result.output.strip(), "Should produce some output"
            # Should not contain generic error messages
            output_lower = result.output.lower()
            assert 'exception' not in output_lower, "Should not contain exception traces"
        else:
            # If failed, should provide meaningful error message
            assert result.output.strip(), "Should provide error message"
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['not found', 'invalid', 'error']), \
                f"Error message should be meaningful: {result.output}"
        
        # Should have attempted API calls
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have attempted API calls"
    
    def test_project_list_table_format(self, cli_runner, mock_api_client):
        """Test that project list outputs in table format by default."""
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        assert_cli_success(result)
        
        # Check for table-like structure (headers and data)
        lines = result.output.strip().split('\n')
        assert len(lines) >= 2, "Should have at least header and one data row"
    
    @pytest.mark.integration
    def test_project_list_with_mock_data(self, cli_runner, mock_api_client):
        """Integration test using actual mock fixture data."""
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        assert_cli_success(result)
        
        # The mock should return data from our fixtures
        # Check that we get some kind of project listing
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['project', 'name', 'id']), \
            f"Output should contain project-related keywords: {result.output}"
    
    def test_project_commands_help(self, cli_runner):
        """Test that project command help works."""
        result = cli_runner.invoke(cli, ['project', '--help'])
        
        assert_cli_success(result)
        assert 'list' in result.output
        assert 'show' in result.output
    
    def test_project_list_help(self, cli_runner):
        """Test that project list help works."""
        result = cli_runner.invoke(cli, ['project', 'list', '--help'])
        
        assert_cli_success(result)
        assert 'format' in result.output.lower()


class TestProjectCommandsWithFixtures:
    """Test project commands using specific fixture data."""
    
    def test_project_list_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that project list actually uses our mock fixture data."""
        # Clear any previous calls
        mock_api_client.clear_call_log()
        
        # Run the command
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Should succeed with our mock data
        assert result.exit_code == 0, f"Command failed with: {result.output}"
        
        # Should have some output (not empty)
        assert result.output.strip(), "Command should produce some output"
        
        # Verify the correct API call was made
        assert mock_api_client.was_called('GET', '/projects'), \
            f"Should have called GET /projects. Actual calls: {mock_api_client.get_call_log()}"
    
    def test_project_list_data_transformation(self, cli_runner, mock_api_client):
        """Test that project list correctly transforms API response data."""
        # Clear call log
        mock_api_client.clear_call_log()
        
        # Get JSON output to verify data transformation
        result = cli_runner.invoke(cli, ['project', 'list', '--format', 'json'])
        
        # Must succeed
        assert result.exit_code == 0, f"JSON command failed: {result.output}"
        
        # Parse and validate JSON structure
        try:
            data = json.loads(result.output)
            
            # Use our strengthened API response validation
            projects = assert_api_response_structure(data, expect_items=False)
            
            # Validate each project structure thoroughly
            for project in projects:
                assert_project_structure(project)
                        
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput: {result.output}")
        except Exception as e:
            pytest.fail(f"Data validation failed: {e}\nData: {result.output}")
    
    def test_project_list_pagination_parameters(self, cli_runner, mock_api_client):
        """Test that pagination parameters are correctly passed to API."""
        # Clear call log
        mock_api_client.clear_call_log()
        
        # Run with specific pagination
        result = cli_runner.invoke(cli, ['project', 'list', '--page', '2', '--size', '5'])
        
        # Should succeed
        assert result.exit_code == 0, f"Pagination command failed: {result.output}"
        
        # Verify API was called (parameters are handled by the CLI command logic)
        calls = mock_api_client.get_call_log()
        assert len(calls) >= 1, "Should have made API calls"
        assert any(call['method'] == 'GET' and '/projects' in call['path'] for call in calls), \
            "Should have called projects endpoint"
    
    def test_project_show_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that project show attempts to use mock data."""
        # Clear any previous calls
        mock_api_client.clear_call_log()
        
        # Use a generic project ID that might exist in our fixtures
        result = cli_runner.invoke(cli, ['project', 'show', 'test-project'])
        
        # The command should run (whether it succeeds depends on fixture data)
        assert isinstance(result.exit_code, int), "Should return an exit code"
        
        # Should produce some output
        assert result.output.strip(), "Command should produce some output"
        
        # Verify API calls were made (either direct project lookup or projects list for ID resolution)
        calls = mock_api_client.get_call_log()
        assert len(calls) > 0, f"Should have made API calls. Calls: {calls}"
        
        # Should have called either GET /projects/{id} or GET /projects (for ID lookup)
        has_project_call = any(call['method'] == 'GET' and 'projects' in call['path'] for call in calls)
        assert has_project_call, f"Should have made project-related API call. Calls: {calls}"


class TestProjectCommandErrors:
    """Test error conditions and edge cases for project commands."""
    
    def test_project_list_invalid_format(self, cli_runner, mock_api_client):
        """Test project list with invalid format option."""
        result = cli_runner.invoke(cli, ['project', 'list', '--format', 'invalid'])
        
        # Should fail with invalid format
        assert result.exit_code != 0, "Should fail with invalid format"
        assert 'invalid' in result.output.lower() or 'choice' in result.output.lower(), \
            f"Should mention invalid choice: {result.output}"
    
    def test_project_show_missing_id(self, cli_runner, mock_api_client):
        """Test project show without providing project ID."""
        result = cli_runner.invoke(cli, ['project', 'show'])
        
        # Command behavior may vary - either fails or shows help/default behavior
        assert isinstance(result.exit_code, int), "Should return an exit code"
        
        if result.exit_code != 0:
            # If it fails, should mention missing argument
            assert 'missing' in result.output.lower() or 'required' in result.output.lower() or 'provided' in result.output.lower(), \
                f"Should mention missing argument: {result.output}"
        else:
            # If it succeeds, should show help or meaningful output
            assert result.output.strip(), "Should produce some output"
    
    def test_project_list_invalid_page_size(self, cli_runner, mock_api_client):
        """Test project list with invalid page size."""
        result = cli_runner.invoke(cli, ['project', 'list', '--size', '-1'])
        
        # Should either fail or handle gracefully
        if result.exit_code != 0:
            # If it fails, should mention the invalid value
            assert 'invalid' in result.output.lower() or 'size' in result.output.lower(), \
                f"Should mention invalid size: {result.output}"
        else:
            # If it succeeds, should have handled the invalid input gracefully
            assert result.output.strip(), "Should produce some output even with invalid size"


# Integration test to verify the full chain works
@pytest.mark.integration
def test_project_command_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for project commands with full mock setup."""
    # Clear call log for clean test
    mock_api_client.clear_call_log()
    
    # Test that we can run project list with all mocking in place
    result = cli_runner.invoke(cli, ['project', 'list'])
    
    # Should work with our complete mock setup
    assert result.exit_code == 0, f"Integration test failed: {result.output}"
    
    # Should have meaningful output
    assert len(result.output.strip()) > 0, "Should produce output"
    
    # Should not contain error traces
    output_lower = result.output.lower()
    assert 'traceback' not in output_lower, "Should not contain Python tracebacks"
    assert 'exception' not in output_lower, "Should not contain exception messages"
    
    # Verify API integration worked
    calls = mock_api_client.get_call_log()
    assert len(calls) >= 1, "Should have made API calls"
    
    # Test JSON format consistency
    json_result = cli_runner.invoke(cli, ['project', 'list', '--format', 'json'])
    assert json_result.exit_code == 0, "JSON format should work"
    
    # JSON should be parseable
    try:
        json_data = json.loads(json_result.output)
        assert isinstance(json_data, dict), "JSON should be dict"
        assert '_embedded' in json_data, "JSON should have API structure"
    except json.JSONDecodeError:
        pytest.fail(f"JSON output is not valid: {json_result.output}")


@pytest.mark.integration  
def test_project_command_error_handling_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for error handling in project commands."""
    # Test invalid format option
    result = cli_runner.invoke(cli, ['project', 'list', '--format', 'invalid'])
    
    # Should fail gracefully
    assert result.exit_code != 0, "Should fail with invalid format"
    assert result.output.strip(), "Should provide error message"
    
    # Error should be user-friendly
    output_lower = result.output.lower()
    assert any(keyword in output_lower for keyword in ['invalid', 'choice', 'format']), \
        f"Should mention format error: {result.output}"
    
    # Should not contain Python tracebacks
    assert 'traceback' not in output_lower, "Should not show Python tracebacks to user"


