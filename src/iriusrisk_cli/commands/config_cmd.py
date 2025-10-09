"""Config command for IriusRisk CLI."""

import click
from pathlib import Path
from ..cli_context import pass_cli_context
from ..config import save_user_config


@click.group(name='config')
def config():
    """Manage IriusRisk CLI configuration.
    
    Configure default hostname and API credentials that will be used
    across all projects. Configuration is stored in ~/.iriusrisk/config.json.
    
    Examples:
        iriusrisk config set-hostname https://mycompany.iriusrisk.com
        iriusrisk config set-api-key abc123xyz
        iriusrisk config show
    """
    pass


@config.command(name='show')
@pass_cli_context
def show(cli_ctx):
    """Show current configuration and sources.
    
    Displays the complete configuration cascade showing where each
    value is coming from and what the resolved configuration will be.
    """
    try:
        config = cli_ctx.get_config()
        sources = config.get_config_sources()
        
        click.echo("Configuration Sources:")
        click.echo()
        
        # User config
        user_config = sources.get('user_config')
        user_config_path = Path.home() / ".iriusrisk" / "config.json"
        if user_config:
            click.echo(f"User config ({user_config_path}):")
            if 'hostname' in user_config:
                click.echo(f"  hostname: {user_config['hostname']}")
            if 'api_token' in user_config:
                # Mask API token
                token = user_config['api_token']
                if len(token) > 4:
                    masked_token = f"{'*' * (len(token) - 4)}{token[-4:]}"
                else:
                    masked_token = "****"
                click.echo(f"  api_token: {masked_token}")
        else:
            click.echo(f"User config ({user_config_path}): not found")
        
        click.echo()
        
        # Project config
        project_config = sources.get('project_config')
        project_config_path = Path.cwd() / ".iriusrisk" / "project.json"
        if project_config:
            click.echo(f"Project config ({project_config_path}):")
            if 'name' in project_config:
                click.echo(f"  project_name: {project_config['name']}")
            if 'project_id' in project_config:
                click.echo(f"  project_id: {project_config['project_id']}")
            if 'reference_id' in project_config:
                click.echo(f"  reference_id: {project_config['reference_id']}")
            if 'hostname' in project_config:
                click.echo(f"  hostname: {project_config['hostname']}")
        else:
            click.echo(f"Project config ({project_config_path}): not found")
        
        click.echo()
        
        # Environment variables
        env = sources.get('environment', {})
        click.echo("Environment variables:")
        if env.get('IRIUS_HOSTNAME'):
            click.echo(f"  IRIUS_HOSTNAME: {env['IRIUS_HOSTNAME']}")
        else:
            click.echo("  IRIUS_HOSTNAME: not set")
        
        if env.get('IRIUS_API_KEY'):
            # Mask API key
            key = env['IRIUS_API_KEY']
            if len(key) > 4:
                masked_key = f"{'*' * (len(key) - 4)}{key[-4:]}"
            else:
                masked_key = "****"
            click.echo(f"  IRIUS_API_KEY: {masked_key}")
        else:
            click.echo("  IRIUS_API_KEY: not set")
        
        if env.get('IRIUS_API_TOKEN'):
            # Mask API token
            token = env['IRIUS_API_TOKEN']
            if len(token) > 4:
                masked_token = f"{'*' * (len(token) - 4)}{token[-4:]}"
            else:
                masked_token = "****"
            click.echo(f"  IRIUS_API_TOKEN: {masked_token}")
        else:
            click.echo("  IRIUS_API_TOKEN: not set")
        
        click.echo()
        
        # Project .env file
        if sources.get('project_env_file'):
            click.echo(f"Project .env file: {Path.cwd() / '.env'} (exists)")
        else:
            click.echo("Project .env file: not found")
        
        click.echo()
        click.echo("─" * 60)
        click.echo()
        
        # Resolved configuration
        resolved = sources.get('resolved', {})
        click.echo("Resolved Configuration:")
        
        hostname = resolved.get('hostname')
        hostname_source = resolved.get('hostname_source')
        if hostname:
            click.echo(f"  hostname: {hostname}")
            click.echo(f"    (from: {hostname_source})")
        else:
            click.echo("  hostname: NOT CONFIGURED")
            click.echo("    Set with: iriusrisk config set-hostname <hostname>")
        
        click.echo()
        
        api_token = resolved.get('api_token')
        api_token_source = resolved.get('api_token_source')
        if api_token:
            # Mask API token
            if len(api_token) > 4:
                masked_token = f"{'*' * (len(api_token) - 4)}{api_token[-4:]}"
            else:
                masked_token = "****"
            click.echo(f"  api_token: {masked_token}")
            click.echo(f"    (from: {api_token_source})")
        else:
            click.echo("  api_token: NOT CONFIGURED")
            click.echo("    Set with: iriusrisk config set-api-key <key>")
        
        click.echo()
        
        # Show project info if available
        if project_config and 'name' in project_config:
            project_name = project_config['name']
            project_ref = project_config.get('reference_id', 'N/A')
            click.echo(f"  project: {project_name} ({project_ref})")
        
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Failed to load configuration: {e}", err=True)
        raise click.Abort()


@config.command(name='set-hostname')
@click.argument('hostname')
def set_hostname(hostname: str):
    """Set the default IriusRisk hostname.
    
    Saves the hostname to ~/.iriusrisk/config.json for use across all projects.
    This can be overridden per-project in .iriusrisk/project.json or via
    environment variables.
    
    Examples:
        iriusrisk config set-hostname https://mycompany.iriusrisk.com
        iriusrisk config set-hostname mycompany.iriusrisk.com
    """
    try:
        # Ensure hostname has a scheme
        if not hostname.startswith(('http://', 'https://')):
            hostname = f"https://{hostname}"
        
        save_user_config(hostname=hostname)
        
        user_config_path = Path.home() / ".iriusrisk" / "config.json"
        click.echo(f"✅ Saved hostname to {user_config_path}")
        click.echo(f"   Hostname: {hostname}")
        click.echo()
        click.echo("This hostname will be used by default for all projects.")
        click.echo("Override per-project by setting 'hostname' in .iriusrisk/project.json")
        click.echo("Override per-session by setting IRIUS_HOSTNAME environment variable")
        
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"❌ Failed to save configuration: {e}", err=True)
        raise click.Abort()


@config.command(name='set-api-key')
def set_api_key():
    """Set the default IriusRisk API key.
    
    Prompts for the API key securely (input hidden to prevent shell history capture).
    Saves the API key to ~/.iriusrisk/config.json with secure file permissions.
    This will be used across all projects. Can be overridden via environment
    variables (IRIUS_API_KEY or IRIUS_API_TOKEN).
    
    Examples:
        iriusrisk config set-api-key
        # You will be prompted to enter your API key securely
    """
    try:
        # Prompt for API key with hidden input
        api_key = click.prompt(
            'Enter your IriusRisk API key',
            hide_input=True,
            confirmation_prompt=True,
            type=str
        )
        
        if not api_key or not api_key.strip():
            click.echo("❌ API key cannot be empty", err=True)
            raise click.Abort()
        
        api_key = api_key.strip()
        
        save_user_config(api_token=api_key)
        
        user_config_path = Path.home() / ".iriusrisk" / "config.json"
        click.echo(f"✅ Saved API key to {user_config_path}")
        
        # Mask the key for display
        if len(api_key) > 4:
            masked_key = f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"
        else:
            masked_key = "****"
        click.echo(f"   API key: {masked_key}")
        click.echo()
        click.echo("This API key will be used by default for all projects.")
        click.echo("Override per-session by setting IRIUS_API_KEY or IRIUS_API_TOKEN environment variable")
        click.echo()
        click.echo("⚠️  Security note:")
        click.echo("   - File permissions set to 0600 (owner read/write only)")
        click.echo("   - API key not stored in shell history")
        
    except (ValueError, OSError) as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        raise click.Abort()

