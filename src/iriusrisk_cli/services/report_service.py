"""Report service for handling report generation business logic."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

from ..repositories.report_repository import ReportRepository
from ..utils.project_resolution import resolve_project_id_to_uuid
from ..utils.error_handling import handle_api_error, IriusRiskError

logger = logging.getLogger(__name__)


class ReportService:
    """Service for managing report operations."""
    
    # Report type mappings
    REPORT_TYPES = {
        'countermeasure': 'technical-countermeasure-report',
        'threat': 'technical-threat-report', 
        'compliance': 'compliance-report',
        'risk-summary': 'residual-risk'
    }
    
    SUPPORTED_FORMATS = ['pdf', 'html', 'xlsx', 'csv', 'xls']
    
    def __init__(self, report_repository=None):
        """Initialize the report service.
        
        Args:
            report_repository: ReportRepository instance (required for dependency injection)
        """
        if report_repository is None:
            raise ValueError("ReportService requires a report_repository instance")
        self.report_repository = report_repository
    
    def generate_report(self, project_id: str, report_type: str, report_format: str = 'pdf',
                       output: Optional[str] = None, timeout: int = 300,
                       standard: Optional[str] = None) -> Dict[str, Any]:
        """Generate and download a report.
        
        Args:
            project_id: Project UUID or reference ID
            report_type: Type of report ('countermeasure', 'threat', 'compliance', 'risk-summary')
            report_format: Output format ('pdf', 'html', 'xlsx', 'csv', 'xls')
            output: Output file path (auto-generated if not specified)
            timeout: Timeout in seconds for report generation
            standard: Standard UUID or reference ID for compliance reports
            
        Returns:
            Dictionary containing report generation result
            
        Raises:
            IriusRiskError: If report generation fails
        """
        logger.info(f"Generating {report_type} report for project '{project_id}' in {report_format} format")
        
        try:
            # Validate report type and format
            logger.debug(f"Validating report type '{report_type}' and format '{report_format}'")
            if report_type not in self.REPORT_TYPES:
                logger.error(f"Invalid report type: {report_type}")
                raise IriusRiskError(f"Invalid report type '{report_type}'. Supported types: {list(self.REPORT_TYPES.keys())}")
            
            if report_format not in self.SUPPORTED_FORMATS:
                logger.error(f"Invalid report format: {report_format}")
                raise IriusRiskError(f"Invalid report format '{report_format}'. Supported formats: {self.SUPPORTED_FORMATS}")
            
            # Convert reference ID to UUID if needed
            logger.debug(f"Resolving project ID to UUID: {project_id}")
            project_uuid = resolve_project_id_to_uuid(project_id, self.report_repository.api_client)
            logger.debug(f"Resolved to UUID: {project_uuid}")
            
            # Generate output filename if not specified
            if not output:
                output = f"{report_type}_report.{report_format}"
                logger.debug(f"Auto-generated output filename: {output}")
            
            output_path = Path(output)
            logger.debug(f"Output path: {output_path.absolute()}")
            
            # Handle compliance reports that require a standard
            standard_uuid = None
            if report_type == 'compliance':
                if not standard:
                    logger.error("Compliance report requested but no standard specified")
                    raise IriusRiskError("Compliance reports require a --standard parameter")
                
                logger.debug(f"Resolving compliance standard: {standard}")
                standard_uuid = self.report_repository.resolve_standard_id(project_uuid, standard)
                logger.debug(f"Resolved standard to UUID: {standard_uuid}")
            
            # Generate the report
            logger.debug(f"Initiating report generation: type={self.REPORT_TYPES[report_type]}, format={report_format}")
            operation_id = self.report_repository.generate_report(
                project_id=project_uuid,
                report_type=self.REPORT_TYPES[report_type],
                report_format=report_format,
                standard=standard_uuid
            )
            logger.info(f"Report generation started (operation ID: {operation_id})")
            
            # Wait for completion
            logger.debug(f"Waiting for report generation to complete (timeout: {timeout}s)")
            self.report_repository.wait_for_completion(operation_id, timeout)
            logger.debug("Report generation completed")
            
            # Find the generated report
            logger.debug("Locating generated report in project reports")
            target_report = self.report_repository.find_report_by_type_and_format(
                project_id=project_uuid,
                report_type=self.REPORT_TYPES[report_type],
                report_format=report_format
            )
            
            if not target_report:
                logger.error("Generated report not found in project reports")
                raise IriusRiskError("Generated report not found in project reports")
            
            report_name = target_report.get('name', 'Unknown')
            logger.debug(f"Found generated report: {report_name}")
            
            # Get download URL from the report links
            download_url = target_report.get('_links', {}).get('download', {}).get('href')
            if not download_url:
                logger.error("No download link found for the report")
                raise IriusRiskError("No download link found for the report")
            
            logger.debug(f"Downloading report content from: {download_url}")
            
            # Download the report
            content = self.report_repository.download_report_content(download_url)
            content_size = len(content)
            logger.debug(f"Downloaded {content_size} bytes of report content")
            
            # Save to file
            logger.debug(f"Saving report to file: {output_path}")
            output_path.write_bytes(content)
            logger.info(f"Report saved successfully: {output_path} ({content_size} bytes)")
            
            return {
                'output_path': output_path,
                'content_size': len(content),
                'report_type': report_type,
                'format': report_format,
                'operation_id': operation_id,
                'standard': standard if standard_uuid else None
            }
            
        except IriusRiskError:
            raise
        except Exception as e:
            raise handle_api_error(e, f"generating {report_type} report")
    
    def list_report_types(self, project_id: str) -> List[Dict[str, Any]]:
        """List available report types for a project.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            List of available report types
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving available report types for project '{project_id}'")
        
        try:
            # Convert reference ID to UUID if needed
            project_uuid = resolve_project_id_to_uuid(project_id, self.report_repository.api_client)
            logger.debug(f"Resolved project to UUID: {project_uuid}")
            
            response = self.report_repository.get_report_types(project_uuid)
            report_types = response.get('report_types', [])
            
            logger.info(f"Retrieved {len(report_types)} available report types for project")
            
            return report_types
            
        except Exception as e:
            raise handle_api_error(e, f"retrieving report types for project '{project_id}'")
    
    def list_standards(self, project_id: str) -> List[Dict[str, Any]]:
        """List available standards for compliance reports.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            List of available standards
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving available compliance standards for project '{project_id}'")
        
        try:
            # Convert reference ID to UUID if needed
            project_uuid = resolve_project_id_to_uuid(project_id, self.report_repository.api_client)
            logger.debug(f"Resolved project to UUID: {project_uuid}")
            
            response = self.report_repository.get_standards(project_uuid)
            standards = response.get('standards', [])
            
            logger.info(f"Retrieved {len(standards)} available compliance standards for project")
            
            return standards
            
        except Exception as e:
            raise handle_api_error(e, f"retrieving standards for project '{project_id}'")
    
    def list_reports(self, project_id: str) -> List[Dict[str, Any]]:
        """List generated reports for a project.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            List of generated reports
            
        Raises:
            IriusRiskError: If API request fails
        """
        logger.debug(f"Retrieving generated reports for project '{project_id}'")
        
        try:
            # Convert reference ID to UUID if needed
            project_uuid = resolve_project_id_to_uuid(project_id, self.report_repository.api_client)
            logger.debug(f"Resolved project to UUID: {project_uuid}")
            
            response = self.report_repository.list_all(project_uuid)
            reports = response.get('reports', [])
            
            logger.info(f"Retrieved {len(reports)} generated reports for project")
            
            return reports
            
        except Exception as e:
            raise handle_api_error(e, f"retrieving reports for project '{project_id}'")
    



