"""
Test helper utilities for IriusRisk CLI testing.

This module tests the consolidated helper utilities to ensure they work correctly.
"""

import pytest
import json
from pathlib import Path
from tests.utils.helpers import (
    MockResponse, TemporaryProject, create_mock_otm_file, 
    create_sample_data, create_paginated_response
)
from tests.utils.assertions import (
    assert_json_structure, assert_project_structure, 
    assert_cli_success, assert_cli_failure
)


class TestMockResponse:
    """Test cases for MockResponse utility."""
    
    def test_mock_response_creation(self):
        """Test creating a mock response."""
        data = {"test": "data"}
        response = MockResponse(data, 200)
        
        assert response.status_code == 200
        assert response.json() == data
        assert response.text == json.dumps(data)
    
    def test_mock_response_error(self):
        """Test mock response error handling."""
        response = MockResponse({}, 404)
        
        with pytest.raises(Exception):  # HTTPError
            response.raise_for_status()


class TestTemporaryProject:
    """Test cases for TemporaryProject utility."""
    
    def test_temporary_project_creation(self):
        """Test creating a temporary project directory."""
        with TemporaryProject("test-proj", "proj-123") as project_dir:
            assert project_dir.exists()
            assert project_dir.name == "test-proj"
            
            # Check .iriusRisk directory structure
            iriusrisk_dir = project_dir / ".iriusRisk"
            assert iriusrisk_dir.exists()
            
            # Check project.json
            project_json = iriusrisk_dir / "project.json"
            assert project_json.exists()
            
            with open(project_json) as f:
                config = json.load(f)
                assert config["project_id"] == "proj-123"
                assert config["project_name"] == "test-proj"


class TestSampleData:
    """Test cases for sample data utilities."""
    
    def test_create_sample_data(self):
        """Test creating sample test data."""
        data = create_sample_data()
        
        assert "project" in data
        assert "threat" in data
        assert "countermeasure" in data
        
        # Validate project structure
        assert_project_structure(data["project"])
    
    def test_create_paginated_response(self):
        """Test creating paginated API responses."""
        items = [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}]
        response = create_paginated_response(items, page=0, size=10, total=20)
        
        assert "_embedded" in response
        assert "items" in response["_embedded"]
        assert response["_embedded"]["items"] == items
        
        assert "page" in response
        page_info = response["page"]
        assert page_info["size"] == 10
        assert page_info["totalElements"] == 20
        assert page_info["totalPages"] == 2
        assert page_info["number"] == 0


class TestAssertions:
    """Test cases for assertion utilities."""
    
    def test_assert_json_structure(self):
        """Test JSON structure assertions."""
        data = {"name": "test", "id": 123, "active": True}
        
        # Should pass
        assert_json_structure(data, ["name", "id"])
        assert_json_structure(data, ["name"], {"name": str, "id": int})
        
        # Should fail
        with pytest.raises(AssertionError):
            assert_json_structure(data, ["missing_key"])
    
    def test_assert_cli_success(self):
        """Test CLI success assertions."""
        # Mock successful result
        class MockResult:
            exit_code = 0
            output = "Success message"
        
        result = MockResult()
        
        # Should pass
        assert_cli_success(result)
        assert_cli_success(result, "Success")
        
        # Should fail
        result.exit_code = 1
        with pytest.raises(AssertionError):
            assert_cli_success(result)
    
    def test_assert_cli_failure(self):
        """Test CLI failure assertions."""
        # Mock failed result
        class MockResult:
            exit_code = 1
            output = "Error message"
        
        result = MockResult()
        
        # Should pass
        assert_cli_failure(result)
        assert_cli_failure(result, "Error")
        
        # Should fail
        result.exit_code = 0
        with pytest.raises(AssertionError):
            assert_cli_failure(result)


class TestOTMFile:
    """Test cases for OTM file utilities."""
    
    def test_create_mock_otm_file(self):
        """Test creating mock OTM files."""
        otm_path = create_mock_otm_file()
        
        try:
            assert Path(otm_path).exists()
            
            with open(otm_path) as f:
                content = f.read()
                assert "otmVersion" in content
                assert "project:" in content
                assert "Test Project" in content
        finally:
            # Cleanup
            Path(otm_path).unlink(missing_ok=True)
    
    def test_create_custom_otm_file(self):
        """Test creating custom OTM files."""
        custom_content = "otmVersion: 0.2.0\nproject:\n  name: Custom Project"
        otm_path = create_mock_otm_file(custom_content)
        
        try:
            with open(otm_path) as f:
                content = f.read()
                assert "Custom Project" in content
                assert "0.2.0" in content
        finally:
            # Cleanup
            Path(otm_path).unlink(missing_ok=True)