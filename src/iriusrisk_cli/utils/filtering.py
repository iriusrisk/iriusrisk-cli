"""Generic filtering and search utilities.

This module provides reusable filtering functionality to eliminate
duplicate search/filter patterns across command modules.
"""

from typing import List, Dict, Any, Optional, Callable


def create_reference_id_filter(reference_id: str) -> str:
    """Create a filter expression for finding items by reference ID.
    
    Args:
        reference_id: The reference ID to filter by
        
    Returns:
        Filter expression string for API queries
    """
    return f"'referenceId'='{reference_id}'"


def create_name_filter(name: str) -> str:
    """Create a filter expression for finding items by name.
    
    Args:
        name: The name to filter by
        
    Returns:
        Filter expression string for API queries
    """
    return f"name:{name}"


def filter_items_by_search_term(items: List[Dict[str, Any]], 
                               search_term: str, 
                               search_fields: List[str]) -> List[Dict[str, Any]]:
    """Filter a list of items by searching in specified fields.
    
    Args:
        items: List of items to filter
        search_term: Term to search for (case-insensitive)
        search_fields: List of field names to search in
        
    Returns:
        Filtered list of items matching the search term
    """
    if not search_term:
        return items
    
    search_term_lower = search_term.lower()
    filtered_items = []
    
    for item in items:
        for field in search_fields:
            field_value = item.get(field, '')
            if isinstance(field_value, str) and search_term_lower in field_value.lower():
                filtered_items.append(item)
                break  # Found match, no need to check other fields for this item
    
    return filtered_items


def filter_items_by_status(items: List[Dict[str, Any]], 
                          status: str, 
                          status_field: str = 'status') -> List[Dict[str, Any]]:
    """Filter items by status field.
    
    Args:
        items: List of items to filter
        status: Status value to filter by
        status_field: Name of the status field (default: 'status')
        
    Returns:
        Filtered list of items with matching status
    """
    if not status:
        return items
    
    return [item for item in items if item.get(status_field, '').lower() == status.lower()]


def filter_items_by_risk_rating(items: List[Dict[str, Any]], 
                               risk_rating: str) -> List[Dict[str, Any]]:
    """Filter items by risk rating.
    
    Args:
        items: List of items to filter
        risk_rating: Risk rating to filter by (e.g., 'HIGH', 'MEDIUM', 'LOW')
        
    Returns:
        Filtered list of items with matching risk rating
    """
    if not risk_rating:
        return items
    
    return [item for item in items if item.get('riskRating', '').upper() == risk_rating.upper()]


def filter_items_by_custom_predicate(items: List[Dict[str, Any]], 
                                    predicate: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
    """Filter items using a custom predicate function.
    
    Args:
        items: List of items to filter
        predicate: Function that takes an item and returns True if it should be included
        
    Returns:
        Filtered list of items matching the predicate
    """
    return [item for item in items if predicate(item)]


def sort_items_by_field(items: List[Dict[str, Any]], 
                       field: str, 
                       reverse: bool = False) -> List[Dict[str, Any]]:
    """Sort items by a specific field.
    
    Args:
        items: List of items to sort
        field: Field name to sort by
        reverse: If True, sort in descending order
        
    Returns:
        Sorted list of items
    """
    return sorted(items, key=lambda x: x.get(field, ''), reverse=reverse)


def paginate_items(items: List[Dict[str, Any]], 
                  page: int = 0, 
                  size: int = 20) -> List[Dict[str, Any]]:
    """Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page: Page number (0-based)
        size: Number of items per page
        
    Returns:
        Paginated subset of items
    """
    start_index = page * size
    end_index = start_index + size
    return items[start_index:end_index]


def extract_embedded_items(api_response: Dict[str, Any], 
                          items_key: str = 'items') -> List[Dict[str, Any]]:
    """Extract items from HAL-style API response.
    
    Args:
        api_response: API response dictionary
        items_key: Key name for items in _embedded section
        
    Returns:
        List of items from the response
    """
    return api_response.get('_embedded', {}).get(items_key, [])


def build_search_filters(name: Optional[str] = None,
                        reference_id: Optional[str] = None,
                        status: Optional[str] = None) -> List[str]:
    """Build a list of filter expressions for common search criteria.
    
    Args:
        name: Optional name filter
        reference_id: Optional reference ID filter
        status: Optional status filter
        
    Returns:
        List of filter expressions
    """
    filters = []
    
    if name:
        filters.append(create_name_filter(name))
    
    if reference_id:
        filters.append(create_reference_id_filter(reference_id))
    
    if status:
        filters.append(f"status:{status}")
    
    return filters
