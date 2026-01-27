"""Verification manager for CI/CD drift detection workflows.

This module provides a context manager for safely downloading, comparing, and cleaning
up threat model artifacts during verification workflows.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class VerificationManager:
    """Manager for verification workspace and file operations."""
    
    def __init__(self, project_path: str, project_client, threat_client, countermeasure_client):
        """Initialize verification manager.
        
        Args:
            project_path: Path to project directory (where .iriusrisk/ is located)
            project_client: ProjectApiClient instance
            threat_client: ThreatApiClient instance
            countermeasure_client: CountermeasureApiClient instance
        """
        self.project_path = Path(project_path)
        self.verification_dir = self.project_path / '.iriusrisk' / 'verification'
        
        self.project_client = project_client
        self.threat_client = threat_client
        self.countermeasure_client = countermeasure_client
        
        self._temp_files = []
        
    def __enter__(self):
        """Context manager entry - create verification directory."""
        self.verification_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created verification workspace: {self.verification_dir}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all temporary files."""
        self.cleanup()
        return False
    
    def download_baseline_state(self, project_id: str, version_id: Optional[str] = None) -> Tuple[str, str, str]:
        """Download baseline state (diagram, threats, countermeasures).
        
        Args:
            project_id: Project UUID
            version_id: Optional version UUID (if None, uses current project state)
            
        Returns:
            Tuple of (diagram_path, threats_path, countermeasures_path)
        """
        prefix = "baseline"
        logger.info(f"Downloading baseline state for project {project_id}" + 
                   (f", version {version_id}" if version_id else " (current)"))
        
        # Download diagram
        if version_id:
            diagram_xml = self.project_client.get_diagram_content_version(project_id, version_id)
        else:
            diagram_xml = self.project_client.get_diagram_content(project_id)
        
        diagram_path = self.verification_dir / f"{prefix}-diagram.xml"
        diagram_path.write_text(diagram_xml, encoding='utf-8')
        self._temp_files.append(diagram_path)
        logger.info(f"Saved baseline diagram: {diagram_path} ({len(diagram_xml)} bytes)")
        
        # Download threats
        if version_id:
            threats_data = self.threat_client.get_threats_version(project_id, version_id, page=0, size=1000)
        else:
            threats_data = self.threat_client.get_threats(project_id, page=0, size=1000)
        
        threats_path = self.verification_dir / f"{prefix}-threats.json"
        threats_path.write_text(json.dumps(threats_data, indent=2), encoding='utf-8')
        self._temp_files.append(threats_path)
        threat_count = len(threats_data.get('_embedded', {}).get('threats', []))
        logger.info(f"Saved baseline threats: {threats_path} ({threat_count} threats)")
        
        # Download countermeasures
        if version_id:
            cm_data = self.countermeasure_client.get_countermeasures_version(project_id, version_id, page=0, size=1000)
        else:
            cm_data = self.countermeasure_client.get_countermeasures(project_id, page=0, size=1000)
        
        cm_path = self.verification_dir / f"{prefix}-countermeasures.json"
        cm_path.write_text(json.dumps(cm_data, indent=2), encoding='utf-8')
        self._temp_files.append(cm_path)
        cm_count = len(cm_data.get('_embedded', {}).get('countermeasures', []))
        logger.info(f"Saved baseline countermeasures: {cm_path} ({cm_count} countermeasures)")
        
        return str(diagram_path), str(threats_path), str(cm_path)
    
    def download_target_state(self, project_id: str, version_id: Optional[str] = None) -> Tuple[str, str, str]:
        """Download target state (diagram, threats, countermeasures).
        
        Args:
            project_id: Project UUID
            version_id: Optional version UUID (if None, uses current project state)
            
        Returns:
            Tuple of (diagram_path, threats_path, countermeasures_path)
        """
        prefix = "verification"
        logger.info(f"Downloading target state for project {project_id}" +
                   (f", version {version_id}" if version_id else " (current)"))
        
        # Download diagram
        if version_id:
            diagram_xml = self.project_client.get_diagram_content_version(project_id, version_id)
        else:
            diagram_xml = self.project_client.get_diagram_content(project_id)
        
        diagram_path = self.verification_dir / f"{prefix}-diagram.xml"
        diagram_path.write_text(diagram_xml, encoding='utf-8')
        self._temp_files.append(diagram_path)
        logger.info(f"Saved target diagram: {diagram_path} ({len(diagram_xml)} bytes)")
        
        # Download threats
        if version_id:
            threats_data = self.threat_client.get_threats_version(project_id, version_id, page=0, size=1000)
        else:
            threats_data = self.threat_client.get_threats(project_id, page=0, size=1000)
        
        threats_path = self.verification_dir / f"{prefix}-threats.json"
        threats_path.write_text(json.dumps(threats_data, indent=2), encoding='utf-8')
        self._temp_files.append(threats_path)
        threat_count = len(threats_data.get('_embedded', {}).get('threats', []))
        logger.info(f"Saved target threats: {threats_path} ({threat_count} threats)")
        
        # Download countermeasures
        if version_id:
            cm_data = self.countermeasure_client.get_countermeasures_version(project_id, version_id, page=0, size=1000)
        else:
            cm_data = self.countermeasure_client.get_countermeasures(project_id, page=0, size=1000)
        
        cm_path = self.verification_dir / f"{prefix}-countermeasures.json"
        cm_path.write_text(json.dumps(cm_data, indent=2), encoding='utf-8')
        self._temp_files.append(cm_path)
        cm_count = len(cm_data.get('_embedded', {}).get('countermeasures', []))
        logger.info(f"Saved target countermeasures: {cm_path} ({cm_count} countermeasures)")
        
        return str(diagram_path), str(threats_path), str(cm_path)
    
    def cleanup(self):
        """Clean up all temporary files in the verification directory."""
        logger.info("Cleaning up verification workspace...")
        
        for file_path in self._temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
        
        # Try to remove the verification directory if empty
        try:
            if self.verification_dir.exists() and not any(self.verification_dir.iterdir()):
                self.verification_dir.rmdir()
                logger.info("Removed empty verification directory")
        except Exception as e:
            logger.debug(f"Could not remove verification directory: {e}")
        
        self._temp_files.clear()
        logger.info("Cleanup complete")


@contextmanager
def verification_context(project_path: str, project_client, threat_client, countermeasure_client):
    """Context manager for verification workflows.
    
    Usage:
        with verification_context(project_path, clients...) as manager:
            baseline_files = manager.download_baseline_state(project_id, version_id)
            target_files = manager.download_target_state(project_id)
            # ... perform comparison ...
        # Automatic cleanup happens here
    
    Args:
        project_path: Path to project directory
        project_client: ProjectApiClient instance
        threat_client: ThreatApiClient instance
        countermeasure_client: CountermeasureApiClient instance
        
    Yields:
        VerificationManager instance
    """
    manager = VerificationManager(project_path, project_client, threat_client, countermeasure_client)
    try:
        yield manager.__enter__()
    finally:
        manager.__exit__(None, None, None)
