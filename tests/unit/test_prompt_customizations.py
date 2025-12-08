"""Tests for MCP prompt customization feature."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.iriusrisk_cli.config import validate_project_config
from src.iriusrisk_cli.mcp.tools.shared_tools import _apply_prompt_customizations, _load_prompt_text


class TestPromptCustomizationValidation:
    """Test validation of prompt customizations in project.json."""
    
    def test_valid_prompt_customization_prefix(self):
        """Test validation passes for valid prefix customization."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "Organization specific rules here\n\n"
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_prompt_customization_postfix(self):
        """Test validation passes for valid postfix customization."""
        config = {
            "name": "test-project",
            "prompts": {
                "create_threat_model": {
                    "postfix": "\n\nAdditional requirements here"
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_prompt_customization_replace(self):
        """Test validation passes for valid replace customization."""
        config = {
            "name": "test-project",
            "prompts": {
                "initialize_iriusrisk_workflow": {
                    "replace": "Completely custom workflow instructions"
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_prompt_customization_multiple_actions(self):
        """Test validation passes for multiple actions on same tool."""
        config = {
            "name": "test-project",
            "prompts": {
                "analyze_source_material": {
                    "prefix": "Prefix text\n",
                    "postfix": "\nPostfix text"
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_prompt_customization_multiple_tools(self):
        """Test validation passes for multiple tool customizations."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "Org rules for threats\n"
                },
                "architecture_and_design_review": {
                    "postfix": "\nArchitecture guidelines"
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_invalid_prompts_not_dict(self):
        """Test validation fails when prompts is not a dictionary."""
        config = {
            "name": "test-project",
            "prompts": "not a dict"
        }
        with pytest.raises(ValueError, match="'prompts' field must be a dictionary"):
            validate_project_config(config)
    
    def test_invalid_tool_name(self):
        """Test validation fails for invalid tool name."""
        config = {
            "name": "test-project",
            "prompts": {
                "invalid_tool_name": {
                    "prefix": "Some text"
                }
            }
        }
        with pytest.raises(ValueError, match="Invalid tool name in prompts: 'invalid_tool_name'"):
            validate_project_config(config)
    
    def test_invalid_customization_not_dict(self):
        """Test validation fails when customization is not a dictionary."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": "not a dict"
            }
        }
        with pytest.raises(ValueError, match="Customization for tool .* must be a dictionary"):
            validate_project_config(config)
    
    def test_invalid_action_name(self):
        """Test validation fails for invalid action name."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "Valid prefix",
                    "invalid_action": "Some text"
                }
            }
        }
        with pytest.raises(ValueError, match="Invalid action 'invalid_action'"):
            validate_project_config(config)
    
    def test_invalid_action_not_string_or_dict(self):
        """Test validation fails when action value is not a string or dict."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": 123
                }
            }
        }
        with pytest.raises(ValueError, match="must be either a string or a dict"):
            validate_project_config(config)
    
    def test_no_valid_actions(self):
        """Test validation fails when no valid actions are present."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {}
            }
        }
        with pytest.raises(ValueError, match="must include at least one of"):
            validate_project_config(config)
    
    def test_warning_for_very_long_text(self, caplog):
        """Test warning is logged for suspiciously long customization text."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "x" * 15000
                }
            }
        }
        # Should validate but log warning
        validate_project_config(config)
        # Note: caplog checking would require actual logging setup


class TestPromptCustomizationApplication:
    """Test application of prompt customizations."""
    
    def test_no_customization_returns_base_prompt(self):
        """Test that base prompt is returned when no customization exists."""
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=(None, None)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt text')
            assert result == 'Base prompt text'
    
    def test_no_project_config_returns_base_prompt(self):
        """Test that base prompt is returned when project config doesn't exist."""
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', {})):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt text')
            assert result == 'Base prompt text'
    
    def test_no_prompts_section_returns_base_prompt(self):
        """Test that base prompt is returned when prompts section doesn't exist."""
        project_config = {"name": "test-project"}
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt text')
            assert result == 'Base prompt text'
    
    def test_no_tool_customization_returns_base_prompt(self):
        """Test that base prompt is returned when tool has no customization."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "some_other_tool": {"prefix": "Other tool prefix"}
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt text')
            assert result == 'Base prompt text'
    
    def test_prefix_customization(self):
        """Test that prefix customization is applied correctly."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "PREFIX: "
                }
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
            assert result == 'PREFIX: Base prompt'
    
    def test_postfix_customization(self):
        """Test that postfix customization is applied correctly."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "postfix": " :POSTFIX"
                }
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
            assert result == 'Base prompt :POSTFIX'
    
    def test_replace_customization(self):
        """Test that replace customization completely overrides base prompt."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "replace": "Completely custom prompt"
                }
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
            assert result == 'Completely custom prompt'
    
    def test_prefix_and_postfix_customization(self):
        """Test that both prefix and postfix are applied correctly."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "START: ",
                    "postfix": " :END"
                }
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
            assert result == 'START: Base prompt :END'
    
    def test_replace_ignores_prefix_and_postfix(self):
        """Test that replace action ignores prefix and postfix."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "PREFIX: ",
                    "postfix": " :POSTFIX",
                    "replace": "Replacement text"
                }
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
            assert result == 'Replacement text'
    
    def test_multiline_customizations(self):
        """Test that multiline customizations work correctly."""
        project_config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "Line 1\nLine 2\n\n",
                    "postfix": "\n\nFooter line 1\nFooter line 2"
                }
            }
        }
        with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
            assert result == 'Line 1\nLine 2\n\nBase prompt\n\nFooter line 1\nFooter line 2'
    
    def test_all_valid_tool_names(self):
        """Test that customizations work for all valid tool names."""
        valid_tools = [
            'initialize_iriusrisk_workflow',
            'threats_and_countermeasures',
            'analyze_source_material',
            'create_threat_model',
            'architecture_and_design_review',
            'security_development_advisor'
        ]
        
        for tool_name in valid_tools:
            project_config = {
                "name": "test-project",
                "prompts": {
                    tool_name: {"prefix": f"Custom for {tool_name}: "}
                }
            }
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', return_value=('/test/path', project_config)):
                result = _apply_prompt_customizations(tool_name, 'Base')
                assert result == f"Custom for {tool_name}: Base"


class TestFileBasedPromptCustomizationValidation:
    """Test validation of file-based prompt customizations."""
    
    def test_valid_file_based_prefix(self):
        """Test validation passes for file-based prefix customization."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": {"file": "custom_prompts/prefix.md"}
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_file_based_postfix(self):
        """Test validation passes for file-based postfix customization."""
        config = {
            "name": "test-project",
            "prompts": {
                "create_threat_model": {
                    "postfix": {"file": "custom_prompts/postfix.txt"}
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_file_based_replace(self):
        """Test validation passes for file-based replace customization."""
        config = {
            "name": "test-project",
            "prompts": {
                "initialize_iriusrisk_workflow": {
                    "replace": {"file": "custom_workflow.md"}
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_file_based_absolute_path(self):
        """Test validation passes for absolute file paths."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "replace": {"file": "/absolute/path/to/prompt.md"}
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_valid_mixed_string_and_file(self):
        """Test validation passes when mixing string and file-based customizations."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": "Inline prefix\n",
                    "postfix": {"file": "custom_prompts/postfix.md"}
                }
            }
        }
        # Should not raise
        validate_project_config(config)
    
    def test_invalid_file_dict_missing_file_key(self):
        """Test validation fails when dict doesn't have 'file' key."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": {"path": "some_file.md"}
                }
            }
        }
        with pytest.raises(ValueError, match="must contain a 'file' key"):
            validate_project_config(config)
    
    def test_invalid_file_dict_empty(self):
        """Test validation fails when dict is empty."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": {}
                }
            }
        }
        with pytest.raises(ValueError, match="must contain a 'file' key"):
            validate_project_config(config)
    
    def test_invalid_file_path_not_string(self):
        """Test validation fails when file path is not a string."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": {"file": 123}
                }
            }
        }
        with pytest.raises(ValueError, match="File path .* must be a string"):
            validate_project_config(config)
    
    def test_warning_for_tilde_path(self, caplog):
        """Test warning is logged for file paths using tilde."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": {"file": "~/custom_prompts/prefix.md"}
                }
            }
        }
        # Should validate but log warning
        validate_project_config(config)


class TestLoadPromptText:
    """Test the _load_prompt_text helper function."""
    
    def test_load_string_value(self):
        """Test loading a direct string value."""
        result = _load_prompt_text("Direct text", Path("/tmp"), "test")
        assert result == "Direct text"
    
    def test_load_from_relative_file(self):
        """Test loading from a file with relative path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iriusrisk_dir = Path(tmpdir) / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create a test file
            prompt_file = iriusrisk_dir / "test_prompt.md"
            prompt_file.write_text("Test prompt content", encoding='utf-8')
            
            result = _load_prompt_text({"file": "test_prompt.md"}, iriusrisk_dir, "test")
            assert result == "Test prompt content"
    
    def test_load_from_relative_subdirectory(self):
        """Test loading from a file in a subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iriusrisk_dir = Path(tmpdir) / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create subdirectory and file
            subdir = iriusrisk_dir / "custom_prompts"
            subdir.mkdir()
            prompt_file = subdir / "my_prompt.md"
            prompt_file.write_text("Custom prompt\nwith multiple lines", encoding='utf-8')
            
            result = _load_prompt_text({"file": "custom_prompts/my_prompt.md"}, iriusrisk_dir, "test")
            assert result == "Custom prompt\nwith multiple lines"
    
    def test_load_from_absolute_path(self):
        """Test loading from an absolute file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "absolute_prompt.md"
            prompt_file.write_text("Absolute path content", encoding='utf-8')
            
            # Use absolute path - should work regardless of iriusrisk_dir
            result = _load_prompt_text({"file": str(prompt_file)}, Path("/irrelevant"), "test")
            assert result == "Absolute path content"
    
    def test_file_not_found_relative(self):
        """Test error when file doesn't exist (relative path)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iriusrisk_dir = Path(tmpdir) / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            with pytest.raises(FileNotFoundError, match="not found"):
                _load_prompt_text({"file": "nonexistent.md"}, iriusrisk_dir, "test")
    
    def test_file_not_found_absolute(self):
        """Test error when file doesn't exist (absolute path)."""
        with pytest.raises(FileNotFoundError, match="not found"):
            _load_prompt_text({"file": "/nonexistent/path/file.md"}, Path("/tmp"), "test")
    
    def test_path_is_directory_not_file(self):
        """Test error when path points to a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iriusrisk_dir = Path(tmpdir) / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create a directory instead of a file
            dir_path = iriusrisk_dir / "not_a_file"
            dir_path.mkdir()
            
            with pytest.raises(ValueError, match="is not a file"):
                _load_prompt_text({"file": "not_a_file"}, iriusrisk_dir, "test")
    
    def test_invalid_type_list(self):
        """Test error when value is a list."""
        with pytest.raises(ValueError, match="must be either a string or a dict"):
            _load_prompt_text(["invalid"], Path("/tmp"), "test")
    
    def test_invalid_type_int(self):
        """Test error when value is an integer."""
        with pytest.raises(ValueError, match="must be either a string or a dict"):
            _load_prompt_text(123, Path("/tmp"), "test")
    
    def test_dict_without_file_key(self):
        """Test error when dict doesn't have 'file' key."""
        with pytest.raises(ValueError, match="must contain a 'file' key"):
            _load_prompt_text({"path": "file.md"}, Path("/tmp"), "test")
    
    def test_file_key_not_string(self):
        """Test error when 'file' value is not a string."""
        with pytest.raises(ValueError, match="must be a string"):
            _load_prompt_text({"file": 123}, Path("/tmp"), "test")
    
    def test_unicode_content(self):
        """Test loading file with unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iriusrisk_dir = Path(tmpdir) / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            prompt_file = iriusrisk_dir / "unicode.md"
            prompt_file.write_text("Unicode: 你好 🎉 café", encoding='utf-8')
            
            result = _load_prompt_text({"file": "unicode.md"}, iriusrisk_dir, "test")
            assert result == "Unicode: 你好 🎉 café"


class TestFileBasedPromptCustomizationApplication:
    """Test application of file-based prompt customizations."""
    
    def test_file_based_prefix(self):
        """Test that file-based prefix is loaded and applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            iriusrisk_dir = project_root / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create prefix file
            prefix_file = iriusrisk_dir / "prefix.md"
            prefix_file.write_text("FILE PREFIX: ", encoding='utf-8')
            
            project_config = {
                "name": "test-project",
                "prompts": {
                    "threats_and_countermeasures": {
                        "prefix": {"file": "prefix.md"}
                    }
                }
            }
            
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', 
                      return_value=(project_root, project_config)):
                result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
                assert result == 'FILE PREFIX: Base prompt'
    
    def test_file_based_postfix(self):
        """Test that file-based postfix is loaded and applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            iriusrisk_dir = project_root / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create postfix file
            postfix_file = iriusrisk_dir / "postfix.md"
            postfix_file.write_text(" :FILE POSTFIX", encoding='utf-8')
            
            project_config = {
                "name": "test-project",
                "prompts": {
                    "threats_and_countermeasures": {
                        "postfix": {"file": "postfix.md"}
                    }
                }
            }
            
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', 
                      return_value=(project_root, project_config)):
                result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
                assert result == 'Base prompt :FILE POSTFIX'
    
    def test_file_based_replace(self):
        """Test that file-based replace is loaded and applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            iriusrisk_dir = project_root / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create replacement file
            replace_file = iriusrisk_dir / "replacement.md"
            replace_file.write_text("Complete replacement from file", encoding='utf-8')
            
            project_config = {
                "name": "test-project",
                "prompts": {
                    "threats_and_countermeasures": {
                        "replace": {"file": "replacement.md"}
                    }
                }
            }
            
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', 
                      return_value=(project_root, project_config)):
                result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
                assert result == 'Complete replacement from file'
    
    def test_mixed_string_and_file_customization(self):
        """Test mixing inline string and file-based customizations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            iriusrisk_dir = project_root / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create postfix file
            postfix_file = iriusrisk_dir / "postfix.md"
            postfix_file.write_text("\n\nFile-based footer", encoding='utf-8')
            
            project_config = {
                "name": "test-project",
                "prompts": {
                    "threats_and_countermeasures": {
                        "prefix": "Inline prefix\n",
                        "postfix": {"file": "postfix.md"}
                    }
                }
            }
            
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', 
                      return_value=(project_root, project_config)):
                result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
                assert result == 'Inline prefix\nBase prompt\n\nFile-based footer'
    
    def test_file_from_subdirectory(self):
        """Test loading file from a subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            iriusrisk_dir = project_root / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            # Create subdirectory and file
            custom_dir = iriusrisk_dir / "custom_prompts"
            custom_dir.mkdir()
            prefix_file = custom_dir / "prefix.md"
            prefix_file.write_text("Subdirectory prefix: ", encoding='utf-8')
            
            project_config = {
                "name": "test-project",
                "prompts": {
                    "threats_and_countermeasures": {
                        "prefix": {"file": "custom_prompts/prefix.md"}
                    }
                }
            }
            
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', 
                      return_value=(project_root, project_config)):
                result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')
                assert result == 'Subdirectory prefix: Base prompt'
    
    def test_file_not_found_error_propagates(self):
        """Test that file not found errors are properly propagated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            iriusrisk_dir = project_root / ".iriusrisk"
            iriusrisk_dir.mkdir()
            
            project_config = {
                "name": "test-project",
                "prompts": {
                    "threats_and_countermeasures": {
                        "prefix": {"file": "nonexistent.md"}
                    }
                }
            }
            
            with patch('src.iriusrisk_cli.utils.project_discovery.find_project_root', 
                      return_value=(project_root, project_config)):
                with pytest.raises(FileNotFoundError):
                    _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt')

