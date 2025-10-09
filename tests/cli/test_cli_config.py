"""CLI tests for config commands."""

import json
from pathlib import Path
import pytest
from click.testing import CliRunner
from src.iriusrisk_cli.main import cli


class TestConfigCommands:
    """Test config command group."""
    
    def test_config_set_hostname(self, tmp_path, monkeypatch):
        """Test setting hostname via config command."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        result = runner.invoke(cli, ['config', 'set-hostname', 'https://test.iriusrisk.com'])
        
        assert result.exit_code == 0
        assert 'Saved hostname' in result.output
        
        # Verify file was created
        config_file = tmp_path / '.iriusrisk' / 'config.json'
        assert config_file.exists()
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        assert config['hostname'] == 'https://test.iriusrisk.com'
    
    def test_config_set_hostname_adds_scheme(self, tmp_path, monkeypatch):
        """Test that hostname without scheme gets https:// added."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        result = runner.invoke(cli, ['config', 'set-hostname', 'test.iriusrisk.com'])
        
        assert result.exit_code == 0
        
        config_file = tmp_path / '.iriusrisk' / 'config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        assert config['hostname'] == 'https://test.iriusrisk.com'
    
    def test_config_set_api_key_prompts(self, tmp_path, monkeypatch):
        """Test that set-api-key prompts for input."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        # Simulate user input (enter key twice for confirmation)
        result = runner.invoke(cli, ['config', 'set-api-key'], input='test-api-key-123\ntest-api-key-123\n')
        
        assert result.exit_code == 0
        assert 'Saved API key' in result.output
        assert 'not stored in shell history' in result.output
        
        # Verify file was created
        config_file = tmp_path / '.iriusrisk' / 'config.json'
        assert config_file.exists()
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        assert config['api_token'] == 'test-api-key-123'
    
    def test_config_set_api_key_confirmation_mismatch(self, tmp_path, monkeypatch):
        """Test that mismatched confirmation is rejected."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        # Different values for confirmation
        result = runner.invoke(cli, ['config', 'set-api-key'], input='key1\nkey2\n')
        
        assert result.exit_code != 0
        assert 'Error' in result.output
    
    def test_config_set_api_key_empty_rejected(self, tmp_path, monkeypatch):
        """Test that empty API key is rejected."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        # Empty input
        result = runner.invoke(cli, ['config', 'set-api-key'], input='\n\n')
        
        assert result.exit_code != 0
    
    def test_config_set_api_key_preserves_hostname(self, tmp_path, monkeypatch):
        """Test that setting API key preserves existing hostname."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        # First set hostname
        runner.invoke(cli, ['config', 'set-hostname', 'https://existing.iriusrisk.com'])
        
        # Then set API key
        result = runner.invoke(cli, ['config', 'set-api-key'], input='new-key\nnew-key\n')
        
        assert result.exit_code == 0
        
        config_file = tmp_path / '.iriusrisk' / 'config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        assert config['hostname'] == 'https://existing.iriusrisk.com'
        assert config['api_token'] == 'new-key'
    
    def test_config_show_no_config(self, tmp_path, monkeypatch):
        """Test config show with no configuration."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'nonexistent')
        monkeypatch.chdir(tmp_path)
        
        # Clear environment variables
        monkeypatch.delenv('IRIUS_HOSTNAME', raising=False)
        monkeypatch.delenv('IRIUS_API_KEY', raising=False)
        monkeypatch.delenv('IRIUS_API_TOKEN', raising=False)
        
        result = runner.invoke(cli, ['config', 'show'])
        
        assert result.exit_code == 0
        assert 'not found' in result.output
        assert 'NOT CONFIGURED' in result.output
    
    def test_config_show_with_user_config(self, tmp_path, monkeypatch):
        """Test config show displays user configuration."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        (tmp_path / 'project').mkdir()
        monkeypatch.chdir(tmp_path / 'project')
        
        # Clear environment variables
        monkeypatch.delenv('IRIUS_HOSTNAME', raising=False)
        monkeypatch.delenv('IRIUS_API_KEY', raising=False)
        monkeypatch.delenv('IRIUS_API_TOKEN', raising=False)
        
        # Set up user config
        runner.invoke(cli, ['config', 'set-hostname', 'https://user.iriusrisk.com'])
        runner.invoke(cli, ['config', 'set-api-key'], input='user-key-123\nuser-key-123\n')
        
        result = runner.invoke(cli, ['config', 'show'])
        
        assert result.exit_code == 0
        assert 'https://user.iriusrisk.com' in result.output
        assert '****' in result.output  # API key should be masked
        assert '123' in result.output  # Last 4 chars visible
        assert 'user config' in result.output.lower()
    
    def test_config_show_masks_api_key(self, tmp_path, monkeypatch):
        """Test that config show masks the API key properly."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        
        # Set up config with known API key
        runner.invoke(cli, ['config', 'set-api-key'], input='secret-key-abc123\nsecret-key-abc123\n')
        
        result = runner.invoke(cli, ['config', 'show'])
        
        assert result.exit_code == 0
        # Should show masked version
        assert 'c123' in result.output  # Last 4 chars
        # Should not show full key
        assert 'secret-key-abc123' not in result.output
    
    def test_config_help(self):
        """Test config command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', '--help'])
        
        assert result.exit_code == 0
        assert 'Manage IriusRisk CLI configuration' in result.output
        assert 'set-hostname' in result.output
        assert 'set-api-key' in result.output
        assert 'show' in result.output
    
    def test_config_set_hostname_help(self):
        """Test set-hostname command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'set-hostname', '--help'])
        
        assert result.exit_code == 0
        assert 'Set the default IriusRisk hostname' in result.output
    
    def test_config_set_api_key_help(self):
        """Test set-api-key command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'set-api-key', '--help'])
        
        assert result.exit_code == 0
        assert 'Prompts for the API key securely' in result.output
        assert 'shell history' in result.output
    
    def test_config_file_permissions(self, tmp_path, monkeypatch):
        """Test that config file has secure permissions."""
        runner = CliRunner()
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        runner.invoke(cli, ['config', 'set-hostname', 'https://test.iriusrisk.com'])
        
        config_file = tmp_path / '.iriusrisk' / 'config.json'
        stats = config_file.stat()
        
        # Check that permissions are 0600 (owner read/write only)
        assert oct(stats.st_mode)[-3:] == '600'

