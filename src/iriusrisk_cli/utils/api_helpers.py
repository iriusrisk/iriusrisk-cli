"""Common API interaction patterns and helpers.

This module provides reusable API interaction functionality to eliminate
duplicate patterns across command modules.
"""

from typing import Dict, Any, List, Optional, Tuple
from ..api.project_client import ProjectApiClient
from .filtering import extract_embedded_items
from .project_resolution import resolve_project_id_to_uuid


def fetch_all_projects(api_client: Optional[ProjectApiClient] = None,
                      name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all projects with optional name filtering.
    
    Args:
        api_client: Optional API client instance
        name_filter: Optional name filter to apply
        
    Returns:
        List of all projects matching the filter
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    filter_expr = f"name:{name_filter}" if name_filter else None
    
    # Start with first page to get total count
    response = api_client.get_projects(page=0, size=100, filter_expression=filter_expr)
    all_projects = extract_embedded_items(response, 'items')
    
    # Get remaining pages if needed
    page_info = response.get('page', {})
    total_elements = page_info.get('totalElements', 0)
    current_size = len(all_projects)
    
    page = 1
    while current_size < total_elements:
        response = api_client.get_projects(page=page, size=100, filter_expression=filter_expr)
        projects = extract_embedded_items(response, 'items')
        all_projects.extend(projects)
        current_size += len(projects)
        page += 1
        
        # Safety check to avoid infinite loops
        if len(projects) == 0:
            break
    
    return all_projects


def fetch_project_data(project_id: str, 
                      api_client: Optional[ProjectApiClient] = None) -> Dict[str, Any]:
    """Fetch complete project data by ID.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        api_client: Optional API client instance
        
    Returns:
        Project data dictionary
        
    Raises:
        Exception: If project not found or API error
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    project_uuid = resolve_project_id_to_uuid(project_id, api_client)
    return api_client.get_project(project_uuid)


def fetch_project_threats(project_id: str,
                         api_client: Optional[ProjectApiClient] = None) -> List[Dict[str, Any]]:
    """Fetch all threats for a project.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        api_client: Optional API client instance
        
    Returns:
        List of threat data
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    project_uuid = resolve_project_id_to_uuid(project_id, api_client)
    response = api_client.get_project_threats(project_uuid)
    return extract_embedded_items(response, 'items')


def fetch_project_countermeasures(project_id: str,
                                 api_client: Optional[ProjectApiClient] = None) -> List[Dict[str, Any]]:
    """Fetch all countermeasures for a project.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        api_client: Optional API client instance
        
    Returns:
        List of countermeasure data
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    project_uuid = resolve_project_id_to_uuid(project_id, api_client)
    response = api_client.get_project_countermeasures(project_uuid)
    return extract_embedded_items(response, 'items')


def fetch_project_components(project_id: str,
                           api_client: Optional[ProjectApiClient] = None) -> List[Dict[str, Any]]:
    """Fetch all components for a project.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        api_client: Optional API client instance
        
    Returns:
        List of component data
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    project_uuid = resolve_project_id_to_uuid(project_id, api_client)
    response = api_client.get_project_components(project_uuid)
    return extract_embedded_items(response, 'items')


def update_threat_status(project_id: str,
                        threat_id: str,
                        status: str,
                        reason: str,
                        comment: Optional[str] = None,
                        api_client: Optional[ProjectApiClient] = None) -> Dict[str, Any]:
    """Update threat status with consistent formatting.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        threat_id: Threat ID
        status: New status
        reason: Reason for the change
        comment: Optional comment
        api_client: Optional API client instance
        
    Returns:
        API response
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    # Format comment with reason if provided
    formatted_comment = reason
    if comment:
        formatted_comment = f"{reason}\n\nImplementation Details:\n{comment}"
    
    return api_client.update_threat_state(threat_id, status, formatted_comment)


def update_countermeasure_status(project_id: str,
                               countermeasure_id: str,
                               status: str,
                               reason: str,
                               comment: Optional[str] = None,
                               api_client: Optional[ProjectApiClient] = None) -> Dict[str, Any]:
    """Update countermeasure status with consistent formatting.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        countermeasure_id: Countermeasure ID
        status: New status
        reason: Reason for the change
        comment: Optional comment
        api_client: Optional API client instance
        
    Returns:
        API response
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    return api_client.update_countermeasure_state(countermeasure_id, status, reason, comment)


def create_threat_comment(project_id: str,
                         threat_id: str,
                         comment: str,
                         api_client: Optional[ProjectApiClient] = None) -> Dict[str, Any]:
    """Create a comment on a threat.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        threat_id: Threat ID
        comment: Comment text
        api_client: Optional API client instance
        
    Returns:
        API response
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    return api_client.create_threat_comment(threat_id, comment)


def create_countermeasure_comment(project_id: str,
                                countermeasure_id: str,
                                comment: str,
                                api_client: Optional[ProjectApiClient] = None) -> Dict[str, Any]:
    """Create a comment on a countermeasure.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        countermeasure_id: Countermeasure ID
        comment: Comment text
        api_client: Optional API client instance
        
    Returns:
        API response
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    return api_client.create_countermeasure_comment(countermeasure_id, comment)


def get_paginated_results(fetch_function: callable,
                         page_size: int = 100,
                         max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    """Generic helper for fetching paginated results.
    
    Args:
        fetch_function: Function that takes (page, size) and returns paginated response
        page_size: Number of items per page
        max_pages: Optional maximum number of pages to fetch
        
    Returns:
        List of all items from all pages
    """
    all_items = []
    page = 0
    
    while True:
        if max_pages and page >= max_pages:
            break
            
        response = fetch_function(page, page_size)
        items = extract_embedded_items(response, 'items')
        
        if not items:
            break
            
        all_items.extend(items)
        
        # Check if we've got all items
        page_info = response.get('page', {})
        total_elements = page_info.get('totalElements', 0)
        
        if len(all_items) >= total_elements:
            break
            
        page += 1
    
    return all_items


def validate_project_exists(project_id: str,
                          api_client: Optional[ProjectApiClient] = None) -> Tuple[bool, str]:
    """Validate that a project exists and return its UUID.
    
    Args:
        project_id: Project ID (UUID or reference ID)
        api_client: Optional API client instance
        
    Returns:
        Tuple of (exists, uuid) where exists is boolean and uuid is the project UUID
    """
    if api_client is None:
        api_client = ProjectApiClient()
    
    try:
        project_uuid = resolve_project_id_to_uuid(project_id, api_client)
        # Try to fetch the project to confirm it exists
        api_client.get_project(project_uuid)
        return True, project_uuid
    except Exception:
        return False, ""


def batch_update_items(items: List[Dict[str, Any]],
                      update_function: callable,
                      batch_size: int = 10) -> List[Dict[str, Any]]:
    """Process items in batches to avoid overwhelming the API.
    
    Args:
        items: List of items to update
        update_function: Function that takes an item and returns the update result
        batch_size: Number of items to process in each batch
        
    Returns:
        List of update results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        for item in batch:
            try:
                result = update_function(item)
                results.append(result)
            except Exception as e:
                results.append({'error': str(e), 'item': item})
    
    return results
