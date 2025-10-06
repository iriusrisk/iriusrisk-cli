"""Unit tests for HealthService."""

import pytest
from unittest.mock import Mock, patch
from src.iriusrisk_cli.services.health_service import HealthService
from src.iriusrisk_cli.api.health_client import HealthApiClient


class TestHealthService:
    """Test cases for HealthService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_health_client = Mock(spec=HealthApiClient)
        self.health_service = HealthService(self.mock_health_client)

    def test_init_with_valid_client(self):
        """Test HealthService initialization with valid client."""
        service = HealthService(self.mock_health_client)
        assert service.health_client == self.mock_health_client

    def test_init_with_none_client_raises_error(self):
        """Test HealthService initialization with None client raises ValueError."""
        with pytest.raises(ValueError, match="HealthService requires a health_client instance"):
            HealthService(None)

    def test_check_health_success(self):
        """Test successful health check."""
        # Arrange
        expected_health = {"status": "healthy", "components": {"database": "up"}}
        self.mock_health_client.get_health.return_value = expected_health

        # Act
        result = self.health_service.check_health()

        # Assert
        assert result == expected_health
        self.mock_health_client.get_health.assert_called_once()

    def test_check_health_client_exception(self):
        """Test health check when client raises exception."""
        # Arrange
        self.mock_health_client.get_health.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            self.health_service.check_health()

    def test_get_instance_info_success(self):
        """Test successful instance info retrieval."""
        # Arrange
        expected_info = {"version": "2.15.0", "build": "12345"}
        self.mock_health_client.get_info.return_value = expected_info

        # Act
        result = self.health_service.get_instance_info()

        # Assert
        assert result == expected_info
        self.mock_health_client.get_info.assert_called_once()

    def test_get_instance_info_client_exception(self):
        """Test instance info when client raises exception."""
        # Arrange
        self.mock_health_client.get_info.side_effect = Exception("API error")

        # Act & Assert
        with pytest.raises(Exception, match="API error"):
            self.health_service.get_instance_info()
