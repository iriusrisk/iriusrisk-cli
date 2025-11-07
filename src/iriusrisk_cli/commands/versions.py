"""Versions command group for IriusRisk CLI."""

import click
import logging
from typing import Optional
from ..cli_context import pass_cli_context
from ..utils.project import resolve_project_id, get_project_context_info
from ..utils.output_formatters import format_and_print_list, format_and_print_detail
from ..utils.table import TableFormatter
from ..utils.error_handling import handle_cli_error

logger = logging.getLogger(__name__)


@click.group()
def versions():
    """Manage project versions.
    
    This command group provides functionality to list, create, and compare
    versions (snapshots) of your IriusRisk projects.
    """
    pass


@versions.command()
@click.argument('project_id', required=False)
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of versions per page', type=int)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False), 
              default='table', help='Output format')
@pass_cli_context
def list(cli_ctx, project_id: Optional[str], page: int, size: int, output_format: str):
    """List all versions for a project.
    
    This command retrieves and displays all version snapshots for a project.
    Versions are point-in-time snapshots that can be used for comparison,
    rollback, or creating new projects.
    
    Examples:
        # List versions for default project
        iriusrisk project versions list
        
        # List versions for specific project
        iriusrisk project versions list my-project-id
        
        # List with pagination
        iriusrisk project versions list --page 1 --size 10
        
        # Output as JSON
        iriusrisk project versions list --format json
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info("Starting project versions list operation")
        logger.debug(f"List parameters: project_id={project_id}, page={page}, size={size}, format={output_format}")
        
        # Resolve project ID from argument or default configuration
        resolved_project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {resolved_project_id}")
        
        # Show context information if using default project
        if not project_id:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        service = cli_ctx.get_service_factory().get_version_service()
        result = service.list_versions(
            project_id=resolved_project_id,
            page=page,
            size=size
        )
        
        versions_data = result['versions']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(versions_data)} versions from API")
        
        if not versions_data:
            logger.info("No versions found for this project")
            click.echo("No versions found for this project.")
            return
        
        total_elements = page_info.get('totalElements', len(versions_data))
        logger.info(f"Found {total_elements} version(s), displaying {len(versions_data)} on page {page}")
        
        # Format output using centralized formatter
        _format_versions_output(versions_data, output_format, page_info, full_response)
        
        logger.info("Project versions list operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "retrieving project versions")


@versions.command()
@click.argument('project_id', required=False)
@click.option('--name', '-n', required=True, help='Version name')
@click.option('--description', '-d', help='Version description')
@click.option('--no-wait', is_flag=True, help='Do not wait for version creation to complete')
@pass_cli_context
def create(cli_ctx, project_id: Optional[str], name: str, description: Optional[str], no_wait: bool):
    """Create a version snapshot of a project.
    
    This command creates a point-in-time snapshot of the current project state.
    Versions can be used for comparison, rollback, or creating new projects.
    
    By default, this command waits for the version creation to complete before
    returning. Use --no-wait to start the operation and return immediately.
    
    Examples:
        # Create version for default project
        iriusrisk project versions create --name "v1.0"
        
        # Create version with description
        iriusrisk project versions create --name "v1.0" --description "Release candidate"
        
        # Create version for specific project
        iriusrisk project versions create my-project-id --name "v1.0"
        
        # Start creation without waiting
        iriusrisk project versions create --name "v1.0" --no-wait
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
        name: Version name (required)
        description: Version description (optional)
        no_wait: Do not wait for completion
    """
    try:
        logger.info(f"Starting project version creation: '{name}'")
        logger.debug(f"Create parameters: project_id={project_id}, name={name}, description={description}, no_wait={no_wait}")
        
        # Resolve project ID from argument or default configuration
        resolved_project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {resolved_project_id}")
        
        # Show context information if using default project
        if not project_id:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        click.echo(f"Creating version '{name}'...")
        if not no_wait:
            click.echo("(This may take a moment...)")
        
        service = cli_ctx.get_service_factory().get_version_service()
        result = service.create_version(
            project_id=resolved_project_id,
            name=name,
            description=description,
            wait=not no_wait
        )
        
        if no_wait:
            operation_id = result.get('id', 'unknown')
            logger.info(f"Version creation initiated: operation {operation_id}")
            click.echo(f"✅ Version creation started")
            click.echo(f"   Operation ID: {operation_id}")
            click.echo(f"   Check status with: iriusrisk project versions list")
        else:
            version_id = result.get('id', 'unknown')
            logger.info(f"Version created successfully: {version_id}")
            click.echo(f"✅ Version '{name}' created successfully")
            if version_id != 'unknown':
                click.echo(f"   Version ID: {version_id}")
        
        logger.info("Project version creation operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "creating project version")


@versions.command()
@click.argument('project_id', required=False)
@click.option('--source', '-s', required=True, help='Source version ID')
@click.option('--target', '-t', required=True, help='Target version ID')
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', default=100, help='Number of changes per page', type=int)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False), 
              default='table', help='Output format')
@pass_cli_context
def compare(cli_ctx, project_id: Optional[str], source: str, target: str, 
           page: int, size: int, output_format: str):
    """Compare two project versions to see what changed.
    
    This command compares two version snapshots and shows what elements were
    added, edited, or removed between them. This helps track changes over time
    and understand the impact of modifications.
    
    Examples:
        # Compare two versions (requires version IDs from list command)
        iriusrisk project versions compare --source <version-id-1> --target <version-id-2>
        
        # Compare with pagination
        iriusrisk project versions compare -s <id-1> -t <id-2> --page 1 --size 50
        
        # Output as JSON
        iriusrisk project versions compare -s <id-1> -t <id-2> --format json
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
        source: Source version ID (UUID)
        target: Target version ID (UUID)
    """
    try:
        logger.info(f"Starting project version comparison: {source} -> {target}")
        logger.debug(f"Compare parameters: project_id={project_id}, source={source}, target={target}, page={page}, size={size}")
        
        # Resolve project ID from argument or default configuration
        resolved_project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {resolved_project_id}")
        
        # Show context information if using default project
        if not project_id:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        click.echo(f"Comparing versions:")
        click.echo(f"  Source: {source}")
        click.echo(f"  Target: {target}")
        click.echo()
        
        service = cli_ctx.get_service_factory().get_version_service()
        result = service.compare_versions(
            project_id=resolved_project_id,
            source_version_id=source,
            target_version_id=target,
            page=page,
            size=size
        )
        
        changes_data = result['changes']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(changes_data)} changes from API")
        
        if not changes_data:
            logger.info("No changes found between these versions")
            click.echo("No changes found between these versions.")
            return
        
        total_elements = page_info.get('totalElements', len(changes_data))
        logger.info(f"Found {total_elements} change(s), displaying {len(changes_data)} on page {page}")
        
        # Format output using centralized formatter
        _format_changes_output(changes_data, output_format, page_info, full_response)
        
        logger.info("Project version comparison operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "comparing project versions")


def _format_versions_output(versions_data: list, output_format: str, 
                            page_info: dict, full_response: dict):
    """Format and print versions output using centralized formatters."""
    
    # Define field mappings for versions
    field_mappings = [
        {'key': 'id'},  # No truncation - IDs needed for operations
        {'key': 'name'},
        {'key': 'description', 'truncate': 40},
        {'key': 'operation'},
        {'key': 'creationDate', 'formatter': lambda x: TableFormatter.format_timestamp(x, 'datetime')},
        {'key': 'creationUser'}
    ]
    
    # Create table headers
    table_headers = ['ID', 'Name', 'Description', 'Status', 'Created', 'Created By']
    
    # Create CSV headers
    csv_headers = ['id', 'name', 'description', 'operation', 'creationDate', 'creationUser']
    
    # Create transformers
    row_transformer = TableFormatter.create_row_transformer(field_mappings)
    csv_transformer = TableFormatter.create_csv_transformer(field_mappings)
    
    # Format and print output
    format_and_print_list(
        items=versions_data,
        output_format=output_format,
        table_headers=table_headers,
        csv_headers=csv_headers,
        row_transformer=row_transformer,
        csv_transformer=csv_transformer,
        title=None,
        page_info=page_info,
        full_response=full_response
    )


def _format_changes_output(changes_data: list, output_format: str, 
                           page_info: dict, full_response: dict):
    """Format and print version changes output using centralized formatters."""
    
    # Define field mappings for changes
    field_mappings = [
        {'key': 'elementType'},
        {'key': 'changeType'},
        {'key': 'elementName'},
        {'key': 'elementId'}  # No truncation - IDs needed for operations
    ]
    
    # Create table headers
    table_headers = ['Element Type', 'Change', 'Element Name', 'Element ID']
    
    # Create CSV headers
    csv_headers = ['elementType', 'changeType', 'elementName', 'elementId']
    
    # Create transformers
    row_transformer = TableFormatter.create_row_transformer(field_mappings)
    csv_transformer = TableFormatter.create_csv_transformer(field_mappings)
    
    # Format and print output
    format_and_print_list(
        items=changes_data,
        output_format=output_format,
        table_headers=table_headers,
        csv_headers=csv_headers,
        row_transformer=row_transformer,
        csv_transformer=csv_transformer,
        title=None,
        page_info=page_info,
        full_response=full_response
    )

