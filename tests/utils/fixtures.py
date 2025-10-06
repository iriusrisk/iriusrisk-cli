"""
Consolidated test fixtures for IriusRisk CLI testing.

This module provides all common fixtures used across the test suite,
eliminating duplication and providing consistent test data.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Import our mock API client
from tests.mocks.api_client_mock import MockIriusRiskApiClient


@pytest.fixture
def cli_runner():
    """Fixture that provides a Click CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Fixture that provides a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup after test
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def project_dir(temp_dir):
    """Fixture that provides a temporary project directory with .iriusRisk setup."""
    project_path = temp_dir / "test_project"
    project_path.mkdir()
    
    # Create .iriusRisk directory
    iriusrisk_dir = project_path / ".iriusRisk"
    iriusrisk_dir.mkdir()
    
    # Create sample project.json
    project_json = {
        "project_id": "test-project-123",
        "project_name": "Test Project",
        "reference_id": "test-project"
    }
    
    with open(iriusrisk_dir / "project.json", "w") as f:
        json.dump(project_json, f, indent=2)
    
    return project_path


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture that sets up mock environment variables."""
    monkeypatch.setenv("IRIUS_HOSTNAME", "https://test.iriusrisk.com")
    monkeypatch.setenv("IRIUS_API_TOKEN", "test-api-token-12345")
    # Disable response logging during tests
    monkeypatch.setenv("IRIUS_LOG_RESPONSES", "false")


@pytest.fixture
def mock_config():
    """Fixture that provides mock configuration values."""
    mock_config_obj = MagicMock()
    mock_config_obj.api_base_url = 'https://test.iriusrisk.com/api/v2'
    mock_config_obj.api_v1_base_url = 'https://test.iriusrisk.com/api/v1'
    mock_config_obj.api_token = 'test-api-token-12345'
    
    # Patch Config class constructor to return our mock in all modules that import it
    with patch('iriusrisk_cli.config.Config', return_value=mock_config_obj):
        with patch('iriusrisk_cli.api_client.Config', return_value=mock_config_obj):
            with patch('iriusrisk_cli.api.base_client.Config', return_value=mock_config_obj):
                with patch('iriusrisk_cli.api.project_client.Config', return_value=mock_config_obj):
                    yield mock_config_obj


@pytest.fixture
def mock_api_client():
    """Fixture that provides a mock API client."""
    return MockIriusRiskApiClient(strict_mode=True)


@pytest.fixture
def lenient_mock_api_client():
    """Fixture that provides a mock API client that returns empty responses for missing fixtures."""
    return MockIriusRiskApiClient(strict_mode=False)


@pytest.fixture
def sample_project_data():
    """Fixture that provides sample project data for testing."""
    return {
        "id": "12345678-1234-1234-1234-123456789abc",
        "name": "Test Web Application",
        "referenceId": "test-project",
        "description": "A test project for unit testing",
        "tags": "test,web-app",
        "status": "ACTIVE"
    }


@pytest.fixture
def sample_threat_data():
    """Fixture that provides sample threat data for testing."""
    return {
        "id": "threat-uuid-1",
        "name": "SQL Injection",
        "description": "SQL injection vulnerability in database queries",
        "state": "expose",
        "riskRating": "HIGH",
        "availability": 75,
        "confidentiality": 75,
        "integrity": 75
    }


@pytest.fixture
def sample_countermeasure_data():
    """Fixture that provides sample countermeasure data for testing."""
    return {
        "id": "countermeasure-uuid-1",
        "name": "Input Validation",
        "description": "Implement proper input validation and sanitization",
        "state": "required",
        "priority": "HIGH",
        "implementationStatus": "not-implemented"
    }


@pytest.fixture
def mock_file_operations():
    """Fixture that mocks file operations for testing."""
    mock_open = MagicMock()
    mock_exists = MagicMock(return_value=True)
    mock_mkdir = MagicMock()
    
    with patch('builtins.open', mock_open):
        with patch('pathlib.Path.exists', mock_exists):
            with patch('pathlib.Path.mkdir', mock_mkdir):
                yield {
                    'open': mock_open,
                    'exists': mock_exists,
                    'mkdir': mock_mkdir
                }


# Service-specific fixtures for unit testing
@pytest.fixture
def mock_project_repository():
    """Fixture that provides a mock ProjectRepository."""
    from iriusrisk_cli.repositories.project_repository import ProjectRepository
    from unittest.mock import Mock
    return Mock(spec=ProjectRepository)


@pytest.fixture
def mock_threat_repository():
    """Fixture that provides a mock ThreatRepository."""
    from iriusrisk_cli.repositories.threat_repository import ThreatRepository
    from unittest.mock import Mock
    return Mock(spec=ThreatRepository)


@pytest.fixture
def mock_countermeasure_repository():
    """Fixture that provides a mock CountermeasureRepository."""
    from iriusrisk_cli.repositories.countermeasure_repository import CountermeasureRepository
    from unittest.mock import Mock
    return Mock(spec=CountermeasureRepository)


@pytest.fixture
def mock_report_repository():
    """Fixture that provides a mock ReportRepository."""
    from iriusrisk_cli.repositories.report_repository import ReportRepository
    from unittest.mock import Mock
    return Mock(spec=ReportRepository)


@pytest.fixture
def project_service(mock_project_repository, mock_threat_repository, mock_countermeasure_repository):
    """Fixture that provides a ProjectService with mock repositories."""
    from iriusrisk_cli.services.project_service import ProjectService
    return ProjectService(
        project_repository=mock_project_repository,
        threat_repository=mock_threat_repository,
        countermeasure_repository=mock_countermeasure_repository
    )


@pytest.fixture
def threat_service(mock_threat_repository):
    """Fixture that provides a ThreatService with mock repository."""
    from iriusrisk_cli.services.threat_service import ThreatService
    return ThreatService(threat_repository=mock_threat_repository)


@pytest.fixture
def countermeasure_service(mock_countermeasure_repository):
    """Fixture that provides a CountermeasureService with mock repository."""
    from iriusrisk_cli.services.countermeasure_service import CountermeasureService
    return CountermeasureService(countermeasure_repository=mock_countermeasure_repository)


@pytest.fixture
def report_service(mock_report_repository):
    """Fixture that provides a ReportService with mock repository."""
    from iriusrisk_cli.services.report_service import ReportService
    return ReportService(report_repository=mock_report_repository)


# Test data helpers
def get_fixture_data(fixture_name: str):
    """Helper function to load fixture data from JSON files."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "api_responses" / f"{fixture_name}.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return None
