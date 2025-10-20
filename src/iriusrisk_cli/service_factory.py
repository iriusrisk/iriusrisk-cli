"""Service factory for managing service creation and dependency injection."""

from typing import Optional

from .api_client import IriusRiskApiClient
from .config import Config
from .repositories.project_repository import ProjectRepository
from .repositories.threat_repository import ThreatRepository
from .repositories.countermeasure_repository import CountermeasureRepository
from .repositories.report_repository import ReportRepository
from .repositories.version_repository import VersionRepository
from .services.project_service import ProjectService
from .services.threat_service import ThreatService
from .services.countermeasure_service import CountermeasureService
from .services.report_service import ReportService
from .services.version_service import VersionService


class ServiceFactory:
    """Factory for creating services with proper dependency injection."""
    
    def __init__(self, api_client: Optional[IriusRiskApiClient] = None, config: Optional[Config] = None):
        """Initialize the service factory.
        
        Args:
            api_client: Main API client instance (creates new one if not provided)
            config: Configuration instance (creates new one if not provided)
        """
        if config is None:
            config = Config()
        self._config = config
        self._api_client = api_client or IriusRiskApiClient(config=config)
        
        # Cache repository instances for lifecycle management
        self._project_repository = None
        self._threat_repository = None
        self._countermeasure_repository = None
        self._report_repository = None
        self._version_repository = None
        
        # Cache service instances for lifecycle management
        self._project_service = None
        self._threat_service = None
        self._countermeasure_service = None
        self._report_service = None
        self._version_service = None
    
    @property
    def api_client(self) -> IriusRiskApiClient:
        """Get the main API client instance."""
        return self._api_client
    
    def get_project_repository(self) -> ProjectRepository:
        """Get or create a ProjectRepository instance."""
        if self._project_repository is None:
            self._project_repository = ProjectRepository(
                api_client=self._api_client.project_client
            )
        return self._project_repository
    
    def get_threat_repository(self) -> ThreatRepository:
        """Get or create a ThreatRepository instance."""
        if self._threat_repository is None:
            self._threat_repository = ThreatRepository(
                api_client=self._api_client.threat_client
            )
        return self._threat_repository
    
    def get_countermeasure_repository(self) -> CountermeasureRepository:
        """Get or create a CountermeasureRepository instance."""
        if self._countermeasure_repository is None:
            self._countermeasure_repository = CountermeasureRepository(
                api_client=self._api_client.countermeasure_client
            )
        return self._countermeasure_repository
    
    def get_report_repository(self) -> ReportRepository:
        """Get or create a ReportRepository instance."""
        if self._report_repository is None:
            self._report_repository = ReportRepository(
                api_client=self._api_client.report_client
            )
        return self._report_repository
    
    def get_version_repository(self) -> VersionRepository:
        """Get or create a VersionRepository instance."""
        if self._version_repository is None:
            self._version_repository = VersionRepository(
                api_client=self._api_client.version_client
            )
        return self._version_repository
    
    def get_project_service(self) -> ProjectService:
        """Get or create a ProjectService instance with proper dependency injection."""
        if self._project_service is None:
            self._project_service = ProjectService(
                project_repository=self.get_project_repository(),
                threat_repository=self.get_threat_repository(),
                countermeasure_repository=self.get_countermeasure_repository()
            )
        return self._project_service
    
    def get_threat_service(self) -> ThreatService:
        """Get or create a ThreatService instance with proper dependency injection."""
        if self._threat_service is None:
            self._threat_service = ThreatService(
                threat_repository=self.get_threat_repository()
            )
        return self._threat_service
    
    def get_countermeasure_service(self) -> CountermeasureService:
        """Get or create a CountermeasureService instance with proper dependency injection."""
        if self._countermeasure_service is None:
            self._countermeasure_service = CountermeasureService(
                countermeasure_repository=self.get_countermeasure_repository()
            )
        return self._countermeasure_service
    
    def get_report_service(self) -> ReportService:
        """Get or create a ReportService instance with proper dependency injection."""
        if self._report_service is None:
            self._report_service = ReportService(
                report_repository=self.get_report_repository()
            )
        return self._report_service
    
    def get_version_service(self) -> VersionService:
        """Get or create a VersionService instance with proper dependency injection."""
        if self._version_service is None:
            self._version_service = VersionService(
                version_repository=self.get_version_repository(),
                report_repository=self.get_report_repository()
            )
        return self._version_service
    
    def cleanup(self):
        """Clean up resources and reset service instances."""
        # Clear cached repository instances
        self._project_repository = None
        self._threat_repository = None
        self._countermeasure_repository = None
        self._report_repository = None
        self._version_repository = None
        
        # Clear cached service instances
        self._project_service = None
        self._threat_service = None
        self._countermeasure_service = None
        self._report_service = None
        self._version_service = None
        
        # Close any sessions if needed
        if hasattr(self._api_client, 'session') and self._api_client.session:
            self._api_client.session.close()
