"""Generic lookup utilities for finding items by ID.

This module provides reusable lookup functionality to eliminate
duplicate "find by ID" patterns across command modules.
"""

from typing import List, Dict, Any, Optional, Union


def find_item_by_id(items: List[Dict[str, Any]], 
                   item_id: str, 
                   id_fields: List[str] = None) -> Optional[Dict[str, Any]]:
    """Find an item by ID, checking multiple possible ID fields.
    
    Args:
        items: List of items to search
        item_id: ID to search for
        id_fields: List of field names to check (default: ['id', 'referenceId', 'ref'])
        
    Returns:
        First matching item or None if not found
    """
    if id_fields is None:
        id_fields = ['id', 'referenceId', 'ref']
    
    for item in items:
        for field in id_fields:
            if item.get(field) == item_id:
                return item
    
    return None


def find_threat_by_id(threats_data: List[Dict[str, Any]], threat_id: str) -> Optional[Dict[str, Any]]:
    """Find a specific threat by its ID within the threats data.
    
    This handles the complex nested structure of threats data from the API.
    
    Args:
        threats_data: List of threat components from API
        threat_id: Threat ID to find
        
    Returns:
        Threat data dictionary or None if not found
    """
    for component in threats_data:
        use_cases = component.get('useCase', {})
        
        if isinstance(use_cases, dict):
            # Single use case
            threats = use_cases.get('threats', [])
            for threat in threats:
                if (threat.get('id') == threat_id or 
                    threat.get('referenceId') == threat_id or
                    threat.get('ref') == threat_id):
                    return threat
        elif isinstance(use_cases, list):
            # Multiple use cases
            for use_case in use_cases:
                threats = use_case.get('threats', [])
                for threat in threats:
                    if (threat.get('id') == threat_id or 
                        threat.get('referenceId') == threat_id or
                        threat.get('ref') == threat_id):
                        return threat
    
    return None


def find_countermeasure_by_id(countermeasures_data: List[Dict[str, Any]], 
                             countermeasure_id: str) -> Optional[Dict[str, Any]]:
    """Find a specific countermeasure by its ID within the countermeasures data.
    
    Args:
        countermeasures_data: List of countermeasures from API
        countermeasure_id: Countermeasure ID to find (can be UUID 'id' or string 'referenceId')
        
    Returns:
        Countermeasure data dictionary or None if not found
    """
    for countermeasure in countermeasures_data:
        # Check both 'id' (UUID) and 'referenceId' (string reference) fields
        if (countermeasure.get('id') == countermeasure_id or 
            countermeasure.get('referenceId') == countermeasure_id or
            countermeasure.get('ref') == countermeasure_id):  # Keep 'ref' for backwards compatibility
            return countermeasure
    
    return None


def find_component_by_id(components_data: List[Dict[str, Any]], 
                        component_id: str) -> Optional[Dict[str, Any]]:
    """Find a specific component by its ID within the components data.
    
    Args:
        components_data: List of components from API
        component_id: Component ID to find (can be UUID or reference ID)
        
    Returns:
        Component data dictionary or None if not found
    """
    for component in components_data:
        # Check both UUID and reference ID
        if (component.get('id') == component_id or 
            component.get('referenceId') == component_id):
            return component
    
    return None


def find_item_by_name(items: List[Dict[str, Any]], 
                     name: str, 
                     name_field: str = 'name',
                     case_sensitive: bool = False) -> Optional[Dict[str, Any]]:
    """Find an item by name.
    
    Args:
        items: List of items to search
        name: Name to search for
        name_field: Field name containing the name (default: 'name')
        case_sensitive: Whether to perform case-sensitive matching
        
    Returns:
        First matching item or None if not found
    """
    for item in items:
        item_name = item.get(name_field, '')
        if case_sensitive:
            if item_name == name:
                return item
        else:
            if item_name.lower() == name.lower():
                return item
    
    return None


def find_items_by_field_value(items: List[Dict[str, Any]], 
                             field: str, 
                             value: Any,
                             exact_match: bool = True) -> List[Dict[str, Any]]:
    """Find all items where a field matches a specific value.
    
    Args:
        items: List of items to search
        field: Field name to check
        value: Value to match
        exact_match: If True, requires exact match. If False, does substring match for strings.
        
    Returns:
        List of matching items
    """
    matches = []
    
    for item in items:
        item_value = item.get(field)
        
        if exact_match:
            if item_value == value:
                matches.append(item)
        else:
            # For string values, do substring matching
            if isinstance(item_value, str) and isinstance(value, str):
                if value.lower() in item_value.lower():
                    matches.append(item)
            elif item_value == value:
                matches.append(item)
    
    return matches


def find_nested_item_by_path(data: Dict[str, Any], 
                            path: List[str], 
                            item_id: str,
                            id_field: str = 'id') -> Optional[Dict[str, Any]]:
    """Find an item in nested data structure by following a path.
    
    Args:
        data: Root data structure
        path: List of keys to navigate through the structure
        item_id: ID of the item to find
        id_field: Field name containing the ID
        
    Returns:
        Found item or None if not found
    """
    current = data
    
    # Navigate to the target list
    for key in path:
        if isinstance(current, dict):
            current = current.get(key, [])
        elif isinstance(current, list) and key.isdigit():
            index = int(key)
            if 0 <= index < len(current):
                current = current[index]
            else:
                return None
        else:
            return None
    
    # Search in the final list
    if isinstance(current, list):
        for item in current:
            if isinstance(item, dict) and item.get(id_field) == item_id:
                return item
    
    return None


def get_unique_values_from_field(items: List[Dict[str, Any]], 
                                field: str) -> List[Any]:
    """Extract unique values from a specific field across all items.
    
    Args:
        items: List of items
        field: Field name to extract values from
        
    Returns:
        List of unique values from the field
    """
    values = set()
    
    for item in items:
        value = item.get(field)
        if value is not None:
            values.add(value)
    
    return sorted(list(values))


def group_items_by_field(items: List[Dict[str, Any]], 
                        field: str) -> Dict[Any, List[Dict[str, Any]]]:
    """Group items by the value of a specific field.
    
    Args:
        items: List of items to group
        field: Field name to group by
        
    Returns:
        Dictionary mapping field values to lists of items
    """
    groups = {}
    
    for item in items:
        key = item.get(field, 'Unknown')
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    
    return groups
