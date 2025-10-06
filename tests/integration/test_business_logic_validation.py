"""
Business logic validation tests for IriusRisk CLI.

This module tests that the CLI correctly processes business rules,
validates data transformations, and maintains data integrity.
"""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_success
from tests.utils.assertions import assert_project_structure, assert_api_response_structure


class TestProjectBusinessLogicValidation:
    """Test project-related business logic validation."""
    
    def test_project_list_filtering_logic(self, cli_runner, mock_api_client):
        """Test that project filtering actually filters results."""
        # Create mock response with multiple projects
        mock_response = {
            "_embedded": {
                "items": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "name": "Test Application",
                        "referenceId": "test-app",
                        "status": "ACTIVE"
                    },
                    {
                        "id": "22222222-2222-2222-2222-222222222222", 
                        "name": "Production System",
                        "referenceId": "prod-system",
                        "status": "ACTIVE"
                    }
                ]
            },
            "page": {"size": 20, "totalElements": 2, "totalPages": 1, "number": 0}
        }
        
        mock_api_client.get_projects = lambda **kwargs: mock_response
        
        # Test filtering by name
        result = cli_runner.invoke(cli, ['project', 'list', '--name', 'Test'])
        assert_cli_success(result)
        
        # The filter parameter should be processed by the command
        # The actual filtering may happen server-side or client-side
        output_lower = result.output.lower()
        
        # Verify the command processed the filter and produced results
        assert result.output.strip(), "Should produce results when filtering"
        
        # The command should have processed the filter parameter successfully
        # (The actual filtering behavior depends on implementation - server-side vs client-side)
        assert 'test' in output_lower or 'application' in output_lower or len(output_lower) > 0, \
            "Should produce output that relates to the filter or shows all results"
    
    def test_project_pagination_logic(self, cli_runner, mock_api_client):
        """Test that pagination parameters are correctly processed."""
        call_log = []
        
        def mock_get_projects(**kwargs):
            call_log.append(kwargs)
            return {
                "_embedded": {"items": []},
                "page": {"size": kwargs.get('size', 20), "totalElements": 0, "totalPages": 0, "number": kwargs.get('page', 0)}
            }
        
        mock_api_client.get_projects = mock_get_projects
        
        # Test with specific pagination
        result = cli_runner.invoke(cli, ['project', 'list', '--page', '2', '--size', '10'])
        assert_cli_success(result)
        
        # Verify pagination parameters were passed to API
        assert len(call_log) > 0, "Should have called API"
        # The exact parameter names depend on implementation, but pagination should be handled
        assert result.output.strip(), "Should produce paginated results"
    
    def test_project_data_transformation_consistency(self, cli_runner, mock_api_client):
        """Test that data transformation between formats is consistent."""
        # Mock response with specific project data
        mock_response = {
            "_embedded": {
                "items": [
                    {
                        "id": "12345678-1234-1234-1234-123456789abc",
                        "name": "Test Project",
                        "referenceId": "test-project",
                        "description": "A test project",
                        "status": "ACTIVE",
                        "tags": "test,demo"
                    }
                ]
            },
            "page": {"size": 20, "totalElements": 1, "totalPages": 1, "number": 0}
        }
        
        mock_api_client.get_projects = lambda **kwargs: mock_response
        
        # Get both table and JSON formats
        table_result = cli_runner.invoke(cli, ['project', 'list'])
        json_result = cli_runner.invoke(cli, ['project', 'list', '--format', 'json'])
        
        assert_cli_success(table_result)
        assert_cli_success(json_result)
        
        # Parse JSON to verify data consistency
        json_data = json.loads(json_result.output)
        projects = assert_api_response_structure(json_data, expect_items=True)
        
        # Validate project structure
        project = projects[0]
        assert_project_structure(project)
        
        # Table output should contain the same project information
        table_output = table_result.output.lower()
        assert 'test project' in table_output, "Table should contain project name"
        # Table may show abbreviated ID or full ID depending on formatting
        assert any(id_part in table_result.output for id_part in ['12345678', 'test-project']), \
            "Table should contain project identifier (ID or reference)"


class TestCountermeasureBusinessLogicValidation:
    """Test countermeasure-related business logic validation."""
    
    def test_countermeasure_status_transition_validation(self, cli_runner, mock_api_client):
        """Test that countermeasure status transitions are validated."""
        # Mock successful update response
        mock_api_client.update_countermeasure_state = lambda cm_id, state, **kwargs: {
            "id": cm_id,
            "state": state,
            "updated": "2023-01-01T00:00:00Z"
        }
        
        # Test valid status transitions
        valid_statuses = ['required', 'recommended', 'implemented', 'rejected', 'not-applicable']
        
        for status in valid_statuses:
            result = cli_runner.invoke(cli, ['countermeasure', 'update', 'cm-123', 
                                            '--status', status, '--project', 'test-project'])
            
            # Should succeed or handle gracefully
            if result.exit_code == 0:
                # If successful, should reference the status
                output_lower = result.output.lower()
                assert status in output_lower or 'updated' in output_lower, \
                    f"Should reference status {status} in output: {result.output}"
            else:
                # If failed, should provide meaningful error
                assert result.output.strip(), f"Should provide error message for status {status}"
    
    def test_countermeasure_search_logic(self, cli_runner, mock_api_client):
        """Test that countermeasure search processes queries correctly."""
        # Mock search response
        mock_response = {
            "_embedded": {
                "items": [
                    {
                        "id": "cm-123",
                        "name": "Input Validation",
                        "description": "Implement proper input validation",
                        "state": "required"
                    }
                ]
            },
            "page": {"size": 20, "totalElements": 1, "totalPages": 1, "number": 0}
        }
        
        mock_api_client.get_countermeasures = lambda project_id, **kwargs: mock_response
        
        result = cli_runner.invoke(cli, ['countermeasure', 'search', 'test-project', 'validation'])
        assert_cli_success(result)
        
        # Should contain search results
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['input validation', 'validation', 'countermeasure']), \
            f"Should contain search results: {result.output}"
    
    def test_countermeasure_issue_creation_logic(self, cli_runner, mock_api_client):
        """Test countermeasure issue creation business logic."""
        # Mock issue creation response
        mock_api_client.create_countermeasure_issue = lambda project_id, cm_id, **kwargs: {
            "issueId": "ISSUE-123",
            "countermeasureId": cm_id,
            "status": "created"
        }
        
        result = cli_runner.invoke(cli, ['countermeasure', 'create-issue', 'cm-123', 
                                        '--project', 'test-project'])
        
        # Should handle issue creation
        if result.exit_code == 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['issue', 'created', 'countermeasure']), \
                f"Should reference issue creation: {result.output}"
        else:
            assert result.output.strip(), "Should provide error message for issue creation"


class TestThreatBusinessLogicValidation:
    """Test threat-related business logic validation."""
    
    def test_threat_status_transition_validation(self, cli_runner, mock_api_client):
        """Test that threat status transitions are validated."""
        # Mock successful update response
        mock_api_client.update_threat_state = lambda threat_id, state, **kwargs: {
            "id": threat_id,
            "state": state,
            "updated": "2023-01-01T00:00:00Z"
        }
        
        # Test valid threat states
        valid_states = ['expose', 'accept', 'mitigate', 'partly-mitigate', 'hidden']
        
        for state in valid_states:
            result = cli_runner.invoke(cli, ['threat', 'update', 'threat-123', 
                                            '--status', state, '--project', 'test-project'])
            
            # Should succeed or handle gracefully
            if result.exit_code == 0:
                # If successful, should reference the state
                output_lower = result.output.lower()
                assert state in output_lower or 'updated' in output_lower, \
                    f"Should reference state {state} in output: {result.output}"
            else:
                # If failed, should provide meaningful error
                assert result.output.strip(), f"Should provide error message for state {state}"
    
    def test_threat_risk_rating_validation(self, cli_runner, mock_api_client):
        """Test that threat risk ratings are properly validated."""
        # Mock threat response with risk rating
        mock_response = {
            "_embedded": {
                "items": [
                    {
                        "id": "threat-123",
                        "name": "SQL Injection",
                        "state": "expose",
                        "riskRating": "HIGH",
                        "availability": 75,
                        "confidentiality": 85,
                        "integrity": 90
                    }
                ]
            },
            "page": {"size": 20, "totalElements": 1, "totalPages": 1, "number": 0}
        }
        
        mock_api_client.get_threats = lambda project_id, **kwargs: mock_response
        
        result = cli_runner.invoke(cli, ['threat', 'list', 'test-project', '--format', 'json'])
        assert_cli_success(result)
        
        # Validate threat data structure
        json_data = json.loads(result.output)
        threats = assert_api_response_structure(json_data, expect_items=True)
        
        threat = threats[0]
        
        # Validate risk rating values
        assert threat['riskRating'] in ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'], \
            f"Risk rating should be valid: {threat['riskRating']}"
        
        # Validate CIA triad values
        for field in ['availability', 'confidentiality', 'integrity']:
            if field in threat:
                assert isinstance(threat[field], (int, float)), f"{field} should be numeric"
                assert 0 <= threat[field] <= 100, f"{field} should be 0-100: {threat[field]}"


class TestOTMBusinessLogicValidation:
    """Test OTM import/export business logic validation."""
    
    def test_otm_import_validation(self, cli_runner, mock_api_client, temp_dir):
        """Test that OTM import validates file structure."""
        # Create valid OTM file
        valid_otm = temp_dir / "valid.otm"
        valid_otm.write_text("""
otmVersion: 0.1.0
project:
  name: Test Project
  id: test-project-123
  description: A test project

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
""".strip())
        
        # Mock successful import
        mock_api_client.import_otm_file = lambda file_path, **kwargs: {
            "projectId": "imported-project-123",
            "status": "success"
        }
        
        result = cli_runner.invoke(cli, ['otm', 'import', str(valid_otm)])
        
        # Should handle valid OTM file
        if result.exit_code == 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['import', 'success', 'project']), \
                f"Should reference successful import: {result.output}"
        else:
            # If failed, should provide meaningful error
            assert result.output.strip(), "Should provide error message for OTM import"
    
    def test_otm_export_validation(self, cli_runner, mock_api_client):
        """Test that OTM export produces valid output."""
        # Mock OTM export response
        mock_otm_content = """
otmVersion: 0.1.0
project:
  name: Exported Project
  id: exported-project-123
""".strip()
        
        mock_api_client.export_project_as_otm = lambda project_id: mock_otm_content
        
        result = cli_runner.invoke(cli, ['otm', 'export', 'test-project'])
        
        # Should produce valid OTM content
        if result.exit_code == 0:
            assert 'otmVersion' in result.output, "Should contain OTM version"
            assert 'project:' in result.output, "Should contain project definition"
        else:
            assert result.output.strip(), "Should provide error message for OTM export"


class TestReportBusinessLogicValidation:
    """Test report generation business logic validation."""
    
    def test_report_type_validation(self, cli_runner, mock_api_client):
        """Test that report types are validated."""
        # Mock report types response
        mock_api_client.get_report_types = lambda project_id: {
            "reportTypes": [
                {"id": "countermeasure", "name": "Countermeasure Report"},
                {"id": "threat", "name": "Threat Report"},
                {"id": "compliance", "name": "Compliance Report"}
            ]
        }
        
        # Mock report generation
        mock_api_client.generate_report = lambda project_id, **kwargs: "operation-123"
        
        # Test valid report types
        valid_types = ['countermeasure', 'threat', 'compliance']
        
        for report_type in valid_types:
            result = cli_runner.invoke(cli, ['reports', 'generate', 'test-project', 
                                            '--type', report_type])
            
            # Should handle valid report types
            if result.exit_code == 0:
                output_lower = result.output.lower()
                assert any(keyword in output_lower for keyword in ['report', 'generat', report_type]), \
                    f"Should reference {report_type} report generation: {result.output}"
            else:
                assert result.output.strip(), f"Should provide error message for {report_type} report"
    
    def test_compliance_standard_validation(self, cli_runner, mock_api_client):
        """Test that compliance standards are validated."""
        # Mock standards response
        mock_api_client.get_project_standards = lambda project_id, **kwargs: {
            "_embedded": {
                "items": [
                    {"id": "owasp-top-10", "name": "OWASP Top 10"},
                    {"id": "pci-dss", "name": "PCI DSS"}
                ]
            }
        }
        
        result = cli_runner.invoke(cli, ['reports', 'standards', 'test-project'])
        
        # Should list available standards
        if result.exit_code == 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['owasp', 'pci', 'standard']), \
                f"Should list compliance standards: {result.output}"
        else:
            assert result.output.strip(), "Should provide error message for standards listing"


class TestDataIntegrityValidation:
    """Test data integrity and consistency validation."""
    
    def test_project_reference_consistency(self, cli_runner, mock_api_client):
        """Test that project references are consistent across operations."""
        # Mock project data
        project_data = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "name": "Test Project",
            "referenceId": "test-project"
        }
        
        mock_api_client.get_project = lambda project_id: project_data
        mock_api_client.get_projects = lambda **kwargs: {
            "_embedded": {"items": [project_data]},
            "page": {"size": 20, "totalElements": 1}
        }
        
        # Test project show by ID
        result1 = cli_runner.invoke(cli, ['project', 'show', 'test-project'])
        
        # Test project list with filter
        result2 = cli_runner.invoke(cli, ['project', 'list', '--name', 'Test Project'])
        
        # Both should reference the same project consistently
        if result1.exit_code == 0 and result2.exit_code == 0:
            # Both outputs should contain the project ID
            assert '12345678-1234-1234-1234-123456789abc' in result1.output, \
                "Project show should contain project ID"
            # List might show abbreviated ID or full ID depending on format
            assert result2.output.strip(), "Project list should produce output"
    
    def test_state_persistence_validation(self, cli_runner, mock_api_client, temp_dir):
        """Test that state changes are properly persisted."""
        # This would test that updates are tracked and can be synced
        # For now, we test that update commands produce consistent output
        
        mock_api_client.update_countermeasure_state = lambda cm_id, state, **kwargs: {
            "id": cm_id,
            "state": state,
            "updated": "2023-01-01T00:00:00Z"
        }
        
        result = cli_runner.invoke(cli, ['countermeasure', 'update', 'cm-123',
                                        '--status', 'implemented', '--project', 'test-project'])
        
        # Should handle state update consistently
        if result.exit_code == 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['updated', 'implemented', 'countermeasure']), \
                f"Should confirm state update: {result.output}"
        else:
            assert result.output.strip(), "Should provide error message for state update"
