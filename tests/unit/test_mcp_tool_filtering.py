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
        """Test that --exclude-tags removes tools from the excluded category."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--exclude-tags', 'workflow'])
        
        # Verify remove_tool was called for workflow tools
        # The workflow category has 11 tools
        assert mock_server.remove_tool.call_count == 11
        
        # Verify some specific workflow tools were removed
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'initialize_iriusrisk_workflow' in removed_tools
        assert 'threats_and_countermeasures' in removed_tools
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_include_tags_calls_enable_with_only(self, mock_fastmcp, mock_container):
        """Test that --include-tags removes all tools except those in the included category."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--include-tags', 'project'])
        
        # Verify remove_tool was called for all non-project tools
        # Total tools: 29, project category has 5 tools, so 24 should be removed
        assert mock_server.remove_tool.call_count == 24
        
        # Verify project tools were NOT removed
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'sync' not in removed_tools
        assert 'import_otm' not in removed_tools
        assert 'export_otm' not in removed_tools
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_exclude_tools_calls_disable_with_keys(self, mock_fastmcp, mock_container):
        """Test that --exclude-tools removes the specified tools."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--exclude-tools', 'sync'])
        
        # Verify remove_tool was called with the sync tool
        mock_server.remove_tool.assert_called()
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'sync' in removed_tools
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_include_tools_calls_enable_with_keys(self, mock_fastmcp, mock_container):
        """Test that --include-tools removes all tools except the specified ones."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ['mcp', '--include-tools', 'sync', '--include-tools', 'import_otm'])
        
        # Verify remove_tool was called for all tools except sync and import_otm
        # Total tools: 29, keeping 2, so 27 should be removed
        assert mock_server.remove_tool.call_count == 27
        
        # Verify the specified tools were NOT removed
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'sync' not in removed_tools
        assert 'import_otm' not in removed_tools
    
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
        
        # Verify remove_tool was called for both workflow (11 tools) and reporting (2 tools)
        assert mock_server.remove_tool.call_count == 13
        
        # Verify tools from both categories were removed
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'initialize_iriusrisk_workflow' in removed_tools  # workflow
        assert 'generate_report' in removed_tools  # reporting
    
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
        
        # Verify remove_tool was called for all tools except project (5) and utility (1)
        # Total tools: 29, keeping 6, so 23 should be removed
        assert mock_server.remove_tool.call_count == 23
        
        # Verify tools from included categories were NOT removed
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'sync' not in removed_tools  # project
        assert 'get_cli_version' not in removed_tools  # utility
    
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
        
        # Verify remove_tool was called
        # Project has 5 tools, but we're excluding sync, so 24 + 1 = 25 tools removed
        assert mock_server.remove_tool.call_count == 25
        
        # Verify sync was removed even though it's in the project category
        removed_tools = [call[0][0] for call in mock_server.remove_tool.call_args_list]
        assert 'sync' in removed_tools
    
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
    
    @patch('src.iriusrisk_cli.container.get_container')
    @patch('src.iriusrisk_cli.commands.mcp.FastMCP')
    def test_tool_name_as_include_tag(self, mock_fastmcp, mock_container):
        """Test that specific tool names can be used in --include-tags."""
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        mock_container.return_value.get.return_value = MagicMock()
        
        # Mock run to prevent actual server startup
        mock_server.run.side_effect = KeyboardInterrupt()
        
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
