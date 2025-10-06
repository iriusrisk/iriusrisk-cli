"""
Countermeasures command module for IriusRisk CLI.

This module provides functionality to list, show, and search countermeasures
within IriusRisk projects.
"""

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


# Countermeasure filtering moved to CountermeasureService



@click.group()
def countermeasure():
    """Manage countermeasures within IriusRisk projects.
    
    This command group provides functionality to list, show, and search
    countermeasures within your IriusRisk projects.
    """
    pass


@countermeasure.command()
@click.argument('project_id', required=False)
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of countermeasures per page', type=int)
@click.option('--risk-level', '-r', help='Filter by risk level (HIGH, MEDIUM, LOW)')
@click.option('--status', help='Filter by countermeasure status')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False),
              default='table', help='Output format')
@click.option('--filter', 'custom_filter', help='Custom filter expression (advanced)')
@pass_cli_context
def list(cli_ctx, project_id: Optional[str], page: int, size: int, risk_level: Optional[str],
         status: Optional[str], output_format: str, custom_filter: Optional[str]):
    """List countermeasures from a project."""
    try:
        logger.info("Starting countermeasure list operation")
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

        service = cli_ctx.get_service_factory().get_countermeasure_service()
        result = service.list_countermeasures(
            project_id=resolved_project_id,
            page=page,
            size=size,
            risk_level=risk_level,
            status=status,
            custom_filter=custom_filter
        )

        countermeasures_data = result['countermeasures']
        page_info = result['page_info']
        full_response = result['full_response']

        logger.debug(f"Retrieved {len(countermeasures_data)} countermeasures from API")

        if not countermeasures_data:
            logger.info("No countermeasures found matching the criteria")
            click.echo("No countermeasures found matching the criteria.")
            return

        total_elements = page_info.get('totalElements', len(countermeasures_data))
        logger.info(f"Found {total_elements} countermeasure(s) matching criteria, displaying {len(countermeasures_data)} on page {page}")

        # Format output using centralized formatter
        _format_countermeasures_output(countermeasures_data, output_format, page_info, full_response)
        
        logger.info("Countermeasure list operation completed successfully")

    except Exception as e:
        handle_cli_error(e, "retrieving countermeasures")


@countermeasure.command()
@click.argument('countermeasure_id')
@click.argument('project_id', required=False)
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
@pass_cli_context
def show(cli_ctx, countermeasure_id: str, project_id: Optional[str], output_format: str):
    """Show detailed information about a specific countermeasure.
    
    Args:
        countermeasure_id: Countermeasure ID
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    try:
        logger.info(f"Starting countermeasure show operation for countermeasure: {countermeasure_id}")
        logger.debug(f"Show parameters: countermeasure_id={countermeasure_id}, project_id={project_id}, format={output_format}")
        
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
        
        service = cli_ctx.get_service_factory().get_countermeasure_service()
        countermeasure_data = service.get_countermeasure(resolved_project_id, countermeasure_id)
        
        countermeasure_name = countermeasure_data.get('name', 'N/A')
        logger.info(f"Retrieved countermeasure data for: {countermeasure_name}")
        
        # Format output using centralized formatter
        format_and_print_detail(countermeasure_data, output_format, _print_countermeasure_details)
        
        logger.info("Countermeasure show operation completed successfully")

    except Exception as e:
        handle_cli_error(e, f"retrieving countermeasure '{countermeasure_id}'")


@countermeasure.command()
@click.argument('search_string')
@click.argument('project_id', required=False)
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False),
              default='table', help='Output format')
@pass_cli_context
def search(cli_ctx, search_string: str, project_id: Optional[str], output_format: str):
    """Search countermeasures by name, description, or other fields.
    
    This performs a deep search across all countermeasures for the specified string.
    """
    try:
        logger.info(f"Starting countermeasure search operation for: '{search_string}'")
        logger.debug(f"Search parameters: search_string='{search_string}', project_id={project_id}, format={output_format}")
        
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
        
        service = cli_ctx.get_service_factory().get_countermeasure_service()
        result = service.search_countermeasures(
            project_id=resolved_project_id,
            search_string=search_string
        )
        
        countermeasures_data = result['countermeasures']
        page_info = result['page_info']
        full_response = result['full_response']
        
        logger.debug(f"Retrieved {len(countermeasures_data)} countermeasures from search")
        
        if not countermeasures_data:
            logger.info(f"No countermeasures found matching search term: '{search_string}'")
            click.echo(f"No countermeasures found matching '{search_string}'.")
            return
        
        total_elements = page_info.get('totalElements', len(countermeasures_data))
        logger.info(f"Found {total_elements} countermeasure(s) matching '{search_string}', displaying {len(countermeasures_data)}")
        click.echo(f"Found {len(countermeasures_data)} countermeasure(s) matching '{search_string}':")
        click.echo()
        
        # Format output using centralized formatter
        _format_countermeasures_output(countermeasures_data, output_format, page_info, full_response)
        
        logger.info("Countermeasure search operation completed successfully")

    except Exception as e:
        handle_cli_error(e, f"searching countermeasures for '{search_string}'")


@countermeasure.command()
@click.argument('countermeasure_id')
@click.option('--status', '-s', required=True, 
              type=click.Choice(['required', 'recommended', 'implemented', 'rejected', 'not-applicable'], case_sensitive=False),
              help='New status for the countermeasure')
@click.option('--reason', '-r', help='Reason for the status change')
@click.option('--comment', '-c', help='Detailed comment with implementation details and code snippets')
@click.option('--project', '-p', help='Project ID (optional if default project configured)')
@pass_cli_context
def update(cli_ctx, countermeasure_id: str, status: str, reason: Optional[str], comment: Optional[str], project: Optional[str]):
    """Update the status of a countermeasure.
    
    This command updates the state of a specific countermeasure by its ID.
    The countermeasure ID should be the full UUID as returned by countermeasure list/show commands.
    
    Examples:
        # Update countermeasure status to required
        iriusrisk countermeasure update ce178b2e-f771-4c92-9f1a-c217e4b97c81 --status required
        
        # Update countermeasure status to implemented
        iriusrisk countermeasure update ce178b2e-f771-4c92-9f1a-c217e4b97c81 --status implemented
        
        # Update countermeasure in specific project
        iriusrisk countermeasure update ce178b2e-f771-4c92-9f1a-c217e4b97c81 --status rejected --project my-project-id
    
    Args:
        countermeasure_id: Countermeasure UUID
        status: New status for the countermeasure
        project: Project ID (optional if default project configured)
    """
    try:
        logger.info(f"Starting countermeasure update operation for countermeasure: {countermeasure_id}")
        logger.debug(f"Update parameters: countermeasure_id={countermeasure_id}, status={status}, "
                    f"reason={reason}, comment={'<provided>' if comment else 'None'}, project={project}")
        
        # Show context information if using default project
        if not project:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        # Update countermeasure state
        logger.info(f"Updating countermeasure {countermeasure_id} to status '{status}'")
        click.echo(f"Updating countermeasure {countermeasure_id} to status '{status}'...")
        
        service = cli_ctx.get_service_factory().get_countermeasure_service()
        result = service.update_countermeasure_status(
            countermeasure_id=countermeasure_id,
            status=status,
            reason=reason,
            comment=comment
        )
        
        logger.info(f"Successfully updated countermeasure {countermeasure_id} to status '{status}'")
        click.echo(f"✅ Successfully updated countermeasure {countermeasure_id} to status '{status}'")
        
        # Show comment creation result
        if comment:
            if result.get('comment_created'):
                logger.info(f"Successfully created comment for countermeasure {countermeasure_id}")
                click.echo(f"✅ Successfully created comment for countermeasure {countermeasure_id}")
                click.echo(f"   Comment: {comment[:100]}{'...' if len(comment) > 100 else ''}")
            elif result.get('comment_error'):
                logger.warning(f"Failed to create comment for countermeasure {countermeasure_id}: {result['comment_error']}")
                click.echo(f"❌ Failed to create comment: {result['comment_error']}", err=True)
        
        if reason:
            logger.debug(f"Update reason: {reason}")
            click.echo(f"   Reason: {reason}")
        
        logger.info("Countermeasure update operation completed successfully")
            
    except Exception as e:
        handle_cli_error(e, f"updating countermeasure '{countermeasure_id}'")


@countermeasure.command(name='create-issue')
@click.argument('countermeasure_id')
@click.option('--tracker', '-t', help='Issue tracker name or ID (optional if default configured)')
@click.option('--project', '-p', help='Project ID (optional if default project configured)')
@pass_cli_context
def create_issue(cli_ctx, countermeasure_id: str, tracker: Optional[str], project: Optional[str]):
    """Create an issue in the configured issue tracker for a countermeasure.
    
    This command creates a ticket in the specified issue tracker (or default if configured)
    for the given countermeasure. The countermeasure ID can be either the reference ID 
    (e.g., C-RELATIONAL-DATABASE-MANAGEMENT-SYSTEM-0001) or the UUID as shown in countermeasure list.
    
    Examples:
        # Create issue using default issue tracker
        iriusrisk countermeasure create-issue C-WEB-APPLICATION-0001
        
        # Create issue using specific issue tracker
        iriusrisk countermeasure create-issue C-WEB-APPLICATION-0001 --tracker "Fraser"
        
        # Create issue for countermeasure in specific project
        iriusrisk countermeasure create-issue C-WEB-APPLICATION-0001 --project my-project-id
    
    Args:
        countermeasure_id: Countermeasure reference ID or UUID
        tracker: Issue tracker name or ID (optional if default configured)
        project: Project ID (optional if default project configured)
    """
    try:
        logger.info(f"Starting countermeasure issue creation for countermeasure: {countermeasure_id}")
        logger.debug(f"Create issue parameters: countermeasure_id={countermeasure_id}, tracker={tracker}, project={project}")
        
        # Show context information if using default project
        if not project:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        # Resolve project ID from argument or default configuration
        resolved_project_id = resolve_project_id(project)
        logger.debug(f"Resolved project ID: {resolved_project_id}")
        
        service = cli_ctx.get_service_factory().get_countermeasure_service()
        result = service.create_countermeasure_issue(
            project_id=resolved_project_id,
            countermeasure_id=countermeasure_id,
            tracker=tracker
        )
        
        countermeasure_name = result['countermeasure_name']
        issue_tracker_name = result['issue_tracker_name']
        api_result = result['result']
        
        logger.info(f"Creating issue for countermeasure '{countermeasure_id}' ({countermeasure_name}) using tracker: {issue_tracker_name}")
        click.echo(f"Creating issue for countermeasure '{countermeasure_id}' ({countermeasure_name})...")
        click.echo(f"Using issue tracker: {issue_tracker_name}")
        
        logger.info(f"Successfully created issue for countermeasure '{countermeasure_id}'")
        click.echo(f"✅ Successfully created issue for countermeasure '{countermeasure_id}'")
        
        # Display any relevant information from the response
        if isinstance(api_result, dict):
            if api_result.get('issueKey'):
                logger.debug(f"Issue Key: {api_result.get('issueKey')}")
                click.echo(f"   Issue Key: {api_result.get('issueKey')}")
            if api_result.get('issueUrl'):
                logger.debug(f"Issue URL: {api_result.get('issueUrl')}")
                click.echo(f"   Issue URL: {api_result.get('issueUrl')}")
            if api_result.get('message'):
                logger.debug(f"Issue message: {api_result.get('message')}")
                click.echo(f"   Message: {api_result.get('message')}")
        
        logger.info("Countermeasure issue creation operation completed successfully")
        
    except Exception as e:
        handle_cli_error(e, f"creating issue for countermeasure '{countermeasure_id}'")


# Filter expression building moved to CountermeasureService


def _print_countermeasures_table(countermeasures: list, page_info: dict):
    """Print countermeasures in a formatted table."""
    from ..utils.table import TableFormatter

    if not countermeasures:
        click.echo("No countermeasures found.")
        return

    # Create table headers
    headers = ['ID', 'Name', 'Reference ID', 'Component', 'Risk', 'Status', 'Priority']

    # Create table rows - V2 API returns countermeasures directly
    rows = []
    for countermeasure in countermeasures:
        # Show full countermeasure ID (needed for updates and other operations)
        countermeasure_id = countermeasure.get('id', '')
        
        # Format countermeasure name for display (truncate if too long)
        countermeasure_name = countermeasure.get('name', '')
        display_name = countermeasure_name[:45] + '...' if len(countermeasure_name) > 45 else countermeasure_name
        
        # Get component information
        component = countermeasure.get('component', {})
        component_name = component.get('name', 'N/A')
        
        # Format priority for display
        priority = countermeasure.get('priority', {})
        if isinstance(priority, dict):
            priority_display = priority.get('calculated', priority.get('manual', ''))
        else:
            priority_display = str(priority)
        
        row = [
            countermeasure_id,
            display_name,
            countermeasure.get('referenceId', ''),
            component_name,
            countermeasure.get('risk', ''),
            countermeasure.get('state', ''),
            priority_display
        ]
        rows.append(row)

    if not rows:
        click.echo("No countermeasures found in the response.")
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

        click.echo(f"\nShowing {len(rows)} countermeasures (page {current_page} of {total_pages})")
    else:
        click.echo(f"\nShowing {len(rows)} countermeasures")


def _format_countermeasures_output(countermeasures_data: list, output_format: str, 
                                  page_info: dict, full_response: dict):
    """Format and print countermeasures output using centralized formatters."""
    
    # Define field mappings for countermeasures
    field_mappings = [
        {'key': 'ref', 'csv_key': 'id', 'truncate': 12},
        {'key': 'name'},
        {'key': 'ref', 'csv_key': 'referenceId'},
        {'key': 'risk'},
        {'key': 'state', 'csv_key': 'status'},
        {'key': 'platform'},
        {'key': 'priority'}
    ]
    
    # Create table headers
    table_headers = ['ID', 'Name', 'Reference ID', 'Risk', 'Status', 'Platform', 'Priority']
    
    # Create CSV headers
    csv_headers = ['id', 'name', 'referenceId', 'risk', 'status', 'platform', 'priority']
    
    # Create transformers
    row_transformer = TableFormatter.create_row_transformer(field_mappings)
    csv_transformer = TableFormatter.create_csv_transformer(field_mappings)
    
    # Format and print output
    format_and_print_list(
        items=countermeasures_data,
        output_format=output_format,
        table_headers=table_headers,
        csv_headers=csv_headers,
        row_transformer=row_transformer,
        csv_transformer=csv_transformer,
        title=None,
        page_info=page_info,
        full_response=full_response
    )


def _print_countermeasure_details(countermeasure: dict):
    """Print detailed countermeasure information in a formatted table."""
    from ..utils.table import TableFormatter
    
    click.echo("Countermeasure Details")
    click.echo("=" * 50)
    
    # Get component information
    component = countermeasure.get('component', {})
    component_name = component.get('name', 'N/A')
    component_id = component.get('id', 'N/A')
    
    # Format owner information
    owner = countermeasure.get('owner', {})
    if isinstance(owner, dict):
        owner_display = owner.get('username', 'N/A')
    else:
        owner_display = str(owner)
    
    # Format priority information
    priority = countermeasure.get('priority', {})
    if isinstance(priority, dict):
        priority_display = f"Calculated: {priority.get('calculated', 'N/A')}, Manual: {priority.get('manual', 'N/A')}"
    else:
        priority_display = str(priority)

    # Basic information
    basic_info = [
        ['UUID', countermeasure.get('id', 'N/A')],
        ['Name', countermeasure.get('name', 'N/A')],
        ['Reference ID', countermeasure.get('referenceId', countermeasure.get('ref', 'N/A'))],
        ['Component', component_name],
        ['Component ID', component_id],
        ['Risk Level', countermeasure.get('risk', 'N/A')],
        ['Status', countermeasure.get('state', 'N/A')],
        ['Priority', priority_display],
        ['Owner', owner_display],
        ['Source', countermeasure.get('source', 'N/A')],
        ['Cost', countermeasure.get('cost', 'N/A')],
        ['Library', countermeasure.get('library', 'N/A')]
    ]
    
    formatter = TableFormatter()
    formatter.print_table(basic_info, ['Field', 'Value'])
    
    # Description
    description = countermeasure.get('desc', '')
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
        value = countermeasure.get(field, '')
        if value and value != 'N/A':
            click.echo(f"\n{field.title()}:")
            click.echo("-" * 20)
            if isinstance(value, (__builtins__['list'], __builtins__['dict'])):
                click.echo(json.dumps(value, indent=2))
            else:
                click.echo(str(value))
