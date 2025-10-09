"""
Centralized error handling utilities for IriusRisk CLI.

This module provides consistent error handling, logging, and user messaging
across all CLI commands and API operations.
"""

import sys
import logging
import traceback
from typing import Optional, Dict, Any, Union
from functools import wraps
import click
import requests

from ..exceptions import (
    IriusRiskError, 
    ConfigurationError,
    AuthenticationError, 
    AuthorizationError,
    NetworkError,
    APIError,
    ValidationError,
    ResourceNotFoundError,
    FileOperationError,
    ProjectError,
    DataProcessingError,
    TimeoutError,
    ExitCodes
)


logger = logging.getLogger(__name__)


def _is_retryable_error(status_code: int) -> bool:
    """Check if an HTTP status code indicates a retryable error.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        True if the error is retryable, False otherwise
    """
    # Retryable errors: rate limiting, server errors, and some client errors
    retryable_codes = {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        408,  # Request Timeout
    }
    return status_code in retryable_codes


def _get_logging_config():
    """Get logging configuration from CLI context if available."""
    try:
        import click
        ctx = click.get_current_context()
        if hasattr(ctx, 'obj') and ctx.obj and hasattr(ctx.obj, 'logging_config'):
            return ctx.obj.logging_config
    except:
        pass
    return None


def handle_api_error(error: requests.RequestException, operation: str = "API request") -> APIError:
    """Convert requests exceptions to appropriate IriusRisk exceptions.
    
    Args:
        error: The requests exception to convert
        operation: Description of the operation that failed
        
    Returns:
        APIError: Appropriate IriusRisk exception
    """
    if hasattr(error, 'response') and error.response is not None:
        status_code = error.response.status_code
        
        # Try to extract clean error message from response
        try:
            response_data = error.response.json()
            error_message = response_data.get('message', '')
        except:
            error_message = ''
            response_data = None
        
        # Map HTTP status codes to specific exceptions
        if status_code == 401:
            return AuthenticationError(
                message=f"{operation} failed: authentication required",
                details={'status_code': status_code, 'response_data': response_data}
            )
        elif status_code == 403:
            return AuthorizationError(
                message=f"{operation} failed: permission denied",
                details={'status_code': status_code, 'response_data': response_data}
            )
        elif status_code == 404:
            # Extract resource info if possible
            resource_type = "Resource"
            resource_id = "unknown"
            if "project" in operation.lower():
                resource_type = "Project"
                # Try to extract project ID from operation string
                import re
                match = re.search(r"'([^']+)'", operation)
                if match:
                    resource_id = match.group(1)
            elif "threat" in operation.lower():
                resource_type = "Threat"
            elif "countermeasure" in operation.lower():
                resource_type = "Countermeasure"
            
            return ResourceNotFoundError(
                resource_type=resource_type,
                resource_id=resource_id,
                details={'status_code': status_code, 'response_data': response_data}
            )
        elif status_code == 400:
            # For 400 errors, provide context-specific messages
            user_friendly_message = error_message if error_message else operation
            
            # Special handling for common 400 scenarios
            if "project" in operation.lower() and "retrieving" in operation.lower():
                # 400 on project retrieval usually means invalid/non-existent project ID
                import re
                match = re.search(r"'([^']+)'", operation)
                if match:
                    project_id = match.group(1)
                    user_friendly_message = f"Project '{project_id}' not found or invalid"
                else:
                    user_friendly_message = "Project not found or invalid"
            
            return ValidationError(
                message=user_friendly_message,
                details={'status_code': status_code, 'response_data': response_data}
            )
        elif status_code >= 500:
            clean_message = error_message if error_message else "server error"
            return APIError(
                message=f"Server error during {operation}: {clean_message}",
                status_code=status_code,
                response_data=response_data
            )
        else:
            clean_message = error_message if error_message else f"HTTP {status_code}"
            return APIError(
                message=f"{operation} failed: {clean_message}",
                status_code=status_code,
                response_data=response_data
            )
    else:
        # Network-level error (no response)
        return NetworkError(
            message=f"Cannot connect to IriusRisk server",
            details={'original_error': str(error), 'operation': operation}
        )


def handle_file_error(error: Exception, operation: str, file_path: str) -> FileOperationError:
    """Convert file operation exceptions to FileOperationError.
    
    Args:
        error: The original exception
        operation: Description of the file operation
        file_path: Path to the file that caused the error
        
    Returns:
        FileOperationError: Appropriate file operation exception
    """
    return FileOperationError(
        operation=operation,
        file_path=file_path,
        original_error=error
    )


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None, operation: str = "operation") -> None:
    """Log an error with appropriate level and context.
    
    Args:
        error: The exception to log
        context: Additional context information
        operation: Description of the operation that failed
    """
    context = context or {}
    
    # Enhance context with operation information
    enhanced_context = {
        'operation': operation,
        'error_type': type(error).__name__,
        'timestamp': str(__import__('datetime').datetime.now()),
        **context
    }
    
    if isinstance(error, IriusRiskError):
        # Log IriusRisk errors at appropriate level with enhanced context
        if isinstance(error, (AuthenticationError, AuthorizationError)):
            logger.warning(f"Authentication/Authorization error during {operation}: {error.message}", extra=enhanced_context)
            logger.debug(f"Auth error context - operation: {operation}, user_message: {error.user_message}")
        elif isinstance(error, ValidationError):
            logger.info(f"Validation error during {operation}: {error.message}", extra=enhanced_context)
            if hasattr(error, 'field') and error.field:
                logger.debug(f"Validation failed for field: {error.field}")
        elif isinstance(error, ResourceNotFoundError):
            logger.info(f"Resource not found during {operation}: {error.message}", extra=enhanced_context)
            logger.debug(f"Resource details - type: {getattr(error, 'resource_type', 'unknown')}, "
                        f"id: {getattr(error, 'resource_id', 'unknown')}")
        elif isinstance(error, NetworkError):
            logger.error(f"Network error during {operation}: {error.message}", extra=enhanced_context)
            logger.debug(f"Network error may be recoverable - consider retry")
        elif isinstance(error, APIError):
            logger.error(f"API error during {operation}: {error.message}", extra=enhanced_context)
            if hasattr(error, 'status_code'):
                logger.debug(f"API error details - status: {error.status_code}, "
                           f"retryable: {_is_retryable_error(error.status_code)}")
        else:
            logger.error(f"IriusRisk error during {operation}: {error.message}", extra=enhanced_context)
            
        # Log details if available with better formatting
        if error.details:
            logger.debug(f"Error details for {operation}: {error.details}")
            
        
    else:
        # Log unexpected errors with full traceback and context
        logger.error(f"Unexpected error during {operation}: {str(error)}", extra=enhanced_context)
        logger.debug(f"Full traceback for {operation}: {traceback.format_exc()}")
        logger.debug(f"Error occurred with context: {enhanced_context}")


def display_error(error: Exception, verbose: bool = False, operation: str = "operation") -> None:
    """Display error message to user in consistent format.
    
    Args:
        error: The exception to display
        verbose: Whether to show detailed error information
        operation: Description of the operation that failed
    """
    # Check if we're in quiet mode
    logging_config = _get_logging_config()
    if logging_config and logging_config.get('quiet', False):
        return  # Don't display errors in quiet mode
    
    if isinstance(error, IriusRiskError):
        # Use user-friendly message for IriusRisk errors
        click.echo(f"❌ {error.user_message}", err=True)
        
        
        if verbose and error.details:
            click.echo(f"Details: {error.details}", err=True)
    else:
        # Generic error message for unexpected errors
        click.echo(f"❌ An unexpected error occurred during {operation}: {str(error)}", err=True)
        
        if verbose:
            click.echo(f"Traceback: {traceback.format_exc()}", err=True)


def get_exit_code(error: Exception) -> int:
    """Get appropriate exit code for an exception.
    
    Args:
        error: The exception to get exit code for
        
    Returns:
        int: Appropriate exit code
    """
    if isinstance(error, IriusRiskError):
        return error.exit_code
    else:
        return ExitCodes.GENERAL_ERROR


def handle_cli_error(error: Exception, operation: str = "operation") -> None:
    """Handle CLI errors consistently and exit with appropriate code.
    
    This function handles exceptions from CLI operations, logs them appropriately,
    displays user-friendly messages, and exits with proper codes.
    
    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
    """
    try:
        if isinstance(error, IriusRiskError):
            # Log and display IriusRisk errors with operation context
            log_error(error, operation=operation)
            display_error(error, verbose=False, operation=operation)
            raise click.Abort()
        elif isinstance(error, requests.RequestException):
            # Convert API errors
            api_error = handle_api_error(error, operation=operation)
            log_error(api_error, operation=operation)
            display_error(api_error, verbose=False, operation=operation)
            raise click.Abort()
        elif isinstance(error, (OSError, IOError)):
            # Convert file operation errors
            file_error = handle_file_error(error, operation=operation, file_path=str(error))
            log_error(file_error, operation=operation)
            display_error(file_error, verbose=False, operation=operation)
            raise click.Abort()
        else:
            # Handle unexpected errors with enhanced logging
            click.echo(f"Error {operation}: {error}", err=True)
            log_error(error, operation=operation)
            raise click.Abort()
    except click.Abort:
        raise
    except Exception as e:
        # Fallback error handling with logging
        click.echo(f"Error {operation}: {e}", err=True)
        logger.error(f"Fallback error handler triggered during {operation}: {e}", exc_info=True)
        raise click.Abort()


def handle_cli_error_decorator(func):
    """Decorator for CLI commands to handle errors consistently.
    
    This decorator catches all exceptions, logs them appropriately,
    displays user-friendly messages, and exits with proper codes.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        operation = f"command '{func.__name__}'"
        try:
            return func(*args, **kwargs)
        except IriusRiskError as e:
            # Log and display IriusRisk errors with operation context
            log_error(e, operation=operation)
            display_error(e, verbose=kwargs.get('verbose', False), operation=operation)
            sys.exit(e.exit_code)
        except requests.RequestException as e:
            # Convert API errors
            api_error = handle_api_error(e, operation=operation)
            log_error(api_error, operation=operation)
            display_error(api_error, verbose=kwargs.get('verbose', False), operation=operation)
            sys.exit(api_error.exit_code)
        except (OSError, IOError) as e:
            # Convert file operation errors
            file_error = handle_file_error(e, operation=operation, file_path=str(e))
            log_error(file_error, operation=operation)
            display_error(file_error, verbose=kwargs.get('verbose', False), operation=operation)
            sys.exit(file_error.exit_code)
        except Exception as e:
            # Handle unexpected errors with enhanced context
            log_error(e, operation=operation)
            display_error(e, verbose=kwargs.get('verbose', False), operation=operation)
            sys.exit(ExitCodes.GENERAL_ERROR)
    
    return wrapper


def safe_api_call(func, *args, operation: str = "API call", **kwargs):
    """Safely execute an API call with proper error handling.
    
    Args:
        func: The API function to call
        *args: Positional arguments for the function
        operation: Description of the operation for error messages
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the API call
        
    Raises:
        IriusRiskError: Appropriate exception for the error type
    """
    try:
        logger.debug(f"Starting safe API call for {operation}")
        result = func(*args, **kwargs)
        logger.debug(f"Safe API call completed successfully for {operation}")
        return result
    except requests.RequestException as e:
        logger.debug(f"Request exception in safe API call for {operation}: {e}")
        api_error = handle_api_error(e, operation)
        log_error(api_error, operation=operation)
        raise api_error
    except Exception as e:
        logger.error(f"Unexpected error in safe API call for {operation}: {str(e)}")
        unexpected_error = IriusRiskError(f"Unexpected error during {operation}: {str(e)}")
        log_error(unexpected_error, operation=operation)
        raise unexpected_error


def validate_required_param(value: Any, param_name: str, param_type: type = str) -> Any:
    """Validate that a required parameter is provided and of correct type.
    
    Args:
        value: The parameter value to validate
        param_name: Name of the parameter for error messages
        param_type: Expected type of the parameter
        
    Returns:
        The validated parameter value
        
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        raise ValidationError(f"Parameter '{param_name}' is required", field=param_name)
    
    if not isinstance(value, param_type):
        raise ValidationError(
            f"Parameter '{param_name}' must be of type {param_type.__name__}",
            field=param_name
        )
    
    return value


def validate_file_exists(file_path: str, operation: str = "read") -> str:
    """Validate that a file exists and is accessible.
    
    Args:
        file_path: Path to the file to validate
        operation: Operation being performed for error messages
        
    Returns:
        The validated file path
        
    Raises:
        FileOperationError: If file doesn't exist or isn't accessible
    """
    import os
    
    if not os.path.exists(file_path):
        raise FileOperationError(
            operation=operation,
            file_path=file_path,
            original_error=FileNotFoundError(f"File not found: {file_path}")
        )
    
    if not os.access(file_path, os.R_OK):
        raise FileOperationError(
            operation=operation,
            file_path=file_path,
            original_error=PermissionError(f"File not readable: {file_path}")
        )
    
    return file_path


def create_error_context(command: str, **kwargs) -> Dict[str, Any]:
    """Create error context dictionary for logging.
    
    Args:
        command: The command being executed
        **kwargs: Additional context information
        
    Returns:
        Dict containing error context
    """
    context = {
        'command': command,
        'timestamp': str(__import__('datetime').datetime.now()),
    }
    context.update(kwargs)
    return context


# Error message templates for consistency
ERROR_MESSAGES = {
    'project_not_found': "Project '{project_id}' not found. Use 'iriusrisk project list' to see available projects.",
    'no_project_configured': "No project configured. Use 'iriusrisk init' to configure a project.",
    'invalid_project_id': "Invalid project ID format: '{project_id}'",
    'api_token_missing': "API token not configured. Use 'iriusrisk auth login' to authenticate.",
    'api_token_invalid': "API token is invalid or expired. Use 'iriusrisk auth login' to re-authenticate.",
    'network_unavailable': "Cannot connect to IriusRisk server. Please check your network connection.",
    'file_not_found': "File not found: '{file_path}'",
    'file_not_readable': "Cannot read file: '{file_path}'. Check file permissions.",
    'invalid_format': "Invalid {data_type} format in '{file_path}'",
    'operation_timeout': "Operation timed out after {timeout} seconds",
    'insufficient_permissions': "Insufficient permissions to perform this operation",
}


def get_error_message(template_key: str, **kwargs) -> str:
    """Get formatted error message from template.
    
    Args:
        template_key: Key for the error message template
        **kwargs: Values to format into the template
        
    Returns:
        Formatted error message
    """
    template = ERROR_MESSAGES.get(template_key, "An error occurred")
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing template parameter {e} for error message '{template_key}'")
        return template
