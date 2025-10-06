"""CLI context management for dependency injection."""

import click
import functools
from typing import Optional
from .container import Container, get_container, set_container
from .config import Config


class CliContext:
    """Context object for CLI commands that manages dependency injection."""
    
    def __init__(self, container: Optional[Container] = None):
        """Initialize CLI context with dependency container.
        
        Args:
            container: Dependency injection container (creates new one if not provided)
        """
        self.container = container or Container()
        self.logging_config = None  # Will be set by main CLI function
    
    def get_config(self) -> Config:
        """Get configuration instance from container."""
        return self.container.get(Config)
    
    def get_service_factory(self):
        """Get service factory instance from container."""
        from .service_factory import ServiceFactory
        return self.container.get(ServiceFactory)
    
    def cleanup(self):
        """Clean up resources."""
        self.container.cleanup()


def pass_cli_context(f):
    """Decorator to pass CLI context to command functions."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        if not hasattr(ctx, 'obj') or ctx.obj is None:
            ctx.obj = CliContext()
        return f(ctx.obj, *args, **kwargs)
    return wrapper


def setup_cli_context() -> CliContext:
    """Set up CLI context with proper dependency injection.
    
    This function creates a new container and sets it as the default.
    It should be called at the start of CLI execution.
    
    Returns:
        Configured CLI context
    """
    container = Container()
    set_container(container)
    return CliContext(container)


def cleanup_cli_context():
    """Clean up CLI context and reset container.
    
    This function should be called at the end of CLI execution.
    """
    from .container import reset_container
    reset_container()
