"""Unit tests for IriusRiskApiClient to improve coverage."""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import yaml

from iriusrisk_cli.api_client import IriusRiskApiClient


class TestIriusRiskApiClientInit:
    """Test API client initialization."""
    
    def test_init_basic(self, mock_config):
        """Test basic initialization."""
        client = IriusRiskApiClient()
        
        assert client.base_url == mock_config.api_base_url
        assert client.v1_base_url == mock_config.api_v1_base_url
        assert isinstance(client.session, requests.Session)
        assert client.session.headers['api-token'] == mock_config.api_token
        assert client.session.headers['Content-Type'] == 'application/json'
        assert client.session.headers['Accept'] == 'application/json, application/hal+json'
    
    @patch.dict(os.environ, {'IRIUS_LOG_RESPONSES': 'true'})
    def test_init_with_logging_enabled(self, mock_config):
        """Test initialization with response logging enabled."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            client = IriusRiskApiClient()
            
            # Logging is now handled by the specialized clients
            assert hasattr(client.project_client, 'log_responses')
            assert hasattr(client.project_client, 'log_dir')
    
    @patch.dict(os.environ, {'IRIUS_LOG_RESPONSES': 'false'})
    def test_init_with_logging_disabled(self, mock_config):
        """Test initialization with response logging disabled."""
        client = IriusRiskApiClient()
        # Logging is now handled by the specialized clients
        assert hasattr(client.project_client, 'log_responses')


class TestIriusRiskApiClientDelegation:
    """Test API client delegation to specialized clients."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    def test_project_methods_delegation(self, mock_config):
        """Test that project methods are properly delegated."""
        # Test that the client has the expected specialized clients
        assert hasattr(self.client, 'project_client')
        assert hasattr(self.client, 'threat_client')
        assert hasattr(self.client, 'countermeasure_client')
        assert hasattr(self.client, 'report_client')
        
        # Test that public methods exist (delegation methods)
        assert hasattr(self.client, 'get_projects')
        assert hasattr(self.client, 'get_project')
    
    @patch.dict(os.environ, {'IRIUS_LOG_RESPONSES': 'true'})
    def test_log_response_v2_api(self):
        """Test logging for v2 API responses through specialized client."""
        # Create a fresh client with logging enabled
        client = IriusRiskApiClient()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"test": "data"}'
        mock_response.json.return_value = {"test": "data"}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.request = Mock()
        mock_response.request.headers = {'api-token': 'test-token'}
        
        url = 'https://test.iriusrisk.com/api/v2/projects'
        request_kwargs = {'json': {'filter': 'test'}}
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                with patch('datetime.datetime') as mock_datetime:
                    mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T12:00:00'
                    mock_datetime.now.return_value.strftime.return_value = '120000'
                    
                    # Test through project_client (which inherits from BaseApiClient)
                    client.project_client._log_response('GET', url, request_kwargs, mock_response)
                    
                    # Verify file was opened for writing
                    mock_file.assert_called_once()
                    # Verify JSON was dumped
                    mock_json_dump.assert_called_once()
                    
                    # Check the structure of logged data
                    logged_data = mock_json_dump.call_args[0][0]
                    assert logged_data['method'] == 'GET'
                    assert logged_data['url'] == url
                    assert logged_data['api_version'] == 'v2'
                    assert logged_data['response']['status_code'] == 200
    
    @patch.dict(os.environ, {'IRIUS_LOG_RESPONSES': 'true'})
    def test_log_response_v1_api(self):
        """Test logging for v1 API responses."""
        # Create a fresh client with logging enabled
        client = IriusRiskApiClient()
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = 'OTM content'
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.request = Mock()
        mock_response.request.headers = {}
        
        url = 'https://test.iriusrisk.com/api/v1/products/otm'
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                with patch('datetime.datetime') as mock_datetime:
                    mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T12:00:00'
                    mock_datetime.now.return_value.strftime.return_value = '120000'
                    
                    client.project_client._log_response('POST', url, {}, mock_response)
                    
                    # Verify logging occurred
                    mock_json_dump.assert_called_once()
                    logged_data = mock_json_dump.call_args[0][0]
                    assert logged_data['api_version'] == 'v1'
                    assert logged_data['response']['body'] == 'OTM content'
    
    @patch.dict(os.environ, {'IRIUS_LOG_RESPONSES': 'true'})
    def test_log_response_uuid_replacement(self):
        """Test that UUIDs are replaced with placeholders in endpoint patterns."""
        # Create a fresh client with logging enabled
        client = IriusRiskApiClient()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{}'
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_response.request = Mock()
        mock_response.request.headers = {}
        
        url = 'https://test.iriusrisk.com/api/v2/projects/12345678-1234-1234-1234-123456789abc/threats'
        
        with patch('builtins.open', mock_open()):
            with patch('json.dump') as mock_json_dump:
                with patch('datetime.datetime') as mock_datetime:
                    mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T12:00:00'
                    mock_datetime.now.return_value.strftime.return_value = '120000'
                    
                    client.threat_client._log_response('GET', url, {}, mock_response)
                    
                    logged_data = mock_json_dump.call_args[0][0]
                    assert logged_data['endpoint_pattern'] == '/projects/{id}/threats'
    
    def test_log_response_non_api_url_skipped(self):
        """Test that non-API URLs are skipped."""
        mock_response = Mock()
        url = 'https://test.iriusrisk.com/login'
        
        with patch('builtins.open') as mock_file:
            self.client.project_client._log_response('GET', url, {}, mock_response)
            mock_file.assert_not_called()


class TestIriusRiskApiClientRequests:
    """Test API client request methods."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        result = self.client.project_client._make_request('GET', '/projects', self.client.base_url)
        
        assert result == {'data': 'test'}
        mock_request.assert_called_once_with(
            'GET',
            f"{self.client.base_url}/projects",
            timeout=30
        )
    
    @patch('requests.Session.request')
    def test_make_request_with_params(self, mock_request):
        """Test API request with parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        params = {'page': 1, 'size': 20}
        json_data = {'filter': 'test'}
        
        result = self.client.project_client._make_request(
            'POST', 
            '/projects/query', 
            self.client.base_url,
            params=params,
            json=json_data
        )
        
        assert result == {'data': 'test'}
        mock_request.assert_called_once_with(
            'POST',
            f"{self.client.base_url}/projects/query",
            params=params,
            json=json_data,
            timeout=30
        )
    
    @patch('requests.Session.request')
    def test_make_request_raw_success(self, mock_request):
        """Test successful raw API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'raw response text'
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        result = self.client.project_client._make_request_raw('GET', '/projects/export', self.client.v1_base_url)
        
        assert result == 'raw response text'
    
    @patch('requests.Session.request')
    def test_make_request_http_error(self, mock_request):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_request.return_value = mock_response
        
        with pytest.raises(requests.HTTPError):
            self.client.project_client._make_request('GET', '/nonexistent', self.client.base_url)
    
    @patch('requests.Session.request')
    def test_make_request_connection_error(self, mock_request):
        """Test API request with connection error."""
        mock_request.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            self.client.project_client._make_request('GET', '/projects', self.client.base_url)
    
    @patch('requests.Session.request')
    def test_make_request_timeout(self, mock_request):
        """Test API request with timeout."""
        mock_request.side_effect = Timeout("Request timed out")
        
        with pytest.raises(Timeout):
            self.client.project_client._make_request('GET', '/projects', self.client.base_url)
    
    @patch('requests.Session.request')
    def test_make_request_json_decode_error(self, mock_request):
        """Test API request with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON response"
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        with pytest.raises(json.JSONDecodeError):
            self.client.project_client._make_request('GET', '/projects', self.client.base_url)


class TestIriusRiskApiClientOTMOperations:
    """Test OTM-related operations."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    def test_extract_project_id_from_otm_yaml_format(self):
        """Test extracting project ID from YAML-formatted OTM file."""
        otm_content = """
otmVersion: "0.1.0"
project:
  name: "Test Project"
  id: "test-project-123"
  description: "A test project"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            f.write(otm_content)
            f.flush()
            
            try:
                project_id = self.client.project_client._extract_project_id_from_otm(f.name)
                assert project_id == "test-project-123"
            finally:
                os.unlink(f.name)
    
    def test_extract_project_id_from_otm_regex_fallback(self):
        """Test extracting project ID using regex fallback."""
        otm_content = """
# This is not valid YAML but contains project ID
project:
  id: "regex-fallback-project"
  name: "Test"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            f.write(otm_content)
            f.flush()
            
            try:
                # Mock yaml module to not be available to trigger regex fallback
                import sys
                yaml_backup = sys.modules.get('yaml')
                if 'yaml' in sys.modules:
                    del sys.modules['yaml']
                try:
                    project_id = self.client.project_client._extract_project_id_from_otm(f.name)
                    assert project_id == "regex-fallback-project"
                finally:
                    if yaml_backup:
                        sys.modules['yaml'] = yaml_backup
            finally:
                os.unlink(f.name)
    
    def test_extract_project_id_from_content_yaml(self):
        """Test extracting project ID from OTM content string."""
        otm_content = """
otmVersion: "0.1.0"
project:
  name: "Test Project"
  id: "content-project-456"
"""
        project_id = self.client.project_client._extract_project_id_from_content(otm_content)
        assert project_id == "content-project-456"
    
    def test_extract_project_id_from_content_regex_fallback(self):
        """Test extracting project ID from content using regex fallback."""
        otm_content = 'project:\n  id: "regex-content-project"'
        
        import sys
        yaml_backup = sys.modules.get('yaml')
        if 'yaml' in sys.modules:
            del sys.modules['yaml']
        try:
            project_id = self.client.project_client._extract_project_id_from_content(otm_content)
            assert project_id == "regex-content-project"
        finally:
            if yaml_backup:
                sys.modules['yaml'] = yaml_backup
    
    def test_extract_project_id_not_found(self):
        """Test when project ID cannot be extracted."""
        otm_content = """
otmVersion: "0.1.0"
project:
  name: "Test Project"
  # No ID field
"""
        project_id = self.client.project_client._extract_project_id_from_content(otm_content)
        assert project_id is None
    
    @patch('requests.Session.post')
    def test_import_otm_file_new_project(self, mock_post):
        """Test importing OTM file to create new project."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'id': 'new-project-uuid',
            'referenceId': 'test-project-123'
        }
        mock_post.return_value = mock_response
        
        otm_content = """
otmVersion: "0.1.0"
project:
  id: "test-project-123"
  name: "Test Project"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            f.write(otm_content)
            f.flush()
            
            try:
                result = self.client.import_otm_file(f.name)
                assert result['id'] == 'new-project-uuid'
                mock_post.assert_called_once()
            finally:
                os.unlink(f.name)
    
    @patch('iriusrisk_cli.utils.api_helpers.validate_project_exists')
    @patch('requests.Session.post')
    def test_import_otm_file_conflict_returns_error(self, mock_post, mock_validate):
        """Test importing OTM file that conflicts with existing project returns error (name conflict)."""
        # Request fails with 400 (project exists by name)
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'message': 'A project with name "Existing Project" already exists',
            'errors': [{'message': 'Project already exists'}]
        }
        mock_response.text = 'A project with name "Existing Project" already exists'
        
        # Create HTTPError with response attribute
        http_error = requests.HTTPError("400 Bad Request")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response
        
        # Mock validate_project_exists to return False (name conflict - exists by name but not by ref ID)
        mock_validate.return_value = (False, "")
        
        otm_content = """
otmVersion: "0.1.0"
project:
  id: "existing-project"
  name: "Existing Project"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            f.write(otm_content)
            f.flush()
            
            try:
                with pytest.raises(requests.RequestException) as exc_info:
                    self.client.import_otm_file(f.name)
                # Verify it's a name conflict error
                assert "NAME CONFLICT" in str(exc_info.value)
            finally:
                os.unlink(f.name)
    
    @patch('iriusrisk_cli.utils.api_helpers.validate_project_exists')
    @patch('requests.Session.put')
    @patch('requests.Session.post')
    def test_import_otm_file_auto_update_success(self, mock_post, mock_put, mock_validate):
        """Test successful auto-update when project exists by ref ID."""
        # Mock POST response - project already exists error
        mock_post_response = Mock()
        mock_post_response.status_code = 400
        mock_post_response.json.return_value = {
            'message': 'Bad Request',
            'errors': [{'message': 'Project already exists'}]
        }
        
        # Create HTTPError for POST
        http_error = requests.HTTPError("400 Bad Request")
        http_error.response = mock_post_response
        mock_post_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_post_response
        
        # Mock validate_project_exists to return True (project exists by ref ID)
        mock_validate.return_value = (True, "550e8400-e29b-41d4-a716-446655440000")
        
        # Mock PUT response - successful update
        mock_put_response = Mock()
        mock_put_response.raise_for_status.return_value = None
        mock_put_response.json.return_value = {
            'id': 'existing-project',
            'name': 'Existing Project',
            'uuid': '550e8400-e29b-41d4-a716-446655440000'
        }
        mock_put.return_value = mock_put_response
        
        otm_content = """
otmVersion: "0.1.0"
project:
  id: "existing-project"
  name: "Existing Project"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            f.write(otm_content)
            f.flush()
            
            try:
                result = self.client.import_otm_file(f.name)
                # Verify successful update
                assert result['action'] == 'updated'
                assert result['id'] == 'existing-project'
                # Verify validate was called with the project ID
                mock_validate.assert_called_once()
                # Verify PUT was called (update)
                mock_put.assert_called_once()
            finally:
                os.unlink(f.name)
    
    @patch('requests.Session.put')
    def test_update_project_with_otm_file(self, mock_put):
        """Test updating project with OTM file."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = "Project updated successfully"
        mock_put.return_value = mock_response
        
        otm_content = "test OTM content"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.otm', delete=False) as f:
            f.write(otm_content)
            f.flush()
            
            try:
                result = self.client.update_project_with_otm_file('project-123', f.name)
                assert result == "Project updated successfully"
                
                # Verify the request was made correctly
                mock_put.assert_called_once()
            finally:
                os.unlink(f.name)
    
    @patch('requests.Session.get')
    def test_export_project_as_otm(self, mock_get):
        """Test exporting project as OTM."""
        mock_otm_content = """
otmVersion: "0.1.0"
project:
  id: "exported-project"
  name: "Exported Project"
"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = mock_otm_content
        mock_get.return_value = mock_response
        
        result = self.client.export_project_as_otm('project-uuid')
        
        assert result == mock_otm_content
        mock_get.assert_called_once()


class TestIriusRiskApiClientProjectOperations:
    """Test project-related operations."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    @patch('iriusrisk_cli.api.project_client.ProjectApiClient._make_request')
    def test_get_projects(self, mock_request):
        """Test getting projects list."""
        mock_response = {
            '_embedded': {
                'items': [
                    {'id': 'proj1', 'name': 'Project 1'},
                    {'id': 'proj2', 'name': 'Project 2'}
                ]
            },
            'page': {'size': 20, 'totalElements': 2}
        }
        mock_request.return_value = mock_response
        
        result = self.client.get_projects(
            page=1, 
            size=20, 
            include_versions=True, 
            filter_expression="name:Test"
        )
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'GET',
            '/projects',
            params={
                'page': 1,
                'size': 20,
                'includeVersions': 'true',
                'filter': "name:Test"
            }
        )
    
    @patch('iriusrisk_cli.api.project_client.ProjectApiClient._make_request')
    def test_get_project(self, mock_request):
        """Test getting single project."""
        mock_response = {'id': 'proj1', 'name': 'Project 1'}
        mock_request.return_value = mock_response
        
        result = self.client.get_project('proj1')
        
        assert result == mock_response
        mock_request.assert_called_once_with('GET', '/projects/proj1')


class TestIriusRiskApiClientStateUpdates:
    """Test threat and countermeasure state update operations."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    @patch('iriusrisk_cli.api.threat_client.ThreatApiClient._make_request')
    def test_update_threat_state(self, mock_request):
        """Test updating threat state."""
        mock_response = {'id': 'threat1', 'state': 'mitigate'}
        mock_request.return_value = mock_response
        
        result = self.client.update_threat_state(
            'threat1',
            'mitigate',
            reason='Security control implemented',
            comment='Added input validation'
        )
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'PUT',
            '/projects/threats/threat1/state',
            json={
                'stateTransition': 'mitigate',
                'reason': 'Security control implemented\n\nImplementation Details:\nAdded input validation'
            }
        )
    
    @patch('iriusrisk_cli.api.countermeasure_client.CountermeasureApiClient._make_request')
    def test_update_countermeasure_state(self, mock_request):
        """Test updating countermeasure state."""
        mock_response = {'id': 'cm1', 'state': 'implemented'}
        mock_request.return_value = mock_response
        
        result = self.client.update_countermeasure_state(
            'cm1',
            'implemented',
            reason='Control deployed',
            comment='WAF rules configured'
        )
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'PUT',
            '/projects/countermeasures/cm1/state',
            json={
                'stateTransition': 'implemented'
            }
        )
    
    @patch('iriusrisk_cli.api.threat_client.ThreatApiClient._make_request')
    def test_create_threat_comment(self, mock_request):
        """Test creating threat comment."""
        mock_response = {'id': 'comment1', 'content': 'Test comment'}
        mock_request.return_value = mock_response
        
        result = self.client.create_threat_comment('threat1', 'Test comment')
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'POST',
            '/projects/threats/comments',
            json={
                'threat': {'id': 'threat1'},
                'comment': 'Test comment'
            }
        )
    
    @patch('iriusrisk_cli.api.countermeasure_client.CountermeasureApiClient._make_request')
    def test_create_countermeasure_comment(self, mock_request):
        """Test creating countermeasure comment."""
        mock_response = {'id': 'comment2', 'content': 'CM comment'}
        mock_request.return_value = mock_response
        
        result = self.client.create_countermeasure_comment('cm1', 'CM comment')
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'POST',
            '/projects/countermeasures/comments',
            json={
                'countermeasure': {'id': 'cm1'},
                'comment': 'CM comment'
            }
        )


class TestIriusRiskApiClientReportOperations:
    """Test report generation operations."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    @patch('iriusrisk_cli.api.report_client.ReportApiClient._make_request')
    def test_get_report_types(self, mock_request):
        """Test getting available report types."""
        mock_response = {
            '_embedded': {
                'items': [
                    {'id': 'countermeasure', 'name': 'Countermeasure Report'},
                    {'id': 'threat', 'name': 'Threat Report'}
                ]
            }
        }
        mock_request.return_value = mock_response
        
        result = self.client.get_report_types('project1')
        
        expected_result = [
            {'id': 'countermeasure', 'name': 'Countermeasure Report'},
            {'id': 'threat', 'name': 'Threat Report'}
        ]
        assert result == expected_result
        mock_request.assert_called_once_with(
            'GET',
            'projects/project1/reports/types'
        )
    
    @patch('iriusrisk_cli.api.report_client.ReportApiClient._make_request')
    def test_generate_report(self, mock_request):
        """Test generating a report."""
        mock_response = {'operationId': 'op123', 'status': 'RUNNING'}
        mock_request.return_value = mock_response
        
        result = self.client.generate_report(
            'project1',
            'countermeasure',
            'pdf',
            filters={'status': 'required'},
            standard='owasp-top-10'
        )
        
        assert result == 'op123'
        mock_request.assert_called_once_with(
            'POST',
            'projects/project1/reports/generate',
            headers={'X-Irius-Async': 'true'},
            json={
                'name': 'countermeasure',
                'format': 'pdf',
                'filters': {'status': 'required'},
                'standard': 'owasp-top-10'
            }
        )
    
    @patch('iriusrisk_cli.api.report_client.ReportApiClient._make_request')
    def test_get_async_operation_status(self, mock_request):
        """Test getting async operation status."""
        mock_response = {'id': 'op123', 'status': 'COMPLETED', 'result': {'reportId': 'report456'}}
        mock_request.return_value = mock_response
        
        result = self.client.get_async_operation_status('op123')
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'GET',
            'async-operations/op123'
        )
    
    @patch.object(requests.Session, 'get')
    def test_download_report_content(self, mock_get):
        """Test downloading report content."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'PDF content here'
        mock_get.return_value = mock_response
        
        result = self.client.download_report_content('report456')
        
        assert result == b'PDF content here'
        mock_get.assert_called_once()


class TestIriusRiskApiClientIssueTrackerOperations:
    """Test issue tracker operations."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = IriusRiskApiClient()
    
    @patch('iriusrisk_cli.api.report_client.ReportApiClient._make_request')
    def test_get_issue_tracker_profiles(self, mock_request):
        """Test getting issue tracker profiles."""
        mock_response = {
            '_embedded': {
                'items': [
                    {'id': 'jira1', 'name': 'JIRA Integration', 'type': 'JIRA'}
                ]
            }
        }
        mock_request.return_value = mock_response
        
        result = self.client.get_issue_tracker_profiles(page=1, size=20)
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'GET',
            '/issue-tracker-profiles/summary',
            params={'page': 1, 'size': 20}
        )
    
    @patch('iriusrisk_cli.api.countermeasure_client.CountermeasureApiClient._make_request')
    def test_create_countermeasure_issue(self, mock_request):
        """Test creating countermeasure issue."""
        mock_response = {'issueId': 'PROJ-123', 'url': 'https://jira.com/PROJ-123'}
        mock_request.return_value = mock_response
        
        result = self.client.create_countermeasure_issue('project1', 'cm1', 'jira1')
        
        assert result == mock_response
        mock_request.assert_called_once_with(
            'POST',
            '/projects/project1/countermeasures/create-issues/bulk',
            json={
                'countermeasureIds': ['cm1'],
                'issueTrackerProfileId': 'jira1'
            },
            headers={'X-Irius-Async': 'true'}
        )
