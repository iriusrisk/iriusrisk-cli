"""Unit tests for the CLI test command."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from src.iriusrisk_cli.main import test
from src.iriusrisk_cli.cli_context import CliContext
from src.iriusrisk_cli.services.health_service import HealthService


class TestCliTestCommand:
    """Test cases for the CLI test command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_health_service = Mock(spec=HealthService)
        self.mock_container = Mock()
        self.mock_container.get.return_value = self.mock_health_service
        self.mock_cli_context = Mock(spec=CliContext)
        self.mock_cli_context.container = self.mock_container

    @patch('src.iriusrisk_cli.main.setup_cli_context')
    def test_test_command_success_with_version(self, mock_setup_cli_context):
        """Test successful test command showing version."""
        # Arrange
        mock_setup_cli_context.return_value = self.mock_cli_context
        self.mock_health_service.get_instance_info.return_value = {"version": "2.15.0"}

        # Act
        result = self.runner.invoke(test)

        # Assert
        assert result.exit_code == 0
        assert "Testing connection to IriusRisk..." in result.output
        assert "✓ Connection successful!" in result.output
        assert "✓ IriusRisk version: 2.15.0" in result.output
        self.mock_health_service.get_instance_info.assert_called_once()

    @patch('src.iriusrisk_cli.main.setup_cli_context')
    def test_test_command_success_unknown_version(self, mock_setup_cli_context):
        """Test successful test command with unknown version."""
        # Arrange
        mock_setup_cli_context.return_value = self.mock_cli_context
        self.mock_health_service.get_instance_info.return_value = {}

        # Act
        result = self.runner.invoke(test)

        # Assert
        assert result.exit_code == 0
        assert "Testing connection to IriusRisk..." in result.output
        assert "✓ Connection successful!" in result.output
        assert "✓ IriusRisk version: unknown" in result.output

    @patch('src.iriusrisk_cli.main.setup_cli_context')
    def test_test_command_health_service_exception(self, mock_setup_cli_context):
        """Test test command when health service raises exception."""
        # Arrange
        mock_setup_cli_context.return_value = self.mock_cli_context
        self.mock_health_service.get_instance_info.side_effect = Exception("Connection failed")

        # Act
        result = self.runner.invoke(test)

        # Assert
        assert result.exit_code == 1
        assert "Testing connection to IriusRisk..." in result.output
        assert "Error testing connection:" in result.output

    @patch('src.iriusrisk_cli.main.setup_cli_context')
    def test_test_command_container_get_exception(self, mock_setup_cli_context):
        """Test test command when container.get raises exception."""
        # Arrange
        mock_setup_cli_context.return_value = self.mock_cli_context
        self.mock_container.get.side_effect = Exception("Service not found")

        # Act
        result = self.runner.invoke(test)

        # Assert
        assert result.exit_code == 1
        assert "Error testing connection:" in result.output

    def test_test_command_with_existing_context(self):
        """Test test command when context already exists."""
        # Arrange
        self.mock_health_service.get_instance_info.return_value = {"version": "2.14.5"}

        # Act
        result = self.runner.invoke(test, obj=self.mock_cli_context)

        # Assert
        assert result.exit_code == 0
        assert "✓ IriusRisk version: 2.14.5" in result.output
        self.mock_health_service.get_instance_info.assert_called_once()

    @patch('src.iriusrisk_cli.main.setup_cli_context')
    def test_test_command_setup_context_exception(self, mock_setup_cli_context):
        """Test test command when setup_cli_context raises exception."""
        # Arrange
        mock_setup_cli_context.side_effect = Exception("Config error")

        # Act
        result = self.runner.invoke(test)

        # Assert  
        # When setup_cli_context fails, the exception is not caught by handle_cli_error
        # so the command exits with the raw exception
        assert result.exit_code != 0
