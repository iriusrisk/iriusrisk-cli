"""Diagram comparison utilities for CI/CD drift detection.

This module provides functions to parse mxGraph XML diagrams and compare them
to identify architectural changes (components, dataflows, trust zones).
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def parse_diagram_xml(xml_content: str) -> Dict[str, Any]:
    """Parse mxGraph XML diagram and extract components, dataflows, and trust zones.
    
    Args:
        xml_content: XML content as string (mxGraph format)
        
    Returns:
        Dictionary with extracted diagram elements:
        {
            'components': [{'id': str, 'name': str, 'type': str, ...}, ...],
            'dataflows': [{'id': str, 'source': str, 'target': str, ...}, ...],
            'trust_zones': [{'id': str, 'name': str, ...}, ...]
        }
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error(f"Failed to parse diagram XML: {e}")
        raise ValueError(f"Invalid XML format: {e}")
    
    components = []
    dataflows = []
    trust_zones = []
    
    # Find all mxCell elements
    for cell in root.findall('.//mxCell'):
        cell_id = cell.get('id')
        cell_style = cell.get('style', '')
        cell_value = cell.get('value', '')
        
        # Skip root cells
        if cell_id in ['0', '1']:
            continue
        
        # Identify component types based on style
        if 'component' in cell_style.lower() or 'shape=' in cell_style:
            # This is a component
            component = {
                'id': cell_id,
                'name': cell_value,
                'style': cell_style,
                'parent': cell.get('parent'),
                'vertex': cell.get('vertex') == '1'
            }
            
            # Extract geometry if present
            geometry = cell.find('mxGeometry')
            if geometry is not None:
                component['geometry'] = {
                    'x': geometry.get('x'),
                    'y': geometry.get('y'),
                    'width': geometry.get('width'),
                    'height': geometry.get('height')
                }
            
            components.append(component)
            
        elif cell.get('edge') == '1':
            # This is a dataflow (edge)
            dataflow = {
                'id': cell_id,
                'name': cell_value,
                'source': cell.get('source'),
                'target': cell.get('target'),
                'style': cell_style,
                'parent': cell.get('parent')
            }
            dataflows.append(dataflow)
        
        # Trust zones are typically containers (parent nodes with specific styles)
        elif cell.get('vertex') == '1' and ('container' in cell_style.lower() or 
                                             'swimlane' in cell_style.lower() or
                                             'trustBoundary' in cell_style):
            trust_zone = {
                'id': cell_id,
                'name': cell_value,
                'style': cell_style,
                'parent': cell.get('parent')
            }
            
            geometry = cell.find('mxGeometry')
            if geometry is not None:
                trust_zone['geometry'] = {
                    'x': geometry.get('x'),
                    'y': geometry.get('y'),
                    'width': geometry.get('width'),
                    'height': geometry.get('height')
                }
            
            trust_zones.append(trust_zone)
    
    logger.info(f"Parsed diagram: {len(components)} components, {len(dataflows)} dataflows, {len(trust_zones)} trust zones")
    
    return {
        'components': components,
        'dataflows': dataflows,
        'trust_zones': trust_zones
    }


def compare_diagrams(baseline_data: Dict[str, Any], target_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two parsed diagrams and identify changes.
    
    Args:
        baseline_data: Parsed baseline diagram
        target_data: Parsed target diagram
        
    Returns:
        Structured diff showing added, removed, and modified elements
    """
    result = {
        'components': _compare_elements(
            baseline_data.get('components', []),
            target_data.get('components', []),
            'component'
        ),
        'dataflows': _compare_elements(
            baseline_data.get('dataflows', []),
            target_data.get('dataflows', []),
            'dataflow'
        ),
        'trust_zones': _compare_elements(
            baseline_data.get('trust_zones', []),
            target_data.get('trust_zones', []),
            'trust_zone'
        )
    }
    
    # Add summary statistics
    result['summary'] = {
        'components_added': len(result['components']['added']),
        'components_removed': len(result['components']['removed']),
        'components_modified': len(result['components']['modified']),
        'dataflows_added': len(result['dataflows']['added']),
        'dataflows_removed': len(result['dataflows']['removed']),
        'dataflows_modified': len(result['dataflows']['modified']),
        'trust_zones_added': len(result['trust_zones']['added']),
        'trust_zones_removed': len(result['trust_zones']['removed']),
        'trust_zones_modified': len(result['trust_zones']['modified'])
    }
    
    logger.info(f"Diagram comparison complete: {result['summary']}")
    
    return result


def _compare_elements(baseline: List[Dict], target: List[Dict], element_type: str) -> Dict[str, List]:
    """Compare two lists of elements and identify added/removed/modified.
    
    Args:
        baseline: List of elements from baseline
        target: List of elements from target
        element_type: Type of element being compared (for logging)
        
    Returns:
        Dictionary with 'added', 'removed', and 'modified' lists
    """
    # Create dictionaries keyed by ID for fast lookup
    baseline_dict = {elem['id']: elem for elem in baseline}
    target_dict = {elem['id']: elem for elem in target}
    
    baseline_ids = set(baseline_dict.keys())
    target_ids = set(target_dict.keys())
    
    # Identify added and removed
    added_ids = target_ids - baseline_ids
    removed_ids = baseline_ids - target_ids
    common_ids = baseline_ids & target_ids
    
    added = [target_dict[id] for id in added_ids]
    removed = [baseline_dict[id] for id in removed_ids]
    
    # Identify modified (elements that exist in both but have differences)
    modified = []
    for elem_id in common_ids:
        baseline_elem = baseline_dict[elem_id]
        target_elem = target_dict[elem_id]
        
        changes = _find_element_changes(baseline_elem, target_elem)
        if changes:
            modified.append({
                'id': elem_id,
                'name': target_elem.get('name', 'Unknown'),
                'changes': changes
            })
    
    return {
        'added': added,
        'removed': removed,
        'modified': modified
    }


def _find_element_changes(baseline_elem: Dict, target_elem: Dict) -> Dict[str, Any]:
    """Find specific changes between two elements.
    
    Args:
        baseline_elem: Element from baseline
        target_elem: Element from target
        
    Returns:
        Dictionary of changes, or empty dict if no changes
    """
    changes = {}
    
    # Compare key fields
    fields_to_compare = ['name', 'style', 'parent', 'source', 'target']
    
    for field in fields_to_compare:
        baseline_value = baseline_elem.get(field)
        target_value = target_elem.get(field)
        
        if baseline_value != target_value and (baseline_value is not None or target_value is not None):
            changes[field] = {
                'old': baseline_value,
                'new': target_value
            }
    
    # Compare geometry if present
    baseline_geom = baseline_elem.get('geometry', {})
    target_geom = target_elem.get('geometry', {})
    
    if baseline_geom != target_geom:
        geom_changes = {}
        for key in ['x', 'y', 'width', 'height']:
            if baseline_geom.get(key) != target_geom.get(key):
                geom_changes[key] = {
                    'old': baseline_geom.get(key),
                    'new': target_geom.get(key)
                }
        if geom_changes:
            changes['geometry'] = geom_changes
    
    return changes
