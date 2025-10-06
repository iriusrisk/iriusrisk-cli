"""Unit tests for HealthApiClient."""

import pytest
from unittest.mock import Mock, patch
from src.iriusrisk_cli.api.health_client import HealthApiClient
from src.iriusrisk_cli.config import Config


class TestHealthApiClient:
    """Test cases for HealthApiClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.api_base_url = "https://test.iriusrisk.com/api/v2"
        self.mock_config.api_token = "test-token"
        
        with patch('src.iriusrisk_cli.api.base_client.BaseApiClient.__init__', return_value=None):
            self.health_client = HealthApiClient(config=self.mock_config)

    @patch('src.iriusrisk_cli.api.health_client.HealthApiClient._make_request')
    def test_get_health_success(self, mock_make_request):
        """Test successful health check."""
        # Arrange
        expected_response = {"status": "healthy", "components": {"database": "up"}}
        mock_make_request.return_value = expected_response

        # Act
        result = self.health_client.get_health()

        # Assert
        assert result == expected_response
        mock_make_request.assert_called_once_with('GET', '/health')

    @patch('src.iriusrisk_cli.api.health_client.HealthApiClient._make_request')
    def test_get_health_api_error(self, mock_make_request):
        """Test health check when API returns error."""
        # Arrange
        mock_make_request.side_effect = Exception("API Error")

        # Act & Assert
        with pytest.raises(Exception, match="API Error"):
            self.health_client.get_health()

    @patch('src.iriusrisk_cli.api.health_client.HealthApiClient._make_request')
    def test_get_info_success(self, mock_make_request):
        """Test successful info retrieval."""
        # Arrange
        expected_response = {"version": "2.15.0", "build": "12345"}
        mock_make_request.return_value = expected_response

        # Act
        result = self.health_client.get_info()

        # Assert
        assert result == expected_response
        mock_make_request.assert_called_once_with('GET', '/info')

    @patch('src.iriusrisk_cli.api.health_client.HealthApiClient._make_request')
    def test_get_info_api_error(self, mock_make_request):
        """Test info retrieval when API returns error."""
        # Arrange
        mock_make_request.side_effect = Exception("Connection timeout")

        # Act & Assert
        with pytest.raises(Exception, match="Connection timeout"):
            self.health_client.get_info()
