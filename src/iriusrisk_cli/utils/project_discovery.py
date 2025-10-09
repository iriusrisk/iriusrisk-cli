"""Project discovery utilities for IriusRisk CLI.

This module provides centralized functionality for discovering project root
directories and configuration files, eliminating duplication across the codebase.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


def find_project_root(
    start_path: Optional[Path] = None,
    check_parents: bool = True,
    check_workspace_env: bool = True,
    check_home_subdirs: bool = True
) -> Tuple[Path, Optional[Dict[str, Any]]]:
    """Find the project root directory containing .iriusrisk/project.json.
    
    This function performs a sophisticated search for project configuration:
    1. Checks workspace environment variables (if enabled)
    2. Checks current/starting directory and parents (if enabled)
    3. Checks common project directories under home (if enabled)
    
    Args:
        start_path: Starting directory (defaults to current working directory)
        check_parents: Whether to walk up parent directories
        check_workspace_env: Whether to check workspace environment variables
        check_home_subdirs: Whether to check common subdirectories under home
        
    Returns:
        Tuple of (project_root_path, project_config_dict or None)
        - project_root_path: Directory containing .iriusRisk folder (or start_path if not found)
        - project_config_dict: Parsed project.json contents, or None if not found
        
    Raises:
        OSError: Only in extreme cases where both cwd and home directory are inaccessible
    
    Examples:
        >>> root, config = find_project_root()
        >>> if config:
        ...     print(f"Found project: {config.get('name')}")
        
        >>> # Simple search in current directory only
        >>> root, config = find_project_root(check_parents=False, check_workspace_env=False)
    """
    from ..config import Config
    
    # Determine starting directory
    try:
        current_dir = start_path or Path.cwd()
    except OSError:
        # If we can't get current directory, fall back to home directory
        current_dir = Path.home()
    
    project_root = current_dir
    project_config = None
    
    # Build list of paths to search
    workspace_paths_to_try = []
    
    # First, check workspace environment variables (IDEs like Cursor, VS Code)
    if check_workspace_env:
        try:
            config = Config()
            workspace_paths_to_try.extend(config.get_workspace_paths())
        except (OSError, ValueError):
            # If Config initialization fails (e.g., Path.cwd() fails or missing env vars),
            # continue without workspace paths from environment
            logger.debug("Could not get workspace paths from environment variables")
            pass
    
    # Add the current working directory and its parents
    if check_parents:
        workspace_paths_to_try.extend([current_dir] + list(current_dir.parents))
    else:
        workspace_paths_to_try.append(current_dir)
    
    # Also search common project directories under home
    if check_home_subdirs:
        home_dir = Path.home()
        for subdir in ['src', 'projects', 'workspace', 'dev', 'code']:
            src_dir = home_dir / subdir
            if src_dir.exists():
                # Look for .iriusRisk directories in subdirectories
                try:
                    for project_dir in src_dir.iterdir():
                        if project_dir.is_dir():
                            workspace_paths_to_try.append(project_dir)
                except (PermissionError, OSError):
                    continue
    
    # Walk through all potential paths looking for .iriusrisk/project.json
    for path in workspace_paths_to_try:
        try:
            project_json_path = path / '.iriusrisk' / 'project.json'
            if project_json_path.exists():
                project_root = path
                try:
                    with open(project_json_path, 'r') as f:
                        project_config = json.load(f)
                    logger.debug(f"Found project config at: {project_json_path}")
                    break
                except (json.JSONDecodeError, OSError, IOError) as e:
                    # If we can't read the project.json, continue looking
                    logger.debug(f"Failed to read {project_json_path}: {e}")
                    continue
        except (OSError, PermissionError):
            continue
    
    # If still no project found, use starting/current working directory
    if project_root == current_dir and not (current_dir / '.iriusrisk' / 'project.json').exists():
        project_root = current_dir
        logger.debug(f"No project config found, using current directory: {project_root}")
    
    return project_root, project_config


def find_project_config(start_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Find and return project configuration if it exists.
    
    This is a convenience function that just returns the config dict.
    
    Args:
        start_path: Starting directory (defaults to current working directory)
        
    Returns:
        Project configuration dictionary or None if not found
        
    Examples:
        >>> config = find_project_config()
        >>> if config:
        ...     project_id = config.get('project_id')
    """
    _, config = find_project_root(start_path)
    return config

