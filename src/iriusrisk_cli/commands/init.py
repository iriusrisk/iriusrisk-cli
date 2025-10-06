"""Init command for IriusRisk CLI."""

import click
import json
import re
import secrets
import string
from pathlib import Path
from typing import Optional
from ..container import get_container
from ..services.project_service import ProjectService


def _generate_reference_id(project_name: str) -> str:
    """Generate a human-readable reference ID from a project name.
    
    Converts the project name to lowercase, replaces spaces with hyphens,
    removes non-alphanumeric characters (except hyphens), and adds a short
    random alphanumeric string for uniqueness.
    
    Args:
        project_name: The project name to convert
        
    Returns:
        A human-readable reference ID
        
    Examples:
        "My Web App" -> "my-web-app-x7k2"
        "API Gateway Service!" -> "api-gateway-service-m9n4"
    """
    # Convert to lowercase and replace spaces with hyphens
    ref_id = project_name.lower().replace(' ', '-')
    
    # Remove non-alphanumeric characters except hyphens
    ref_id = re.sub(r'[^a-z0-9-]', '', ref_id)
    
    # Remove multiple consecutive hyphens
    ref_id = re.sub(r'-+', '-', ref_id)
    
    # Remove leading/trailing hyphens
    ref_id = ref_id.strip('-')
    
    # If the result is empty or too short, use a default
    if not ref_id or len(ref_id) < 3:
        ref_id = 'project'
    
    # Add a short random alphanumeric string for uniqueness
    random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    
    return f"{ref_id}-{random_suffix}"


@click.command()
@click.option('--name', '-n', help='Project name (will prompt if not provided)')
@click.option('--project-ref', '-p', help='Project reference ID (will generate from name if not provided)')
@click.option('--existing-ref', '-r', help='Existing project reference ID to fetch from IriusRisk instance')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing .iriusRisk directory')
def init(name: Optional[str], project_ref: Optional[str], existing_ref: Optional[str], force: bool):
    """Initialize a new or existing IriusRisk project in the current directory.
    
    This command creates a .iriusRisk directory with a project.json file
    containing project configuration. This allows other commands to use
    the project by default without requiring a project ID parameter.
    
    You can initialize either a new project (with generated or provided details)
    or an existing project by providing its reference ID.
    
    Examples:
        iriusrisk init                           # Interactive setup for new project
        iriusrisk init -n "My Web App"          # Set project name for new project
        iriusrisk init -n "My App" -p abc123    # Set name and project ID for new project
        iriusrisk init -r "my-project-ref"      # Initialize existing project by reference ID
        iriusrisk init --force                  # Overwrite existing config
    """
    current_dir = Path.cwd()
    irisrisk_dir = current_dir / ".iriusRisk"
    project_file = irisrisk_dir / "project.json"
    
    # Check if .iriusRisk directory already exists
    if irisrisk_dir.exists() and not force:
        click.echo(f"❌ .iriusRisk directory already exists in {current_dir}")
        click.echo("Use --force to overwrite existing configuration.")
        raise click.Abort()
    
    # Handle existing project initialization
    if existing_ref:
        click.echo(f"🔍 Fetching project metadata for reference ID: {existing_ref}")
        try:
            # Search for project by reference ID using Container
            container = get_container()
            project_service = container.get(ProjectService)
            filter_expr = f"'referenceId'='{existing_ref}'"
            result = project_service.list_projects(page=0, size=1, custom_filter=filter_expr)
            
            projects = result.get('projects', [])
            if not projects:
                click.echo(f"❌ No project found with reference ID '{existing_ref}'", err=True)
                raise click.Abort()
            elif len(projects) > 1:
                click.echo(f"❌ Multiple projects found with reference ID '{existing_ref}'. This shouldn't happen.", err=True)
                raise click.Abort()
            
            project_data = projects[0]
            click.echo(f"✅ Found project: {project_data.get('name', 'N/A')}")
            
            # Use fetched project data
            name = project_data.get('name', '')
            project_id = project_data.get('id', '')
            description = project_data.get('description', '')
            reference_id = project_data.get('referenceId', '')
            
            # Create enhanced project configuration with fetched metadata
            project_config = {
                "name": name,
                "project_id": project_id,
                "reference_id": reference_id,
                "description": description or f"IriusRisk project configuration for {name}",
                "created_at": str(Path.cwd()),
                "initialized_from": "existing_project",
                "metadata": {
                    "state": project_data.get('state'),
                    "tags": project_data.get('tags', []),
                    "is_archived": project_data.get('isArchived', False),
                    "is_blueprint": project_data.get('isBlueprint', False),
                    "workflow_state": project_data.get('workflowState', {}),
                    "version": project_data.get('version', {}),
                    "model_updated": project_data.get('modelUpdated')
                }
            }
            
        except Exception as e:
            click.echo(f"❌ Failed to fetch project metadata: {e}", err=True)
            raise click.Abort()
    
    else:
        # Handle new project initialization
        # Get project name
        if not name:
            name = click.prompt("Project name", type=str)
        
        # Generate or use provided reference ID
        if not project_ref:
            reference_id = _generate_reference_id(name)
            click.echo(f"Generated reference ID: {reference_id}")
        else:
            reference_id = project_ref
        
        # Create project configuration for new project
        project_config = {
            "name": name,
            "reference_id": reference_id,
            "created_at": str(Path.cwd()),
            "description": f"IriusRisk project configuration for {name}",
            "initialized_from": "new_project"
        }
    
    try:
        # Create .iriusRisk directory
        irisrisk_dir.mkdir(exist_ok=True)
        
        # Write project.json file
        with open(project_file, 'w') as f:
            json.dump(project_config, f, indent=2)
        
        if existing_ref:
            click.echo(f"✅ Initialized existing IriusRisk project: {name}")
            click.echo(f"📁 Project directory: {irisrisk_dir}")
            click.echo(f"🆔 Project UUID: {project_config.get('project_id', 'N/A')}")
            click.echo(f"🔗 Reference ID: {project_config.get('reference_id', 'N/A')}")
            if project_config.get('description'):
                click.echo(f"📝 Description: {project_config['description']}")
        else:
            click.echo(f"✅ Initialized new IriusRisk project: {name}")
            click.echo(f"📁 Project directory: {irisrisk_dir}")
            click.echo(f"🔗 Reference ID: {project_config.get('reference_id', 'N/A')}")
        
        click.echo()
        click.echo("This project will be used by default in other commands.")
        click.echo("You can override the project by providing a project ID or reference ID to specific commands.")
        
    except Exception as e:
        click.echo(f"❌ Failed to initialize project: {e}")
        raise click.Abort()
