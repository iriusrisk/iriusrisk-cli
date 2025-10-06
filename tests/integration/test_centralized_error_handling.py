"""
Test centralized error handling system.

This module tests the new centralized error handling, exception hierarchy,
and logging system implemented in Phase 3 of the refactoring.
"""

import pytest
import logging
import requests
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from iriusrisk_cli.exceptions import (
    IriusRiskError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    APIError,
    ResourceNotFoundError,
    FileOperationError,
    ProjectError,
    ExitCodes
)
from iriusrisk_cli.utils.error_handling import (
    handle_api_error,
    handle_file_error,
    safe_api_call,
    validate_required_param,
    validate_file_exists,
    get_error_message,
    handle_cli_error_decorator
)
from iriusrisk_cli.utils.logging_config import setup_logging, get_logger


class TestExceptionHierarchy:
    """Test the custom exception hierarchy."""
    
    def test_base_exception_creation(self):
        """Test IriusRiskError base exception."""
        error = IriusRiskError("Test error", exit_code=42, details={"key": "value"})
        
        assert error.message == "Test error"
        assert error.exit_code == 42
        assert error.details == {"key": "value"}
        assert error.user_message == "Test error"
        assert str(error) == "Test error"
    
    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Invalid field", field="test_field")
        
        assert error.exit_code == ExitCodes.VALIDATION_ERROR
        assert error.field == "test_field"
        assert "Invalid input" in error.user_message
        assert error.details["field"] == "test_field"
    
    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        error = AuthenticationError("Auth failed")
        
        assert error.exit_code == ExitCodes.AUTHENTICATION_ERROR
        assert "Authentication failed" in error.user_message
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError exception."""
        error = ResourceNotFoundError("Project", "test-123")
        
        assert error.exit_code == ExitCodes.RESOURCE_NOT_FOUND
        assert error.resource_type == "Project"
        assert error.resource_id == "test-123"
        assert "Project 'test-123' not found" in error.message
    
    def test_api_error_with_response_data(self):
        """Test APIError with response data."""
        response_data = {"message": "Bad request", "code": 400}
        error = APIError("Request failed", status_code=400, response_data=response_data)
        
        assert error.exit_code == ExitCodes.API_ERROR
        assert error.status_code == 400
        assert error.response_data == response_data
        assert error.details["status_code"] == 400
        assert error.details["response_data"] == response_data


class TestErrorHandling:
    """Test error handling utilities."""
    
    def test_handle_api_error_401(self):
        """Test handling of 401 authentication errors."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid token"}
        mock_response.text = "Unauthorized"
        
        mock_error = requests.RequestException("401 error")
        mock_error.response = mock_response
        
        result = handle_api_error(mock_error, "test operation")
        
        assert isinstance(result, AuthenticationError)
        assert result.exit_code == ExitCodes.AUTHENTICATION_ERROR
        assert "test operation failed" in result.message
    
    def test_handle_api_error_404(self):
        """Test handling of 404 not found errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not found"}
        mock_response.text = "Not Found"
        
        mock_error = requests.RequestException("404 error")
        mock_error.response = mock_response
        
        result = handle_api_error(mock_error, "get project")
        
        assert isinstance(result, ResourceNotFoundError)
        assert result.exit_code == ExitCodes.RESOURCE_NOT_FOUND
        assert result.resource_type == "Project"
    
    def test_handle_api_error_network(self):
        """Test handling of network errors (no response)."""
        mock_error = requests.RequestException("Connection failed")
        # No response attribute to simulate network error
        
        result = handle_api_error(mock_error, "test operation")
        
        assert isinstance(result, NetworkError)
        assert result.exit_code == ExitCodes.NETWORK_ERROR
        assert "test operation failed" in result.message
    
    def test_handle_file_error(self):
        """Test file error handling."""
        original_error = FileNotFoundError("File not found")
        result = handle_file_error(original_error, "read", "/path/to/file")
        
        assert isinstance(result, FileOperationError)
        assert result.operation == "read"
        assert result.file_path == "/path/to/file"
        assert result.original_error == original_error
    
    def test_safe_api_call_success(self):
        """Test successful API call through safe_api_call."""
        mock_func = Mock(return_value={"success": True})
        
        result = safe_api_call(mock_func, "arg1", "arg2", operation="test op", kwarg1="value1")
        
        assert result == {"success": True}
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    
    def test_safe_api_call_request_exception(self):
        """Test API call that raises RequestException."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Server error"}
        
        mock_error = requests.RequestException("Server error")
        mock_error.response = mock_response
        
        mock_func = Mock(side_effect=mock_error)
        
        with pytest.raises(APIError) as exc_info:
            safe_api_call(mock_func, operation="test operation")
        
        assert exc_info.value.status_code == 500
    
    def test_validate_required_param_success(self):
        """Test successful parameter validation."""
        result = validate_required_param("test_value", "test_param", str)
        assert result == "test_value"
    
    def test_validate_required_param_none(self):
        """Test validation failure for None value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_required_param(None, "test_param")
        
        assert exc_info.value.field == "test_param"
        assert "required" in exc_info.value.message
    
    def test_validate_required_param_wrong_type(self):
        """Test validation failure for wrong type."""
        with pytest.raises(ValidationError) as exc_info:
            validate_required_param(123, "test_param", str)
        
        assert exc_info.value.field == "test_param"
        assert "must be of type str" in exc_info.value.message
    
    @patch('os.path.exists')
    @patch('os.access')
    def test_validate_file_exists_success(self, mock_access, mock_exists):
        """Test successful file validation."""
        mock_exists.return_value = True
        mock_access.return_value = True
        
        result = validate_file_exists("/path/to/file", "read")
        assert result == "/path/to/file"
    
    @patch('os.path.exists')
    def test_validate_file_exists_not_found(self, mock_exists):
        """Test file validation failure for non-existent file."""
        mock_exists.return_value = False
        
        with pytest.raises(FileOperationError) as exc_info:
            validate_file_exists("/path/to/file", "read")
        
        assert exc_info.value.operation == "read"
        assert exc_info.value.file_path == "/path/to/file"
    
    def test_get_error_message_with_template(self):
        """Test error message template formatting."""
        message = get_error_message("project_not_found", project_id="test-123")
        assert "Project 'test-123' not found" in message
        assert "iriusrisk project list" in message
    
    def test_get_error_message_missing_template(self):
        """Test error message with non-existent template."""
        message = get_error_message("non_existent_template")
        assert message == "An error occurred"


class TestCLIErrorDecorator:
    """Test the CLI error handling decorator."""
    
    def test_handle_cli_error_decorator_success(self):
        """Test decorator with successful function."""
        @handle_cli_error_decorator
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
    
    def test_handle_cli_error_decorator_iriusrisk_error(self):
        """Test decorator with IriusRiskError."""
        @handle_cli_error_decorator
        def test_func():
            raise ValidationError("Test error")
        
        with pytest.raises(SystemExit) as exc_info:
            test_func()
        
        assert exc_info.value.code == ExitCodes.VALIDATION_ERROR
    
    def test_handle_cli_error_decorator_request_exception(self):
        """Test decorator with requests.RequestException."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        
        mock_error = requests.RequestException("Auth error")
        mock_error.response = mock_response
        
        @handle_cli_error_decorator
        def test_func():
            raise mock_error
        
        with pytest.raises(SystemExit) as exc_info:
            test_func()
        
        assert exc_info.value.code == ExitCodes.AUTHENTICATION_ERROR
    
    def test_handle_cli_error_decorator_unexpected_error(self):
        """Test decorator with unexpected exception."""
        @handle_cli_error_decorator
        def test_func():
            raise ValueError("Unexpected error")
        
        with pytest.raises(SystemExit) as exc_info:
            test_func()
        
        assert exc_info.value.code == ExitCodes.GENERAL_ERROR


class TestLoggingConfiguration:
    """Test legacy logging configuration (for backward compatibility)."""
    
    def test_setup_logging_creates_logger(self):
        """Test that setup_logging creates a properly configured logger."""
        logger = setup_logging(component="test", log_level="DEBUG")
        
        assert logger.name == "iriusrisk_cli.test"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0
    
    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns a configured logger."""
        # Note: get_logger is deprecated in favor of standard logging.getLogger
        logger = get_logger("test_component")
        
        assert logger.name == "iriusrisk_cli.test_component"
        assert len(logger.handlers) > 0
    
    @patch('iriusrisk_cli.utils.logging_config.Path.mkdir')
    def test_logging_creates_log_directory(self, mock_mkdir):
        """Test that logging setup creates log directory."""
        setup_logging(component="test")
        mock_mkdir.assert_called()


class TestErrorHandlingIntegration:
    """Integration tests for error handling with CLI commands."""
    
    def test_components_command_with_error_handling(self):
        """Test that components command uses centralized error handling."""
        # This test verifies that the updated components command
        # properly integrates with the error handling system
        from iriusrisk_cli.commands.components import component
        
        runner = CliRunner()
        
        # Test with invalid page parameter
        result = runner.invoke(component, ['list', '--page', '-1'])
        
        # Should exit with validation error code
        assert result.exit_code == ExitCodes.VALIDATION_ERROR
        assert "❌" in result.output  # Error message should be formatted consistently


class TestExitCodes:
    """Test exit code constants."""
    
    def test_exit_codes_are_unique(self):
        """Test that all exit codes are unique."""
        exit_codes = [
            ExitCodes.SUCCESS,
            ExitCodes.GENERAL_ERROR,
            ExitCodes.CONFIGURATION_ERROR,
            ExitCodes.AUTHENTICATION_ERROR,
            ExitCodes.AUTHORIZATION_ERROR,
            ExitCodes.NETWORK_ERROR,
            ExitCodes.API_ERROR,
            ExitCodes.VALIDATION_ERROR,
            ExitCodes.RESOURCE_NOT_FOUND,
            ExitCodes.FILE_OPERATION_ERROR,
            ExitCodes.PROJECT_ERROR,
            ExitCodes.DATA_PROCESSING_ERROR,
            ExitCodes.TIMEOUT_ERROR
        ]
        
        assert len(exit_codes) == len(set(exit_codes)), "Exit codes must be unique"
    
    def test_exit_codes_are_integers(self):
        """Test that all exit codes are integers."""
        for attr_name in dir(ExitCodes):
            if not attr_name.startswith('_'):
                value = getattr(ExitCodes, attr_name)
                assert isinstance(value, int), f"{attr_name} must be an integer"
