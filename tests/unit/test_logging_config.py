"""
Unit tests for the new CLI logging configuration.

This module tests the new logging behavior including CLI options,
environment variables, and different logging modes.
"""

import pytest
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open
from click.testing import CliRunner

from iriusrisk_cli.utils.logging_config import configure_cli_logging, IriusRiskFormatter
from iriusrisk_cli.main import cli


class TestConfigureCliLogging:
    """Test the new configure_cli_logging function."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_default_configuration_quiet_mode(self):
        """Test default configuration creates quiet mode (ERROR level only)."""
        configure_cli_logging()
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR
        
        # Should have no handlers in quiet mode
        assert len(root_logger.handlers) == 0
    
    def test_verbose_mode_configuration(self):
        """Test verbose mode enables INFO level logging to stderr."""
        configure_cli_logging(verbose=True)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        # Should have stderr handler
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.INFO
    
    def test_debug_mode_configuration(self):
        """Test debug mode enables DEBUG level logging to stderr."""
        configure_cli_logging(debug=True)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        
        # Should have stderr handler
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.DEBUG
    
    def test_quiet_mode_suppresses_output(self):
        """Test quiet mode suppresses all output."""
        configure_cli_logging(quiet=True)
        
        root_logger = logging.getLogger()
        # Should have no handlers in quiet mode
        assert len(root_logger.handlers) == 0
    
    def test_file_logging_configuration(self):
        """Test file logging creates file handler."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            log_file = tmp_file.name
        
        try:
            configure_cli_logging(debug=True, log_file=log_file)
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG
            
            # Should have both stderr and file handlers
            assert len(root_logger.handlers) == 2
            
            # Check handlers
            handler_types = [type(h).__name__ for h in root_logger.handlers]
            assert 'StreamHandler' in handler_types  # stderr
            assert 'FileHandler' in handler_types    # file
            
        finally:
            # Cleanup
            Path(log_file).unlink(missing_ok=True)
    
    def test_log_level_override(self):
        """Test explicit log level override."""
        configure_cli_logging(log_level="WARNING")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
    
    def test_debug_implies_verbose(self):
        """Test that debug mode implies verbose mode."""
        configure_cli_logging(debug=True)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1  # stderr handler
    
    def test_third_party_logger_suppression(self):
        """Test that third-party loggers are suppressed."""
        configure_cli_logging(debug=True)
        
        requests_logger = logging.getLogger("requests")
        urllib3_logger = logging.getLogger("urllib3")
        charset_normalizer_logger = logging.getLogger("charset_normalizer")
        httpcore_logger = logging.getLogger("httpcore")
        httpx_logger = logging.getLogger("httpx")
        asyncio_logger = logging.getLogger("asyncio")
        
        assert requests_logger.level == logging.WARNING
        assert urllib3_logger.level == logging.WARNING
        assert charset_normalizer_logger.level == logging.WARNING
        assert httpcore_logger.level == logging.WARNING
        assert httpx_logger.level == logging.WARNING
        assert asyncio_logger.level == logging.WARNING


class TestIriusRiskFormatter:
    """Test the custom IriusRisk formatter."""
    
    def test_console_output_formatting(self):
        """Test console output formatting with colors."""
        formatter = IriusRiskFormatter()
        
        # Create a mock record with console_output attribute
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.console_output = True
        
        formatted = formatter.format(record)
        
        # Should contain ANSI color codes and the message
        assert "\033[32m" in formatted  # Green for INFO
        assert "INFO" in formatted
        assert "Test message" in formatted
        assert "\033[0m" in formatted   # Reset color
    
    def test_file_output_formatting(self):
        """Test file output formatting without colors."""
        formatter = IriusRiskFormatter()
        
        # Create a mock record without console_output attribute
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain timestamp, logger name, level, and message
        assert "test.logger" in formatted
        assert "ERROR" in formatted
        assert "Error message" in formatted
        # Should not contain ANSI color codes
        assert "\033[" not in formatted


class TestCLILoggingOptions:
    """Test CLI logging options integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_default_cli_behavior(self):
        """Test default CLI behavior (quiet mode)."""
        result = self.runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
        
        # Should not have created any log files
        logs_dir = Path("logs")
        if logs_dir.exists():
            log_files_before = list(logs_dir.glob("*.log"))
            # Run command again
            self.runner.invoke(cli, ['--version'])
            log_files_after = list(logs_dir.glob("*.log"))
            # Should not have created new log files
            assert len(log_files_after) == len(log_files_before)
    
    def test_verbose_cli_option(self):
        """Test --verbose CLI option."""
        result = self.runner.invoke(cli, ['--verbose', '--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
    
    def test_debug_cli_option(self):
        """Test --debug CLI option."""
        result = self.runner.invoke(cli, ['--debug', '--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
    
    def test_quiet_cli_option(self):
        """Test --quiet CLI option."""
        result = self.runner.invoke(cli, ['--quiet', '--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
    
    def test_log_file_cli_option(self):
        """Test --log-file CLI option."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp_file:
            log_file = tmp_file.name
        
        try:
            result = self.runner.invoke(cli, ['--debug', '--log-file', log_file, '--version'])
            
            assert result.exit_code == 0
            assert "IriusRisk CLI version" in result.output
            
            # Log file should exist and contain logs
            assert Path(log_file).exists()
            
        finally:
            # Cleanup
            Path(log_file).unlink(missing_ok=True)
    
    def test_log_level_cli_option(self):
        """Test --log-level CLI option."""
        result = self.runner.invoke(cli, ['--log-level', 'INFO', '--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
    
    def test_invalid_log_level(self):
        """Test invalid log level option."""
        result = self.runner.invoke(cli, ['--log-level', 'INVALID', '--version'])
        
        # Should fail with invalid choice
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid choice" in result.output.lower()


class TestEnvironmentVariables:
    """Test environment variable support for logging."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    @patch.dict(os.environ, {'IRIUSRISK_DEBUG': '1'})
    def test_debug_environment_variable(self):
        """Test IRIUSRISK_DEBUG environment variable."""
        result = self.runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
    
    @patch.dict(os.environ, {'IRIUSRISK_DEBUG': 'true'})
    def test_debug_environment_variable_true(self):
        """Test IRIUSRISK_DEBUG=true environment variable."""
        result = self.runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "IriusRisk CLI version" in result.output
    
    @patch.dict(os.environ, {'IRIUSRISK_LOG_FILE': 'env_test.log'})
    def test_log_file_environment_variable(self):
        """Test IRIUSRISK_LOG_FILE environment variable."""
        try:
            result = self.runner.invoke(cli, ['--debug', '--version'])
            
            assert result.exit_code == 0
            assert "IriusRisk CLI version" in result.output
            
            # Log file should exist
            assert Path('env_test.log').exists()
            
        finally:
            # Cleanup
            Path('env_test.log').unlink(missing_ok=True)
    
    def test_cli_options_override_environment(self):
        """Test that CLI options override environment variables."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp_file:
            cli_log_file = tmp_file.name
        
        try:
            with patch.dict(os.environ, {'IRIUSRISK_LOG_FILE': 'env_test.log'}):
                result = self.runner.invoke(cli, ['--debug', '--log-file', cli_log_file, '--version'])
                
                assert result.exit_code == 0
                
                # CLI option should override environment variable
                assert Path(cli_log_file).exists()
                assert not Path('env_test.log').exists()
                
        finally:
            # Cleanup
            Path(cli_log_file).unlink(missing_ok=True)
            Path('env_test.log').unlink(missing_ok=True)


class TestLoggingIntegration:
    """Integration tests for logging with actual CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_help_command_with_logging_options(self):
        """Test help command shows logging options."""
        result = self.runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "--verbose" in result.output
        assert "--debug" in result.output
        assert "--quiet" in result.output
        assert "--log-file" in result.output
        assert "--log-level" in result.output
    
    def test_detailed_help_includes_logging_section(self):
        """Test detailed help includes logging information."""
        result = self.runner.invoke(cli, ['help'])
        
        assert result.exit_code == 0
        assert "LOGGING OPTIONS:" in result.output
        assert "--verbose" in result.output
        assert "--debug" in result.output
        assert "IRIUSRISK_DEBUG" in result.output
    
    def test_no_automatic_log_files_created(self):
        """Test that no automatic log files are created."""
        logs_dir = Path("logs")
        
        # Count existing log files
        existing_logs = list(logs_dir.glob("*.log")) if logs_dir.exists() else []
        initial_count = len(existing_logs)
        
        # Run a command
        result = self.runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        
        # Check that no new log files were created
        current_logs = list(logs_dir.glob("*.log")) if logs_dir.exists() else []
        current_count = len(current_logs)
        
        assert current_count == initial_count, "No new log files should be created by default"
