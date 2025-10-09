"""
Centralized logging configuration for IriusRisk CLI.

This module provides consistent logging setup across all components
of the CLI application, with proper error logging and debugging support.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class IriusRiskFormatter(logging.Formatter):
    """Custom formatter for IriusRisk CLI logs."""
    
    def __init__(self):
        super().__init__()
        
    def format(self, record):
        # Add color coding for console output
        if hasattr(record, 'console_output') and record.console_output:
            level_colors = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',    # Red
                'CRITICAL': '\033[35m', # Magenta
            }
            reset_color = '\033[0m'
            
            level_name = record.levelname
            colored_level = f"{level_colors.get(level_name, '')}{level_name}{reset_color}"
            
            return f"{colored_level}: {record.getMessage()}"
        else:
            # Standard format for file output
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            return f"{timestamp} - {record.name} - {record.levelname} - {record.getMessage()}"


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = False,
    component: Optional[str] = None
) -> logging.Logger:
    """Set up centralized logging for IriusRisk CLI.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional specific log file path
        console_output: Whether to output logs to console
        component: Component name for logger identification
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Determine logger name
    logger_name = f"iriusrisk_cli.{component}" if component else "iriusrisk_cli"
    logger = logging.getLogger(logger_name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create formatter
    formatter = IriusRiskFormatter()
    
    # File handler
    if log_file:
        file_path = Path(log_file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        component_suffix = f"_{component}" if component else ""
        file_path = logs_dir / f"iriusrisk_cli{component_suffix}_{timestamp}.log"
    
    # Ensure log file directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use rotating file handler to prevent huge log files
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        
        # Mark records for console formatting
        class ConsoleFilter(logging.Filter):
            def filter(self, record):
                record.console_output = True
                return True
        
        console_handler.addFilter(ConsoleFilter())
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Log the setup
    logger.info(f"Logging initialized for {logger_name} - Level: {log_level} - File: {file_path}")
    
    return logger


def get_logger(component: str) -> logging.Logger:
    """Get a logger for a specific component.
    
    Args:
        component: Component name (e.g., 'api_client', 'commands.sync')
        
    Returns:
        Logger instance for the component
    """
    logger_name = f"iriusrisk_cli.{component}"
    logger = logging.getLogger(logger_name)
    
    # If logger doesn't have handlers, set it up with default configuration
    if not logger.handlers:
        return setup_logging(component=component)
    
    return logger


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any],
    operation: str = "operation"
) -> None:
    """Log an error with rich context information.
    
    Args:
        logger: Logger instance to use
        error: Exception that occurred
        context: Context information dictionary
        operation: Description of the operation that failed
    """
    error_info = {
        'operation': operation,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context
    }
    
    logger.error(f"Error in {operation}: {error}", extra=error_info)
    
    # Log additional context
    for key, value in context.items():
        logger.debug(f"Context {key}: {value}")


def log_api_request(
    logger: logging.Logger,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    response_time: Optional[float] = None,
    error: Optional[Exception] = None
) -> None:
    """Log API request details.
    
    Args:
        logger: Logger instance to use
        method: HTTP method
        url: Request URL
        status_code: Response status code
        response_time: Response time in seconds
        error: Exception if request failed
    """
    if error:
        # Log API failures at DEBUG level to avoid cluttering user output
        # The error will be properly handled and displayed by the error handling layer
        logger.debug(f"API request failed: {method} {url} - Error: {error}")
    else:
        level = logging.INFO if status_code and status_code < 400 else logging.WARNING
        message = f"API request: {method} {url}"
        
        if status_code:
            message += f" - Status: {status_code}"
        if response_time:
            message += f" - Time: {response_time:.3f}s"
            
        logger.log(level, message)


def configure_root_logger(debug: bool = False) -> None:
    """Configure the root logger for the entire application.
    
    Args:
        debug: Whether to enable debug logging
    """
    log_level = "DEBUG" if debug else "INFO"
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up main application logger
    setup_logging(
        log_level=log_level,
        console_output=debug,  # Show console output in debug mode
        component="main"
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def configure_cli_logging(
    debug: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    log_file: Optional[str] = None,
    log_level: Optional[str] = None
) -> None:
    """Configure logging for CLI based on user options.
    
    Args:
        debug: Enable debug output to stderr
        verbose: Enable verbose output to stderr  
        quiet: Suppress non-essential output
        log_file: Optional file to write logs to
        log_level: Specific log level to use
    """
    # Determine effective log level
    if log_level:
        effective_level = log_level.upper()
    elif debug:
        effective_level = "DEBUG"
    elif verbose:
        effective_level = "INFO"
    else:
        effective_level = "ERROR"  # Only errors by default
    
    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    numeric_level = getattr(logging, effective_level, logging.ERROR)
    root_logger.setLevel(numeric_level)
    
    # Configure stderr handler (only if verbose/debug mode, not in quiet mode)
    if (verbose or debug) and not quiet:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(numeric_level)
        
        # Use colored formatter for stderr
        formatter = IriusRiskFormatter()
        stderr_handler.setFormatter(formatter)
        
        # Mark records for console formatting
        class ConsoleFilter(logging.Filter):
            def filter(self, record):
                record.console_output = True
                return True
        
        stderr_handler.addFilter(ConsoleFilter())
        root_logger.addHandler(stderr_handler)
    
    # Configure file handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        
        # Use standard formatter for file output
        file_formatter = IriusRiskFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Set up IriusRisk CLI logger
    cli_logger = logging.getLogger("iriusrisk_cli")
    cli_logger.setLevel(numeric_level)


def get_log_file_path(component: Optional[str] = None) -> Path:
    """Get the current log file path for a component.
    
    Args:
        component: Component name
        
    Returns:
        Path to the log file
    """
    logs_dir = Path("logs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    component_suffix = f"_{component}" if component else ""
    return logs_dir / f"iriusrisk_cli{component_suffix}_{timestamp}.log"


# Context manager for operation logging
class LoggedOperation:
    """Context manager for logging operations with timing and error handling."""
    
    def __init__(self, logger: logging.Logger, operation: str, context: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.operation = operation
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation}", extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"Completed {self.operation} in {duration:.3f}s", extra=self.context)
            
            # Log performance warnings for slow operations
            _log_performance_warning(self.logger, self.operation, duration)
        else:
            self.logger.error(
                f"Failed {self.operation} after {duration:.3f}s: {exc_val}",
                extra=self.context
            )
        
        return False  # Don't suppress exceptions


def _log_performance_warning(logger: logging.Logger, operation: str, duration: float) -> None:
    """Log performance warnings for operations that take too long."""
    # Define performance thresholds for different operation types
    thresholds = {
        'api_request': 5.0,      # API requests > 5s
        'file_operation': 2.0,   # File operations > 2s
        'data_processing': 10.0, # Data processing > 10s
        'sync': 30.0,           # Sync operations > 30s
        'report': 15.0,         # Report generation > 15s
        'default': 5.0          # Default threshold
    }
    
    # Determine threshold based on operation type
    threshold = thresholds.get('default', 5.0)
    for op_type, op_threshold in thresholds.items():
        if op_type in operation.lower():
            threshold = op_threshold
            break
    
    if duration > threshold:
        logger.warning(f"Performance warning: {operation} took {duration:.3f}s (threshold: {threshold}s)")


def log_performance_metrics(logger: logging.Logger, operation: str, metrics: Dict[str, Any]) -> None:
    """Log detailed performance metrics for an operation.
    
    Args:
        logger: Logger instance to use
        operation: Description of the operation
        metrics: Dictionary containing performance metrics
    """
    logger.debug(f"Performance metrics for {operation}:")
    for metric, value in metrics.items():
        if isinstance(value, float) and metric.endswith('_time'):
            logger.debug(f"  {metric}: {value:.3f}s")
        elif isinstance(value, int) and metric.endswith('_count'):
            logger.debug(f"  {metric}: {value:,}")
        elif isinstance(value, int) and metric.endswith('_bytes'):
            logger.debug(f"  {metric}: {_format_bytes(value)}")
        else:
            logger.debug(f"  {metric}: {value}")


def _format_bytes(bytes_count: int) -> str:
    """Format byte count in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"


def log_memory_usage(logger: logging.Logger, operation: str) -> None:
    """Log current memory usage for an operation.
    
    Args:
        logger: Logger instance to use
        operation: Description of the operation
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        logger.debug(f"Memory usage for {operation}:")
        logger.debug(f"  RSS: {_format_bytes(memory_info.rss)}")
        logger.debug(f"  VMS: {_format_bytes(memory_info.vms)}")
        
        # Log warning for high memory usage (>500MB)
        if memory_info.rss > 500 * 1024 * 1024:
            logger.warning(f"High memory usage in {operation}: {_format_bytes(memory_info.rss)}")
            
    except ImportError:
        logger.debug(f"psutil not available - cannot log memory usage for {operation}")
    except Exception as e:
        logger.debug(f"Failed to get memory usage for {operation}: {e}")


class PerformanceTimer:
    """Simple timer for measuring operation performance."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self) -> None:
        """Start the timer."""
        self.start_time = datetime.now()
    
    def stop(self) -> float:
        """Stop the timer and return elapsed time in seconds."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        self.end_time = datetime.now()
        return (self.end_time - self.start_time).total_seconds()
    
    def elapsed(self) -> float:
        """Get elapsed time without stopping the timer."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        return (datetime.now() - self.start_time).total_seconds()
