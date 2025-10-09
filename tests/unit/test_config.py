"""Unit tests for configuration management."""

import os
import json
import tempfile
from pathlib import Path
import pytest
from src.iriusrisk_cli.config import Config, save_user_config, validate_project_config


class TestConfigCascade:
    """Test configuration cascade loading."""
    
    def test_hostname_from_environment(self, monkeypatch, tmp_path):
        """Test that hostname is loaded from environment variable."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'https://env.iriusrisk.com')
        monkeypatch.setenv('IRIUS_API_TOKEN', 'test-token')
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        assert config.hostname == 'https://env.iriusrisk.com'
    
    def test_hostname_adds_scheme(self, monkeypatch, tmp_path):
        """Test that hostname without scheme gets https:// prefix."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'env.iriusrisk.com')
        monkeypatch.setenv('IRIUS_API_TOKEN', 'test-token')
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        assert config.hostname == 'https://env.iriusrisk.com'
    
    def test_api_token_from_api_key_env(self, monkeypatch, tmp_path):
        """Test that API token is loaded from IRIUS_API_KEY environment variable."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'https://test.iriusrisk.com')
        monkeypatch.setenv('IRIUS_API_KEY', 'test-key-123')
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        assert config.api_token == 'test-key-123'
    
    def test_api_token_from_api_token_env(self, monkeypatch, tmp_path):
        """Test that API token is loaded from IRIUS_API_TOKEN environment variable."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'https://test.iriusrisk.com')
        monkeypatch.setenv('IRIUS_API_TOKEN', 'test-token-456')
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        assert config.api_token == 'test-token-456'
    
    def test_api_key_preferred_over_token(self, monkeypatch, tmp_path):
        """Test that IRIUS_API_KEY is preferred over IRIUS_API_TOKEN."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'https://test.iriusrisk.com')
        monkeypatch.setenv('IRIUS_API_KEY', 'preferred-key')
        monkeypatch.setenv('IRIUS_API_TOKEN', 'fallback-token')
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        assert config.api_token == 'preferred-key'
    
    def test_hostname_from_user_config(self, monkeypatch, tmp_path):
        """Test that hostname is loaded from user config."""
        # Clear environment variables
        monkeypatch.delenv('IRIUS_HOSTNAME', raising=False)
        monkeypatch.delenv('IRIUS_API_KEY', raising=False)
        monkeypatch.setenv('IRIUS_API_TOKEN', 'test-token')
        
        # Create user config
        user_config_dir = tmp_path / ".iriusrisk"
        user_config_dir.mkdir()
        user_config_file = user_config_dir / "config.json"
        user_config_file.write_text(json.dumps({
            "hostname": "https://user.iriusrisk.com",
            "api_token": "user-token"
        }))
        
        # Mock home directory
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        (tmp_path / "project").mkdir()
        monkeypatch.chdir(tmp_path / "project")
        
        config = Config()
        assert config.hostname == 'https://user.iriusrisk.com'
    
    def test_hostname_from_project_config(self, monkeypatch, tmp_path):
        """Test that hostname is loaded from project config."""
        # Clear environment and user config
        monkeypatch.delenv('IRIUS_HOSTNAME', raising=False)
        monkeypatch.setenv('IRIUS_API_TOKEN', 'test-token')
        monkeypatch.setattr(Path, 'home', lambda: tmp_path / "nonexistent")
        
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        iriusrisk_dir = project_dir / ".iriusrisk"
        iriusrisk_dir.mkdir()
        project_config_file = iriusrisk_dir / "project.json"
        project_config_file.write_text(json.dumps({
            "hostname": "https://project.iriusrisk.com",
            "project_id": "test-project"
        }))
        
        monkeypatch.chdir(project_dir)
        
        config = Config()
        assert config.hostname == 'https://project.iriusrisk.com'
    
    def test_missing_hostname_raises_error(self, monkeypatch, tmp_path):
        """Test that missing hostname raises clear error."""
        monkeypatch.delenv('IRIUS_HOSTNAME', raising=False)
        monkeypatch.delenv('IRIUS_API_KEY', raising=False)
        monkeypatch.setenv('IRIUS_API_TOKEN', 'test-token')
        monkeypatch.setattr(Path, 'home', lambda: tmp_path / "nonexistent")
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        with pytest.raises(ValueError, match="IRIUS_HOSTNAME not found"):
            _ = config.hostname
    
    def test_missing_api_token_raises_error(self, monkeypatch, tmp_path):
        """Test that missing API token raises clear error."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'https://test.iriusrisk.com')
        monkeypatch.delenv('IRIUS_API_KEY', raising=False)
        monkeypatch.delenv('IRIUS_API_TOKEN', raising=False)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path / "nonexistent")
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        with pytest.raises(ValueError, match="IRIUS_API_TOKEN not found"):
            _ = config.api_token


class TestSaveUserConfig:
    """Test saving user configuration."""
    
    def test_save_hostname_only(self, monkeypatch, tmp_path):
        """Test saving only hostname preserves existing api_token."""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        # Create existing config
        config_dir = tmp_path / ".iriusrisk"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"api_token": "existing-token"}))
        
        save_user_config(hostname="https://new.iriusrisk.com")
        
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config['hostname'] == "https://new.iriusrisk.com"
        assert saved_config['api_token'] == "existing-token"
    
    def test_save_api_token_only(self, monkeypatch, tmp_path):
        """Test saving only api_token preserves existing hostname."""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        # Create existing config
        config_dir = tmp_path / ".iriusrisk"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"hostname": "https://existing.iriusrisk.com"}))
        
        save_user_config(api_token="new-token-123")
        
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config['hostname'] == "https://existing.iriusrisk.com"
        assert saved_config['api_token'] == "new-token-123"
    
    def test_save_creates_directory(self, monkeypatch, tmp_path):
        """Test that saving config creates directory if it doesn't exist."""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        save_user_config(hostname="https://test.iriusrisk.com", api_token="test-token")
        
        config_file = tmp_path / ".iriusrisk" / "config.json"
        assert config_file.exists()
        
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config['hostname'] == "https://test.iriusrisk.com"
        assert saved_config['api_token'] == "test-token"
    
    def test_save_sets_secure_permissions(self, monkeypatch, tmp_path):
        """Test that config file has secure permissions (0600)."""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        save_user_config(hostname="https://test.iriusrisk.com", api_token="test-token")
        
        config_file = tmp_path / ".iriusrisk" / "config.json"
        stats = config_file.stat()
        # Check that permissions are 0600 (owner read/write only)
        assert oct(stats.st_mode)[-3:] == '600'


class TestValidateProjectConfig:
    """Test project configuration validation."""
    
    def test_valid_config_passes(self):
        """Test that valid config passes validation."""
        config = {
            "project_id": "test-123",
            "name": "Test Project",
            "hostname": "https://test.iriusrisk.com"
        }
        # Should not raise
        validate_project_config(config)
    
    def test_api_token_forbidden(self):
        """Test that api_token field is forbidden."""
        config = {
            "project_id": "test-123",
            "api_token": "secret-token"
        }
        with pytest.raises(ValueError, match="must not contain sensitive fields"):
            validate_project_config(config)
    
    def test_api_key_forbidden(self):
        """Test that api_key field is forbidden."""
        config = {
            "project_id": "test-123",
            "api_key": "secret-key"
        }
        with pytest.raises(ValueError, match="must not contain sensitive fields"):
            validate_project_config(config)
    
    def test_token_forbidden(self):
        """Test that token field is forbidden."""
        config = {
            "project_id": "test-123",
            "token": "secret-token"
        }
        with pytest.raises(ValueError, match="must not contain sensitive fields"):
            validate_project_config(config)
    
    def test_password_forbidden(self):
        """Test that password field is forbidden."""
        config = {
            "project_id": "test-123",
            "password": "secret-password"
        }
        with pytest.raises(ValueError, match="must not contain sensitive fields"):
            validate_project_config(config)
    
    def test_secret_forbidden(self):
        """Test that secret field is forbidden."""
        config = {
            "project_id": "test-123",
            "secret": "secret-value"
        }
        with pytest.raises(ValueError, match="must not contain sensitive fields"):
            validate_project_config(config)


class TestConfigSources:
    """Test get_config_sources method."""
    
    def test_config_sources_shows_all_sources(self, monkeypatch, tmp_path):
        """Test that config sources method returns all configuration sources."""
        monkeypatch.setenv('IRIUS_HOSTNAME', 'https://env.iriusrisk.com')
        monkeypatch.setenv('IRIUS_API_KEY', 'env-key')
        monkeypatch.chdir(tmp_path)
        
        config = Config()
        sources = config.get_config_sources()
        
        assert 'resolved' in sources
        assert 'environment' in sources
        assert 'user_config' in sources
        assert 'project_config' in sources
        
        assert sources['resolved']['hostname'] == 'https://env.iriusrisk.com'
        assert sources['resolved']['api_token'] == 'env-key'
        assert sources['environment']['IRIUS_HOSTNAME'] == 'https://env.iriusrisk.com'
        assert sources['environment']['IRIUS_API_KEY'] == 'env-key'

