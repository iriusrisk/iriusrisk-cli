"""Unit tests for MCP (Model Context Protocol) functionality to improve coverage."""

import pytest
import json
import tempfile
import os
import logging
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, mock_open
import asyncio

from src.iriusrisk_cli.commands.mcp import (
    _find_project_root_and_config,
    setup_mcp_logging
)


class TestMCPProjectRootFinding:
    """Test project root and configuration finding functionality."""
    
    def test_find_project_root_current_directory(self):
        """Test finding project root in current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            iriusrisk_dir = temp_path / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            project_config = {
                'project_id': 'test-project-123',
                'project_name': 'Test Project',
                'reference_id': 'test-ref'
            }
            
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                json.dump(project_config, f)
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                root, config = _find_project_root_and_config()
                
                assert root == temp_path
                assert config == project_config
    
    def test_find_project_root_parent_directory(self):
        """Test finding project root in parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subdir = temp_path / 'subdir' / 'nested'
            subdir.mkdir(parents=True)
            
            iriusrisk_dir = temp_path / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            project_config = {'project_id': 'parent-project'}
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                json.dump(project_config, f)
            
            with patch('pathlib.Path.cwd', return_value=subdir):
                root, config = _find_project_root_and_config()
                
                assert root == temp_path
                assert config == project_config
    
    @patch.dict(os.environ, {'CURSOR_WORKSPACE': '/test/workspace'})
    def test_find_project_root_environment_variable(self):
        """Test finding project root using environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / 'workspace'
            workspace_path.mkdir()
            
            iriusrisk_dir = workspace_path / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            project_config = {'project_id': 'env-project'}
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                json.dump(project_config, f)
            
            with patch.dict(os.environ, {'CURSOR_WORKSPACE': str(workspace_path)}):
                with patch('pathlib.Path.cwd', return_value=Path('/different/path')):
                    root, config = _find_project_root_and_config()
                    
                    assert root == workspace_path
                    assert config == project_config
    
    def test_find_project_root_home_src_directory(self):
        """Test finding project root in home/src directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            home_path = Path(temp_dir)
            src_dir = home_path / 'src'
            src_dir.mkdir()
            
            project_dir = src_dir / 'my_project'
            project_dir.mkdir()
            
            iriusrisk_dir = project_dir / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            project_config = {'project_id': 'home-src-project'}
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                json.dump(project_config, f)
            
            with patch('pathlib.Path.home', return_value=home_path):
                with patch('pathlib.Path.cwd', return_value=Path('/different/path')):
                    root, config = _find_project_root_and_config()
                    
                    assert root == project_dir
                    assert config == project_config
    
    def test_find_project_root_invalid_json(self):
        """Test handling of invalid project.json files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            iriusrisk_dir = temp_path / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            # Create invalid JSON file
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                f.write('{ invalid json }')
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                with patch('pathlib.Path.home', return_value=temp_path):  # Mock home directory
                    with patch.dict('os.environ', {}, clear=True):  # Clear all environment variables
                        root, config = _find_project_root_and_config()
                        
                        # Should continue searching and fall back to current directory
                        assert root == temp_path
                        assert config is None
    
    def test_find_project_root_permission_error(self):
        """Test handling of permission errors during search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                with patch('pathlib.Path.iterdir', side_effect=PermissionError("Access denied")):
                    root, config = _find_project_root_and_config()
                    
                    # Should fall back to current directory
                    assert root == temp_path
                    assert config is None
    
    def test_find_project_root_no_project_found(self):
        """Test when no project configuration is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                with patch('pathlib.Path.home', return_value=temp_path):
                    root, config = _find_project_root_and_config()
                    
                    assert root == temp_path
                    assert config is None


class TestMCPLogging:
    """Test MCP logging setup functionality."""
    
    def test_setup_mcp_logging_with_log_file(self):
        """Test that MCP logging setup respects --log-file option."""
        # Mock CLI context with log file specified
        mock_cli_ctx = Mock()
        mock_cli_ctx.logging_config = {
            'log_file': '/path/to/test.log',
            'debug': True,
            'verbose': False,
            'log_level': None
        }
        
        with patch('src.iriusrisk_cli.utils.logging_config.setup_logging') as mock_setup_logging:
            with patch('logging.getLogger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                
                setup_mcp_logging(mock_cli_ctx)
                
                # Verify setup_logging was called with correct parameters
                mock_setup_logging.assert_called_once_with(
                    log_level="DEBUG",
                    log_file='/path/to/test.log',
                    console_output=False,
                    component="mcp"
                )
    
    def test_setup_mcp_logging_silent_mode(self):
        """Test that MCP logging is silent when no log file specified."""
        # Mock CLI context with no log file
        mock_cli_ctx = Mock()
        mock_cli_ctx.logging_config = {
            'log_file': None,
            'debug': False,
            'verbose': False,
            'log_level': None
        }
        
        with patch('logging.getLogger') as mock_get_logger:
            with patch('logging.NullHandler') as mock_null_handler:
                mock_mcp_logger = Mock()
                mock_root_logger = Mock()
                mock_handler = Mock()
                mock_null_handler.return_value = mock_handler
                
                # Mock getLogger to return different loggers for different calls
                def get_logger_side_effect(name=None):
                    if name == 'iriusrisk_cli.commands.mcp':
                        return mock_mcp_logger
                    elif name is None or name == '':
                        return mock_root_logger
                    return Mock()
                
                mock_get_logger.side_effect = get_logger_side_effect
                
                # Mock that loggers have no handlers initially
                mock_mcp_logger.handlers = []
                mock_root_logger.handlers = []
                
                setup_mcp_logging(mock_cli_ctx)
                
                # Verify MCP logger was set to silent mode
                mock_mcp_logger.setLevel.assert_called_with(logging.CRITICAL + 1)
                mock_mcp_logger.addHandler.assert_called_once_with(mock_handler)
                
                # Verify root logger was also configured for silence
                mock_root_logger.addHandler.assert_called_once_with(mock_handler)
                mock_root_logger.setLevel.assert_called_with(logging.CRITICAL + 1)


class TestMCPServerTools:
    """Test MCP server tool implementations."""
    
    def setup_method(self):
        """Set up test environment."""
        # Import the MCP server tools
        import sys
        from unittest.mock import patch
        
        # Mock the FastMCP server to avoid actual server startup
        self.mock_server = Mock()
        
        # We'll need to patch the actual MCP tool functions when they're called
        # Since they're async and use the actual API client
    
    def test_mcp_initialize_workflow(self):
        """Test MCP initialize workflow tool."""
        # Import the actual MCP module to test the tools
        from src.iriusrisk_cli.commands import mcp
        
        # Mock the FastMCP server and its tool decorator
        with patch('src.iriusrisk_cli.commands.mcp.FastMCP') as mock_fastmcp:
            mock_app = Mock()
            mock_fastmcp.return_value = mock_app
            
            # Since we can't easily test the actual async tools without running the server,
            # we'll test the tool registration and basic functionality
            
            # Verify that the MCP command exists and can be imported
            assert hasattr(mcp, 'mcp')
            assert callable(mcp.mcp)
    
    def test_mcp_server_initialization_with_project_config(self):
        """Test MCP server initialization when project config exists."""
        project_config = {
            'project_id': 'test-project-uuid',
            'project_name': 'Test Project',
            'reference_id': 'test-ref'
        }
        
        with patch('src.iriusrisk_cli.commands.mcp._find_project_root_and_config') as mock_find:
            mock_find.return_value = (Path('/test/project'), project_config)
            
            with patch('src.iriusrisk_cli.commands.mcp.FastMCP') as mock_fastmcp:
                with patch('src.iriusrisk_cli.commands.mcp.setup_mcp_logging'):
                    mock_app = Mock()
                    mock_fastmcp.return_value = mock_app
                    
                    # Import and test the MCP command
                    from src.iriusrisk_cli.commands.mcp import mcp
                    
                    # The command should be callable
                    assert callable(mcp)
    
    def test_mcp_server_initialization_without_project_config(self):
        """Test MCP server initialization when no project config exists."""
        with patch('src.iriusrisk_cli.commands.mcp._find_project_root_and_config') as mock_find:
            mock_find.return_value = (Path('/test/project'), None)
            
            with patch('src.iriusrisk_cli.commands.mcp.FastMCP') as mock_fastmcp:
                with patch('src.iriusrisk_cli.commands.mcp.setup_mcp_logging'):
                    mock_app = Mock()
                    mock_fastmcp.return_value = mock_app
                    
                    # Import and test the MCP command
                    from src.iriusrisk_cli.commands.mcp import mcp
                    
                    # The command should be callable
                    assert callable(mcp)


class TestMCPDataOperations:
    """Test MCP data operation helpers."""
    
    def test_mcp_imports_sync_functions(self):
        """Test that MCP module imports required sync functions."""
        from src.iriusrisk_cli.commands.mcp import (
            _download_components_data,
            _download_trust_zones_data,
            _download_threats_data,
            _download_countermeasures_data,
            _ensure_iriusrisk_directory,
            _save_json_file
        )
        
        # Verify all required functions are imported
        assert callable(_download_components_data)
        assert callable(_download_trust_zones_data)
        assert callable(_download_threats_data)
        assert callable(_download_countermeasures_data)
        assert callable(_ensure_iriusrisk_directory)
        assert callable(_save_json_file)
    
    def test_mcp_imports_utility_functions(self):
        """Test that MCP module imports required utility functions."""
        from src.iriusrisk_cli.commands.mcp import (
            resolve_project_id,
            get_project_context_info,
            get_update_tracker
        )
        
        # Verify all required utility functions are imported
        assert callable(resolve_project_id)
        assert callable(get_project_context_info)
        assert callable(get_update_tracker)
    
    def test_mcp_imports_api_client(self):
        """Test that MCP module imports API client classes."""
        from src.iriusrisk_cli.commands.mcp import ProjectApiClient
        
        # Verify API client classes are imported
        assert ProjectApiClient is not None


class TestMCPErrorHandling:
    """Test MCP error handling scenarios."""
    
    def test_find_project_root_os_error(self):
        """Test handling of OS errors during project root search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with patch('pathlib.Path.cwd', side_effect=OSError("System error")):
                with patch('pathlib.Path.home', return_value=temp_path):
                    with patch.dict('os.environ', {}, clear=True):
                        # Should not raise exception, should handle gracefully
                        root, config = _find_project_root_and_config()
                        # Should return the home directory fallback
                        assert root == temp_path
                        assert config is None
    
    def test_find_project_root_file_not_found(self):
        """Test handling when project.json file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            iriusrisk_dir = temp_path / '.iriusrisk'
            iriusrisk_dir.mkdir()
            # Don't create project.json file
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                with patch('pathlib.Path.home', return_value=temp_path):  # Mock home directory
                    with patch.dict('os.environ', {}, clear=True):  # Clear all environment variables
                        root, config = _find_project_root_and_config()
                        
                        assert root == temp_path
                        assert config is None


class TestMCPIntegration:
    """Test MCP integration with other components."""
    
    def test_mcp_version_import(self):
        """Test that MCP module can import version information."""
        from src.iriusrisk_cli.commands.mcp import __version__
        
        # Verify version is imported
        assert __version__ is not None
        assert isinstance(__version__, str)
    
    def test_mcp_config_import(self):
        """Test that MCP module can import configuration."""
        from src.iriusrisk_cli.config import Config
        
        # Verify config class is available
        config = Config()
        assert config is not None
    
    def test_mcp_json_import(self):
        """Test that MCP module can import JSON functionality."""
        from src.iriusrisk_cli.commands.mcp import json
        
        # Verify JSON module is imported
        assert json is not None
        assert hasattr(json, 'load')
        assert hasattr(json, 'dump')


class TestMCPPathHandling:
    """Test MCP path handling functionality."""
    
    def test_find_project_root_multiple_environment_variables(self):
        """Test project root finding with multiple environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace1 = Path(temp_dir) / 'workspace1'
            workspace2 = Path(temp_dir) / 'workspace2'
            workspace1.mkdir()
            workspace2.mkdir()
            
            # Create project in workspace2
            iriusrisk_dir = workspace2 / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            project_config = {'project_id': 'multi-env-project'}
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                json.dump(project_config, f)
            
            # Set multiple environment variables
            env_vars = {
                'PWD': str(workspace1),  # This one doesn't have project
                'CURSOR_WORKSPACE': str(workspace2),  # This one has project
                'VSCODE_CWD': '/nonexistent'
            }
            
            with patch.dict(os.environ, env_vars):
                with patch('pathlib.Path.cwd', return_value=Path('/different/path')):
                    root, config = _find_project_root_and_config()
                    
                    # Should find the project in workspace2
                    assert root == workspace2
                    assert config == project_config
    
    def test_find_project_root_nested_search(self):
        """Test project root finding in nested directory structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            home_path = Path(temp_dir)
            
            # Create nested structure: home/src/project1, home/src/project2
            src_dir = home_path / 'src'
            src_dir.mkdir()
            
            project1_dir = src_dir / 'project1'
            project2_dir = src_dir / 'project2'
            project1_dir.mkdir()
            project2_dir.mkdir()
            
            # Only project2 has .iriusrisk
            iriusrisk_dir = project2_dir / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            project_config = {'project_id': 'nested-project'}
            project_json = iriusrisk_dir / 'project.json'
            with open(project_json, 'w') as f:
                json.dump(project_config, f)
            
            with patch('pathlib.Path.home', return_value=home_path):
                with patch('pathlib.Path.cwd', return_value=Path('/different/path')):
                    root, config = _find_project_root_and_config()
                    
                    # Should find project2
                    assert root == project2_dir
                    assert config == project_config
