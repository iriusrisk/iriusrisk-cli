"""Project ID resolution utilities.

This module provides centralized functionality for resolving project IDs
to UUIDs, eliminating code duplication across command modules.
"""

from typing import Optional
from uuid import UUID
from ..api.project_client import ProjectApiClient


def resolve_project_id_to_uuid(project_id: str, api_client: ProjectApiClient) -> str:
    """Resolve project ID to UUID for V2 API calls.
    
    V2 API requires UUIDs in URL paths. This function:
    1. Returns UUIDs as-is
    2. Converts reference IDs to UUIDs by looking them up
    
    Args:
        project_id: Project ID to resolve (UUID or reference ID)
        api_client: API client instance (required)
        
    Returns:
        UUID that works with the V2 API
        
    Raises:
        Exception: If project lookup fails or project not found
    """
    # If it looks like a UUID, return as-is
    if is_uuid_format(project_id):
        return project_id
    
    # It's likely a reference ID, look up the corresponding UUID
    
    try:
        filter_expr = f"'referenceId'='{project_id}'"
        project_response = api_client.get_projects(page=0, size=1, filter_expression=filter_expr)
        projects = project_response.get('_embedded', {}).get('items', [])
        if projects:
            uuid = projects[0].get('id')
            if uuid:
                return uuid
        # If no projects found with this reference ID, return original and let API handle it
        return project_id
    except Exception as e:
        # If lookup fails, return the original ID and let the API handle it
        return project_id


def resolve_project_id_to_uuid_strict(project_id: str, api_client: ProjectApiClient) -> str:
    """Resolve project ID to UUID with strict error handling.
    
    This is a stricter version that raises exceptions on lookup failures,
    used in contexts where we need to ensure the project exists.
    
    Args:
        project_id: Project ID to resolve (UUID or reference ID)
        api_client: API client instance (required)
        
    Returns:
        UUID that works with the V2 API
        
    Raises:
        Exception: If project lookup fails or project not found
    """
    # If it looks like a UUID, return as-is
    if is_uuid_format(project_id):
        return project_id
    
    # It's likely a reference ID, look up the corresponding UUID
    
    try:
        filter_expr = f"'referenceId'='{project_id}'"
        project_response = api_client.get_projects(page=0, size=1, filter_expression=filter_expr)
        projects = project_response.get('_embedded', {}).get('items', [])
        if projects:
            uuid = projects[0].get('id')
            if uuid:
                return uuid
        raise Exception(f"Project with reference ID '{project_id}' not found")
    except Exception as e:
        raise Exception(f"Failed to resolve project reference '{project_id}' to UUID: {e}")


def is_uuid_format(value: str) -> bool:
    """Check if a string is a valid UUID format.
    
    Uses Python's built-in uuid module to validate UUID format properly.
    
    Args:
        value: String to check
        
    Returns:
        True if the string is a valid UUID format
    """
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False
