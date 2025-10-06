"""Reports command for generating and downloading IriusRisk reports."""

import click
import logging
from pathlib import Path
from typing import Optional

from ..cli_context import pass_cli_context
from ..utils.project import resolve_project_id
from ..utils.error_handling import handle_cli_error

logger = logging.getLogger(__name__)


# Report constants moved to ReportService




@click.group()
def reports():
    """Generate and download IriusRisk reports."""
    pass


@reports.command()
@click.option('--project-id', help='Project ID (uses current project if not specified)')
@click.option('--type', 'report_type', 
              type=click.Choice(['countermeasure', 'threat', 'compliance', 'risk-summary']),
              default='countermeasure',
              help='Type of report to generate')
@click.option('--format', 'report_format',
              type=click.Choice(['pdf', 'html', 'xlsx', 'csv', 'xls']),
              default='pdf',
              help='Output format for the report')
@click.option('--output', '-o', 
              help='Output file path (auto-generated if not specified)')
@click.option('--timeout', default=300,
              help='Timeout in seconds for report generation (default: 300)')
@click.option('--standard', 
              help='Standard UUID or reference ID for compliance reports (required for compliance reports)')
@pass_cli_context
def generate(cli_ctx, project_id: Optional[str], report_type: str, report_format: str, 
             output: Optional[str], timeout: int, standard: Optional[str]):
    """Generate and download a report."""
    
    try:
        logger.info("Starting report generation operation")
        logger.debug(f"Generate parameters: project_id={project_id}, report_type={report_type}, "
                    f"report_format={report_format}, output={output}, timeout={timeout}, standard={standard}")
        
        # Get project ID
        project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {project_id}")
        
        service = cli_ctx.get_service_factory().get_report_service()
        
        logger.info(f"Generating {report_type} report in {report_format} format")
        result = service.generate_report(
            project_id=project_id,
            report_type=report_type,
            report_format=report_format,
            output=output,
            timeout=timeout,
            standard=standard
        )
        
        click.echo(f"Generating {report_type} report in {report_format} format...")
        if result.get('standard'):
            logger.info(f"Using standard: {result['standard']}")
            click.echo(f"Using standard: {result['standard']}")
        
        logger.info("Report generation completed successfully")
        click.echo("Report generation completed!")
        
        output_path = result['output_path']
        content_size = result['content_size']
        logger.info(f"Downloading report to: {output_path}")
        click.echo(f"Downloading report to {output_path}...")
        
        logger.info(f"Report successfully saved: {content_size:,} bytes")
        click.echo(f"Report successfully saved to {output_path}")
        click.echo(f"Report size: {content_size:,} bytes")
        
    except Exception as e:
        handle_cli_error(e, "generating report")


@reports.command()
@click.option('--project-id', help='Project ID (uses current project if not specified)')
@pass_cli_context
def types(cli_ctx, project_id: Optional[str]):
    """List available report types for a project."""
    
    try:
        logger.info("Starting report types list operation")
        logger.debug(f"Types parameters: project_id={project_id}")
        
        # Get project ID
        project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {project_id}")
        
        service = cli_ctx.get_service_factory().get_report_service()
        report_types = service.list_report_types(project_id)
        
        logger.info(f"Retrieved {len(report_types)} report types")
        click.echo("Available report types:")
        for report_type in report_types:
            name = report_type.get('name', 'Unknown')
            report_id = report_type.get('id', 'Unknown')
            formats = ', '.join(report_type.get('formatsAllowed', []))
            logger.debug(f"Report type: {name} (id: {report_id}), formats: {formats}")
            click.echo(f"  {name} (id: {report_id})")
            click.echo(f"    Formats: {formats}")
        
        logger.info("Report types list operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "retrieving report types")


@reports.command()
@click.option('--project-id', help='Project ID (uses current project if not specified)')
@pass_cli_context
def standards(cli_ctx, project_id: Optional[str]):
    """List available standards for compliance reports."""
    
    try:
        logger.info("Starting standards list operation")
        logger.debug(f"Standards parameters: project_id={project_id}")
        
        # Get project ID
        project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {project_id}")
        
        service = cli_ctx.get_service_factory().get_report_service()
        standards = service.list_standards(project_id)
        
        logger.info(f"Retrieved {len(standards)} standards")
        
        if not standards:
            logger.info("No standards found for this project")
            click.echo("No standards found for this project.")
            return
        
        click.echo("Available standards for compliance reports:")
        for standard in standards:
            name = standard.get('name', 'Unknown')
            reference_id = standard.get('referenceId', 'Unknown')
            standard_id = standard.get('id', 'Unknown')
            
            logger.debug(f"Standard: {name} (ref: {reference_id}, id: {standard_id})")
            click.echo(f"  {name}")
            click.echo(f"    Reference ID: {reference_id}")
            click.echo(f"    UUID: {standard_id}")
            click.echo()
        
        logger.info("Standards list operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "retrieving standards")


@reports.command()
@click.option('--project-id', help='Project ID (uses current project if not specified)')
@pass_cli_context
def list(cli_ctx, project_id: Optional[str]):
    """List generated reports for a project."""
    
    try:
        logger.info("Starting reports list operation")
        logger.debug(f"List parameters: project_id={project_id}")
        
        # Get project ID
        project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {project_id}")
        
        service = cli_ctx.get_service_factory().get_report_service()
        reports = service.list_reports(project_id)
        
        logger.info(f"Retrieved {len(reports)} reports")
        
        if not reports:
            logger.info("No reports found for this project")
            click.echo("No reports found for this project.")
            return
        
        click.echo("Generated reports:")
        for report in reports:
            name = report.get('name', 'Unknown')
            report_format = report.get('format', 'Unknown')
            date = report.get('date', 'Unknown')
            report_id = report.get('id', 'Unknown')
            
            logger.debug(f"Report: {name} ({report_format}) - {date} (id: {report_id})")
            click.echo(f"  {name} ({report_format}) - {date}")
            click.echo(f"    ID: {report_id}")
        
        logger.info("Reports list operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "retrieving reports")
