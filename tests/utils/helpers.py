"""
Consolidated test helper utilities for IriusRisk CLI testing.

This module provides utility functions and classes to make testing easier
and more consistent across the test suite.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200, text: str = None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text or json.dumps(json_data)
        self.headers = {'Content-Type': 'application/json'}
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            from requests import HTTPError
            raise HTTPError(f"HTTP {self.status_code}")


class TemporaryProject:
    """Context manager for creating temporary project directories."""
    
    def __init__(self, project_name: str = "test-project", project_id: str = None):
        self.project_name = project_name
        self.project_id = project_id or "test-project-123"
        self.temp_dir = None
        self.project_dir = None
    
    def __enter__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_dir = self.temp_dir / self.project_name
        self.project_dir.mkdir()
        
        # Create .iriusrisk directory structure
        iriusrisk_dir = self.project_dir / ".iriusrisk"
        iriusrisk_dir.mkdir()
        
        # Create project.json
        project_config = {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "reference_id": self.project_name.lower().replace(" ", "-")
        }
        
        with open(iriusrisk_dir / "project.json", "w") as f:
            json.dump(project_config, f, indent=2)
        
        return self.project_dir
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


def create_mock_otm_file(content: str = None) -> str:
    """Create a temporary OTM file for testing."""
    if content is None:
        content = """
otmVersion: 0.1.0
project:
  name: Test Project
  id: test-project-123
  description: A test project for unit testing

representations:
- name: Test Architecture
  id: test-arch
  type: code

trustZones:
- id: internet
  name: Internet
  risk:
    trustRating: 1

components:
- id: web-app
  name: Web Application
  type: web-application
  parent:
    trustZone: internet

dataflows:
- id: user-request
  name: User Request
  source: user
  destination: web-app
"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False)
    temp_file.write(content.strip())
    temp_file.close()
    return temp_file.name


def mock_api_responses(responses: Dict[str, Any]):
    """Decorator to mock specific API responses for a test."""
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            with patch('requests.Session.request') as mock_request:
                def side_effect(method, url, **request_kwargs):
                    # Find matching response based on method and URL
                    for key, response_data in responses.items():
                        if key in url and method.upper() in key.upper():
                            return MockResponse(response_data)
                    
                    # Default response if no match
                    return MockResponse({"error": "No mock response defined"}, 404)
                
                mock_request.side_effect = side_effect
                return test_func(*args, **kwargs)
        return wrapper
    return decorator


def capture_cli_output(cli_runner, command_args: List[str], input_data: str = None):
    """Helper to capture CLI command output with proper error handling."""
    from iriusrisk_cli.main import cli
    
    result = cli_runner.invoke(cli, command_args, input=input_data, catch_exceptions=False)
    
    return {
        'exit_code': result.exit_code,
        'output': result.output,
        'exception': result.exception
    }


def load_fixture_response(endpoint_pattern: str, method: str = "GET", status_code: str = "200") -> Optional[Dict[str, Any]]:
    """Load a specific response from fixture files."""
    # Convert endpoint pattern to filename
    filename = endpoint_pattern.replace('/', '_').replace('{id}', 'id').strip('_')
    if not filename:
        filename = 'root'
    filename = f"{method.lower()}_{filename}.json"
    
    fixture_path = Path(__file__).parent.parent / "fixtures" / "api_responses" / filename
    
    if not fixture_path.exists():
        return None
    
    with open(fixture_path, 'r') as f:
        fixture_data = json.load(f)
    
    responses = fixture_data.get('responses', {})
    if status_code in responses and responses[status_code]:
        return responses[status_code][0]['response_data']
    
    return None


class CLITestCase:
    """Base class for CLI command test cases."""
    
    def __init__(self, cli_runner, mock_api_client):
        self.cli_runner = cli_runner
        self.mock_api_client = mock_api_client
    
    def run_command(self, command_args: List[str], input_data: str = None, expect_success: bool = True):
        """Run a CLI command and return the result."""
        from iriusrisk_cli.main import cli
        
        result = self.cli_runner.invoke(cli, command_args, input=input_data)
        
        if expect_success:
            assert result.exit_code == 0, f"Command failed: {result.output}"
        
        return result
    
    def assert_output_contains(self, result, expected_text: str):
        """Assert that command output contains expected text."""
        assert expected_text in result.output, f"Expected '{expected_text}' in output: {result.output}"
    
    def assert_output_json(self, result, expected_keys: List[str] = None):
        """Assert that command output is valid JSON with expected keys."""
        try:
            data = json.loads(result.output)
            if expected_keys:
                from .assertions import assert_json_structure
                assert_json_structure(data, expected_keys)
            return data
        except json.JSONDecodeError as e:
            raise AssertionError(f"Output is not valid JSON: {e}\nOutput: {result.output}")


class ServiceTestBase:
    """Base class for service unit tests with common setup patterns."""
    
    def setup_method(self):
        """Common setup for service tests - override in subclasses."""
        pass
    
    def create_mock_repositories(self):
        """Create mock repositories for service testing."""
        from unittest.mock import Mock
        from iriusrisk_cli.repositories.project_repository import ProjectRepository
        from iriusrisk_cli.repositories.threat_repository import ThreatRepository
        from iriusrisk_cli.repositories.countermeasure_repository import CountermeasureRepository
        from iriusrisk_cli.repositories.report_repository import ReportRepository
        from iriusrisk_cli.repositories.version_repository import VersionRepository
        
        return {
            'project': Mock(spec=ProjectRepository),
            'threat': Mock(spec=ThreatRepository),
            'countermeasure': Mock(spec=CountermeasureRepository),
            'report': Mock(spec=ReportRepository),
            'version': Mock(spec=VersionRepository)
        }


def create_sample_data():
    """Create sample test data for various entities."""
    return {
        'project': {
            "id": "12345678-1234-1234-1234-123456789abc",
            "name": "Test Web Application",
            "referenceId": "test-project",
            "description": "A test project for unit testing",
            "tags": "test,web-app",
            "status": "ACTIVE"
        },
        'threat': {
            "id": "threat-uuid-1",
            "name": "SQL Injection",
            "description": "SQL injection vulnerability in database queries",
            "state": "expose",
            "riskRating": "HIGH",
            "availability": 75,
            "confidentiality": 75,
            "integrity": 75
        },
        'countermeasure': {
            "id": "countermeasure-uuid-1",
            "name": "Input Validation",
            "description": "Implement proper input validation and sanitization",
            "state": "required",
            "priority": "HIGH",
            "implementationStatus": "not-implemented"
        }
    }


def create_paginated_response(items: List[Dict[str, Any]], page: int = 0, size: int = 20, total: int = None) -> Dict[str, Any]:
    """Create a paginated API response structure."""
    if total is None:
        total = len(items)
    
    total_pages = (total + size - 1) // size  # Ceiling division
    
    return {
        "_embedded": {
            "items": items
        },
        "page": {
            "size": size,
            "totalElements": total,
            "totalPages": total_pages,
            "number": page
        }
    }
