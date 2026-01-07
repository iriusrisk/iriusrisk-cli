"""Unit tests for ProjectService with repository pattern."""

import pytest
from datetime import datetime
from unittest.mock import patch

from iriusrisk_cli.services.project_service import ProjectService
from iriusrisk_cli.utils.error_handling import IriusRiskError
from tests.utils.helpers import ServiceTestBase


class TestProjectService(ServiceTestBase):
    """Test cases for ProjectService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        repositories = self.create_mock_repositories()
        
        # Create service with repository dependencies
        self.service = ProjectService(
            project_repository=repositories['project'],
            threat_repository=repositories['threat'],
            countermeasure_repository=repositories['countermeasure']
        )
        
        # Store references for easy access
        self.mock_project_repository = repositories['project']
        self.mock_threat_repository = repositories['threat']
        self.mock_countermeasure_repository = repositories['countermeasure']
    
    def test_list_projects_success(self):
        """Test successful project listing."""
        # Arrange
        expected_result = {
            'projects': [
                {'id': 'proj1', 'name': 'Project 1'},
                {'id': 'proj2', 'name': 'Project 2'}
            ],
            'page_info': {'totalElements': 2},
            'full_response': {}
        }
        self.mock_project_repository.list_all.return_value = expected_result
        
        # Act
        result = self.service.list_projects(page=0, size=20)
        
        # Assert
        assert result == expected_result
        self.mock_project_repository.list_all.assert_called_once_with(
            page=0, size=20, name=None, tags=None, workflow_state=None,
            archived=None, blueprint=None, include_versions=False, custom_filter=None
        )
    
    def test_list_projects_with_filters(self):
        """Test project listing with filters."""
        # Arrange
        expected_result = {
            'projects': [{'id': 'proj1', 'name': 'Filtered Project'}],
            'page_info': {'totalElements': 1},
            'full_response': {}
        }
        self.mock_project_repository.list_all.return_value = expected_result
        
        # Act
        result = self.service.list_projects(
            name="test",
            tags="prod critical",
            archived=False,
            include_versions=True
        )
        
        # Assert
        assert result == expected_result
        self.mock_project_repository.list_all.assert_called_once_with(
            page=0, size=20, name="test", tags="prod critical", workflow_state=None,
            archived=False, blueprint=None, include_versions=True, custom_filter=None
        )
    
    def test_get_project_by_uuid(self):
        """Test getting project by UUID."""
        # Arrange
        project_id = "12345678-1234-1234-1234-123456789012"
        mock_project = {'id': project_id, 'name': 'Test Project'}
        self.mock_project_repository.get_by_id.return_value = mock_project
        
        # Act
        result = self.service.get_project(project_id)
        
        # Assert
        assert result == mock_project
        self.mock_project_repository.get_by_id.assert_called_once_with(project_id)
    
    def test_get_project_by_reference_id(self):
        """Test getting project by reference ID."""
        # Arrange
        reference_id = "my-project-ref"
        mock_project = {'id': 'uuid', 'name': 'Test Project', 'referenceId': reference_id}
        self.mock_project_repository.get_by_id.return_value = mock_project
        
        # Act
        result = self.service.get_project(reference_id)
        
        # Assert
        assert result == mock_project
        self.mock_project_repository.get_by_id.assert_called_once_with(reference_id)
    
    def test_get_project_not_found(self):
        """Test getting non-existent project."""
        # Arrange
        reference_id = "non-existent"
        self.mock_project_repository.get_by_id.side_effect = IriusRiskError("No project found with reference ID 'non-existent'")
        
        # Act & Assert
        with pytest.raises(IriusRiskError, match="No project found"):
            self.service.get_project(reference_id)
    
    def test_search_projects_success(self):
        """Test successful project search."""
        # Arrange
        search_string = "web app"
        expected_result = {
            'projects': [{'id': 'proj1', 'name': 'Web App Project'}],
            'page_info': {'totalElements': 1},
            'full_response': {},
            'search_string': search_string
        }
        self.mock_project_repository.search.return_value = expected_result
        
        # Act
        result = self.service.search_projects(search_string)
        
        # Assert
        assert result == expected_result
        self.mock_project_repository.search.assert_called_once_with(
            search_string=search_string, page=0, size=20, include_versions=False
        )
    
    def test_search_projects_empty_string(self):
        """Test project search with empty string."""
        # Arrange
        self.mock_project_repository.search.side_effect = IriusRiskError("Search string cannot be empty")
        
        # Act & Assert
        with pytest.raises(IriusRiskError, match="Search string cannot be empty"):
            self.service.search_projects("")
    
    def test_get_project_diagram_success(self):
        """Test successful project diagram retrieval."""
        # Arrange
        project_id = "test-project"
        artifacts_result = {
            'artifacts': [
                {'id': 'artifact1', 'name': 'diagram.png', 'visible': True}
            ]
        }
        content_result = {
            'content': 'base64content',
            'successfulGeneration': True
        }
        
        self.mock_project_repository.get_artifacts.return_value = artifacts_result
        self.mock_project_repository.get_artifact_content.return_value = content_result
        
        with patch('iriusrisk_cli.services.project_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = project_id
            
            # Act
            result = self.service.get_project_diagram(project_id, 'ORIGINAL')
            
            # Assert
            assert result['base64_content'] == 'base64content'
            assert result['artifact_name'] == 'diagram.png'
            assert result['artifact_id'] == 'artifact1'
            assert result['project_id'] == project_id
            assert result['size'] == 'ORIGINAL'
            mock_resolve.assert_called_once_with(project_id, self.mock_project_repository.api_client)
    
    def test_get_project_diagram_no_artifacts(self):
        """Test project diagram when no artifacts exist."""
        # Arrange
        project_id = "test-project"
        self.mock_project_repository.get_artifacts.return_value = {'artifacts': []}
        
        with patch('iriusrisk_cli.services.project_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = project_id
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="No artifacts found"):
                self.service.get_project_diagram(project_id)
    
    def test_generate_project_stats_success(self):
        """Test successful project statistics generation."""
        # Arrange
        project_id = "test-project"
        project_data = {'id': project_id, 'name': 'Test Project'}
        threats_data = {'threats': [{'state': 'expose', 'risk': 80}]}
        countermeasures_data = {'countermeasures': [{'state': 'required', 'priority': {'calculated': 'high'}}]}
        
        self.mock_project_repository.get_by_id.return_value = project_data
        self.mock_threat_repository.list_all.return_value = threats_data
        self.mock_countermeasure_repository.list_all.return_value = countermeasures_data
        
        with patch('iriusrisk_cli.services.project_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = project_id
            
            # Act
            result = self.service.generate_project_stats(project_id)
            
            # Assert
            assert result['metadata']['project_id'] == project_id
            assert result['metadata']['project_name'] == 'Test Project'
            assert result['threats']['total'] == 1
            assert result['countermeasures']['total'] == 1
            mock_resolve.assert_called_once_with(project_id, self.mock_project_repository.api_client)
    
    def test_categorize_risk_level(self):
        """Test risk level categorization."""
        # Test different risk score ranges
        assert self.service._categorize_risk_level(90) == 'critical'
        assert self.service._categorize_risk_level(70) == 'high'
        assert self.service._categorize_risk_level(50) == 'medium'
        assert self.service._categorize_risk_level(30) == 'low'
        assert self.service._categorize_risk_level(10) == 'very-low'
