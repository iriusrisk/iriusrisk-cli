"""Unit tests for HTTP authentication module.

Tests cover:
- Credential extraction from request headers
- AuthenticationError handling
- API client creation from request
- Validation of header formats
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.iriusrisk_cli.mcp.auth import (
    AuthenticationError,
    extract_credentials_from_request,
    create_api_client_from_request,
)


class TestAuthenticationError:
    """Test AuthenticationError exception."""
    
    def test_authentication_error_message(self):
        """Test that AuthenticationError carries the message."""
        error = AuthenticationError("Test error message")
        assert str(error) == "Test error message"
    
    def test_authentication_error_is_exception(self):
        """Test that AuthenticationError is a proper exception."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Test")


class TestExtractCredentialsFromRequest:
    """Test extract_credentials_from_request function."""
    
    def test_extract_valid_credentials(self):
        """Test extracting valid credentials from request headers."""
        mock_request = Mock()
        mock_request.headers = {
            'X-IriusRisk-API-Key': 'test-api-key-12345',
            'X-IriusRisk-Hostname': 'https://example.iriusrisk.com'
        }
        
        api_key, hostname = extract_credentials_from_request(mock_request)
        
        assert api_key == 'test-api-key-12345'
        assert hostname == 'https://example.iriusrisk.com'
    
    def test_extract_credentials_strips_whitespace(self):
        """Test that whitespace is stripped from credentials."""
        mock_request = Mock()
        mock_request.headers = {
            'X-IriusRisk-API-Key': '  test-api-key  ',
            'X-IriusRisk-Hostname': '  https://example.iriusrisk.com  '
        }
        
        api_key, hostname = extract_credentials_from_request(mock_request)
        
        assert api_key == 'test-api-key'
        assert hostname == 'https://example.iriusrisk.com'
    
    def test_extract_credentials_no_request(self):
        """Test extraction with None request."""
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(None)
        
        assert "No request context" in str(exc_info.value)
    
    def test_extract_credentials_missing_api_key(self):
        """Test extraction with missing API key header."""
        mock_request = Mock()
        headers_dict = {
            'X-IriusRisk-Hostname': 'https://example.iriusrisk.com'
        }
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: headers_dict.get(key)
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        assert "X-IriusRisk-API-Key" in str(exc_info.value)
    
    def test_extract_credentials_missing_hostname(self):
        """Test extraction with missing hostname header."""
        mock_request = Mock()
        headers_dict = {
            'X-IriusRisk-API-Key': 'test-api-key'
        }
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: headers_dict.get(key)
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        assert "X-IriusRisk-Hostname" in str(exc_info.value)
    
    def test_extract_credentials_empty_api_key(self):
        """Test extraction with empty API key."""
        mock_request = Mock()
        headers_dict = {
            'X-IriusRisk-API-Key': '   ',  # Just whitespace
            'X-IriusRisk-Hostname': 'https://example.iriusrisk.com'
        }
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: headers_dict.get(key)
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_extract_credentials_empty_hostname(self):
        """Test extraction with empty hostname."""
        mock_request = Mock()
        headers_dict = {
            'X-IriusRisk-API-Key': 'test-api-key',
            'X-IriusRisk-Hostname': '   '  # Just whitespace
        }
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: headers_dict.get(key)
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_extract_credentials_invalid_hostname_format_no_protocol(self):
        """Test extraction with hostname missing protocol."""
        mock_request = Mock()
        headers_dict = {
            'X-IriusRisk-API-Key': 'test-api-key',
            'X-IriusRisk-Hostname': 'example.iriusrisk.com'  # Missing https://
        }
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: headers_dict.get(key)
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        assert "complete URL" in str(exc_info.value)
    
    def test_extract_credentials_http_hostname_accepted(self):
        """Test that http:// (not just https://) is accepted."""
        mock_request = Mock()
        mock_request.headers = {
            'X-IriusRisk-API-Key': 'test-api-key',
            'X-IriusRisk-Hostname': 'http://localhost:8080'
        }
        
        api_key, hostname = extract_credentials_from_request(mock_request)
        
        assert hostname == 'http://localhost:8080'


class TestCreateApiClientFromRequest:
    """Test create_api_client_from_request function."""
    
    def test_create_api_client_success(self):
        """Test successful API client creation."""
        with patch('src.iriusrisk_cli.api_client.IriusRiskApiClient') as mock_api_client_class:
            with patch('src.iriusrisk_cli.config.Config') as mock_config_class:
                mock_request = Mock()
                mock_request.headers = {
                    'X-IriusRisk-API-Key': 'test-api-key',
                    'X-IriusRisk-Hostname': 'https://example.iriusrisk.com'
                }
                
                mock_config = Mock()
                mock_config_class.return_value = mock_config
                
                mock_client = Mock()
                mock_api_client_class.return_value = mock_client
                
                result = create_api_client_from_request(mock_request)
                
                # Should have set credentials on config
                assert mock_config._api_key == 'test-api-key'
                assert mock_config._hostname == 'https://example.iriusrisk.com'
                
                # Should have created API client with config
                mock_api_client_class.assert_called_once_with(mock_config)
                
                # Should return the API client
                assert result == mock_client
    
    def test_create_api_client_propagates_auth_error(self):
        """Test that authentication errors are propagated."""
        mock_request = Mock()
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: None  # Missing headers
        
        with pytest.raises(AuthenticationError):
            create_api_client_from_request(mock_request)
    
    def test_create_api_client_creates_new_config_each_time(self):
        """Test that each request gets a fresh Config instance."""
        with patch('src.iriusrisk_cli.api_client.IriusRiskApiClient') as mock_api_client_class:
            with patch('src.iriusrisk_cli.config.Config') as mock_config_class:
                mock_request = Mock()
                mock_request.headers = {
                    'X-IriusRisk-API-Key': 'test-api-key',
                    'X-IriusRisk-Hostname': 'https://example.iriusrisk.com'
                }
                
                mock_config = Mock()
                mock_config_class.return_value = mock_config
                
                # Call twice
                create_api_client_from_request(mock_request)
                create_api_client_from_request(mock_request)
                
                # Config should be instantiated twice
                assert mock_config_class.call_count == 2


class TestHeaderCaseInsensitivity:
    """Test header name case handling.
    
    Note: HTTP headers are case-insensitive per RFC 7230,
    but the mock needs to match the implementation's lookup method.
    """
    
    def test_headers_with_standard_casing(self):
        """Test headers with standard casing work."""
        mock_request = Mock()
        mock_request.headers = {
            'X-IriusRisk-API-Key': 'test-api-key',
            'X-IriusRisk-Hostname': 'https://example.iriusrisk.com'
        }
        
        api_key, hostname = extract_credentials_from_request(mock_request)
        
        assert api_key == 'test-api-key'
        assert hostname == 'https://example.iriusrisk.com'


class TestAuthErrorMessages:
    """Test that error messages are informative."""
    
    def test_missing_api_key_message_includes_header_name(self):
        """Test that missing API key error includes the header name."""
        mock_request = Mock()
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: None
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        error_msg = str(exc_info.value)
        assert 'X-IriusRisk-API-Key' in error_msg
    
    def test_invalid_hostname_message_includes_example(self):
        """Test that invalid hostname error includes an example."""
        mock_request = Mock()
        headers_dict = {
            'X-IriusRisk-API-Key': 'test-key',
            'X-IriusRisk-Hostname': 'invalid-hostname'
        }
        mock_request.headers = Mock()
        mock_request.headers.get = lambda key: headers_dict.get(key)
        
        with pytest.raises(AuthenticationError) as exc_info:
            extract_credentials_from_request(mock_request)
        
        error_msg = str(exc_info.value)
        assert 'https://' in error_msg or 'http://' in error_msg

