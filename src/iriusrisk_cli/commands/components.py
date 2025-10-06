"""
Components command module for IriusRisk CLI.

This module provides functionality to list, show, and search system components
that are available for use when drawing diagrams in IriusRisk.
"""

import click
import json
from typing import Optional
from ..container import get_container
from ..api_client import IriusRiskApiClient
from ..utils.error_handling import handle_cli_error_decorator, safe_api_call
from ..utils.logging_config import LoggedOperation
from ..utils.output_formatters import format_and_print_list, format_and_print_detail
from ..utils.table import TableFormatter
from ..exceptions import ValidationError, ResourceNotFoundError
import logging

logger = logging.getLogger('iriusrisk_cli.commands.components')


def _filter_components_by_search(components_data: list, search_string: str) -> list:
    """Filter components by search string using client-side filtering.
    
    Args:
        components_data: List of components from API
        search_string: String to search for
        
    Returns:
        Filtered list of components
    """
    if not search_string:
        return components_data
    
    search_lower = search_string.lower()
    filtered_components = []
    
    for component in components_data:
        # Search in component name, description, reference ID, and category
        component_name = component.get('name', '').lower()
        component_desc = component.get('description', '').lower() if component.get('description') else ''
        component_ref = component.get('referenceId', '').lower()
        component_category = component.get('category', {}).get('name', '').lower()
        component_type = component.get('componentType', '').lower()
        
        if (search_lower in component_name or 
            search_lower in component_desc or 
            search_lower in component_ref or
            search_lower in component_category or
            search_lower in component_type):
            filtered_components.append(component)
    
    return filtered_components


def _find_component_by_id(components_data: list, component_id: str) -> Optional[dict]:
    """Find a specific component by its ID within the components data.
    
    Args:
        components_data: List of components from API
        component_id: Component ID to find (can be UUID or reference ID)
        
    Returns:
        Component data dictionary or None if not found
    """
    for component in components_data:
        # Check both UUID and reference ID
        if (component.get('id') == component_id or 
            component.get('referenceId') == component_id):
            return component
    
    return None


@click.group()
def component():
    """Manage system components within IriusRisk.
    
    This command group provides functionality to list, show, and search
    system components that are available for use when drawing diagrams.
    """
    pass


@component.command()
@click.option('--page', '-p', default=0, help='Page number (0-based)', type=int)
@click.option('--size', '-s', default=20, help='Number of components per page', type=int)
@click.option('--category', '-c', help='Filter by component category')
@click.option('--type', '-t', help='Filter by component type')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False),
              default='table', help='Output format')
@click.option('--filter', 'custom_filter', help='Custom filter expression (advanced)')
@handle_cli_error_decorator
def list(page: int, size: int, category: Optional[str], type: Optional[str],
         output_format: str, custom_filter: Optional[str]):
    """List system components available for diagram creation."""
    with LoggedOperation(logger, "list components", {"page": page, "size": size}):
        # Validate parameters
        if page < 0:
            raise ValidationError("Page number must be non-negative", field="page")
        if size <= 0 or size > 1000:
            raise ValidationError("Size must be between 1 and 1000", field="size")

        # Build filter expression
        filter_expr = custom_filter
        if not filter_expr:
            filter_expr = build_component_filter_expression(
                category=category,
                component_type=type
            )

        # Make API request using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        response = safe_api_call(
            api_client.project_client.get_components,
            page=page,
            size=size,
            filter_expression=filter_expr,
            operation="list components"
        )

        # Handle response format
        components_data = response.get('_embedded', {}).get('items', [])
        page_info = response.get('page', {})

        if not components_data:
            click.echo("No components found matching the criteria.")
            return

        logger.info(f"Retrieved {len(components_data)} components")

        # Format output using centralized formatter
        _format_components_output(components_data, output_format, page_info, response)


@component.command()
@click.argument('component_id')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
@handle_cli_error_decorator
def show(component_id: str, output_format: str):
    """Show detailed information about a specific component.
    
    Args:
        component_id: Component UUID or reference ID
    """
    with LoggedOperation(logger, "show component", {"component_id": component_id}):
        # Validate component_id
        if not component_id or not component_id.strip():
            raise ValidationError("Component ID cannot be empty", field="component_id")
        
        component_data = None
        
        # Try to get the component directly first using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        try:
            component_data = safe_api_call(
                api_client.project_client.get_component,
                component_id,
                operation=f"get component {component_id}"
            )
        except ResourceNotFoundError:
            # If direct lookup fails, search through the list
            logger.info(f"Direct lookup failed for {component_id}, searching through components...")
            response = safe_api_call(
                api_client.project_client.get_components,
                page=0,
                size=1000,
                operation="get all components for search"
            )
            all_components = response.get('_embedded', {}).get('items', [])
            component_data = _find_component_by_id(all_components, component_id)
            
            if not component_data:
                raise ResourceNotFoundError("Component", component_id)
        
        logger.info(f"Retrieved component details for {component_id}")
        
        # Format output using centralized formatter
        format_and_print_detail(component_data, output_format, _print_component_details)


@component.command()
@click.argument('search_string')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'csv'], case_sensitive=False),
              default='table', help='Output format')
@handle_cli_error_decorator
def search(search_string: str, output_format: str):
    """Search components by name, description, category, or other fields.
    
    This performs a deep search across all components for the specified string.
    """
    with LoggedOperation(logger, "search components", {"search_string": search_string}):
        # Validate search string
        if not search_string or not search_string.strip():
            raise ValidationError("Search string cannot be empty", field="search_string")
        
        search_string = search_string.strip()
        
        # Get all components for client-side filtering (API doesn't support search) using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        response = safe_api_call(
            api_client.project_client.get_components,
            page=0,
            size=1000,
            operation="get all components for search"
        )
        all_components = response.get('_embedded', {}).get('items', [])
        page_info = response.get('page', {})
        
        if not all_components:
            click.echo(f"No components found matching '{search_string}'.")
            return
        
        # Apply client-side filtering for search
        components_data = _filter_components_by_search(all_components, search_string)
        
        if not components_data:
            click.echo(f"No components found matching '{search_string}'.")
            return
        
        logger.info(f"Found {len(components_data)} components matching '{search_string}'")
        
        click.echo(f"Found {len(components_data)} component(s) matching '{search_string}':")
        click.echo()
        
        # Format output using centralized formatter
        _format_components_output(components_data, output_format, page_info, response)


def build_component_filter_expression(category: Optional[str] = None,
                                     component_type: Optional[str] = None) -> Optional[str]:
    """Build a filter expression for component API based on provided filters.
    
    Args:
        category: Filter by component category
        component_type: Filter by component type
        
    Returns:
        Filter expression string or None if no filters
    """
    filters = []
    
    if category:
        filters.append(f"'category.name'='{category}'")
    
    if component_type:
        filters.append(f"'componentType'='{component_type}'")
    
    if not filters:
        return None
    
    # Join filters with AND
    return ':AND:'.join(filters)


def _print_components_table(components: list, page_info: dict):
    """Print components in a formatted table."""
    from ..utils.table import TableFormatter

    if not components:
        click.echo("No components found.")
        return

    # Create table headers
    headers = ['ID', 'Name', 'Reference ID', 'Category', 'Type', 'Description']

    # Create table rows
    rows = []
    for component in components:
        # Truncate long fields for display
        name = component.get('name', '')
        if len(name) > 40:
            name = name[:37] + '...'
        
        description = component.get('description', '') or ''
        if len(description) > 50:
            description = description[:47] + '...'
        
        row = [
            component.get('id', '')[:8] + '...' if len(component.get('id', '')) > 8 else component.get('id', ''),
            name,
            component.get('referenceId', ''),
            component.get('category', {}).get('name', ''),
            component.get('componentType', ''),
            description
        ]
        rows.append(row)

    if not rows:
        click.echo("No components found in the response.")
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

        click.echo(f"\nShowing {len(rows)} components (page {current_page} of {total_pages})")
    else:
        click.echo(f"\nShowing {len(rows)} components")


def _format_components_output(components_data: list, output_format: str, 
                             page_info: dict, full_response: dict):
    """Format and print components output using centralized formatters."""
    
    # Define field mappings for components
    field_mappings = [
        {'key': 'id', 'truncate': 12},
        {'key': 'referenceId'},
        {'key': 'name'},
        {'key': 'category.name', 'csv_key': 'category'},
        {'key': 'componentType', 'csv_key': 'type'},
        {'key': 'description', 'truncate': 50}
    ]
    
    # Create table headers
    table_headers = ['ID', 'Reference ID', 'Name', 'Category', 'Type', 'Description']
    
    # Create CSV headers
    csv_headers = ['id', 'referenceId', 'name', 'category', 'type', 'description']
    
    # Create transformers
    row_transformer = TableFormatter.create_row_transformer(field_mappings)
    csv_transformer = TableFormatter.create_csv_transformer(field_mappings)
    
    # Format and print output
    format_and_print_list(
        items=components_data,
        output_format=output_format,
        table_headers=table_headers,
        csv_headers=csv_headers,
        row_transformer=row_transformer,
        csv_transformer=csv_transformer,
        title=None,
        page_info=page_info,
        full_response=full_response
    )


def _print_component_details(component: dict):
    """Print detailed component information in a formatted table."""
    from ..utils.table import TableFormatter
    
    click.echo("Component Details")
    click.echo("=" * 50)
    
    # Basic information
    basic_info = [
        ['ID', component.get('id', 'N/A')],
        ['Reference ID', component.get('referenceId', 'N/A')],
        ['Name', component.get('name', 'N/A')],
        ['Category', component.get('category', {}).get('name', 'N/A')],
        ['Component Type', component.get('componentType', 'N/A')],
        ['Custom Icon', component.get('customIcon', 'N/A')]
    ]
    
    formatter = TableFormatter()
    formatter.print_table(basic_info, ['Field', 'Value'])
    
    # Description
    description = component.get('description', '')
    if description:
        click.echo(f"\nDescription:")
        click.echo("-" * 20)
        click.echo(description)
    
    # Links
    links = component.get('_links', {})
    if links:
        click.echo(f"\nLinks:")
        click.echo("-" * 20)
        for link_name, link_data in links.items():
            if isinstance(link_data, dict) and 'href' in link_data:
                click.echo(f"{link_name}: {link_data['href']}")
            else:
                click.echo(f"{link_name}: {link_data}")
