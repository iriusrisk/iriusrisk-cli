"""Configuration management for IriusRisk CLI."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv


class Config:
    """Configuration class for IriusRisk CLI with cascading configuration sources."""
    
    def __init__(self):
        """Initialize configuration by loading from various sources."""
        # Load .env file in current directory if it exists (for dotenv to work)
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)  # Don't override existing env vars
        
        # Cache for loaded configs
        self._user_config_cache: Optional[Dict[str, Any]] = None
        self._project_config_cache: Optional[Dict[str, Any]] = None
    
    def _get_user_config(self) -> Optional[Dict[str, Any]]:
        """Load user configuration from ~/.iriusrisk/config.json.
        
        Returns:
            User configuration dictionary or None if not found or malformed
        """
        if self._user_config_cache is not None:
            return self._user_config_cache
        
        user_config_file = Path.home() / ".iriusrisk" / "config.json"
        if user_config_file.exists():
            try:
                with open(user_config_file, 'r') as f:
                    self._user_config_cache = json.load(f)
                    return self._user_config_cache
            except (json.JSONDecodeError, IOError) as e:
                raise ValueError(f"Failed to load user config from {user_config_file}: {e}")
        
        self._user_config_cache = {}
        return None
    
    def _get_hostname_from_cascade(self) -> Tuple[Optional[str], Optional[str]]:
        """Get hostname from cascade of sources.
        
        Returns:
            Tuple of (hostname, source) where source indicates where the value came from
        """
        # 1. Check environment variables (highest priority)
        hostname = os.getenv("IRIUS_HOSTNAME")
        if hostname:
            return (hostname, "environment variable")
        
        # 2. Check project .env file (already loaded by load_dotenv)
        # This is redundant but kept for clarity - already checked above
        
        # 3. Check project config (.iriusrisk/project.json)
        project_config = self.get_project_config()
        if project_config and 'hostname' in project_config:
            return (project_config['hostname'], "project config")
        
        # 4. Check user config (~/.iriusrisk/config.json)
        user_config = self._get_user_config()
        if user_config and 'hostname' in user_config:
            return (user_config['hostname'], "user config")
        
        return (None, None)
    
    def _get_api_token_from_cascade(self) -> Tuple[Optional[str], Optional[str]]:
        """Get API token from cascade of sources.
        
        Returns:
            Tuple of (api_token, source) where source indicates where the value came from
        """
        # 1. Check environment variables (highest priority)
        # Support both IRIUS_API_KEY and IRIUS_API_TOKEN, prefer API_KEY
        api_token = os.getenv("IRIUS_API_KEY")
        if api_token:
            return (api_token, "environment variable (IRIUS_API_KEY)")
        
        api_token = os.getenv("IRIUS_API_TOKEN")
        if api_token:
            return (api_token, "environment variable (IRIUS_API_TOKEN)")
        
        # 2. Check project .env file (already loaded by load_dotenv)
        # This is redundant but kept for clarity - already checked above
        
        # 3. Check user config (~/.iriusrisk/config.json)
        # NOTE: Project config should NEVER contain api_token
        user_config = self._get_user_config()
        if user_config and 'api_token' in user_config:
            return (user_config['api_token'], "user config")
        
        return (None, None)
    
    @property
    def hostname(self) -> str:
        """Get IriusRisk hostname from cascading configuration sources.
        
        Priority order (highest to lowest):
        1. IRIUS_HOSTNAME environment variable
        2. .env file in project directory
        3. hostname in .iriusrisk/project.json
        4. hostname in ~/.iriusrisk/config.json
        
        Returns:
            Hostname with proper scheme (https://)
            
        Raises:
            ValueError: If hostname not found in any source
        """
        hostname, source = self._get_hostname_from_cascade()
        if not hostname:
            raise ValueError(
                "IRIUS_HOSTNAME not found. Checked:\n"
                "  1. IRIUS_HOSTNAME environment variable\n"
                "  2. .env file in project directory\n"
                "  3. .iriusrisk/project.json (hostname field)\n"
                "  4. ~/.iriusrisk/config.json (hostname field)\n"
                "\nSet hostname using: iriusrisk config set-hostname <hostname>"
            )
        
        # Ensure the hostname has a proper scheme
        if not hostname.startswith(('http://', 'https://')):
            hostname = f"https://{hostname}"
        
        return hostname
    
    @property
    def api_token(self) -> str:
        """Get IriusRisk API token from cascading configuration sources.
        
        Priority order (highest to lowest):
        1. IRIUS_API_KEY or IRIUS_API_TOKEN environment variable
        2. .env file in project directory
        3. api_token in ~/.iriusrisk/config.json
        
        Returns:
            API token string
            
        Raises:
            ValueError: If API token not found in any source
        """
        api_token, source = self._get_api_token_from_cascade()
        if not api_token:
            raise ValueError(
                "IRIUS_API_TOKEN not found. Checked:\n"
                "  1. IRIUS_API_KEY environment variable\n"
                "  2. IRIUS_API_TOKEN environment variable\n"
                "  3. .env file in project directory\n"
                "  4. ~/.iriusrisk/config.json (api_token field)\n"
                "\nSet API token using: iriusrisk config set-api-key <token>"
            )
        return api_token
    
    @property
    def api_base_url(self) -> str:
        """Get the base URL for the IriusRisk API v2."""
        return f"{self.hostname.rstrip('/')}/api/v2"
    
    @property
    def api_v1_base_url(self) -> str:
        """Get the base URL for the IriusRisk API v1."""
        return f"{self.hostname.rstrip('/')}/api/v1"
    
    def get_config_sources(self) -> Dict[str, Any]:
        """Get configuration values and their sources for debugging.
        
        Returns:
            Dictionary with configuration sources and resolved values
        """
        hostname, hostname_source = self._get_hostname_from_cascade()
        api_token, api_token_source = self._get_api_token_from_cascade()
        
        # Get all config file contents
        user_config = self._get_user_config()
        project_config = self.get_project_config()
        
        return {
            'resolved': {
                'hostname': hostname,
                'hostname_source': hostname_source,
                'api_token': api_token,
                'api_token_source': api_token_source,
            },
            'user_config': user_config,
            'project_config': project_config,
            'environment': {
                'IRIUS_HOSTNAME': os.getenv('IRIUS_HOSTNAME'),
                'IRIUS_API_KEY': os.getenv('IRIUS_API_KEY'),
                'IRIUS_API_TOKEN': os.getenv('IRIUS_API_TOKEN'),
            },
            'project_env_file': (Path.cwd() / ".env").exists(),
        }
    
    def get_project_config(self) -> Optional[Dict[str, Any]]:
        """Get project configuration from .iriusrisk/project.json if it exists.
        
        Returns:
            Project configuration dictionary or None if not found
        """
        if self._project_config_cache is not None:
            return self._project_config_cache if self._project_config_cache else None
        
        project_file = Path.cwd() / ".iriusrisk" / "project.json"
        if project_file.exists():
            try:
                with open(project_file, 'r') as f:
                    self._project_config_cache = json.load(f)
                    return self._project_config_cache
            except (json.JSONDecodeError, IOError):
                self._project_config_cache = {}
                return None
        
        self._project_config_cache = {}
        return None
    
    def get_default_project_id(self) -> Optional[str]:
        """Get the default project ID from local project configuration.
        
        For projects initialized from existing IriusRisk projects, this returns
        the UUID (project_id). For new projects that haven't been created yet,
        this returns the reference_id.
        
        Returns:
            Project ID string or None if not configured
        """
        project_config = self.get_project_config()
        if project_config:
            # Prefer project_id (UUID) if available (for existing projects)
            # Fall back to reference_id for new projects that haven't been created yet
            return project_config.get('project_id') or project_config.get('reference_id')
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


def save_user_config(hostname: Optional[str] = None, api_token: Optional[str] = None) -> None:
    """Save user configuration to ~/.iriusrisk/config.json.
    
    This function preserves existing values if the parameter is None.
    
    Args:
        hostname: Hostname to save (None to preserve existing)
        api_token: API token to save (None to preserve existing)
        
    Raises:
        ValueError: If config file is malformed or cannot be written
        OSError: If directory cannot be created or file cannot be written
    """
    user_config_dir = Path.home() / ".iriusrisk"
    user_config_file = user_config_dir / "config.json"
    
    # Load existing config if it exists
    existing_config = {}
    if user_config_file.exists():
        try:
            with open(user_config_file, 'r') as f:
                existing_config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Existing config file is malformed: {e}")
    
    # Update with new values (preserving existing if parameter is None)
    if hostname is not None:
        existing_config['hostname'] = hostname
    if api_token is not None:
        existing_config['api_token'] = api_token
    
    # Create directory if it doesn't exist
    user_config_dir.mkdir(mode=0o700, exist_ok=True)
    
    # Write config file with restrictive permissions
    with open(user_config_file, 'w') as f:
        json.dump(existing_config, f, indent=2)
    
    # Set file permissions to 0600 (read/write for owner only)
    user_config_file.chmod(0o600)


def validate_project_config(config: Dict[str, Any]) -> None:
    """Validate project configuration to ensure security rules and proper structure.
    
    Args:
        config: Project configuration dictionary to validate
        
    Raises:
        ValueError: If config contains forbidden fields or invalid prompt customizations
    """
    forbidden_fields = ['api_token', 'api_key', 'token', 'password', 'secret']
    found_forbidden = [field for field in forbidden_fields if field in config]
    
    if found_forbidden:
        raise ValueError(
            f"Project config must not contain sensitive fields: {', '.join(found_forbidden)}. "
            "Use 'iriusrisk config set-api-key' to set API credentials in user config instead."
        )
    
    # Validate prompts structure if present
    if 'prompts' in config:
        prompts = config['prompts']
        
        if not isinstance(prompts, dict):
            raise ValueError("'prompts' field must be a dictionary")
        
        # Valid MCP tool names that support prompt customization
        valid_tool_names = [
            'initialize_iriusrisk_workflow',
            'threats_and_countermeasures',
            'analyze_source_material',
            'create_threat_model',
            'architecture_and_design_review',
            'security_development_advisor'
        ]
        
        # Valid customization actions
        valid_actions = ['prefix', 'postfix', 'replace']
        
        for tool_name, customization in prompts.items():
            # Check if tool name is valid
            if tool_name not in valid_tool_names:
                raise ValueError(
                    f"Invalid tool name in prompts: '{tool_name}'. "
                    f"Valid tool names are: {', '.join(valid_tool_names)}"
                )
            
            # Check if customization is a dictionary
            if not isinstance(customization, dict):
                raise ValueError(
                    f"Customization for tool '{tool_name}' must be a dictionary"
                )
            
            # Check if at least one valid action is present
            if not any(action in customization for action in valid_actions):
                raise ValueError(
                    f"Customization for tool '{tool_name}' must include at least one of: "
                    f"{', '.join(valid_actions)}"
                )
            
            # Validate each action
            for action, text in customization.items():
                if action not in valid_actions:
                    raise ValueError(
                        f"Invalid action '{action}' for tool '{tool_name}'. "
                        f"Valid actions are: {', '.join(valid_actions)}"
                    )
                
                if not isinstance(text, str):
                    raise ValueError(
                        f"Text for action '{action}' in tool '{tool_name}' must be a string"
                    )
                
                # Warn if text is suspiciously long (might be a copy-paste error)
                if len(text) > 10000:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Prompt customization for '{tool_name}.{action}' is very long "
                        f"({len(text)} characters). This may be unintentional."
                    )
