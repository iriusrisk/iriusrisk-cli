"""Dependency injection container for IriusRisk CLI."""

from typing import Optional, Dict, Any, TypeVar, Type, Callable
from .config import Config
from .api_client import IriusRiskApiClient
from .service_factory import ServiceFactory
from .repositories.project_repository import ProjectRepository
from .repositories.threat_repository import ThreatRepository
from .repositories.countermeasure_repository import CountermeasureRepository
from .repositories.report_repository import ReportRepository
from .services.project_service import ProjectService
from .services.threat_service import ThreatService
from .services.countermeasure_service import CountermeasureService
from .services.report_service import ReportService
from .services.health_service import HealthService

T = TypeVar('T')


class Container:
    """Dependency injection container for managing application dependencies."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the container with optional configuration.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        self._config = config or Config()
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        
        # Register default factories
        self._register_factories()
    
    def _register_factories(self):
        """Register factory functions for creating instances."""
        # Configuration (singleton)
        self._factories[Config] = lambda: self._config
        
        # API Client (singleton)
        self._factories[IriusRiskApiClient] = lambda: IriusRiskApiClient(
            config=self.get(Config)
        )
        
        # Repositories (singletons)
        self._factories[ProjectRepository] = lambda: ProjectRepository(
            api_client=self.get(IriusRiskApiClient).project_client
        )
        self._factories[ThreatRepository] = lambda: ThreatRepository(
            api_client=self.get(IriusRiskApiClient).threat_client
        )
        self._factories[CountermeasureRepository] = lambda: CountermeasureRepository(
            api_client=self.get(IriusRiskApiClient).countermeasure_client
        )
        self._factories[ReportRepository] = lambda: ReportRepository(
            api_client=self.get(IriusRiskApiClient).report_client
        )
        
        # Services (singletons)
        self._factories[ProjectService] = lambda: ProjectService(
            project_repository=self.get(ProjectRepository),
            threat_repository=self.get(ThreatRepository),
            countermeasure_repository=self.get(CountermeasureRepository)
        )
        self._factories[ThreatService] = lambda: ThreatService(
            threat_repository=self.get(ThreatRepository)
        )
        self._factories[CountermeasureService] = lambda: CountermeasureService(
            countermeasure_repository=self.get(CountermeasureRepository)
        )
        self._factories[ReportService] = lambda: ReportService(
            report_repository=self.get(ReportRepository)
        )
        self._factories[HealthService] = lambda: HealthService(
            health_client=self.get(IriusRiskApiClient).health_client
        )
        
        # Service Factory (singleton) - for backward compatibility
        self._factories[ServiceFactory] = lambda: ServiceFactory(
            api_client=self.get(IriusRiskApiClient)
        )
    
    def get(self, service_type: Type[T]) -> T:
        """Get an instance of the specified service type.
        
        Args:
            service_type: The type of service to retrieve
            
        Returns:
            Instance of the requested service type
            
        Raises:
            ValueError: If the service type is not registered
        """
        # Return cached instance if available
        if service_type in self._instances:
            return self._instances[service_type]
        
        # Create new instance using factory
        if service_type not in self._factories:
            raise ValueError(f"No factory registered for {service_type.__name__}")
        
        instance = self._factories[service_type]()
        self._instances[service_type] = instance
        return instance
    
    def register_factory(self, service_type: Type[T], factory: Callable[[], T]):
        """Register a factory function for a service type.
        
        Args:
            service_type: The type of service
            factory: Factory function that creates instances
        """
        self._factories[service_type] = factory
        # Clear cached instance if it exists
        if service_type in self._instances:
            del self._instances[service_type]
    
    def register_instance(self, service_type: Type[T], instance: T):
        """Register a specific instance for a service type.
        
        Args:
            service_type: The type of service
            instance: The instance to register
        """
        self._instances[service_type] = instance
    
    def clear_cache(self):
        """Clear all cached instances, forcing recreation on next access."""
        self._instances.clear()
    
    def cleanup(self):
        """Clean up resources and close connections."""
        # Clean up API client session if it exists
        if IriusRiskApiClient in self._instances:
            api_client = self._instances[IriusRiskApiClient]
            if hasattr(api_client, 'session') and api_client.session:
                api_client.session.close()
        
        # Clear all cached instances
        self.clear_cache()


# Global container instance - will be replaced with context-based injection
_default_container: Optional[Container] = None


def get_container() -> Container:
    """Get the default container instance.
    
    This function provides backward compatibility during the transition.
    Eventually, containers should be passed explicitly through context.
    
    Returns:
        The default container instance
    """
    global _default_container
    if _default_container is None:
        _default_container = Container()
    return _default_container


def set_container(container: Container):
    """Set the default container instance.
    
    This function allows for dependency injection in tests and different contexts.
    
    Args:
        container: The container instance to use as default
    """
    global _default_container
    _default_container = container


def reset_container():
    """Reset the default container to None, forcing recreation."""
    global _default_container
    if _default_container:
        _default_container.cleanup()
    _default_container = None
