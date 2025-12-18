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
            
            # CRITICAL CHECK: Verify project.json exists before proceeding
            project_json_path = project_root / '.iriusrisk' / 'project.json'
            logger.info(f"Looking for project.json at: {project_json_path}")
            
            if not project_json_path.exists():
                # Return clear error message visible to AI through MCP
                error_msg = f"""⚠️  CRITICAL: No project.json file found at {project_json_path}

This project has NOT been initialized with IriusRisk CLI.

WHY THIS MATTERS:
- Without project.json, there is no stable IriusRisk project ID
- Each operation will attempt to create a NEW project
- You cannot track threats, countermeasures, or project state across sessions
- Sync operations will not function properly after threat model generation

REQUIRED ACTION:
Please ask the user to run this command in the project directory:

    iriusrisk init

This command will:
1. Create a .iriusrisk/project.json file with a stable project reference ID
2. Allow proper project tracking across MCP sessions
3. Enable sync functionality to work correctly

DO NOT PROCEED with threat modeling until the project is initialized.
"""
                logger.error("project.json not found - returning error to AI")
                return error_msg
            
            # Read project.json to get project_id if available
            project_config = None
            try:
                with open(project_json_path, 'r') as f:
                    project_config = json.load(f)
                logger.info(f"Successfully loaded project.json: {project_config.get('name', 'Unknown')}")
            except Exception as e:
                error_msg = f"❌ Could not read project.json: {e}\n\nPlease ensure the file is valid JSON."
                logger.error(error_msg)
                return error_msg
            
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
    
    @mcp_server.tool()
    async def import_otm(otm_file_path: str, project_id: str = None) -> str:
        """Import an OTM (Open Threat Model) file to create or update a project.
        
        In stdio mode, provide a file path to the OTM file. The file will be read
        from the local filesystem and imported to IriusRisk.
        
        Args:
            otm_file_path: Path to the OTM file (relative or absolute)
            project_id: Optional project UUID or reference ID to update an EXISTING project.
                       If provided, checks if project exists first. If project doesn't exist,
                       creates a new project instead of failing with 404.
                       If not provided, creates new project (or auto-updates if name matches).
        
        Returns:
            Status message with project details
        """
        logger.info(f"MCP tool invoked: import_otm (file={otm_file_path}, project_id={project_id})")
        
        try:
            # Resolve file path
            otm_path = Path(otm_file_path)
            if not otm_path.is_absolute():
                otm_path = Path.cwd() / otm_path
            
            if not otm_path.exists():
                error_msg = f"❌ OTM file not found: {otm_file_path}"
                logger.error(error_msg)
                return error_msg
            
            if not otm_path.is_file():
                error_msg = f"❌ Path is not a file: {otm_file_path}"
                logger.error(error_msg)
                return error_msg
            
            # Read OTM content
            try:
                with open(otm_path, 'r', encoding='utf-8') as f:
                    otm_content = f.read()
            except Exception as e:
                error_msg = f"❌ Failed to read OTM file: {str(e)}"
                logger.error(error_msg)
                return error_msg
            
            # Validate it's valid JSON or YAML
            try:
                # Try parsing as JSON first
                json.loads(otm_content)
            except json.JSONDecodeError:
                # Try YAML
                try:
                    import yaml
                    yaml.safe_load(otm_content)
                except (ImportError, Exception) as e:
                    error_msg = f"❌ Invalid OTM format (not valid JSON or YAML): {str(e)}"
                    logger.error(error_msg)
                    return error_msg
            
            # ============================================================================
            # CRITICAL: V1 OTM API DOES NOT REQUIRE UUID RESOLUTION - DO NOT "FIX" THIS!
            # ============================================================================
            # The V1 API endpoint PUT /products/otm/{project_id} accepts BOTH:
            #   - UUIDs (e.g., "a1b2c3d4-e5f6-...")
            #   - Reference IDs (e.g., "my-project-ref")
            #
            # Unlike V2 API endpoints which STRICTLY require UUIDs in URL paths,
            # the V1 OTM endpoints handle reference ID resolution internally.
            #
            # ❌ DO NOT add resolve_project_id_to_uuid_strict() here! ❌
            # 
            # Why this breaks if you add resolution:
            #   1. Makes an unnecessary extra API call (performance penalty)
            #   2. FAILS when updating by reference ID: tries to look up project that
            #      may not exist yet, even though the V1 API would handle it correctly
            #   3. Error message becomes confusing: "Project not found" when the real
            #      issue is we're looking up before the API needs it
            #   4. The CLI command (commands/otm.py line 125) doesn't do resolution
            #      and works perfectly fine - MCP should match CLI behavior
            #
            # Example of what BREAKS if you add resolution:
            #   import_otm("file.otm", project_id="badger-app-poug")
            #   → Resolution tries: GET /projects?filter='referenceId'='badger-app-poug'
            #   → No project found yet → Exception: "Project not found"
            #   → But PUT /products/otm/badger-app-poug would have worked!
            #
            # When you DO need UUID resolution:
            #   - V2 API endpoints: GET /v2/projects/{uuid}/threats
            #   - See: mcp/tools/stdio_tools.py lines 510, 599 (threat/countermeasure updates)
            #   - See: mcp/tools/stdio_tools.py lines 439, 680, 804 (get_project, reports, diagrams)
            #
            # This has been a RECURRING issue where someone "fixes" this by adding
            # resolution, breaks OTM import, then it gets removed, then someone adds
            # it back. If you're tempted to add resolve_project_id_to_uuid_strict()
            # here, re-read these comments first!
            # ============================================================================
            
            # Import via API
            if project_id:
                # Check if project exists first before attempting update
                # This avoids the 404 error when project_id is provided but project doesn't exist yet
                from ...utils.api_helpers import validate_project_exists
                from ...api.project_client import ProjectApiClient
                project_client = ProjectApiClient()
                
                exists, resolved_uuid = validate_project_exists(project_id, project_client)
                
                if exists:
                    # Project exists - update it
                    result = api_client.update_project_with_otm_content(resolved_uuid or project_id, otm_content)
                    action = "updated"
                else:
                    # Project doesn't exist - create it instead
                    logger.info(f"Project '{project_id}' not found, creating new project instead")
                    result = api_client.import_otm_content(otm_content, auto_update=True)
                    action = result.get('action', 'created')
            else:
                # Create new project (or auto-update if exists)
                result = api_client.import_otm_content(otm_content, auto_update=True)
                action = result.get('action', 'created')
            
            result_project_id = result.get('id', 'Unknown')
            project_name = result.get('name', 'Unknown')
            
            # Build output
            output = []
            output.append(f"✅ OTM import successful!")
            output.append(f"Action: Project {action}")
            output.append(f"Project ID: {result_project_id}")
            output.append(f"Project Name: {project_name}")
            output.append("")
            output.append("💡 Next steps:")
            output.append("  1. Run sync() to download threats and countermeasures")
            output.append("  2. Review threats and countermeasures data in .iriusrisk/")
            
            logger.info(f"OTM imported successfully: {project_name} ({result_project_id})")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to import OTM: {str(e)}"
            logger.error(f"MCP import_otm failed: {e}")
            return error_msg
    
    # ============================================================================
    # NOTE: Search tools intentionally NOT included in stdio mode
    # ============================================================================
    # In stdio mode, AI assistants have direct file system access and can read
    # .iriusrisk/*.json files directly. They can perform more flexible and powerful
    # analysis by reading the raw JSON rather than using pre-built search tools.
    # 
    # Tools NOT included:
    # - search_components (AI reads .iriusrisk/components.json directly)
    # - get_component_categories (AI extracts from components.json directly)
    # - get_trust_zones (AI reads .iriusrisk/trust-zones.json directly)
    # - search_threats (AI reads .iriusrisk/threats.json directly)
    # - search_countermeasures (AI reads .iriusrisk/countermeasures.json directly)
    #
    # This approach provides more flexibility and eliminates unnecessary abstraction
    # layers when direct file access is available.
    # ============================================================================
    
    # ============================================================================
    # API-based tools (work in both modes, but stdio can use API client)
    # ============================================================================
    
    @mcp_server.tool()
    async def list_projects(page: int = 0, size: int = 10) -> str:
        """List IriusRisk projects with default ordering.
        
        Returns a simple list of projects without filtering. Use search_projects()
        to find specific projects by name or criteria.
        
        Args:
            page: Page number for pagination (default: 0)
            size: Number of results per page (default: 10)
        
        Returns:
            Formatted list of projects with IDs, names, and key details
        """
        logger.info(f"MCP tool invoked: list_projects (page={page}, size={size})")
        
        try:
            response = api_client.get_projects(page=page, size=size)
            projects = response.get('_embedded', {}).get('items', [])
            page_info = response.get('page', {})
            total = page_info.get('totalElements', 0)
            
            if not projects:
                return f"No projects found. Total projects: {total}"
            
            # Format output
            output = []
            output.append(f"📋 IriusRisk Projects (Total: {total})\n")
            output.append(f"Showing page {page + 1} ({len(projects)} results)\n")
            
            for idx, project in enumerate(projects, 1):
                name = project.get('name', 'Unknown')
                project_id = project.get('id', 'Unknown')
                ref_id = project.get('referenceId', 'None')
                workflow = project.get('workflowState', {}).get('name', 'Unknown')
                updated = project.get('modelUpdated', 'Unknown')
                
                output.append(f"{idx}. **{name}**")
                output.append(f"   UUID: {project_id}")
                output.append(f"   Reference ID: {ref_id}")
                output.append(f"   Workflow: {workflow}")
                output.append(f"   Last Updated: {updated}")
                output.append("")
            
            if total > (page + 1) * size:
                output.append(f"💡 More results available. Use page={page + 1} to see next page.")
            
            output.append(f"\n💡 To search for specific projects, use search_projects(query='...')")
            
            logger.info(f"Listed {len(projects)} projects successfully")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to list projects: {str(e)}"
            logger.error(f"MCP list_projects failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def search_projects(query: str, filter_tags: str = None, 
                             filter_workflow_state: str = None, page: int = 0, size: int = 20) -> str:
        """Search IriusRisk projects by name, tags, or workflow state.
        
        Args:
            query: Search term for project name (partial match, case-insensitive)
            filter_tags: Filter projects by tags (space-separated)
            filter_workflow_state: Filter by workflow state
            page: Page number for pagination (default: 0)
            size: Number of results per page (default: 20)
        
        Returns:
            Formatted list of matching projects with IDs, names, and key details
        """
        logger.info(f"MCP tool invoked: search_projects (query={query}, page={page})")
        
        try:
            # Build filter expression
            filters = []
            if query:
                filters.append(f"'name'~'{query}'")
            if filter_tags:
                for tag in filter_tags.split():
                    filters.append(f"'tags'~'{tag}'")
            if filter_workflow_state:
                filters.append(f"'workflowState.name'='{filter_workflow_state}'")
            
            filter_expr = ":AND:".join(filters) if filters else None
            
            response = api_client.get_projects(page=page, size=size, filter_expression=filter_expr)
            projects = response.get('_embedded', {}).get('items', [])
            page_info = response.get('page', {})
            total = page_info.get('totalElements', 0)
            
            if not projects:
                return f"No projects found matching query: '{query}'" if query else "No projects found."
            
            # Format output
            output = []
            if query:
                output.append(f"🔍 Search results for '{query}': {total} project(s) found\n")
            else:
                output.append(f"📋 Found {total} project(s)\n")
            output.append(f"Showing page {page + 1} ({len(projects)} results)\n")
            
            for idx, project in enumerate(projects, 1):
                name = project.get('name', 'Unknown')
                project_id = project.get('id', 'Unknown')
                ref_id = project.get('referenceId', 'None')
                workflow = project.get('workflowState', {}).get('name', 'Unknown')
                updated = project.get('modelUpdated', 'Unknown')
                
                output.append(f"{idx}. **{name}**")
                output.append(f"   UUID: {project_id}")
                output.append(f"   Reference ID: {ref_id}")
                output.append(f"   Workflow: {workflow}")
                output.append(f"   Last Updated: {updated}")
                output.append("")
            
            if total > (page + 1) * size:
                output.append(f"💡 More results available. Use page={page + 1} to see next page.")
            
            logger.info(f"Search returned {len(projects)} projects")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to search projects: {str(e)}"
            logger.error(f"MCP search_projects failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_project(project_id: str) -> str:
        """Get detailed information about a specific project.
        
        Args:
            project_id: Project UUID or reference ID
        
        Returns:
            Detailed project information including metadata and status
        """
        logger.info(f"MCP tool invoked: get_project (project_id={project_id})")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get project details
            project = api_client.get_project(project_uuid)
            
            # Format output
            output = []
            output.append("📊 Project Details:\n")
            output.append(f"Name: {project.get('name', 'Unknown')}")
            output.append(f"UUID: {project.get('id', 'Unknown')}")
            output.append(f"Reference ID: {project.get('referenceId', 'None')}")
            output.append(f"Description: {project.get('description', 'No description')}")
            output.append(f"Workflow State: {project.get('workflowState', {}).get('name', 'Unknown')}")
            output.append(f"Last Updated: {project.get('modelUpdated', 'Unknown')}")
            output.append(f"Archived: {'Yes' if project.get('isArchived', False) else 'No'}")
            
            tags = project.get('tags', [])
            if tags:
                output.append(f"Tags: {', '.join(tags)}")
            
            logger.info(f"Retrieved project details for {project_uuid}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to get project: {str(e)}"
            logger.error(f"MCP get_project failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def update_threat_status(project_id: str, threat_id: str, status: str, 
                                   reason: str, comment: str = None) -> str:
        """Update threat status with local tracking.
        
        TRANSPARENCY REQUIREMENT: For any status change, especially 'accept', you MUST
        provide a detailed comment explaining why the decision was made, what compensating
        controls exist, and who approved it. This is required for auditability and transparency.
        
        Updates the threat status in IriusRisk and tracks the change locally
        in .iriusrisk/updates.json for future reference.
        
        Args:
            project_id: Project UUID or reference ID
            threat_id: Threat UUID
            status: New status (accept, mitigate, expose, partly-mitigate, hidden, not-applicable)
            reason: Explanation for the status change
            comment: HTML-formatted comment with decision details - REQUIRED for transparency.
                     Should include: why the decision was made, compensating controls,
                     business justification, and AI attribution. Use HTML tags.
        
        Returns:
            Confirmation message with transparency about comment creation
        """
        logger.info(f"MCP tool invoked: update_threat_status (project={project_id}, threat={threat_id}, status={status})")
        
        # Validate comment length (IriusRisk API limit is 1000 characters)
        if comment and len(comment) > 1000:
            error_msg = f"❌ Comment too long: {len(comment)} characters (max: 1000). Please shorten your comment and try again."
            logger.error(error_msg)
            return error_msg
        
        # Warn if no comment provided (transparency issue), especially for 'accept'
        if not comment:
            logger.warning(f"⚠️  Threat status update WITHOUT comment - transparency requirement not met!")
            if status == 'accept':
                logger.warning(f"⚠️  Risk acceptance WITHOUT justification comment is a serious compliance issue!")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            from ...utils.project_discovery import find_project_root
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Update threat status via API (note: API method is update_threat_state, not update_threat_status)
            # Note: We don't pass comment here because we create it separately below for better error tracking
            api_client.update_threat_state(threat_id, status, reason=reason)
            logger.info(f"✅ Status updated successfully")
            
            # Add comment if provided - track success/failure separately for transparency
            comment_status = ""
            if comment:
                try:
                    api_client.create_threat_comment(threat_id, comment)
                    logger.info(f"✅ Comment added successfully")
                    comment_status = " with comment"
                except Exception as comment_error:
                    logger.error(f"❌ Comment creation failed: {comment_error}")
                    comment_status = f"\n⚠️  WARNING: Status updated but comment creation FAILED: {comment_error}\nPlease manually add this comment in IriusRisk:\n{comment[:200]}..."
            else:
                if status == 'accept':
                    comment_status = "\n⚠️  CRITICAL: Risk acceptance WITHOUT justification comment - this is a compliance issue. Please add a comment explaining why this risk was accepted."
                else:
                    comment_status = "\n⚠️  WARNING: No comment provided - transparency requirement not met. Please add a comment explaining the decision."
            
            # Track locally using UpdateTracker
            try:
                from ...utils.updates import get_update_tracker
                project_root, _ = find_project_root()
                if project_root:
                    iriusrisk_dir = project_root / '.iriusrisk'
                    tracker = get_update_tracker(iriusrisk_dir)
                    tracker.track_threat_update(
                        threat_id=threat_id,
                        status=status,
                        reason=reason,
                        comment=comment
                    )
                    # Mark as applied immediately since we just applied it (prevents duplicate comments on sync)
                    tracker.mark_update_applied(threat_id, "threat")
                    logger.info(f"Tracked and marked threat update as applied in {iriusrisk_dir / 'updates.json'}")
            except Exception as track_error:
                logger.warning(f"Could not track update locally: {track_error}")
            
            logger.info(f"Updated threat {threat_id} to status {status}")
            return f"✅ Threat status updated to '{status}'{comment_status}"
            
        except Exception as e:
            error_msg = f"❌ Failed to update threat status: {str(e)}"
            logger.error(f"MCP update_threat_status failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def update_countermeasure_status(project_id: str, countermeasure_id: str, 
                                          status: str, reason: str, comment: str = None) -> str:
        """Update countermeasure status with local tracking.
        
        TRANSPARENCY REQUIREMENT: For any status change, especially 'implemented', you MUST
        provide a detailed comment explaining what was done, how it was done, and what files
        were modified. This is required for auditability and transparency.
        
        Updates the countermeasure status in IriusRisk and tracks the change locally
        in .iriusrisk/updates.json for future reference.
        
        Args:
            project_id: Project UUID or reference ID
            countermeasure_id: Countermeasure UUID
            status: New status (required, recommended, implemented, rejected, not-applicable)
            reason: Explanation for the status change
            comment: HTML-formatted comment with implementation details - REQUIRED for transparency.
                     Should include: what was implemented, which files were modified, how it was
                     tested, and AI attribution. Use HTML tags (<p>, <ul><li>, <code>, <strong>).
        
        Returns:
            Confirmation message with transparency about comment creation
        """
        logger.info(f"MCP tool invoked: update_countermeasure_status (project={project_id}, cm={countermeasure_id}, status={status})")
        
        # Validate comment length (IriusRisk API limit is 1000 characters)
        if comment and len(comment) > 1000:
            error_msg = f"❌ Comment too long: {len(comment)} characters (max: 1000). Please shorten your comment and try again."
            logger.error(error_msg)
            return error_msg
        
        # Warn if no comment provided (transparency issue)
        if not comment:
            logger.warning(f"⚠️  Countermeasure status update WITHOUT comment - transparency requirement not met!")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            from ...utils.project_discovery import find_project_root
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Update countermeasure status via API (note: API method is update_countermeasure_state, not update_countermeasure_status)
            # Note: We don't pass comment here because we create it separately below for better error tracking
            api_client.update_countermeasure_state(countermeasure_id, status, reason=reason)
            logger.info(f"✅ Status updated successfully")
            
            # Add comment if provided - track success/failure separately for transparency
            comment_status = ""
            if comment:
                try:
                    api_client.create_countermeasure_comment(countermeasure_id, comment)
                    logger.info(f"✅ Comment added successfully")
                    comment_status = " with comment"
                except Exception as comment_error:
                    logger.error(f"❌ Comment creation failed: {comment_error}")
                    comment_status = f"\n⚠️  WARNING: Status updated but comment creation FAILED: {comment_error}\nPlease manually add this comment in IriusRisk:\n{comment[:200]}..."
            else:
                comment_status = "\n⚠️  WARNING: No comment provided - transparency requirement not met. Please add a comment explaining what was changed."
            
            # Track locally using UpdateTracker
            try:
                from ...utils.updates import get_update_tracker
                project_root, _ = find_project_root()
                if project_root:
                    iriusrisk_dir = project_root / '.iriusrisk'
                    tracker = get_update_tracker(iriusrisk_dir)
                    tracker.track_countermeasure_update(
                        countermeasure_id=countermeasure_id,
                        status=status,
                        reason=reason,
                        comment=comment
                    )
                    # Mark as applied immediately since we just applied it (prevents duplicate comments on sync)
                    tracker.mark_update_applied(countermeasure_id, "countermeasure")
                    logger.info(f"Tracked and marked countermeasure update as applied in {iriusrisk_dir / 'updates.json'}")
            except Exception as track_error:
                logger.warning(f"Could not track update locally: {track_error}")
            
            logger.info(f"Updated countermeasure {countermeasure_id} to status {status}")
            return f"✅ Countermeasure status updated to '{status}'{comment_status}"
            
        except Exception as e:
            error_msg = f"❌ Failed to update countermeasure status: {str(e)}"
            logger.error(f"MCP update_countermeasure_status failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def generate_report(project_id: str, report_type: str = "countermeasure",
                             format: str = "pdf", standard: str = None) -> str:
        """Generate and save an IriusRisk report to local directory.
        
        Generates various types of reports from IriusRisk projects and saves them
        to the .iriusrisk/reports directory.
        
        Args:
            project_id: Project UUID or reference ID
            report_type: Type - countermeasure, threat, compliance, risk-summary (default: countermeasure)
            format: Format - pdf, html, xlsx, csv, xls (default: pdf)
            standard: Standard reference ID for compliance reports (required for compliance type)
        
        Returns:
            Success message with file path
        """
        logger.info(f"MCP tool invoked: generate_report (project={project_id}, type={report_type}, format={format})")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict, is_uuid_format
            from ...utils.project_discovery import find_project_root
            import time
            
            # Report type mappings
            report_mappings = {
                'countermeasure': 'technical-countermeasure-report',
                'threat': 'technical-threat-report',
                'compliance': 'compliance-report',
                'risk-summary': 'residual-risk',
                'risk': 'residual-risk',
            }
            
            api_report_type = report_mappings.get(report_type.lower(), report_type)
            
            # Resolve project ID
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Handle compliance reports that require a standard
            standard_uuid = None
            if 'compliance' in report_type.lower():
                if not standard:
                    return "❌ Compliance reports require a 'standard' parameter."
                
                # Resolve standard
                if is_uuid_format(standard):
                    standard_uuid = standard
                else:
                    standards = api_client.get_project_standards(project_uuid)
                    for std in standards:
                        if std.get('referenceId') == standard:
                            standard_uuid = std.get('id')
                            break
                    if not standard_uuid:
                        return f"❌ Standard '{standard}' not found"
            
            # Generate report
            operation_id = api_client.generate_report(
                project_id=project_uuid,
                report_type=api_report_type,
                format=format.lower(),
                standard=standard_uuid
            )
            
            # Poll for completion
            timeout = 120
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status_response = api_client.get_async_operation_status(operation_id)
                status = status_response.get('status')
                
                if status == 'finished-success':
                    break
                elif status in ['finished-error', 'finished-failure', 'failed']:
                    return f"❌ Report generation failed: {status_response.get('errorMessage', 'Unknown error')}"
                elif status in ['pending', 'in-progress']:
                    time.sleep(2)
                else:
                    return f"❌ Unknown operation status: {status}"
            else:
                return f"❌ Report generation timed out after {timeout} seconds"
            
            # Get the generated report
            reports = api_client.get_project_reports(project_uuid)
            if not reports:
                return "❌ No reports found after generation"
            
            # Find the most recent report of correct type
            target_report = None
            for report in reports:
                if (report.get('reportType') == api_report_type and 
                    report.get('format') == format.lower()):
                    target_report = report
                    break
            
            if not target_report:
                return "❌ Generated report not found"
            
            # Download report content
            download_url = target_report.get('_links', {}).get('download', {}).get('href')
            if not download_url:
                return "❌ No download link found"
            
            content = api_client.download_report_content_from_url(download_url)
            
            # Save to .iriusrisk/reports directory
            project_root, _ = find_project_root()
            if not project_root:
                project_root = Path.cwd()
            
            reports_dir = project_root / '.iriusrisk' / 'reports'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{report_type}-{timestamp}.{format.lower()}"
            filepath = reports_dir / filename
            
            # Write file
            filepath.write_bytes(content)
            
            output = []
            output.append(f"✅ Report generated and saved successfully")
            output.append(f"Type: {report_type}")
            output.append(f"Format: {format.upper()}")
            output.append(f"Size: {len(content):,} bytes")
            output.append(f"File: {filepath}")
            
            logger.info(f"Generated {format} report and saved to {filepath}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to generate report: {str(e)}"
            logger.error(f"MCP generate_report failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_diagram(project_id: str, size: str = "PREVIEW") -> str:
        """Get project diagram and save to local directory.
        
        Downloads the project threat model diagram as a PNG image and saves it
        to the .iriusrisk/diagrams directory.
        
        Args:
            project_id: Project UUID or reference ID
            size: Image size - ORIGINAL, PREVIEW, or THUMBNAIL (default: PREVIEW)
        
        Returns:
            Success message with file path
        """
        logger.info(f"MCP tool invoked: get_diagram (project_id={project_id}, size={size})")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            from ...utils.project_discovery import find_project_root
            import base64
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get artifacts
            artifacts_response = api_client.get_project_artifacts(project_uuid, page=0, size=100)
            artifacts = artifacts_response.get('_embedded', {}).get('items', [])
            
            if not artifacts:
                return "❌ No diagram artifacts found for this project"
            
            # Find diagram artifact
            diagram_artifact = next((a for a in artifacts if a.get('visible', True)), artifacts[0])
            artifact_id = diagram_artifact.get('id')
            
            # Get the artifact content
            content_response = api_client.get_project_artifact_content(artifact_id, size=size.upper())
            base64_content = content_response.get('content')
            
            if not base64_content:
                return "❌ No image content found in diagram artifact"
            
            # Decode base64 content
            image_bytes = base64.b64decode(base64_content)
            
            # Save to .iriusrisk/diagrams directory
            project_root, _ = find_project_root()
            if not project_root:
                project_root = Path.cwd()
            
            diagrams_dir = project_root / '.iriusrisk' / 'diagrams'
            diagrams_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"diagram-{size.lower()}-{timestamp}.png"
            filepath = diagrams_dir / filename
            
            # Write file
            filepath.write_bytes(image_bytes)
            
            output = []
            output.append(f"✅ Diagram downloaded and saved successfully")
            output.append(f"Size: {size}")
            output.append(f"File size: {len(image_bytes):,} bytes")
            output.append(f"File: {filepath}")
            
            logger.info(f"Retrieved diagram and saved to {filepath}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to get diagram: {str(e)}"
            logger.error(f"MCP get_diagram failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def show_diagram(project_id: str = None, size: str = "PREVIEW") -> str:
        """Download and display the project threat model diagram.
        
        This tool downloads the project's automatically generated threat model diagram
        as a PNG image and saves it to the .iriusrisk directory.
        
        Args:
            project_id: Project ID or reference ID (optional if project.json exists)
            size: Image size - ORIGINAL, PREVIEW, or THUMBNAIL (default: PREVIEW)
            
        Returns:
            Status message with diagram file location and details.
        """
        logger.info(f"MCP tool invoked: show_diagram (project_id={project_id}, size={size})")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            from ...utils.project_discovery import find_project_root
            import base64
            
            # Find project root
            project_root, project_config = find_project_root()
            if not project_root:
                project_root = Path.cwd()
            
            # Resolve project ID
            if not project_id and project_config:
                project_id = project_config.get('reference_id') or project_config.get('project_id')
            
            if not project_id:
                error_msg = "❌ No project ID provided and no default project configured"
                logger.error(error_msg)
                return error_msg
            
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get artifacts (diagrams)
            artifacts_response = api_client.get_project_artifacts(project_uuid, page=0, size=100)
            artifacts = artifacts_response.get('_embedded', {}).get('items', [])
            
            if not artifacts:
                error_msg = "❌ No diagram artifacts found for this project"
                logger.error(error_msg)
                return error_msg
            
            # Find diagram artifact (first visible one)
            diagram_artifact = next((a for a in artifacts if a.get('visible', True)), artifacts[0])
            artifact_id = diagram_artifact.get('id')
            
            # Get the artifact content
            content_response = api_client.get_project_artifact_content(artifact_id, size=size.upper())
            base64_content = content_response.get('content')
            
            if not base64_content:
                error_msg = "❌ No image content found in diagram artifact"
                logger.error(error_msg)
                return error_msg
            
            # Decode and save to file
            image_data = base64.b64decode(base64_content)
            
            # Create diagrams directory
            diagrams_dir = project_root / '.iriusrisk' / 'diagrams'
            diagrams_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            filename = f"diagram-{size.lower()}.png"
            diagram_path = diagrams_dir / filename
            
            with open(diagram_path, 'wb') as f:
                f.write(image_data)
            
            # Build output
            output = []
            output.append("🖼️  Threat Model Diagram Downloaded")
            output.append(f"📁 Project: {project_id}")
            output.append(f"📏 Size: {size}")
            output.append(f"💾 Saved to: {diagram_path}")
            output.append(f"📊 File size: {len(image_data):,} bytes")
            output.append("")
            output.append("💡 Open the PNG file in any image viewer to see your threat model diagram")
            
            logger.info(f"Diagram saved to {diagram_path}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to download diagram: {str(e)}"
            logger.error(f"MCP show_diagram failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def generate_report(report_type: str = "countermeasure", format: str = "pdf", 
                             project_id: str = None, output_path: str = None, standard: str = None) -> str:
        """Generate and download an IriusRisk report.
        
        This tool generates various types of reports from IriusRisk projects and saves them
        to the .iriusrisk/reports directory.
        
        Args:
            report_type: Type of report - "countermeasure", "threat", "compliance", "risk-summary"
            format: Output format - "pdf", "html", "xlsx", "csv", "xls" (default: "pdf")
            project_id: Project ID or reference ID (optional if project.json exists)
            output_path: Custom output path (optional, auto-generates if not provided)
            standard: Standard reference ID for compliance reports (required for compliance type)
        
        Returns:
            Status message with report file location and details.
        """
        logger.info(f"MCP tool invoked: generate_report (type={report_type}, format={format}, project_id={project_id})")
        
        try:
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict, is_uuid_format
            from ...utils.project_discovery import find_project_root
            import time
            from datetime import datetime
            
            # Find project root
            project_root, project_config = find_project_root()
            if not project_root:
                project_root = Path.cwd()
            
            # Report type mappings
            report_mappings = {
                'countermeasure': 'technical-countermeasure-report',
                'countermeasures': 'technical-countermeasure-report',
                'threat': 'technical-threat-report',
                'threats': 'technical-threat-report',
                'compliance': 'compliance-report',
                'risk': 'residual-risk',
                'risk-summary': 'residual-risk',
            }
            
            # Normalize report type
            normalized_type = report_type.lower().strip()
            api_report_type = report_mappings.get(normalized_type, report_type)
            
            # Validate format
            supported_formats = ['pdf', 'html', 'xlsx', 'csv', 'xls']
            if format.lower() not in supported_formats:
                error_msg = f"❌ Unsupported format: {format}. Supported: {', '.join(supported_formats)}"
                logger.error(error_msg)
                return error_msg
            
            format = format.lower()
            
            # Resolve project ID
            if not project_id and project_config:
                project_id = project_config.get('reference_id') or project_config.get('project_id')
            
            if not project_id:
                error_msg = "❌ No project ID provided and no default project configured"
                logger.error(error_msg)
                return error_msg
            
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Handle compliance reports that require a standard
            standard_uuid = None
            if 'compliance' in normalized_type:
                if not standard:
                    error_msg = "❌ Compliance reports require a 'standard' parameter. Use the CLI 'iriusrisk projects standards' command to see options."
                    logger.error(error_msg)
                    return error_msg
                
                # Resolve standard
                if is_uuid_format(standard):
                    standard_uuid = standard
                else:
                    standards = api_client.get_project_standards(project_uuid)
                    for std in standards:
                        if std.get('referenceId') == standard or std.get('name') == standard:
                            standard_uuid = std.get('id')
                            break
                    if not standard_uuid:
                        error_msg = f"❌ Standard '{standard}' not found"
                        logger.error(error_msg)
                        return error_msg
            
            # Generate report
            logger.info(f"Generating {api_report_type} report in {format} format")
            operation_id = api_client.generate_report(
                project_id=project_uuid,
                report_type=api_report_type,
                format=format,
                standard=standard_uuid
            )
            
            # Poll for completion
            timeout = 120
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status_response = api_client.get_async_operation_status(operation_id)
                status = status_response.get('status')
                
                if status == 'finished-success':
                    break
                elif status in ['finished-error', 'finished-failure', 'failed']:
                    error_msg = f"❌ Report generation failed: {status_response.get('errorMessage', 'Unknown error')}"
                    logger.error(error_msg)
                    return error_msg
                elif status in ['pending', 'in-progress']:
                    time.sleep(2)
                else:
                    error_msg = f"❌ Unknown operation status: {status}"
                    logger.error(error_msg)
                    return error_msg
            else:
                error_msg = f"❌ Report generation timed out after {timeout} seconds"
                logger.error(error_msg)
                return error_msg
            
            # Get the generated report
            reports = api_client.get_project_reports(project_uuid)
            if not reports:
                error_msg = "❌ No reports found after generation"
                logger.error(error_msg)
                return error_msg
            
            # Find the most recent report of correct type
            target_report = None
            for report in reports:
                if (report.get('reportType') == api_report_type and 
                    report.get('format') == format):
                    target_report = report
                    break
            
            if not target_report:
                error_msg = "❌ Generated report not found"
                logger.error(error_msg)
                return error_msg
            
            # Download report content
            download_url = target_report.get('_links', {}).get('download', {}).get('href')
            if not download_url:
                error_msg = "❌ No download link found"
                logger.error(error_msg)
                return error_msg
            
            content = api_client.download_report_content_from_url(download_url)
            
            # Determine output path
            if output_path:
                report_path = Path(output_path)
            else:
                # Auto-generate filename
                reports_dir = project_root / '.iriusrisk' / 'reports'
                reports_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                filename = f"{normalized_type}-report-{timestamp}.{format}"
                report_path = reports_dir / filename
            
            # Save report
            with open(report_path, 'wb') as f:
                f.write(content)
            
            # Build output
            output = []
            output.append("📊 Report Generated Successfully")
            output.append(f"📁 Project: {project_id}")
            output.append(f"📄 Type: {report_type}")
            output.append(f"📑 Format: {format.upper()}")
            if standard:
                output.append(f"📋 Standard: {standard}")
            output.append(f"💾 Saved to: {report_path}")
            output.append(f"📊 File size: {len(content):,} bytes")
            output.append("")
            output.append("💡 Open the file in your preferred application to view the report")
            
            logger.info(f"Report saved to {report_path}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to generate report: {str(e)}"
            logger.error(f"MCP generate_report failed: {e}")
            return error_msg

