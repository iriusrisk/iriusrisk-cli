# IriusRisk HTTP MCP Server Workflow Instructions

## Overview

You are interacting with an IriusRisk CLI MCP server running in **HTTP mode**. This mode operates statelessly without access to the local filesystem. All operations are performed directly against the IriusRisk API.

## Key Differences from Local (Stdio) Mode

### Project Context
- **No local `.iriusrisk/` directory** - all data is fetched on-demand from IriusRisk
- **Explicit project_id required** - you must pass project_id with every tool call
- **Project discovery** - use `list_projects()` to find and select projects

### Data Access
- **No local file storage** - threats, countermeasures, and other data are retrieved via API calls
- **Direct API operations** - changes are applied immediately, no local tracking
- **No sync workflow** - data is fetched when needed, not synced to disk

### Workflow
- **Stateless** - each request is independent, no persistent state between calls
- **Real-time** - all operations happen immediately against IriusRisk API
- **Project-centric** - always work with specific project IDs

## Available Tools

### Project Discovery & Selection
```
list_projects(filter_name, filter_tags, filter_workflow_state, page, size)
```
Search and list projects. Essential for finding which project to work with.

**Example workflow:**
```
User: "Let's work on the Badger project"
You: list_projects(filter_name="Badger")
     # Returns list of matching projects with UUIDs
     # Use the UUID in subsequent calls
```

### Project Information
```
get_project(project_id)
get_project_overview(project_id)
```
Get detailed information about a specific project. Use `get_project_overview()` for comprehensive statistics including threat/countermeasure counts and risk levels.

### Component & Trust Zone Library
```
search_components(query, category, limit)
get_component_categories()
get_trust_zones()
```
**IMPORTANT**: Search the component library before creating threat models.

**Best Practice Workflow:**
1. `get_component_categories()` - See what categories exist
2. `search_components(query="database", category="Database", limit=20)` - Find specific components
3. Make multiple searches if needed (e.g., "lambda", "api gateway", "dynamodb")
4. First search downloads library (~1.6MB), subsequent searches use cached data
5. `get_trust_zones()` - Get all trust zones (small, returns complete list)

**Session Caching**: The component library is downloaded once per conversation and cached.
Multiple searches in the same session are fast and don't re-download.

### Threat Model Data
```
get_threats(project_id, filter_status, limit)
get_countermeasures(project_id, filter_status, limit)
```
Retrieve threats and countermeasures for a project. Returns JSON data.

### Organization Overview
```
org_risk_snapshot()
```
Get organization-wide risk view showing high-risk projects and portfolio-level metrics. Essential for executive/CISO visibility.

### Status Updates
```
update_threat_status(project_id, threat_id, status, reason, comment)
update_countermeasure_status(project_id, countermeasure_id, status, reason, comment)
```
Update threat/countermeasure status **immediately** in IriusRisk. No local tracking.

### OTM Import
```
import_otm(otm_content, project_id)
```
Import OTM data. Pass OTM as JSON string (not file path).

### Diagrams
```
get_diagram(project_id, size)
```
Returns base64 encoded PNG diagram (not saved to disk).

## Typical Workflow Examples

### Example 1: Reviewing a Project's Threats

```
User: "Show me the top 5 threats for the Badger project"

Step 1: Find the project
You: list_projects(filter_name="Badger")
Response: [Project found: UUID=abc-123, Name="Badger Web App"]

Step 2: Get threats
You: get_threats(project_id="abc-123", limit=100)
Response: [JSON data with all threats]

Step 3: Analyze and present
You: [Parse JSON, sort by risk, present top 5 to user]
```

### Example 2: Updating Threat Status

```
User: "Mark the SQL injection threat as mitigated"

Step 1: Get current threats (if not already fetched)
You: get_threats(project_id="abc-123")

Step 2: Find the specific threat
You: [Search through threats for SQL injection]
     Threat ID: def-456

Step 3: Update status immediately
You: update_threat_status(
       project_id="abc-123",
       threat_id="def-456",
       status="mitigate",
       reason="Implemented parameterized queries",
       comment="<p>Updated all database queries to use parameterized statements...</p>"
     )
Response: ✅ Threat status updated to 'mitigate'
```

### Example 3: Creating a Threat Model

```
User: "Create a threat model for this application"

Step 1: Search for needed components
You: search_components(query="web server", limit=10)
Response: [Top 10 web server components]
You: search_components(query="database", limit=10)
Response: [Top 10 database components]
You: search_components(query="load balancer", limit=5)
Response: [Top 5 load balancer components]

Step 2: Get trust zones
You: get_trust_zones()
Response: [JSON array with trust zone objects including id, name, trustRating]

⚠️ CRITICAL TRUST ZONE REQUIREMENTS:
- Parse the JSON response and extract the `id` field (UUID) from each trust zone
- Use the EXACT UUID from the `id` field in your OTM file
- DO NOT invent trust zone IDs or use descriptive names as IDs
- DO NOT use trust zone `name` as the ID
- Example from response: {"id": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c", "name": "Internet", "risk": {"trustRating": 1}}
- Use in OTM: parent: { trustZone: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c" }

Step 3: Analyze codebase
You: [Analyze user's code, select appropriate components from search results]

Step 4: Create OTM structure
You: [Build OTM JSON using selected components and EXACT trust zone UUIDs from get_trust_zones()]

Note: First component search downloads library, subsequent searches are instant (cached).

⚠️ OTM TRUST ZONE REQUIREMENTS:
When creating the OTM file:
1. In the trustZones section: Use the exact UUID from get_trust_zones() response in the `id` field
2. In component parents: Use `parent: { trustZone: "exact-uuid" }` with the UUID from get_trust_zones()
3. DO NOT invent new trust zone IDs or use descriptive names
4. Example:
   ```json
   "trustZones": [
     {
       "id": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c",  // Exact UUID from get_trust_zones()
       "name": "Internet",  // Descriptive name (can customize)
       "risk": { "trustRating": 1 }  // From get_trust_zones()
     }
   ],
   "components": [
     {
       "id": "web-lb",
       "name": "Load Balancer",
       "type": "CD-V2-AWS-ALB",
       "parent": { 
         "trustZone": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  // Exact UUID from above
       }
     }
   ]
   ```

Step 5: Import to IriusRisk
You: import_otm(
       otm_content="{...OTM JSON as string...}",
       project_id=null  # Creates new project
     )
Response: [Project created with UUID=xyz-789]

Step 4: Wait for processing
You: [IriusRisk generates threats automatically]

Step 5: Retrieve generated threats
You: get_threats(project_id="xyz-789")
Response: [JSON with auto-generated threats]

Step 6: Present to user
You: [Analyze and present threats to user]
```

### Example 4: Evolving an Existing Threat Model

```
User: "Add an EC2 instance to the Public DMZ trust zone in the Badger project"

Step 1: Get current project
You: get_project(project_id="abc-123")

Step 2: Create updated OTM
You: [Build OTM with additional EC2 component in Public DMZ]

Step 3: Update project
You: import_otm(
       otm_content="{...updated OTM JSON...}",
       project_id="abc-123"  # Updates existing project
     )

Step 4: Get updated threats
You: get_threats(project_id="abc-123")
Response: [JSON includes new threats for EC2 instance]

Step 5: Explain changes
You: [Highlight new threats introduced by EC2 instance]
```

## Important Guidelines

### Critical: Trust Zone IDs

**⚠️ MOST COMMON ERROR:** Using wrong trust zone IDs or inventing IDs

When you call `get_trust_zones()`, you receive JSON like:
```json
[
  {
    "id": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c",
    "name": "Internet",
    "risk": {"trustRating": 1}
  },
  {
    "id": "f0ba7722-39b6-4c81-8290-a30a248bb8d9",
    "name": "Public Cloud",
    "risk": {"trustRating": 5}
  }
]
```

**YOU MUST:**
1. Parse the JSON response
2. Extract the `id` field (this is a UUID)
3. Use that EXACT UUID in your OTM file
4. DO NOT use the `name` as an ID
5. DO NOT invent trust zone IDs like "internet" or "dmz" or "public-cloud"

**In OTM trustZones section:**
```json
"trustZones": [
  {
    "id": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c",  // UUID from get_trust_zones()
    "name": "Internet",  // Can use the name or customize
    "risk": {"trustRating": 1}  // Use trustRating from get_trust_zones()
  }
]
```

**In component parent:**
```json
"components": [
  {
    "id": "my-component",
    "parent": {
      "trustZone": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  // Exact UUID
    }
  }
]
```

### Always Pass project_id
Every operation needs an explicit project ID. Don't assume project context from previous calls.

**Good:**
```
get_threats(project_id="abc-123")
update_threat_status(project_id="abc-123", threat_id="def-456", ...)
```

**Bad:**
```
get_threats()  # ❌ Missing project_id
update_threat_status(threat_id="def-456", ...)  # ❌ Missing project_id
```

### Use UUIDs, Not Reference IDs
When you get a project from `list_projects()`, use the **UUID** (the `id` field), not the `referenceId`.

### Trust Zones Are UUIDs
Trust zone IDs are UUIDs like `"b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"`, NOT names like `"internet"` or `"dmz"`. Always use the exact `id` field from `get_trust_zones()` response.

### No Local Files
- Don't try to read/write `.iriusrisk/` directory
- Don't use `sync()` tool (not available in HTTP mode)
- Don't track updates locally
- **Use `get_components()` and `get_trust_zones()` instead of sync** to get the library data

### Direct Operations
- Status updates happen immediately via API
- No batching or local tracking
- Each change is committed instantly

### Parse JSON Responses
Tools like `get_threats()` and `get_countermeasures()` return JSON strings. Parse them to extract specific information for the user.

### HTML Formatting for Comments
When adding comments to threats/countermeasures, use HTML formatting:
```html
<p>Main description paragraph.</p>
<strong>Important:</strong> 
<ul>
  <li>Point 1</li>
  <li>Point 2</li>
</ul>
<code>inline code</code>
<pre>code block</pre>
```

## Error Handling

### Project Not Found
```
list_projects(filter_name="NonExistent")
# Returns empty results
# Help user refine search or list all projects
```

### Invalid Project ID
```
get_threats(project_id="invalid")
# Returns error message
# Suggest using list_projects() to find correct ID
```

### Authentication Issues
```
# If credentials are invalid or missing
# Tool returns authentication error
# User needs to check their MCP client configuration
```

## Best Practices

1. **Start with project discovery** - Use `list_projects()` to help users find the right project
2. **Cache project IDs in conversation** - Remember the project UUID within the conversation
3. **Present data clearly** - Parse JSON and format for human readability
4. **Explain impacts** - When updating statuses, explain why and what it means
5. **Be explicit** - Always include project_id even if it seems repetitive
6. **Handle errors gracefully** - If a tool fails, explain the issue and suggest solutions

## Comparison to Stdio Mode

| Aspect | HTTP Mode (This) | Stdio Mode (Local) |
|--------|------------------|-------------------|
| Project Context | Explicit project_id | From .iriusrisk/project.json |
| Data Storage | API calls | Local files |
| Status Updates | Immediate API | Tracked locally, synced later |
| OTM Import | JSON string | File path |
| Diagrams | Base64 returned | Saved to filesystem |
| Sync | Not available | Downloads to .iriusrisk/ |

## Getting Started

When a user first interacts with you in HTTP mode:

1. Explain that you're working in HTTP mode (stateless, direct API)
2. Ask them which project they want to work with
3. Use `list_projects()` to help them find it
4. Once project is selected, proceed with their request

**Example:**
```
User: "Help me review the security threats"

You: "I'm connected to your IriusRisk instance via HTTP. To review threats, I need to know which project to analyze. Would you like me to list your projects, or do you know the project name you want to work with?"

User: "Show me projects with 'banking' in the name"

You: list_projects(filter_name="banking")
     [Shows results, user selects one]
     
Then proceed with threat analysis...
```

## Critical OTM Validation Checklist

Before importing an OTM file, validate ALL references:

**Trust Zones (CRITICAL):**
- ☐ Called `get_trust_zones()` and received JSON response
- ☐ **Parsed JSON and extracted EXACT `id` field values (UUIDs)**
- ☐ **Used those UUIDs in OTM trustZones section `id` field**
- ☐ **Used those same UUIDs in component `parent: { trustZone: "uuid" }`**
- ☐ **Did NOT invent trust zone IDs like "internet" or "dmz"**
- ☐ **Did NOT use trust zone `name` field as the ID**

**Components:**
- ☐ Searched for each needed component type using `search_components()`
- ☐ **Extracted EXACT `referenceId` field from search results**
- ☐ **Used complete referenceId without abbreviation** (e.g., "CD-V2-AWS-ALB", not "ALB")
- ☐ Every component has a parent (trustZone or component)

**Dataflows (CRITICAL):**
- ☐ **Dataflows ONLY connect component IDs, NEVER trust zone IDs**
- ☐ All dataflow source IDs are component IDs defined in the OTM
- ☐ All dataflow destination IDs are component IDs defined in the OTM
- ☐ **No dataflows reference trust zone IDs** (common error that causes import failure)

**Common Trust Zone Mapping Errors:**

❌ **WRONG** - Inventing IDs:
```json
"trustZones": [
  {"id": "internet", "name": "Internet"}  // ❌ "internet" is not a valid UUID
]
```

❌ **WRONG** - Using name as ID:
```json
"parent": {"trustZone": "Internet"}  // ❌ Should be UUID, not name
```

❌ **WRONG** - Guessing UUIDs:
```json
"parent": {"trustZone": "00000000-0000-0000-0000-000000000000"}  // ❌ Must be actual UUID from get_trust_zones()
```

✅ **CORRECT** - Using exact UUID from get_trust_zones():
```json
"trustZones": [
  {"id": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c", "name": "Internet", "risk": {"trustRating": 1}}
],
"components": [
  {
    "id": "lb",
    "parent": {"trustZone": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"}  // ✅ Exact UUID
  }
]
```

## Summary

HTTP mode gives you direct, real-time access to IriusRisk without filesystem dependencies. Every operation requires explicit project IDs, and all changes happen immediately. Use project discovery tools to help users navigate their projects, and remember that data is fetched on-demand rather than cached locally.

**CRITICAL REMINDER**: Always call `get_trust_zones()` before creating OTMs and use the EXACT UUID values from the `id` field. This is the #1 cause of OTM import failures.

