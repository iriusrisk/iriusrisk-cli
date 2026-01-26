"""MCP (Model Context Protocol) command for IriusRisk CLI."""

import click
import asyncio
import sys
import logging
from typing import Any
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .. import __version__
from ..cli_context import pass_cli_context
from .sync import sync_data_to_directory
from ..utils.project import resolve_project_id, get_project_context_info
from ..utils.updates import get_update_tracker
from ..utils.project_resolution import resolve_project_id_to_uuid_strict, is_uuid_format
from ..utils.project_discovery import find_project_root
from ..utils.mcp_logging import setup_mcp_logging
from ..api.project_client import ProjectApiClient
import json

logger = logging.getLogger(__name__)


def _find_project_root_and_config():
    """Find the project root directory and read project.json if it exists.
    
    DEPRECATED: This function is maintained for backward compatibility.
    Use utils.project_discovery.find_project_root() instead.
    
    Returns:
        tuple: (project_root_path, project_config_dict or None)
    """
    return find_project_root()


def _load_prompt(prompt_name: str) -> str:
    """Load prompt instructions from external file.
    
    Prompts are stored in the prompts/ directory as markdown files.
    This allows easier editing and version control of AI instructions.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        
    Returns:
        The prompt content as a string
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        IOError: If the file cannot be read
    """
    prompts_dir = Path(__file__).parent.parent / 'prompts'
    prompt_file = prompts_dir / f'{prompt_name}.md'
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_file}")
        raise FileNotFoundError(f"Prompt file '{prompt_name}.md' not found in {prompts_dir}")
    except IOError as e:
        logger.error(f"Error reading prompt file {prompt_file}: {e}")
        raise


def _load_prompt_text(value, iriusrisk_dir: Path, action_name: str) -> str:
    """Load prompt text from either a string or a file reference.
    
    Args:
        value: Either a string (used directly) or a dict with 'file' key (loaded from file)
        iriusrisk_dir: Path to the .iriusrisk directory (for resolving relative paths)
        action_name: Name of the action (prefix/postfix/replace) for error messages
        
    Returns:
        The prompt text as a string
        
    Raises:
        ValueError: If the value format is invalid
        FileNotFoundError: If the file doesn't exist
        IOError: If the file cannot be read
    """
    # If it's a string, use it directly
    if isinstance(value, str):
        return value
    
    # If it's a dict, expect a 'file' key
    if isinstance(value, dict):
        if 'file' not in value:
            raise ValueError(
                f"Dictionary value for '{action_name}' must contain a 'file' key. "
                f"Got: {list(value.keys())}"
            )
        
        file_path = value['file']
        if not isinstance(file_path, str):
            raise ValueError(f"File path for '{action_name}' must be a string, got: {type(file_path)}")
        
        # Convert to Path object
        path = Path(file_path)
        
        # If not absolute, make it relative to .iriusrisk directory
        if not path.is_absolute():
            path = iriusrisk_dir / path
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt file for '{action_name}' not found: {path}\n"
                f"(resolved from: {file_path})"
            )
        
        if not path.is_file():
            raise ValueError(f"Prompt path for '{action_name}' is not a file: {path}")
        
        # Read and return the file contents
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded {len(content)} characters from file: {path}")
            return content
        except IOError as e:
            logger.error(f"Error reading prompt file {path}: {e}")
            raise IOError(f"Failed to read prompt file for '{action_name}': {path}") from e
    
    # Invalid type
    raise ValueError(
        f"Prompt customization '{action_name}' must be either a string or a dict with 'file' key. "
        f"Got: {type(value)}"
    )


def _apply_prompt_customizations(tool_name: str, base_prompt: str) -> str:
    """Apply any configured prompt customizations from project.json.
    
    This allows users to customize MCP tool prompts on a per-project basis by adding
    a 'prompts' section to their project.json file. Supports three actions:
    - prefix: Add text before the base prompt
    - postfix: Add text after the base prompt
    - replace: Completely replace the base prompt
    
    Each action can be specified as either:
    - A string value (used directly)
    - A dict with 'file' key (loaded from file, relative to .iriusrisk directory)
    
    Args:
        tool_name: Name of the MCP tool function (e.g., 'threats_and_countermeasures')
        base_prompt: The default prompt text for the tool
        
    Returns:
        The customized prompt text, or the base prompt if no customizations exist
        
    Example project.json structure:
        {
          "prompts": {
            "threats_and_countermeasures": {
              "prefix": "Organization-specific rules here\\n\\n",
              "postfix": {"file": "custom_prompts/additional_rules.md"}
            },
            "create_threat_model": {
              "replace": {"file": "custom_prompts/my_workflow.md"}
            }
          }
        }
    """
    from pathlib import Path
    
    # Debug logging
    logger.info(f"_apply_prompt_customizations called for tool: {tool_name}")
    logger.info(f"Current working directory: {Path.cwd()}")
    
    # Use the same project discovery logic as other MCP tools
    project_root, project_config = find_project_root()
    logger.info(f"Project root found: {project_root}")
    logger.info(f"Project config loaded: {project_config is not None}")
    if project_config:
        logger.info(f"Project config keys: {list(project_config.keys())}")
        logger.info(f"Has prompts section: {'prompts' in project_config}")
    
    if not project_config:
        logger.info(f"No project config found, returning base prompt for {tool_name}")
        return base_prompt
    
    customizations = project_config.get('prompts', {}).get(tool_name, {})
    logger.info(f"Customizations for {tool_name}: {customizations}")
    
    if not customizations:
        logger.info(f"No customizations found for {tool_name}")
        return base_prompt
    
    # Get the .iriusrisk directory for resolving relative file paths
    if project_root:
        # Convert to Path if it's a string (handles both real usage and mocked tests)
        if isinstance(project_root, str):
            project_root = Path(project_root)
        iriusrisk_dir = project_root / '.iriusrisk'
    else:
        iriusrisk_dir = Path.cwd() / '.iriusrisk'
    
    # Handle replace first (it overrides everything)
    if 'replace' in customizations:
        logger.info(f"Applying 'replace' customization to {tool_name}")
        try:
            replacement_text = _load_prompt_text(customizations['replace'], iriusrisk_dir, 'replace')
            logger.info(f"Replace text length: {len(replacement_text)} characters")
            return replacement_text
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error(f"Error loading 'replace' customization for {tool_name}: {e}")
            raise
    
    # Apply prefix and/or postfix
    result = base_prompt
    if 'prefix' in customizations:
        logger.info(f"Applying 'prefix' customization to {tool_name}")
        try:
            prefix_text = _load_prompt_text(customizations['prefix'], iriusrisk_dir, 'prefix')
            result = prefix_text + result
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error(f"Error loading 'prefix' customization for {tool_name}: {e}")
            raise
    
    if 'postfix' in customizations:
        logger.info(f"Applying 'postfix' customization to {tool_name}")
        try:
            postfix_text = _load_prompt_text(customizations['postfix'], iriusrisk_dir, 'postfix')
            result = result + postfix_text
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error(f"Error loading 'postfix' customization for {tool_name}: {e}")
            raise
    
    return result


@click.command()
@pass_cli_context
def mcp(cli_ctx):
    """Start MCP (Model Context Protocol) server for AI integration.
    
    This command starts an MCP server that provides tools for AI assistants
    to interact with IriusRisk CLI functionality. The server communicates
    via stdio and is designed to be used by AI-enabled IDEs like Cursor.
    
    The MCP server provides:
    - Instructions for AI on how to use IriusRisk MCP tools
    - Version information for the IriusRisk CLI
    - Future: Additional IriusRisk-specific tools and capabilities
    
    This command is not intended for direct user interaction but rather
    for integration with AI systems that support MCP.
    """
    # Configure MCP logging based on CLI context
    setup_mcp_logging(cli_ctx)
    logger.info("Starting IriusRisk MCP server")
    
    # Store CLI context for use in MCP functions
    config = cli_ctx.get_config()
    
    # Get API client from container (used by MCP tools)
    from ..container import get_container
    from ..api_client import IriusRiskApiClient
    container = get_container()
    api_client = container.get(IriusRiskApiClient)
    
    # Initialize FastMCP server
    mcp_server = FastMCP("iriusrisk-cli")
    
    @mcp_server.tool()
    async def initialize_iriusrisk_workflow() -> str:
        """Initialize IriusRisk workflow and get critical usage instructions for AI assistants.
        
        MANDATORY: This tool must be called before using any other IriusRisk MCP tools.
        Provides essential workflow instructions and tool usage guidelines.
        
        Returns:
            Critical workflow instructions and tool usage guidelines for AI assistants.
        """
        logger.info("MCP tool invoked: initialize_iriusrisk_workflow")
        logger.debug("Providing workflow instructions to AI assistant")
        instructions = _load_prompt("initialize_iriusrisk_workflow")
        logger.info("Provided critical IriusRisk workflow instructions to AI assistant")
        return _apply_prompt_customizations('initialize_iriusrisk_workflow', instructions)
    
    @mcp_server.tool()
    async def get_cli_version() -> str:
        """Get the current version of IriusRisk CLI.
        
        Returns:
            Version string of the IriusRisk CLI.
        """
        logger.info(f"Provided CLI version: {__version__}")
        return f"IriusRisk CLI version {__version__}"
    
    @mcp_server.tool()
    async def sync(project_path: str = None) -> str:
        """Synchronize with IriusRisk to pull down components, trust zones, and project data.
        
        This tool pulls down the IriusRisk component library, trust zones, and optionally
        syncs threats and countermeasures if a project already exists.
        
        Args:
            project_path: Full path to the project directory (where .iriusrisk should be created)
        
        Returns:
            Status message indicating what was synced and where files were saved.
        """
        from datetime import datetime
        from ..utils.logging_config import PerformanceTimer
        
        timer = PerformanceTimer()
        timer.start()
        
        logger.info("MCP tool invoked: sync")
        logger.debug(f"Sync parameters: project_path={project_path}")
        logger.info("Starting IriusRisk sync via MCP")
        
        try:
            from pathlib import Path
            
            # Determine output directory from project path
            if project_path:
                project_root = Path(project_path).resolve()
                if not project_root.exists():
                    error_msg = f"❌ Project path does not exist: {project_path}"
                    logger.error(error_msg)
                    return error_msg
                if not project_root.is_dir():
                    error_msg = f"❌ Project path is not a directory: {project_path}"
                    logger.error(error_msg)
                    return error_msg
                output_dir = str(project_root / '.iriusrisk')
            else:
                project_root = Path.cwd()
                output_dir = str(project_root / '.iriusrisk')
            
            # Read project.json to get project_id if available
            project_config = None
            project_json_path = project_root / '.iriusrisk' / 'project.json'
            logger.info(f"Looking for project.json at: {project_json_path}")
            if project_json_path.exists():
                try:
                    with open(project_json_path, 'r') as f:
                        project_config = json.load(f)
                    logger.info(f"Successfully loaded project.json: {project_config.get('name', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"Could not read project.json: {e}")
            else:
                logger.warning(f"project.json not found at: {project_json_path}")
            
            # Get project_id from project.json if available
            project_id = None
            if project_config:
                # Prefer project_id (UUID) for existing projects, fall back to reference_id
                project_id = project_config.get('project_id') or project_config.get('reference_id')
            
            # Use the shared sync logic
            # MCP doesn't use Config for defaults (uses project.json instead)
            # MCP doesn't need verbose output (formats its own return string)
            results = sync_data_to_directory(
                project_id=project_id,
                output_dir=output_dir,
                check_config_for_default=False,
                verbose=False
            )
            
            # Format results for MCP display
            output_lines = []
            output_dir_display = results.get('output_directory', output_dir)
            output_lines.append(f"🔄 Synchronizing IriusRisk data to: {output_dir_display}")
            output_lines.append(f"⏰ Sync timestamp: {results.get('timestamp', 'Unknown')}")
            output_lines.append(f"🗂️  Working directory: {Path.cwd()}")
            output_lines.append(f"📁 Project root: {project_root}")
            output_lines.append(f"🔍 Looking for project.json at: {project_json_path}")
            output_lines.append(f"📄 project.json exists: {project_json_path.exists()}")
            
            if project_config:
                # Show the reference ID for display (more readable than UUID)
                display_id = project_config.get('reference_id') or project_config.get('project_id', 'Unknown')
                output_lines.append(f"📋 Using project: {project_config.get('name', 'Unknown')} (ID: {display_id})")
            else:
                output_lines.append("📋 No project.json found or could not read it")
            
            if results.get('project_id') and results.get('project_id') != project_id:
                output_lines.append(f"🔄 Using reference ID: {results['project_id']}")
            
            if results.get('project_resolution_error'):
                output_lines.append(f"⚠️  Project resolution warning: {results['project_resolution_error']}")
            
            output_lines.append("")
            
            # Show what was synced
            if results.get('components'):
                if 'error' in results['components']:
                    output_lines.append(f"❌ Failed to download components: {results['components']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['components']['count']} system components")
                    output_lines.append(f"📄 Components saved to: {results['components']['file']}")
            
            if results.get('trust_zones'):
                if 'error' in results['trust_zones']:
                    output_lines.append(f"❌ Failed to download trust zones: {results['trust_zones']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['trust_zones']['count']} system trust zones")
                    output_lines.append(f"📄 Trust zones saved to: {results['trust_zones']['file']}")
            
            if results.get('threats'):
                if 'error' in results['threats']:
                    output_lines.append(f"❌ Failed to download threats: {results['threats']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['threats']['count']} threats")
                    output_lines.append(f"📄 Threats saved to: {results['threats']['file']}")
            
            if results.get('countermeasures'):
                if 'error' in results['countermeasures']:
                    output_lines.append(f"❌ Failed to download countermeasures: {results['countermeasures']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['countermeasures']['count']} countermeasures")
                    output_lines.append(f"📄 Countermeasures saved to: {results['countermeasures']['file']}")
            
            if results.get('questionnaires'):
                if 'error' in results['questionnaires']:
                    output_lines.append(f"❌ Failed to download questionnaires: {results['questionnaires']['error']}")
                else:
                    project_count = results['questionnaires'].get('project_count', 0)
                    component_count = results['questionnaires'].get('component_count', 0)
                    output_lines.append(f"✅ Downloaded questionnaires: {project_count} project, {component_count} components")
                    output_lines.append(f"📄 Questionnaires saved to: {results['questionnaires']['file']}")
            
            if results.get('threat_model_otm'):
                if 'error' in results['threat_model_otm']:
                    output_lines.append(f"❌ Failed to download current threat model (OTM): {results['threat_model_otm']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded current threat model (OTM)")
                    output_lines.append(f"📄 Threat model saved to: {results['threat_model_otm']['file']}")
                    output_lines.append(f"   📊 Size: {results['threat_model_otm']['size']:,} bytes")
            
            # Show update results if any
            if results.get('updates_applied', 0) > 0 or results.get('updates_failed', 0) > 0:
                output_lines.append("")
                output_lines.append("🔄 Status Updates Applied:")
                if results.get('updates_applied', 0) > 0:
                    output_lines.append(f"✅ Successfully applied {results['updates_applied']} status updates")
                if results.get('updates_failed', 0) > 0:
                    output_lines.append(f"❌ Failed to apply {results['updates_failed']} status updates")
                    for failed_update in results.get('failed_updates', []):
                        output_lines.append(f"   • {failed_update}")
                
                # Show comment creation results
                if results.get('comment_results'):
                    output_lines.append("")
                    output_lines.append("💬 Comment Creation Results:")
                    for comment_result in results['comment_results']:
                        output_lines.append(f"   • {comment_result}")
                
                # Show debug messages
                if results.get('debug_messages'):
                    output_lines.append("")
                    output_lines.append("🐛 Debug Information:")
                    for debug_msg in results['debug_messages']:
                        output_lines.append(f"   • {debug_msg}")
            
            # Show errors if any
            if results.get('errors'):
                output_lines.append("")
                for error in results['errors']:
                    output_lines.append(f"⚠️  {error}")
            
            # Summary
            output_lines.append("")
            output_lines.append("🎉 Sync completed! You can now create threat models with access to:")
            output_lines.append("   • Latest IriusRisk component library")
            if results.get('project_id'):
                output_lines.append("   • Current project threats, countermeasures, and questionnaires")
                if results.get('threat_model_otm'):
                    output_lines.append("")
                    output_lines.append("🔄 IMPORTANT: current-threat-model.otm exists - you should UPDATE/MERGE")
                    output_lines.append("   the existing threat model, not create a new one from scratch.")
                    output_lines.append("   Read the OTM file and incorporate existing components in your updates.")
            else:
                output_lines.append("💡 Use 'iriusrisk init' to set up a project for full sync")
            
            sync_result = "\n".join(output_lines)
            
            # Log performance metrics
            duration = timer.stop()
            logger.info(f"IriusRisk sync completed successfully via MCP in {duration:.3f}s")
            logger.debug(f"Sync performance: {duration:.3f}s total")
            
            return sync_result
            
        except Exception as e:
            # Ensure we don't get type errors when handling the exception
            error_str = str(e) if e is not None else "Unknown error"
            error_msg = f"❌ Sync failed: {error_str}"
            
            # Log error with performance context
            duration = timer.elapsed() if 'timer' in locals() else 0
            logger.error(f"MCP sync failed after {duration:.3f}s: {error_str}")
            logger.debug(f"Sync error context: project_path={project_path}, duration={duration:.3f}s")
            
            return error_msg
    
    @mcp_server.tool()
    async def import_otm(otm_file_path: str) -> str:
        """Import an OTM file to create or update a project in IriusRisk.
        
        This tool imports an OTM (Open Threat Model) file to IriusRisk, creating a new
        project or updating an existing one if it already exists.
        
        Args:
            otm_file_path: Path to the OTM file to import
            
        Returns:
            Status message indicating the result of the import operation.
        """
        from pathlib import Path
        
        logger.info("MCP tool invoked: import_otm")
        logger.debug(f"Import parameters: otm_file_path={otm_file_path}")
        logger.info(f"Starting OTM import via MCP for file: {otm_file_path}")
        
        try:
            # Find project root and read project.json if it exists
            project_root, project_config = _find_project_root_and_config()
            
            # Validate file path
            otm_path = Path(otm_file_path)
            if not otm_path.exists():
                error_msg = f"❌ OTM file not found: {otm_file_path}"
                logger.error(error_msg)
                return error_msg
            
            if not otm_path.is_file():
                error_msg = f"❌ Path is not a file: {otm_file_path}"
                logger.error(error_msg)
                return error_msg
            
            results = []
            results.append(f"📤 Importing OTM file: {otm_path.name}")
            results.append(f"📂 File path: {otm_path.absolute()}")
            
            # Check for auto-versioning configuration
            auto_versioning_enabled = project_config and project_config.get('auto_versioning', False)
            
            # Check if we need to override the OTM project ID with reference_id from project.json
            should_override_project_id = False
            override_project_id = None
            target_project_id = None
            
            if project_config:
                project_name = project_config.get('name', 'Unknown')
                project_id = project_config.get('project_id', 'Unknown')
                reference_id = project_config.get('reference_id')
                
                results.append(f"🎯 Target project: {project_name} (ID: {project_id})")
                if reference_id:
                    results.append(f"🔗 Reference ID: {reference_id}")
                    # Use reference_id to override the OTM project ID
                    override_project_id = reference_id
                    should_override_project_id = True
                    target_project_id = reference_id
                    logger.info(f"Will override OTM project ID with reference_id: {reference_id}")
            
            # If no override, extract project ID from OTM file
            if not target_project_id:
                target_project_id = api_client.project_client._extract_project_id_from_otm(str(otm_path))
                logger.debug(f"Extracted project ID from OTM file: {target_project_id}")
            
            # Check if project exists and handle auto-versioning
            project_exists = False
            if target_project_id:
                try:
                    # Try direct lookup first (in case it's a UUID)
                    api_client.get_project(target_project_id)
                    project_exists = True
                except Exception:
                    # Try searching by reference ID
                    try:
                        filter_expr = f"'referenceId'='{target_project_id}'"
                        response = api_client.get_projects(page=0, size=1, filter_expression=filter_expr)
                        projects = response.get('_embedded', {}).get('items', [])
                        project_exists = len(projects) > 0
                    except Exception:
                        pass
                
                logger.debug(f"Project exists check for '{target_project_id}': {project_exists}")
                
                if project_exists and auto_versioning_enabled:
                    logger.info("Auto-versioning is enabled and project exists, creating backup version before import")
                    results.append("📸 Auto-versioning enabled: Creating backup version...")
                    
                    try:
                        from ..services.version_service import VersionService
                        from datetime import datetime
                        
                        version_service = container.get(VersionService)
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        version_name = f"Auto-backup before import {timestamp}"
                        
                        # Create version and wait for completion (includes project unlock polling)
                        version_service.create_version(
                            project_id=target_project_id,
                            name=version_name,
                            description="Automatic backup created by MCP before OTM import",
                            wait=True,
                            timeout=300
                        )
                        results.append("✅ Backup version created and project unlocked")
                        logger.info("Backup version created successfully and project is ready")
                    except Exception as e:
                        # Version creation failed - STOP, don't continue with import
                        # Continuing would cause 401 error because project is locked
                        error_msg = (
                            f"❌ Auto-versioning failed: {e}\n\n"
                            f"Cannot proceed with OTM import while auto-versioning is enabled. "
                            f"The project may be locked or inaccessible.\n\n"
                            f"Options:\n"
                            f"1. Disable auto-versioning in .iriusrisk/project.json\n"
                            f"2. Check if project has pending changes in IriusRisk UI\n"
                            f"3. Verify project exists and is accessible"
                        )
                        logger.error(f"Auto-versioning failed, aborting import: {e}")
                        return error_msg
            
            results.append("")
            
            # Import the OTM file (auto-update if project exists) using container API client
            if should_override_project_id:
                # Read OTM content, modify project ID, then import
                results.append(f"📝 Overriding project ID to match project.json: {override_project_id}")
                
                with open(otm_path, 'r', encoding='utf-8') as f:
                    otm_content = f.read()
                
                # Modify the project ID to match reference_id from project.json
                modified_content = api_client.project_client._modify_otm_project_id(otm_content, override_project_id)
                
                # Import using the modified content
                result = api_client.import_otm_content(modified_content, auto_update=True)
            else:
                # Normal import without override
                result = api_client.import_otm_file(str(otm_path), auto_update=True)
            
            # Extract key information
            project_id = result.get('id', 'Unknown')
            project_name = result.get('name', 'Unknown')
            action = result.get('action', 'processed')
            
            results.append(f"✅ Project successfully {action}!")
            results.append(f"   📋 ID: {project_id}")
            results.append(f"   📛 Name: {project_name}")
            
            if 'ref' in result:
                results.append(f"   🔗 Reference: {result['ref']}")
            
            results.append("")
            results.append("🎉 OTM import completed successfully!")
            results.append("   • IriusRisk is now processing your architecture")
            results.append("   • Threats and countermeasures are being generated automatically")
            results.append("   • Use sync() MCP tool to download the generated security data")
            
            import_result = "\n".join(results)
            logger.info(f"OTM import completed successfully via MCP: {project_id}")
            return import_result
            
        except Exception as e:
            error_msg = f"❌ OTM import failed: {e}"
            logger.error(f"MCP OTM import failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def export_otm(project_id: str = None, output_path: str = None) -> str:
        """Export the current threat model from IriusRisk as OTM format.
        
        This tool retrieves the existing threat model for a project and exports it
        as an OTM file. This is essential for multi-repository workflows where
        subsequent repositories need to see and merge with the existing threat model.
        
        Args:
            project_id: Project ID or reference ID (optional if default project configured)
            output_path: Where to save the OTM file (optional, returns content if not specified)
            
        Returns:
            Status message with OTM export details, or OTM content if no output_path provided
        """
        from pathlib import Path
        
        logger.info(f"MCP tool invoked: export_otm")
        logger.debug(f"Export parameters: project_id={project_id}, output_path={output_path}")
        logger.info(f"Starting OTM export via MCP for project: {project_id or 'default'}")
        
        try:
            # Resolve project ID from argument, project.json, or default configuration
            if project_id:
                resolved_project_id = project_id
            else:
                # Try to get project ID from project.json first
                project_root, project_config = _find_project_root_and_config()
                resolved_project_id = None
                
                if project_config:
                    # Prefer project_id (UUID) for existing projects, fall back to reference_id
                    resolved_project_id = project_config.get('project_id') or project_config.get('reference_id')
                    logger.info(f"Using project ID from project.json: {resolved_project_id}")
                
                # Fall back to config if no project.json
                if not resolved_project_id:
                    resolved_project_id = config.get_default_project_id()
                
                if not resolved_project_id:
                    error_msg = "❌ No project ID provided and no default project configured. Use export_otm(project_id) or set up a project with 'iriusrisk init'."
                    logger.error(error_msg)
                    return error_msg
            
            # Resolve project ID to UUID for V2 API (upfront, no fallback mechanism)
            from ..utils.project_resolution import resolve_project_id_to_uuid
            logger.debug(f"Resolving project ID to UUID: {resolved_project_id}")
            final_project_id = resolve_project_id_to_uuid(resolved_project_id, api_client)
            logger.debug(f"Resolved to UUID: {final_project_id}")
            
            results = []
            results.append(f"📥 Exporting threat model from IriusRisk")
            results.append(f"📋 Project: {final_project_id}")
            results.append("")
            
            # Export the threat model using container API client
            logger.info(f"Calling export_project_as_otm for project: {final_project_id}")
            otm_content = api_client.export_project_as_otm(final_project_id)
            
            # If output path specified, save to file
            if output_path:
                output_file = Path(output_path)
                output_file.write_text(otm_content, encoding='utf-8')
                
                results.append(f"✅ Threat model exported successfully!")
                results.append(f"📁 Saved to: {output_file.absolute()}")
                results.append(f"📊 Size: {len(otm_content):,} bytes")
                results.append("")
                results.append("💡 This OTM file contains the current threat model including:")
                results.append("   • All components and trust zones")
                results.append("   • Data flows between components")
                results.append("   • Existing threats and countermeasures")
                results.append("")
                results.append("🔄 Use this file as a starting point to merge additional repository contributions.")
                
                export_result = "\n".join(results)
                logger.info(f"OTM export completed successfully via MCP: {output_file}")
                return export_result
            else:
                # Return the OTM content directly for AI to process
                results.append(f"✅ Threat model exported successfully!")
                results.append(f"📊 Size: {len(otm_content):,} bytes")
                results.append("")
                results.append("OTM Content:")
                results.append("="*50)
                results.append(otm_content)
                results.append("="*50)
                
                export_result = "\n".join(results)
                logger.info(f"OTM export completed successfully via MCP (returned content)")
                return export_result
            
        except Exception as e:
            error_msg = f"❌ OTM export failed: {e}"
            logger.error(f"MCP OTM export failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def project_status(project_id: str = None) -> str:
        """Check the status of a project in IriusRisk.
        
        This tool retrieves detailed information about a project to verify
        it exists, has been processed, and is ready for use.
        
        Args:
            project_id: Project ID or reference ID (optional if default project configured)
            
        Returns:
            Status message with project details and processing status.
        """
        logger.info(f"Checking project status via MCP for project: {project_id or 'default'}")
        
        try:
            # Resolve project ID from argument, project.json, or default configuration
            if project_id:
                resolved_project_id = project_id
            else:
                # Try to get project ID from project.json first
                from pathlib import Path
                project_json_path = Path.cwd() / '.iriusrisk' / 'project.json'
                resolved_project_id = None
                
                if project_json_path.exists():
                    try:
                        with open(project_json_path, 'r') as f:
                            project_config = json.load(f)
                        resolved_project_id = project_config.get('project_id')
                        logger.info(f"Using project ID from project.json: {resolved_project_id}")
                    except Exception as e:
                        logger.warning(f"Could not read project.json: {e}")
                
                # Fall back to config if no project.json
                if not resolved_project_id:
                    resolved_project_id = config.get_default_project_id()
                
                if not resolved_project_id:
                    error_msg = "❌ No project ID provided and no default project configured. Use project_status(project_id) or set up a project with 'iriusrisk init'."
                    logger.error(error_msg)
                    return error_msg
            
            results = []
            results.append(f"🔍 Checking project status: {resolved_project_id}")
            results.append("")
            
            # Try to get project details using container API client
            try:
                project_data = api_client.get_project(resolved_project_id)
            except Exception as direct_error:
                # If direct lookup fails, try searching by reference ID
                if "400" in str(direct_error) or "404" in str(direct_error) or "Bad Request" in str(direct_error) or "Not Found" in str(direct_error):
                    results.append(f"📋 Searching by reference ID: {resolved_project_id}")
                    
                    filter_expr = f"'referenceId'='{resolved_project_id}'"
                    response = api_client.get_projects(page=0, size=1, filter_expression=filter_expr)
                    
                    projects = response.get('_embedded', {}).get('items', [])
                    if not projects:
                        error_msg = f"❌ No project found with ID or reference: {resolved_project_id}"
                        logger.error(error_msg)
                        return error_msg
                    
                    project_data = projects[0]
                    results.append(f"✅ Found project by reference ID")
                else:
                    raise direct_error
            
            # Extract project information
            project_name = project_data.get('name', 'Unknown')
            project_uuid = project_data.get('id', 'Unknown')
            project_ref = project_data.get('referenceId', 'None')
            workflow_state = project_data.get('workflowState', {})
            workflow_name = workflow_state.get('name', 'Unknown') if workflow_state else 'Unknown'
            is_archived = project_data.get('isArchived', False)
            model_updated = project_data.get('modelUpdated', 'Unknown')
            
            # Get threat model synchronization status
            state = project_data.get('state', 'unknown')
            operation = project_data.get('operation', 'unknown')
            
            results.append("📊 Project Status:")
            results.append(f"   📛 Name: {project_name}")
            results.append(f"   🆔 UUID: {project_uuid}")
            results.append(f"   🔗 Reference: {project_ref}")
            results.append(f"   🔄 Workflow State: {workflow_name}")
            results.append(f"   📅 Last Updated: {model_updated}")
            results.append(f"   📦 Archived: {'Yes' if is_archived else 'No'}")
            results.append(f"   🔄 Threat Model State: {state}")
            results.append(f"   ⚙️  Operation: {operation}")
            
            # Determine status and provide actionable guidance
            if is_archived:
                results.append("")
                results.append("⚠️  Project is archived - it may not be actively processing")
            elif state == "draft":
                results.append("")
                results.append("⚠️  THREAT MODEL NEEDS UPDATE")
                results.append("   • The project has pending changes that need to be applied")
                results.append("   • In the web UI, this is when the orange 'Update Threat Model' button appears")
                results.append("   • The threat model must be regenerated to apply changes")
                results.append("   • Changes may be from: questionnaire updates, component changes, or rule modifications")
                results.append("")
                results.append("💡 Recommendation:")
                results.append("   • If you made changes via API/CLI, trigger threat model regeneration in the web UI")
                results.append("   • Or wait for automatic regeneration if enabled in your IriusRisk configuration")
            elif state == "syncing" or state == "syncing-draft":
                results.append("")
                results.append("⏳ Threat model is currently being updated")
                results.append("   • Rules engine is processing changes")
                results.append("   • Wait for the state to change to 'synced' before using the threat model")
                results.append("   • This typically takes a few seconds to a few minutes depending on project complexity")
            elif state == "synced":
                results.append("")
                results.append("✅ Threat model is synchronized and up to date")
                results.append("   • OTM import has been processed")
                results.append("   • All pending changes have been applied")
                results.append("   • Threats and countermeasures are current")
                results.append("   • Ready for sync() to download generated data")
            else:
                results.append("")
                results.append("✅ Project is active and ready for use")
                results.append("   • OTM import has been processed")
                results.append("   • Threats and countermeasures should be available")
                results.append("   • Ready for sync() to download generated data")
            
            status_result = "\n".join(results)
            logger.info(f"Project status check completed via MCP: {project_uuid}")
            return status_result
            
        except Exception as e:
            error_msg = f"❌ Failed to check project status: {e}"
            logger.error(f"MCP project status check failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def threats_and_countermeasures() -> str:
        """Get instructions for reading and exploring threats and countermeasures data.
        
        This tool provides comprehensive instructions for AI assistants on how to
        read, analyze, and help users explore the threats and countermeasures that
        IriusRisk automatically generated for their project.
        
        Returns:
            Detailed instructions for working with threats and countermeasures data.
        """
        logger.info("Providing threats and countermeasures instructions via MCP")
        
        instructions = _load_prompt("threats_and_countermeasures")
        
        logger.info("Provided threats and countermeasures instructions to AI assistant")
        return _apply_prompt_customizations('threats_and_countermeasures', instructions)
    
    @mcp_server.tool()
    async def questionnaire_guidance() -> str:
        """Get comprehensive instructions for completing questionnaires.
        
        This tool provides detailed guidance for AI assistants on how to analyze source code
        and complete project and component questionnaires. Questionnaires help IriusRisk
        refine the threat model based on actual implementation details.
        
        Returns:
            Detailed instructions for questionnaire completion workflow.
        """
        logger.info("Providing questionnaire guidance instructions via MCP")
        
        instructions = _load_prompt("questionnaire_guidance")
        
        logger.info("Provided questionnaire guidance instructions to AI assistant")
        return _apply_prompt_customizations('questionnaire_guidance', instructions)
    
    @mcp_server.tool()
    async def show_diagram(project_path: str, project_id: str = None, size: str = "PREVIEW") -> str:
        """Download and display the project threat model diagram.
        
        This tool downloads the project's automatically generated threat model diagram
        as a PNG image. The diagram shows the architecture with components, trust zones,
        and data flows that were modeled in the OTM.
        
        Args:
            project_path: Full path to the project directory (where .iriusrisk is located)
            project_id: Project ID or reference ID (optional if project.json exists)
            size: Image size - ORIGINAL, PREVIEW, or THUMBNAIL (default: PREVIEW)
            
        Returns:
            Status message with diagram file location and details.
        """
        from pathlib import Path
        import base64
        
        logger.info(f"Downloading project diagram via MCP for project: {project_id or 'default'}")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            # Resolve project ID from argument or project.json
            if project_id:
                resolved_project_id = project_id
            else:
                # Try to get project ID from project.json
                project_json_path = project_root / '.iriusrisk' / 'project.json'
                resolved_project_id = None
                
                if project_json_path.exists():
                    try:
                        with open(project_json_path, 'r') as f:
                            project_config = json.load(f)
                        resolved_project_id = project_config.get('project_id')
                        logger.info(f"Using project ID from project.json: {resolved_project_id}")
                    except Exception as e:
                        logger.warning(f"Could not read project.json: {e}")
                
                if not resolved_project_id:
                    error_msg = "❌ No project ID found in project.json. Please provide project_id parameter or ensure project.json exists."
                    logger.error(error_msg)
                    return error_msg
            
            results = []
            results.append(f"🖼️  Downloading threat model diagram")
            results.append(f"📁 Project: {resolved_project_id}")
            results.append(f"📏 Size: {size}")
            results.append("")
            
            # Resolve project ID to UUID for V2 API (upfront, no fallback mechanism)
            from ..utils.project_resolution import resolve_project_id_to_uuid
            logger.debug(f"Resolving project ID to UUID: {resolved_project_id}")
            final_project_id = resolve_project_id_to_uuid(resolved_project_id, api_client)
            logger.debug(f"Resolved to UUID: {final_project_id}")
            
            # Get artifacts with the resolved UUID
            artifacts_response = api_client.get_project_artifacts(final_project_id, page=0, size=100)
            artifacts = artifacts_response.get('_embedded', {}).get('items', [])
            
            if not artifacts:
                error_msg = "❌ No diagram artifacts found for this project. Make sure the project has been synchronized and contains a threat model."
                logger.error(error_msg)
                return error_msg
            
            # Find the diagram artifact (usually the first visible one)
            diagram_artifact = None
            for artifact in artifacts:
                # Look for artifacts that are likely diagrams (visible artifacts are usually diagrams)
                if artifact.get('visible', True):
                    diagram_artifact = artifact
                    break
            
            if not diagram_artifact:
                # If no visible artifacts, take the first one
                diagram_artifact = artifacts[0]
            
            artifact_id = diagram_artifact.get('id')
            artifact_name = diagram_artifact.get('name', 'diagram')
            
            results.append(f"📊 Found diagram: {artifact_name}")
            results.append(f"🔍 Downloading {size.lower()} image...")
            
            # Get the artifact content (base64 encoded image)
            content_response = api_client.get_project_artifact_content(artifact_id, size=size.upper())
            
            if not content_response.get('successfulGeneration', True):
                results.append("⚠️  Warning: Diagram generation may not have been fully successful")
            
            # Extract base64 content
            base64_content = content_response.get('content')
            if not base64_content:
                error_msg = "❌ No image content found in diagram artifact"
                logger.error(error_msg)
                return error_msg
            
            # Create filename from project configuration
            try:
                project_json_path = project_root / '.iriusrisk' / 'project.json'
                if project_json_path.exists():
                    try:
                        with open(project_json_path, 'r') as f:
                            project_config = json.load(f)
                        project_name = project_config.get('name', 'project')
                        # Clean up project name for filename
                        clean_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        clean_name = clean_name.replace(' ', '-').lower()
                        filename = f"{clean_name}-diagram-{size.lower()}.png"
                    except (json.JSONDecodeError, OSError, IOError, KeyError) as e:
                        logger.debug(f"Failed to parse project.json: {e}")
                        filename = f"threat-model-diagram-{size.lower()}.png"
                else:
                    filename = f"threat-model-diagram-{size.lower()}.png"
                    
            except (OSError, RuntimeError) as e:
                # If path operations fail, use generic filename
                logger.debug(f"Failed to determine filename: {e}")
                filename = f"threat-model-diagram-{size.lower()}.png"
            
            # Decode base64 and save to project directory
            try:
                image_data = base64.b64decode(base64_content)
                output_path = project_root / filename
                
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                
                results.append("")
                results.append("✅ Diagram downloaded successfully!")
                results.append(f"📁 File: {output_path.absolute()}")
                results.append(f"📂 Project: {project_root}")
                results.append(f"📊 Size: {len(image_data):,} bytes")
                results.append(f"🖼️  Format: PNG image ({size})")
                results.append("")
                results.append("💡 The diagram shows your threat model architecture:")
                results.append("   • Components and their relationships")
                results.append("   • Trust zones and boundaries") 
                results.append("   • Data flows between components")
                results.append("   • Generated automatically from your OTM file")
                
                diagram_result = "\n".join(results)
                logger.info(f"Diagram downloaded successfully via MCP: {filename}")
                return diagram_result
                
            except Exception as e:
                error_msg = f"❌ Failed to save diagram: {e}"
                logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"❌ Failed to download diagram: {e}"
            logger.error(f"MCP show_diagram failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def analyze_source_material() -> str:
        """Get comprehensive instructions for analyzing mixed source repositories.
        
        This tool provides AI assistants with detailed guidance on how to analyze
        repositories containing multiple source types (application code, infrastructure,
        policies, documentation) and extract all relevant components for a single,
        comprehensive threat model.
        
        Returns:
            Detailed instructions for analyzing mixed source repositories and extracting
            all component types for unified threat modeling.
        """
        logger.info("Providing source material analysis instructions via MCP")
        
        instructions = _load_prompt("analyze_source_material")
        
        logger.info("Provided source material analysis instructions to AI assistant")
        return _apply_prompt_customizations('analyze_source_material', instructions)
    
    @mcp_server.tool()
    async def create_threat_model() -> str:
        """Get comprehensive instructions for creating an IriusRisk threat model.
        
        This tool provides step-by-step instructions for AI assistants on how to
        create a complete threat model using the IriusRisk CLI workflow.
        
        Returns:
            Detailed instructions for creating threat models from source material.
        """
        instructions = _load_prompt("create_threat_model")
        logger.info("Provided CreateThreatModel instructions to AI assistant")
        return _apply_prompt_customizations('create_threat_model', instructions)
    
    @mcp_server.tool()
    async def track_threat_update(threat_id: str, status: str, reason: str, project_path: str, context: str = None, comment: str = None) -> str:
        """Track a threat status update for later synchronization with IriusRisk.
        
        Use this tool when implementing security measures that address specific threats.
        The updates will be applied to IriusRisk when the user runs the sync command.
        
        IMPORTANT: Threat states 'mitigate', 'partly-mitigate', and 'hidden' are AUTO-CALCULATED by IriusRisk
        based on countermeasure implementation status. You cannot set these directly. Instead:
        - To mitigate a threat: Implement its associated countermeasures
        - The threat state will automatically become 'mitigate' or 'partly-mitigate' based on countermeasure completion
        
        CRITICAL: Understand the difference between 'accept' and 'not-applicable':
        
        Use 'accept' when THE THREAT IS REAL but you're choosing to accept the risk:
        - Compensating controls are in place
        - Risk is not worth the resources to fix
        - Too difficult/expensive to fix right now
        - Business decision to live with the risk
        Example: "Accepting SQL injection risk - WAF protects us and DB is read-only"
        
        Use 'not-applicable' when THE THREAT DOES NOT EXIST (false positive):
        - Threat scenario doesn't apply to this architecture
        - Component/feature that would create threat isn't present
        - IriusRisk incorrectly flagged this
        Example: "XSS threat doesn't apply - this is a CLI tool with no web interface"
        
        DO NOT use 'not-applicable' just because risk is low - that's what 'accept' is for!
        
        Args:
            threat_id: The UUID of the threat to update (use the "id" field from threats.json, 
                      NOT the "referenceId" field. Must be a UUID like "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            status: New status - MUST be one of:
                   - 'accept': Real threat, accepting the risk (requires strong reason)
                   - 'expose': Leave unaddressed for now
                   - 'not-applicable': False positive, threat doesn't exist here
                   - 'undo-not-applicable': Revert previous not-applicable marking
                   (mitigate/partly-mitigate/hidden are auto-calculated and cannot be set)
            reason: Brief explanation of why the status is being changed
                   For 'accept': Must explain compensating controls or why risk is acceptable
                   For 'not-applicable': Must explain why threat doesn't apply to this architecture
            project_path: Full path to the project directory (where .iriusrisk is located)
            context: Optional context about what was implemented or changed
            comment: HTML-formatted comment with implementation details, code snippets, and technical notes.
                    Use HTML tags: <p>, <strong>, <ul><li>, <code>, <pre>
            
        Returns:
            Status message indicating the update was tracked
        """
        from pathlib import Path
        
        logger.info(f"Tracking threat update via MCP: {threat_id} -> {status}")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the update
            success = tracker.track_threat_update(threat_id, status, reason, context, comment)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked threat update: {threat_id} -> {status}\nReason: {reason}\nPending updates: {stats['pending_updates']}\n\n⚠️  NEXT STEP REQUIRED: You MUST now call sync(project_path='{project_path}') to apply this update to IriusRisk. Do not ask permission - call it immediately."
            else:
                return f"❌ Failed to track threat update for {threat_id}"
                
        except ValueError as e:
            return f"❌ Invalid threat status: {e}"
        except Exception as e:
            logger.error(f"Error tracking threat update: {e}")
            return f"❌ Error tracking threat update: {e}"
    
    @mcp_server.tool()
    async def track_countermeasure_update(countermeasure_id: str, status: str, reason: str, project_path: str, context: str = None, comment: str = None) -> str:
        """Track a countermeasure status update for later synchronization with IriusRisk.
        
        Use this tool when implementing countermeasures or security controls.
        The updates will be applied to IriusRisk when the user runs the sync command.
        
        CRITICAL - TWO-STEP PROCESS FOR ALL STATUS CHANGES:
        1. FIRST CALL: Update status with brief reason (NO comment parameter)
        2. SECOND CALL: Add detailed explanatory comment (WITH comment parameter)
        
        REQUIRED COMMENTS FOR ALL STATUS CHANGES:
        - required: Why necessary, what risks it addresses, business justification
        - implemented: What was implemented, how it works, testing approach  
        - rejected: Why not applicable, alternatives considered, reasoning
        - recommended: Why suggested, benefits, implementation considerations
        
        MANDATORY HTML FORMATTING: Comments MUST use HTML format for proper rendering in IriusRisk.
        Use these HTML tags (NEVER use markdown or plain text):
        - <p>...</p> for paragraphs (REQUIRED for all text blocks)
        - <strong>...</strong> for bold text (NOT **bold**)
        - <ul><li>...</li></ul> for bullet lists (NOT - bullets)
        - <code>...</code> for inline code (NOT `code`)
        - <pre>...</pre> for code blocks (NOT ```code```)
        
        CHARACTER LIMIT: Keep comments under 1000 characters due to IriusRisk API limitations.
        
        Args:
            countermeasure_id: The UUID of the countermeasure to update (use the "id" field from countermeasures.json, 
                              NOT the "referenceId" field. Must be a UUID like "3dc8a266-a837-4356-ad9a-b446c1535f54")
            status: New status (required, recommended, implemented, rejected, not-applicable)
            reason: Brief explanation of why the status is being changed
            project_path: Full path to the project directory (where .iriusrisk is located)
            context: Optional context about what was implemented or changed
            comment: REQUIRED for 'implemented' status - HTML-formatted comment with implementation details, 
                    code snippets, configuration changes, file paths, and testing approach
            
        Returns:
            Status message indicating the update was tracked
        """
        from pathlib import Path
        
        logger.info(f"Tracking countermeasure update via MCP: {countermeasure_id} -> {status}")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Check comment length limit (IriusRisk has ~1000 character limit)
            if comment and len(comment) > 1000:
                return f"❌ Error: Comment is {len(comment)} characters, but IriusRisk has a 1000 character limit. Please shorten the comment and try again."
            
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the update
            success = tracker.track_countermeasure_update(countermeasure_id, status, reason, context, comment)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked countermeasure update: {countermeasure_id} -> {status}\nReason: {reason}\nPending updates: {stats['pending_updates']}\n\n⚠️  NEXT STEP REQUIRED: You MUST now call sync(project_path='{project_path}') to apply this update to IriusRisk. Do not ask permission - call it immediately."
            else:
                return f"❌ Failed to track countermeasure update for {countermeasure_id}"
                
        except ValueError as e:
            return f"❌ Invalid countermeasure status: {e}"
        except Exception as e:
            logger.error(f"Error tracking countermeasure update: {e}")
            return f"❌ Error tracking countermeasure update: {e}"
    
    @mcp_server.tool()
    async def create_countermeasure_issue(countermeasure_id: str, project_path: str, issue_tracker_id: str = None) -> str:
        """Track an issue creation request for a countermeasure.
        
        This tool tracks a request to create a ticket in the issue tracker for the specified
        countermeasure. The issue will be created when the user runs the sync command.
        
        Use this tool when you want to create tracking tickets for countermeasures that
        need to be implemented or addressed by the development team.
        
        Args:
            countermeasure_id: The UUID of the countermeasure to create an issue for
                              (use the "id" field from countermeasures.json, NOT the "referenceId" field.
                              Must be a UUID like "3dc8a266-a837-4356-ad9a-b446c1535f54")
            project_path: Full path to the project directory (where .iriusrisk is located)
            issue_tracker_id: Optional specific issue tracker ID to use (if not provided, uses default)
            
        Returns:
            Status message indicating whether the issue creation request was tracked
        """
        from pathlib import Path
        
        logger.info(f"Tracking issue creation request for countermeasure via MCP: {countermeasure_id}")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            # Read project config for issue tracker settings
            project_json_path = project_root / '.iriusrisk' / 'project.json'
            project_config = None
            if project_json_path.exists():
                try:
                    with open(project_json_path, 'r') as f:
                        project_config = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read project.json: {e}")
            
            if not project_config:
                return "❌ Error: Could not find project configuration. Make sure you have a valid project setup."
            
            # Check if there's a default issue tracker configured (unless specific one provided)
            if not issue_tracker_id:
                default_tracker = project_config.get('default_issue_tracker')
                if not default_tracker:
                    return "❌ Error: No default issue tracker configured and no specific tracker provided. Use 'iriusrisk issue-tracker set-default <tracker-name>' to configure a default."
                issue_tracker_id = default_tracker.get('id')
                tracker_name = default_tracker.get('name', 'default')
            else:
                tracker_name = issue_tracker_id
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the issue creation request
            success = tracker.track_issue_creation(countermeasure_id, issue_tracker_id)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked issue creation request for countermeasure {countermeasure_id}\nIssue tracker: {tracker_name}\nPending updates: {stats['pending_updates']}\nUse sync() to create the issue in IriusRisk."
            else:
                return f"❌ Failed to track issue creation request for countermeasure {countermeasure_id}"
                
        except Exception as e:
            logger.error(f"Error tracking issue creation request: {e}")
            return f"❌ Error tracking issue creation request for countermeasure {countermeasure_id}: {e}"
    
    @mcp_server.tool()
    async def track_project_questionnaire_update(project_id: str, answers_data: dict, project_path: str, context: str = None) -> str:
        """Track a project questionnaire update for later synchronization with IriusRisk.
        
        Use this tool after analyzing source code to answer project/architecture questionnaire questions.
        The updates will be applied to IriusRisk when the user runs the sync command, which will
        also trigger the rules engine to regenerate the threat model based on the answers.
        
        Args:
            project_id: Project UUID (from project.json)
            answers_data: Questionnaire update request with steps and answers in the format:
                         {
                           "steps": [
                             {
                               "questions": [
                                 {
                                   "referenceId": "question-ref-id",
                                   "answers": [
                                     {
                                       "referenceId": "answer-ref-id",
                                       "value": "true"  # or "false"
                                     }
                                   ]
                                 }
                               ]
                             }
                           ]
                         }
            project_path: Full path to the project directory (where .iriusrisk is located)
            context: Optional context explaining what was analyzed to determine the answers
            
        Returns:
            Status message indicating the update was tracked
        """
        from pathlib import Path
        
        logger.info(f"Tracking project questionnaire update via MCP: {project_id}")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the update
            success = tracker.track_project_questionnaire_update(project_id, answers_data, context)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked project questionnaire update for project {project_id}\nPending updates: {stats['pending_updates']}\n\n⚠️  NEXT STEP REQUIRED: You MUST now call sync(project_path='{project_path}') to apply this update to IriusRisk and regenerate the threat model. Do not ask permission - call it immediately."
            else:
                return f"❌ Failed to track project questionnaire update for {project_id}"
                
        except Exception as e:
            logger.error(f"Error tracking project questionnaire update: {e}")
            return f"❌ Error tracking project questionnaire update: {e}"
    
    @mcp_server.tool()
    async def track_component_questionnaire_update(component_id: str, answers_data: dict, project_path: str, context: str = None) -> str:
        """Track a component questionnaire update for later synchronization with IriusRisk.
        
        Use this tool after analyzing source code to answer component-specific questionnaire questions.
        The updates will be applied to IriusRisk when the user runs the sync command, which will
        also trigger the rules engine to regenerate the threat model based on the answers.
        
        Args:
            component_id: Component UUID (from questionnaires.json)
            answers_data: Questionnaire update request with steps and answers in the format:
                         {
                           "steps": [
                             {
                               "questions": [
                                 {
                                   "referenceId": "question-ref-id",
                                   "answers": [
                                     {
                                       "referenceId": "answer-ref-id",
                                       "value": "true"  # or "false"
                                     }
                                   ]
                                 }
                               ]
                             }
                           ]
                         }
            project_path: Full path to the project directory (where .iriusrisk is located)
            context: Optional context explaining what was analyzed to determine the answers
            
        Returns:
            Status message indicating the update was tracked
        """
        from pathlib import Path
        
        logger.info(f"Tracking component questionnaire update via MCP: {component_id}")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the update
            success = tracker.track_component_questionnaire_update(component_id, answers_data, context)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked component questionnaire update for component {component_id}\nPending updates: {stats['pending_updates']}\n\n⚠️  NEXT STEP REQUIRED: You MUST now call sync(project_path='{project_path}') to apply this update to IriusRisk and regenerate the threat model. Do not ask permission - call it immediately."
            else:
                return f"❌ Failed to track component questionnaire update for {component_id}"
                
        except Exception as e:
            logger.error(f"Error tracking component questionnaire update: {e}")
            return f"❌ Error tracking component questionnaire update: {e}"
    
    @mcp_server.tool()
    async def get_pending_updates(project_path: str) -> str:
        """Get all pending threat and countermeasure updates that haven't been synced yet.
        
        Args:
            project_path: Full path to the project directory (where .iriusrisk is located)
        
        Returns:
            Summary of pending updates and statistics
        """
        from pathlib import Path
        
        logger.info("Getting pending updates via MCP")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            pending_updates = tracker.get_pending_updates()
            stats = tracker.get_stats()
            
            if not pending_updates:
                return "No pending updates. All tracked changes have been synchronized with IriusRisk."
            
            result = f"📋 Pending Updates Summary:\n"
            result += f"Total pending: {stats['pending_updates']}\n"
            result += f"Threats: {len([u for u in pending_updates if u['type'] == 'threat'])}\n"
            result += f"Countermeasures: {len([u for u in pending_updates if u['type'] == 'countermeasure'])}\n"
            result += f"Project Questionnaires: {len([u for u in pending_updates if u['type'] == 'project_questionnaire'])}\n"
            result += f"Component Questionnaires: {len([u for u in pending_updates if u['type'] == 'component_questionnaire'])}\n\n"
            
            result += "Recent Updates:\n"
            # Show last 10 pending updates
            for update in pending_updates[-10:]:
                update_type = update['type']
                if update_type in ['project_questionnaire', 'component_questionnaire']:
                    result += f"- {update_type.replace('_', ' ').title()}: {update['id'][:8]}...\n"
                    if update.get('context'):
                        result += f"  Context: {update['context'][:60]}{'...' if len(update['context']) > 60 else ''}\n"
                else:
                    result += f"- {update_type.title()}: {update['id'][:8]}... -> {update.get('new_status', 'N/A')}\n"
                    if update.get('reason'):
                        result += f"  Reason: {update['reason'][:60]}{'...' if len(update['reason']) > 60 else ''}\n"
                    if update.get('context'):
                        result += f"  Context: {update['context'][:60]}{'...' if len(update['context']) > 60 else ''}\n"
                result += "\n"
            
            if len(pending_updates) > 10:
                result += f"... and {len(pending_updates) - 10} more updates\n\n"
            
            result += "Use sync() to apply these updates to IriusRisk."
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pending updates: {e}")
            return f"❌ Error getting pending updates: {e}"
    
    @mcp_server.tool()
    async def clear_updates(project_path: str) -> str:
        """Clear all tracked updates (both pending and applied).
        
        Use this tool carefully - it will remove all tracked status changes.
        This is useful if you want to start fresh or if there are issues with the updates.
        
        Args:
            project_path: Full path to the project directory (where .iriusrisk is located)
        
        Returns:
            Status message indicating how many updates were cleared
        """
        from pathlib import Path
        
        logger.info("Clearing all updates via MCP")
        logger.debug(f"Project path: {project_path}")
        
        try:
            # Validate project path
            project_root = Path(project_path).resolve()
            if not project_root.exists():
                return f"❌ Project path does not exist: {project_path}"
            if not project_root.is_dir():
                return f"❌ Project path is not a directory: {project_path}"
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            cleared_count = tracker.clear_all_updates()
            
            return f"✅ Cleared {cleared_count} tracked updates. The updates queue is now empty."
            
        except Exception as e:
            logger.error(f"Error clearing updates: {e}")
            return f"❌ Error clearing updates: {e}"
    
    @mcp_server.tool()
    async def list_standards(project_id: str = None) -> str:
        """List available standards for compliance reports.
        
        This tool lists all available compliance standards that can be used when generating compliance reports.
        Standards include OWASP Top 10, PCI DSS, NIST frameworks, ISO standards, and more.
        
        Args:
            project_id: Project ID to list standards for. Uses current project if not specified.
        
        Returns:
            List of available standards with names, reference IDs, and UUIDs.
        """
        try:
            from ..utils.project import resolve_project_id
            from ..api.project_client import ProjectApiClient
            
            logger.info(f"MCP list_standards called: project_id={project_id}")
            
            # Resolve project ID
            try:
                resolved_project_id = resolve_project_id(project_id)
                project_uuid = resolve_project_id_to_uuid_strict(resolved_project_id, api_client.project_client)
            except Exception as e:
                return f"❌ Error resolving project ID: {str(e)}"
            
            # Get standards using container API client
            standards = api_client.get_project_standards(project_uuid)
            
            if not standards:
                return "❌ No standards found for this project."
            
            results = []
            results.append("📋 Available standards for compliance reports:")
            results.append("")
            
            for standard in standards:
                name = standard.get('name', 'Unknown')
                reference_id = standard.get('referenceId', 'Unknown')
                standard_id = standard.get('id', 'Unknown')
                
                results.append(f"• **{name}**")
                results.append(f"  - Reference ID: `{reference_id}`")
                results.append(f"  - UUID: `{standard_id}`")
                results.append("")
            
            results.append("💡 Use the reference ID (e.g., 'owasp-top-10-2021') when generating compliance reports.")
            
            logger.info(f"MCP list_standards returned {len(standards)} standards")
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error in list_standards MCP tool: {e}")
            return f"❌ Failed to list standards: {str(e)}"
    
    @mcp_server.tool()
    async def generate_report(report_type: str = "countermeasure", format: str = "pdf", project_path: str = None, project_id: str = None, output_path: str = None, standard: str = None) -> str:
        """Generate and download an IriusRisk report.
        
        This tool generates various types of reports from IriusRisk projects and downloads them to the specified location.
        Use this when asked to create reports like "Create a compliance report" or "Generate a countermeasure report".
        
        Args:
            report_type: Type of report to generate. Options: "countermeasure", "threat", "compliance", "risk-summary". 
                        Also accepts natural language like "compliance report", "countermeasure report", etc.
            format: Output format for the report. Options: "pdf", "html", "xlsx", "csv", "xls". Defaults to "pdf".
            project_path: Full path to the project directory (where .iriusrisk is located). Used to save report if output_path not specified.
            project_id: Project ID to generate report for. Uses current project if not specified.
            output_path: Where to save the report file. Auto-generates filename if not provided.
            standard: Standard reference ID or UUID for compliance reports (required for compliance reports).
                     Use list_standards() to see available options. Examples: "owasp-top-10-2021", "pci-dss-v4.0"
        
        Returns:
            Status message indicating success or failure with details.
        """
        try:
            from ..utils.project import resolve_project_id
            from ..api.project_client import ProjectApiClient
            import time
            from pathlib import Path
            
            logger.info(f"MCP generate_report called: type={report_type}, format={format}, project_id={project_id}")
            logger.debug(f"Project path: {project_path}")
            
            # Report type mappings - handle natural language
            report_mappings = {
                'countermeasure': 'technical-countermeasure-report',
                'countermeasures': 'technical-countermeasure-report',
                'countermeasure report': 'technical-countermeasure-report',
                'countermeasures report': 'technical-countermeasure-report',
                'technical countermeasure': 'technical-countermeasure-report',
                'technical countermeasure report': 'technical-countermeasure-report',
                
                'threat': 'technical-threat-report',
                'threats': 'technical-threat-report', 
                'threat report': 'technical-threat-report',
                'threats report': 'technical-threat-report',
                'technical threat': 'technical-threat-report',
                'technical threat report': 'technical-threat-report',
                
                'compliance': 'compliance-report',
                'compliance report': 'compliance-report',
                
                'risk': 'residual-risk',
                'risk summary': 'residual-risk',
                'risk-summary': 'residual-risk',
                'current risk': 'residual-risk',
                'current risk summary': 'residual-risk',
                'residual risk': 'residual-risk'
            }
            
            # Normalize report type
            normalized_type = report_type.lower().strip()
            if normalized_type in report_mappings:
                api_report_type = report_mappings[normalized_type]
                display_type = normalized_type.replace(' report', '').replace('technical ', '')
            else:
                return f"❌ Unknown report type: {report_type}. Supported types: countermeasure, threat, compliance, risk-summary"
            
            # Validate format
            supported_formats = ['pdf', 'html', 'xlsx', 'csv', 'xls']
            if format.lower() not in supported_formats:
                return f"❌ Unsupported format: {format}. Supported formats: {', '.join(supported_formats)}"
            
            format = format.lower()
            
            # Resolve project ID
            try:
                resolved_project_id = resolve_project_id(project_id)
                project_uuid = resolve_project_id_to_uuid_strict(resolved_project_id, api_client)
            except Exception as e:
                return f"❌ Error resolving project ID: {str(e)}"
            
            # Handle compliance reports that require a standard
            standard_uuid = None
            if normalized_type in ['compliance', 'compliance report']:
                if not standard:
                    return f"❌ Compliance reports require a 'standard' parameter. Use list_standards() to see available options."
                
                # Resolve standard reference ID to UUID if needed using container API client
                try:
                    # If it looks like a UUID, use it directly
                    if is_uuid_format(standard):
                        standard_uuid = standard
                    else:
                        # It's likely a reference ID, look it up
                        standards = api_client.get_project_standards(project_uuid)
                        for std in standards:
                            if std.get('referenceId') == standard:
                                standard_uuid = std.get('id')
                                break
                        
                        if not standard_uuid:
                            return f"❌ Standard '{standard}' not found. Use list_standards() to see available options."
                except Exception as e:
                    return f"❌ Error resolving standard: {str(e)}"
            
            # Generate output filename if not specified
            if not output_path:
                # Use project_path if provided, otherwise current directory
                if project_path:
                    project_root = Path(project_path).resolve()
                    if not project_root.exists() or not project_root.is_dir():
                        return f"❌ Invalid project path: {project_path}"
                    output_path = str(project_root / f"{display_type}_report.{format}")
                else:
                    output_path = f"{display_type}_report.{format}"
            
            output_file = Path(output_path)
            
            results = []
            results.append(f"🔄 Generating {display_type} report in {format.upper()} format...")
            if standard_uuid:
                results.append(f"📋 Using standard: {standard}")
            
            # Generate the report using container API client
            try:
                operation_id = api_client.generate_report(
                    project_id=project_uuid,
                    report_type=api_report_type,
                    format=format,
                    standard=standard_uuid
                )
                
                if not operation_id:
                    return "❌ Failed to start report generation - no operation ID returned"
                    
                results.append(f"📋 Report generation started (operation ID: {operation_id})")
                
                # Poll for completion with timeout
                timeout = 300  # 5 minutes
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    status_response = api_client.get_async_operation_status(operation_id)
                    status = status_response.get('status')
                    
                    if status == 'finished-success':
                        results.append("✅ Report generation completed!")
                        break
                    elif status in ['finished-error', 'finished-failure', 'failed']:
                        error_msg = status_response.get('errorMessage', 'Unknown error')
                        return f"❌ Report generation failed: {error_msg}"
                    elif status in ['pending', 'in-progress']:
                        # Continue polling
                        time.sleep(2)
                    else:
                        return f"❌ Unknown operation status: {status}"
                else:
                    return f"❌ Report generation timed out after {timeout} seconds"
                
                # Get the generated report
                reports = api_client.get_project_reports(project_uuid)
                if not reports:
                    return "❌ No reports found after generation"
                
                # Find the most recent report of the correct type
                target_report = None
                for report in reports:
                    if (report.get('reportType') == api_report_type and 
                        report.get('format') == format):
                        target_report = report
                        break
                
                if not target_report:
                    return "❌ Generated report not found in project reports"
                
                # Get download URL from the report links
                download_url = target_report.get('_links', {}).get('download', {}).get('href')
                if not download_url:
                    return "❌ No download link found for the report"
                
                # Download the report
                results.append(f"📥 Downloading report to {output_file}...")
                content = api_client.download_report_content_from_url(download_url)
                
                # Save to file
                output_file.write_bytes(content)
                
                results.append(f"✅ Report successfully saved to {output_file}")
                results.append(f"📊 Report size: {len(content):,} bytes")
                
                logger.info(f"MCP report generated successfully: {output_file}")
                return "\n".join(results)
                
            except Exception as e:
                error_msg = f"❌ Error during report generation: {str(e)}"
                logger.error(f"MCP generate_report failed: {e}")
                return error_msg
                
        except Exception as e:
            logger.error(f"Error in generate_report MCP tool: {e}")
            return f"❌ Failed to generate report: {str(e)}"
    
    @mcp_server.tool()
    async def architecture_and_design_review() -> str:
        """Provides guidance for architecture and design reviews with optional threat modeling.
        
        **CALL THIS TOOL FOR:**
        - Architecture reviews: "Review the architecture", "Explain the system design"
        - Codebase understanding: "What does this project do?", "How does this system work?"
        - Design analysis: "Analyze the design", "Show me the components"
        - Security assessment: "Is this secure?", "What are the risks?", "Security review"
        - System documentation: "Document the architecture", "Explain the structure"
        
        This tool helps AI assistants determine whether to use existing threat models or recommend
        threat model creation based on user intent and context.
        
        Returns:
            Instructions for conducting architecture reviews and when to recommend threat modeling.
        """
        logger.info("MCP architecture_and_design_review called")
        
        guidance = _load_prompt("architecture_and_design_review")

        logger.info("Provided architecture and design review guidance")
        return _apply_prompt_customizations('architecture_and_design_review', guidance)
    
    @mcp_server.tool()
    async def security_development_advisor() -> str:
        """Provides security guidance and recommendations for development work.
        
        Call this tool when developers are:
        - Planning security-impacting changes (integrations, data handling, auth changes)
        - Asking about security implications of their work
        - Working on features that cross trust boundaries
        - Making architectural or infrastructure changes
        
        This tool helps assess security impact and recommend when threat modeling would be valuable,
        while respecting developer autonomy and workflow.
        
        Returns:
            Security assessment and guidance on when to recommend threat modeling.
        """
        guidance = _load_prompt("security_development_advisor")

        logger.info("MCP security_development_advisor called")
        return _apply_prompt_customizations('security_development_advisor', guidance)
    
    @mcp_server.tool()
    async def list_project_versions(project_id: str = None) -> str:
        """List all version snapshots for a project.
        
        This tool lists all saved version snapshots of a project. Versions are point-in-time
        snapshots that can be used to track changes, compare different states, or restore
        previous configurations.
        
        Args:
            project_id: Project UUID or reference ID (optional if project.json exists in current directory)
            
        Returns:
            Formatted list of versions with details about each snapshot.
        """
        logger.info(f"MCP list_project_versions called with project_id={project_id}")
        
        try:
            from ..container import get_container
            from ..services.version_service import VersionService
            
            container = get_container()
            version_service = container.get(VersionService)
            api_client = container.get(IriusRiskApiClient)
            
            # Resolve project ID
            if not project_id:
                project_root, project_config = find_project_root()
                if project_config:
                    project_id = project_config.get('project_id')
                
                if not project_id:
                    return "❌ No project ID provided and no project.json found in current directory"
            
            # Resolve to UUID
            resolved_project_id = resolve_project_id_to_uuid_strict(project_id, api_client.project_client)
            logger.info(f"Resolved project ID to UUID: {resolved_project_id}")
            
            # List versions
            result = version_service.list_versions(resolved_project_id, page=0, size=50)
            versions = result.get('versions', [])
            total = result.get('page_info', {}).get('totalElements', 0)
            
            if not versions:
                return f"📋 No versions found for project {project_id}\n\nℹ️  Versions are snapshots created manually or automatically during OTM imports when auto_versioning is enabled."
            
            # Format output
            output = [f"📋 Project Versions for {project_id}"]
            output.append(f"   Total versions: {total}")
            output.append("")
            
            for idx, version in enumerate(versions, 1):
                version_id = version.get('id', 'Unknown')
                name = version.get('name', 'Unnamed')
                description = version.get('description', 'No description')
                created = version.get('creationDate', 'Unknown')
                created_by = version.get('creationUser', 'Unknown')
                operation = version.get('operation', 'none')
                
                output.append(f"{idx}. {name}")
                output.append(f"   ID: {version_id}")
                output.append(f"   Description: {description}")
                output.append(f"   Created: {created}")
                output.append(f"   Created by: {created_by}")
                output.append(f"   Status: {operation}")
                output.append("")
            
            logger.info(f"Successfully listed {len(versions)} versions for project {resolved_project_id}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to list project versions: {str(e)}"
            logger.error(f"MCP list_project_versions failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def create_project_version(name: str, description: str = None, project_id: str = None) -> str:
        """Create a new version snapshot of a project.
        
        This tool creates a point-in-time snapshot of a project's current state. The snapshot
        includes all threat model data, components, threats, and countermeasures. This is useful
        for tracking changes over time or creating backups before making significant modifications.
        
        Args:
            name: Name for the version (e.g., "v1.0", "Before API refactor")
            description: Optional description of what this version represents
            project_id: Project UUID or reference ID (optional if project.json exists in current directory)
            
        Returns:
            Success message with version details or error message.
        """
        logger.info(f"MCP create_project_version called: name={name}, project_id={project_id}")
        
        try:
            from ..container import get_container
            from ..services.version_service import VersionService
            
            container = get_container()
            version_service = container.get(VersionService)
            api_client = container.get(IriusRiskApiClient)
            
            # Resolve project ID
            if not project_id:
                project_root, project_config = find_project_root()
                if project_config:
                    project_id = project_config.get('project_id')
                
                if not project_id:
                    return "❌ No project ID provided and no project.json found in current directory"
            
            # Resolve to UUID
            resolved_project_id = resolve_project_id_to_uuid_strict(project_id, api_client.project_client)
            logger.info(f"Resolved project ID to UUID: {resolved_project_id}")
            
            # Create version (with wait=True to ensure it completes)
            result = version_service.create_version(
                project_id=resolved_project_id,
                name=name,
                description=description,
                wait=True,
                timeout=300
            )
            
            # Check if successful
            state = result.get('state', '').lower()
            if state == 'completed':
                output = [f"✅ Version created successfully!"]
                output.append(f"   Name: {name}")
                if description:
                    output.append(f"   Description: {description}")
                output.append(f"   Project: {project_id}")
                output.append("")
                output.append("ℹ️  The version snapshot has been saved and can be used for:")
                output.append("   • Comparing changes between versions")
                output.append("   • Restoring previous configurations (via UI)")
                output.append("   • Tracking threat model evolution")
                
                logger.info(f"Successfully created version '{name}' for project {resolved_project_id}")
                return "\n".join(output)
            else:
                error_msg = result.get('errorMessage', 'Unknown error')
                return f"❌ Version creation failed: {error_msg}"
            
        except Exception as e:
            error_msg = f"❌ Failed to create project version: {str(e)}"
            logger.error(f"MCP create_project_version failed: {e}")
            return error_msg

    try:
        logger.info("MCP server initialized successfully")
        # Run the MCP server with stdio transport
        mcp_server.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        click.echo(f"Error starting MCP server: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    mcp()
