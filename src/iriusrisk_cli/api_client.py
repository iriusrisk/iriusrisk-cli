"""Main API client that coordinates specialized API clients."""

from typing import Dict, Any, Optional, List

from .api.project_client import ProjectApiClient
from .api.threat_client import ThreatApiClient
from .api.countermeasure_client import CountermeasureApiClient
from .api.report_client import ReportApiClient
from .api.health_client import HealthApiClient
from .api.version_client import VersionApiClient
from .api.questionnaire_client import QuestionnaireApiClient
from .config import Config


class IriusRiskApiClient:
    """Main API client that coordinates specialized API clients using the coordinator pattern."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the API client with specialized client instances.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        if config is None:
            config = Config()
        
        # Initialize specialized clients with configuration
        self.project_client = ProjectApiClient(config=config)
        self.threat_client = ThreatApiClient(config=config)
        self.countermeasure_client = CountermeasureApiClient(config=config)
        self.report_client = ReportApiClient(config=config)
        self.health_client = HealthApiClient(config=config)
        self.version_client = VersionApiClient(config=config)
        self.questionnaire_client = QuestionnaireApiClient(config=config)
        
        # For backward compatibility, expose base properties
        self.base_url = self.project_client.base_url
        self.v1_base_url = self.project_client.v1_base_url
        self.session = self.project_client.session
    
    # Project-related methods - delegate to project_client
    def get_projects(self, 
                    page: int = 0, 
                    size: int = 20, 
                    include_versions: bool = False,
                    filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get all projects with optional filtering and pagination."""
        return self.project_client.get_projects(page, size, include_versions, filter_expression)
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a specific project by ID."""
        return self.project_client.get_project(project_id)
    
    def get_project_artifacts(self, project_id: str, page: int = 0, size: int = 20) -> Dict[str, Any]:
        """Get all artifacts for a project."""
        return self.project_client.get_project_artifacts(project_id, page, size)
    
    def get_project_artifact_content(self, artifact_id: str, size: str = "ORIGINAL") -> Dict[str, Any]:
        """Get artifact content (image data) by artifact ID."""
        return self.project_client.get_project_artifact_content(artifact_id, size)
    
    def get_components(self, page: int = 0, size: int = 20, filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get system components with optional filtering and pagination."""
        return self.project_client.get_components(page, size, filter_expression)
    
    def get_trust_zones(self, page: int = 0, size: int = 20, filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get system trust zones with optional filtering and pagination."""
        return self.project_client.get_trust_zones(page, size, filter_expression)
    
    def get_component(self, component_id: str) -> Dict[str, Any]:
        """Get a specific component by ID."""
        return self.project_client.get_component(component_id)
    
    # OTM API methods - delegate to project_client
    def import_otm_file(self, otm_file_path: str, auto_update: bool = True) -> Dict[str, Any]:
        """Import an OTM file to create a new project or update existing one."""
        return self.project_client.import_otm_file(otm_file_path, auto_update)
    
    def import_otm_content(self, otm_content: str, auto_update: bool = True) -> Dict[str, Any]:
        """Import OTM content to create a new project or update existing one."""
        return self.project_client.import_otm_content(otm_content, auto_update)
    
    def update_project_with_otm_file(self, project_id: str, otm_file_path: str) -> Dict[str, Any]:
        """Update an existing project with an OTM file."""
        return self.project_client.update_project_with_otm_file(project_id, otm_file_path)
    
    def update_project_with_otm_content(self, project_id: str, otm_content: str) -> Dict[str, Any]:
        """Update an existing project with OTM content."""
        return self.project_client.update_project_with_otm_content(project_id, otm_content)
    
    def export_project_as_otm(self, project_id: str) -> str:
        """Export a project as OTM format."""
        return self.project_client.export_project_as_otm(project_id)
    
    # Threat-related methods - delegate to threat_client
    def get_threats(self, 
                    project_id: str,
                    page: int = 0, 
                    size: int = 20, 
                    filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get threats for a specific project with optional filtering and pagination."""
        return self.threat_client.get_threats(project_id, page, size, filter_expression)
    
    def get_threat(self, project_id: str, threat_id: str) -> Dict[str, Any]:
        """Get a specific threat by ID within a project."""
        return self.threat_client.get_threat(project_id, threat_id)
    
    def update_threat_state(self, threat_id: str, state_transition: str, reason: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """Update the state of a threat."""
        return self.threat_client.update_threat_state(threat_id, state_transition, reason, comment)
    
    def create_threat_comment(self, threat_id: str, comment: str) -> Dict[str, Any]:
        """Create a comment for a threat."""
        return self.threat_client.create_threat_comment(threat_id, comment)
    
    # Countermeasure-related methods - delegate to countermeasure_client
    def get_countermeasures(self,
                           project_id: str,
                           page: int = 0,
                           size: int = 20,
                           filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get countermeasures for a specific project with optional filtering and pagination."""
        return self.countermeasure_client.get_countermeasures(project_id, page, size, filter_expression)

    def get_countermeasure(self, project_id: str, countermeasure_id: str) -> Dict[str, Any]:
        """Get a specific countermeasure by ID within a project."""
        return self.countermeasure_client.get_countermeasure(project_id, countermeasure_id)
    
    def update_countermeasure_state(self, countermeasure_id: str, state_transition: str, reason: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """Update the state of a countermeasure."""
        return self.countermeasure_client.update_countermeasure_state(countermeasure_id, state_transition, reason, comment)
    
    def create_countermeasure_comment(self, countermeasure_id: str, comment: str) -> Dict[str, Any]:
        """Create a comment for a countermeasure."""
        return self.countermeasure_client.create_countermeasure_comment(countermeasure_id, comment)
    
    def create_countermeasure_issue(self, project_id: str, countermeasure_id: str, issue_tracker_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an issue in the configured issue tracker for a countermeasure."""
        return self.countermeasure_client.create_countermeasure_issue(project_id, countermeasure_id, issue_tracker_id)
    
    # Report generation methods - delegate to report_client
    def get_report_types(self, project_id: str) -> List[Dict[str, Any]]:
        """Get available report types for a project."""
        return self.report_client.get_report_types(project_id)
    
    def generate_report(self, project_id: str, report_type: str, format: str, 
                       filters: Optional[Dict[str, Any]] = None, standard: Optional[str] = None) -> str:
        """Generate a report for a project."""
        return self.report_client.generate_report(project_id, report_type, format, filters, standard)
    
    def get_async_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get the status of an async operation."""
        return self.report_client.get_async_operation_status(operation_id)
    
    def get_project_reports(self, project_id: str, page: int = 0, size: int = 100) -> List[Dict[str, Any]]:
        """Get list of generated reports for a project."""
        return self.report_client.get_project_reports(project_id, page, size)
    
    def get_project_standards(self, project_id: str, page: int = 0, size: int = 1000) -> List[Dict[str, Any]]:
        """Get list of available standards for a project."""
        return self.report_client.get_project_standards(project_id, page, size)
    
    def download_report_content(self, report_id: str) -> bytes:
        """Download the content of a generated report."""
        return self.report_client.download_report_content(report_id)
    
    def download_report_content_from_url(self, download_url: str) -> bytes:
        """Download the content of a generated report from a full URL."""
        return self.report_client.download_report_content_from_url(download_url)
    
    # Issue Tracker API methods - delegate to report_client
    def get_issue_tracker_profiles(self, page: int = 0, size: int = 9999) -> Dict[str, Any]:
        """Get all available issue tracker profiles."""
        return self.report_client.get_issue_tracker_profiles(page, size)
    
    def get_project_issue_trackers(self, project_id: str, page: int = 0, size: int = 9999) -> Dict[str, Any]:
        """Get issue trackers configured for a specific project."""
        return self.report_client.get_project_issue_trackers(project_id, page, size)


# Global API client instance - removed to prevent eager config loading
# Use container.get(IriusRiskApiClient) instead
# api_client = IriusRiskApiClient()