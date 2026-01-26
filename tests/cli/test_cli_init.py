"""
Tests for init CLI command.

This module tests the 'iriusrisk init' command using mocked API responses
to ensure it works correctly without requiring actual API access.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from iriusrisk_cli.main import cli
from iriusrisk_cli.commands.init import _generate_reference_id
from tests.utils.assertions import assert_cli_success, assert_cli_failure


class TestInitCommand:
    """Test cases for init CLI command."""
    
    def test_init_new_project_interactive(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init' with interactive project name input."""
        # Change to temporary directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Provide input for project name and empty scope (press Enter)
            result = cli_runner.invoke(cli, ['init'], input='My Test Project\n\n')
            
            # Command must succeed
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            
            # Check output messages
            assert "My Test Project" in result.output
            assert "Generated reference ID:" in result.output
            assert "✅ Initialized new IriusRisk project" in result.output
            
            # Check that .iriusrisk directory was created
            irius_dir = tmp_path / ".iriusrisk"
            assert irius_dir.exists(), ".iriusrisk directory should be created"
            
            # Check that project.json was created with correct content
            project_file = irius_dir / "project.json"
            assert project_file.exists(), "project.json should be created"
            
            with open(project_file) as f:
                config = json.load(f)
            
            assert config["name"] == "My Test Project"
            assert "reference_id" in config
            assert config["initialized_from"] == "new_project"
            assert "my-test-project-" in config["reference_id"]
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_new_project_with_name(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init --name' command."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Provide empty input to skip scope prompt
            result = cli_runner.invoke(cli, ['init', '--name', 'Web Application'], input='\n')
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "Web Application" in result.output
            assert "✅ Initialized new IriusRisk project" in result.output
            
            # Check project.json content
            project_file = tmp_path / ".iriusrisk" / "project.json"
            with open(project_file) as f:
                config = json.load(f)
            
            assert config["name"] == "Web Application"
            assert "web-application-" in config["reference_id"]
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_new_project_with_name_and_ref(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init --name --project-ref' command."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Provide empty input to skip scope prompt
            result = cli_runner.invoke(cli, ['init', '--name', 'API Service', '--project-ref', 'api-service-123'], input='\n')
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "API Service" in result.output
            
            # Check project.json content
            project_file = tmp_path / ".iriusrisk" / "project.json"
            with open(project_file) as f:
                config = json.load(f)
            
            assert config["name"] == "API Service"
            assert config["reference_id"] == "api-service-123"
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_existing_project(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init --existing-ref' command."""
        # Mock API response for existing project
        mock_project_data = {
            "_embedded": {
                "items": [{
                    "id": "proj-uuid-123",
                    "name": "Existing Project",
                    "referenceId": "existing-ref",
                    "description": "An existing project",
                    "state": "active",
                    "tags": ["production"],
                    "isArchived": False,
                    "isBlueprint": False,
                    "workflowState": {"name": "in-progress"},
                    "version": {"number": "1.0"},
                    "modelUpdated": "2024-01-01T00:00:00Z"
                }]
            }
        }
        
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Mock the Container and ProjectService
            with patch('iriusrisk_cli.commands.init.get_container') as mock_container:
                mock_service = MagicMock()
                mock_service.list_projects.return_value = {
                    'projects': mock_project_data['_embedded']['items'],
                    'page_info': {},
                    'full_response': mock_project_data
                }
                mock_container.return_value.get.return_value = mock_service
                
                # Provide empty input to skip scope prompt
                result = cli_runner.invoke(cli, ['init', '--existing-ref', 'existing-ref'], input='\n')
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "Existing Project" in result.output
            assert "✅ Initialized existing IriusRisk project" in result.output
            assert "proj-uuid-123" in result.output
            
            # Verify service was called with correct filter
            mock_service.list_projects.assert_called_with(
                page=0, 
                size=1, 
                custom_filter="'referenceId'='existing-ref'"
            )
            
            # Check project.json content
            project_file = tmp_path / ".iriusrisk" / "project.json"
            with open(project_file) as f:
                config = json.load(f)
            
            assert config["name"] == "Existing Project"
            assert config["project_id"] == "proj-uuid-123"
            assert config["reference_id"] == "existing-ref"
            assert config["initialized_from"] == "existing_project"
            assert config["metadata"]["tags"] == ["production"]
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_existing_project_not_found(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init --existing-ref' with non-existent project."""
        # Mock API response for no projects found
        mock_project_data = {"_embedded": {"items": []}}
        
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Mock the Container and ProjectService
            with patch('iriusrisk_cli.commands.init.get_container') as mock_container:
                mock_service = MagicMock()
                mock_service.list_projects.return_value = {
                    'projects': [],
                    'page_info': {},
                    'full_response': mock_project_data
                }
                mock_container.return_value.get.return_value = mock_service
                
                result = cli_runner.invoke(cli, ['init', '--existing-ref', 'non-existent'])
            
            assert result.exit_code != 0, "Command should fail for non-existent project"
            assert "No project found with reference ID 'non-existent'" in result.output
            
            # Should not create .iriusrisk directory
            irius_dir = tmp_path / ".iriusrisk"
            assert not irius_dir.exists(), ".iriusrisk directory should not be created"
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_directory_already_exists(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init' when .iriusrisk directory already exists."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create existing .iriusrisk directory
            irius_dir = tmp_path / ".iriusrisk"
            irius_dir.mkdir()
            
            result = cli_runner.invoke(cli, ['init', '--name', 'Test Project'])
            
            assert result.exit_code != 0, "Command should fail when directory exists"
            assert ".iriusrisk directory already exists" in result.output
            assert "Use --force to overwrite" in result.output
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_force_overwrite(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init --force' to overwrite existing directory."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create existing .iriusrisk directory with old config
            irius_dir = tmp_path / ".iriusrisk"
            irius_dir.mkdir()
            old_config = {"name": "Old Project"}
            with open(irius_dir / "project.json", 'w') as f:
                json.dump(old_config, f)
            
            # Provide empty input to skip scope prompt
            result = cli_runner.invoke(cli, ['init', '--name', 'New Project', '--force'], input='\n')
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "New Project" in result.output
            
            # Check that config was overwritten
            with open(irius_dir / "project.json") as f:
                config = json.load(f)
            
            assert config["name"] == "New Project"
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_help(self, cli_runner):
        """Test 'iriusrisk init --help' command."""
        result = cli_runner.invoke(cli, ['init', '--help'])
        
        assert result.exit_code == 0
        assert "Initialize a new or existing IriusRisk project" in result.output
        assert "--name" in result.output
        assert "--existing-ref" in result.output
        assert "--force" in result.output


class TestGenerateReferenceId:
    """Test cases for _generate_reference_id function."""
    
    def test_generate_reference_id_normal_name(self):
        """Test reference ID generation with normal project name."""
        ref_id = _generate_reference_id("My Web App")
        
        assert ref_id.startswith("my-web-app-")
        assert len(ref_id) == len("my-web-app-") + 4  # 4 character suffix
        assert ref_id[-4:].isalnum()  # suffix should be alphanumeric
    
    def test_generate_reference_id_special_characters(self):
        """Test reference ID generation with special characters."""
        ref_id = _generate_reference_id("API Gateway Service!")
        
        assert ref_id.startswith("api-gateway-service-")
        assert "!" not in ref_id
        assert len(ref_id) == len("api-gateway-service-") + 4
    
    def test_generate_reference_id_empty_name(self):
        """Test reference ID generation with empty name."""
        ref_id = _generate_reference_id("")
        
        assert ref_id.startswith("project-")
        assert len(ref_id) == len("project-") + 4
    
    def test_generate_reference_id_short_name(self):
        """Test reference ID generation with very short name."""
        ref_id = _generate_reference_id("A")
        
        assert ref_id.startswith("project-")
        assert len(ref_id) == len("project-") + 4
    
    def test_generate_reference_id_multiple_spaces(self):
        """Test reference ID generation with multiple spaces."""
        ref_id = _generate_reference_id("My    Web     App")
        
        assert ref_id.startswith("my-web-app-")
        assert "--" not in ref_id  # no consecutive hyphens
    
    def test_generate_reference_id_uniqueness(self):
        """Test that reference ID generation produces unique results."""
        name = "Test Project"
        ref_ids = [_generate_reference_id(name) for _ in range(10)]
        
        # All should start with the same base
        for ref_id in ref_ids:
            assert ref_id.startswith("test-project-")
        
        # All should be unique (very high probability with 4-char random suffix)
        assert len(set(ref_ids)) == len(ref_ids)


class TestInitCommandIntegration:
    """Integration tests for init command."""
    
    def test_init_command_integration(self, cli_runner, mock_api_client, mock_env_vars, tmp_path):
        """Test init command with full environment setup."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Provide empty input to skip scope prompt
            result = cli_runner.invoke(cli, ['init', '--name', 'Integration Test Project'], input='\n')
            
            assert result.exit_code == 0
            
            # Verify directory structure
            irius_dir = tmp_path / ".iriusrisk"
            assert irius_dir.exists()
            assert irius_dir.is_dir()
            
            project_file = irius_dir / "project.json"
            assert project_file.exists()
            assert project_file.is_file()
            
            # Verify project.json structure
            with open(project_file) as f:
                config = json.load(f)
            
            required_fields = ["name", "reference_id", "created_at", "description", "initialized_from"]
            for field in required_fields:
                assert field in config, f"Missing required field: {field}"
            
            assert config["name"] == "Integration Test Project"
            assert config["initialized_from"] == "new_project"
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_new_project_with_scope(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init --name --scope' command for multi-repo support."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            scope_text = "Backend API services handling order processing and user management"
            result = cli_runner.invoke(cli, [
                'init', 
                '--name', 'E-commerce Platform',
                '--scope', scope_text
            ])
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "E-commerce Platform" in result.output
            assert "✅ Initialized new IriusRisk project" in result.output
            
            # Check project.json contains scope
            project_file = tmp_path / ".iriusrisk" / "project.json"
            with open(project_file) as f:
                config = json.load(f)
            
            assert config["name"] == "E-commerce Platform"
            assert config["scope"] == scope_text
            assert "Scope:" in result.output
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_existing_project_with_scope(self, cli_runner, mock_api_client, tmp_path):
        """Test 'iriusrisk init -r --scope' for connecting to existing project with scope."""
        # Mock API response for existing project
        mock_project_data = {
            "_embedded": {
                "items": [{
                    "id": "abc-123-def-456",
                    "name": "E-commerce Platform",
                    "referenceId": "ecommerce-platform",
                    "description": "Existing project",
                    "state": "synced",
                    "tags": [],
                    "isArchived": False,
                    "isBlueprint": False,
                    "workflowState": {"name": "in-progress"},
                    "version": {"number": "1.0"},
                    "modelUpdated": "2024-01-01T00:00:00Z"
                }]
            }
        }
        
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Mock the Container and ProjectService
            with patch('iriusrisk_cli.commands.init.get_container') as mock_container_patch:
                mock_service = MagicMock()
                mock_service.list_projects.return_value = {
                    'projects': mock_project_data['_embedded']['items'],
                    'page_info': {},
                    'full_response': mock_project_data
                }
                mock_container_patch.return_value.get.return_value = mock_service
                
                scope_text = "AWS infrastructure via Terraform - ECS, RDS, VPC networking"
                result = cli_runner.invoke(cli, [
                    'init',
                    '-r', 'ecommerce-platform',
                    '--scope', scope_text
                ])
                
                assert result.exit_code == 0, f"Command failed with output: {result.output}"
                assert "✅ Found project: E-commerce Platform" in result.output
                assert "✅ Initialized existing IriusRisk project" in result.output
                
                # Check project.json contains scope
                project_file = tmp_path / ".iriusrisk" / "project.json"
                with open(project_file) as f:
                    config = json.load(f)
                
                assert config["name"] == "E-commerce Platform"
                assert config["project_id"] == "abc-123-def-456"
                assert config["reference_id"] == "ecommerce-platform"
                assert config["scope"] == scope_text
                assert config["initialized_from"] == "existing_project"
            
        finally:
            os.chdir(original_cwd)
    
    def test_config_get_project_scope(self, tmp_path):
        """Test Config.get_project_scope() method reads scope from project.json."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .iriusrisk directory and project.json with scope
            irius_dir = tmp_path / ".iriusrisk"
            irius_dir.mkdir()
            
            project_config = {
                "name": "Test Project",
                "reference_id": "test-project-123",
                "scope": "Backend API for order processing"
            }
            
            project_file = irius_dir / "project.json"
            with open(project_file, 'w') as f:
                json.dump(project_config, f)
            
            # Test Config.get_project_scope()
            from iriusrisk_cli.config import Config
            config = Config()
            
            scope = config.get_project_scope()
            assert scope == "Backend API for order processing"
            
        finally:
            os.chdir(original_cwd)
    
    def test_config_get_project_scope_returns_none_when_not_defined(self, tmp_path):
        """Test Config.get_project_scope() returns None when scope not defined."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .iriusrisk directory and project.json WITHOUT scope
            irius_dir = tmp_path / ".iriusrisk"
            irius_dir.mkdir()
            
            project_config = {
                "name": "Test Project",
                "reference_id": "test-project-123"
            }
            
            project_file = irius_dir / "project.json"
            with open(project_file, 'w') as f:
                json.dump(project_config, f)
            
            # Test Config.get_project_scope()
            from iriusrisk_cli.config import Config
            config = Config()
            
            scope = config.get_project_scope()
            assert scope is None
            
        finally:
            os.chdir(original_cwd)


def test_init_command_exists_in_main_cli(cli_runner):
    """Test that init command is registered in main CLI."""
    result = cli_runner.invoke(cli, ['--help'])
    
    assert result.exit_code == 0
    assert 'init' in result.output
