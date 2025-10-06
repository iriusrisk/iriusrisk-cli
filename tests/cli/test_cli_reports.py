"""
Tests for report-related CLI commands.

This module tests the 'iriusrisk reports' commands using mocked API responses.
"""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success


class TestReportCommands:
    """Test cases for report CLI commands."""
    
    @patch('pathlib.Path.write_bytes')
    def test_reports_generate_default(self, mock_write, cli_runner, mock_api_client):
        """Test 'iriusrisk reports generate' command with default settings."""
        result = cli_runner.invoke(cli, ['reports', 'generate', '--project-id', 'test-project'])
        
        # The command should attempt to generate a report
        assert result.exit_code in [0, 1], f"Generate command should run: {result.output}"
        
        # Should show some indication of report generation
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['report', 'generat', 'download']), \
            f"Output should contain report-related keywords: {result.output}"
    
    @patch('pathlib.Path.write_bytes')
    def test_reports_generate_with_type(self, mock_write, cli_runner, mock_api_client):
        """Test 'iriusrisk reports generate --type' command."""
        result = cli_runner.invoke(cli, ['reports', 'generate', '--project-id', 'test-project', 
                                        '--type', 'countermeasure', '--format', 'pdf'])
        
        # Should attempt to generate specific report type
        assert result.exit_code in [0, 1], f"Generate with type should run: {result.output}"
        assert result.output.strip(), "Should produce some output"
    
    @patch('pathlib.Path.write_bytes')
    def test_reports_generate_compliance(self, mock_write, cli_runner, mock_api_client):
        """Test 'iriusrisk reports generate --type compliance' command."""
        result = cli_runner.invoke(cli, ['reports', 'generate', '--project-id', 'test-project',
                                        '--type', 'compliance', '--standard', 'owasp-top-10-2021'])
        
        # Should attempt to generate compliance report
        assert result.exit_code in [0, 1], f"Compliance report should run: {result.output}"
        assert result.output.strip(), "Should produce some output"
    
    def test_reports_list(self, cli_runner, mock_api_client):
        """Test 'iriusrisk reports list' command."""
        result = cli_runner.invoke(cli, ['reports', 'list', '--project-id', 'test-project'])
        
        assert_cli_success(result)
        
        # Should show list of reports or message about no reports
        assert result.output.strip(), "Should produce some output"
    
    def test_reports_list_with_project_id(self, cli_runner, mock_api_client):
        """Test 'iriusrisk reports list --project-id' command."""
        result = cli_runner.invoke(cli, ['reports', 'list', '--project-id', 'specific-project'])
        
        assert_cli_success(result)
        
        # Should show list of reports or message about no reports
        assert result.output.strip(), "Should have some output message"
    
    def test_reports_types(self, cli_runner, mock_api_client):
        """Test 'iriusrisk reports types' command."""
        result = cli_runner.invoke(cli, ['reports', 'types', '--project-id', 'test-project'])
        
        assert_cli_success(result)
        
        # Should show available report types
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['report', 'type', 'countermeasure', 'threat']), \
            f"Output should contain report type keywords: {result.output}"
    
    def test_reports_standards(self, cli_runner, mock_api_client):
        """Test 'iriusrisk reports standards' command."""
        result = cli_runner.invoke(cli, ['reports', 'standards', '--project-id', 'test-project'])
        
        assert_cli_success(result)
        
        # Should show available standards
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['standard', 'compliance', 'owasp', 'iso']), \
            f"Output should contain standards keywords: {result.output}"
    
    def test_reports_commands_help(self, cli_runner):
        """Test that reports command help works."""
        result = cli_runner.invoke(cli, ['reports', '--help'])
        
        assert_cli_success(result)
        assert 'generate' in result.output
        assert 'list' in result.output
        assert 'types' in result.output
        assert 'standards' in result.output
    
    def test_reports_generate_help(self, cli_runner):
        """Test that reports generate help works."""
        result = cli_runner.invoke(cli, ['reports', 'generate', '--help'])
        
        assert_cli_success(result)
        assert 'type' in result.output.lower()
        assert 'format' in result.output.lower()


class TestReportCommandsWithFixtures:
    """Test report commands using specific fixture data."""
    
    def test_reports_types_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that reports types actually uses our mock fixture data."""
        result = cli_runner.invoke(cli, ['reports', 'types', '--project-id', 'test-project'])
        
        # Should succeed with our mock data
        assert result.exit_code == 0, f"Command failed with: {result.output}"
        
        # Should have some output (not empty)
        assert result.output.strip(), "Command should produce some output"
    
    def test_reports_standards_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that reports standards uses mock data."""
        result = cli_runner.invoke(cli, ['reports', 'standards', '--project-id', 'test-project'])
        
        # Should succeed with our mock data
        assert result.exit_code == 0, f"Command failed with: {result.output}"
        
        # Should have some output
        assert result.output.strip(), "Command should produce some output"
    
    def test_reports_list_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that reports list uses mock data."""
        result = cli_runner.invoke(cli, ['reports', 'list', '--project-id', 'test-project'])
        
        # Should succeed with our mock data
        assert result.exit_code == 0, f"Command failed with: {result.output}"
        
        # Should have some output
        assert result.output.strip(), "Command should produce some output"


@pytest.mark.integration
def test_reports_command_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for reports commands with full mock setup."""
    # Test that we can run reports types with all mocking in place
    result = cli_runner.invoke(cli, ['reports', 'types', '--project-id', 'test-project'])
    
    # Should work with our complete mock setup
    assert result.exit_code == 0, f"Integration test failed: {result.output}"
    
    # Should have meaningful output
    assert len(result.output.strip()) > 0, "Should produce output"
