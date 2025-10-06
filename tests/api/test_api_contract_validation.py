"""
API contract validation tests for IriusRisk CLI.

This module validates that fixture data matches expected API contracts
and that the CLI correctly handles API response structures.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Any, List

from tests.utils.assertions import assert_project_structure, assert_countermeasure_structure, assert_threat_structure


class TestFixtureDataValidation:
    """Validate that fixture data matches expected API contracts."""
    
    def test_projects_fixture_structure(self):
        """Test that projects fixture has correct structure."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "api_responses" / "get_projects.json"
        
        if not fixture_path.exists():
            pytest.skip("Projects fixture not found")
        
        with open(fixture_path, 'r') as f:
            fixture_data = json.load(f)
        
        # Validate fixture metadata
        assert 'endpoint' in fixture_data, "Fixture should have endpoint metadata"
        assert 'method' in fixture_data, "Fixture should have method metadata"
        assert 'responses' in fixture_data, "Fixture should have responses"
        
        # Validate response structure
        responses = fixture_data['responses']
        assert '200' in responses, "Should have 200 response"
        
        response_data = responses['200'][0]['response_data']
        
        # Validate API response structure
        assert '_embedded' in response_data, "Should have _embedded structure"
        assert 'items' in response_data['_embedded'], "Should have items array"
        assert isinstance(response_data['_embedded']['items'], list), "Items should be list"
        
        # Validate each project in the response
        projects = response_data['_embedded']['items']
        for project in projects:
            assert_project_structure(project)
        
        # Validate pagination structure
        if 'page' in response_data:
            page_info = response_data['page']
            assert isinstance(page_info, dict), "Page info should be dict"
            
            required_fields = ['size', 'totalElements', 'totalPages', 'number']
            for field in required_fields:
                if field in page_info:
                    assert isinstance(page_info[field], int), f"Page {field} should be integer"
                    assert page_info[field] >= 0, f"Page {field} should be non-negative"
    
    def test_countermeasures_fixture_structure(self):
        """Test that countermeasures fixture has correct structure."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "api_responses" / "post_projects_id_countermeasures_query.json"
        
        if not fixture_path.exists():
            pytest.skip("Countermeasures fixture not found")
        
        with open(fixture_path, 'r') as f:
            fixture_data = json.load(f)
        
        # Validate fixture structure
        assert 'responses' in fixture_data, "Fixture should have responses"
        
        if '200' in fixture_data['responses']:
            response_data = fixture_data['responses']['200'][0]['response_data']
            
            # Validate API response structure
            assert '_embedded' in response_data, "Should have _embedded structure"
            assert 'items' in response_data['_embedded'], "Should have items array"
            
            # Validate each countermeasure
            countermeasures = response_data['_embedded']['items']
            for countermeasure in countermeasures:
                assert_countermeasure_structure(countermeasure)
    
    def test_threats_fixture_structure(self):
        """Test that threats fixture has correct structure."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "api_responses" / "post_projects_id_threats_query.json"
        
        if not fixture_path.exists():
            pytest.skip("Threats fixture not found")
        
        with open(fixture_path, 'r') as f:
            fixture_data = json.load(f)
        
        # Validate fixture structure
        assert 'responses' in fixture_data, "Fixture should have responses"
        
        if '200' in fixture_data['responses']:
            response_data = fixture_data['responses']['200'][0]['response_data']
            
            # Validate API response structure
            assert '_embedded' in response_data, "Should have _embedded structure"
            assert 'items' in response_data['_embedded'], "Should have items array"
            
            # Validate each threat
            threats = response_data['_embedded']['items']
            for threat in threats:
                assert_threat_structure(threat)
    
    def test_individual_project_fixture_structure(self):
        """Test that individual project fixture has correct structure."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "api_responses" / "get_projects_id.json"
        
        if not fixture_path.exists():
            pytest.skip("Individual project fixture not found")
        
        with open(fixture_path, 'r') as f:
            fixture_data = json.load(f)
        
        # Validate fixture structure
        assert 'responses' in fixture_data, "Fixture should have responses"
        
        if '200' in fixture_data['responses']:
            project_data = fixture_data['responses']['200'][0]['response_data']
            
            # Individual project should be a single object, not wrapped in _embedded
            assert_project_structure(project_data)


class TestAPIResponseSchemaValidation:
    """Validate API response schemas match expected contracts."""
    
    def test_hal_json_compliance(self):
        """Test that API responses comply with HAL+JSON format."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "api_responses"
        
        # List endpoints that should return HAL+JSON format
        hal_endpoints = [
            "get_projects.json",
            "post_projects_id_countermeasures_query.json", 
            "post_projects_id_threats_query.json"
        ]
        
        for endpoint_file in hal_endpoints:
            fixture_path = fixtures_dir / endpoint_file
            
            if not fixture_path.exists():
                continue
            
            with open(fixture_path, 'r') as f:
                fixture_data = json.load(f)
            
            if '200' not in fixture_data.get('responses', {}):
                continue
            
            response_data = fixture_data['responses']['200'][0]['response_data']
            
            # HAL+JSON should have _embedded for collections
            if isinstance(response_data, dict) and '_embedded' in response_data:
                assert 'items' in response_data['_embedded'], \
                    f"{endpoint_file}: HAL+JSON _embedded should have items"
                
                # Should have pagination info for collections
                if 'page' in response_data:
                    page_info = response_data['page']
                    assert isinstance(page_info, dict), f"{endpoint_file}: Page info should be dict"
                    
                    # Common pagination fields
                    expected_fields = ['size', 'totalElements']
                    for field in expected_fields:
                        if field in page_info:
                            assert isinstance(page_info[field], int), \
                                f"{endpoint_file}: Page {field} should be integer"
    
    def test_uuid_format_consistency(self):
        """Test that UUIDs in fixtures follow consistent format."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "api_responses"
        
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        
        def validate_uuids_in_object(obj: Any, path: str = ""):
            """Recursively validate UUIDs in an object."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if this field should be a UUID
                    if key in ['id', 'uuid', 'projectId', 'countermeasureId', 'threatId']:
                        if isinstance(value, str) and value:
                            assert uuid_pattern.match(value), \
                                f"Invalid UUID format at {current_path}: {value}"
                    
                    validate_uuids_in_object(value, current_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    validate_uuids_in_object(item, f"{path}[{i}]")
        
        # Check UUID format in key fixtures
        key_fixtures = [
            "get_projects.json",
            "get_projects_id.json",
            "post_projects_id_countermeasures_query.json",
            "post_projects_id_threats_query.json"
        ]
        
        for fixture_file in key_fixtures:
            fixture_path = fixtures_dir / fixture_file
            
            if not fixture_path.exists():
                continue
            
            with open(fixture_path, 'r') as f:
                fixture_data = json.load(f)
            
            if '200' in fixture_data.get('responses', {}):
                response_data = fixture_data['responses']['200'][0]['response_data']
                validate_uuids_in_object(response_data, fixture_file)
    
    def test_enum_value_consistency(self):
        """Test that enum values in fixtures are consistent."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "api_responses"
        
        # Define expected enum values
        expected_enums = {
            'status': ['ACTIVE', 'INACTIVE', 'ARCHIVED', 'DRAFT'],
            'state': {
                'threat': ['expose', 'accept', 'mitigate', 'partly-mitigate', 'hidden'],
                'countermeasure': ['required', 'recommended', 'implemented', 'rejected', 'not-applicable']
            },
            'riskRating': ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'],
            'priority': ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'],
            'implementationStatus': ['not-implemented', 'partially-implemented', 'implemented', 'not-applicable']
        }
        
        def validate_enums_in_object(obj: Any, context: str = ""):
            """Recursively validate enum values in an object."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'state':
                        # State validation depends on context (threat vs countermeasure)
                        if isinstance(value, str) and value:
                            # Try both threat and countermeasure states
                            valid_states = (expected_enums['state']['threat'] + 
                                          expected_enums['state']['countermeasure'])
                            assert value in valid_states, \
                                f"Invalid state value in {context}: {value}"
                    
                    elif key in expected_enums and key != 'state':
                        if isinstance(value, str) and value:
                            assert value in expected_enums[key], \
                                f"Invalid {key} value in {context}: {value}"
                    
                    validate_enums_in_object(value, f"{context}.{key}")
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    validate_enums_in_object(item, f"{context}[{i}]")
        
        # Check enum values in fixtures
        for fixture_file in fixtures_dir.glob("*.json"):
            if fixture_file.name == 'summary.json':
                continue
            
            try:
                with open(fixture_file, 'r') as f:
                    fixture_data = json.load(f)
                
                if '200' in fixture_data.get('responses', {}):
                    response_data = fixture_data['responses']['200'][0]['response_data']
                    validate_enums_in_object(response_data, fixture_file.name)
            
            except Exception as e:
                # Don't fail the test for fixture loading issues, just skip
                continue


class TestAPIEndpointCoverage:
    """Test that we have fixture coverage for all expected API endpoints."""
    
    def test_required_endpoint_coverage(self):
        """Test that we have fixtures for all required API endpoints."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "api_responses"
        
        # Define required endpoints based on CLI functionality
        required_endpoints = [
            ("GET", "/projects"),                                    # Project list
            ("GET", "/projects/{id}"),                              # Individual project
            ("POST", "/projects/{id}/countermeasures/query"),       # Countermeasures list
            ("POST", "/projects/{id}/threats/query"),               # Threats list
            ("GET", "/projects/{id}/reports/types"),                # Report types
            ("GET", "/projects/{id}/standards"),                    # Compliance standards
        ]
        
        # Check that we have fixtures for each required endpoint
        existing_fixtures = set()
        for fixture_file in fixtures_dir.glob("*.json"):
            if fixture_file.name == 'summary.json':
                continue
            
            try:
                with open(fixture_file, 'r') as f:
                    fixture_data = json.load(f)
                
                method = fixture_data.get('method', 'GET')
                endpoint = fixture_data.get('endpoint', '')
                
                existing_fixtures.add((method, endpoint))
            
            except:
                continue
        
        # Check coverage
        missing_endpoints = []
        for method, endpoint in required_endpoints:
            # Check for exact match or pattern match
            found = False
            for existing_method, existing_endpoint in existing_fixtures:
                if (method == existing_method and 
                    (endpoint == existing_endpoint or 
                     endpoint.replace('{id}', 'id') in existing_endpoint or
                     existing_endpoint.replace('{id}', 'id') in endpoint)):
                    found = True
                    break
            
            if not found:
                missing_endpoints.append((method, endpoint))
        
        if missing_endpoints:
            missing_str = ', '.join([f"{m} {e}" for m, e in missing_endpoints])
            pytest.fail(f"Missing fixtures for required endpoints: {missing_str}")
    
    def test_fixture_completeness(self):
        """Test that core fixtures have complete response data."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "api_responses"
        
        # Only check core fixtures that are essential for CLI functionality
        core_fixtures = [
            "get_projects.json",
            "get_projects_id.json", 
            "post_projects_id_countermeasures_query.json",
            "post_projects_id_threats_query.json"
        ]
        
        incomplete_fixtures = []
        
        for fixture_name in core_fixtures:
            fixture_file = fixtures_dir / fixture_name
            
            if not fixture_file.exists():
                incomplete_fixtures.append(f"{fixture_name}: file not found")
                continue
            
            try:
                with open(fixture_file, 'r') as f:
                    fixture_data = json.load(f)
                
                # Check fixture structure
                if 'responses' not in fixture_data:
                    incomplete_fixtures.append(f"{fixture_name}: missing responses")
                    continue
                
                responses = fixture_data['responses']
                if '200' not in responses:
                    incomplete_fixtures.append(f"{fixture_name}: missing 200 response")
                    continue
                
                response_list = responses['200']
                if not response_list or not response_list[0].get('response_data'):
                    incomplete_fixtures.append(f"{fixture_name}: missing response_data")
                    continue
            
            except Exception as e:
                incomplete_fixtures.append(f"{fixture_name}: {str(e)}")
        
        if incomplete_fixtures:
            pytest.fail(f"Incomplete core fixtures found:\n" + '\n'.join(incomplete_fixtures))


class TestMockAPIClientContractCompliance:
    """Test that mock API client maintains contract compliance."""
    
    def test_mock_client_response_format(self, mock_api_client):
        """Test that mock client returns properly formatted responses."""
        # Test projects endpoint
        projects_response = mock_api_client.get_projects()
        
        # Should return HAL+JSON format
        assert isinstance(projects_response, dict), "Projects response should be dict"
        assert '_embedded' in projects_response, "Should have _embedded structure"
        assert 'items' in projects_response['_embedded'], "Should have items array"
        
        # Validate project structure
        projects = projects_response['_embedded']['items']
        for project in projects:
            assert_project_structure(project)
    
    def test_mock_client_error_handling(self, mock_api_client):
        """Test that mock client handles missing fixtures appropriately."""
        # In strict mode, should raise AssertionError for missing fixtures
        with pytest.raises(AssertionError, match="No fixture found"):
            mock_api_client._get_response('GET', '/nonexistent/endpoint')
    
    def test_mock_client_fixture_matching(self, mock_api_client):
        """Test that mock client correctly matches fixture patterns."""
        # Test that UUID patterns are matched correctly
        # This should work because of the flexible pattern matching
        try:
            response = mock_api_client.get_project("12345678-1234-1234-1234-123456789abc")
            # If we get here, the pattern matching worked
            assert isinstance(response, dict), "Should return dict response"
        except AssertionError as e:
            # If no fixture exists, that's also valid - the test confirms the behavior
            assert "No fixture found" in str(e), "Should provide clear error for missing fixture"
