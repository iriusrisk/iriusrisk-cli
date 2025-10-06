"""Report-specific API client for IriusRisk API."""

import requests
from typing import Dict, Any, Optional, List

from .base_client import BaseApiClient
from ..config import Config


class ReportApiClient(BaseApiClient):
    """API client for report generation operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the report API client.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)
    
    def get_report_types(self, project_id: str) -> List[Dict[str, Any]]:
        """Get available report types for a project.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            List of available report types with their supported formats
        """
        response = self._make_request('GET', f'projects/{project_id}/reports/types')
        return response.get('_embedded', {}).get('items', [])
    
    def generate_report(self, project_id: str, report_type: str, format: str, 
                       filters: Optional[Dict[str, Any]] = None, standard: Optional[str] = None) -> str:
        """Generate a report for a project.
        
        Args:
            project_id: UUID of the project
            report_type: Type of report (e.g., 'technical-countermeasure-report')
            format: Output format (pdf, html, xlsx, csv, xls)
            filters: Optional filters for the report
            standard: Optional standard UUID (required for compliance reports)
            
        Returns:
            Async operation ID for tracking report generation
        """
        # Build payload based on report type
        payload = {
            "name": report_type,
            "format": format
        }
        
        # Add standard for compliance reports (required)
        if standard:
            payload["standard"] = standard
        
        # Add filters for non-compliance reports
        if report_type != 'compliance-report':
            if filters is None:
                if 'countermeasure' in report_type:
                    filters = {
                        "all": {
                            "currentRisks": [],
                            "riskMitigation": None,
                            "riskMitigationPlanned": None,
                            "states": [],
                            "testResults": [],
                            "priorities": []
                        }
                    }
                else:
                    filters = {}
            payload["filters"] = filters
        
        # Set async header for report generation
        headers = {'X-Irius-Async': 'true'}
        
        response = self._make_request(
            'POST', 
            f'projects/{project_id}/reports/generate',
            headers=headers,
            json=payload
        )
        
        return response.get('operationId')
    
    def get_async_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get the status of an async operation.
        
        Args:
            operation_id: ID of the async operation
            
        Returns:
            Operation status information
        """
        return self._make_request('GET', f'async-operations/{operation_id}')
    
    def get_project_reports(self, project_id: str, page: int = 0, size: int = 100) -> List[Dict[str, Any]]:
        """Get list of generated reports for a project.
        
        Args:
            project_id: UUID of the project
            page: Page number for pagination
            size: Number of items per page
            
        Returns:
            List of generated reports
        """
        response = self._make_request(
            'GET', 
            f'projects/{project_id}/reports?page={page}&size={size}'
        )
        return response.get('_embedded', {}).get('items', [])
    
    def get_project_standards(self, project_id: str, page: int = 0, size: int = 1000) -> List[Dict[str, Any]]:
        """Get list of available standards for a project.
        
        Args:
            project_id: UUID of the project
            page: Page number for pagination
            size: Number of items per page
            
        Returns:
            List of available standards with id, name, and referenceId
        """
        response = self._make_request(
            'GET', 
            f'projects/{project_id}/standards?page={page}&size={size}'
        )
        return response.get('_embedded', {}).get('items', [])
    
    def download_report_content(self, report_id: str) -> bytes:
        """Download the content of a generated report.
        
        Args:
            report_id: UUID of the report
            
        Returns:
            Binary content of the report file
        """
        url = f"{self.base_url.rstrip('/')}/projects/reports/{report_id}/content"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    error_msg = str(e)
                raise Exception(f"Failed to download report: {error_msg}")
            else:
                raise Exception(f"Failed to download report: {str(e)}")
    
    def download_report_content_from_url(self, download_url: str) -> bytes:
        """Download the content of a generated report from a full URL.
        
        Args:
            download_url: Full URL to download the report from
            
        Returns:
            Binary content of the report file
        """
        # Use appropriate headers for file download
        headers = {
            'api-token': self.session.headers['api-token'],
            'Accept': '*/*'  # Accept any content type for file downloads
        }
        
        try:
            response = requests.get(download_url, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    error_msg = str(e)
                raise Exception(f"Failed to download report: {error_msg}")
            else:
                raise Exception(f"Failed to download report: {str(e)}")
    
    def get_issue_tracker_profiles(self, page: int = 0, size: int = 9999) -> Dict[str, Any]:
        """Get all available issue tracker profiles.
        
        Args:
            page: Page number (0-based)
            size: Number of profiles per page
            
        Returns:
            Issue tracker profiles response with _embedded.items containing the profiles
        """
        params = {
            'page': page,
            'size': size
        }
        return self._make_request('GET', '/issue-tracker-profiles/summary', params=params)
    
    def get_project_issue_trackers(self, project_id: str, page: int = 0, size: int = 9999) -> Dict[str, Any]:
        """Get issue trackers configured for a specific project.
        
        Args:
            project_id: Project UUID
            page: Page number (0-based)
            size: Number of issue trackers per page
            
        Returns:
            Project issue trackers response with _embedded.items containing the trackers
        """
        params = {
            'page': page,
            'size': size
        }
        return self._make_request('GET', f'/projects/{project_id}/issue-trackers/summary', params=params)
