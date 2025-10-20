"""OTM (Open Threat Model) commands for IriusRisk CLI."""

import click
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..container import get_container
from ..api_client import IriusRiskApiClient
from ..config import Config
from ..utils.project import resolve_project_id, get_project_context_info
from ..services.version_service import VersionService

logger = logging.getLogger(__name__)


@click.group()
def otm():
    """OTM (Open Threat Model) import/export operations.
    
    These commands allow you to import and export threat models using
    the Open Threat Model (OTM) format.
    
    Examples:
        iriusrisk otm import example.otm           # Import OTM file as new project
        iriusrisk otm import example.otm --update PROJECT_ID  # Update existing project
        iriusrisk otm export PROJECT_ID           # Export project as OTM
        iriusrisk otm export PROJECT_ID -o file.otm  # Export to specific file
    """
    pass


@otm.command()
@click.argument('otm_file', type=click.Path(exists=True, readable=True))
@click.option('--update', '-u', help='Update existing project by ID instead of auto-detecting')
@click.option('--no-auto-update', is_flag=True, help='Disable automatic update if project exists')
@click.option('--format', 'output_format', type=click.Choice(['json', 'table']), 
              default='table', help='Output format')
def import_cmd(otm_file: str, update: Optional[str], no_auto_update: bool, output_format: str):
    """Import an OTM file to create or update a project.
    
    By default, if a project with the same ID already exists, it will be automatically
    updated. Use --no-auto-update to disable this behavior.
    
    Args:
        OTM_FILE: Path to the OTM file to import
        
    Examples:
        iriusrisk otm import example.otm                    # Create new or auto-update existing
        iriusrisk otm import example.otm -u PROJECT_ID      # Update specific project
        iriusrisk otm import example.otm --no-auto-update   # Only create, fail if exists
        iriusrisk otm import example.otm --format json      # Output as JSON
    """
    otm_path = Path(otm_file)
    
    if not otm_path.exists():
        click.echo(f"Error: OTM file '{otm_file}' not found", err=True)
        raise click.Abort()
    
    try:
        # Get API client from container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        
        # Check for auto-versioning configuration
        config = Config()
        project_config = config.get_project_config()
        auto_versioning_enabled = project_config and project_config.get('auto_versioning', False)
        
        # Handle auto-versioning if enabled and we're updating a project
        if auto_versioning_enabled and update:
            logger.info("Auto-versioning is enabled, creating backup version before import")
            click.echo("📸 Auto-versioning enabled: Creating backup version before import...")
            
            try:
                version_service = container.get(VersionService)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                version_name = f"Auto-backup before import {timestamp}"
                
                # Create version and wait for completion
                version_service.create_version(
                    project_id=update,
                    name=version_name,
                    description="Automatic backup created by CLI before OTM import",
                    wait=True,
                    timeout=300
                )
                click.echo("✅ Backup version created successfully")
            except Exception as e:
                # Log the error but continue with import
                logger.warning(f"Failed to create backup version: {e}")
                click.echo(f"⚠️  Warning: Could not create backup version: {e}")
                click.echo("   Continuing with import...")
        
        if update:
            # Explicit update of existing project
            click.echo(f"Updating project '{update}' with OTM file: {otm_file}")
            result = api_client.update_project_with_otm_file(update, str(otm_path))
            result['action'] = 'updated'
        else:
            # Create new project or auto-update if exists
            click.echo(f"Importing OTM file: {otm_file}")
            auto_update = not no_auto_update
            result = api_client.import_otm_file(str(otm_path), auto_update=auto_update)
        
        if output_format == 'json':
            click.echo(json.dumps(result, indent=2))
        else:
            # Extract key information for table display
            project_id = result.get('id', 'Unknown')
            project_name = result.get('name', 'Unknown')
            action = result.get('action', 'processed')
            
            click.echo(f"\n✓ Project successfully {action}!")
            click.echo(f"  ID: {project_id}")
            click.echo(f"  Name: {project_name}")
            
            if 'ref' in result:
                click.echo(f"  Reference: {result['ref']}")
            
    except Exception as e:
        click.echo(f"Error importing OTM file: {str(e)}", err=True)
        raise click.Abort()


# Create an alias for the import command since 'import' is a Python keyword
import_cmd.name = 'import'


@otm.command()
@click.argument('project_id', required=False)
@click.option('--output', '-o', help='Output file path (default: stdout)')
@click.option('--format', 'output_format', type=click.Choice(['otm', 'json']), 
              default='otm', help='Output format')
def export(project_id: Optional[str], output: Optional[str], output_format: str):
    """Export a project as OTM format.
    
    If no project ID is provided, it will use the default project from the
    local configuration.
    
    Args:
        PROJECT_ID: ID or reference of the project to export (optional if default project configured)
        
    Examples:
        iriusrisk otm export                    # Export default project to stdout
        iriusrisk otm export PROJECT_ID         # Export specific project to stdout
        iriusrisk otm export PROJECT_ID -o file.otm  # Save to file
        iriusrisk otm export PROJECT_ID --format json  # Export as JSON
    """
    try:
        # Resolve project ID from argument or default configuration
        resolved_project_id = resolve_project_id(project_id)
        
        # Show context information if using default project
        if not project_id:
            project_name = get_project_context_info()
            if project_name:
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        click.echo(f"Exporting project '{resolved_project_id}' as OTM...")
        
        # Get API client from container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        otm_content = api_client.export_project_as_otm(resolved_project_id)
        
        if output_format == 'json':
            # Try to parse as YAML and convert to JSON for pretty printing
            try:
                import yaml
                parsed = yaml.safe_load(otm_content)
                formatted_content = json.dumps(parsed, indent=2)
            except ImportError:
                # yaml not available, just output as-is
                formatted_content = otm_content
            except (TypeError, AttributeError, ValueError):
                # YAML parsing failed, output as-is
                formatted_content = otm_content
        else:
            formatted_content = otm_content
        
        if output:
            # Write to file
            output_path = Path(output)
            output_path.write_text(formatted_content, encoding='utf-8')
            click.echo(f"✓ Project exported to: {output}")
        else:
            # Output to stdout
            click.echo("\n" + "="*50)
            click.echo(formatted_content)
            click.echo("="*50)
            
    except Exception as e:
        if "resolved_project_id" in locals():
            click.echo(f"Error exporting project: {str(e)}", err=True)
        raise click.Abort()


@otm.command()
def example():
    """Generate an example OTM file for testing.
    
    This creates a sample OTM file that demonstrates the basic structure
    and can be used for testing the import functionality.
    
    Examples:
        iriusrisk otm example > example.otm       # Create example file
        iriusrisk otm example                     # View example content
    """
    example_otm = """otmVersion: 0.1.0
project:
  name: "Example Web Application"
  id: "example-web-app"
  description: "A sample web application threat model for testing OTM import"

trustZones:
  - id: "internet"
    name: "Internet"
    risk:
      trustRating: 1
  
  - id: "public-cloud"
    name: "Public Cloud"
    risk:
      trustRating: 3
  
  - id: "private-secured"
    name: "Private Secured"
    risk:
      trustRating: 10

components:
  - id: "web-client"
    name: "Web Client"
    type: "web-application-client-side"
    parent:
      trustZone: "internet"
    
  - id: "web-server"
    name: "Web Server"
    type: "web-application-server-side"
    parent:
      trustZone: "public-cloud"
    
  - id: "database"
    name: "Database"
    type: "sql-database"
    parent:
      trustZone: "private-secured"

dataflows:
  - id: "client-to-server"
    name: "HTTP Requests"
    source: "web-client"
    destination: "web-server"
    
  - id: "server-to-db"
    name: "Database Queries"
    source: "web-server"
    destination: "database"

threats:
  - id: "sql-injection"
    name: "SQL Injection Attack"
    description: "Attacker could inject malicious SQL code"
    categories: ["injection"]
    cwes: ["89"]
    risk:
      likelihood: 4
      impact: 4
    
  - id: "xss-attack"
    name: "Cross-Site Scripting"
    description: "Malicious scripts executed in user's browser"
    categories: ["injection"]
    cwes: ["79"]
    risk:
      likelihood: 3
      impact: 3

mitigations:
  - id: "input-validation"
    name: "Input Validation"
    description: "Validate and sanitize all user inputs"
    riskReduction: 30
    
  - id: "output-encoding"
    name: "Output Encoding"
    description: "Encode output to prevent script execution"
    riskReduction: 25
"""
    
    click.echo(example_otm)
