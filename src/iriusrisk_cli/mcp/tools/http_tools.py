"""HTTP-only MCP tools that operate without filesystem access.

These tools are stateless and designed for HTTP transport mode.
They require explicit project_id parameters and return data directly
rather than writing to the filesystem.
"""

import logging
import json
import base64

try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

logger = logging.getLogger(__name__)


def register_http_tools(mcp_server, get_api_client_func):
    """Register stateless tools for HTTP mode.
    
    Args:
        mcp_server: FastMCP server instance
        get_api_client_func: Function that returns a request-scoped API client
    """
    
    @mcp_server.tool()
    async def get_project_overview(project_id: str) -> str:
        """Get comprehensive project overview with statistics and risk summary.
        
        This tool provides a complete snapshot of a project including threat counts,
        countermeasure status, risk levels, and key metadata. Essential for understanding
        project health at a glance in stateless mode.
        
        Args:
            project_id: Project UUID or reference ID
        
        Returns:
            Formatted overview with project metadata, threat statistics, countermeasure
            statistics, risk breakdown, and key insights
        """
        logger.info(f"MCP HTTP tool invoked: get_project_overview (project_id={project_id})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get project details
            project = api_client.get_project(project_uuid)
            
            # Get threats and countermeasures for statistics
            threats_response = api_client.get_threats(project_uuid, page=0, size=1000)
            countermeasures_response = api_client.get_countermeasures(project_uuid, page=0, size=1000)
            
            threats = threats_response.get('_embedded', {}).get('items', [])
            countermeasures = countermeasures_response.get('_embedded', {}).get('items', [])
            
            # Calculate statistics
            threat_stats = _calculate_threat_stats(threats)
            countermeasure_stats = _calculate_countermeasure_stats(countermeasures)
            
            # Get hostname from request to build URL
            try:
                context = mcp_server.get_context()
                request = context.request_context.request
                hostname = request.headers.get("X-IriusRisk-Hostname", "")
                project_url = _build_project_url(hostname, project_uuid)
            except Exception:
                project_url = None
            
            # Format overview
            output = []
            output.append("📊 PROJECT OVERVIEW\n")
            output.append(f"**{project.get('name', 'Unknown')}**")
            output.append(f"UUID: {project.get('id', 'Unknown')}")
            output.append(f"Reference: {project.get('referenceId', 'None')}")
            if project_url:
                output.append(f"🔗 URL: {project_url}")
            output.append(f"Workflow: {project.get('workflowState', {}).get('name', 'Unknown')}")
            output.append(f"Last Updated: {project.get('modelUpdated', 'Unknown')}")
            output.append("")
            
            # Threat Summary
            output.append("🛡️  THREAT SUMMARY")
            output.append(f"Total Threats: {threat_stats['total']}")
            output.append(f"Critical: {threat_stats['by_risk']['critical']}")
            output.append(f"High: {threat_stats['by_risk']['high']}")
            output.append(f"Medium: {threat_stats['by_risk']['medium']}")
            output.append(f"Low: {threat_stats['by_risk']['low']}")
            output.append("")
            output.append("By Status:")
            for status, count in threat_stats['by_state'].items():
                if count > 0:
                    output.append(f"  {status}: {count}")
            output.append("")
            
            # Countermeasure Summary
            output.append("🔐 COUNTERMEASURE SUMMARY")
            output.append(f"Total Countermeasures: {countermeasure_stats['total']}")
            output.append(f"Implemented: {countermeasure_stats['by_state'].get('implemented', 0)}")
            output.append(f"Required: {countermeasure_stats['by_state'].get('required', 0)}")
            output.append(f"Recommended: {countermeasure_stats['by_state'].get('recommended', 0)}")
            output.append(f"Rejected: {countermeasure_stats['by_state'].get('rejected', 0)}")
            output.append("")
            
            # Key insights
            critical_exposed = sum(1 for t in threats if t.get('risk') == 'critical' and t.get('state') == 'expose')
            high_exposed = sum(1 for t in threats if t.get('risk') == 'high' and t.get('state') == 'expose')
            
            output.append("📈 KEY INSIGHTS")
            if critical_exposed > 0:
                output.append(f"⚠️  {critical_exposed} CRITICAL threats are still exposed")
            if high_exposed > 0:
                output.append(f"⚠️  {high_exposed} HIGH risk threats are still exposed")
            
            impl_rate = (countermeasure_stats['by_state'].get('implemented', 0) / countermeasure_stats['total'] * 100) if countermeasure_stats['total'] > 0 else 0
            output.append(f"Implementation Rate: {impl_rate:.1f}%")
            
            logger.info(f"Generated overview for project {project_uuid}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to get project overview: {str(e)}"
            logger.error(f"MCP get_project_overview failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def org_risk_snapshot() -> str:
        """Get organization-wide risk snapshot across all projects.
        
        This tool provides a portfolio-level view of security posture, showing
        high-risk projects, critical threats, and overall statistics. Essential
        for executive/CISO-level visibility in stateless mode.
        
        Returns:
            Formatted snapshot with top risks, project summaries, and key metrics
        """
        logger.info("MCP HTTP tool invoked: org_risk_snapshot")
        
        try:
            api_client = get_api_client_func()
            
            # Get all projects
            response = api_client.get_projects(page=0, size=100)
            projects = response.get('_embedded', {}).get('items', [])
            total_projects = response.get('page', {}).get('totalElements', len(projects))
            
            # Calculate org-level statistics
            org_stats = {
                'total_projects': total_projects,
                'high_risk_projects': [],
                'total_critical_threats': 0,
                'total_high_threats': 0,
                'total_exposed_critical': 0,
                'total_exposed_high': 0,
            }
            
            # Sample top projects for detailed analysis
            for project in projects[:20]:  # Limit to 20 for performance
                project_id = project.get('id')
                project_name = project.get('name')
                
                try:
                    # Get threats for this project
                    threats_resp = api_client.get_threats(project_id, page=0, size=1000)
                    threats = threats_resp.get('_embedded', {}).get('items', [])
                    
                    # Count critical and high threats
                    critical_threats = [t for t in threats if t.get('risk') == 'critical']
                    high_threats = [t for t in threats if t.get('risk') == 'high']
                    exposed_critical = [t for t in critical_threats if t.get('state') == 'expose']
                    exposed_high = [t for t in high_threats if t.get('state') == 'expose']
                    
                    org_stats['total_critical_threats'] += len(critical_threats)
                    org_stats['total_high_threats'] += len(high_threats)
                    org_stats['total_exposed_critical'] += len(exposed_critical)
                    org_stats['total_exposed_high'] += len(exposed_high)
                    
                    # Track high-risk projects
                    if len(exposed_critical) > 0 or len(exposed_high) > 3:
                        org_stats['high_risk_projects'].append({
                            'name': project_name,
                            'id': project_id,
                            'critical_exposed': len(exposed_critical),
                            'high_exposed': len(exposed_high),
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to get threats for project {project_name}: {e}")
                    continue
            
            # Format output
            output = []
            output.append("🏢 ORGANIZATION RISK SNAPSHOT\n")
            output.append(f"Total Projects: {org_stats['total_projects']}")
            output.append(f"Projects Analyzed: {min(20, len(projects))}")
            output.append("")
            
            output.append("⚠️  CRITICAL FINDINGS")
            output.append(f"Total Critical Threats: {org_stats['total_critical_threats']}")
            output.append(f"Total High Risk Threats: {org_stats['total_high_threats']}")
            output.append(f"Exposed Critical: {org_stats['total_exposed_critical']}")
            output.append(f"Exposed High: {org_stats['total_exposed_high']}")
            output.append("")
            
            if org_stats['high_risk_projects']:
                output.append("🔴 HIGH RISK PROJECTS")
                for proj in sorted(org_stats['high_risk_projects'], 
                                 key=lambda p: (p['critical_exposed'], p['high_exposed']), 
                                 reverse=True)[:10]:
                    output.append(f"\n**{proj['name']}**")
                    output.append(f"  UUID: {proj['id']}")
                    if proj['critical_exposed'] > 0:
                        output.append(f"  ⚠️  {proj['critical_exposed']} Critical threats exposed")
                    if proj['high_exposed'] > 0:
                        output.append(f"  ⚠️  {proj['high_exposed']} High risk threats exposed")
                output.append("")
            else:
                output.append("✅ No high-risk projects identified")
                output.append("")
            
            # Recommendations
            output.append("💡 RECOMMENDATIONS")
            if org_stats['total_exposed_critical'] > 0:
                output.append(f"  Priority 1: Address {org_stats['total_exposed_critical']} exposed critical threats")
            if org_stats['total_exposed_high'] > 10:
                output.append(f"  Priority 2: Review {org_stats['total_exposed_high']} exposed high-risk threats")
            if not org_stats['high_risk_projects']:
                output.append("  Continue monitoring and maintaining current security posture")
            
            logger.info(f"Generated org risk snapshot: {org_stats['total_projects']} projects")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to generate org risk snapshot: {str(e)}"
            logger.error(f"MCP org_risk_snapshot failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def generate_report(project_id: str, report_type: str = "countermeasure", 
                             format: str = "pdf", standard: str = None) -> str:
        """Generate and return IriusRisk report as base64 encoded data.
        
        In HTTP mode, reports are returned as base64 encoded strings rather than
        saved to filesystem. Supports countermeasure, threat, compliance, and risk-summary reports.
        
        Args:
            project_id: Project UUID or reference ID
            report_type: Type - countermeasure, threat, compliance, risk-summary (default: countermeasure)
            format: Format - pdf, html, xlsx, csv, xls (default: pdf)
            standard: Standard reference ID for compliance reports (required for compliance type)
        
        Returns:
            Base64 encoded report data with metadata
        """
        logger.info(f"MCP HTTP tool invoked: generate_report (project={project_id}, type={report_type}, format={format})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict, is_uuid_format
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
                    return "❌ Compliance reports require a 'standard' parameter. Use list_standards() to see options."
                
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
            
            # Encode as base64
            encoded = base64.b64encode(content).decode('ascii')
            
            output = []
            output.append(f"✅ Report generated successfully")
            output.append(f"Type: {report_type}")
            output.append(f"Format: {format.upper()}")
            output.append(f"Size: {len(content):,} bytes")
            output.append("")
            output.append("Base64 encoded content:")
            output.append(encoded)
            
            logger.info(f"Generated {format} report for project {project_uuid}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to generate report: {str(e)}"
            logger.error(f"MCP generate_report failed: {e}")
            return error_msg
    
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
        logger.info(f"MCP HTTP tool invoked: list_projects (page={page}, size={size})")
        
        try:
            # Get API client
            try:
                api_client = get_api_client_func()
                logger.debug(f"API client created: {api_client is not None}")
            except Exception as auth_err:
                logger.error(f"Failed to create API client: {auth_err}")
                return f"❌ Authentication failed: {str(auth_err)}"
            
            if api_client is None:
                return "❌ Failed to create API client - authentication may have failed"
            
            # Get projects from API (no filtering)
            try:
                logger.debug(f"Calling get_projects(page={page}, size={size})")
                response = api_client.get_projects(page=page, size=size)
                logger.debug(f"get_projects response type: {type(response)}")
            except Exception as api_err:
                logger.error(f"API call failed: {api_err}")
                return f"❌ API call failed: {str(api_err)}"
            
            if response is None:
                return "❌ API returned None - this may indicate an authentication or connection issue"
            
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                return f"❌ Unexpected response type: {type(response)}"
            
            logger.debug(f"Response keys: {list(response.keys())}")
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
        
        This tool searches for projects matching the given criteria. Use list_projects()
        for a simple unfiltered list.
        
        Args:
            query: Search term for project name (partial match, case-insensitive)
            filter_tags: Filter projects by tags (space-separated)
            filter_workflow_state: Filter by workflow state
            page: Page number for pagination (default: 0)
            size: Number of results per page (default: 20)
        
        Returns:
            Formatted list of matching projects with IDs, names, and key details
        """
        logger.info(f"MCP HTTP tool invoked: search_projects (query={query}, page={page})")
        
        try:
            # Get API client
            try:
                api_client = get_api_client_func()
                logger.debug(f"API client created: {api_client is not None}")
            except Exception as auth_err:
                logger.error(f"Failed to create API client: {auth_err}")
                return f"❌ Authentication failed: {str(auth_err)}"
            
            if api_client is None:
                return "❌ Failed to create API client - authentication may have failed"
            
            # Build filter expression with query
            filters = []
            if query:
                filters.append(f"'name'~'{query}'")
            if filter_tags:
                for tag in filter_tags.split():
                    filters.append(f"'tags'~'{tag}'")
            if filter_workflow_state:
                filters.append(f"'workflowState.name'='{filter_workflow_state}'")
            
            filter_expr = ":AND:".join(filters) if filters else None
            logger.debug(f"Search filter expression: {filter_expr}")
            
            # Get projects from API
            try:
                logger.debug(f"Calling get_projects(page={page}, size={size}, filter={filter_expr})")
                response = api_client.get_projects(
                    page=page,
                    size=size,
                    filter_expression=filter_expr
                )
                logger.debug(f"get_projects response type: {type(response)}")
            except Exception as api_err:
                logger.error(f"API call failed: {api_err}")
                return f"❌ API call failed: {str(api_err)}"
            
            if response is None:
                return "❌ API returned None - this may indicate an authentication or connection issue"
            
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                return f"❌ Unexpected response type: {type(response)}"
            
            logger.debug(f"Response keys: {list(response.keys())}")
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
    async def search_components(query: str, category: str = None, limit: int = 20) -> str:
        """Search component library by name, description, or category.
        
        Downloads complete component library on first call in a session (~1.6MB, thousands of components).
        Subsequent searches in the same conversation use cached data for performance.
        Returns only the most relevant matches to save tokens.
        
        Args:
            query: Search term (e.g., "lambda", "database", "web server", "ec2")
            category: Optional category filter (e.g., "Compute", "Database", "Network")
            limit: Maximum matches to return (default: 20)
        
        Returns:
            JSON object with query, total library size, matches found, and array of matching components
        
        Examples:
            search_components(query="lambda", limit=10)
            search_components(query="database", category="Database")
            search_components(query="api", limit=5)
        
        Note: Make multiple searches if needed - first call downloads library, subsequent calls
        are fast using cached data.
        """
        logger.info(f"MCP HTTP tool invoked: search_components (query={query}, category={category}, limit={limit})")
        
        try:
            api_client = get_api_client_func()
            
            # Get all components (cached per session)
            all_components = await _get_components_cached(api_client, mcp_server)
            
            # Apply category filter if specified
            if category:
                filtered = [c for c in all_components if c.get('category', '').lower() == category.lower()]
                logger.debug(f"Category filter '{category}' reduced to {len(filtered)} components")
            else:
                filtered = all_components
            
            # Search in memory
            matches = _search_components_in_memory(filtered, query, limit)
            
            # Calculate metadata to help AI understand search space
            metadata = _calculate_component_metadata(all_components)
            
            # Count total matches before limit (for search_info)
            all_matches = _search_components_in_memory(filtered, query, limit=999999)
            
            result = {
                "matches": matches,
                "metadata": {
                    "library_info": {
                        "total_components": metadata['total_components'],
                        "cached": hasattr(mcp_server.get_context().session, '_component_cache')
                    },
                    "category_breakdown": metadata['categories'],
                    "search_info": {
                        "query": query,
                        "category_filter": category,
                        "total_matches_in_library": len(all_matches),
                        "returned": len(matches),
                        "limit": limit
                    }
                }
            }
            
            logger.info(f"Search returned {len(matches)} matches (of {len(all_matches)} total) for query '{query}'")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to search components: {str(e)}"
            logger.error(f"MCP search_components failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_trust_zones() -> str:
        """Get the complete IriusRisk trust zone library.
        
        Trust zones define security boundaries in threat models (Internet, DMZ, 
        Internal Network, etc.). This tool returns all available trust zones.
        Small enough (~15KB) to return complete list every time.
        
        Returns:
            JSON array of all trust zone definitions with IDs, names, and risk levels
        
        Examples:
            get_trust_zones()
        """
        logger.info("MCP HTTP tool invoked: get_trust_zones")
        
        try:
            api_client = get_api_client_func()
            
            # Fetch all trust zones (they're small, usually <50 total)
            all_trust_zones = []
            page = 0
            while True:
                response = api_client.get_trust_zones(page=page, size=100)
                
                if response is None:
                    return "❌ API returned None - check connection"
                
                items = response.get('_embedded', {}).get('items', [])
                if not items:
                    break
                all_trust_zones.extend(items)
                
                total = response.get('page', {}).get('totalElements', 0)
                if len(all_trust_zones) >= total:
                    break
                page += 1
            
            logger.info(f"Retrieved {len(all_trust_zones)} trust zones")
            
            # Return all trust zones (small dataset)
            return json.dumps(all_trust_zones, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to get trust zones: {str(e)}"
            logger.error(f"MCP get_trust_zones failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def get_component_categories() -> str:
        """Get list of all component categories.
        
        Returns available component categories (Compute, Database, Network, etc.)
        to help narrow searches. Useful for understanding component organization.
        
        Returns:
            JSON array of category names
        
        Example:
            get_component_categories()
            # Returns: ["Compute", "Database", "Network", "Storage", ...]
        """
        logger.info("MCP HTTP tool invoked: get_component_categories")
        
        try:
            api_client = get_api_client_func()
            
            # Get all components (cached)
            all_components = await _get_components_cached(api_client, mcp_server)
            
            # Extract unique categories
            categories = set()
            for comp in all_components:
                cat = comp.get('category')
                if cat:
                    categories.add(cat)
            
            # Return sorted list
            result = sorted(list(categories))
            
            logger.info(f"Found {len(result)} component categories")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to get component categories: {str(e)}"
            logger.error(f"MCP get_component_categories failed: {e}")
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
            
            # Get hostname from request to build URL
            try:
                context = mcp_server.get_context()
                request = context.request_context.request
                hostname = request.headers.get("X-IriusRisk-Hostname", "")
                project_url = _build_project_url(hostname, project_uuid)
            except Exception:
                project_url = None
            
            # Format output
            output = []
            output.append("📊 Project Details:\n")
            output.append(f"Name: {project.get('name', 'Unknown')}")
            output.append(f"UUID: {project.get('id', 'Unknown')}")
            output.append(f"Reference ID: {project.get('referenceId', 'None')}")
            if project_url:
                output.append(f"🔗 URL: {project_url}")
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
    async def search_threats(project_id: str, query: str = None, risk_level: str = None, 
                            status: str = None, limit: int = 20) -> str:
        """Search threats for a project with intelligent filtering and fuzzy matching.
        
        First call for a project downloads all threats (~250KB for typical project).
        Subsequent searches use cached data. Returns top matches sorted by risk level.
        Includes metadata showing threat distribution by risk and status.
        
        Args:
            project_id: Project UUID or reference ID
            query: Optional fuzzy search on threat name/description (e.g., "sql injection", "xss")
            risk_level: Optional filter by risk - critical, high, medium, low
            status: Optional filter by status - expose, mitigate, accept, partly-mitigate, hidden, not-applicable
            limit: Maximum matches to return (default: 20)
        
        Returns:
            JSON object with threats array and metadata (total, by_risk, by_status)
        
        Examples:
            search_threats(project_id="abc-123")  # Top 20 by risk
            search_threats(project_id="abc-123", risk_level="critical")  # All critical
            search_threats(project_id="abc-123", query="injection", limit=10)  # Fuzzy search
            search_threats(project_id="abc-123", status="expose", risk_level="high")  # Filtered
        """
        logger.info(f"MCP HTTP tool invoked: search_threats (project={project_id}, query={query}, risk={risk_level})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get all threats (cached per project)
            all_threats = await _get_threats_cached(api_client, mcp_server, project_uuid)
            
            # Calculate metadata
            metadata = _calculate_threat_metadata(all_threats)
            
            # Search/filter in memory
            matches = _search_threats_in_memory(all_threats, query, risk_level, status, limit)
            
            result = {
                "threats": matches,
                "metadata": {
                    "project_id": project_id,
                    "library_info": {
                        "total_threats": metadata['total_threats'],
                        "cached": True
                    },
                    "risk_breakdown": metadata['by_risk'],
                    "status_breakdown": metadata['by_status'],
                    "search_info": {
                        "query": query,
                        "risk_filter": risk_level,
                        "status_filter": status,
                        "returned": len(matches),
                        "limit": limit
                    }
                }
            }
            
            logger.info(f"Search returned {len(matches)} threats for project {project_uuid}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to search threats: {str(e)}"
            logger.error(f"MCP search_threats failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def search_countermeasures(project_id: str, query: str = None, status: str = None,
                                     priority: str = None, limit: int = 20) -> str:
        """Search countermeasures for a project with intelligent filtering and fuzzy matching.
        
        First call for a project downloads all countermeasures (~320KB for typical project).
        Subsequent searches use cached data. Returns top matches sorted by priority.
        Includes metadata showing countermeasure distribution by status and priority.
        
        Args:
            project_id: Project UUID or reference ID
            query: Optional fuzzy search on name/description (e.g., "authentication", "encryption")
            status: Optional filter by status - required, recommended, implemented, rejected, not-applicable
            priority: Optional filter by priority - very-high, high, medium, low
            limit: Maximum matches to return (default: 20)
        
        Returns:
            JSON object with countermeasures array and metadata (total, by_status, by_priority)
        
        Examples:
            search_countermeasures(project_id="abc-123")  # Top 20 by priority
            search_countermeasures(project_id="abc-123", status="required")  # All required
            search_countermeasures(project_id="abc-123", query="auth", limit=10)  # Fuzzy search
            search_countermeasures(project_id="abc-123", priority="very-high")  # High priority only
        """
        logger.info(f"MCP HTTP tool invoked: search_countermeasures (project={project_id}, query={query}, priority={priority})")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
            # Resolve to UUID if needed
            project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
            
            # Get all countermeasures (cached per project)
            all_countermeasures = await _get_countermeasures_cached(api_client, mcp_server, project_uuid)
            
            # Calculate metadata
            metadata = _calculate_countermeasure_metadata(all_countermeasures)
            
            # Search/filter in memory
            matches = _search_countermeasures_in_memory(all_countermeasures, query, status, priority, limit)
            
            result = {
                "countermeasures": matches,
                "metadata": {
                    "project_id": project_id,
                    "library_info": {
                        "total_countermeasures": metadata['total_countermeasures'],
                        "cached": True
                    },
                    "status_breakdown": metadata['by_status'],
                    "priority_breakdown": metadata['by_priority'],
                    "search_info": {
                        "query": query,
                        "status_filter": status,
                        "priority_filter": priority,
                        "returned": len(matches),
                        "limit": limit
                    }
                }
            }
            
            logger.info(f"Search returned {len(matches)} countermeasures for project {project_uuid}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"❌ Failed to search countermeasures: {str(e)}"
            logger.error(f"MCP search_countermeasures failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def import_otm(otm_content: str, project_id: str = None) -> str:
        """Import an OTM (Open Threat Model) to create or update a project.
        
        In HTTP mode, OTM content is passed as a string rather than a file path.
        
        Args:
            otm_content: OTM data as JSON string
            project_id: Optional project UUID or reference ID to update an EXISTING project.
                       If provided, checks if project exists first. If project doesn't exist,
                       creates a new project instead of failing with 404.
                       If not provided, creates new project (or auto-updates if name matches).
        
        Returns:
            Status message with project details
        """
        logger.info(f"MCP HTTP tool invoked: import_otm (project_id={project_id})")
        
        try:
            api_client = get_api_client_func()
            
            # Parse OTM content to validate it's valid JSON
            try:
                otm_data = json.loads(otm_content)
            except json.JSONDecodeError as e:
                return f"❌ Invalid OTM JSON: {str(e)}"
            
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
            #   import_otm(otm_content, project_id="badger-app-poug")
            #   → Resolution tries: GET /projects?filter='referenceId'='badger-app-poug'
            #   → No project found yet → Exception: "Project not found"
            #   → But PUT /products/otm/badger-app-poug would have worked!
            #
            # When you DO need UUID resolution:
            #   - V2 API endpoints: GET /v2/projects/{uuid}/threats
            #   - See: mcp/tools/http_tools.py lines 51, 739, 810, 881 (various V2 operations)
            #   - See: utils/project_resolution.py for the resolution utility
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
                else:
                    # Project doesn't exist - create it instead
                    logger.info(f"Project '{project_id}' not found, creating new project instead")
                    result = api_client.import_otm_content(otm_content, auto_update=True)
            else:
                # Create new project
                result = api_client.import_otm_content(otm_content, auto_update=True)
            
            project_id = result.get('id', 'Unknown')
            project_name = result.get('name', 'Unknown')
            
            # Get hostname from request to build URL
            try:
                context = mcp_server.get_context()
                request = context.request_context.request
                hostname = request.headers.get("X-IriusRisk-Hostname", "")
                project_url = _build_project_url(hostname, result.get('id', project_id))
            except Exception:
                project_url = None
            
            output = []
            output.append("✅ OTM import successful!")
            output.append(f"Project ID: {project_id}")
            output.append(f"Project Name: {project_name}")
            if project_url:
                output.append(f"🔗 Project URL: {project_url}")
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
        
        TRANSPARENCY REQUIREMENT: For any status change, especially 'accept', you MUST
        provide a detailed comment explaining why the decision was made, what compensating
        controls exist, and who approved it. This is required for auditability and transparency.
        
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
        logger.info(f"MCP HTTP tool invoked: update_threat_status (project={project_id}, threat={threat_id}, status={status})")
        
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
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
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
            
            logger.info(f"Updated threat {threat_id} to status {status}")
            return f"✅ Threat status updated to '{status}'{comment_status}"
            
        except Exception as e:
            error_msg = f"❌ Failed to update threat status: {str(e)}"
            logger.error(f"MCP update_threat_status failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def update_countermeasure_status(project_id: str, countermeasure_id: str, 
                                          status: str, reason: str, comment: str = None) -> str:
        """Update countermeasure status directly (no local tracking).
        
        TRANSPARENCY REQUIREMENT: For any status change, especially 'implemented', you MUST
        provide a detailed comment explaining what was done, how it was done, and what files
        were modified. This is required for auditability and transparency.
        
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
        logger.info(f"MCP HTTP tool invoked: update_countermeasure_status (project={project_id}, cm={countermeasure_id}, status={status})")
        
        # Validate comment length (IriusRisk API limit is 1000 characters)
        if comment and len(comment) > 1000:
            error_msg = f"❌ Comment too long: {len(comment)} characters (max: 1000). Please shorten your comment and try again."
            logger.error(error_msg)
            return error_msg
        
        # Warn if no comment provided (transparency issue)
        if not comment:
            logger.warning(f"⚠️  Countermeasure status update WITHOUT comment - transparency requirement not met!")
        
        try:
            api_client = get_api_client_func()
            from ...utils.project_resolution import resolve_project_id_to_uuid_strict
            
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
            
            logger.info(f"Updated countermeasure {countermeasure_id} to status {status}")
            return f"✅ Countermeasure status updated to '{status}'{comment_status}"
            
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


def _build_project_url(hostname: str, project_id: str) -> str:
    """Build the IriusRisk project URL.
    
    Args:
        hostname: IriusRisk hostname (e.g., https://release.iriusrisk.com)
        project_id: Project UUID
    
    Returns:
        Full URL to project diagram page
    """
    # Remove trailing slash from hostname if present
    base = hostname.rstrip('/')
    return f"{base}/projects/{project_id}/diagram"


async def _get_components_cached(api_client, mcp_server):
    """Get all components with session-level caching.
    
    First call in a session fetches all components from IriusRisk.
    Subsequent calls in the same session use cached data.
    Cache is automatically freed when session ends.
    
    Args:
        api_client: Request-scoped API client
        mcp_server: FastMCP server instance
    
    Returns:
        List of all component dictionaries
    """
    context = mcp_server.get_context()
    session = context.session
    
    # Check if already cached in this session
    if not hasattr(session, '_component_cache'):
        logger.info("Fetching all components (first call in session)...")
        
        # Fetch all components by pagination
        all_components = []
        page = 0
        while True:
            response = api_client.get_components(page=page, size=100)
            items = response.get('_embedded', {}).get('items', [])
            if not items:
                break
            all_components.extend(items)
            
            total = response.get('page', {}).get('totalElements', 0)
            if len(all_components) >= total:
                break
            page += 1
            
            # Safety limit to prevent infinite loops
            if page > 100:
                logger.warning(f"Stopped pagination at page {page}")
                break
        
        # Cache on session object
        session._component_cache = all_components
        logger.info(f"Cached {len(all_components)} components for session")
    else:
        logger.info(f"Using cached components ({len(session._component_cache)} items)")
    
    return session._component_cache


async def _get_threats_cached(api_client, mcp_server, project_id: str):
    """Get all threats for a project with session-level caching.
    
    First call for a project fetches all threats and caches them.
    Subsequent calls for the same project use cached data.
    Cache is per-project and automatically freed when session ends.
    
    Args:
        api_client: Request-scoped API client
        mcp_server: FastMCP server instance
        project_id: Project UUID
    
    Returns:
        List of all threat dictionaries for the project
    """
    context = mcp_server.get_context()
    session = context.session
    
    cache_key = f'_threats_{project_id}'
    
    # Check if already cached for this project
    if not hasattr(session, cache_key):
        logger.info(f"Fetching all threats for project {project_id} (first call)...")
        
        # Fetch all threats by pagination
        all_threats = []
        page = 0
        while True:
            response = api_client.get_threats(project_id, page=page, size=100)
            items = response.get('_embedded', {}).get('items', [])
            if not items:
                break
            all_threats.extend(items)
            
            total = response.get('page', {}).get('totalElements', 0)
            if len(all_threats) >= total:
                break
            page += 1
            
            # Safety limit
            if page > 100:
                logger.warning(f"Stopped threat pagination at page {page}")
                break
        
        # Cache on session object
        setattr(session, cache_key, all_threats)
        logger.info(f"Cached {len(all_threats)} threats for project {project_id}")
    else:
        cached_threats = getattr(session, cache_key)
        logger.info(f"Using cached threats ({len(cached_threats)} items) for project {project_id}")
    
    return getattr(session, cache_key)


async def _get_countermeasures_cached(api_client, mcp_server, project_id: str):
    """Get all countermeasures for a project with session-level caching.
    
    First call for a project fetches all countermeasures and caches them.
    Subsequent calls for the same project use cached data.
    Cache is per-project and automatically freed when session ends.
    
    Args:
        api_client: Request-scoped API client
        mcp_server: FastMCP server instance
        project_id: Project UUID
    
    Returns:
        List of all countermeasure dictionaries for the project
    """
    context = mcp_server.get_context()
    session = context.session
    
    cache_key = f'_countermeasures_{project_id}'
    
    # Check if already cached for this project
    if not hasattr(session, cache_key):
        logger.info(f"Fetching all countermeasures for project {project_id} (first call)...")
        
        # Fetch all countermeasures by pagination
        all_countermeasures = []
        page = 0
        while True:
            response = api_client.get_countermeasures(project_id, page=page, size=100)
            items = response.get('_embedded', {}).get('items', [])
            if not items:
                break
            all_countermeasures.extend(items)
            
            total = response.get('page', {}).get('totalElements', 0)
            if len(all_countermeasures) >= total:
                break
            page += 1
            
            # Safety limit
            if page > 100:
                logger.warning(f"Stopped countermeasure pagination at page {page}")
                break
        
        # Cache on session object
        setattr(session, cache_key, all_countermeasures)
        logger.info(f"Cached {len(all_countermeasures)} countermeasures for project {project_id}")
    else:
        cached_cms = getattr(session, cache_key)
        logger.info(f"Using cached countermeasures ({len(cached_cms)} items) for project {project_id}")
    
    return getattr(session, cache_key)


def _calculate_threat_metadata(threats: list) -> dict:
    """Calculate metadata about threats for a project.
    
    Args:
        threats: List of all threat dictionaries
    
    Returns:
        Dictionary with total count and breakdowns by risk/status
    """
    metadata = {
        'total_threats': len(threats),
        'by_risk': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'very-low': 0},
        'by_status': {}
    }
    
    for threat in threats:
        # Count by risk level (handle dict or string)
        risk_val = threat.get('risk', 'unknown')
        if isinstance(risk_val, dict):
            risk = str(risk_val.get('name', 'unknown')).lower()
        else:
            risk = str(risk_val).lower()
        
        if risk in metadata['by_risk']:
            metadata['by_risk'][risk] += 1
        
        # Count by status (handle dict or string)
        status_val = threat.get('state', 'unknown')
        if isinstance(status_val, dict):
            status = str(status_val.get('name', 'unknown'))
        else:
            status = str(status_val)
        
        metadata['by_status'][status] = metadata['by_status'].get(status, 0) + 1
    
    return metadata


def _calculate_countermeasure_metadata(countermeasures: list) -> dict:
    """Calculate metadata about countermeasures for a project.
    
    Args:
        countermeasures: List of all countermeasure dictionaries
    
    Returns:
        Dictionary with total count and breakdowns by status/priority
    """
    metadata = {
        'total_countermeasures': len(countermeasures),
        'by_status': {},
        'by_priority': {'very-high': 0, 'high': 0, 'medium': 0, 'low': 0}
    }
    
    for cm in countermeasures:
        # Count by status (handle dict or string)
        status_val = cm.get('state', 'unknown')
        if isinstance(status_val, dict):
            status = str(status_val.get('name', 'unknown'))
        else:
            status = str(status_val)
        
        metadata['by_status'][status] = metadata['by_status'].get(status, 0) + 1
        
        # Count by priority (handle dict or string)
        priority_val = cm.get('priority', 'unknown')
        if isinstance(priority_val, dict):
            priority = str(priority_val.get('name', 'unknown')).lower()
        else:
            priority = str(priority_val).lower()
        
        if priority in metadata['by_priority']:
            metadata['by_priority'][priority] += 1
    
    return metadata


def _search_threats_in_memory(threats: list, query: str = None, 
                              risk_level: str = None, status: str = None, 
                              limit: int = 20) -> list:
    """Search and filter threats with fuzzy matching and sorting.
    
    Args:
        threats: List of all threat dictionaries
        query: Optional fuzzy search on name/description
        risk_level: Optional filter by risk (critical, high, medium, low)
        status: Optional filter by status (expose, mitigate, accept, etc.)
        limit: Maximum results to return
    
    Returns:
        List of matching threats, sorted by risk level (critical first)
    """
    filtered = threats
    
    # Apply risk level filter
    if risk_level:
        filtered = [t for t in filtered if t.get('risk', '').lower() == risk_level.lower()]
    
    # Apply status filter
    if status:
        filtered = [t for t in filtered if t.get('state', '').lower() == status.lower()]
    
    # Apply fuzzy search if query provided
    if query and FUZZY_AVAILABLE:
        from rapidfuzz import fuzz
        scored = []
        query_lower = query.lower()
        
        for threat in filtered:
            name = str(threat.get('name', ''))
            desc = str(threat.get('description', ''))
            
            name_score = fuzz.WRatio(query_lower, name.lower())
            desc_score = fuzz.partial_ratio(query_lower, desc.lower())
            
            final_score = 0
            if name_score > 60:
                final_score += name_score * 5
            if desc_score > 70:
                final_score += desc_score
            
            if final_score > 0:
                scored.append((final_score, threat))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        filtered = [t for score, t in scored]
    elif query:
        # Basic search fallback
        query_lower = query.lower()
        filtered = [t for t in filtered 
                   if query_lower in str(t.get('name', '')).lower() 
                   or query_lower in str(t.get('description', '')).lower()]
    
    # Sort by risk level priority: critical > high > medium > low
    risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'very-low': 4}
    
    def get_risk_key(threat):
        risk_val = threat.get('risk', 'low')
        # Handle case where risk might be a dict
        if isinstance(risk_val, dict):
            risk_str = str(risk_val.get('name', 'low')).lower()
        else:
            risk_str = str(risk_val).lower()
        return risk_order.get(risk_str, 99)
    
    filtered.sort(key=get_risk_key)
    
    return filtered[:limit]


def _search_countermeasures_in_memory(countermeasures: list, query: str = None,
                                      status: str = None, priority: str = None,
                                      limit: int = 20) -> list:
    """Search and filter countermeasures with fuzzy matching and sorting.
    
    Args:
        countermeasures: List of all countermeasure dictionaries
        query: Optional fuzzy search on name/description
        status: Optional filter by status (required, implemented, rejected, etc.)
        priority: Optional filter by priority (very-high, high, medium, low)
        limit: Maximum results to return
    
    Returns:
        List of matching countermeasures, sorted by priority (very-high first)
    """
    filtered = countermeasures
    
    # Apply status filter
    if status:
        filtered = [c for c in filtered if c.get('state', '').lower() == status.lower()]
    
    # Apply priority filter
    if priority:
        filtered = [c for c in filtered if c.get('priority', '').lower() == priority.lower()]
    
    # Apply fuzzy search if query provided
    if query and FUZZY_AVAILABLE:
        from rapidfuzz import fuzz
        scored = []
        query_lower = query.lower()
        
        for cm in filtered:
            name = str(cm.get('name', ''))
            desc = str(cm.get('description', ''))
            
            name_score = fuzz.WRatio(query_lower, name.lower())
            desc_score = fuzz.partial_ratio(query_lower, desc.lower())
            
            final_score = 0
            if name_score > 60:
                final_score += name_score * 5
            if desc_score > 70:
                final_score += desc_score
            
            if final_score > 0:
                scored.append((final_score, cm))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        filtered = [cm for score, cm in scored]
    elif query:
        # Basic search fallback
        query_lower = query.lower()
        filtered = [c for c in filtered 
                   if query_lower in str(c.get('name', '')).lower() 
                   or query_lower in str(c.get('description', '')).lower()]
    
    # Sort by priority: very-high > high > medium > low
    priority_order = {'very-high': 0, 'high': 1, 'medium': 2, 'low': 3}
    
    def get_priority_key(cm):
        priority_val = cm.get('priority', 'low')
        # Handle case where priority might be a dict
        if isinstance(priority_val, dict):
            priority_str = str(priority_val.get('name', 'low')).lower()
        else:
            priority_str = str(priority_val).lower()
        return priority_order.get(priority_str, 99)
    
    filtered.sort(key=get_priority_key)
    
    return filtered[:limit]


def _calculate_component_metadata(components: list) -> dict:
    """Calculate metadata about the component library.
    
    Provides category breakdown to help AI understand the search space
    and make more informed search decisions.
    
    Args:
        components: List of all component dictionaries
    
    Returns:
        Dictionary with total count and category breakdown
    """
    metadata = {
        'total_components': len(components),
        'categories': {}
    }
    
    for comp in components:
        # Category might be a dict or string
        category_val = comp.get('category', 'Uncategorized')
        if isinstance(category_val, dict):
            category = category_val.get('name', 'Uncategorized')
        else:
            category = str(category_val) if category_val else 'Uncategorized'
        
        metadata['categories'][category] = metadata['categories'].get(category, 0) + 1
    
    # Sort categories by count (descending)
    metadata['categories'] = dict(sorted(
        metadata['categories'].items(),
        key=lambda x: x[1],
        reverse=True
    ))
    
    return metadata


def _search_components_in_memory(components: list, query: str, limit: int) -> list:
    """Search components using fuzzy matching (if available) or basic string matching.
    
    Uses rapidfuzz for intelligent fuzzy matching when available, providing:
    - Typo tolerance (e.g., "databse" finds "database")
    - Word order flexibility (e.g., "server web" finds "web server")
    - Partial matching (e.g., "sql" finds "Azure SQL Database")
    
    Falls back to basic string matching if rapidfuzz not installed.
    
    Args:
        components: List of all component dictionaries
        query: Search term
        limit: Maximum matches to return
    
    Returns:
        List of matching components, sorted by relevance
    """
    if FUZZY_AVAILABLE:
        return _fuzzy_search_components(components, query, limit)
    else:
        return _basic_search_components(components, query, limit)


def _fuzzy_search_components(components: list, query: str, limit: int) -> list:
    """Fuzzy search using rapidfuzz library.
    
    Provides intelligent matching with typo tolerance and partial matching.
    """
    from rapidfuzz import fuzz, process
    
    query_lower = query.lower()
    scored = []
    
    for comp in components:
        # Extract searchable fields
        name = str(comp.get('name', ''))
        desc = str(comp.get('description', ''))
        
        # Category might be a dict
        category_val = comp.get('category', '')
        if isinstance(category_val, dict):
            category = str(category_val.get('name', ''))
        else:
            category = str(category_val)
        
        ref_id = str(comp.get('referenceId', ''))
        
        # Calculate fuzzy match scores for different fields
        name_score = fuzz.WRatio(query_lower, name.lower())  # Weighted ratio (best overall)
        ref_score = fuzz.ratio(query_lower, ref_id.lower())  # Exact matching for IDs
        category_score = fuzz.partial_ratio(query_lower, category.lower())  # Partial for categories
        desc_score = fuzz.partial_ratio(query_lower, desc.lower())  # Partial for descriptions
        
        # Weighted scoring system
        final_score = 0
        
        # Name is most important (weight: 5x)
        if name_score > 60:  # Threshold for relevance
            final_score += name_score * 5
        
        # Reference ID (weight: 4x)
        if ref_score > 60:
            final_score += ref_score * 4
        
        # Category (weight: 2x)
        if category_score > 70:
            final_score += category_score * 2
        
        # Description (weight: 1x)
        if desc_score > 70:
            final_score += desc_score
        
        # Bonus for exact matches
        if query_lower == name.lower():
            final_score += 10000
        elif query_lower == ref_id.lower():
            final_score += 5000
        
        # Bonus for shorter names (more specific)
        if final_score > 0 and len(name) < 30:
            final_score += 50
        
        if final_score > 0:
            scored.append((final_score, comp))
    
    # Sort by score descending, return top N
    scored.sort(reverse=True, key=lambda x: x[0])
    return [comp for score, comp in scored[:limit]]


def _basic_search_components(components: list, query: str, limit: int) -> list:
    """Basic search using string matching (fallback when rapidfuzz not available)."""
    query_lower = query.lower()
    scored = []
    
    for comp in components:
        # Safely get string values (some fields might be dicts or None)
        name = str(comp.get('name', '')).lower()
        desc = str(comp.get('description', '')).lower()
        
        # Category might be a dict, extract name if so
        category_val = comp.get('category', '')
        if isinstance(category_val, dict):
            category = str(category_val.get('name', '')).lower()
        else:
            category = str(category_val).lower()
        
        ref_id = str(comp.get('referenceId', '')).lower()
        
        score = 0
        
        # Exact match in name = highest score
        if query_lower == name:
            score = 1000
        # Query is in reference ID = very high
        elif query_lower == ref_id:
            score = 900
        # Name starts with query = high score
        elif name.startswith(query_lower):
            score = 500
        # Query in name = medium-high score
        elif query_lower in name:
            score = 300
        # Query in category = medium score
        elif query_lower in category:
            score = 100
        # Query in description = low score
        elif query_lower in desc:
            score = 50
        
        # Bonus points for shorter names (more specific)
        if score > 0 and len(name) < 30:
            score += 10
        
        if score > 0:
            scored.append((score, comp))
    
    # Sort by score descending, return top N
    scored.sort(reverse=True, key=lambda x: x[0])
    return [comp for score, comp in scored[:limit]]


def _calculate_threat_stats(threats: list) -> dict:
    """Calculate threat statistics from threat list.
    
    Args:
        threats: List of threat dictionaries
    
    Returns:
        Dictionary with threat statistics
    """
    stats = {
        'total': len(threats),
        'by_state': {},
        'by_risk': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'very-low': 0}
    }
    
    for threat in threats:
        state = threat.get('state', 'unknown')
        risk = threat.get('risk', 'unknown')
        
        stats['by_state'][state] = stats['by_state'].get(state, 0) + 1
        if risk in stats['by_risk']:
            stats['by_risk'][risk] += 1
    
    return stats


def _calculate_countermeasure_stats(countermeasures: list) -> dict:
    """Calculate countermeasure statistics from countermeasure list.
    
    Args:
        countermeasures: List of countermeasure dictionaries
    
    Returns:
        Dictionary with countermeasure statistics
    """
    stats = {
        'total': len(countermeasures),
        'by_state': {},
        'by_priority': {'very-high': 0, 'high': 0, 'medium': 0, 'low': 0}
    }
    
    for cm in countermeasures:
        state = cm.get('state', 'unknown')
        priority = cm.get('priority', 'unknown')
        
        stats['by_state'][state] = stats['by_state'].get(state, 0) + 1
        if priority in stats['by_priority']:
            stats['by_priority'][priority] += 1
    
    return stats

