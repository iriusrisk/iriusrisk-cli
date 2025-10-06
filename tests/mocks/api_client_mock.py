"""
Mock API client for testing IriusRisk CLI.

This module provides a mock implementation of the IriusRisk API client
that returns pre-recorded responses from fixture files.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock


class MockIriusRiskApiClient:
    """Mock API client that returns fixture data instead of making real API calls."""
    
    def __init__(self, fixtures_dir: Optional[Path] = None, strict_mode: bool = True):
        """Initialize mock client with fixture directory.
        
        Args:
            fixtures_dir: Directory containing fixture files
            strict_mode: If True, fail tests when fixtures are missing. If False, return empty responses.
        """
        if fixtures_dir is None:
            fixtures_dir = Path(__file__).parent.parent / 'fixtures' / 'api_responses'
        self.fixtures_dir = fixtures_dir
        self.strict_mode = strict_mode
        self.call_log = []  # Track API calls for verification
        
        # Add attributes needed by the coordinator pattern
        self.base_url = 'https://test.iriusrisk.com/api/v2'
        self.v1_base_url = 'https://test.iriusrisk.com/api/v1'
        self.session = Mock()
        
        self._load_fixtures()
    
    def _load_fixtures(self):
        """Load all fixture files."""
        self.fixtures = {}
        
        if not self.fixtures_dir.exists():
            return
        
        for fixture_file in self.fixtures_dir.glob('*.json'):
            if fixture_file.name == 'summary.json':
                continue
                
            try:
                with open(fixture_file, 'r', encoding='utf-8') as f:
                    fixture_data = json.load(f)
                    endpoint = fixture_data.get('endpoint', '')
                    method = fixture_data.get('method', 'GET')
                    key = f"{method}_{endpoint}"
                    self.fixtures[key] = fixture_data
            except Exception as e:
                print(f"Error loading fixture {fixture_file}: {e}")
    
    def _find_matching_fixture(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        """Find a fixture that matches the given method and path."""
        # Try exact match first
        key = f"{method}_{path}"
        if key in self.fixtures:
            return self.fixtures[key]
        
        # Try pattern matching (replace UUIDs with {id})
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        pattern_path = re.sub(uuid_pattern, '{id}', path, flags=re.IGNORECASE)
        pattern_key = f"{method}_{pattern_path}"
        
        if pattern_key in self.fixtures:
            return self.fixtures[pattern_key]
        
        # Try more flexible matching - replace any path segment that looks like an ID
        # but preserve the structure (projects, threats, countermeasures, etc.)
        flexible_path = path
        path_parts = flexible_path.split('/')
        for i, part in enumerate(path_parts):
            # Replace parts that look like IDs but keep known keywords
            if part and part not in ['projects', 'threats', 'countermeasures', 'reports', 'query', 'generate', 'types', 'standards']:
                # If it's alphanumeric and looks like an ID, replace it
                if re.match(r'^[a-zA-Z0-9\-_]+$', part):
                    path_parts[i] = '{id}'
        
        flexible_path = '/'.join(path_parts)
        flexible_key = f"{method}_{flexible_path}"
        
        if flexible_key in self.fixtures:
            return self.fixtures[flexible_key]
        
        return None
    
    def _get_response(self, method: str, path: str, status_code: str = '200') -> Any:
        """Get a response from fixtures and log the call."""
        # Log the API call for verification
        self.call_log.append({
            'method': method,
            'path': path,
            'status_code': status_code
        })
        
        fixture = self._find_matching_fixture(method, path)
        
        if not fixture:
            if self.strict_mode:
                # CRITICAL: Fail tests when fixtures are missing to prevent false security
                # This ensures tests fail when API endpoints change or fixtures are incomplete
                raise AssertionError(
                    f"No fixture found for {method} {path}. "
                    f"This indicates either:\n"
                    f"1. Missing fixture data for this endpoint\n"
                    f"2. API endpoint has changed\n"
                    f"3. Test is calling an unexpected endpoint\n"
                    f"Available fixtures: {list(self.fixtures.keys())}"
                )
            else:
                # Non-strict mode: return empty responses (for backward compatibility)
                if 'query' in path or method == 'POST':
                    return {
                        "_embedded": {"items": []},
                        "page": {"size": 20, "totalElements": 0, "totalPages": 0, "number": 0}
                    }
                elif '/projects/' in path and path.count('/') >= 3:
                    return {}
                else:
                    return {
                        "_embedded": {"items": []},
                        "page": {"size": 20, "totalElements": 0, "totalPages": 0, "number": 0}
                    }
        
        responses = fixture.get('responses', {})
        if status_code in responses and responses[status_code]:
            # Return the first response for the status code
            return responses[status_code][0]['response_data']
        
        # Fallback to first available response
        for status, response_list in responses.items():
            if response_list:
                return response_list[0]['response_data']
        
        # If no response data found, this is also a fixture problem
        raise AssertionError(
            f"Fixture found for {method} {path} but no valid response data. "
            f"Fixture structure: {fixture}"
        )

    # Mock the main API methods used by the CLI
    def get_projects(self, **kwargs) -> Dict[str, Any]:
        """Mock get_projects method."""
        return self._get_response('GET', '/projects')
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Mock get_project method."""
        return self._get_response('GET', f'/projects/{project_id}')
    
    def get_threats(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """Mock get_threats method."""
        return self._get_response('POST', f'/projects/{project_id}/threats/query')
    
    def get_threat(self, project_id: str, threat_id: str) -> Dict[str, Any]:
        """Mock get_threat method."""
        return self._get_response('GET', f'/projects/threats/{threat_id}')
    
    def get_countermeasures(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """Mock get_countermeasures method."""
        return self._get_response('POST', f'/projects/{project_id}/countermeasures/query')
    
    def get_countermeasure(self, project_id: str, countermeasure_id: str) -> Dict[str, Any]:
        """Mock get_countermeasure method."""
        return self._get_response('GET', f'/projects/countermeasures/{countermeasure_id}')
    
    def get_components(self, **kwargs) -> Dict[str, Any]:
        """Mock get_components method."""
        # Components endpoint not found in fixtures, return empty response
        return {"_embedded": {"items": []}, "page": {"size": 20, "totalElements": 0}}
    
    def get_trust_zones(self, **kwargs) -> Dict[str, Any]:
        """Mock get_trust_zones method."""
        # Trust zones endpoint not found in fixtures, return empty response
        return {"_embedded": {"items": []}, "page": {"size": 20, "totalElements": 0}}
    
    def get_report_types(self, project_id: str) -> Dict[str, Any]:
        """Mock get_report_types method."""
        return self._get_response('GET', f'/projects/{project_id}/reports/types')
    
    def generate_report(self, project_id: str, **kwargs) -> str:
        """Mock generate_report method."""
        response = self._get_response('POST', f'/projects/{project_id}/reports/generate')
        if isinstance(response, dict):
            return response.get('operationId', 'mock-operation-id')
        else:
            # Fallback if response is not a dict
            return 'mock-operation-id'
    
    def get_project_standards(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """Mock get_project_standards method."""
        return self._get_response('GET', f'/projects/{project_id}/standards')
    
    def get_project_reports(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """Mock get_project_reports method."""
        # Return mock reports for CLI tests
        return {
            "_embedded": {
                "items": [
                    {
                        "id": "mock-report-1",
                        "name": "Mock Countermeasure Report",
                        "reportType": "technical-countermeasure-report",
                        "format": "pdf",
                        "created": "2023-01-01T00:00:00Z",
                        "_links": {
                            "download": {
                                "href": "https://mock.example.com/reports/mock-report-1.pdf"
                            }
                        }
                    },
                    {
                        "id": "mock-report-2", 
                        "name": "Mock Threat Report",
                        "reportType": "technical-threat-report",
                        "format": "pdf",
                        "created": "2023-01-01T00:00:00Z",
                        "_links": {
                            "download": {
                                "href": "https://mock.example.com/reports/mock-report-2.pdf"
                            }
                        }
                    }
                ]
            }
        }
    
    # OTM API methods (v1 API)
    def import_otm_file(self, otm_file_path: str, **kwargs) -> Dict[str, Any]:
        """Mock import_otm_file method."""
        return self._get_response('POST', '/products/otm')
    
    def import_otm_content(self, otm_content: str, **kwargs) -> Dict[str, Any]:
        """Mock import_otm_content method."""
        return self._get_response('POST', '/products/otm')
    
    def update_project_with_otm_file(self, project_id: str, otm_file_path: str) -> Dict[str, Any]:
        """Mock update_project_with_otm_file method."""
        return self._get_response('PUT', f'/products/otm/{project_id}')
    
    def update_project_with_otm_content(self, project_id: str, otm_content: str) -> Dict[str, Any]:
        """Mock update_project_with_otm_content method."""
        return self._get_response('PUT', f'/products/otm/{project_id}')
    
    def export_project_as_otm(self, project_id: str) -> str:
        """Mock export_project_as_otm method."""
        response = self._get_response('GET', f'/products/otm/{project_id}')
        # OTM export returns text, not JSON
        return response if isinstance(response, str) else "# Mock OTM content"
    
    # Additional API methods used by CLI commands
    def update_threat_state(self, threat_id: str, state_transition: str, **kwargs) -> Dict[str, Any]:
        """Mock update_threat_state method."""
        return self._get_response('PUT', f'/projects/threats/{threat_id}/state')
    
    def update_countermeasure_state(self, countermeasure_id: str, state_transition: str, **kwargs) -> Dict[str, Any]:
        """Mock update_countermeasure_state method."""
        return self._get_response('PUT', f'/projects/countermeasures/{countermeasure_id}/state')
    
    def create_threat_comment(self, threat_id: str, comment: str) -> Dict[str, Any]:
        """Mock create_threat_comment method."""
        return {"id": "comment-123", "comment": comment, "created": "2023-01-01T00:00:00Z"}
    
    def create_countermeasure_comment(self, countermeasure_id: str, comment: str) -> Dict[str, Any]:
        """Mock create_countermeasure_comment method."""
        return {"id": "comment-456", "comment": comment, "created": "2023-01-01T00:00:00Z"}
    
    def get_async_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Mock get_async_operation_status method."""
        # For CLI tests, always return success to avoid infinite loops
        # Override fixture behavior to prevent test timeouts
        return {
            "id": operation_id,
            "status": "finished-success",
            "summary": {
                "fail": 0,
                "success": 1,
                "pending": 0,
                "interrupted": 0
            }
        }
    
    def download_report_content(self, report_id: str) -> bytes:
        """Mock download_report_content method."""
        return b"Mock report content"
    
    def download_report_content_from_url(self, url: str) -> bytes:
        """Mock download_report_content_from_url method."""
        return b"Mock report content from URL"
    
    def get_issue_tracker_profiles(self, **kwargs) -> Dict[str, Any]:
        """Mock get_issue_tracker_profiles method."""
        return self._get_response('GET', '/issue-tracker-profiles/summary')
    
    def create_countermeasure_issue(self, project_id: str, countermeasure_id: str, **kwargs) -> Dict[str, Any]:
        """Mock create_countermeasure_issue method."""
        return self._get_response('POST', f'/projects/countermeasures/{countermeasure_id}/create-issue')
    
    # Test verification methods
    def get_call_log(self) -> list:
        """Get the log of API calls made during testing."""
        return self.call_log.copy()
    
    def clear_call_log(self):
        """Clear the API call log."""
        self.call_log.clear()
    
    def was_called(self, method: str, path_pattern: str) -> bool:
        """Check if a specific API call was made."""
        for call in self.call_log:
            if call['method'] == method and path_pattern in call['path']:
                return True
        return False
    
    def get_calls_matching(self, method: str = None, path_pattern: str = None) -> list:
        """Get all calls matching the given criteria."""
        matching_calls = []
        for call in self.call_log:
            if method and call['method'] != method:
                continue
            if path_pattern and path_pattern not in call['path']:
                continue
            matching_calls.append(call)
        return matching_calls


def create_mock_api_client() -> MockIriusRiskApiClient:
    """Create and return a mock API client instance."""
    return MockIriusRiskApiClient()
