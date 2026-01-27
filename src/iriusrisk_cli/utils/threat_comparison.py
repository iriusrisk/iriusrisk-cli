"""Threat and countermeasure comparison utilities for CI/CD drift detection.

This module provides functions to compare threats and countermeasures JSON data
to identify security changes between threat model versions.
"""

import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def parse_threats_json(json_content: str) -> List[Dict[str, Any]]:
    """Parse threats JSON response from IriusRisk API.
    
    Args:
        json_content: JSON string containing threats data
        
    Returns:
        List of threat dictionaries
    """
    try:
        data = json.loads(json_content) if isinstance(json_content, str) else json_content
        threats = data.get('_embedded', {}).get('threats', [])
        logger.info(f"Parsed {len(threats)} threats from JSON")
        return threats
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse threats JSON: {e}")
        raise ValueError(f"Invalid threats JSON format: {e}")


def parse_countermeasures_json(json_content: str) -> List[Dict[str, Any]]:
    """Parse countermeasures JSON response from IriusRisk API.
    
    Args:
        json_content: JSON string containing countermeasures data
        
    Returns:
        List of countermeasure dictionaries
    """
    try:
        data = json.loads(json_content) if isinstance(json_content, str) else json_content
        countermeasures = data.get('_embedded', {}).get('countermeasures', [])
        logger.info(f"Parsed {len(countermeasures)} countermeasures from JSON")
        return countermeasures
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse countermeasures JSON: {e}")
        raise ValueError(f"Invalid countermeasures JSON format: {e}")


def compare_threats(baseline: List[Dict], target: List[Dict]) -> Dict[str, Any]:
    """Compare two threat lists and identify changes.
    
    Args:
        baseline: List of threats from baseline
        target: List of threats from target
        
    Returns:
        Structured diff showing added, removed, and modified threats
    """
    # Create dictionaries keyed by ID for fast lookup
    baseline_dict = {threat['id']: threat for threat in baseline}
    target_dict = {threat['id']: threat for threat in target}
    
    baseline_ids = set(baseline_dict.keys())
    target_ids = set(target_dict.keys())
    
    # Identify added and removed
    added_ids = target_ids - baseline_ids
    removed_ids = baseline_ids - target_ids
    common_ids = baseline_ids & target_ids
    
    added = [_enrich_threat(target_dict[id]) for id in added_ids]
    removed = [_enrich_threat(baseline_dict[id]) for id in removed_ids]
    
    # Identify modified threats
    modified = []
    severity_increases = []
    
    for threat_id in common_ids:
        baseline_threat = baseline_dict[threat_id]
        target_threat = target_dict[threat_id]
        
        changes = _find_threat_changes(baseline_threat, target_threat)
        if changes:
            modified_item = {
                'id': threat_id,
                'referenceId': target_threat.get('referenceId'),
                'name': target_threat.get('name'),
                'changes': changes
            }
            modified.append(modified_item)
            
            # Track severity increases
            if 'riskRating' in changes:
                old_severity = changes['riskRating']['old']
                new_severity = changes['riskRating']['new']
                if _is_severity_increase(old_severity, new_severity):
                    severity_increases.append({
                        'threat_id': threat_id,
                        'threat_name': target_threat.get('name'),
                        'old_severity': old_severity,
                        'new_severity': new_severity
                    })
    
    result = {
        'added': added,
        'removed': removed,
        'modified': modified,
        'severity_increases': severity_increases
    }
    
    logger.info(f"Threat comparison: {len(added)} added, {len(removed)} removed, "
                f"{len(modified)} modified, {len(severity_increases)} severity increases")
    
    return result


def compare_countermeasures(baseline: List[Dict], target: List[Dict]) -> Dict[str, Any]:
    """Compare two countermeasure lists and identify changes.
    
    Args:
        baseline: List of countermeasures from baseline
        target: List of countermeasures from target
        
    Returns:
        Structured diff showing added, removed, and modified countermeasures
    """
    # Create dictionaries keyed by ID for fast lookup
    baseline_dict = {cm['id']: cm for cm in baseline}
    target_dict = {cm['id']: cm for cm in target}
    
    baseline_ids = set(baseline_dict.keys())
    target_ids = set(target_dict.keys())
    
    # Identify added and removed
    added_ids = target_ids - baseline_ids
    removed_ids = baseline_ids - target_ids
    common_ids = baseline_ids & target_ids
    
    added = [_enrich_countermeasure(target_dict[id]) for id in added_ids]
    removed = [_enrich_countermeasure(baseline_dict[id]) for id in removed_ids]
    
    # Identify modified countermeasures
    modified = []
    critical_removals = []
    
    for cm_id in common_ids:
        baseline_cm = baseline_dict[cm_id]
        target_cm = target_dict[cm_id]
        
        changes = _find_countermeasure_changes(baseline_cm, target_cm)
        if changes:
            modified.append({
                'id': cm_id,
                'referenceId': target_cm.get('referenceId'),
                'name': target_cm.get('name'),
                'changes': changes
            })
    
    # Identify critical removals (implemented countermeasures that were removed)
    for cm_id in removed_ids:
        removed_cm = baseline_dict[cm_id]
        if removed_cm.get('state') == 'implemented':
            critical_removals.append({
                'countermeasure_id': cm_id,
                'countermeasure_name': removed_cm.get('name'),
                'severity': 'CRITICAL',
                'reason': 'Implemented countermeasure was removed'
            })
    
    result = {
        'added': added,
        'removed': removed,
        'modified': modified,
        'critical_removals': critical_removals
    }
    
    logger.info(f"Countermeasure comparison: {len(added)} added, {len(removed)} removed, "
                f"{len(modified)} modified, {len(critical_removals)} critical removals")
    
    return result


def _enrich_threat(threat: Dict) -> Dict:
    """Enrich threat data with relevant fields for comparison.
    
    Args:
        threat: Threat dictionary from API
        
    Returns:
        Enriched threat dictionary with key fields
    """
    return {
        'id': threat.get('id'),
        'referenceId': threat.get('referenceId'),
        'name': threat.get('name'),
        'description': threat.get('description'),
        'riskRating': threat.get('riskRating'),
        'state': threat.get('state'),
        'categories': threat.get('categories', []),
        'components': [c.get('name') for c in threat.get('components', [])],
        'countermeasures': [cm.get('name') for cm in threat.get('countermeasures', [])]
    }


def _enrich_countermeasure(cm: Dict) -> Dict:
    """Enrich countermeasure data with relevant fields for comparison.
    
    Args:
        cm: Countermeasure dictionary from API
        
    Returns:
        Enriched countermeasure dictionary with key fields
    """
    return {
        'id': cm.get('id'),
        'referenceId': cm.get('referenceId'),
        'name': cm.get('name'),
        'description': cm.get('description'),
        'state': cm.get('state'),
        'mitigates_threats': [t.get('name') for t in cm.get('threats', [])],
        'components': [c.get('name') for c in cm.get('components', [])]
    }


def _find_threat_changes(baseline_threat: Dict, target_threat: Dict) -> Dict[str, Any]:
    """Find specific changes between two threats.
    
    Args:
        baseline_threat: Threat from baseline
        target_threat: Threat from target
        
    Returns:
        Dictionary of changes, or empty dict if no changes
    """
    changes = {}
    
    # Compare key fields
    fields_to_compare = ['riskRating', 'state', 'description']
    
    for field in fields_to_compare:
        baseline_value = baseline_threat.get(field)
        target_value = target_threat.get(field)
        
        if baseline_value != target_value:
            changes[field] = {
                'old': baseline_value,
                'new': target_value
            }
    
    return changes


def _find_countermeasure_changes(baseline_cm: Dict, target_cm: Dict) -> Dict[str, Any]:
    """Find specific changes between two countermeasures.
    
    Args:
        baseline_cm: Countermeasure from baseline
        target_cm: Countermeasure from target
        
    Returns:
        Dictionary of changes, or empty dict if no changes
    """
    changes = {}
    
    # Compare key fields
    fields_to_compare = ['state', 'description']
    
    for field in fields_to_compare:
        baseline_value = baseline_cm.get(field)
        target_value = target_cm.get(field)
        
        if baseline_value != target_value:
            changes[field] = {
                'old': baseline_value,
                'new': target_value
            }
    
    return changes


def _is_severity_increase(old_severity: str, new_severity: str) -> bool:
    """Determine if the severity increased.
    
    Args:
        old_severity: Old severity level
        new_severity: New severity level
        
    Returns:
        True if severity increased, False otherwise
    """
    severity_order = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    try:
        old_index = severity_order.index(old_severity) if old_severity else -1
        new_index = severity_order.index(new_severity) if new_severity else -1
        return new_index > old_index
    except ValueError:
        return False
