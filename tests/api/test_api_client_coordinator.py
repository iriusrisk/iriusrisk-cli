"""Unit tests for IriusRiskApiClient coordinator functionality."""

import pytest
from unittest.mock import Mock, patch
import requests

from iriusrisk_cli.api_client import IriusRiskApiClient


class TestIriusRiskApiClientCoordinator:
    """Test API client coordinator pattern functionality."""
    
    def test_init_creates_specialized_clients(self, mock_config):
        """Test that initialization creates all specialized clients."""
        client = IriusRiskApiClient()
        
        # Verify specialized clients are created
        assert hasattr(client, 'project_client')
        assert hasattr(client, 'threat_client') 
        assert hasattr(client, 'countermeasure_client')
        assert hasattr(client, 'report_client')
        
        # Verify backward compatibility properties
        assert client.base_url == mock_config.api_base_url
        assert client.v1_base_url == mock_config.api_v1_base_url
        assert isinstance(client.session, requests.Session)
    
    def test_project_methods_delegation(self, mock_config):
        """Test that project methods are properly delegated."""
        client = IriusRiskApiClient()
        
        # Mock the project client method
        client.project_client.get_projects = Mock(return_value={'test': 'data'})
        
        # Call the coordinator method
        result = client.get_projects(page=1, size=10)
        
        # Verify delegation occurred
        client.project_client.get_projects.assert_called_once_with(1, 10, False, None)
        assert result == {'test': 'data'}
    
    def test_threat_methods_delegation(self, mock_config):
        """Test that threat methods are properly delegated."""
        client = IriusRiskApiClient()
        
        # Mock the threat client method
        client.threat_client.get_threats = Mock(return_value={'threats': []})
        
        # Call the coordinator method
        result = client.get_threats('project-123', page=0, size=20)
        
        # Verify delegation occurred
        client.threat_client.get_threats.assert_called_once_with('project-123', 0, 20, None)
        assert result == {'threats': []}
    
    def test_countermeasure_methods_delegation(self, mock_config):
        """Test that countermeasure methods are properly delegated."""
        client = IriusRiskApiClient()
        
        # Mock the countermeasure client method
        client.countermeasure_client.get_countermeasures = Mock(return_value={'countermeasures': []})
        
        # Call the coordinator method
        result = client.get_countermeasures('project-123', page=0, size=20)
        
        # Verify delegation occurred
        client.countermeasure_client.get_countermeasures.assert_called_once_with('project-123', 0, 20, None)
        assert result == {'countermeasures': []}
    
    def test_report_methods_delegation(self, mock_config):
        """Test that report methods are properly delegated."""
        client = IriusRiskApiClient()
        
        # Mock the report client method
        client.report_client.get_report_types = Mock(return_value=[{'type': 'pdf'}])
        
        # Call the coordinator method
        result = client.get_report_types('project-123')
        
        # Verify delegation occurred
        client.report_client.get_report_types.assert_called_once_with('project-123')
        assert result == [{'type': 'pdf'}]
    
    def test_otm_methods_delegation(self, mock_config):
        """Test that OTM methods are properly delegated."""
        client = IriusRiskApiClient()
        
        # Mock the project client OTM method
        client.project_client.import_otm_file = Mock(return_value={'id': 'project-123', 'action': 'created'})
        
        # Call the coordinator method
        result = client.import_otm_file('/path/to/file.otm', auto_update=True)
        
        # Verify delegation occurred
        client.project_client.import_otm_file.assert_called_once_with('/path/to/file.otm', True)
        assert result == {'id': 'project-123', 'action': 'created'}
    
    def test_state_update_methods_delegation(self, mock_config):
        """Test that state update methods are properly delegated."""
        client = IriusRiskApiClient()
        
        # Mock the threat client state update method
        client.threat_client.update_threat_state = Mock(return_value={'status': 'updated'})
        
        # Call the coordinator method
        result = client.update_threat_state('threat-123', 'mitigate', 'Test reason')
        
        # Verify delegation occurred
        client.threat_client.update_threat_state.assert_called_once_with('threat-123', 'mitigate', 'Test reason', None)
        assert result == {'status': 'updated'}
    
    def test_all_public_methods_exist(self, mock_config):
        """Test that all expected public methods exist on the coordinator."""
        client = IriusRiskApiClient()
        
        # Project methods
        assert hasattr(client, 'get_projects')
        assert hasattr(client, 'get_project')
        assert hasattr(client, 'get_project_artifacts')
        assert hasattr(client, 'get_project_artifact_content')
        assert hasattr(client, 'get_components')
        assert hasattr(client, 'get_trust_zones')
        assert hasattr(client, 'get_component')
        
        # OTM methods
        assert hasattr(client, 'import_otm_file')
        assert hasattr(client, 'import_otm_content')
        assert hasattr(client, 'update_project_with_otm_file')
        assert hasattr(client, 'update_project_with_otm_content')
        assert hasattr(client, 'export_project_as_otm')
        
        # Threat methods
        assert hasattr(client, 'get_threats')
        assert hasattr(client, 'get_threat')
        assert hasattr(client, 'update_threat_state')
        assert hasattr(client, 'create_threat_comment')
        
        # Countermeasure methods
        assert hasattr(client, 'get_countermeasures')
        assert hasattr(client, 'get_countermeasure')
        assert hasattr(client, 'update_countermeasure_state')
        assert hasattr(client, 'create_countermeasure_comment')
        assert hasattr(client, 'create_countermeasure_issue')
        
        # Report methods
        assert hasattr(client, 'get_report_types')
        assert hasattr(client, 'generate_report')
        assert hasattr(client, 'get_async_operation_status')
        assert hasattr(client, 'get_project_reports')
        assert hasattr(client, 'get_project_standards')
        assert hasattr(client, 'download_report_content')
        assert hasattr(client, 'download_report_content_from_url')
        
        # Issue tracker methods
        assert hasattr(client, 'get_issue_tracker_profiles')
        assert hasattr(client, 'get_project_issue_trackers')
