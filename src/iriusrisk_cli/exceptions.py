"""
Custom exception hierarchy for IriusRisk CLI.

This module defines a comprehensive exception hierarchy that provides
consistent error handling across all CLI commands and API operations.
"""

from typing import Optional, Dict, Any


class IriusRiskError(Exception):
    """Base exception for all IriusRisk CLI errors.
    
    Attributes:
        message: Human-readable error message
        exit_code: Exit code for CLI commands (default: 1)
        details: Additional error details for debugging
        user_message: User-friendly message (defaults to message if not provided)
    """
    
    def __init__(self, 
                 message: str, 
                 exit_code: int = 1, 
                 details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.details = details or {}
        self.user_message = user_message or message


class ConfigurationError(IriusRiskError):
    """Raised when there are configuration-related issues."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            exit_code=2,  # Configuration errors
            details=details,
            user_message=f"Configuration error: {message}"
        )


class AuthenticationError(IriusRiskError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            exit_code=3,  # Authentication errors
            details=details,
            user_message="Authentication failed. Please check your API token configuration."
        )


class AuthorizationError(IriusRiskError):
    """Raised when user lacks permission for an operation."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            exit_code=4,  # Authorization errors
            details=details,
            user_message="Access denied. You don't have permission for this operation."
        )


class NetworkError(IriusRiskError):
    """Raised when network/connectivity issues occur."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            exit_code=5,  # Network errors
            details=details,
            user_message="Network error. Please check your connection and try again."
        )


class APIError(IriusRiskError):
    """Raised when API requests fail."""
    
    def __init__(self, 
                 message: str, 
                 status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None,
                 details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if status_code:
            details['status_code'] = status_code
        if response_data:
            details['response_data'] = response_data
            
        super().__init__(
            message=message,
            exit_code=6,  # API errors
            details=details,
            user_message=f"API request failed: {message}"
        )
        self.status_code = status_code
        self.response_data = response_data


class ValidationError(IriusRiskError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details['field'] = field
            
        super().__init__(
            message=message,
            exit_code=7,  # Validation errors
            details=details,
            user_message=f"Invalid input: {message}"
        )
        self.field = field


class ResourceNotFoundError(IriusRiskError):
    """Raised when a requested resource is not found."""
    
    def __init__(self, 
                 resource_type: str, 
                 resource_id: str, 
                 details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} '{resource_id}' not found"
        details = details or {}
        details.update({
            'resource_type': resource_type,
            'resource_id': resource_id
        })
        
        super().__init__(
            message=message,
            exit_code=8,  # Resource not found
            details=details,
            user_message=message
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class FileOperationError(IriusRiskError):
    """Raised when file operations fail."""
    
    def __init__(self, 
                 operation: str, 
                 file_path: str, 
                 original_error: Optional[Exception] = None,
                 details: Optional[Dict[str, Any]] = None):
        message = f"Failed to {operation} file '{file_path}'"
        if original_error:
            message += f": {str(original_error)}"
            
        details = details or {}
        details.update({
            'operation': operation,
            'file_path': file_path
        })
        if original_error:
            details['original_error'] = str(original_error)
            
        super().__init__(
            message=message,
            exit_code=9,  # File operation errors
            details=details,
            user_message=message
        )
        self.operation = operation
        self.file_path = file_path
        self.original_error = original_error


class ProjectError(IriusRiskError):
    """Raised when project-related operations fail."""
    
    def __init__(self, message: str, project_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if project_id:
            details['project_id'] = project_id
            
        super().__init__(
            message=message,
            exit_code=10,  # Project errors
            details=details,
            user_message=f"Project error: {message}"
        )
        self.project_id = project_id


class DataProcessingError(IriusRiskError):
    """Raised when data processing operations fail."""
    
    def __init__(self, 
                 operation: str, 
                 data_type: str, 
                 original_error: Optional[Exception] = None,
                 details: Optional[Dict[str, Any]] = None):
        message = f"Failed to {operation} {data_type} data"
        if original_error:
            message += f": {str(original_error)}"
            
        details = details or {}
        details.update({
            'operation': operation,
            'data_type': data_type
        })
        if original_error:
            details['original_error'] = str(original_error)
            
        super().__init__(
            message=message,
            exit_code=11,  # Data processing errors
            details=details,
            user_message=message
        )
        self.operation = operation
        self.data_type = data_type
        self.original_error = original_error


class TimeoutError(IriusRiskError):
    """Raised when operations timeout."""
    
    def __init__(self, 
                 operation: str, 
                 timeout_seconds: int, 
                 details: Optional[Dict[str, Any]] = None):
        message = f"{operation} timed out after {timeout_seconds} seconds"
        details = details or {}
        details.update({
            'operation': operation,
            'timeout_seconds': timeout_seconds
        })
        
        super().__init__(
            message=message,
            exit_code=12,  # Timeout errors
            details=details,
            user_message=message
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


# Exit code constants for consistency
class ExitCodes:
    """Standard exit codes for the CLI application."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    CONFIGURATION_ERROR = 2
    AUTHENTICATION_ERROR = 3
    AUTHORIZATION_ERROR = 4
    NETWORK_ERROR = 5
    API_ERROR = 6
    VALIDATION_ERROR = 7
    RESOURCE_NOT_FOUND = 8
    FILE_OPERATION_ERROR = 9
    PROJECT_ERROR = 10
    DATA_PROCESSING_ERROR = 11
    TIMEOUT_ERROR = 12
