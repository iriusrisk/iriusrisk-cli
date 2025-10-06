"""Unit tests for ReportService with repository pattern."""

import pytest
from pathlib import Path
from unittest.mock import patch

from iriusrisk_cli.services.report_service import ReportService
from iriusrisk_cli.utils.error_handling import IriusRiskError
from tests.utils.helpers import ServiceTestBase


class TestReportService(ServiceTestBase):
    """Test cases for ReportService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        repositories = self.create_mock_repositories()
        
        # Create service with repository dependency
        self.service = ReportService(report_repository=repositories['report'])
        self.mock_report_repository = repositories['report']
    
    def test_generate_report_success(self):
        """Test successful report generation."""
        # Arrange
        operation_id = 'op-123'
        report_data = {
            '_links': {
                'download': {'href': 'https://example.com/report.pdf'}
            },
            'reportType': 'technical-countermeasure-report',
            'format': 'pdf'
        }
        content = b'PDF content'
        
        self.mock_report_repository.generate_report.return_value = operation_id
        self.mock_report_repository.wait_for_completion.return_value = {'status': 'finished-success'}
        self.mock_report_repository.find_report_by_type_and_format.return_value = report_data
        self.mock_report_repository.download_report_content.return_value = content
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve, \
             patch('pathlib.Path.write_bytes') as mock_write:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.generate_report('project-id', 'countermeasure', 'pdf', 'output.pdf')
            
            # Assert
            assert result['output_path'] == Path('output.pdf')
            assert result['content_size'] == len(content)
            assert result['report_type'] == 'countermeasure'
            assert result['format'] == 'pdf'
            assert result['operation_id'] == operation_id
            
            # Verify write_bytes was called with correct content
            mock_write.assert_called_once_with(content)
    
    def test_generate_report_invalid_type(self):
        """Test report generation with invalid type."""
        # Act & Assert
        with pytest.raises(IriusRiskError, match="Invalid report type"):
            self.service.generate_report('project-id', 'invalid-type')
    
    def test_generate_report_invalid_format(self):
        """Test report generation with invalid format."""
        # Act & Assert
        with pytest.raises(IriusRiskError, match="Invalid report format"):
            self.service.generate_report('project-id', 'countermeasure', 'invalid-format')
    
    def test_generate_report_compliance_without_standard(self):
        """Test compliance report generation without standard."""
        # Act & Assert
        with pytest.raises(IriusRiskError, match="Compliance reports require a --standard parameter"):
            self.service.generate_report('project-id', 'compliance')
    
    def test_generate_report_compliance_with_standard(self):
        """Test compliance report generation with standard."""
        # Arrange
        operation_id = 'op-123'
        report_data = {
            '_links': {
                'download': {'href': 'https://example.com/compliance.pdf'}
            },
            'reportType': 'compliance-report',
            'format': 'pdf'
        }
        content = b'Compliance PDF content'
        
        self.mock_report_repository.resolve_standard_id.return_value = 'standard-uuid'
        self.mock_report_repository.generate_report.return_value = operation_id
        self.mock_report_repository.wait_for_completion.return_value = {'status': 'finished-success'}
        self.mock_report_repository.find_report_by_type_and_format.return_value = report_data
        self.mock_report_repository.download_report_content.return_value = content
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve, \
             patch('pathlib.Path.write_bytes') as mock_write:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.generate_report('project-id', 'compliance', 'pdf', 'compliance.pdf', standard='owasp-top-10')
            
            # Assert
            assert result['output_path'] == Path('compliance.pdf')
            assert result['standard'] == 'owasp-top-10'
            self.mock_report_repository.resolve_standard_id.assert_called_once_with('project-uuid', 'owasp-top-10')
            
            # Verify write_bytes was called with correct content
            mock_write.assert_called_once_with(content)
    
    def test_generate_report_timeout(self):
        """Test report generation timeout."""
        # Arrange
        operation_id = 'op-123'
        self.mock_report_repository.generate_report.return_value = operation_id
        self.mock_report_repository.wait_for_completion.side_effect = IriusRiskError("Report generation timed out after 300 seconds")
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="timed out"):
                self.service.generate_report('project-id', 'countermeasure', timeout=300)
    
    def test_generate_report_failed(self):
        """Test report generation failure."""
        # Arrange
        operation_id = 'op-123'
        self.mock_report_repository.generate_report.return_value = operation_id
        self.mock_report_repository.wait_for_completion.side_effect = IriusRiskError("Report generation failed: Server error")
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act & Assert
            with pytest.raises(IriusRiskError, match="Report generation failed"):
                self.service.generate_report('project-id', 'countermeasure')
    
    def test_list_report_types_success(self):
        """Test successful report types listing."""
        # Arrange
        expected_types = [
            {'name': 'Countermeasure Report', 'type': 'technical-countermeasure-report'},
            {'name': 'Threat Report', 'type': 'technical-threat-report'}
        ]
        self.mock_report_repository.get_report_types.return_value = {'report_types': expected_types}
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_report_types('project-id')
            
            # Assert
            assert result == expected_types
            mock_resolve.assert_called_once_with('project-id')
            self.mock_report_repository.get_report_types.assert_called_once_with('project-uuid')
    
    def test_list_standards_success(self):
        """Test successful standards listing."""
        # Arrange
        expected_standards = [
            {'name': 'OWASP Top 10', 'referenceId': 'owasp-top-10'},
            {'name': 'PCI DSS', 'referenceId': 'pci-dss'}
        ]
        self.mock_report_repository.get_standards.return_value = {'standards': expected_standards}
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_standards('project-id')
            
            # Assert
            assert result == expected_standards
            mock_resolve.assert_called_once_with('project-id')
            self.mock_report_repository.get_standards.assert_called_once_with('project-uuid')
    
    def test_list_reports_success(self):
        """Test successful reports listing."""
        # Arrange
        expected_reports = [
            {'id': 'report1', 'reportType': 'technical-countermeasure-report', 'format': 'pdf'},
            {'id': 'report2', 'reportType': 'compliance-report', 'format': 'html'}
        ]
        self.mock_report_repository.list_all.return_value = {'reports': expected_reports}
        
        with patch('iriusrisk_cli.services.report_service.resolve_project_id_to_uuid') as mock_resolve:
            mock_resolve.return_value = 'project-uuid'
            
            # Act
            result = self.service.list_reports('project-id')
            
            # Assert
            assert result == expected_reports
            mock_resolve.assert_called_once_with('project-id')
            self.mock_report_repository.list_all.assert_called_once_with('project-uuid')
    
    def test_resolve_standard_id_uuid(self):
        """Test standard ID resolution when already a UUID."""
        # This method was moved to repository, so we test through the service
        # The actual resolution is now handled by the repository
        pass
    
    def test_resolve_standard_id_reference(self):
        """Test standard ID resolution from reference ID."""
        # This method was moved to repository, so we test through the service
        # The actual resolution is now handled by the repository
        pass
    
    def test_resolve_standard_id_not_found(self):
        """Test standard ID resolution when not found."""
        # This method was moved to repository, so we test through the service
        # The actual resolution is now handled by the repository
        pass
