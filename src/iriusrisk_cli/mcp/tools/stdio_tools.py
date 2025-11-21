"""Stdio-only MCP tools that require filesystem access.

These tools are only available in stdio transport mode as they
depend on local filesystem access for reading/writing project files.
"""

import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


def register_stdio_tools(mcp_server, api_client):
    """Register tools that require filesystem access (stdio mode only).
    
    Args:
        mcp_server: FastMCP server instance
        api_client: IriusRiskApiClient instance
    """
    
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
        from ...utils.logging_config import PerformanceTimer
        from ...commands.sync import sync_data_to_directory
        from ...utils.project_discovery import find_project_root
        
        timer = PerformanceTimer()
        timer.start()
        
        logger.info("MCP tool invoked: sync")
        logger.debug(f"Sync parameters: project_path={project_path}")
        logger.info("Starting IriusRisk sync via MCP")
        
        try:
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
                project_id = project_config.get('project_id') or project_config.get('reference_id')
            
            # Use the shared sync logic
            results = sync_data_to_directory(
                project_id=project_id,
                output_dir=output_dir
            )
            
            # Format results for MCP display
            output_lines = []
            output_dir_display = results.get('output_directory', output_dir)
            output_lines.append(f"🔄 Synchronizing IriusRisk data to: {output_dir_display}")
            output_lines.append(f"⏰ Sync timestamp: {results.get('timestamp', 'Unknown')}")
            
            if project_config:
                display_id = project_config.get('reference_id') or project_config.get('project_id', 'Unknown')
                output_lines.append(f"📋 Using project: {project_config.get('name', 'Unknown')} (ID: {display_id})")
            
            output_lines.append("")
            
            # Show what was synced
            if results.get('components'):
                if 'error' in results['components']:
                    output_lines.append(f"❌ Failed to download components: {results['components']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['components']['count']} system components")
            
            if results.get('trust_zones'):
                if 'error' in results['trust_zones']:
                    output_lines.append(f"❌ Failed to download trust zones: {results['trust_zones']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['trust_zones']['count']} system trust zones")
            
            if results.get('threats'):
                if 'error' in results['threats']:
                    output_lines.append(f"❌ Failed to download threats: {results['threats']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['threats']['count']} threats")
            
            if results.get('countermeasures'):
                if 'error' in results['countermeasures']:
                    output_lines.append(f"❌ Failed to download countermeasures: {results['countermeasures']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['countermeasures']['count']} countermeasures")
            
            # Show update results if any
            if results.get('updates_applied', 0) > 0 or results.get('updates_failed', 0) > 0:
                output_lines.append("")
                output_lines.append("🔄 Status Updates Applied:")
                if results.get('updates_applied', 0) > 0:
                    output_lines.append(f"✅ Successfully applied {results['updates_applied']} status updates")
                if results.get('updates_failed', 0) > 0:
                    output_lines.append(f"❌ Failed to apply {results['updates_failed']} status updates")
            
            output_lines.append("")
            output_lines.append("🎉 Sync completed!")
            
            sync_result = "\n".join(output_lines)
            
            duration = timer.stop()
            logger.info(f"IriusRisk sync completed successfully via MCP in {duration:.3f}s")
            
            return sync_result
            
        except Exception as e:
            error_str = str(e) if e is not None else "Unknown error"
            error_msg = f"❌ Sync failed: {error_str}"
            
            duration = timer.elapsed() if 'timer' in locals() else 0
            logger.error(f"MCP sync failed after {duration:.3f}s: {error_str}")
            
            return error_msg
    
    # Additional stdio tools will be added here
    # track_threat_update, track_countermeasure_update, get_pending_updates, etc.
    # For now, focusing on the core implementation structure

