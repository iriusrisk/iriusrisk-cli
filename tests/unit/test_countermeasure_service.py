"""Unit tests for CountermeasureService with repository pattern."""

import pytest
from unittest.mock import patch

from iriusrisk_cli.services.countermeasure_service import CountermeasureService
from iriusrisk_cli.utils.error_handling import IriusRiskError
from tests.utils.helpers import ServiceTestBase


class TestCountermeasureService(ServiceTestBase):
    """Test cases for CountermeasureService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        repositories = self.create_mock_repositories()
        
        # Create service with repository dependency
        self.service = CountermeasureService(countermeasure_repository=repositories['countermeasure'])
        self.mock_countermeasure_repository = repositories['countermeasure']
    
    def test_list_countermeasures_success(self):
        """Test successful countermeasure listing."""
        # Arrange
        expected_result = {
            'countermeasures': [
                {'id': 'cm1', 'name': 'Input Validation', 'state': 'required'},
                {'id': 'cm2', 'name': 'Authentication', 'state': 'implemented'}
            ],
            'page_info': {'totalElements': 2},
            'full_response': {}
        }
        self.mock_countermeasure_repository.list_all.return_value = expected_result
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_countermeasures('project-id', page=0, size=20)
            
            # Assert
            assert result == expected_result
            mock_resolve.assert_called_once_with('project-id', self.mock_countermeasure_repository.api_client)
            self.mock_countermeasure_repository.list_all.assert_called_once_with(
                project_id='project-uuid', page=0, size=20, risk_level=None, status=None, custom_filter=None
            )
    
    def test_list_countermeasures_with_filters(self):
        """Test countermeasure listing with filters."""
        # Arrange
        expected_result = {
            'countermeasures': [{'id': 'cm1', 'name': 'High Priority Control'}],
            'page_info': {'totalElements': 1},
            'full_response': {}
        }
        self.mock_countermeasure_repository.list_all.return_value = expected_result
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_countermeasures(
                'project-id', page=1, size=10, risk_level='HIGH', status='required'
            )
            
            # Assert
            assert result == expected_result
            self.mock_countermeasure_repository.list_all.assert_called_once_with(
                project_id='project-uuid', page=1, size=10, risk_level='HIGH', status='required', custom_filter=None
            )
    
    def test_get_countermeasure_success(self):
        """Test successful countermeasure retrieval."""
        # Arrange
        countermeasure_data = {'id': 'cm1', 'name': 'Input Validation', 'state': 'required'}
        self.mock_countermeasure_repository.get_by_id.return_value = countermeasure_data
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.get_countermeasure('project-id', 'cm1')
            
            # Assert
            assert result == countermeasure_data
            mock_resolve.assert_called_once_with('project-id', self.mock_countermeasure_repository.api_client)
            self.mock_countermeasure_repository.get_by_id.assert_called_once_with('cm1', 'project-uuid')
    
    def test_get_countermeasure_not_found(self):
        """Test getting non-existent countermeasure."""
        # Arrange
        self.mock_countermeasure_repository.get_by_id.side_effect = IriusRiskError("Countermeasure 'nonexistent' not found")
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="Countermeasure 'nonexistent' not found"):
                self.service.get_countermeasure('project-id', 'nonexistent')
    
    def test_search_countermeasures_success(self):
        """Test successful countermeasure search."""
        # Arrange
        expected_result = {
            'countermeasures': [{'id': 'cm1', 'name': 'Input Validation'}],
            'page_info': {'totalElements': 1},
            'full_response': {},
            'search_string': 'validation'
        }
        self.mock_countermeasure_repository.search.return_value = expected_result
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.search_countermeasures('project-id', 'validation')
            
            # Assert
            assert result == expected_result
            mock_resolve.assert_called_once_with('project-id', self.mock_countermeasure_repository.api_client)
            self.mock_countermeasure_repository.search.assert_called_once_with(
                project_id='project-uuid', search_string='validation'
            )
    
    def test_update_countermeasure_status_success(self):
        """Test successful countermeasure status update."""
        # Arrange
        expected_result = {
            'countermeasure_id': 'cm1',
            'status': 'implemented',
            'reason': 'Control implemented',
            'comment_created': True,
            'response': {'success': True}
        }
        self.mock_countermeasure_repository.update_status.return_value = expected_result
        
        # Act
        result = self.service.update_countermeasure_status(
            'cm1', 'implemented', reason='Control implemented', comment='Details of implementation'
        )
        
        # Assert
        assert result == expected_result
        self.mock_countermeasure_repository.update_status.assert_called_once_with(
            countermeasure_id='cm1', status='implemented', reason='Control implemented', comment='Details of implementation'
        )
    
    def test_update_countermeasure_status_comment_error(self):
        """Test countermeasure status update with comment creation error."""
        # Arrange
        expected_result = {
            'countermeasure_id': 'cm1',
            'status': 'implemented',
            'reason': 'Done',
            'comment_created': False,
            'comment_error': 'Comment creation failed',
            'response': {'success': True}
        }
        self.mock_countermeasure_repository.update_status.return_value = expected_result
        
        # Act
        result = self.service.update_countermeasure_status(
            'cm1', 'implemented', reason='Done', comment='Details'
        )
        
        # Assert
        assert result == expected_result
        assert result['comment_created'] is False
        assert 'comment_error' in result
    
    def test_create_countermeasure_issue_success(self):
        """Test successful countermeasure issue creation."""
        # Arrange
        countermeasure_data = {
            'id': 'cm-uuid',
            'name': 'Input Validation',
            'referenceId': 'cm1'
        }
        profiles_result = {
            'profiles': [
                {'id': 'tracker1', 'name': 'Jira Tracker'}
            ]
        }
        issue_result = {'issueId': 'PROJ-123', 'issueLink': 'https://jira.example.com/PROJ-123'}
        
        self.mock_countermeasure_repository.find_countermeasure_by_reference_or_uuid.return_value = countermeasure_data
        self.mock_countermeasure_repository.get_issue_tracker_profiles.return_value = profiles_result
        self.mock_countermeasure_repository.create_issue.return_value = issue_result
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.create_countermeasure_issue('project-id', 'cm1', 'Jira Tracker')
            
            # Assert
            assert result['countermeasure_id'] == 'cm1'
            assert result['countermeasure_name'] == 'Input Validation'
            assert result['issue_tracker_name'] == 'Jira Tracker'
            assert result['result'] == issue_result
    
    def test_create_countermeasure_issue_already_exists(self):
        """Test countermeasure issue creation when issue already exists."""
        # Arrange
        countermeasure_data = {
            'id': 'cm-uuid',
            'name': 'Input Validation',
            'referenceId': 'cm1',
            'issueId': 'EXISTING-123',
            'issueLink': 'https://jira.example.com/EXISTING-123',
            'issueState': 'Open'
        }
        
        self.mock_countermeasure_repository.find_countermeasure_by_reference_or_uuid.return_value = countermeasure_data
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="already has an issue"):
                self.service.create_countermeasure_issue('project-id', 'cm1')
    
    def test_create_countermeasure_issue_not_found(self):
        """Test countermeasure issue creation when countermeasure not found."""
        # Arrange
        self.mock_countermeasure_repository.find_countermeasure_by_reference_or_uuid.return_value = None
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="not found in project"):
                self.service.create_countermeasure_issue('project-id', 'nonexistent')
    
    def test_create_countermeasure_issue_tracker_not_found(self):
        """Test countermeasure issue creation with invalid tracker."""
        # Arrange
        countermeasure_data = {
            'id': 'cm-uuid',
            'name': 'Input Validation',
            'referenceId': 'cm1'
        }
        profiles_result = {
            'profiles': [
                {'id': 'tracker1', 'name': 'Jira Tracker'}
            ]
        }
        
        self.mock_countermeasure_repository.find_countermeasure_by_reference_or_uuid.return_value = countermeasure_data
        self.mock_countermeasure_repository.get_issue_tracker_profiles.return_value = profiles_result
        
        with patch('iriusrisk_cli.services.countermeasure_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="Issue tracker 'InvalidTracker' not found"):
                self.service.create_countermeasure_issue('project-id', 'cm1', 'InvalidTracker')
