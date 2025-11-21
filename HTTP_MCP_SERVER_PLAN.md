# HTTP MCP Server Implementation Plan

## Overview

This document outlines the plan to add HTTP server mode to the IriusRisk CLI's existing MCP (Model Context Protocol) integration. The goal is to enable remote access to IriusRisk functionality via HTTP while maintaining the existing stdio transport for local AI assistant usage.

## Goals

1. **Add HTTP server capability** without breaking existing stdio mode
2. **Multi-tenant authentication** - each MCP client uses their own IriusRisk API credentials
3. **Stateless operation** - no filesystem dependencies in HTTP mode
4. **Consistent UX** - HTTP mode should feel similar to stdio mode from the AI assistant's perspective
5. **Flexible deployment** - run locally or behind reverse proxy

## Architecture

### Two Transport Modes

#### Stdio Mode (Current Implementation)
- **Use Case**: Local AI assistants (Claude Desktop, Cursor, etc.)
- **Transport**: stdin/stdout
- **State**: Filesystem-based (`.iriusrisk/` directory)
- **Authentication**: Environment variables or user config files
- **Project Context**: Derived from local `.iriusrisk/project.json`
- **Workflow**: Track updates locally, sync to IriusRisk in batches

#### HTTP Mode (New Implementation)
- **Use Case**: Remote AI assistants accessing centralized server
- **Transport**: HTTP (no SSE, no WebSocket)
- **State**: Stateless - no filesystem access
- **Authentication**: Per-request via HTTP headers
- **Project Context**: Explicit project_id passed in each tool call
- **Workflow**: Direct API operations, no local tracking

### Command Structure

```bash
# Stdio mode (default, unchanged)
iriusrisk mcp

# HTTP server mode (new)
iriusrisk mcp --server --host 127.0.0.1 --port 8000
```

### MCP Client Configuration

**Stdio Mode:**
```json
{
  "mcpServers": {
    "iriusrisk-cli": {
      "command": "iriusrisk",
      "args": ["mcp"],
      "env": {
        "IRIUS_HOSTNAME": "https://myinstance.iriusrisk.com",
        "IRIUS_API_KEY": "user-api-key"
      }
    }
  }
}
```

**HTTP Mode:**
```json
{
  "mcpServers": {
    "iriusrisk-remote": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "X-IriusRisk-API-Key": "user-api-key",
        "X-IriusRisk-Hostname": "https://myinstance.iriusrisk.com"
      }
    }
  }
}
```

## Authentication

### HTTP Mode Per-Request Authentication

**Flow:**
1. MCP client sends request with headers:
   - `X-IriusRisk-API-Key`: User's IriusRisk API key
   - `X-IriusRisk-Hostname`: IriusRisk instance URL
2. Server extracts headers from incoming request
3. Server creates request-scoped `IriusRiskApiClient` with those credentials
4. Server executes tool with that API client
5. Server returns response
6. Server discards API client (stateless)

**Security:**
- Server NEVER stores credentials
- Each request authenticated independently
- Multi-tenant: different clients = different IriusRisk users
- Credentials only in memory during request processing

**Implementation:**
```python
# Using FastMCP's dependency injection
from fastmcp.server.dependencies import get_http_request

@mcp_server.tool()
async def some_tool(project_id: str):
    request = get_http_request()
    api_key = request.headers.get("X-IriusRisk-API-Key")
    hostname = request.headers.get("X-IriusRisk-Hostname")
    
    if not api_key or not hostname:
        raise ValueError("Missing authentication headers")
    
    # Create request-scoped API client
    api_client = create_api_client(hostname, api_key)
    
    # Use it for this request
    result = api_client.get_project(project_id)
    return result
```

## Tool Sets

### Shared Tools (Both Modes)

These tools work identically in both modes:

- `initialize_iriusrisk_workflow()` - workflow instructions (may have mode-specific variants)
- `get_cli_version()` - version info
- `project_status(project_id)` - check project status
- `list_standards(project_id)` - list compliance standards
- `architecture_and_design_review()` - guidance (may have mode-specific variants)
- `security_development_advisor()` - guidance (may have mode-specific variants)
- `list_project_versions(project_id)` - list project versions
- `create_project_version(name, description, project_id)` - create version snapshot
- `analyze_source_material()` - analysis instructions
- `create_threat_model()` - threat modeling instructions
- `threats_and_countermeasures()` - T&C instructions

### Stdio-Only Tools

These tools require filesystem access and are NOT available in HTTP mode:

- `sync(project_path)` - downloads data to `.iriusrisk/` directory
- `track_threat_update(project_path, ...)` - tracks updates in local `updates.json`
- `track_countermeasure_update(project_path, ...)` - tracks updates in local `updates.json`
- `create_countermeasure_issue(project_path, ...)` - tracks issue requests in local `updates.json`
- `get_pending_updates(project_path)` - reads local `updates.json`
- `clear_updates(project_path)` - clears local `updates.json`
- `show_diagram(project_path, ...)` - writes diagram PNG to filesystem

### HTTP-Only Tools

These tools are specific to HTTP mode's stateless workflow:

**Project Discovery:**
- `list_projects(filter_name, filter_tags, filter_workflow_state, page, size)` - search/list projects
- `get_project(project_id)` - get detailed project info

**Data Retrieval:**
- `get_threats(project_id, filters)` - get threats for a project
- `get_countermeasures(project_id, filters)` - get countermeasures for a project
- `get_components(project_id)` - get system components for a project

**Direct Status Updates:**
- `update_threat_status(project_id, threat_id, status, reason, comment)` - immediate API update
- `update_countermeasure_status(project_id, countermeasure_id, status, reason, comment)` - immediate API update
- `create_issue_for_countermeasure(project_id, countermeasure_id, issue_tracker_id)` - immediate issue creation

**Modified Tools:**
- `import_otm(otm_content, project_id)` - accepts OTM as string content, not file path
- `get_diagram(project_id, size)` - returns base64 encoded PNG, not file path

### Excluded from HTTP Mode (For Now)

- `generate_report()` - disabled in HTTP mode initially (can be enabled later to return base64)

## Workflow Comparison

### Stdio Mode Workflow

```
User: "Create a threat model for this project"
AI Assistant:
1. Calls sync() to download component library
2. Analyzes local codebase
3. Creates OTM file on filesystem
4. Calls import_otm(file_path)
5. Calls sync(project_path) again to download threats/countermeasures
6. Reads threats.json and countermeasures.json from .iriusrisk/
7. Discusses threats with user
8. Calls track_threat_update() for status changes (stored locally)
9. Calls sync() to push updates to IriusRisk
```

### HTTP Mode Workflow

```
User: "Create a threat model for the Badger project"
AI Assistant:
1. Calls list_projects(filter_name="Badger") to find project
2. Analyzes codebase (no local files needed)
3. Creates OTM content as string
4. Calls import_otm(otm_content, project_id="badger-id")
5. Waits for processing
6. Calls get_threats(project_id="badger-id") to retrieve threats
7. Discusses threats with user
8. Calls update_threat_status(project_id, threat_id, status, reason, comment) directly
   (No local tracking - immediate API calls)
```

### Key Differences

| Aspect | Stdio Mode | HTTP Mode |
|--------|------------|-----------|
| **Project Context** | From `.iriusrisk/project.json` | Explicitly passed in each call |
| **Data Storage** | Local files in `.iriusrisk/` | Fetched on-demand from API |
| **Update Tracking** | Batched in `updates.json` | Direct API calls |
| **OTM Import** | File path | String content |
| **Diagrams** | Saved to filesystem | Returned as base64 |
| **State** | Persistent across commands | Stateless per request |

## Implementation Steps

### Phase 1: Core Infrastructure

1. **Refactor API Client Creation**
   - Create factory function for request-scoped API clients
   - Support both singleton (stdio) and per-request (HTTP) patterns
   - Extract credentials from request headers in HTTP mode

2. **Add Command-Line Options**
   - Add `--server` flag to `mcp` command
   - Add `--host` and `--port` options
   - Branch logic based on transport mode

3. **FastMCP HTTP Configuration**
   - Research FastMCP's `get_http_request()` dependency injection
   - Set up HTTP transport with FastMCP
   - Implement header extraction middleware

### Phase 2: Tool Registration

1. **Create Tool Registration Functions**
   - `register_stdio_tools(mcp_server, cli_ctx)` - current tools
   - `register_http_tools(mcp_server)` - stateless tools
   - `register_shared_tools(mcp_server, api_client)` - common tools

2. **Implement Mode Detection**
   - Pass transport mode through tool context
   - Allow tools to adapt behavior based on mode

### Phase 3: HTTP-Specific Tools

1. **Project Discovery Tools**
   - `list_projects()` - wrapper around existing API client methods
   - `get_project()` - wrapper around existing API client methods

2. **Data Retrieval Tools**
   - `get_threats()` - fetch and return as JSON
   - `get_countermeasures()` - fetch and return as JSON
   - `get_components()` - fetch and return as JSON

3. **Direct Update Tools**
   - `update_threat_status()` - direct API call, no local tracking
   - `update_countermeasure_status()` - direct API call
   - `create_issue_for_countermeasure()` - direct API call

4. **Modified Tools**
   - `import_otm()` - accept string content parameter
   - `get_diagram()` - return base64 encoded image

### Phase 4: Instructions/Prompts

1. **HTTP-Specific Workflow Instructions**
   - Modify `initialize_iriusrisk_workflow()` to detect mode
   - Create HTTP-specific workflow prompt
   - Explain stateless, project-id-based workflow

2. **Update Other Guidance Tools**
   - Adapt `architecture_and_design_review()` for HTTP mode
   - Adapt `security_development_advisor()` for HTTP mode

### Phase 5: Testing

1. **Unit Tests**
   - Test per-request API client creation
   - Test header extraction
   - Test tool execution in both modes

2. **Integration Tests**
   - Test stdio mode still works (regression)
   - Test HTTP server startup
   - Test multi-tenant scenarios (multiple clients with different keys)
   - Test error handling (missing headers, invalid credentials)

3. **Manual Testing**
   - Run HTTP server locally
   - Configure MCP client with headers
   - Test full workflow with AI assistant

## File Organization

### New Files to Create

```
src/iriusrisk_cli/
├── commands/
│   └── mcp.py (modify existing)
├── mcp/
│   ├── __init__.py
│   ├── transport.py          # Transport mode detection
│   ├── http_server.py        # HTTP server implementation
│   ├── stdio_server.py       # Stdio server (refactor from mcp.py)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── shared_tools.py   # Tools for both modes
│   │   ├── stdio_tools.py    # Filesystem-dependent tools
│   │   └── http_tools.py     # Stateless HTTP tools
│   └── auth.py               # HTTP authentication handling
├── prompts/
│   ├── http_workflow.md      # HTTP-specific workflow instructions
│   └── (existing prompts)
```

### Modified Files

- `src/iriusrisk_cli/commands/mcp.py` - add CLI options, route to transport modes
- `src/iriusrisk_cli/api_client.py` - support request-scoped client creation
- `manifest.json` - update with new HTTP tools

## Open Questions / Considerations

### 1. FastMCP HTTP Support
- Does FastMCP fully support HTTP transport with header access?
- Need to verify `get_http_request()` is available and works as expected
- May need to fall back to uvicorn/starlette if FastMCP doesn't support our needs

### 2. Error Handling
- How to handle missing authentication headers?
- How to handle invalid API keys?
- Should we return structured error responses?

### 3. HTTPS / TLS
- Should the server support TLS directly?
- Or assume it runs behind reverse proxy (nginx) for HTTPS?
- Probably assume reverse proxy for production

### 4. Rate Limiting
- Should we implement rate limiting in the HTTP server?
- Or rely on IriusRisk API's rate limiting?

### 5. Logging
- How to log in multi-tenant HTTP mode?
- Should we log which user (API key) is making requests?
- Privacy/security considerations

### 6. Performance
- Connection pooling for API clients?
- Caching of frequently accessed data?
- Keep it simple for v1, optimize later if needed

## Success Criteria

The implementation will be considered successful when:

1. ✅ Stdio mode continues to work exactly as before (no regressions)
2. ✅ HTTP server can be started with `iriusrisk mcp --server`
3. ✅ Multiple MCP clients can connect with different API keys
4. ✅ Each client's requests use their own credentials
5. ✅ All HTTP-mode tools work correctly
6. ✅ Workflow instructions accurately describe HTTP mode
7. ✅ Server is stateless (no filesystem dependencies)
8. ✅ AI assistant can complete full workflow in HTTP mode:
   - Search/list projects
   - Import OTM
   - Retrieve threats/countermeasures
   - Update statuses
   - Create issues

## Future Enhancements (Not in Initial Implementation)

- OAuth support (when IriusRisk backend supports it)
- WebSocket transport for streaming
- Report generation in HTTP mode (return base64 encoded reports)
- Sync-like functionality (bulk data download endpoint)
- Token-based authentication (server issues tokens instead of using API keys directly)
- Admin API for server health/metrics
- Request rate limiting
- Request/response logging and audit trail

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Shiv Deepak - Remote MCP Server Tutorial](https://shivdeepak.com/posts/lets-write-a-remote-mcp-server/)
- [IriusRisk API Documentation](https://iriusrisk.com/docs/api/)

## Next Steps

1. ✅ Review and approve this implementation plan
2. Research FastMCP HTTP capabilities in detail
3. Create proof-of-concept for per-request authentication
4. Implement Phase 1 (core infrastructure)
5. Implement Phase 2 (tool registration)
6. Continue through phases 3-5

