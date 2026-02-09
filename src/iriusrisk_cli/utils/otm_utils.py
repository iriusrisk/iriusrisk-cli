"""OTM (Open Threat Model) utility functions.

This module provides utilities for manipulating OTM files, including
layout reset functionality and schema validation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def strip_layout_from_otm(otm_content: str) -> str:
    """Remove all layout/positioning data from OTM content.
    
    This removes the 'representation' section from all components and trust zones,
    forcing IriusRisk to auto-layout the diagram from scratch.
    
    Removes:
    - representation.position (x, y coordinates)
    - representation.size (width, height)
    - Any other representation data
    
    This is useful when:
    - The diagram has become messy after multiple updates
    - You want IriusRisk's auto-layout to reorganize everything
    - Major architectural refactoring makes old positions irrelevant
    
    Args:
        otm_content: OTM content as string (YAML format)
        
    Returns:
        Modified OTM content with all layout data removed
        
    Example:
        >>> otm = load_otm_file("threat-model.otm")
        >>> clean_otm = strip_layout_from_otm(otm)
        >>> # clean_otm has no position/size data
    """
    try:
        # Try to use PyYAML for proper parsing if available
        import yaml
        
        logger.debug("Using PyYAML to strip layout from OTM")
        
        # Parse the OTM
        otm_data = yaml.safe_load(otm_content)
        
        # Remove representation from components
        if 'components' in otm_data:
            for component in otm_data['components']:
                if 'representation' in component:
                    del component['representation']
                    logger.debug(f"Removed representation from component: {component.get('id', 'unknown')}")
        
        # Remove representation from trust zones
        if 'trustZones' in otm_data:
            for trust_zone in otm_data['trustZones']:
                if 'representation' in trust_zone:
                    del trust_zone['representation']
                    logger.debug(f"Removed representation from trust zone: {trust_zone.get('id', 'unknown')}")
        
        # Remove representation from dataflows (if any have routing points)
        if 'dataflows' in otm_data:
            for dataflow in otm_data['dataflows']:
                if 'representation' in dataflow:
                    del dataflow['representation']
                    logger.debug(f"Removed representation from dataflow: {dataflow.get('id', 'unknown')}")
        
        # Convert back to YAML
        modified_content = yaml.dump(otm_data, default_flow_style=False, sort_keys=False)
        
        logger.info("Successfully stripped layout data from OTM using PyYAML")
        return modified_content
        
    except ImportError:
        # PyYAML not available, use regex-based approach
        logger.warning("PyYAML not available, using regex-based layout stripping (less reliable)")
        return _strip_layout_regex(otm_content)


def _strip_layout_regex(otm_content: str) -> str:
    """Strip layout using regex (fallback when PyYAML not available).
    
    This is less reliable than YAML parsing but works without dependencies.
    
    Args:
        otm_content: OTM content as string
        
    Returns:
        Modified OTM content with layout data removed
    """
    # Pattern to match entire representation blocks
    # Matches:
    #   representation:
    #     position:
    #       x: 100
    #       y: 200
    #     size:
    #       width: 85
    #       height: 85
    
    # Remove representation blocks (handles multi-line with proper indentation)
    pattern = r'^\s*representation:\s*\n(?:\s+\w+:.*\n)*'
    modified = re.sub(pattern, '', otm_content, flags=re.MULTILINE)
    
    # Also handle single-line representation if any
    modified = re.sub(r'^\s*representation:.*$', '', modified, flags=re.MULTILINE)
    
    # Clean up any resulting multiple blank lines
    modified = re.sub(r'\n\n\n+', '\n\n', modified)
    
    logger.info("Stripped layout data from OTM using regex")
    return modified


def has_layout_data(otm_content: str) -> bool:
    """Check if OTM content contains layout/positioning data.
    
    Args:
        otm_content: OTM content as string
        
    Returns:
        True if layout data is present, False otherwise
    """
    try:
        import yaml
        otm_data = yaml.safe_load(otm_content)
        
        # Check components
        if 'components' in otm_data:
            for component in otm_data['components']:
                if 'representation' in component:
                    return True
        
        # Check trust zones
        if 'trustZones' in otm_data:
            for trust_zone in otm_data['trustZones']:
                if 'representation' in trust_zone:
                    return True
        
        # Check dataflows
        if 'dataflows' in otm_data:
            for dataflow in otm_data['dataflows']:
                if 'representation' in dataflow:
                    return True
        
        return False
        
    except ImportError:
        # Fallback to simple string search
        return 'representation:' in otm_content


def validate_otm_schema(otm_content: str) -> Tuple[bool, Optional[List[str]]]:
    """Validate OTM content against the official JSON schema.
    
    This validates the OTM structure to ensure it conforms to the Open Threat Model
    specification before import. This helps catch issues early and prevents data loss.
    
    Args:
        otm_content: OTM content as string (YAML or JSON format)
        
    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if validation passes, False otherwise
        - error_messages: List of validation error messages, or None if valid
        
    Example:
        >>> is_valid, errors = validate_otm_schema(otm_content)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"Validation error: {error}")
    """
    try:
        # Try to import jsonschema for validation
        try:
            import jsonschema
            from jsonschema import validate, ValidationError, Draft7Validator
        except ImportError:
            logger.warning("jsonschema package not available - skipping OTM validation")
            logger.warning("Install with: pip install jsonschema")
            return True, None  # Skip validation if jsonschema not available
        
        # Parse OTM content (could be YAML or JSON)
        try:
            import yaml
            otm_data = yaml.safe_load(otm_content)
        except ImportError:
            # Try JSON parsing if YAML not available
            otm_data = json.loads(otm_content)
        
        # Load the OTM schema
        schema_path = Path(__file__).parent.parent / 'otm_schema.json'
        
        if not schema_path.exists():
            logger.warning(f"OTM schema file not found at {schema_path} - skipping validation")
            return True, None
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Validate against schema
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(otm_data))
        
        if errors:
            error_messages = []
            for error in errors:
                # Build a user-friendly error message
                path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                message = f"At '{path}': {error.message}"
                error_messages.append(message)
                logger.error(f"OTM validation error: {message}")
            
            return False, error_messages
        
        logger.info("OTM validation passed")
        return True, None
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON/YAML format: {e}"
        logger.error(f"OTM parsing error: {error_msg}")
        return False, [error_msg]
    except Exception as e:
        error_msg = f"Validation error: {e}"
        logger.error(f"OTM validation failed: {error_msg}")
        return False, [error_msg]


def get_otm_validation_summary(otm_content: str) -> Dict[str, Any]:
    """Get a summary of OTM content for validation reporting.
    
    This provides a quick overview of what's in the OTM file to help
    users understand what might be missing or incorrect.
    
    Args:
        otm_content: OTM content as string
        
    Returns:
        Dictionary with counts of major elements:
        {
            'has_project': bool,
            'project_id': str or None,
            'project_name': str or None,
            'trust_zones_count': int,
            'components_count': int,
            'dataflows_count': int,
            'threats_count': int,
            'mitigations_count': int
        }
    """
    try:
        import yaml
        otm_data = yaml.safe_load(otm_content)
    except ImportError:
        otm_data = json.loads(otm_content)
    
    summary = {
        'has_project': 'project' in otm_data,
        'project_id': otm_data.get('project', {}).get('id'),
        'project_name': otm_data.get('project', {}).get('name'),
        'trust_zones_count': len(otm_data.get('trustZones', [])),
        'components_count': len(otm_data.get('components', [])),
        'dataflows_count': len(otm_data.get('dataflows', [])),
        'threats_count': len(otm_data.get('threats', [])),
        'mitigations_count': len(otm_data.get('mitigations', []))
    }
    
    return summary
