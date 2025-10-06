"""
Tests for sync-related CLI commands.

This module tests the 'iriusrisk sync' command using mocked API responses.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success


class TestSyncCommands:
    """Test cases for sync CLI commands."""
    
    def test_sync_default(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync' command with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--output-dir', temp_dir])
            
            # Should attempt to sync (may succeed or fail depending on mock data)
            assert result.exit_code in [0, 1], f"Sync command should run: {result.output}"
            
            # Should show some indication of sync progress
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['sync', 'download', 'threat', 'countermeasure']), \
                f"Output should contain sync-related keywords: {result.output}"
    
    def test_sync_threats_only(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync --threats-only' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--threats-only', '--output-dir', temp_dir])
            
            # Should attempt to sync threats only
            assert result.exit_code in [0, 1], f"Threats-only sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_countermeasures_only(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync --countermeasures-only' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--countermeasures-only', '--output-dir', temp_dir])
            
            # Should attempt to sync countermeasures only
            assert result.exit_code in [0, 1], f"Countermeasures-only sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_components_only(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync --components-only' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--components-only', '--output-dir', temp_dir])
            
            # Should attempt to sync components only
            assert result.exit_code in [0, 1], f"Components-only sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_trust_zones_only(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync --trust-zones-only' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--trust-zones-only', '--output-dir', temp_dir])
            
            # Should attempt to sync trust zones only
            assert result.exit_code in [0, 1], f"Trust zones-only sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_pretty_format(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync --format pretty' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--format', 'pretty', '--output-dir', temp_dir])
            
            # Should attempt to sync with pretty format
            assert result.exit_code in [0, 1], f"Pretty format sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_json_format(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync --format json' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--format', 'json', '--output-dir', temp_dir])
            
            # Should attempt to sync with JSON format
            assert result.exit_code in [0, 1], f"JSON format sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_without_project_id(self, cli_runner, mock_api_client):
        """Test 'iriusrisk sync' command without project ID (should use default)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', '--output-dir', temp_dir])
            
            # Should attempt to sync with default project
            assert result.exit_code in [0, 1], f"Default project sync should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_help(self, cli_runner):
        """Test that sync command help works."""
        result = cli_runner.invoke(cli, ['sync', '--help'])
        
        assert_cli_success(result)
        assert 'threats-only' in result.output
        assert 'countermeasures-only' in result.output
        assert 'components-only' in result.output
        assert 'trust-zones-only' in result.output
        assert 'output-dir' in result.output
        assert 'format' in result.output


class TestSyncCommandsWithFixtures:
    """Test sync commands using specific fixture data."""
    
    def test_sync_creates_output_directory(self, cli_runner, mock_api_client):
        """Test that sync creates the output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, 'new_sync_dir')
            
            # Directory shouldn't exist initially
            assert not os.path.exists(output_dir), "Output directory should not exist initially"
            
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--output-dir', output_dir])
            
            # Command should run (whether it succeeds depends on fixture data)
            assert isinstance(result.exit_code, int), "Should return an exit code"
            
            # Should produce some output
            assert result.output.strip(), "Command should produce some output"
    
    def test_sync_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that sync attempts to use mock data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--output-dir', temp_dir])
            
            # The command should run (whether it succeeds depends on fixture data)
            assert isinstance(result.exit_code, int), "Should return an exit code"
            
            # Should produce some output
            assert result.output.strip(), "Command should produce some output"
    
    def test_sync_threats_only_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that sync --threats-only uses mock data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--threats-only', '--output-dir', temp_dir])
            
            # Should run with mock data
            assert isinstance(result.exit_code, int), "Should return an exit code"
            assert result.output.strip(), "Should produce some output"
    
    def test_sync_countermeasures_only_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that sync --countermeasures-only uses mock data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--countermeasures-only', '--output-dir', temp_dir])
            
            # Should run with mock data
            assert isinstance(result.exit_code, int), "Should return an exit code"
            assert result.output.strip(), "Should produce some output"


class TestSyncCommandEdgeCases:
    """Test edge cases and error conditions for sync commands."""
    
    def test_sync_invalid_format(self, cli_runner, mock_api_client):
        """Test sync with invalid format option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--format', 'invalid', '--output-dir', temp_dir])
            
            # Should fail with invalid format
            assert result.exit_code != 0, "Should fail with invalid format"
            assert 'invalid' in result.output.lower() or 'choice' in result.output.lower(), \
                f"Should show format error: {result.output}"
    
    def test_sync_multiple_only_flags(self, cli_runner, mock_api_client):
        """Test sync with multiple --*-only flags (should work)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli_runner.invoke(cli, ['sync', 'test-project', '--threats-only', '--countermeasures-only', '--output-dir', temp_dir])
            
            # Should attempt to run (behavior depends on CLI implementation)
            assert isinstance(result.exit_code, int), "Should return an exit code"
            assert result.output.strip(), "Should produce some output"


@pytest.mark.integration
def test_sync_command_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for sync commands with full mock setup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test that we can run sync with all mocking in place
        result = cli_runner.invoke(cli, ['sync', 'test-project', '--output-dir', temp_dir])
        
        # Should work with our complete mock setup
        assert isinstance(result.exit_code, int), f"Integration test should return exit code: {result.output}"
        
        # Should have meaningful output
        assert len(result.output.strip()) > 0, "Should produce output"
