"""Tests for OTM utility functions."""

import pytest
from src.iriusrisk_cli.utils.otm_utils import (
    strip_layout_from_otm, 
    has_layout_data,
    validate_otm_schema,
    get_otm_validation_summary
)


def test_strip_layout_from_otm_with_yaml():
    """Test stripping layout data using PyYAML."""
    otm_with_layout = """otmVersion: 0.1.0
project:
  name: "Test Project"
  id: "test-project"

components:
  - id: "component-1"
    name: "Component 1"
    type: "web-service"
    representation:
      position:
        x: 100
        y: 200
      size:
        width: 85
        height: 85
  - id: "component-2"
    name: "Component 2"
    type: "database"
    representation:
      position:
        x: 300
        y: 200
      size:
        width: 85
        height: 85
"""
    
    result = strip_layout_from_otm(otm_with_layout)
    
    # Verify layout data is removed
    assert 'representation:' not in result
    assert 'position:' not in result
    assert 'size:' not in result
    
    # Verify structure is preserved
    assert 'component-1' in result
    assert 'component-2' in result
    assert 'web-service' in result
    assert 'database' in result


def test_strip_layout_preserves_structure():
    """Test that stripping layout preserves component structure."""
    otm_with_layout = """otmVersion: 0.1.0
project:
  name: "Test Project"
  id: "test-project"

trustZones:
  - id: "internet"
    name: "Internet"
    risk:
      trustRating: 1
    representation:
      position:
        x: 0
        y: 0
      size:
        width: 500
        height: 500

components:
  - id: "web-app"
    name: "Web Application"
    type: "web-service"
    parent:
      trustZone: "internet"
    representation:
      position:
        x: 100
        y: 100
      size:
        width: 85
        height: 85

dataflows:
  - id: "flow-1"
    source: "web-app"
    destination: "database"
"""
    
    result = strip_layout_from_otm(otm_with_layout)
    
    # Verify structure is preserved
    assert 'trustZones:' in result
    assert 'internet' in result
    assert 'trustRating: 1' in result
    
    assert 'components:' in result
    assert 'web-app' in result
    assert 'parent:' in result
    assert 'trustZone: internet' in result
    
    assert 'dataflows:' in result
    assert 'flow-1' in result
    
    # Verify layout is removed
    assert 'representation:' not in result


def test_has_layout_data_true():
    """Test detecting layout data presence."""
    otm_with_layout = """components:
  - id: "test"
    representation:
      position:
        x: 100
"""
    
    assert has_layout_data(otm_with_layout) is True


def test_has_layout_data_false():
    """Test detecting absence of layout data."""
    otm_without_layout = """components:
  - id: "test"
    name: "Test Component"
"""
    
    assert has_layout_data(otm_without_layout) is False


def test_strip_layout_empty_otm():
    """Test stripping layout from OTM with no components."""
    otm_minimal = """otmVersion: 0.1.0
project:
  name: "Minimal Project"
  id: "minimal"
"""
    
    result = strip_layout_from_otm(otm_minimal)
    
    # Should not fail, just return similar content
    assert 'Minimal Project' in result
    assert 'minimal' in result


def test_strip_layout_already_clean():
    """Test stripping layout from OTM that has no layout data."""
    otm_clean = """otmVersion: 0.1.0
project:
  name: "Clean Project"
  id: "clean"

components:
  - id: "component-1"
    name: "Component 1"
    type: "web-service"
"""
    
    result = strip_layout_from_otm(otm_clean)
    
    # Should preserve everything
    assert 'component-1' in result
    assert 'web-service' in result
    assert 'representation:' not in result


def test_validate_otm_schema_valid():
    """Test validation of valid OTM."""
    valid_otm = """otmVersion: "0.1.0"
project:
  name: "Test Project"
  id: "test-project"

trustZones:
  - id: "internet"
    name: "Internet"
    risk:
      trustRating: 1

components:
  - id: "web-app"
    name: "Web Application"
    type: "web-service"
    parent:
      trustZone: "internet"

dataflows:
  - id: "flow-1"
    name: "User Request"
    source: "web-app"
    destination: "database"
"""
    
    is_valid, errors = validate_otm_schema(valid_otm)
    
    # Should pass validation (or skip if jsonschema not available)
    if errors is not None:  # None means validation was skipped
        assert is_valid is True
        assert errors is None


def test_validate_otm_schema_missing_required():
    """Test validation catches missing required fields."""
    invalid_otm = """otmVersion: "0.1.0"
project:
  name: "Test Project"
  # Missing required 'id' field

components:
  - id: "web-app"
    name: "Web Application"
    type: "web-service"
    # Missing required 'parent' field
"""
    
    is_valid, errors = validate_otm_schema(invalid_otm)
    
    # Should fail validation (or skip if jsonschema not available)
    if errors is not None:  # None means validation was skipped
        assert is_valid is False
        assert len(errors) > 0
        # Should mention missing fields
        error_text = " ".join(errors)
        assert 'id' in error_text.lower() or 'parent' in error_text.lower()


def test_get_otm_validation_summary():
    """Test getting OTM validation summary."""
    otm_content = """otmVersion: "0.1.0"
project:
  name: "Test Project"
  id: "test-project-123"

trustZones:
  - id: "zone-1"
    name: "Zone 1"
    risk:
      trustRating: 5

components:
  - id: "comp-1"
    name: "Component 1"
    type: "web-service"
    parent:
      trustZone: "zone-1"
  - id: "comp-2"
    name: "Component 2"
    type: "database"
    parent:
      trustZone: "zone-1"

dataflows:
  - id: "flow-1"
    name: "Flow 1"
    source: "comp-1"
    destination: "comp-2"

threats:
  - id: "threat-1"
    name: "Threat 1"
    risk:
      likelihood: 3
      impact: 4

mitigations:
  - id: "mit-1"
    name: "Mitigation 1"
    riskReduction: 50
"""
    
    summary = get_otm_validation_summary(otm_content)
    
    assert summary['has_project'] is True
    assert summary['project_id'] == "test-project-123"
    assert summary['project_name'] == "Test Project"
    assert summary['trust_zones_count'] == 1
    assert summary['components_count'] == 2
    assert summary['dataflows_count'] == 1
    assert summary['threats_count'] == 1
    assert summary['mitigations_count'] == 1
