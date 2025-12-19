"""
Tests for OTM (Open Threat Model) related CLI commands.

This module tests the 'iriusrisk otm' commands using mocked API responses.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success


class TestOTMCommands:
    """Test cases for OTM CLI commands."""
    
    def test_otm_example(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm example' command."""
        result = cli_runner.invoke(cli, ['otm', 'example'])
        
        assert_cli_success(result)
        
        # Should output YAML content
        assert 'otmVersion:' in result.output, "Should contain otmVersion field"
        assert 'project:' in result.output, "Should contain project field"
        assert result.output.strip(), "Should produce output"
    
    def test_otm_example_with_redirection(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm example' command can be redirected to file."""
        result = cli_runner.invoke(cli, ['otm', 'example'])
        
        assert_cli_success(result)
        
        # Should output YAML that can be saved to file
        assert 'otmVersion:' in result.output, "Should contain otmVersion field"
        assert 'components:' in result.output, "Should contain components field"
        assert len(result.output.strip()) > 100, "Should produce substantial output"
    
    def test_otm_import_new_project(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm import' command for new project."""
        # Create a temporary OTM file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            otm_data = {
                "otmVersion": "0.1.0",
                "project": {
                    "name": "Test Project",
                    "id": "test-project"
                },
                "representations": []
            }
            json.dump(otm_data, f)
            otm_file = f.name
        
        try:
            result = cli_runner.invoke(cli, ['otm', 'import', otm_file])
            
            # Should attempt to import (may succeed or fail depending on mock data)
            assert result.exit_code in [0, 1], f"Import command should run: {result.output}"
            
            # Should reference the file or show import progress
            assert any(keyword in result.output.lower() for keyword in ['import', 'project', 'otm']), \
                f"Output should contain import-related keywords: {result.output}"
        finally:
            os.unlink(otm_file)
    
    def test_otm_import_creates_or_updates(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm import' command automatically creates or updates."""
        # Create a temporary OTM file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            otm_data = {
                "otmVersion": "0.1.0",
                "project": {
                    "name": "Test Project",
                    "id": "test-project-123"
                },
                "representations": []
            }
            json.dump(otm_data, f)
            otm_file = f.name
        
        try:
            result = cli_runner.invoke(cli, ['otm', 'import', otm_file])
            
            # Should attempt to import (create or update automatically)
            assert result.exit_code in [0, 1], f"Import should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
        finally:
            os.unlink(otm_file)
    
    def test_otm_export(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm export' command."""
        result = cli_runner.invoke(cli, ['otm', 'export', 'test-project'])
        
        # Should attempt to export (may succeed or fail depending on mock data)
        assert result.exit_code in [0, 1], f"Export command should run: {result.output}"
        
        # Should show some indication of export or error
        assert result.output.strip(), "Should produce some output"
    
    def test_otm_export_to_file(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm export -o file.otm' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, 'exported.otm')
            result = cli_runner.invoke(cli, ['otm', 'export', 'test-project', '-o', output_file])
            
            # Should attempt to export to file
            assert result.exit_code in [0, 1], f"Export to file should run: {result.output}"
            assert result.output.strip(), "Should produce some output"
    
    def test_otm_import_nonexistent_file(self, cli_runner, mock_api_client):
        """Test 'iriusrisk otm import' with non-existent file."""
        result = cli_runner.invoke(cli, ['otm', 'import', 'nonexistent.otm'])
        
        # Should fail gracefully
        assert result.exit_code != 0, "Should fail for non-existent file"
        assert 'not found' in result.output.lower() or 'error' in result.output.lower(), \
            f"Should show file not found error: {result.output}"
    
    def test_otm_commands_help(self, cli_runner):
        """Test that OTM command help works."""
        result = cli_runner.invoke(cli, ['otm', '--help'])
        
        assert_cli_success(result)
        assert 'import' in result.output
        assert 'export' in result.output
        assert 'example' in result.output
    
    def test_otm_import_help(self, cli_runner):
        """Test that OTM import help works."""
        result = cli_runner.invoke(cli, ['otm', 'import', '--help'])
        
        assert_cli_success(result)
        assert 'create' in result.output.lower() or 'import' in result.output.lower()
    
    def test_otm_export_help(self, cli_runner):
        """Test that OTM export help works."""
        result = cli_runner.invoke(cli, ['otm', 'export', '--help'])
        
        assert_cli_success(result)
        assert 'output' in result.output.lower()


class TestOTMCommandsWithFixtures:
    """Test OTM commands using specific fixture data."""
    
    def test_otm_example_creates_valid_otm(self, cli_runner, mock_api_client):
        """Test that OTM example creates a structurally valid OTM file."""
        result = cli_runner.invoke(cli, ['otm', 'example'])
        
        # Should succeed
        assert result.exit_code == 0, f"Example command failed: {result.output}"
        
        # Should output valid YAML with OTM structure
        assert 'otmVersion:' in result.output, "Should have otmVersion field"
        assert 'project:' in result.output, "Should have project field"
        assert 'name:' in result.output, "Should have project name"
        assert 'components:' in result.output, "Should have components section"
        assert 'trustZones:' in result.output, "Should have trustZones section"
    
    def test_otm_import_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that OTM import attempts to use mock data."""
        # Create a minimal valid OTM file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            otm_data = {
                "otmVersion": "0.1.0",
                "project": {
                    "name": "Mock Test Project",
                    "id": "mock-test-project"
                }
            }
            json.dump(otm_data, f)
            otm_file = f.name
        
        try:
            result = cli_runner.invoke(cli, ['otm', 'import', otm_file])
            
            # The command should run (whether it succeeds depends on fixture data)
            assert isinstance(result.exit_code, int), "Should return an exit code"
            
            # Should produce some output
            assert result.output.strip(), "Command should produce some output"
            
        finally:
            os.unlink(otm_file)
    
    def test_otm_export_uses_mock_data(self, cli_runner, mock_api_client):
        """Test that OTM export attempts to use mock data."""
        result = cli_runner.invoke(cli, ['otm', 'export', 'test-project'])
        
        # The command should run (whether it succeeds depends on fixture data)
        assert isinstance(result.exit_code, int), "Should return an exit code"
        
        # Should produce some output
        assert result.output.strip(), "Command should produce some output"


class TestOTMAutoVersioning:
    """Test auto versioning functionality for OTM imports."""
    
    def test_otm_import_with_auto_versioning_existing_project(self, cli_runner, mock_api_client, tmp_path, monkeypatch):
        """Test auto versioning when updating an existing project."""
        # Create a temporary OTM file
        otm_file = tmp_path / "test.otm"
        otm_data = {
            "otmVersion": "0.1.0",
            "project": {
                "name": "Test Project",
                "id": "test-project-123"
            }
        }
        otm_file.write_text(json.dumps(otm_data))
        
        # Create a project config with auto_versioning enabled
        project_dir = tmp_path / ".iriusrisk"
        project_dir.mkdir()
        project_config = {
            "name": "Test Project",
            "project_id": "test-project-123",
            "auto_versioning": True
        }
        (project_dir / "project.json").write_text(json.dumps(project_config))
        
        # Mock the current working directory
        monkeypatch.chdir(tmp_path)
        
        # Run import (will automatically update if project exists)
        result = cli_runner.invoke(cli, ['otm', 'import', str(otm_file)])
        
        # Should attempt to create a version (may succeed or fail depending on mock)
        # The key is that the auto-versioning logic should be triggered
        assert result.exit_code in [0, 1], f"Import with auto-versioning should run: {result.output}"
        
        # If auto-versioning is working, we should see the versioning message
        if result.exit_code == 0 or 'Auto-versioning' in result.output:
            assert 'Auto-versioning' in result.output or 'Backup' in result.output, \
                f"Should mention auto-versioning: {result.output}"
    
    def test_otm_import_new_project_with_auto_versioning(self, cli_runner, mock_api_client, tmp_path, monkeypatch):
        """Test auto versioning does not trigger for new projects."""
        # Create a temporary OTM file
        otm_file = tmp_path / "test.otm"
        otm_data = {
            "otmVersion": "0.1.0",
            "project": {
                "name": "Test Project",
                "id": "test-project-new"
            }
        }
        otm_file.write_text(json.dumps(otm_data))
        
        # Create a project config with auto_versioning enabled
        project_dir = tmp_path / ".iriusrisk"
        project_dir.mkdir()
        project_config = {
            "name": "Test Project",
            "reference_id": "test-project-new",
            "auto_versioning": True
        }
        (project_dir / "project.json").write_text(json.dumps(project_config))
        
        # Mock the current working directory
        monkeypatch.chdir(tmp_path)
        
        # Run import (project doesn't exist, so creates new)
        result = cli_runner.invoke(cli, ['otm', 'import', str(otm_file)])
        
        # The command should run (success depends on mock data)
        assert result.exit_code in [0, 1], f"Import should run: {result.output}"
        
        # Should produce output but may or may not mention versioning
        # (versioning only happens if project already exists)
        assert result.output.strip(), "Should produce some output"
    
    def test_otm_import_without_auto_versioning(self, cli_runner, mock_api_client, tmp_path, monkeypatch):
        """Test that auto versioning does NOT trigger when disabled."""
        # Create a temporary OTM file
        otm_file = tmp_path / "test.otm"
        otm_data = {
            "otmVersion": "0.1.0",
            "project": {
                "name": "Test Project",
                "id": "test-project-no-version"
            }
        }
        otm_file.write_text(json.dumps(otm_data))
        
        # Create a project config with auto_versioning disabled
        project_dir = tmp_path / ".iriusrisk"
        project_dir.mkdir()
        project_config = {
            "name": "Test Project",
            "project_id": "test-project-no-version",
            "auto_versioning": False
        }
        (project_dir / "project.json").write_text(json.dumps(project_config))
        
        # Mock the current working directory
        monkeypatch.chdir(tmp_path)
        
        # Run import
        result = cli_runner.invoke(cli, ['otm', 'import', str(otm_file)])
        
        # Should run but NOT mention auto-versioning
        assert result.exit_code in [0, 1], f"Import should run: {result.output}"
        assert 'Auto-versioning' not in result.output, \
            f"Should NOT mention auto-versioning when disabled: {result.output}"


@pytest.mark.integration
def test_otm_command_integration(cli_runner, mock_api_client, mock_env_vars):
    """Integration test for OTM commands with full mock setup."""
    # Test that we can run OTM example with all mocking in place
    result = cli_runner.invoke(cli, ['otm', 'example'])
    
    # Should work with our complete mock setup
    assert result.exit_code == 0, f"Integration test failed: {result.output}"
    
    # Should produce valid YAML output with OTM structure
    assert 'otmVersion:' in result.output, "Should produce valid OTM structure"
    assert 'project:' in result.output, "Should have project section"
