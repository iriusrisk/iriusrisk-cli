"""Project utility functions for IriusRisk CLI."""

import click
import json
from pathlib import Path
from typing import Optional, Dict, Any


def resolve_project_id(provided_project_id: Optional[str] = None) -> str:
    """Resolve project ID from provided value or default configuration.
    
    This function handles the resolution of project IDs for commands that need them.
    It first checks if a project ID was provided, then falls back to the default
    project ID from the local configuration. If the default project ID is a UUID
    and fails, it will try to find the reference ID for that project.
    
    Args:
        provided_project_id: Project ID provided via command line option
        
    Returns:
        Resolved project ID string
        
    Raises:
        click.Abort: If no project ID can be resolved
    """
    # Use provided project ID if available
    if provided_project_id:
        return provided_project_id
    
    # Try to get default project ID from configuration
    from ..config import Config
    config_instance = Config()
    default_project_id = config_instance.get_default_project_id()
    if default_project_id:
        return default_project_id
    
    # No project ID available
    click.echo("❌ No project ID provided and no default project configured.")
    click.echo()
    click.echo("To fix this, you can:")
    click.echo("  1. Provide a project ID: --project-id <project-id>")
    click.echo("  2. Initialize a default project: iriusrisk init")
    click.echo()
    click.echo("For more information, run: iriusrisk init --help")
    raise click.Abort()


def get_project_context_info() -> Optional[str]:
    """Get project context information for display purposes.
    
    Returns:
        Project name if available, None otherwise
    """
    from ..config import Config
    config_instance = Config()
    return config_instance.get_default_project_name()


def get_project_config() -> Optional[Dict[str, Any]]:
    """Get the current project configuration.
    
    Returns:
        Project configuration dictionary or None if not found
    """
    from ..config import Config
    config_instance = Config()
    return config_instance.get_project_config()


def update_project_config(new_config: Dict[str, Any]) -> None:
    """Update the project configuration file.
    
    Args:
        new_config: New configuration dictionary to save
        
    Raises:
        Exception: If unable to write configuration file
    """
    project_dir = Path.cwd() / ".iriusRisk"
    project_file = project_dir / "project.json"
    
    # Ensure the .iriusRisk directory exists
    project_dir.mkdir(exist_ok=True)
    
    try:
        with open(project_file, 'w') as f:
            json.dump(new_config, f, indent=2)
    except IOError as e:
        raise Exception(f"Failed to update project configuration: {e}")
