"""Project service for handling project-related business logic."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from ..repositories.project_repository import ProjectRepository
from ..repositories.threat_repository import ThreatRepository
from ..repositories.countermeasure_repository import CountermeasureRepository
from ..utils.project_resolution import resolve_project_id_to_uuid
from ..utils.error_handling import handle_api_error, IriusRiskError
from ..exceptions import ResourceNotFoundError, APIError

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing project operations."""
    
    def __init__(self, project_repository=None, threat_repository=None, countermeasure_repository=None):
        """Initialize the project service.
        
        Args:
            project_repository: ProjectRepository instance (required for dependency injection)
            threat_repository: ThreatRepository instance (required for stats generation)
            countermeasure_repository: CountermeasureRepository instance (required for stats generation)
        """
        if project_repository is None:
            raise ValueError("ProjectService requires a project_repository instance")
        if threat_repository is None:
            raise ValueError("ProjectService requires a threat_repository instance")
        if countermeasure_repository is None:
            raise ValueError("ProjectService requires a countermeasure_repository instance")
        
        self.project_repository = project_repository
        self.threat_repository = threat_repository
        self.countermeasure_repository = countermeasure_repository
    
    def list_projects(self, page: int = 0, size: int = 20, 
                     name: Optional[str] = None, tags: Optional[str] = None,
                     workflow_state: Optional[str] = None, archived: Optional[bool] = None,
                     blueprint: Optional[bool] = None, include_versions: bool = False,
                     custom_filter: Optional[str] = None) -> Dict[str, Any]:
        """List projects with filtering options.
        
        Args:
            page: Page number (0-based)
            size: Number of projects per page
            name: Filter by project name (partial match)
            tags: Filter by tags (space-separated)
            workflow_state: Filter by workflow state
            archived: Filter by archived status
            blueprint: Filter by blueprint status
            include_versions: Include version information
            custom_filter: Custom filter expression
            
        Returns:
            Dictionary containing projects data and pagination info
            
        Raises:
            IriusRiskError: If API request fails
        """
        operation = f"list projects (page {page + 1}, size {size})"
        context = {
            'page': page,
            'size': size,
            'filters': {
                'name': name,
                'tags': tags,
                'workflow_state': workflow_state,
                'archived': archived,
                'blueprint': blueprint,
                'include_versions': include_versions,
                'custom_filter': custom_filter
            }
        }
        
        logger.debug(f"Listing projects with filters: page={page}, size={size}, name={name}, "
                    f"tags={tags}, workflow_state={workflow_state}, archived={archived}, "
                    f"blueprint={blueprint}, include_versions={include_versions}")
        
        if custom_filter:
            logger.debug(f"Using custom filter: {custom_filter}")
        
        result = self.project_repository.list_all(
            page=page,
            size=size,
            name=name,
            tags=tags,
            workflow_state=workflow_state,
            archived=archived,
            blueprint=blueprint,
            include_versions=include_versions,
            custom_filter=custom_filter
        )
        
        projects_count = len(result.get('projects', []))
        total_count = result.get('totalElements', 0)
        logger.info(f"Retrieved {projects_count} projects (page {page + 1}, {total_count} total)")
        
        return result
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a specific project by ID or reference ID.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            Project data dictionary
            
        Raises:
            IriusRiskError: If project not found or API request fails
        """
        logger.debug(f"Retrieving project: {project_id}")
        
        result = self.project_repository.get_by_id(project_id)
        
        project_name = result.get('name', 'Unknown')
        project_uuid = result.get('id', project_id)
        logger.info(f"Retrieved project '{project_name}' (UUID: {project_uuid})")
        
        return result
    
    def search_projects(self, search_string: str, page: int = 0, size: int = 20,
                       include_versions: bool = False) -> Dict[str, Any]:
        """Search projects by name, ID, or description.
        
        Args:
            search_string: String to search for
            page: Page number (0-based)
            size: Number of projects per page
            include_versions: Include version information
            
        Returns:
            Dictionary containing search results and pagination info
            
        Raises:
            IriusRiskError: If search fails
        """
        logger.debug(f"Searching projects with query: '{search_string}' (page={page}, size={size})")
        
        result = self.project_repository.search(
            search_string=search_string,
            page=page,
            size=size,
            include_versions=include_versions
        )
        
        projects_count = len(result.get('projects', []))
        total_count = result.get('totalElements', 0)
        logger.info(f"Search returned {projects_count} projects (page {page + 1}, {total_count} total)")
        
        return result
    
    def get_project_diagram(self, project_id: str, size: str = 'ORIGINAL') -> Dict[str, Any]:
        """Get project diagram as base64 encoded image.
        
        Args:
            project_id: Project UUID or reference ID
            size: Image size ('ORIGINAL', 'PREVIEW', 'THUMBNAIL')
            
        Returns:
            Dictionary containing diagram data and metadata
            
        Raises:
            IriusRiskError: If diagram not found or API request fails
        """
        logger.info(f"Retrieving project diagram for '{project_id}' (size: {size})")
        
        try:
            # Resolve project ID to UUID for V2 API (upfront, no fallback mechanism)
            logger.debug(f"Resolving project ID to UUID: {project_id}")
            final_project_id = resolve_project_id_to_uuid(project_id, self.project_repository.api_client)
            logger.debug(f"Resolved to UUID: {final_project_id}")
            
            # Get artifacts with the resolved UUID
            artifacts_response = self.project_repository.get_artifacts(final_project_id, page=0, size=100)
            artifacts = artifacts_response.get('artifacts', [])
            logger.debug(f"Found {len(artifacts)} artifacts for project")
            
            if not artifacts:
                logger.error("No artifacts found for project")
                raise IriusRiskError("No artifacts found for this project. Make sure the project has been synchronized and contains a threat model.")
            
            # Find the diagram artifact (usually the first one, but let's be safe)
            diagram_artifact = None
            logger.debug("Searching for diagram artifact among available artifacts")
            for artifact in artifacts:
                # Look for artifacts that are likely diagrams (visible artifacts are usually diagrams)
                if artifact.get('visible', True):  # Assume visible artifacts are diagrams
                    diagram_artifact = artifact
                    logger.debug(f"Selected visible artifact: {artifact.get('name', 'unnamed')}")
                    break
            
            if not diagram_artifact:
                # If no visible artifacts, take the first one
                diagram_artifact = artifacts[0]
                logger.debug(f"No visible artifacts found, using first artifact: {diagram_artifact.get('name', 'unnamed')}")
            
            artifact_id = diagram_artifact.get('id')
            artifact_name = diagram_artifact.get('name', 'diagram')
            logger.debug(f"Retrieving content for artifact '{artifact_name}' (ID: {artifact_id})")
            
            # Get the artifact content (base64 encoded image)
            content_response = self.project_repository.get_artifact_content(artifact_id, size=size.upper())
            
            if not content_response.get('successfulGeneration', True):
                logger.warning("Artifact generation may not have been successful")
            
            # Extract base64 content
            base64_content = content_response.get('content')
            if not base64_content:
                logger.error("No image content found in artifact response")
                raise IriusRiskError("No image content found in artifact")
            
            content_size = len(base64_content)
            logger.info(f"Successfully retrieved diagram '{artifact_name}' ({content_size} bytes, size: {size})")
            
            return {
                'base64_content': base64_content,
                'artifact_name': artifact_name,
                'artifact_id': artifact_id,
                'project_id': final_project_id,
                'size': size
            }
            
        except IriusRiskError:
            raise
        except Exception as e:
            raise handle_api_error(e, f"downloading diagram for project '{project_id}'")
    
    def generate_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Generate comprehensive project statistics.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            Dictionary containing project statistics
            
        Raises:
            IriusRiskError: If stats generation fails
        """
        logger.info(f"Generating project statistics for: {project_id}")
        
        try:
            # Resolve project ID to UUID for V2 API
            logger.debug(f"Resolving project ID to UUID: {project_id}")
            final_project_id = resolve_project_id_to_uuid(project_id, self.project_repository.api_client)
            logger.debug(f"Resolved to UUID: {final_project_id}")
            
            # Get project details for metadata
            project_name = 'Unknown'
            try:
                logger.debug("Retrieving project metadata")
                project_data = self.project_repository.get_by_id(final_project_id)
                project_name = project_data.get('name', 'Unknown')
                logger.debug(f"Found project: '{project_name}'")
            except (ResourceNotFoundError, APIError) as e:
                # If project metadata retrieval fails, continue with 'Unknown' name
                logger.warning(f"Could not retrieve project metadata: {e}. Using 'Unknown' for project name.")
                project_name = 'Unknown'
            
            # Collect threats data
            logger.debug("Retrieving threats data for statistics")
            threats_response = self.threat_repository.list_all(
                project_id=final_project_id,
                page=0,
                size=1000  # Get all threats
            )
            threats_data = threats_response.get('threats', [])
            logger.debug(f"Retrieved {len(threats_data)} threats")
            
            # Collect countermeasures data
            logger.debug("Retrieving countermeasures data for statistics")
            countermeasures_response = self.countermeasure_repository.list_all(
                project_id=final_project_id,
                page=0,
                size=1000  # Get all countermeasures
            )
            countermeasures_data = countermeasures_response.get('countermeasures', [])
            logger.debug(f"Retrieved {len(countermeasures_data)} countermeasures")
            
            # Generate statistics
            logger.debug("Processing statistics data")
            stats = self._generate_stats_data(
                project_id=final_project_id,
                project_name=project_name,
                threats_data=threats_data,
                countermeasures_data=countermeasures_data
            )
            
            logger.info(f"Generated statistics for project '{project_name}': "
                       f"{len(threats_data)} threats, {len(countermeasures_data)} countermeasures")
            
            return stats
            
        except IriusRiskError:
            raise
        except Exception as e:
            raise handle_api_error(e, f"generating project statistics for '{project_id}'")
    
    
    def _categorize_risk_level(self, risk_score: int) -> str:
        """Categorize numerical risk score into risk level."""
        if risk_score >= 80:
            return 'critical'
        elif risk_score >= 60:
            return 'high'
        elif risk_score >= 40:
            return 'medium'
        elif risk_score >= 20:
            return 'low'
        else:
            return 'very-low'
    
    def _generate_stats_data(self, project_id: str, project_name: str, 
                           threats_data: List[Dict], countermeasures_data: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive project statistics."""
        logger.debug(f"Generating statistics for {len(threats_data)} threats and {len(countermeasures_data)} countermeasures")
        
        # Initialize stats structure
        stats = {
            "metadata": {
                "project_id": project_id,
                "project_name": project_name,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            "threats": {
                "total": len(threats_data),
                "by_state": {},
                "by_risk_level": {},
                "by_state_and_risk": {}
            },
            "countermeasures": {
                "total": len(countermeasures_data),
                "by_state": {},
                "by_priority": {},
                "by_state_and_priority": {}
            }
        }
        
        # Define possible values based on actual IriusRisk API source code
        threat_states = ['expose', 'accept', 'partly-mitigate', 'mitigate', 'not-applicable', 'hidden']
        risk_levels = ['very-low', 'low', 'medium', 'high', 'critical']
        countermeasure_states = ['not-applicable', 'rejected', 'recommended', 'required', 'implemented']
        priorities = ['low', 'medium', 'high', 'very-high']
        
        # Initialize counters
        for state in threat_states:
            stats["threats"]["by_state"][state] = 0
        for level in risk_levels:
            stats["threats"]["by_risk_level"][level] = 0
            stats["threats"]["by_state_and_risk"][level] = {}
            for state in threat_states:
                stats["threats"]["by_state_and_risk"][level][state] = 0
        
        for state in countermeasure_states:
            stats["countermeasures"]["by_state"][state] = 0
        for priority in priorities:
            stats["countermeasures"]["by_priority"][priority] = 0
            stats["countermeasures"]["by_state_and_priority"][priority] = {}
            for state in countermeasure_states:
                stats["countermeasures"]["by_state_and_priority"][priority][state] = 0
        
        # Process threats data
        for threat in threats_data:
            state = threat.get('state', 'expose')
            risk_score = threat.get('risk', 0)
            risk_level = self._categorize_risk_level(risk_score)
            
            # Count by state
            if state in stats["threats"]["by_state"]:
                stats["threats"]["by_state"][state] += 1
            
            # Count by risk level
            stats["threats"]["by_risk_level"][risk_level] += 1
            
            # Count by state and risk combination
            stats["threats"]["by_state_and_risk"][risk_level][state] += 1
        
        # Process countermeasures data
        logger.debug("Processing countermeasures data for statistics")
        for countermeasure in countermeasures_data:
            state = countermeasure.get('state', 'required')
            priority_obj = countermeasure.get('priority', {})
            priority = priority_obj.get('calculated', 'medium') if isinstance(priority_obj, dict) else 'medium'
            
            # Count by state
            if state in stats["countermeasures"]["by_state"]:
                stats["countermeasures"]["by_state"][state] += 1
            
            # Count by priority
            if priority in stats["countermeasures"]["by_priority"]:
                stats["countermeasures"]["by_priority"][priority] += 1
            
            # Count by state and priority combination
            if priority in stats["countermeasures"]["by_state_and_priority"]:
                if state in stats["countermeasures"]["by_state_and_priority"][priority]:
                    stats["countermeasures"]["by_state_and_priority"][priority][state] += 1
        
        # Log summary of generated statistics
        threat_summary = ", ".join([f"{state}: {count}" for state, count in stats["threats"]["by_state"].items() if count > 0])
        countermeasure_summary = ", ".join([f"{state}: {count}" for state, count in stats["countermeasures"]["by_state"].items() if count > 0])
        logger.debug(f"Threat breakdown: {threat_summary}")
        logger.debug(f"Countermeasure breakdown: {countermeasure_summary}")
        
        return stats



