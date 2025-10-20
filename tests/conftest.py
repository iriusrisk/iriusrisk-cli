"""
Pytest configuration and shared fixtures for IriusRisk CLI tests.

This module provides the main test configuration and the complex dependency
injection patching required for CLI integration tests.
"""

import pytest
from unittest.mock import patch, MagicMock

# Import consolidated fixtures
import sys
from pathlib import Path

# Add the project root to Python path to ensure imports work
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tests.utils.fixtures import *  # noqa: F403,F401
from tests.mocks.api_client_mock import MockIriusRiskApiClient


@pytest.fixture
def mock_api_client(patch_api_client):
    """Fixture that provides the same mock API client used in patch_api_client."""
    return patch_api_client


@pytest.fixture(autouse=True)
def patch_api_client(monkeypatch):
    """Auto-use fixture that patches the dependency injection system with our mock."""
    # Disable response logging during all tests
    monkeypatch.setenv("IRIUS_LOG_RESPONSES", "false")
    
    # Create a single mock instance that will be used throughout the test
    mock_client = MockIriusRiskApiClient(strict_mode=True)
    mock_client.base_url = 'https://test.iriusrisk.com/api/v2'
    mock_client.v1_base_url = 'https://test.iriusrisk.com/api/v1'
    
    # Import the classes we need
    from iriusrisk_cli.config import Config
    from iriusrisk_cli.container import Container
    from iriusrisk_cli.cli_context import CliContext
    from iriusrisk_cli.service_factory import ServiceFactory
    from iriusrisk_cli.repositories.project_repository import ProjectRepository
    from iriusrisk_cli.repositories.threat_repository import ThreatRepository
    from iriusrisk_cli.repositories.countermeasure_repository import CountermeasureRepository
    from iriusrisk_cli.repositories.report_repository import ReportRepository
    from iriusrisk_cli.repositories.version_repository import VersionRepository
    from iriusrisk_cli.services.project_service import ProjectService
    from iriusrisk_cli.services.threat_service import ThreatService
    from iriusrisk_cli.services.countermeasure_service import CountermeasureService
    from iriusrisk_cli.services.report_service import ReportService
    from iriusrisk_cli.services.version_service import VersionService
    
    # Create mock config
    mock_config = Config()
    
    # Create repository instances with our mock client
    project_repository = ProjectRepository(api_client=mock_client)
    threat_repository = ThreatRepository(api_client=mock_client)
    countermeasure_repository = CountermeasureRepository(api_client=mock_client)
    report_repository = ReportRepository(api_client=mock_client)
    version_repository = VersionRepository(api_client=mock_client.version_client)
    
    # Create real service instances with our mock repositories
    project_service = ProjectService(
        project_repository=project_repository,
        threat_repository=threat_repository,
        countermeasure_repository=countermeasure_repository
    )
    threat_service = ThreatService(threat_repository=threat_repository)
    countermeasure_service = CountermeasureService(countermeasure_repository=countermeasure_repository)
    report_service = ReportService(report_repository=report_repository)
    version_service = VersionService(
        version_repository=version_repository,
        report_repository=report_repository
    )
    
    # Create a mock service factory
    mock_service_factory = MagicMock(spec=ServiceFactory)
    mock_service_factory.get_project_service.return_value = project_service
    mock_service_factory.get_threat_service.return_value = threat_service
    mock_service_factory.get_countermeasure_service.return_value = countermeasure_service
    mock_service_factory.get_report_service.return_value = report_service
    mock_service_factory.get_version_service.return_value = version_service
    
    # Create a mock CLI context
    mock_cli_context = MagicMock(spec=CliContext)
    mock_cli_context.get_config.return_value = mock_config
    mock_cli_context.get_service_factory.return_value = mock_service_factory
    
    # Create a mock container
    from iriusrisk_cli.services.version_service import VersionService
    
    mock_container = MagicMock(spec=Container)
    mock_container.get.side_effect = lambda service_type: {
        Config: mock_config,
        ServiceFactory: mock_service_factory,
        VersionService: version_service,
        ProjectService: project_service,
        ThreatService: threat_service,
        CountermeasureService: countermeasure_service,
        ReportService: report_service
    }.get(service_type, MagicMock())
    
    # Patch the container system and CLI context more comprehensively
    with patch('iriusrisk_cli.container.get_container', return_value=mock_container):
        with patch('iriusrisk_cli.cli_context.CliContext', return_value=mock_cli_context):
            with patch('iriusrisk_cli.cli_context.setup_cli_context', return_value=mock_cli_context):
                # Patch the pass_cli_context decorator to inject our mock context
                def mock_pass_cli_context(f):
                    def wrapper(*args, **kwargs):
                        return f(mock_cli_context, *args, **kwargs)
                    return wrapper
                
                with patch('iriusrisk_cli.cli_context.pass_cli_context', mock_pass_cli_context):
                    # No longer need to patch api_client global as it's lazy-loaded
                    yield mock_client


# All fixtures and helpers are now imported from tests.utils.fixtures
