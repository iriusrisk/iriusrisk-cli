"""HTTP-only MCP tools that operate without filesystem access.

These tools are stateless and designed for HTTP transport mode.
They require explicit project_id parameters and return data directly
rather than writing to the filesystem.
"""

import logging
import json
import base64

logger = logging.getLogger(__name__)


def register_http_tools(mcp_server, get_api_client_func):
    """Register stateless tools for HTTP mode.
    
    Args:
        mcp_server: FastMCP server instance
        get_api_client_func: Function that returns a request-scoped API client
    """
    
    @mcp_server.tool()
    async def list_projects(filter_name: str = None, filter_tags: str = None, 
                           filter_workflow_state: str = None, page: int = 0, size: int = 20) -> str:
        """List and search IriusRisk projects.
        
        This tool allows searching for projects by name, tags, or workflow state.
        Essential for HTTP mode where there's no local project context.
        
        Args:
            filter_name: Filter projects by name (partial match)
            filter_tags: Filter projects by tags (space-separated)
            filter_workflow_state: Filter by workflow state
            page: Page number for pagination (default: 0)
            size: Number of results per page (default: 20)
        
        Returns:
            Formatted list of projects with IDs, names, and key details
        """
        logger.info(f"MCP HTTP tool invoked: list_projects (name={filter_name}, page={page})")
        
        try:
            api_client = get_api_client_func()
            
            # Build filter expression
            filters = []
            if filter_name:
                filters.append(f"'name'~'{filter_name}'")
            if filter_tags:
                for tag in filter_tags.split():
                    filters.append(f"'tags'~'{tag}'")
            if filter_workflow_state:
                filters.append(f"'workflowState.name'='{filter_workflow_state}'")
            
            filter_expr = ":AND:".join(filters) if filters else None
            
            # Get projects from API
            response = api_client.get_projects(
                page=page,
                size=size,
                filter_expression=filter_expr
            )
            
            projects = response.get('_embedded', {}).get('items', [])
            page_info = response.get('page', {})
            total = page_info.get('totalElements', 0)
            
            if not projects:
                return "No projects found matching the specified filters."
            
            # Format output
            output = []
            output.append(f"📋 Found {total} project(s) matching filters\n")
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
            
            logger.info(f"Listed {len(projects)} projects successfully")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to list projects: {str(e)}"
            logger.error(f"MCP list_projects failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_project(project_id: str) -> str:
        """Get detailed information about a specific project.
        
        Args:
            project_id: Project UUID or reference ID
        
        Returns:
            Detailed project information including metadata and status
        """
        logger.info(f"MCP HTTP tool invoked: get_project (project_id={project_id})")
        
        try:
            api_client = get_api_client_func()
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
    async def get_threats(project_id: str, filter_status: str = None, limit: int = 100) -> str:
        """Get threats for a specific project.
        
        Args:
            project_id: Project UUID or reference ID
            filter_status: Optional filter by status (e.g., 'required', 'implemented')
            limit: Maximum number of threats to return (default: 100)
        
        Returns:
            JSON string containing threats data
        """
        logger.info(f"MCP HTTP tool invoked: get_threats (project_id={project_id})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get threats from API
            response = api_client.get_threats(project_uuid, page=0, size=limit)
            threats = response.get('_embedded', {}).get('items', [])
            
            # Apply status filter if provided
            if filter_status:
                threats = [t for t in threats if t.get('state') == filter_status]
            
            logger.info(f"Retrieved {len(threats)} threats for project {project_uuid}")
            return json.dumps(threats, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to get threats: {str(e)}"
            logger.error(f"MCP get_threats failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_countermeasures(project_id: str, filter_status: str = None, limit: int = 100) -> str:
        """Get countermeasures for a specific project.
        
        Args:
            project_id: Project UUID or reference ID
            filter_status: Optional filter by status (e.g., 'required', 'implemented')
            limit: Maximum number of countermeasures to return (default: 100)
        
        Returns:
            JSON string containing countermeasures data
        """
        logger.info(f"MCP HTTP tool invoked: get_countermeasures (project_id={project_id})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get countermeasures from API
            response = api_client.get_countermeasures(project_uuid, page=0, size=limit)
            countermeasures = response.get('_embedded', {}).get('items', [])
            
            # Apply status filter if provided
            if filter_status:
                countermeasures = [c for c in countermeasures if c.get('state') == filter_status]
            
            logger.info(f"Retrieved {len(countermeasures)} countermeasures for project {project_uuid}")
            return json.dumps(countermeasures, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to get countermeasures: {str(e)}"
            logger.error(f"MCP get_countermeasures failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def import_otm(otm_content: str, project_id: str = None) -> str:
        """Import an OTM (Open Threat Model) to create or update a project.
        
        In HTTP mode, OTM content is passed as a string rather than a file path.
        
        Args:
            otm_content: OTM data as JSON string
            project_id: Optional project UUID to update (creates new project if not provided)
        
        Returns:
            Status message with project details
        """
        logger.info(f"MCP HTTP tool invoked: import_otm (project_id={project_id})")
        
        try:
            api_client = get_api_client_func()
            
            # Parse OTM content
            try:
                otm_data = json.loads(otm_content)
            except json.JSONDecodeError as e:
                return f"❌ Invalid OTM JSON: {str(e)}"
            
            # Import via API
            result = api_client.import_otm_data(otm_data, project_id=project_id)
            
            project_id = result.get('id', 'Unknown')
            project_name = result.get('name', 'Unknown')
            
            output = []
            output.append("✅ OTM import successful!")
            output.append(f"Project ID: {project_id}")
            output.append(f"Project Name: {project_name}")
            output.append("")
            output.append("💡 Use get_threats() and get_countermeasures() to retrieve generated security data")
            
            logger.info(f"OTM imported successfully for project {project_id}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to import OTM: {str(e)}"
            logger.error(f"MCP import_otm failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def update_threat_status(project_id: str, threat_id: str, status: str, 
                                   reason: str, comment: str = None) -> str:
        """Update threat status directly (no local tracking).
        
        Args:
            project_id: Project UUID or reference ID
            threat_id: Threat UUID
            status: New status (accept, mitigate, expose, partly-mitigate, hidden)
            reason: Explanation for the status change
            comment: Optional HTML-formatted comment with details
        
        Returns:
            Confirmation message
        """
        logger.info(f"MCP HTTP tool invoked: update_threat_status (project={project_id}, threat={threat_id}, status={status})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Update threat status via API
            api_client.update_threat_status(project_uuid, threat_id, status)
            
            # Add comment if provided
            if comment:
                api_client.create_threat_comment(threat_id, comment)
            
            logger.info(f"Updated threat {threat_id} to status {status}")
            return f"✅ Threat status updated to '{status}'"
            
        except Exception as e:
            error_msg = f"❌ Failed to update threat status: {str(e)}"
            logger.error(f"MCP update_threat_status failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def update_countermeasure_status(project_id: str, countermeasure_id: str, 
                                          status: str, reason: str, comment: str = None) -> str:
        """Update countermeasure status directly (no local tracking).
        
        Args:
            project_id: Project UUID or reference ID
            countermeasure_id: Countermeasure UUID
            status: New status (required, recommended, implemented, rejected, not-applicable)
            reason: Explanation for the status change
            comment: Optional HTML-formatted comment with implementation details
        
        Returns:
            Confirmation message
        """
        logger.info(f"MCP HTTP tool invoked: update_countermeasure_status (project={project_id}, cm={countermeasure_id}, status={status})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Update countermeasure status via API
            api_client.update_countermeasure_status(project_uuid, countermeasure_id, status)
            
            # Add comment if provided
            if comment:
                api_client.create_countermeasure_comment(countermeasure_id, comment)
            
            logger.info(f"Updated countermeasure {countermeasure_id} to status {status}")
            return f"✅ Countermeasure status updated to '{status}'"
            
        except Exception as e:
            error_msg = f"❌ Failed to update countermeasure status: {str(e)}"
            logger.error(f"MCP update_countermeasure_status failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_diagram(project_id: str, size: str = "PREVIEW") -> str:
        """Get the project threat model diagram as base64 encoded PNG.
        
        Args:
            project_id: Project UUID or reference ID
            size: Image size - ORIGINAL, PREVIEW, or THUMBNAIL (default: PREVIEW)
        
        Returns:
            Base64 encoded PNG image data
        """
        logger.info(f"MCP HTTP tool invoked: get_diagram (project_id={project_id}, size={size})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
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
            
            logger.info(f"Retrieved diagram for project {project_uuid}")
            return base64_content
            
        except Exception as e:
            error_msg = f"❌ Failed to get diagram: {str(e)}"
            logger.error(f"MCP get_diagram failed: {e}")
            return error_msg

