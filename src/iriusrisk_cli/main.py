"""Main CLI module for IriusRisk CLI."""

import click
import atexit
from .cli_context import setup_cli_context, cleanup_cli_context
from .commands.projects import project
from .commands.otm import otm
from .commands.mcp import mcp
from .commands.init import init
from .commands.threats import threat
from .commands.countermeasures import countermeasure
from .commands.sync import sync
from .commands.components import component
from .commands.updates import updates
from .commands.reports import reports
from .commands.issue_trackers import issue_tracker
from .commands.config_cmd import config
from .commands.versions import versions


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version and exit')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output to stderr')
@click.option('--debug', is_flag=True, help='Enable debug output to stderr')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.option('--log-file', type=click.Path(), help='Write logs to specified file')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARN', 'ERROR'], case_sensitive=False), help='Set log level')
@click.pass_context
def cli(ctx, version, verbose, debug, quiet, log_file, log_level):
    """IriusRisk CLI - A command line interface for IriusRisk API v2.
    
    This tool enables developers and security engineers to integrate 
    IriusRisk into their software development lifecycle.
    
    \b
    Quick Start:
      iriusrisk config set-hostname <hostname>
      iriusrisk config set-api-key
      iriusrisk init
      iriusrisk project list
    
    \b
    For detailed help run:
      iriusrisk help
    """
    # Configure logging based on CLI options and environment variables
    from .utils.logging_config import configure_cli_logging
    import os
    
    # Check environment variables for defaults
    env_debug = os.getenv('IRIUSRISK_DEBUG', '').lower() in ('true', '1', 'yes')
    env_log_file = os.getenv('IRIUSRISK_LOG_FILE')
    
    # Resolve logging configuration
    is_debug = debug or env_debug
    is_verbose = verbose or is_debug
    resolved_log_file = log_file or env_log_file
    
    # Configure logging early
    configure_cli_logging(
        debug=is_debug,
        verbose=is_verbose, 
        quiet=quiet,
        log_file=resolved_log_file,
        log_level=log_level
    )
    
    # Set up CLI context with dependency injection
    if ctx.obj is None:
        ctx.obj = setup_cli_context()
        # Store logging config in context for commands to access
        ctx.obj.logging_config = {
            'debug': is_debug,
            'verbose': is_verbose,
            'quiet': quiet,
            'log_file': resolved_log_file,
            'log_level': log_level
        }
        # Register cleanup function to run on exit
        atexit.register(cleanup_cli_context)
    
    if version:
        from . import __version__
        click.echo(f"IriusRisk CLI version {__version__}")
        return
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
def help():
    """Show detailed help information for IriusRisk CLI.
    
    This command provides comprehensive help including examples,
    configuration instructions, and available commands.
    """
    help_text = """
IriusRisk CLI - Command Line Interface for IriusRisk API v2

DESCRIPTION:
    This tool enables developers and security engineers to integrate 
    IriusRisk into their software development lifecycle through a 
    command-line interface.

CONFIGURATION:
    Before using the CLI, you need to configure your IriusRisk connection.
    
    Option 1 - User-level configuration (recommended):
        iriusrisk config set-hostname https://your-instance.iriusrisk.com
        iriusrisk config set-api-key  # Prompts securely for API key
        iriusrisk config show  # View current configuration
        
    Option 2 - Environment variables:
        export IRIUS_HOSTNAME=https://your-instance.iriusrisk.com
        export IRIUS_API_KEY=your-api-token-here
        
    Option 3 - Project .env file:
        echo "IRIUS_HOSTNAME=https://your-instance.iriusrisk.com" > .env
        echo "IRIUS_API_KEY=your-api-token-here" >> .env
    
    Configuration priority (highest to lowest):
        1. Environment variables (IRIUS_HOSTNAME, IRIUS_API_KEY)
        2. Project .env file
        3. Project config (.iriusrisk/project.json - hostname only)
        4. User config (~/.iriusrisk/config.json)

LOGGING OPTIONS:
    By default, the CLI operates quietly with minimal output. Use these options to control logging:
    
    --verbose, -v                     # Enable verbose output to stderr
    --debug                           # Enable debug output to stderr
    --quiet, -q                       # Suppress non-essential output
    --log-file FILE                   # Write logs to specified file
    --log-level LEVEL                 # Set specific log level (DEBUG, INFO, WARN, ERROR)
    
    Environment variables:
    IRIUSRISK_DEBUG=1                 # Enable debug mode
    IRIUSRISK_LOG_FILE=debug.log      # Set log file path

BASIC USAGE:
    iriusrisk help                    # Show this detailed help
    iriusrisk --help                  # Show basic command help
    iriusrisk --version               # Show version information
    iriusrisk test                    # Test API connection and authentication
    
    # With logging options
    iriusrisk --verbose project list # Show progress information
    iriusrisk --debug project list   # Show detailed debug information
    iriusrisk --quiet project list   # Minimal output, only results

AVAILABLE COMMANDS:
    Configuration:
        iriusrisk config set-hostname <hostname>        # Set default hostname
        iriusrisk config set-api-key                    # Set default API key (prompts securely)
        iriusrisk config show                           # Show current configuration
    
    Project Initialization:
        iriusrisk init                              # Initialize new project configuration
        iriusrisk init -n "My Web App"             # Initialize new project with name
        iriusrisk init -n "My App" -p abc123       # Initialize new project with name and ID
        iriusrisk init -r "my-project-ref"         # Initialize existing project by reference ID
        iriusrisk init --force                     # Overwrite existing configuration
    Project Management:
        iriusrisk project list                              # List visible projects
        iriusrisk project list --name "web"                 # Filter by name
        iriusrisk project list --tags "prod critical"       # Filter by tags
        iriusrisk project list --format json                # Output as JSON
        iriusrisk project show <project_id>                 # Show detailed project info
        
    Threat Management:
        iriusrisk threat list                               # List threats from default project
        iriusrisk threat list <project_id>                  # List threats from specific project
        iriusrisk threat show <threat_id>                   # Show detailed threat info
        iriusrisk threat search "SQL injection"             # Search threats by string
        iriusrisk threat update <threat_id> --status accept # Update threat status
        
    Countermeasure Management:
        iriusrisk countermeasure list                       # List countermeasures from default project
        iriusrisk countermeasure list <project_id>          # List countermeasures from specific project
        iriusrisk countermeasure show <countermeasure_id>   # Show detailed countermeasure info
        iriusrisk countermeasure search "authentication"    # Search countermeasures by string
        iriusrisk countermeasure update <cm_id> --status required # Update countermeasure status
        
    Data Synchronization:
        iriusrisk sync                                      # Sync all data from default project
        iriusrisk sync <project_id>                         # Sync all data from specific project
        iriusrisk sync --threats-only                       # Sync only threats data
        iriusrisk sync --countermeasures-only               # Sync only countermeasures data
        iriusrisk sync --components-only                    # Sync only system components data
        iriusrisk sync -o /path/to/output                   # Sync to custom output directory
        
    System Components:
        iriusrisk component list                            # List system components
        iriusrisk component show <component_id>             # Show detailed component info
        iriusrisk component search "database"               # Search components by string
        iriusrisk component list --category "Database"      # Filter by category
        iriusrisk component list --type "project-component" # Filter by type
        
    Reports:
        iriusrisk reports generate                          # Generate countermeasure report (default)
        iriusrisk reports generate --type threat --format pdf # Generate threat report as PDF
        iriusrisk reports generate --type compliance --standard owasp-top-10-2021 # Generate compliance report
        iriusrisk reports standards                         # List available compliance standards
        iriusrisk reports types                             # List available report types
        iriusrisk reports list                              # List generated reports
        
    Issue Tracker Integration:
        iriusrisk issue-tracker list                        # List available issue tracker profiles
        iriusrisk issue-tracker show <tracker-id>           # Show issue tracker details
        iriusrisk issue-tracker set-default <tracker-name>  # Set default issue tracker for project
        iriusrisk countermeasure create-issue <cm-id>       # Create issue for countermeasure
        iriusrisk countermeasure create-issue <cm-id> --tracker "Jira" # Create issue with specific tracker
        
    OTM (Open Threat Model):
        iriusrisk otm example                               # Generate example OTM file
        iriusrisk otm import example.otm                    # Import OTM file (auto-validates against schema)
        iriusrisk otm import example.otm --reset-layout     # Import and reset diagram layout
        iriusrisk otm export PROJECT_ID                     # Export project as OTM format
        iriusrisk otm export PROJECT_ID -o file.otm        # Export to specific file
        
    MCP (Model Context Protocol):
        iriusrisk mcp                                       # MCP server (invoked by AI tools via stdio, not run directly)
        iriusrisk mcp-example                               # Generate example mcp.json configuration file
        
PLANNED COMMANDS (coming soon):
    Project Management:
        iriusrisk project fetch <project_id>                # Download project data

EXAMPLES:
    # Set up configuration (recommended)
    iriusrisk config set-hostname https://your-instance.iriusrisk.com
    iriusrisk config set-api-key  # Prompts securely for API key
    
    # Or use environment variables / .env file
    echo "IRIUS_HOSTNAME=https://your-instance.iriusrisk.com" > .env
    echo "IRIUS_API_KEY=your-api-token-here" >> .env
    
    # Test your connection
    iriusrisk test
    
    # Initialize a new project
    iriusrisk init -n "My Web Application"
    
    # Initialize an existing project
    iriusrisk init -r "my-existing-project"
    
    # Get help
    iriusrisk help
    
    # Check version
    iriusrisk --version

For more information, visit: https://github.com/iriusrisk/iriusrisk-cli
    """
    click.echo(help_text)


@cli.command()
def version():
    """Show version information."""
    from . import __version__
    click.echo(f"IriusRisk CLI version {__version__}")


@cli.command()
@click.pass_context
def test(ctx):
    """Test connection to IriusRisk.
    
    This command tests your IriusRisk connection and validates your 
    authentication credentials. It performs a minimal check to confirm
    everything is configured correctly.
    """
    from .utils.error_handling import handle_cli_error
    
    # Set up CLI context if not already done
    if ctx.obj is None:
        ctx.obj = setup_cli_context()
    
    try:
        # Use the health service to test connectivity
        from .services.health_service import HealthService
        health_service = ctx.obj.container.get(HealthService)
        
        click.echo("Testing connection to IriusRisk...")
        
        # Get instance info
        info_result = health_service.get_instance_info()
        click.echo("✓ Connection successful!")
        
        version = info_result.get('version', 'unknown')
        click.echo(f"✓ IriusRisk version: {version}")
            
    except Exception as e:
        handle_cli_error(e, "testing connection")


@cli.command(name='mcp-example')
def mcp_example():
    """Generate an example mcp.json file for MCP server configuration.
    
    This command generates an example mcp.json file that can be used to configure
    the IriusRisk CLI as an MCP server for AI integration tools like Claude Desktop.
    
    Examples:
        iriusrisk mcp-example > mcp.json          # Save to file
        iriusrisk mcp-example                     # View example content
    """
    import json
    
    example_config = {
        "mcpServers": {
            "iriusrisk-cli": {
                "command": "iriusrisk",
                "args": [
                    "mcp"
                ]
            }
        }
    }
    
    click.echo(json.dumps(example_config, indent=2))


# Add command groups
cli.add_command(config)
cli.add_command(project)
cli.add_command(otm)
cli.add_command(mcp)
cli.add_command(init)
cli.add_command(threat)
cli.add_command(countermeasure)
cli.add_command(sync)
cli.add_command(component)
cli.add_command(updates)
cli.add_command(reports)
cli.add_command(issue_tracker)

# Add versions as subcommand to project
project.add_command(versions)

# Add plural aliases for commands (hidden from help to keep it clean)
# Create hidden aliases that point to the same command groups
@cli.group(name='projects', hidden=True)
def projects_alias():
    """Alias for 'project' command."""
    pass

@cli.group(name='threats', hidden=True)
def threats_alias():
    """Alias for 'threat' command."""
    pass

@cli.group(name='countermeasures', hidden=True)
def countermeasures_alias():
    """Alias for 'countermeasure' command."""
    pass

@cli.group(name='components', hidden=True)
def components_alias():
    """Alias for 'component' command."""
    pass

# Add all subcommands to the aliases
for cmd in project.commands.values():
    projects_alias.add_command(cmd)
for cmd in threat.commands.values():
    threats_alias.add_command(cmd)
for cmd in countermeasure.commands.values():
    countermeasures_alias.add_command(cmd)
for cmd in component.commands.values():
    components_alias.add_command(cmd)

# Also add projects alias to main CLI
cli.add_command(projects_alias)


if __name__ == '__main__':
    cli()
