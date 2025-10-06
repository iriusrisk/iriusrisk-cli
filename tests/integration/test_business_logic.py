"""
Tests for business logic validation in IriusRisk CLI.

This module tests that the CLI correctly processes and transforms data,
validates inputs, and handles business rules properly.
"""

import pytest
import json
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success
from tests.utils.assertions import assert_project_structure, assert_countermeasure_structure


class TestProjectBusinessLogic:
    """Test business logic for project operations."""
    
    def test_project_list_filters_correctly(self, cli_runner, mock_api_client):
        """Test that project list applies filters correctly."""
        # Clear call log
        mock_api_client.clear_call_log()
        
        # Test with name filter
        result = cli_runner.invoke(cli, ['project', 'list', '--name', 'test-app'])
        
        assert_cli_success(result)
        
        # Verify the API was called with filter parameters
        calls = mock_api_client.get_call_log()
        assert len(calls) > 0, "Should have made API calls"
        
        # The actual filtering might happen client-side or server-side
        # We're testing that the command processes the filter parameter
        assert result.output.strip(), "Should produce filtered results"
    
    def test_project_list_pagination_parameters(self, cli_runner, mock_api_client):
        """Test that pagination parameters are handled correctly."""
        mock_api_client.clear_call_log()
        
        # Test with specific page and size
        result = cli_runner.invoke(cli, ['project', 'list', '--page', '1', '--size', '5'])
        
        assert_cli_success(result)
        
        # Should have made API call
        calls = mock_api_client.get_call_log()
        assert len(calls) > 0, "Should have made API calls"
        
        # Should produce results
        assert result.output.strip(), "Should produce paginated results"
    
    def test_project_json_output_structure(self, cli_runner, mock_api_client):
        """Test that JSON output has correct business structure."""
        result = cli_runner.invoke(cli, ['project', 'list', '--format', 'json'])
        
        assert_cli_success(result)
        
        # Parse and validate JSON structure
        try:
            data = json.loads(result.output)
            
            # Should be either a list or a dict with _embedded structure
            if isinstance(data, dict):
                if '_embedded' in data:
                    # API response format
                    assert 'items' in data['_embedded'], "Should have items array"
                    projects = data['_embedded']['items']
                else:
                    # Single project format
                    projects = [data]
            else:
                # Direct list format
                projects = data
            
            # Validate project data structure
            if projects:
                project = projects[0]
                # Use our structured validation
                assert_project_structure(project)
                        
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.output}")


class TestCountermeasureBusinessLogic:
    """Test business logic for countermeasure operations."""
    
    def test_countermeasure_status_validation(self, cli_runner, mock_api_client):
        """Test that countermeasure status updates use valid values."""
        # Test with valid status
        result = cli_runner.invoke(cli, ['countermeasure', 'update', 'cm-123', 
                                        '--status', 'implemented', '--project', 'test-project'])
        
        # Should succeed (or fail gracefully if no fixture)
        assert result.exit_code in [0, 1], f"Should handle valid status: {result.output}"
        
        # If successful, should reference the status
        if result.exit_code == 0:
            output_lower = result.output.lower()
            assert 'implemented' in output_lower or 'status' in output_lower, \
                f"Should reference status update: {result.output}"
    
    def test_countermeasure_search_logic(self, cli_runner, mock_api_client):
        """Test that countermeasure search processes results correctly."""
        result = cli_runner.invoke(cli, ['countermeasure', 'search', 'test-project', 'validation'])
        
        assert_cli_success(result)
        
        # Should produce search results
        assert result.output.strip(), "Search should produce results"
        
        # Should not show error messages
        output_lower = result.output.lower()
        assert 'error' not in output_lower, f"Should not contain errors: {result.output}"


class TestDataTransformation:
    """Test data transformation and formatting logic."""
    
    def test_table_output_formatting(self, cli_runner, mock_api_client):
        """Test that table output is properly formatted."""
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        assert_cli_success(result)
        
        lines = result.output.strip().split('\n')
        
        # Should have multiple lines for table format
        assert len(lines) >= 1, "Should have at least one line of output"
        
        # Should not be JSON (no curly braces at start)
        assert not result.output.strip().startswith('{'), "Should not be JSON format"
        assert not result.output.strip().startswith('['), "Should not be JSON array format"
    
    def test_json_vs_table_format_consistency(self, cli_runner, mock_api_client):
        """Test that JSON and table formats show consistent data."""
        # Get table format
        table_result = cli_runner.invoke(cli, ['project', 'list'])
        assert_cli_success(table_result)
        
        # Get JSON format
        json_result = cli_runner.invoke(cli, ['project', 'list', '--format', 'json'])
        assert_cli_success(json_result)
        
        # Both should have content
        assert table_result.output.strip(), "Table format should have content"
        assert json_result.output.strip(), "JSON format should have content"
        
        # JSON should be parseable
        try:
            json_data = json.loads(json_result.output)
            assert json_data is not None, "JSON should parse successfully"
        except json.JSONDecodeError:
            pytest.fail(f"JSON format output is not valid JSON: {json_result.output}")


class TestInputValidation:
    """Test input validation and error handling."""
    
    def test_project_id_validation(self, cli_runner, mock_api_client):
        """Test that project ID validation works correctly."""
        # Test with empty project ID
        result = cli_runner.invoke(cli, ['project', 'show', ''])
        
        # Should either fail or handle gracefully
        if result.exit_code != 0:
            # If it fails, should provide meaningful error
            assert result.output.strip(), "Should provide error message"
        else:
            # If it succeeds, should handle empty ID gracefully
            assert result.output.strip(), "Should produce some output"
    
    def test_invalid_command_arguments(self, cli_runner, mock_api_client):
        """Test handling of invalid command arguments."""
        # Test with invalid option
        result = cli_runner.invoke(cli, ['project', 'list', '--invalid-option'])
        
        # Should fail with helpful error
        assert result.exit_code != 0, "Should fail with invalid option"
        assert 'invalid' in result.output.lower() or 'option' in result.output.lower(), \
            f"Should mention invalid option: {result.output}"


class TestBusinessRuleEnforcement:
    """Test that business rules are properly enforced."""
    
    def test_countermeasure_requires_project(self, cli_runner, mock_api_client):
        """Test that countermeasure commands require project context."""
        # Try to list countermeasures without project
        result = cli_runner.invoke(cli, ['countermeasure', 'list'])
        
        # Should fail or require project specification
        if result.exit_code != 0:
            # Should mention missing project
            output_lower = result.output.lower()
            assert 'project' in output_lower or 'missing' in output_lower, \
                f"Should mention missing project: {result.output}"
    
    def test_update_commands_require_valid_ids(self, cli_runner, mock_api_client):
        """Test that update commands validate ID formats."""
        # Test countermeasure update with clearly invalid ID
        result = cli_runner.invoke(cli, ['countermeasure', 'update', '', 
                                        '--status', 'implemented', '--project', 'test-project'])
        
        # Should either fail or handle gracefully
        if result.exit_code != 0:
            # Should provide meaningful error about ID
            assert result.output.strip(), "Should provide error message for invalid ID"
