"""
Consolidated assertion utilities for IriusRisk CLI testing.

This module provides reusable assertion functions for validating
API responses, CLI output, and data structures.
"""

import json
import re
from typing import Dict, Any, List, Optional


def assert_cli_success(result, expected_output=None):
    """Helper function to assert CLI command success."""
    assert result.exit_code == 0, f"CLI command failed with output: {result.output}"
    if expected_output:
        assert expected_output in result.output


def assert_cli_failure(result, expected_error=None):
    """Helper function to assert CLI command failure."""
    assert result.exit_code != 0, f"CLI command should have failed but succeeded with output: {result.output}"
    if expected_error:
        assert expected_error in result.output


def assert_json_structure(data: Dict[str, Any], expected_keys: List[str], required_types: Dict[str, type] = None):
    """Assert that a JSON response has the expected structure and types."""
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    
    for key in expected_keys:
        assert key in data, f"Missing expected key '{key}' in response"
    
    # Validate types if provided
    if required_types:
        for key, expected_type in required_types.items():
            if key in data:
                assert isinstance(data[key], expected_type), \
                    f"Key '{key}' should be {expected_type.__name__}, got {type(data[key])}"


def assert_api_response_structure(response: Dict[str, Any], expect_items: bool = True):
    """Assert that an API response has the correct IriusRisk API structure."""
    assert isinstance(response, dict), f"API response should be dict, got {type(response)}"
    
    # Check for HAL+JSON structure
    assert '_embedded' in response, "API response should have _embedded structure"
    assert 'items' in response['_embedded'], "API response should have items in _embedded"
    assert isinstance(response['_embedded']['items'], list), "Items should be a list"
    
    # Check pagination info
    if 'page' in response:
        page_info = response['page']
        assert isinstance(page_info, dict), "Page info should be dict"
        
        # Validate page fields
        required_page_fields = ['size', 'totalElements', 'totalPages', 'number']
        for field in required_page_fields:
            if field in page_info:
                assert isinstance(page_info[field], int), f"Page {field} should be integer"
                assert page_info[field] >= 0, f"Page {field} should be non-negative"
    
    # Validate items if expected
    if expect_items:
        items = response['_embedded']['items']
        assert len(items) > 0, "Expected API response to contain items"
        
        # Each item should be a dict with at least an ID
        for item in items:
            assert isinstance(item, dict), "Each item should be a dict"
            assert 'id' in item, "Each item should have an ID"
            assert isinstance(item['id'], str), "Item ID should be string"
    
    return response['_embedded']['items']


def assert_project_structure(project: Dict[str, Any]):
    """Assert that a project object has the correct structure and valid data."""
    required_fields = ['id', 'name']
    optional_fields = ['referenceId', 'description', 'tags', 'status', 'workflowState']
    
    # Check required fields
    for field in required_fields:
        assert field in project, f"Project missing required field: {field}"
        assert project[field], f"Project {field} should not be empty"
        assert isinstance(project[field], str), f"Project {field} should be string"
    
    # Validate ID format (should be UUID)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, project['id'], re.IGNORECASE), \
        f"Project ID should be valid UUID format, got: {project['id']}"
    
    # Validate name is meaningful (not just whitespace or placeholder)
    name = project['name'].strip()
    assert len(name) > 0, "Project name should not be empty or whitespace"
    assert not name.lower().startswith('test') or len(name) > 4, \
        f"Project name appears to be a placeholder: {name}"
    
    # Validate optional fields if present
    for field in optional_fields:
        if field in project and project[field] is not None:
            if field == 'workflowState':
                # workflowState is an object
                assert isinstance(project[field], dict), f"Project {field} should be dict"
                if 'uuid' in project[field]:
                    assert re.match(uuid_pattern, project[field]['uuid'], re.IGNORECASE), \
                        f"WorkflowState UUID should be valid format: {project[field]['uuid']}"
            elif field == 'status':
                # Status should be a valid project status
                valid_statuses = ['ACTIVE', 'INACTIVE', 'ARCHIVED', 'DRAFT']
                if project[field]:  # Only validate if not empty
                    assert project[field] in valid_statuses, \
                        f"Project status should be one of {valid_statuses}, got: {project[field]}"
            else:
                assert isinstance(project[field], str), f"Project {field} should be string"


def assert_countermeasure_structure(countermeasure: Dict[str, Any]):
    """Assert that a countermeasure object has the correct structure and valid data."""
    required_fields = ['id', 'name']
    optional_fields = ['description', 'state', 'priority', 'implementationStatus']
    
    # Check required fields
    for field in required_fields:
        assert field in countermeasure, f"Countermeasure missing required field: {field}"
        assert countermeasure[field], f"Countermeasure {field} should not be empty"
        assert isinstance(countermeasure[field], str), f"Countermeasure {field} should be string"
    
    # Validate ID format (should be UUID)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, countermeasure['id'], re.IGNORECASE), \
        f"Countermeasure ID should be valid UUID format, got: {countermeasure['id']}"
    
    # Validate name is meaningful
    name = countermeasure['name'].strip()
    assert len(name) > 0, "Countermeasure name should not be empty or whitespace"
    
    # Validate optional fields if present
    for field in optional_fields:
        if field in countermeasure and countermeasure[field] is not None:
            if field == 'state':
                valid_states = ['required', 'recommended', 'implemented', 'rejected', 'not-applicable']
                assert countermeasure[field] in valid_states, \
                    f"Countermeasure state should be one of {valid_states}, got: {countermeasure[field]}"
            elif field == 'priority':
                valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
                assert countermeasure[field] in valid_priorities, \
                    f"Countermeasure priority should be one of {valid_priorities}, got: {countermeasure[field]}"
            elif field == 'implementationStatus':
                valid_statuses = ['not-implemented', 'partially-implemented', 'implemented', 'not-applicable']
                assert countermeasure[field] in valid_statuses, \
                    f"Implementation status should be one of {valid_statuses}, got: {countermeasure[field]}"
            else:
                assert isinstance(countermeasure[field], str), f"Countermeasure {field} should be string"


def assert_threat_structure(threat: Dict[str, Any]):
    """Assert that a threat object has the correct structure and valid data."""
    required_fields = ['id', 'name']
    optional_fields = ['description', 'state', 'riskRating', 'availability', 'confidentiality', 'integrity']
    
    # Check required fields
    for field in required_fields:
        assert field in threat, f"Threat missing required field: {field}"
        assert threat[field], f"Threat {field} should not be empty"
        assert isinstance(threat[field], str), f"Threat {field} should be string"
    
    # Validate ID format (should be UUID)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, threat['id'], re.IGNORECASE), \
        f"Threat ID should be valid UUID format, got: {threat['id']}"
    
    # Validate name is meaningful
    name = threat['name'].strip()
    assert len(name) > 0, "Threat name should not be empty or whitespace"
    
    # Validate optional fields if present
    for field in optional_fields:
        if field in threat and threat[field] is not None:
            if field in ['availability', 'confidentiality', 'integrity']:
                # These should be numbers between 0-100
                assert isinstance(threat[field], (int, float)), f"Threat {field} should be number"
                assert 0 <= threat[field] <= 100, f"Threat {field} should be 0-100, got: {threat[field]}"
            elif field == 'state':
                valid_states = ['expose', 'accept', 'mitigate', 'partly-mitigate', 'hidden', 'not-applicable']
                assert threat[field] in valid_states, \
                    f"Threat state should be one of {valid_states}, got: {threat[field]}"
            elif field == 'riskRating':
                valid_ratings = ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
                assert threat[field] in valid_ratings, \
                    f"Risk rating should be one of {valid_ratings}, got: {threat[field]}"
            else:
                assert isinstance(threat[field], str), f"Threat {field} should be string"


def assert_table_output(output: str, expected_headers: List[str], min_rows: int = 1):
    """Assert that CLI table output has expected structure."""
    lines = output.strip().split('\n')
    
    # Check headers are present
    header_line = None
    for line in lines:
        if any(header in line for header in expected_headers):
            header_line = line
            break
    
    assert header_line is not None, f"Expected headers {expected_headers} not found in output"
    
    # Count data rows (excluding headers and separators)
    data_rows = [line for line in lines if line.strip() and not line.startswith('-') and line != header_line]
    assert len(data_rows) >= min_rows, f"Expected at least {min_rows} data rows, got {len(data_rows)}"
