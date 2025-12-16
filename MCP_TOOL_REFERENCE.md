# MCP Tools Reference Guide

## Tool Availability Matrix

| Tool Name | Stdio Mode | HTTP Mode | Notes |
|-----------|-----------|-----------|-------|
| **Shared Tools** | | | |
| `get_cli_version` | ✅ | ✅ | Returns CLI version |
| `initialize_iriusrisk_workflow` | ✅ | ✅ | Must call first |
| `analyze_source_material` | ✅ | ✅ | Source analysis instructions |
| `create_threat_model` | ✅ | ✅ | Threat model creation guide |
| `threats_and_countermeasures` | ✅ | ✅ | T&C exploration guide |
| `architecture_and_design_review` | ✅ | ✅ | Architecture review guidance |
| `security_development_advisor` | ✅ | ✅ | Security guidance |
| **Data Sync** | | | |
| `sync` | ✅ | ❌ | Downloads to `.iriusrisk/` directory |
| **Component Library** | | | |
| `search_components` | ❌ * | ✅ (API) | Search component library |
| `get_component_categories` | ❌ * | ✅ (API) | List component categories |
| **Trust Zones** | | | |
| `get_trust_zones` | ❌ * | ✅ (API) | Get trust zone library |
| **OTM Import** | | | |
| `import_otm` | ✅ (file) | ✅ (string) | Import OTM threat model |
| **Threats** | | | |
| `search_threats` | ❌ * | ✅ (API) | Search project threats |
| **Countermeasures** | | | |
| `search_countermeasures` | ❌ * | ✅ (API) | Search project countermeasures |
| **Project Management** | | | |
| `list_projects` | ❌ | ✅ | List all projects |
| `search_projects` | ❌ | ✅ | Search projects by criteria |
| `get_project` | ❌ | ✅ | Get project details |
| `get_project_overview` | ❌ | ✅ | Get project statistics |
| **Organization** | | | |
| `org_risk_snapshot` | ❌ | ✅ | Organization-wide risk view |
| **Status Updates** | | | |
| `update_threat_status` | ❌ | ✅ | Update threat status |
| `update_countermeasure_status` | ❌ | ✅ | Update countermeasure status |
| **Reports & Diagrams** | | | |
| `generate_report` | ✅ (file) | ✅ (base64) | Generate reports |
| `show_diagram` / `get_diagram` | ✅ (file) | ✅ (base64) | Get diagram |
| **TOTAL** | **16** | **22** | |

**Note:** * = Tools intentionally not included in stdio mode because AI has direct filesystem access to `.iriusrisk/*.json` files. AI can read these files directly and perform more flexible analysis than pre-built search tools allow.

## Stdio Mode Tools (16)

### Prerequisites
Most stdio tools require running `sync()` first to download data to `.iriusrisk/` directory.

### Important Note on Search Tools
Search tools (`search_components`, `search_threats`, `search_countermeasures`, `get_trust_zones`, `get_component_categories`) are **intentionally NOT included** in stdio mode. 

**Why?** In stdio mode, AI assistants have direct filesystem access and can read `.iriusrisk/*.json` files directly. This provides **more flexibility and power** than pre-built search tools. The AI can:
- Perform arbitrary filtering and analysis
- Cross-reference multiple files
- Use sophisticated queries beyond what pre-built tools offer

For example, instead of calling `search_components(query="lambda", limit=20)`, the AI can:
```python
# Read file directly and do custom analysis
components = json.load(open('.iriusrisk/components.json'))
aws_lambda = [c for c in components 
              if 'aws' in c['category'].lower() 
              and 'lambda' in c['name'].lower()
              and len(c.get('threats', [])) > 5]  # Custom criteria!
```

### Workflow Tools (7)
1. **`get_cli_version()`** - Get CLI version
2. **`initialize_iriusrisk_workflow()`** - Get workflow instructions (call first!)
3. **`analyze_source_material()`** - Source analysis guide
4. **`create_threat_model()`** - Threat model creation guide
5. **`threats_and_countermeasures()`** - T&C exploration guide
6. **`architecture_and_design_review()`** - Architecture review guide
7. **`security_development_advisor()`** - Security guidance

### Data Access Tools (7)
8. **`sync(project_path=None)`** - Download IriusRisk data to local directory
   - Downloads: components, trust zones, threats, countermeasures
   - Creates `.iriusrisk/` directory with JSON files
   - Required before AI can read local JSON files

9. **`import_otm(otm_file_path, project_id=None)`** - Import OTM file
   - Takes local file path (relative or absolute)
   - Validates JSON/YAML format
   - Creates new project or updates existing

10. **`list_projects(page=0, size=10)`** - List projects
    - API call (works same as HTTP mode)
    - Paginated results

11. **`search_projects(query, filter_tags=None, filter_workflow_state=None, page=0, size=20)`** - Search projects
    - API call (works same as HTTP mode)
    - Search by name, tags, workflow state

12. **`get_project(project_id)`** - Get project details
    - API call (works same as HTTP mode)
    - Returns full project metadata

13. **`update_threat_status(project_id, threat_id, status, reason, comment=None)`** - Update threat
    - API call + local tracking in `.iriusrisk/pending_updates.json`
    - Tracks changes for audit/sync purposes

14. **`update_countermeasure_status(project_id, countermeasure_id, status, reason, comment=None)`** - Update countermeasure
    - API call + local tracking in `.iriusrisk/pending_updates.json`
    - Tracks changes for audit/sync purposes

## HTTP Mode Tools (22)

### Workflow Tools (7)
Same 7 shared tools as stdio mode.

### Stateless Data Access Tools (15)

1. **`list_projects(page=0, size=10)`** - List projects
   - Paginated project list
   - No filtering

2. **`search_projects(query, filter_tags=None, filter_workflow_state=None, page=0, size=20)`** - Search projects
   - Search by name, tags, workflow state
   - Paginated results

3. **`get_project(project_id)`** - Get project details
   - Full project metadata
   - Includes URL link

4. **`get_project_overview(project_id)`** - Get project overview
   - Statistics and risk summary
   - Threat/countermeasure breakdowns
   - Key insights

5. **`org_risk_snapshot()`** - Organization risk snapshot
   - Portfolio-level view
   - High-risk projects
   - Critical findings

6. **`search_components(query, category=None, limit=20)`** - Search components
   - API call with session caching
   - First call downloads ~1.6MB component library
   - Subsequent calls use cache

7. **`get_component_categories()`** - Get component categories
   - API call with session caching
   - Returns unique categories

8. **`get_trust_zones()`** - Get trust zones
   - API call (~15KB)
   - Complete trust zone library

9. **`import_otm(otm_content, project_id=None)`** - Import OTM
   - Takes OTM content as string (not file path)
   - Validates and imports

10. **`search_threats(project_id, query=None, risk_level=None, status=None, limit=20)`** - Search threats
    - API call with session caching per project
    - Filter and fuzzy search

11. **`search_countermeasures(project_id, query=None, status=None, priority=None, limit=20)`** - Search countermeasures
    - API call with session caching per project
    - Filter and fuzzy search

12. **`update_threat_status(project_id, threat_id, status, reason, comment=None)`** - Update threat
    - Direct API update
    - No local tracking

13. **`update_countermeasure_status(project_id, countermeasure_id, status, reason, comment=None)`** - Update countermeasure
    - Direct API update
    - No local tracking

14. **`generate_report(project_id, report_type="countermeasure", format="pdf", standard=None)`** - Generate report
    - Returns base64 encoded report
    - Supports: countermeasure, threat, compliance, risk-summary

15. **`get_diagram(project_id, size="PREVIEW")`** - Get diagram
    - Returns base64 encoded PNG
    - Sizes: ORIGINAL, PREVIEW, THUMBNAIL

## Key Differences

### Stdio Mode
- **Requires**: Running `sync()` first to download data
- **Storage**: Local `.iriusrisk/` directory
- **Performance**: Fast (local file access)
- **Network**: Only needed for `sync()` and `import_otm()`
- **Caching**: Files persist until next `sync()`
- **Use case**: Local development, Cursor, Claude Desktop

### HTTP Mode
- **Requires**: API credentials per request
- **Storage**: Session-based memory cache
- **Performance**: Moderate (API calls, then cached)
- **Network**: Required for all operations
- **Caching**: Per-session, cleared when session ends
- **Use case**: Remote access, stateless environments, web services

## Common Workflows

### Stdio Mode: Create Threat Model
```
1. initialize_iriusrisk_workflow()     # Get instructions
2. sync(project_path="/path/to/repo") # Download data
3. search_components(query="lambda")   # Find components
4. get_trust_zones()                   # Get trust zones
5. create_threat_model()               # Get creation guide
   # Create OTM file based on guidance
6. import_otm(otm_file_path="threat-model.otm")
7. sync()                              # Sync threats/countermeasures
8. search_threats(risk_level="critical")
9. search_countermeasures(status="required")
```

### HTTP Mode: Create Threat Model
```
1. initialize_iriusrisk_workflow()                    # Get instructions
2. search_components(query="lambda")                  # Find components (cached)
3. get_trust_zones()                                  # Get trust zones
4. create_threat_model()                              # Get creation guide
   # Create OTM content string based on guidance
5. import_otm(otm_content=otm_string)                # Import
6. search_threats(project_id=pid, risk_level="critical")
7. search_countermeasures(project_id=pid, status="required")
8. update_threat_status(pid, tid, "mitigate", "...")  # Update status
```

### Stdio Mode: Review Existing Project
```
1. sync(project_path="/path/to/repo")                # Get latest data
2. search_threats(risk_level="critical")              # Critical threats
3. search_threats(status="expose", risk_level="high") # Exposed high risks
4. search_countermeasures(status="required")          # Required CMs
5. search_countermeasures(priority="very-high")       # High priority CMs
```

### HTTP Mode: Organization Dashboard
```
1. org_risk_snapshot()                   # Overall risk view
2. search_projects(query="production")   # Find prod projects
3. get_project_overview(project_id=pid)  # Project details
4. search_threats(pid, status="expose", risk_level="critical")
5. generate_report(pid, "risk-summary", "pdf")
```


