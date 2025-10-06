"""
Issue tracker command module for IriusRisk CLI.

This module provides functionality to list, show, and manage issue tracker
profiles within IriusRisk.
"""

import click
import json
from typing import Optional
from ..container import get_container
from ..api_client import IriusRiskApiClient
from ..utils.project import resolve_project_id, get_project_context_info, get_project_config, update_project_config
from ..utils.project_resolution import resolve_project_id_to_uuid as _resolve_project_id_to_uuid


@click.group(name='issue-tracker')
def issue_tracker():
    """Manage issue tracker profiles and integrations.
    
    This command group provides functionality to list, show, and configure
    issue tracker profiles for creating tickets from countermeasures.
    """
    pass


@issue_tracker.command()
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
def list(output_format: str):
    """List all available issue tracker profiles."""
    try:
        # Get all issue tracker profiles using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        response = api_client.get_issue_tracker_profiles()
        
        # Handle response format
        if isinstance(response, dict):
            profiles_data = response.get('_embedded', {}).get('items', [])
            page_info = response.get('page', {})
        else:
            profiles_data = response if response else []
            page_info = {}

        if not profiles_data:
            click.echo("No issue tracker profiles found.")
            return

        # Format output
        if output_format == 'json':
            click.echo(json.dumps(response, indent=2))
        else:  # table format
            _print_issue_tracker_profiles_table(profiles_data, page_info)

    except Exception as e:
        click.echo(f"Error retrieving issue tracker profiles: {e}", err=True)
        raise click.Abort()


@issue_tracker.command()
@click.argument('tracker_id')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
def show(tracker_id: str, output_format: str):
    """Show detailed information about a specific issue tracker profile.
    
    Args:
        tracker_id: Issue tracker profile ID or name
    """
    try:
        # Get all issue tracker profiles and find the specific one using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        response = api_client.get_issue_tracker_profiles()
        
        # Handle response format
        if isinstance(response, dict):
            profiles_data = response.get('_embedded', {}).get('items', [])
        else:
            profiles_data = response if response else []
        
        # Find the specific profile by ID or name
        profile_data = None
        for profile in profiles_data:
            if (profile.get('id') == tracker_id or 
                profile.get('name') == tracker_id):
                profile_data = profile
                break
        
        if not profile_data:
            click.echo(f"Issue tracker profile '{tracker_id}' not found.", err=True)
            raise click.Abort()
        
        # Format output
        if output_format == 'json':
            click.echo(json.dumps(profile_data, indent=2))
        else:  # table format
            _print_issue_tracker_profile_details(profile_data)

    except Exception as e:
        click.echo(f"Error retrieving issue tracker profile '{tracker_id}': {e}", err=True)
        raise click.Abort()


@issue_tracker.command()
@click.argument('search_string')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
def search(search_string: str, output_format: str):
    """Search issue tracker profiles by name or type.
    
    This command performs a search across issue tracker profile names and types.
    
    Examples:
        # Search for issue trackers containing "jira"
        iriusrisk issue-tracker search "jira"
        
        # Search with JSON output
        iriusrisk issue-tracker search "github" --format json
    
    Args:
        search_string: String to search for in issue tracker names and types
    """
    try:
        if not search_string.strip():
            click.echo("Error: Search string cannot be empty.", err=True)
            raise click.Abort()
        
        # Get all issue tracker profiles using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        response = api_client.get_issue_tracker_profiles()
        
        # Handle response format
        if isinstance(response, dict):
            all_profiles = response.get('_embedded', {}).get('items', [])
            page_info = response.get('page', {})
        else:
            all_profiles = response if response else []
            page_info = {}
        
        if not all_profiles:
            click.echo("No issue tracker profiles found.")
            return
        
        # Perform client-side search filtering
        search_term = search_string.lower()
        filtered_profiles = []
        
        for profile in all_profiles:
            name = profile.get('name', '').lower()
            tracker_type = profile.get('issueTrackerType', '').lower()
            profile_id = profile.get('id', '').lower()
            
            # Search in name, type, and ID
            if (search_term in name or 
                search_term in tracker_type or 
                search_term in profile_id):
                filtered_profiles.append(profile)
        
        click.echo(f"Searching issue tracker profiles for: '{search_string}'")
        click.echo()
        
        if not filtered_profiles:
            click.echo(f"No issue tracker profiles found matching '{search_string}'.")
            return
        
        # Show search results summary
        click.echo(f"Found {len(filtered_profiles)} issue tracker profile(s) matching '{search_string}':")
        click.echo()
        
        # Format output
        if output_format == 'json':
            click.echo(json.dumps(filtered_profiles, indent=2))
        else:  # table format
            _print_issue_tracker_profiles_table(filtered_profiles, page_info)
    
    except Exception as e:
        click.echo(f"Error searching issue tracker profiles: {e}", err=True)
        raise click.Abort()


@issue_tracker.command(name='set-default')
@click.argument('tracker_identifier')
@click.option('--project', '-p', help='Project ID (optional if default project configured)')
def set_default(tracker_identifier: str, project: Optional[str]):
    """Set the default issue tracker for a project.
    
    Args:
        tracker_identifier: Issue tracker profile ID or name
        project: Project ID (optional if default project configured)
    """
    try:
        # Show context information if using default project
        if not project:
            project_name = get_project_context_info()
            if project_name:
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        # Get all issue tracker profiles to validate the identifier using container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        response = api_client.get_issue_tracker_profiles()
        
        # Handle response format
        if isinstance(response, dict):
            profiles_data = response.get('_embedded', {}).get('items', [])
        else:
            profiles_data = response if response else []
        
        # Find the specific profile by ID or name
        selected_profile = None
        for profile in profiles_data:
            if (profile.get('id') == tracker_identifier or 
                profile.get('name') == tracker_identifier):
                selected_profile = profile
                break
        
        if not selected_profile:
            click.echo(f"Issue tracker profile '{tracker_identifier}' not found.", err=True)
            click.echo("\nAvailable issue tracker profiles:")
            _print_issue_tracker_profiles_table(profiles_data, {})
            raise click.Abort()
        
        # Update project configuration
        try:
            config = get_project_config()
            if not config:
                click.echo("No project configuration found. Please run 'iriusrisk init' first.", err=True)
                raise click.Abort()
            
            # Add default issue tracker to configuration
            config['default_issue_tracker'] = {
                'id': selected_profile.get('id'),
                'name': selected_profile.get('name'),
                'type': selected_profile.get('issueTrackerType')
            }
            
            update_project_config(config)
            
            click.echo(f"✅ Successfully set default issue tracker to '{selected_profile.get('name')}' ({selected_profile.get('issueTrackerType')})")
            
        except Exception as config_error:
            click.echo(f"Error updating project configuration: {config_error}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error setting default issue tracker: {e}", err=True)
        raise click.Abort()


def _print_issue_tracker_profiles_table(profiles: list, page_info: dict):
    """Print issue tracker profiles in a formatted table."""
    from ..utils.table import TableFormatter

    if not profiles:
        click.echo("No issue tracker profiles found.")
        return

    # Create table headers
    headers = ['ID', 'Name', 'Type', 'Status']

    # Create table rows
    rows = []
    for profile in profiles:
        # Determine status based on published/draft state
        status = "Published" if profile.get('published') else "Draft"
        if profile.get('default', False):
            status += " (Default)"
        
        row = [
            profile.get('id', '')[:8] + '...',  # Truncate ID for readability
            profile.get('name', ''),
            profile.get('issueTrackerType', ''),
            status
        ]
        rows.append(row)

    if not rows:
        click.echo("No issue tracker profiles found in the response.")
        return

    # Print table
    formatter = TableFormatter()
    formatter.print_table(rows, headers)

    # Print pagination info
    if page_info:
        total_elements = page_info.get('totalElements', 0)
        total_pages = page_info.get('totalPages', 0)
        current_page = page_info.get('number', 0) + 1
        
        click.echo(f"\nShowing {len(rows)} issue tracker profiles (page {current_page} of {total_pages})")
    else:
        click.echo(f"\nShowing {len(rows)} issue tracker profiles")


def _print_issue_tracker_profile_details(profile: dict):
    """Print detailed issue tracker profile information in a formatted table."""
    from ..utils.table import TableFormatter
    
    click.echo("Issue Tracker Profile Details")
    click.echo("=" * 50)
    
    # Basic information
    basic_info = [
        ['ID', profile.get('id', 'N/A')],
        ['Name', profile.get('name', 'N/A')],
        ['Type', profile.get('issueTrackerType', 'N/A')],
        ['Assignment Type', profile.get('issueTrackerAssignmentType', 'N/A')],
        ['Default', 'Yes' if profile.get('default', False) else 'No'],
        ['Status', 'Published' if profile.get('published') else 'Draft']
    ]
    
    formatter = TableFormatter()
    formatter.print_table(basic_info, ['Field', 'Value'])
    
    # Additional details if available
    if profile.get('published'):
        published_info = profile.get('published', {})
        if published_info:
            click.echo(f"\nPublished Configuration:")
            click.echo("-" * 30)
            click.echo(f"Name: {published_info.get('name', 'N/A')}")
            click.echo(f"Type: {published_info.get('issueTrackerType', 'N/A')}")
    
    if profile.get('draft'):
        draft_info = profile.get('draft', {})
        if draft_info:
            click.echo(f"\nDraft Configuration:")
            click.echo("-" * 30)
            click.echo(f"Name: {draft_info.get('name', 'N/A')}")
            click.echo(f"Type: {draft_info.get('issueTrackerType', 'N/A')}")
