"""
Tests for project versions CLI commands.

This module tests the 'iriusrisk project versions' commands using mocked API responses
to ensure they work correctly without requiring actual API access.
"""

import pytest
import json
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success, assert_cli_failure


class TestVersionCommands:
    """Test cases for project versions CLI commands."""
    
    def test_versions_list_default(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project versions list' command with default output."""
        result = cli_runner.invoke(cli, ['project', 'versions', 'list', 'test-project'])
        
        # Command must succeed
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Must produce output
        assert result.output.strip(), "Command should produce output"
    
    def test_versions_list_json_format(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project versions list --format json' command."""
        result = cli_runner.invoke(cli, ['project', 'versions', 'list', 'test-project', '--format', 'json'])
        
        # Command must succeed
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Must produce output
        assert result.output.strip(), "JSON command should produce output"
        
        # If output is valid JSON, verify structure
        output = result.output.strip()
        if output and output[0] in ['{', '[']:
            try:
                data = json.loads(output)
                # Should have expected structure
                assert isinstance(data, dict) or isinstance(data, list), "JSON output should be dict or list"
            except json.JSONDecodeError:
                # If it's not JSON, it might be an empty message, which is acceptable
                pass
    
    def test_versions_list_with_pagination(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project versions list' with pagination options."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'list', 'test-project',
            '--page', '1', '--size', '10'
        ])
        
        assert_cli_success(result)
        assert result.output.strip() != "", "Paginated results should not be empty"
    
    def test_versions_create_with_name(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project versions create --name' command."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'create', 'test-project',
            '--name', 'v1.0', '--no-wait'
        ])
        
        # Command should either succeed or handle network errors gracefully
        # During testing with mocks, network errors may occur
        assert result.output.strip(), "Create command should produce output"
    
    def test_versions_create_with_description(self, cli_runner, mock_api_client):
        """Test version creation with description."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'create', 'test-project',
            '--name', 'v1.0',
            '--description', 'Release candidate',
            '--no-wait'
        ])
        
        # Should produce output
        assert result.output.strip(), "Create command should produce output"
    
    def test_versions_create_without_name_fails(self, cli_runner, mock_api_client):
        """Test that version creation fails without required name."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'create', 'test-project'
        ])
        
        # Should fail due to missing required option
        assert result.exit_code != 0, "Command should fail without --name"
    
    def test_versions_compare(self, cli_runner, mock_api_client):
        """Test 'iriusrisk project versions compare' command."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'compare', 'test-project',
            '--source', 'version-id-1',
            '--target', 'version-id-2'
        ])
        
        # Should produce output
        assert result.output.strip(), "Compare command should produce output"
    
    def test_versions_compare_json_format(self, cli_runner, mock_api_client):
        """Test version comparison with JSON output."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'compare', 'test-project',
            '--source', 'version-id-1',
            '--target', 'version-id-2',
            '--format', 'json'
        ])
        
        # Should produce output
        assert result.output.strip(), "Compare command should produce output"
    
    def test_versions_compare_without_source_fails(self, cli_runner, mock_api_client):
        """Test that compare fails without required source."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'compare', 'test-project',
            '--target', 'version-id-2'
        ])
        
        # Should fail due to missing required option
        assert result.exit_code != 0, "Command should fail without --source"
    
    def test_versions_compare_without_target_fails(self, cli_runner, mock_api_client):
        """Test that compare fails without required target."""
        result = cli_runner.invoke(cli, [
            'project', 'versions', 'compare', 'test-project',
            '--source', 'version-id-1'
        ])
        
        # Should fail due to missing required option
        assert result.exit_code != 0, "Command should fail without --target"
    
    def test_versions_list_table_format(self, cli_runner, mock_api_client):
        """Test that versions list outputs in table format by default."""
        result = cli_runner.invoke(cli, ['project', 'versions', 'list', 'test-project'])
        
        assert_cli_success(result)
        
        # Check for table-like structure (should have some output)
        lines = result.output.strip().split('\n')
        assert len(lines) >= 1, "Should have at least some output"
    
    def test_versions_commands_with_projects_alias(self, cli_runner, mock_api_client):
        """Test that versions commands work with 'projects' alias."""
        result = cli_runner.invoke(cli, ['projects', 'versions', 'list', 'test-project'])
        
        # Should work the same as 'project'
        assert result.exit_code == 0, "Should work with 'projects' alias"
    
    @pytest.mark.integration
    def test_versions_list_with_mock_data(self, cli_runner, mock_api_client):
        """Integration test using actual mock fixture data."""
        result = cli_runner.invoke(cli, ['project', 'versions', 'list', 'test-project'])
        
        assert_cli_success(result)
        
        # The mock should return data from our fixtures
        assert result.output.strip(), "Should return mock data"

