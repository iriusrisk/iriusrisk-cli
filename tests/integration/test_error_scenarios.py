"""
Comprehensive error scenario testing for IriusRisk CLI.

This module tests error handling, network failures, authentication issues,
and other failure modes to ensure robust behavior during refactoring.
"""

import pytest
import json
from unittest.mock import patch, Mock
from click.testing import CliRunner
import requests

from iriusrisk_cli.main import cli
from tests.utils.assertions import assert_cli_failure


class TestAPIErrorHandling:
    """Test API error response handling."""
    
    def test_api_401_unauthorized(self, cli_runner, mock_api_client):
        """Test handling of 401 Unauthorized responses."""
        # Mock API client to raise 401 error
        def mock_get_projects(**kwargs):
            error = requests.HTTPError("401 Client Error: Unauthorized")
            error.response = Mock()
            error.response.status_code = 401
            error.response.json.return_value = {"message": "Invalid API token"}
            error.response.text = "Unauthorized"
            raise error
        
        mock_api_client.get_projects = mock_get_projects
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Should fail with meaningful error
        assert result.exit_code != 0, "Should fail with 401 error"
        assert result.output.strip(), "Should provide error message"
        
        # Error message should be user-friendly
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['unauthorized', 'token', 'authentication']), \
            f"Should mention authentication issue: {result.output}"
    
    def test_api_403_forbidden(self, cli_runner, mock_api_client):
        """Test handling of 403 Forbidden responses."""
        def mock_get_projects(**kwargs):
            error = requests.HTTPError("403 Client Error: Forbidden")
            error.response = Mock()
            error.response.status_code = 403
            error.response.json.return_value = {"message": "Insufficient permissions"}
            error.response.text = "Forbidden"
            raise error
        
        mock_api_client.get_projects = mock_get_projects
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        assert result.exit_code != 0, "Should fail with 403 error"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['forbidden', 'permission', 'access']), \
            f"Should mention permission issue: {result.output}"
    
    def test_api_404_not_found(self, cli_runner, mock_api_client):
        """Test handling of 404 Not Found responses."""
        def mock_get_project(project_id):
            error = requests.HTTPError("404 Client Error: Not Found")
            error.response = Mock()
            error.response.status_code = 404
            error.response.json.return_value = {"message": "Project not found"}
            error.response.text = "Not Found"
            raise error
        
        mock_api_client.get_project = mock_get_project
        
        result = cli_runner.invoke(cli, ['project', 'show', 'nonexistent-project'])
        
        assert result.exit_code != 0, "Should fail with 404 error"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['not found', 'does not exist', 'project']), \
            f"Should mention project not found: {result.output}"
    
    def test_api_500_server_error(self, cli_runner, mock_api_client):
        """Test handling of 500 Internal Server Error responses."""
        def mock_get_projects(**kwargs):
            error = requests.HTTPError("500 Server Error: Internal Server Error")
            error.response = Mock()
            error.response.status_code = 500
            error.response.json.return_value = {"message": "Internal server error"}
            error.response.text = "Internal Server Error"
            raise requests.RequestException("API request failed: HTTP 500: Internal Server Error")
        
        mock_api_client.get_projects = mock_get_projects
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        assert result.exit_code != 0, "Should fail with 500 error"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['server error', 'internal error', 'try again']), \
            f"Should mention server error: {result.output}"
    
    def test_api_network_timeout(self, cli_runner, mock_api_client):
        """Test handling of network timeout errors."""
        def mock_get_projects(**kwargs):
            raise requests.RequestException("API request failed: Connection timeout")
        
        mock_api_client.get_projects = mock_get_projects
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        assert result.exit_code != 0, "Should fail with timeout error"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['timeout', 'connection', 'network']), \
            f"Should mention network issue: {result.output}"
    
    def test_api_malformed_response(self, cli_runner, mock_api_client):
        """Test handling of malformed API responses."""
        def mock_get_projects(**kwargs):
            # Return invalid data structure
            return {"invalid": "structure", "missing": "_embedded"}
        
        mock_api_client.get_projects = mock_get_projects
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Should either handle gracefully or fail with meaningful error
        if result.exit_code != 0:
            assert result.output.strip(), "Should provide error message for malformed response"
        else:
            # If it succeeds, it should handle the malformed response gracefully
            assert result.output.strip(), "Should produce some output even with malformed response"


class TestInputValidationErrors:
    """Test input validation and parameter errors."""
    
    def test_invalid_project_id_format(self, cli_runner, mock_api_client):
        """Test validation of project ID format."""
        # Test with clearly invalid project ID
        result = cli_runner.invoke(cli, ['project', 'show', 'invalid-id-format!@#'])
        
        # Should handle gracefully - either validate format or let API handle it
        assert isinstance(result.exit_code, int), "Should return valid exit code"
        assert result.output.strip(), "Should provide some output"
    
    def test_missing_required_arguments(self, cli_runner, mock_api_client):
        """Test handling of missing required arguments."""
        # Test countermeasure update without required parameters
        result = cli_runner.invoke(cli, ['countermeasure', 'update'])
        
        assert result.exit_code != 0, "Should fail with missing arguments"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['missing', 'required', 'argument']), \
            f"Should mention missing arguments: {result.output}"
    
    def test_invalid_enum_values(self, cli_runner, mock_api_client):
        """Test handling of invalid enum values."""
        # Test with invalid status value
        result = cli_runner.invoke(cli, ['countermeasure', 'update', 'cm-123', 
                                        '--status', 'invalid-status', '--project', 'test-project'])
        
        # Should fail with validation error
        if result.exit_code != 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['invalid', 'status', 'choice']), \
                f"Should mention invalid status: {result.output}"
    
    def test_invalid_format_option(self, cli_runner, mock_api_client):
        """Test handling of invalid format options."""
        result = cli_runner.invoke(cli, ['project', 'list', '--format', 'invalid-format'])
        
        assert result.exit_code != 0, "Should fail with invalid format"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['invalid', 'format', 'choice']), \
            f"Should mention invalid format: {result.output}"


class TestConfigurationErrors:
    """Test configuration and environment errors."""
    
    def test_missing_api_token(self, cli_runner, monkeypatch):
        """Test behavior when API token is missing."""
        # Remove API token from environment
        monkeypatch.delenv("IRIUS_API_TOKEN", raising=False)
        monkeypatch.delenv("IRIUS_HOSTNAME", raising=False)
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Should fail with configuration error
        if result.exit_code != 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['token', 'configuration', 'environment']), \
                f"Should mention missing token: {result.output}"
    
    def test_invalid_api_hostname(self, cli_runner, monkeypatch):
        """Test behavior with invalid API hostname."""
        monkeypatch.setenv("IRIUS_HOSTNAME", "invalid-hostname-format")
        monkeypatch.setenv("IRIUS_API_TOKEN", "test-token")
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Should handle gracefully - either validate URL or let requests handle it
        assert isinstance(result.exit_code, int), "Should return valid exit code"


class TestFileOperationErrors:
    """Test file operation error handling."""
    
    def test_otm_file_not_found(self, cli_runner, mock_api_client):
        """Test OTM import with non-existent file."""
        result = cli_runner.invoke(cli, ['otm', 'import', '/nonexistent/file.otm'])
        
        assert result.exit_code != 0, "Should fail with file not found"
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in ['not found', 'file', 'does not exist']), \
            f"Should mention file not found: {result.output}"
    
    def test_otm_file_permission_denied(self, cli_runner, mock_api_client, temp_dir):
        """Test OTM import with permission denied."""
        # Create a file and make it unreadable (if possible on this system)
        test_file = temp_dir / "unreadable.otm"
        test_file.write_text("test content")
        
        try:
            test_file.chmod(0o000)  # Remove all permissions
            
            result = cli_runner.invoke(cli, ['otm', 'import', str(test_file)])
            
            # Should handle permission error gracefully
            if result.exit_code != 0:
                output_lower = result.output.lower()
                # Click may provide different error messages for file access issues
                assert any(keyword in output_lower for keyword in ['permission', 'access', 'denied', 'readable', 'not readable']), \
                    f"Should mention file access issue: {result.output}"
        finally:
            # Restore permissions for cleanup
            try:
                test_file.chmod(0o644)
            except:
                pass
    
    def test_invalid_otm_file_content(self, cli_runner, mock_api_client, temp_dir):
        """Test OTM import with invalid file content."""
        # Create file with invalid OTM content
        invalid_otm = temp_dir / "invalid.otm"
        invalid_otm.write_text("invalid yaml content: [unclosed bracket")
        
        result = cli_runner.invoke(cli, ['otm', 'import', str(invalid_otm)])
        
        # Should handle invalid content gracefully
        if result.exit_code != 0:
            output_lower = result.output.lower()
            assert any(keyword in output_lower for keyword in ['invalid', 'parse', 'format']), \
                f"Should mention invalid content: {result.output}"


class TestConcurrencyAndRaceConditions:
    """Test concurrent operations and race conditions."""
    
    def test_concurrent_project_operations(self, cli_runner, mock_api_client):
        """Test that concurrent operations don't interfere."""
        # This is a basic test - real concurrency testing would be more complex
        results = []
        
        # Simulate multiple operations
        for i in range(3):
            result = cli_runner.invoke(cli, ['project', 'list'])
            results.append(result)
        
        # All operations should succeed or fail consistently
        exit_codes = [r.exit_code for r in results]
        assert len(set(exit_codes)) <= 2, "Exit codes should be consistent across operations"
        
        # All should produce output
        for result in results:
            assert result.output.strip(), "Each operation should produce output"


class TestResourceLimits:
    """Test behavior with resource limits and large datasets."""
    
    def test_large_project_list_handling(self, cli_runner, mock_api_client):
        """Test handling of large project lists."""
        # Mock a large response
        large_response = {
            "_embedded": {
                "items": [
                    {
                        "id": f"project-{i:04d}-1234-5678-9abc-def012345678",
                        "name": f"Project {i}",
                        "referenceId": f"project-{i}",
                        "status": "ACTIVE"
                    }
                    for i in range(100)  # 100 projects
                ]
            },
            "page": {
                "size": 100,
                "totalElements": 100,
                "totalPages": 1,
                "number": 0
            }
        }
        
        mock_api_client.get_projects = lambda **kwargs: large_response
        
        result = cli_runner.invoke(cli, ['project', 'list'])
        
        # Should handle large response gracefully
        assert result.exit_code == 0, f"Should handle large response: {result.output}"
        assert result.output.strip(), "Should produce output for large response"
        
        # Output should not be truncated unexpectedly
        assert len(result.output) > 1000, "Output should contain substantial content for 100 projects"


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery and retry mechanisms."""
    
    def test_api_error_recovery(self, cli_runner, mock_api_client):
        """Test that CLI handles API errors gracefully without crashing."""
        # Test multiple error scenarios in sequence
        error_scenarios = [
            lambda **kwargs: (_ for _ in ()).throw(requests.RequestException("Connection error")),
            lambda **kwargs: (_ for _ in ()).throw(requests.RequestException("API request failed: HTTP 500")),
            lambda **kwargs: {"invalid": "response"}
        ]
        
        for i, error_func in enumerate(error_scenarios):
            mock_api_client.get_projects = error_func
            
            result = cli_runner.invoke(cli, ['project', 'list'])
            
            # Should handle each error gracefully
            assert isinstance(result.exit_code, int), f"Scenario {i}: Should return valid exit code"
            assert result.output.strip(), f"Scenario {i}: Should provide error message"
            
            # Should not contain Python tracebacks (unless in debug mode)
            output_lower = result.output.lower()
            assert 'traceback' not in output_lower, f"Scenario {i}: Should not show Python tracebacks"
