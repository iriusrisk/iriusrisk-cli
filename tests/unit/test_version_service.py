"""Unit tests for VersionService with repository pattern."""

import pytest
from unittest.mock import Mock

from iriusrisk_cli.services.version_service import VersionService
from iriusrisk_cli.utils.error_handling import IriusRiskError
from tests.utils.helpers import ServiceTestBase


class TestVersionService(ServiceTestBase):
    """Test cases for VersionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # Create mock repositories
        from iriusrisk_cli.repositories.version_repository import VersionRepository
        from iriusrisk_cli.repositories.report_repository import ReportRepository
        from iriusrisk_cli.repositories.project_repository import ProjectRepository
        
        self.mock_version_repository = Mock(spec=VersionRepository)
        self.mock_report_repository = Mock(spec=ReportRepository)
        self.mock_project_repository = Mock(spec=ProjectRepository)
        
        # Mock the api_client attribute for UUID resolution
        self.mock_api_client = Mock()
        # Mock get_projects to return a valid project with UUID for reference ID lookup
        self.mock_api_client.get_projects.return_value = {
            '_embedded': {
                'items': [
                    {'id': '00000000-0000-0000-0000-000000000000', 'referenceId': 'test-project'}
                ]
            }
        }
        self.mock_project_repository.api_client = self.mock_api_client
        
        # Create service with repository dependencies
        self.service = VersionService(
            version_repository=self.mock_version_repository,
            report_repository=self.mock_report_repository,
            project_repository=self.mock_project_repository
        )
    
    def test_list_versions_success(self):
        """Test successful version listing."""
        # Arrange
        project_id = "test-project"
        expected_result = {
            'versions': [
                {'id': 'v1', 'name': 'Version 1', 'operation': 'none'},
                {'id': 'v2', 'name': 'Version 2', 'operation': 'none'}
            ],
            'page_info': {'totalElements': 2},
            'full_response': {}
        }
        self.mock_version_repository.list_all.return_value = expected_result
        
        # Act
        result = self.service.list_versions(project_id, page=0, size=20)
        
        # Assert
        assert result == expected_result
        self.mock_version_repository.list_all.assert_called_once()
        call_args = self.mock_version_repository.list_all.call_args
        assert call_args[1]['page'] == 0
        assert call_args[1]['size'] == 20
    
    def test_list_versions_with_pagination(self):
        """Test version listing with pagination."""
        # Arrange
        project_id = "test-project"
        expected_result = {
            'versions': [{'id': 'v1', 'name': 'Version 1'}],
            'page_info': {'totalElements': 10, 'number': 2},
            'full_response': {}
        }
        self.mock_version_repository.list_all.return_value = expected_result
        
        # Act
        result = self.service.list_versions(project_id, page=2, size=5)
        
        # Assert
        assert result == expected_result
        call_args = self.mock_version_repository.list_all.call_args
        assert call_args[1]['page'] == 2
        assert call_args[1]['size'] == 5
    
    def test_create_version_without_wait(self):
        """Test version creation without waiting for completion."""
        # Arrange
        project_id = "test-project"
        version_name = "v1.0"
        expected_result = {
            'id': 'async-op-123',
            'state': 'pending'
        }
        self.mock_version_repository.create.return_value = expected_result
        
        # Act
        result = self.service.create_version(
            project_id=project_id,
            name=version_name,
            wait=False
        )
        
        # Assert
        assert result == expected_result
        self.mock_version_repository.create.assert_called_once()
        call_args = self.mock_version_repository.create.call_args
        assert call_args[1]['name'] == version_name
    
    def test_create_version_with_wait_success(self):
        """Test version creation with waiting for completion."""
        # Arrange
        project_id = "test-project"
        version_name = "v1.0"
        operation_id = "async-op-123"
        
        # Mock version creation response - API returns 'operationId' not 'id'
        self.mock_version_repository.create.return_value = {
            'operationId': operation_id,
            'status': 'pending'
        }
        
        # Mock async operation completion - matches actual API response format
        self.mock_report_repository.get_operation_status.return_value = {
            'id': operation_id,
            'status': 'finished-success',
            'summary': {
                'fail': 0,
                'success': 1,
                'pending': 0,
                'interrupted': 0,
                'in-progress': 0
            }
        }
        
        # Mock project unlock - project is ready
        self.mock_project_repository.get_by_id.return_value = {
            'id': project_id,
            'operation': 'none',
            'isThreatModelLocked': False,
            'readOnly': False
        }
        
        # Act
        result = self.service.create_version(
            project_id=project_id,
            name=version_name,
            wait=True,
            timeout=300
        )
        
        # Assert
        assert result['status'] == 'finished-success'
        self.mock_report_repository.get_operation_status.assert_called()
        self.mock_project_repository.get_by_id.assert_called()
    
    def test_create_version_with_wait_timeout(self):
        """Test version creation timeout while waiting."""
        # Arrange
        project_id = "test-project"
        version_name = "v1.0"
        operation_id = "async-op-123"
        
        # Mock version creation response - API returns 'operationId' not 'id'
        self.mock_version_repository.create.return_value = {
            'operationId': operation_id,
            'status': 'pending'
        }
        
        # Mock async operation that never completes
        self.mock_report_repository.get_operation_status.return_value = {
            'id': operation_id,
            'status': 'in-progress'
        }
        
        # Act & Assert
        with pytest.raises(IriusRiskError, match="timed out"):
            self.service.create_version(
                project_id=project_id,
                name=version_name,
                wait=True,
                timeout=1  # Short timeout for testing
            )
    
    def test_create_version_with_description(self):
        """Test version creation with description."""
        # Arrange
        project_id = "test-project"
        version_name = "v1.0"
        description = "Release candidate"
        expected_result = {'id': 'async-op-123'}
        self.mock_version_repository.create.return_value = expected_result
        
        # Act
        result = self.service.create_version(
            project_id=project_id,
            name=version_name,
            description=description,
            wait=False
        )
        
        # Assert
        assert result == expected_result
        call_args = self.mock_version_repository.create.call_args
        assert call_args[1]['description'] == description
    
    def test_update_version_success(self):
        """Test successful version metadata update."""
        # Arrange
        version_id = "version-uuid-123"
        new_name = "v1.0 Final"
        new_description = "Final release"
        expected_result = {
            'id': version_id,
            'name': new_name,
            'description': new_description
        }
        self.mock_version_repository.update.return_value = expected_result
        
        # Act
        result = self.service.update_version(version_id, new_name, new_description)
        
        # Assert
        assert result == expected_result
        self.mock_version_repository.update.assert_called_once_with(
            version_id=version_id,
            name=new_name,
            description=new_description
        )
    
    def test_compare_versions_success(self):
        """Test successful version comparison."""
        # Arrange
        project_id = "test-project"
        source_id = "version-1"
        target_id = "version-2"
        expected_result = {
            'changes': [
                {'elementType': 'threat', 'changeType': 'added', 'elementName': 'New Threat'},
                {'elementType': 'component', 'changeType': 'removed', 'elementName': 'Old Component'}
            ],
            'page_info': {'totalElements': 2},
            'full_response': {}
        }
        self.mock_version_repository.compare.return_value = expected_result
        
        # Act
        result = self.service.compare_versions(
            project_id=project_id,
            source_version_id=source_id,
            target_version_id=target_id
        )
        
        # Assert
        assert result == expected_result
        self.mock_version_repository.compare.assert_called_once()
        call_args = self.mock_version_repository.compare.call_args
        assert call_args[1]['source_version_id'] == source_id
        assert call_args[1]['target_version_id'] == target_id
    
    def test_compare_versions_with_filters(self):
        """Test version comparison with filter expression."""
        # Arrange
        project_id = "test-project"
        source_id = "version-1"
        target_id = "version-2"
        filter_expr = "'elementType'='threat'"
        expected_result = {
            'changes': [{'elementType': 'threat', 'changeType': 'added'}],
            'page_info': {'totalElements': 1},
            'full_response': {}
        }
        self.mock_version_repository.compare.return_value = expected_result
        
        # Act
        result = self.service.compare_versions(
            project_id=project_id,
            source_version_id=source_id,
            target_version_id=target_id,
            filter_expression=filter_expr
        )
        
        # Assert
        assert result == expected_result
        call_args = self.mock_version_repository.compare.call_args
        assert call_args[1]['filter_expression'] == filter_expr
    
    def test_list_versions_error_handling(self):
        """Test error handling in version listing."""
        # Arrange
        project_id = "invalid-project"
        self.mock_version_repository.list_all.side_effect = IriusRiskError("Project not found")
        
        # Act & Assert
        with pytest.raises(IriusRiskError, match="Project not found"):
            self.service.list_versions(project_id)
    
    def test_create_version_error_handling(self):
        """Test error handling in version creation."""
        # Arrange
        project_id = "test-project"
        version_name = "v1.0"
        self.mock_version_repository.create.side_effect = IriusRiskError("Permission denied")
        
        # Act & Assert
        with pytest.raises(IriusRiskError, match="Permission denied"):
            self.service.create_version(project_id, version_name, wait=False)

