"""Projects command group for IriusRisk CLI."""

import click
import json
import base64
import logging
from pathlib import Path
from typing import Optional
from ..cli_context import pass_cli_context
from ..utils.table import print_projects_table, print_project_details, TableFormatter
from ..utils.project import resolve_project_id, get_project_context_info
from ..utils.output_formatters import format_and_print_list, format_and_print_detail
from ..utils.error_handling import handle_cli_error

logger = logging.getLogger(__name__)


@click.group()
def project():
    """Manage IriusRisk projects.
    
    This command group provides functionality to list, fetch, and manage
    projects in your IriusRisk instance.
    """
    pass


# Filter expression building moved to ProjectService


@project.command()
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of projects per page', type=int)
@click.option('--name', '-n', help='Filter by project name (partial match)')
@click.option('--tags', '-t', help='Filter by tags (space-separated)')
@click.option('--workflow-state', '-w', help='Filter by workflow state')
@click.option('--archived/--not-archived', default=None, help='Filter by archived status')
@click.option('--blueprint/--not-blueprint', default=None, help='Filter by blueprint status')
@click.option('--include-versions', is_flag=True, help='Include version information')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False), 
              default='table', help='Output format')
@click.option('--filter', 'custom_filter', help='Custom filter expression (advanced)')
@pass_cli_context
def list(cli_ctx, page: int, size: int, name: Optional[str], tags: Optional[str], 
         workflow_state: Optional[str], archived: Optional[bool], 
         blueprint: Optional[bool], include_versions: bool, 
         output_format: str, custom_filter: Optional[str]):
    """List projects from IriusRisk.
    
    This command retrieves and displays projects from your IriusRisk instance
    with various filtering and formatting options.
    
    Examples:
        # List all projects
        iriusrisk project list
        
        # List first 10 projects
        iriusrisk project list --size 10
        
        # Filter by name
        iriusrisk project list --name "web app"
        
        # Filter by tags
        iriusrisk project list --tags "production critical"
        
        # Filter by workflow state
        iriusrisk project list --workflow-state "in-progress"
        
        # Show only non-archived projects
        iriusrisk project list --not-archived
        
        # Output as JSON
        iriusrisk project list --format json
        
        # Advanced filtering
        iriusrisk project list --filter "'name'~'web':AND:'tags'~'prod'"
    """
    try:
        logger.info("Starting project list operation")
        logger.debug(f"List parameters: page={page}, size={size}, name={name}, tags={tags}, "
                    f"workflow_state={workflow_state}, archived={archived}, blueprint={blueprint}, "
                    f"include_versions={include_versions}, custom_filter={custom_filter}, format={output_format}")
        
        service = cli_ctx.get_service_factory().get_project_service()
        result = service.list_projects(
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
        
        projects_data = result['projects']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(projects_data)} projects from API")
        
        if not projects_data:
            logger.info("No projects found matching the criteria")
            click.echo("No projects found matching the criteria.")
            return
        
        total_elements = page_info.get('totalElements', len(projects_data))
        logger.info(f"Found {total_elements} project(s) matching criteria, displaying {len(projects_data)} on page {page}")
        
        # Format output using centralized formatter
        _format_projects_output(projects_data, output_format, include_versions, page_info, full_response)
        
        logger.info("Project list operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "retrieving projects")




@project.command()
@click.argument('project_id', required=False)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json'], case_sensitive=False), 
              default='table', help='Output format')
@pass_cli_context
def show(cli_ctx, project_id: Optional[str], output_format: str):
    """Show detailed information for a specific project.
    
    This command retrieves and displays detailed metadata for a single project
    by its ID or reference ID. If no project ID is provided, it will use the
    default project from the local configuration.
    
    Examples:
        # Show default project (if configured)
        iriusrisk project show
        
        # Show project by UUID
        iriusrisk project show 3fa85f64-5717-4562-b3fc-2c963f66afa6
        
        # Show project by reference ID
        iriusrisk project show my-project-ref
        
        # Output as JSON
        iriusrisk project show my-project --format json
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info("Starting project show operation")
        logger.debug(f"Show parameters: project_id={project_id}, format={output_format}")
        
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
        
        service = cli_ctx.get_service_factory().get_project_service()
        project_data = service.get_project(resolved_project_id)
        
        project_name = project_data.get('name', 'N/A')
        logger.info(f"Retrieved project data for: {project_name}")
        
        # Show found message if we searched by reference ID
        if not project_id or len(resolved_project_id) != 36:
            click.echo(f"Found project: {project_name}")
        
        # Format output using centralized formatter
        format_and_print_detail(project_data, output_format, print_project_details)
        
        logger.info("Project show operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, f"retrieving project '{resolved_project_id}'" if 'resolved_project_id' in locals() else "retrieving project")


@project.command()
@click.argument('search_string')
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of projects per page', type=int)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False), 
              default='table', help='Output format')
@click.option('--include-versions', is_flag=True, help='Include version information')
@pass_cli_context
def search(cli_ctx, search_string: str, page: int, size: int, output_format: str, include_versions: bool):
    """Search projects by name, ID, or description.
    
    This command performs a comprehensive search across project names, reference IDs,
    and descriptions using server-side filtering for optimal performance.
    
    Examples:
        # Search for projects containing "web"
        iriusrisk project search "web"
        
        # Search with pagination
        iriusrisk project search "api" --page 1 --size 10
        
        # Output as JSON
        iriusrisk project search "mobile" --format json
        
        # Include version information
        iriusrisk project search "app" --include-versions
    
    Args:
        search_string: String to search for in project names, IDs, and descriptions
    """
    try:
        logger.info(f"Starting project search operation for: '{search_string}'")
        logger.debug(f"Search parameters: search_string='{search_string}', page={page}, size={size}, "
                    f"include_versions={include_versions}, format={output_format}")
        
        service = cli_ctx.get_service_factory().get_project_service()
        result = service.search_projects(
            search_string=search_string,
            page=page,
            size=size,
            include_versions=include_versions
        )
        
        projects_data = result['projects']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(projects_data)} projects from search")
        
        click.echo(f"Searching projects for: '{search_string}'")
        click.echo()
        
        if not projects_data:
            logger.info(f"No projects found matching search term: '{search_string}'")
            click.echo(f"No projects found matching '{search_string}'.")
            return
        
        # Show search results summary
        total_elements = page_info.get('totalElements', len(projects_data))
        logger.info(f"Found {total_elements} project(s) matching '{search_string}', displaying {len(projects_data)} on page {page}")
        click.echo(f"Found {total_elements} project(s) matching '{search_string}':")
        click.echo()
        
        # Format output using centralized formatter
        _format_projects_output(projects_data, output_format, include_versions, page_info, full_response)
        
        logger.info("Project search operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, f"searching projects for '{search_string}'")


@project.command()
@click.argument('project_id', required=False)
@click.option('--size', '-s', 
              type=click.Choice(['ORIGINAL', 'PREVIEW', 'THUMBNAIL'], case_sensitive=False),
              default='ORIGINAL', help='Image size to download')
@click.option('--output', '-o', help='Output file path (default: project-diagram.png)')
@pass_cli_context
def diagram(cli_ctx, project_id: Optional[str], size: str, output: Optional[str]):
    """Download the project diagram as an image.
    
    This command downloads the project's threat model diagram as a PNG image.
    The diagram is automatically generated when the project is synchronized.
    
    Examples:
        # Download diagram for default project
        iriusrisk project diagram
        
        # Download diagram for specific project
        iriusrisk project diagram my-project-id
        
        # Download thumbnail size
        iriusrisk project diagram --size THUMBNAIL
        
        # Save to specific file
        iriusrisk project diagram --output my-diagram.png
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info("Starting project diagram download operation")
        logger.debug(f"Diagram parameters: project_id={project_id}, size={size}, output={output}")
        
        # Resolve project ID from argument or default configuration
        if project_id:
            resolved_project_id = project_id
            logger.debug(f"Using provided project ID: {project_id}")
        else:
            logger.debug("No project ID provided, attempting to resolve from configuration")
            # Try to get project ID from project.json first
            project_json_path = Path.cwd() / '.iriusrisk' / 'project.json'
            resolved_project_id = None
            
            if project_json_path.exists():
                logger.debug("Found project.json, attempting to read project configuration")
                try:
                    with open(project_json_path, 'r') as f:
                        project_config = json.load(f)
                    resolved_project_id = project_config.get('project_id')
                    if not project_id:  # Show context if using default
                        project_name = project_config.get('name', 'Unknown')
                        logger.info(f"Using project from project.json: {project_name}")
                        click.echo(f"Using project from project.json: {project_name}")
                        click.echo()
                except Exception as e:
                    logger.debug(f"Failed to read project.json: {e}")
                    pass
            
            # Fall back to config if no project.json
            if not resolved_project_id:
                logger.debug("No project.json found, falling back to global configuration")
                from ..config import Config
                config = Config()
                resolved_project_id = config.get_default_project_id()
                if resolved_project_id and not project_id:
                    project_name = get_project_context_info()
                    if project_name:
                        logger.info(f"Using default project: {project_name}")
                        click.echo(f"Using default project: {project_name}")
                    click.echo()
            
            if not resolved_project_id:
                logger.error("No project ID could be resolved from arguments or configuration")
                click.echo("❌ No project ID provided and no default project configured.", err=True)
                click.echo("Use 'iriusrisk project diagram <project-id>' or set up a project with 'iriusrisk init'.")
                raise click.Abort()
        
        logger.info(f"Resolved project ID: {resolved_project_id}")
        click.echo(f"📥 Getting artifacts for project: {resolved_project_id}")
        
        service = cli_ctx.get_service_factory().get_project_service()
        result = service.get_project_diagram(resolved_project_id, size)
        
        logger.info(f"Retrieved diagram artifact: {result['artifact_name']}")
        click.echo(f"📊 Found diagram artifact: {result['artifact_name']}")
        click.echo(f"🔍 Downloaded {size.lower()} size image")
        
        # Determine output filename
        if not output:
            logger.debug("No output filename provided, generating default filename")
            # Use project name from resolved project if available
            try:
                if resolved_project_id and not project_id:
                    # We're using default project, try to get a nice name
                    project_json_path = Path.cwd() / '.iriusrisk' / 'project.json'
                    if project_json_path.exists():
                        with open(project_json_path, 'r') as f:
                            project_config = json.load(f)
                        project_name = project_config.get('name', 'project')
                        # Clean up project name for filename
                        clean_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        clean_name = clean_name.replace(' ', '-').lower()
                        output = f"{clean_name}-diagram.png"
                        logger.debug(f"Generated filename from project name: {output}")
                    else:
                        output = "project-diagram.png"
                        logger.debug("Using default filename: project-diagram.png")
                else:
                    output = "project-diagram.png"
                    logger.debug("Using default filename: project-diagram.png")
            except Exception as e:
                logger.debug(f"Failed to generate filename from project name: {e}")
                output = "project-diagram.png"
        else:
            logger.debug(f"Using provided output filename: {output}")
        
        # Decode base64 and save to file
        try:
            logger.debug("Decoding base64 image data")
            image_data = base64.b64decode(result['base64_content'])
            output_path = Path(output)
            
            logger.info(f"Saving diagram to: {output_path.absolute()}")
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"Diagram saved successfully: {len(image_data):,} bytes")
            click.echo(f"✅ Diagram saved successfully!")
            click.echo(f"📁 File: {output_path.absolute()}")
            click.echo(f"📊 Size: {len(image_data):,} bytes")
            
        except Exception as e:
            logger.error(f"Failed to save diagram: {e}")
            click.echo(f"❌ Failed to save diagram: {e}", err=True)
            raise click.Abort()
        
        logger.info("Project diagram download operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "downloading diagram")


@project.command()
@click.argument('project_id', required=False)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['text', 'json'], case_sensitive=False), 
              default='text', help='Output format')
@pass_cli_context
def stats(cli_ctx, project_id: Optional[str], output_format: str):
    """Generate project statistics for automation and CI/CD integration.
    
    This command provides comprehensive statistics about threats and countermeasures
    in a project, including all combinations of states and risk/priority levels.
    The output is designed to be easily parsed by automation tools and CI/CD pipelines.
    
    Examples:
        # Get stats for default project (text format)
        iriusrisk project stats
        
        # Get stats for specific project
        iriusrisk project stats badger-app-w9z3
        
        # Get stats as JSON for automation
        iriusrisk project stats --format json
        
        # CI/CD example: fail build if critical threats are exposed
        critical_exposed=$(iriusrisk project stats | grep "threats_critical_expose:" | cut -d: -f2 | tr -d ' ')
        if [ "$critical_exposed" -gt 0 ]; then exit 1; fi
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info("Starting project stats generation operation")
        logger.debug(f"Stats parameters: project_id={project_id}, format={output_format}")
        
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
        
        click.echo("📊 Collecting project data...", err=True)
        logger.info("Starting data collection for project statistics")
        
        service = cli_ctx.get_service_factory().get_project_service()
        stats_data = service.generate_project_stats(resolved_project_id)
        
        logger.info("Project statistics generated successfully")
        logger.debug(f"Stats summary: {stats_data['threats']['total']} threats, "
                    f"{stats_data['countermeasures']['total']} countermeasures")
        
        # Output in requested format
        if output_format == 'json':
            logger.debug("Outputting statistics in JSON format")
            click.echo(json.dumps(stats_data, indent=2))
        else:  # text format
            logger.debug("Outputting statistics in text format")
            _print_stats_text(stats_data)
        
        logger.info("Project stats operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "generating project statistics")




# Stats generation functions moved to ProjectService


def _print_stats_text(stats: dict):
    """Print statistics in text format (grep-friendly).
    
    Args:
        stats: Statistics dictionary
    """
    metadata = stats["metadata"]
    threats = stats["threats"]
    countermeasures = stats["countermeasures"]
    
    print("PROJECT_STATS_START")
    print(f"project_id: {metadata['project_id']}")
    print(f"project_name: {metadata['project_name']}")
    print(f"generated_at: {metadata['generated_at']}")
    print()
    
    print("THREAT_TOTALS")
    print(f"total_threats: {threats['total']}")
    for state, count in threats["by_state"].items():
        print(f"threats_by_state_{state}: {count}")
    print()
    
    print("THREAT_RISK_LEVELS")
    for level, count in threats["by_risk_level"].items():
        print(f"threats_risk_{level}: {count}")
    print()
    
    print("THREAT_STATE_RISK_COMBINATIONS")
    for level in ['very-low', 'low', 'medium', 'high', 'critical']:
        for state in ['expose', 'accept', 'partly-mitigate', 'mitigate', 'not-applicable', 'hidden']:
            count = threats["by_state_and_risk"][level][state]
            print(f"threats_{level}_{state}: {count}")
    print()
    
    print("COUNTERMEASURE_TOTALS")
    print(f"total_countermeasures: {countermeasures['total']}")
    for state, count in countermeasures["by_state"].items():
        print(f"countermeasures_by_state_{state}: {count}")
    print()
    
    print("COUNTERMEASURE_PRIORITIES")
    for priority, count in countermeasures["by_priority"].items():
        print(f"countermeasures_priority_{priority}: {count}")
    print()
    
    print("COUNTERMEASURE_STATE_PRIORITY_COMBINATIONS")
    for priority in ['low', 'medium', 'high', 'very-high']:
        for state in ['not-applicable', 'rejected', 'recommended', 'required', 'implemented']:
            count = countermeasures["by_state_and_priority"][priority][state]
            print(f"countermeasures_{priority}_{state}: {count}")
    print()
    
    print("PROJECT_STATS_END")


def _format_projects_output(projects_data: list, output_format: str, include_versions: bool, 
                           page_info: dict, full_response: dict):
    """Format and print projects output using centralized formatters."""
    
    # Define field mappings for projects
    base_field_mappings = [
        {'key': 'id'},  # No truncation - IDs needed for operations
        {'key': 'name'},
        {'key': 'referenceId'},
        {'key': 'state'},  # Threat model state
        {'key': 'workflowState.name', 'csv_key': 'workflowState'},
        {'key': 'isArchived', 'formatter': TableFormatter.format_boolean},
        {'key': 'modelUpdated', 'formatter': lambda x: TableFormatter.format_timestamp(x, 'date'), 'truncate': 10}
    ]
    
    if include_versions:
        base_field_mappings.append({'key': 'version.name', 'csv_key': 'version'})
    
    # Create table headers
    table_headers = ['ID', 'Name', 'Reference ID', 'TM State', 'Workflow State', 'Archived', 'Updated']
    if include_versions:
        table_headers.append('Version')
    
    # Create CSV headers
    csv_headers = ['id', 'name', 'referenceId', 'state', 'workflowState', 'isArchived', 'modelUpdated']
    if include_versions:
        csv_headers.append('version')
    
    # Create transformers
    row_transformer = TableFormatter.create_row_transformer(base_field_mappings)
    csv_transformer = TableFormatter.create_csv_transformer(base_field_mappings)
    
    # Format and print output
    format_and_print_list(
        items=projects_data,
        output_format=output_format,
        table_headers=table_headers,
        csv_headers=csv_headers,
        row_transformer=row_transformer,
        csv_transformer=csv_transformer,
        title=None,
        page_info=page_info,
        full_response=full_response
    )


