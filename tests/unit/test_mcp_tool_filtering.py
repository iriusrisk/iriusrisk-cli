"""Unit tests for MCP tool filtering functionality."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.iriusrisk_cli.main import cli


class TestMCPToolFiltering:
    """Test MCP tool filtering with --include-tags, --exclude-tags, etc."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_list_tools_flag(self):
        """Test --list-tools flag displays all tools and categories."""
        result = self.runner.invoke(cli, ['mcp', '--list-tools'])
        
        assert result.exit_code == 0
        assert 'Available MCP Tools by Category:' in result.output
        assert 'workflow:' in result.output
        assert 'project:' in result.output
        assert 'threats-and-controls:' in result.output
        assert 'questionnaires:' in result.output
        assert 'reporting:' in result.output
        assert 'versioning:' in result.output
        assert 'utility:' in result.output
        assert 'Total: 29 tools' in result.output
    
    def test_list_tools_shows_specific_tools(self):
        """Test --list-tools shows specific tool names."""
        result = self.runner.invoke(cli, ['mcp', '--list-tools'])
        
        assert result.exit_code == 0
        # Check for some specific tools
        assert 'initialize_iriusrisk_workflow' in result.output
        assert 'sync' in result.output
        assert 'track_threat_update' in result.output
        assert 'generate_report' in result.output
    
    def test_invalid_category_in_include_tags(self):
        """Test error when invalid category is provided to --include-tags."""
        result = self.runner.invoke(cli, ['mcp', '--include-tags', 'invalid_category'])
        
        assert result.exit_code == 1
        assert "Error: Unknown category or tool 'invalid_category'" in result.output
        assert 'Valid categories:' in result.output
    
    def test_invalid_category_in_exclude_tags(self):
        """Test error when invalid category is provided to --exclude-tags."""
        result = self.runner.invoke(cli, ['mcp', '--exclude-tags', 'nonexistent'])
        
        assert result.exit_code == 1
        assert "Error: Unknown category or tool 'nonexistent'" in result.output
    
    def test_invalid_tool_in_include_tools(self):
        """Test error when invalid tool name is provided to --include-tools."""
        result = self.runner.invoke(cli, ['mcp', '--include-tools', 'fake_tool'])
        
        assert result.exit_code == 1
        assert "Error: Unknown tool 'fake_tool'" in result.output
        assert 'Use --list-tools to see all available tools' in result.output
    
    def test_invalid_tool_in_exclude_tools(self):
        """Test error when invalid tool name is provided to --exclude-tools."""
        result = self.runner.invoke(cli, ['mcp', '--exclude-tools', 'nonexistent_tool'])
        
        assert result.exit_code == 1
        assert "Error: Unknown tool 'nonexistent_tool'" in result.output
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_exclude_tags_calls_disable(self, mock_fastmcp, mock_container):
        """Test that --exclude-tags calls mcp_server.disable() with correct tags."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--exclude-tags', 'workflow'])
        
        # Verify disable was called with workflow tag
        mock_server.disable.assert_called()
        call_args = mock_server.disable.call_args
        assert 'workflow' in call_args[1]['tags']
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_include_tags_calls_enable_with_only(self, mock_fastmcp, mock_container):
        """Test that --include-tags calls mcp_server.enable() with only=True."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--include-tags', 'project'])
        
        # Verify enable was called with only=True
        mock_server.enable.assert_called()
        call_args = mock_server.enable.call_args
        assert call_args[1]['only'] is True
        assert 'project' in call_args[1]['tags']
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_exclude_tools_calls_disable_with_keys(self, mock_fastmcp, mock_container):
        """Test that --exclude-tools calls mcp_server.disable() with tool keys."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--exclude-tools', 'sync'])
        
        # Verify disable was called with correct key format
        mock_server.disable.assert_called()
        call_args = mock_server.disable.call_args
        assert 'tool:sync' in call_args[1]['keys']
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_include_tools_calls_enable_with_keys(self, mock_fastmcp, mock_container):
        """Test that --include-tools calls mcp_server.enable() with tool keys."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--include-tools', 'sync', '--include-tools', 'import_otm'])
        
        # Verify enable was called with correct key format
        mock_server.enable.assert_called()
        call_args = mock_server.enable.call_args
        assert 'tool:sync' in call_args[1]['keys']
        assert 'tool:import_otm' in call_args[1]['keys']
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_multiple_exclude_tags(self, mock_fastmcp, mock_container):
        """Test excluding multiple categories."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--exclude-tags', 'workflow', '--exclude-tags', 'reporting'])
        
        # Verify disable was called with both tags
        mock_server.disable.assert_called()
        call_args = mock_server.disable.call_args
        assert 'workflow' in call_args[1]['tags']
        assert 'reporting' in call_args[1]['tags']
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_multiple_include_tags(self, mock_fastmcp, mock_container):
        """Test including multiple categories."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--include-tags', 'project', '--include-tags', 'utility'])
        
        # Verify enable was called with both tags and only=True
        mock_server.enable.assert_called()
        call_args = mock_server.enable.call_args
        assert 'project' in call_args[1]['tags']
        assert 'utility' in call_args[1]['tags']
        assert call_args[1]['only'] is True
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_combined_include_and_exclude(self, mock_fastmcp, mock_container):
        """Test combining --include-tags and --exclude-tools."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, [
            'mcp',
            '--include-tags', 'project',
            '--exclude-tools', 'sync'
        ])
        
        # Verify both enable and disable were called
        assert mock_server.enable.called
        assert mock_server.disable.called
    
    def test_valid_category_names(self):
        """Test that all expected categories are recognized."""
        valid_categories = [
            'workflow', 'project', 'threats-and-controls',
            'questionnaires', 'reporting', 'versioning', 'utility'
        ]
        
        for category in valid_categories:
            result = self.runner.invoke(cli, ['mcp', '--list-tools'])
            assert result.exit_code == 0
            assert f'{category}:' in result.output
    
    def test_tool_name_as_include_tag(self):
        """Test that specific tool names can be used in --include-tags."""
        # This should work - the code allows both categories and tool names
        result = self.runner.invoke(cli, ['mcp', '--include-tags', 'sync'])
        # Should not error out during validation
        assert "Error: Unknown category or tool 'sync'" not in result.output


class TestMCPToolCategories:
    """Test that tool categories are correctly defined."""
    
    def test_all_tools_have_categories(self):
        """Test that TOOL_CATEGORIES includes all 29 tools."""
        from src.iriusrisk_cli.commands.mcp import mcp
        
        runner = CliRunner()
        result = runner.invoke(mcp, ['--list-tools'])
        
        # Count tools in output
        assert 'Total: 29 tools' in result.output
    
    def test_workflow_category_count(self):
        """Test that workflow category has 11 tools."""
        runner = CliRunner()
        result = runner.invoke(cli, ['mcp', '--list-tools'])
        
        # Extract workflow section
        lines = result.output.split('\n')
        workflow_idx = next(i for i, line in enumerate(lines) if 'workflow:' in line)
        
        # Count tools under workflow (until next category or empty line)
        tool_count = 0
        for i in range(workflow_idx + 1, len(lines)):
            if lines[i].strip().startswith('-'):
                tool_count += 1
            elif lines[i].strip() and not lines[i].strip().startswith('-'):
                break
        
        assert tool_count == 11
    
    def test_project_category_count(self):
        """Test that project category has 5 tools."""
        runner = CliRunner()
        result = runner.invoke(cli, ['mcp', '--list-tools'])
        
        lines = result.output.split('\n')
        project_idx = next(i for i, line in enumerate(lines) if 'project:' in line)
        
        tool_count = 0
        for i in range(project_idx + 1, len(lines)):
            if lines[i].strip().startswith('-'):
                tool_count += 1
            elif lines[i].strip() and not lines[i].strip().startswith('-'):
                break
        
        assert tool_count == 5
