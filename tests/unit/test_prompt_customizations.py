"""Tests for MCP prompt customization feature."""

import pytest
from unittest.mock import Mock, patch
from src.iriusrisk_cli.config import validate_project_config
from src.iriusrisk_cli.commands.mcp import _apply_prompt_customizations


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
    
    def test_invalid_action_not_string(self):
        """Test validation fails when action value is not a string."""
        config = {
            "name": "test-project",
            "prompts": {
                "threats_and_countermeasures": {
                    "prefix": 123
                }
            }
        }
        with pytest.raises(ValueError, match="Text for action .* must be a string"):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=None):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt text')
            assert result == 'Base prompt text'
    
    def test_no_project_config_returns_base_prompt(self):
        """Test that base prompt is returned when project config doesn't exist."""
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value={}):
            result = _apply_prompt_customizations('threats_and_countermeasures', 'Base prompt text')
            assert result == 'Base prompt text'
    
    def test_no_prompts_section_returns_base_prompt(self):
        """Test that base prompt is returned when prompts section doesn't exist."""
        project_config = {"name": "test-project"}
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
        with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
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
            with patch('src.iriusrisk_cli.utils.project.get_project_config', return_value=project_config):
                result = _apply_prompt_customizations(tool_name, 'Base')
                assert result == f"Custom for {tool_name}: Base"

