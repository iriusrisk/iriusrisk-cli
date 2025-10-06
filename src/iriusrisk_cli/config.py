"""Configuration management for IriusRisk CLI."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class Config:
    """Configuration class for IriusRisk CLI."""
    
    def __init__(self):
        """Initialize configuration by loading from .env file and environment."""
        # Look for .env file in current directory first
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        else:
            # Fall back to environment variables
            load_dotenv()
    
    @property
    def hostname(self) -> str:
        """Get IriusRisk hostname from environment."""
        hostname = os.getenv("IRIUS_HOSTNAME")
        if not hostname:
            raise ValueError("IRIUS_HOSTNAME environment variable not set")
        
        # Ensure the hostname has a proper scheme
        if not hostname.startswith(('http://', 'https://')):
            hostname = f"https://{hostname}"
        
        return hostname
    
    @property
    def api_token(self) -> str:
        """Get IriusRisk API token from environment."""
        token = os.getenv("IRIUS_API_TOKEN")
        if not token:
            raise ValueError("IRIUS_API_TOKEN environment variable not set")
        return token
    
    @property
    def api_base_url(self) -> str:
        """Get the base URL for the IriusRisk API v2."""
        return f"{self.hostname.rstrip('/')}/api/v2"
    
    @property
    def api_v1_base_url(self) -> str:
        """Get the base URL for the IriusRisk API v1."""
        return f"{self.hostname.rstrip('/')}/api/v1"
    
    def get_project_config(self) -> Optional[Dict[str, Any]]:
        """Get project configuration from .iriusRisk/project.json if it exists.
        
        Returns:
            Project configuration dictionary or None if not found
        """
        project_file = Path.cwd() / ".iriusRisk" / "project.json"
        if project_file.exists():
            try:
                with open(project_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def get_default_project_id(self) -> Optional[str]:
        """Get the default project ID from local project configuration.
        
        For new projects, this returns the reference_id (human-readable).
        For legacy projects, this returns the project_id (UUID).
        
        Returns:
            Project ID string or None if not configured
        """
        project_config = self.get_project_config()
        if project_config:
            # Prefer reference_id (new format) over project_id (legacy format)
            return project_config.get('reference_id') or project_config.get('project_id')
        return None
    
    def get_default_project_name(self) -> Optional[str]:
        """Get the default project name from local project configuration.
        
        Returns:
            Project name string or None if not configured
        """
        project_config = self.get_project_config()
        if project_config:
            return project_config.get('name')
        return None
    
    def get_workspace_paths(self) -> list:
        """Get workspace paths from common IDE environment variables.
        
        Checks environment variables that IDEs commonly set to indicate
        the workspace/project directory (e.g., Cursor, VS Code).
        
        Returns:
            List of Path objects for workspace directories found in environment
        """
        from pathlib import Path
        
        workspace_paths = []
        # Check common IDE environment variables
        for env_var in ['PWD', 'CURSOR_WORKSPACE', 'VSCODE_CWD', 'PROJECT_ROOT']:
            value = os.getenv(env_var)
            if value:
                workspace_paths.append(Path(value))
        
        return workspace_paths
