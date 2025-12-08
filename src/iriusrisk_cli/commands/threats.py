"""Threats command group for IriusRisk CLI."""

import click
import json
import logging
from typing import Optional
from ..cli_context import pass_cli_context
from ..utils.project import resolve_project_id, get_project_context_info
from ..utils.output_formatters import format_and_print_list, format_and_print_detail
from ..utils.table import TableFormatter
from ..utils.error_handling import handle_cli_error

logger = logging.getLogger(__name__)


# Threat filtering moved to ThreatService


@click.group()
def threat():
    """Manage threats within IriusRisk projects.
    
    This command group provides functionality to list, show, and search
    threats within your IriusRisk projects.
    """
    pass


# Filter expression building moved to ThreatService


@threat.command()
@click.argument('project_id', required=False)
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of threats per page', type=int)
@click.option('--risk-level', '-r', help='Filter by risk level (HIGH, MEDIUM, LOW)')
@click.option('--status', help='Filter by threat status')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False), 
              default='table', help='Output format')
@click.option('--filter', 'custom_filter', help='Custom filter expression (advanced)')
@pass_cli_context
def list(cli_ctx, project_id: Optional[str], page: int, size: int, risk_level: Optional[str], 
         status: Optional[str], output_format: str, custom_filter: Optional[str]):
    """List threats from a project.
    
    This command retrieves and displays threats from a specific project
    with various filtering and formatting options.
    
    Examples:
        # List all threats from default project
        iriusrisk threat list
        
        # List threats from specific project
        iriusrisk threat list my-project-id
        
        # List first 10 threats
        iriusrisk threat list --size 10
        
        # Filter by risk level
        iriusrisk threat list --risk-level HIGH
        
        # Filter by status
        iriusrisk threat list --status OPEN
        
        # Output as JSON
        iriusrisk threat list --format json
        
        # Advanced filtering
        iriusrisk threat list --filter "'risk'='HIGH':AND:'status'='OPEN'"
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info("Starting threat list operation")
        logger.debug(f"List parameters: project_id={project_id}, page={page}, size={size}, "
                    f"risk_level={risk_level}, status={status}, custom_filter={custom_filter}, format={output_format}")
        
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
        
        service = cli_ctx.get_service_factory().get_threat_service()
        result = service.list_threats(
            project_id=resolved_project_id,
            page=page,
            size=size,
            risk_level=risk_level,
            status=status,
            custom_filter=custom_filter
        )
        
        threats_data = result['threats']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(threats_data)} threats from API")
        
        if not threats_data:
            logger.info("No threats found matching the criteria")
            click.echo("No threats found matching the criteria.")
            return
        
        total_elements = page_info.get('totalElements', len(threats_data))
        logger.info(f"Found {total_elements} threat(s) matching criteria, displaying {len(threats_data)} on page {page}")
        
        # Format output using centralized formatter
        _format_threats_output(threats_data, output_format, page_info, full_response)
        
        logger.info("Threat list operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, "retrieving threats")


@threat.command()
@click.argument('threat_id')
@click.argument('project_id', required=False)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json'], case_sensitive=False), 
              default='table', help='Output format')
@pass_cli_context
def show(cli_ctx, threat_id: str, project_id: Optional[str], output_format: str):
    """Show detailed information for a specific threat.
    
    This command retrieves and displays detailed information for a single threat
    by its ID within a project.
    
    Examples:
        # Show threat from default project
        iriusrisk threat show threat-123
        
        # Show threat from specific project
        iriusrisk threat show threat-123 my-project-id
        
        # Output as JSON
        iriusrisk threat show threat-123 --format json
    
    Args:
        threat_id: Threat ID
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info(f"Starting threat show operation for threat: {threat_id}")
        logger.debug(f"Show parameters: threat_id={threat_id}, project_id={project_id}, format={output_format}")
        
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
        
        service = cli_ctx.get_service_factory().get_threat_service()
        threat_data = service.get_threat(resolved_project_id, threat_id)
        
        threat_name = threat_data.get('name', 'N/A')
        logger.info(f"Retrieved threat data for: {threat_name}")
        
        # Format output using centralized formatter
        format_and_print_detail(threat_data, output_format, _print_threat_details)
        
        logger.info("Threat show operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, f"retrieving threat '{threat_id}'")


@threat.command()
@click.argument('search_string')
@click.argument('project_id', required=False)
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of threats per page', type=int)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False), 
              default='table', help='Output format')
@pass_cli_context
def search(cli_ctx, search_string: str, project_id: Optional[str], page: int, size: int, output_format: str):
    """Search threats within a project.
    
    This command performs a deep search across all threats in a project,
    searching in names, descriptions, and other relevant fields.
    
    Examples:
        # Search threats in default project
        iriusrisk threat search "SQL injection"
        
        # Search threats in specific project
        iriusrisk threat search "authentication" my-project-id
        
        # Search with pagination
        iriusrisk threat search "vulnerability" --page 1 --size 10
        
        # Output as JSON
        iriusrisk threat search "XSS" --format json
    
    Args:
        search_string: String to search for in threat names, descriptions, etc.
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info(f"Starting threat search operation for: '{search_string}'")
        logger.debug(f"Search parameters: search_string='{search_string}', project_id={project_id}, "
                    f"page={page}, size={size}, format={output_format}")
        
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
        
        service = cli_ctx.get_service_factory().get_threat_service()
        result = service.search_threats(
            project_id=resolved_project_id,
            search_string=search_string,
            page=page,
            size=size
        )
        
        threats_data = result['threats']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(threats_data)} threats from search")
        
        if not threats_data:
            logger.info(f"No threats found matching search term: '{search_string}'")
            click.echo(f"No threats found matching '{search_string}'.")
            return
        
        total_elements = page_info.get('totalElements', len(threats_data))
        logger.info(f"Found {total_elements} threat(s) matching '{search_string}', displaying {len(threats_data)} on page {page}")
        click.echo(f"Found {len(threats_data)} threat(s) matching '{search_string}':")
        click.echo()
        
        # Format output using centralized formatter
        _format_threats_output(threats_data, output_format, page_info, full_response)
        
        logger.info("Threat search operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, f"searching threats for '{search_string}'")


@threat.command()
@click.argument('threat_id')
@click.option('--status', '-s', required=True, 
              type=click.Choice(['accept', 'mitigate', 'expose', 'partly-mitigate', 'hidden'], case_sensitive=False),
              help='New status for the threat')
@click.option('--reason', '-r', help='Reason for the status change (required for "accept" status)')
@click.option('--comment', '-c', help='Detailed comment with implementation details and code snippets')
@click.option('--project', '-p', help='Project ID (optional if default project configured)')
@pass_cli_context
def update(cli_ctx, threat_id: str, status: str, reason: Optional[str], comment: Optional[str], project: Optional[str]):
    """Update the status of a threat.
    
    This command updates the state of a specific threat by its ID.
    The threat ID should be the full UUID as returned by threat list/show commands.
    
    Examples:
        # Update threat status to accept (reason required for accept)
        iriusrisk threat update e29deb79-ae4d-4c42-8180-56e79149d180 --status accept --reason "Risk accepted after review"
        
        # Update threat to other status (reason optional)
        iriusrisk threat update e29deb79-ae4d-4c42-8180-56e79149d180 --status mitigate
        
        # Update threat in specific project
        iriusrisk threat update e29deb79-ae4d-4c42-8180-56e79149d180 --status mitigate --project my-project-id
    
    Args:
        threat_id: Threat UUID
        status: New status for the threat
        reason: Reason for the status change (required when status is "accept", optional for other statuses)
        project: Project ID (optional if default project configured)
    """
    try:
        logger.info(f"Starting threat update operation for threat: {threat_id}")
        logger.debug(f"Update parameters: threat_id={threat_id}, status={status}, "
                    f"reason={reason}, comment={'<provided>' if comment else 'None'}, project={project}")
        
        # Show context information if using default project
        if not project:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        # Update threat state
        logger.info(f"Updating threat {threat_id} to status '{status}'")
        click.echo(f"Updating threat {threat_id} to status '{status}'...")
        
        service = cli_ctx.get_service_factory().get_threat_service()
        result = service.update_threat_status(
            threat_id=threat_id,
            status=status,
            reason=reason,
            comment=comment
        )
        
        logger.info(f"Successfully updated threat {threat_id} to status '{status}'")
        click.echo(f"✅ Successfully updated threat {threat_id} to status '{status}'")
        
        # Show comment creation result
        if comment:
            if result.get('comment_created'):
                logger.info(f"Successfully created comment for threat {threat_id}")
                click.echo(f"✅ Successfully created comment for threat {threat_id}")
                click.echo(f"   Comment: {comment[:100]}{'...' if len(comment) > 100 else ''}")
            elif result.get('comment_error'):
                logger.warning(f"Failed to create comment for threat {threat_id}: {result['comment_error']}")
                click.echo(f"❌ Failed to create comment: {result['comment_error']}", err=True)
        
        if reason:
            logger.debug(f"Update reason: {reason}")
            click.echo(f"   Reason: {reason}")
        
        logger.info("Threat update operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, f"updating threat '{threat_id}'")


def _format_threats_output(threats_data: list, output_format: str, 
                          page_info: dict, full_response: dict):
    """Format and print threats output using centralized formatters."""
    
    # Define field mappings for threats
    field_mappings = [
        {'key': 'id'},  # No truncation - IDs needed for operations
        {'key': 'name'},
        {'key': 'referenceId'},
        {'key': 'description', 'truncate': 40},
        {'key': 'risk'},
        {'key': 'state'},  # API returns 'state', not 'status'
        {'key': 'category'},
        {'key': 'created', 'formatter': lambda x: TableFormatter.format_timestamp(x, 'date')},
        {'key': 'updated', 'formatter': lambda x: TableFormatter.format_timestamp(x, 'date')}
    ]
    
    # Create table headers
    table_headers = ['ID', 'Name', 'Reference ID', 'Description', 'Risk', 'Status', 'Category', 'Created', 'Updated']
    
    # Create CSV headers
    csv_headers = ['id', 'name', 'referenceId', 'description', 'risk', 'state', 'category', 'created', 'updated']
    
    # Create transformers
    row_transformer = TableFormatter.create_row_transformer(field_mappings)
    csv_transformer = TableFormatter.create_csv_transformer(field_mappings)
    
    # Format and print output
    format_and_print_list(
        items=threats_data,
        output_format=output_format,
        table_headers=table_headers,
        csv_headers=csv_headers,
        row_transformer=row_transformer,
        csv_transformer=csv_transformer,
        title=None,
        page_info=page_info,
        full_response=full_response
    )


def _print_threats_table(threats: list, page_info: dict):
    """Print threats in a formatted table."""
    from ..utils.table import TableFormatter
    
    if not threats:
        click.echo("No threats found.")
        return
    
    # Create table headers
    headers = ['ID', 'Name', 'Reference ID', 'Component', 'Risk', 'Status']
    
    # Create table rows - V2 API returns threats directly, not nested under components
    rows = []
    for threat in threats:
        # Get component information
        component = threat.get('component', {})
        component_name = component.get('name', 'N/A')
        
        # Show full threat ID (needed for updates and other operations)
        threat_id = threat.get('id', '')
        
        # Format threat name for display (truncate if too long)
        threat_name = threat.get('name', '')
        display_name = threat_name[:45] + '...' if len(threat_name) > 45 else threat_name
        
        row = [
            threat_id,
            display_name,
            threat.get('referenceId', ''),
            component_name,
            threat.get('inherentRisk', threat.get('risk', '')),
            threat.get('state', '')
        ]
        rows.append(row)
    
    if not rows:
        click.echo("No threats found in the response.")
        return
    
    # Print table
    formatter = TableFormatter()
    formatter.print_table(rows, headers)
    
    # Print pagination info
    if page_info:
        total_elements = page_info.get('totalElements', 0)
        total_pages = page_info.get('totalPages', 0)
        current_page = page_info.get('number', 0) + 1
        size = page_info.get('size', 0)
        
        click.echo(f"\nShowing {len(rows)} threats (page {current_page} of {total_pages})")
    else:
        click.echo(f"\nShowing {len(rows)} threats")


def _print_threat_details(threat: dict):
    """Print detailed threat information."""
    from ..utils.table import TableFormatter
    
    click.echo("Threat Details")
    click.echo("=" * 50)
    
    # Get component information
    component = threat.get('component', {})
    component_name = component.get('name', 'N/A')
    component_id = component.get('id', 'N/A')
    
    # Format owner information
    owner = threat.get('owner', {})
    if isinstance(owner, dict):
        owner_display = owner.get('username', 'N/A')
    else:
        owner_display = str(owner)
    
    # Get library information
    library = threat.get('library', {})
    if isinstance(library, dict):
        library_display = library.get('name', 'N/A')
    else:
        library_display = str(library)

    # Basic information
    basic_info = [
        ['UUID', threat.get('id', 'N/A')],
        ['Name', threat.get('name', 'N/A')],
        ['Reference ID', threat.get('referenceId', threat.get('ref', 'N/A'))],
        ['Component', component_name],
        ['Component ID', component_id],
        ['Inherent Risk', threat.get('inherentRisk', 'N/A')],
        ['Current Risk', threat.get('risk', 'N/A')],
        ['Status', threat.get('state', 'N/A')],
        ['Owner', owner_display],
        ['Source', threat.get('source', 'N/A')],
        ['Library', library_display],
        ['Mitigation %', threat.get('mitigation', 'N/A')],
        ['Confidentiality', threat.get('confidentiality', 'N/A')],
        ['Integrity', threat.get('integrity', 'N/A')],
        ['Availability', threat.get('availability', 'N/A')]
    ]
    
    formatter = TableFormatter()
    formatter.print_table(basic_info, ['Field', 'Value'])
    
    # Description
    description = threat.get('desc', '')
    if description:
        click.echo(f"\nDescription:")
        click.echo("-" * 20)
        # Clean up HTML tags from description
        import re
        clean_description = re.sub(r'<[^>]+>', '', description)
        click.echo(clean_description)
    
    # Additional fields
    additional_fields = ['mitigation', 'references', 'tags']
    for field in additional_fields:
        value = threat.get(field, '')
        if value:
            click.echo(f"\n{field.title()}:")
            click.echo("-" * 20)
            if isinstance(value, __builtins__['list']):
                for item in value:
                    click.echo(f"  • {item}")
            else:
                click.echo(value)
