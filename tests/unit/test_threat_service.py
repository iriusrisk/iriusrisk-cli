"""Unit tests for ThreatService with repository pattern."""

import pytest
from unittest.mock import patch

from iriusrisk_cli.services.threat_service import ThreatService
from iriusrisk_cli.utils.error_handling import IriusRiskError
from tests.utils.helpers import ServiceTestBase


class TestThreatService(ServiceTestBase):
    """Test cases for ThreatService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        repositories = self.create_mock_repositories()
        
        # Create service with repository dependency
        self.service = ThreatService(threat_repository=repositories['threat'])
        self.mock_threat_repository = repositories['threat']
    
    def test_list_threats_success(self):
        """Test successful threat listing."""
        # Arrange
        expected_result = {
            'threats': [
                {'id': 'threat1', 'name': 'SQL Injection', 'state': 'expose'},
                {'id': 'threat2', 'name': 'XSS', 'state': 'mitigate'}
            ],
            'page_info': {'totalElements': 2},
            'full_response': {}
        }
        self.mock_threat_repository.list_all.return_value = expected_result
        
        with patch('iriusrisk_cli.services.threat_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_threats('project-id', page=0, size=20)
            
            # Assert
            assert result == expected_result
            mock_resolve.assert_called_once_with('project-id', self.mock_threat_repository.api_client)
            self.mock_threat_repository.list_all.assert_called_once_with(
                project_id='project-uuid', page=0, size=20, risk_level=None, status=None, custom_filter=None
            )
    
    def test_list_threats_with_filters(self):
        """Test threat listing with filters."""
        # Arrange
        expected_result = {
            'threats': [{'id': 'threat1', 'name': 'High Risk Threat'}],
            'page_info': {'totalElements': 1},
            'full_response': {}
        }
        self.mock_threat_repository.list_all.return_value = expected_result
        
        with patch('iriusrisk_cli.services.threat_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_threats(
                'project-id', page=1, size=10, risk_level='HIGH', status='expose'
            )
            
            # Assert
            assert result == expected_result
            self.mock_threat_repository.list_all.assert_called_once_with(
                project_id='project-uuid', page=1, size=10, risk_level='HIGH', status='expose', custom_filter=None
            )
    
    def test_get_threat_success(self):
        """Test successful threat retrieval."""
        # Arrange
        threat_data = {'id': 'threat1', 'name': 'SQL Injection', 'state': 'expose'}
        self.mock_threat_repository.get_by_id.return_value = threat_data
        
        with patch('iriusrisk_cli.services.threat_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.get_threat('project-id', 'threat1')
            
            # Assert
            assert result == threat_data
            mock_resolve.assert_called_once_with('project-id', self.mock_threat_repository.api_client)
            self.mock_threat_repository.get_by_id.assert_called_once_with('threat1', 'project-uuid')
    
    def test_get_threat_not_found(self):
        """Test getting non-existent threat."""
        # Arrange
        self.mock_threat_repository.get_by_id.side_effect = IriusRiskError("Threat 'nonexistent' not found")
        
        with patch('iriusrisk_cli.services.threat_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="Threat 'nonexistent' not found"):
                self.service.get_threat('project-id', 'nonexistent')
    
    def test_search_threats_success(self):
        """Test successful threat search."""
        # Arrange
        expected_result = {
            'threats': [{'id': 'threat1', 'name': 'SQL Injection'}],
            'page_info': {'totalElements': 1},
            'full_response': {},
            'search_string': 'sql'
        }
        self.mock_threat_repository.search.return_value = expected_result
        
        with patch('iriusrisk_cli.services.threat_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.search_threats('project-id', 'sql', page=0, size=20)
            
            # Assert
            assert result == expected_result
            mock_resolve.assert_called_once_with('project-id', self.mock_threat_repository.api_client)
            self.mock_threat_repository.search.assert_called_once_with(
                project_id='project-uuid', search_string='sql', page=0, size=20
            )
    
    def test_update_threat_status_success(self):
        """Test successful threat status update."""
        # Arrange
        expected_result = {
            'threat_id': 'threat1',
            'status': 'mitigate',
            'reason': 'Fixed vulnerability',
            'comment_created': True,
            'response': {'success': True}
        }
        self.mock_threat_repository.update_status.return_value = expected_result
        
        # Act
        result = self.service.update_threat_status(
            'threat1', 'mitigate', reason='Fixed vulnerability', comment='Applied security patch'
        )
        
        # Assert
        assert result == expected_result
        self.mock_threat_repository.update_status.assert_called_once_with(
            threat_id='threat1', status='mitigate', reason='Fixed vulnerability', comment='Applied security patch'
        )
    
    def test_update_threat_status_accept_without_reason(self):
        """Test threat status update to 'accept' without reason fails."""
        # Arrange
        self.mock_threat_repository.update_status.side_effect = IriusRiskError("The 'accept' status requires a reason")
        
        # Act & Assert
        with pytest.raises(IriusRiskError, match="The 'accept' status requires a reason"):
            self.service.update_threat_status('threat1', 'accept')
    
    def test_update_threat_status_comment_error(self):
        """Test threat status update with comment creation error."""
        # Arrange
        expected_result = {
            'threat_id': 'threat1',
            'status': 'mitigate',
            'reason': 'Fixed',
            'comment_created': False,
            'comment_error': 'Comment creation failed',
            'response': {'success': True}
        }
        self.mock_threat_repository.update_status.return_value = expected_result
        
        # Act
        result = self.service.update_threat_status(
            'threat1', 'mitigate', reason='Fixed', comment='Details'
        )
        
        # Assert
        assert result == expected_result
        assert result['comment_created'] is False
        assert 'comment_error' in result
