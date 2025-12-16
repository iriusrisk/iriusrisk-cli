# MCP Tool Distribution Analysis

## Current State

### Shared Tools (Available in Both Modes) - 7 tools
1. `get_cli_version` - Returns CLI version
2. `initialize_iriusrisk_workflow` - Workflow instructions
3. `analyze_source_material` - Source analysis instructions
4. `create_threat_model` - Threat model creation instructions
5. `threats_and_countermeasures` - T&C instructions
6. `architecture_and_design_review` - Architecture review guidance
7. `security_development_advisor` - Security guidance

### Stdio-Only Tools (Require Filesystem) - 1 tool
1. `sync` - Syncs data to `.iriusrisk/` directory

### HTTP-Only Tools (Stateless) - 15 tools
1. `get_project_overview` - Project stats and summary
2. `org_risk_snapshot` - Organization-wide risk view
3. `generate_report` - Generate reports (returns base64)
4. `list_projects` - List all projects
5. `search_projects` - Search projects by criteria
6. `search_components` - Search component library
7. `get_trust_zones` - Get trust zone library
8. `get_component_categories` - Get component categories
9. `get_project` - Get project details
10. `search_threats` - Search project threats
11. `search_countermeasures` - Search project countermeasures
12. `import_otm` - Import OTM (takes content string)
13. `update_threat_status` - Update threat status
14. `update_countermeasure_status` - Update countermeasure status
15. `get_diagram` - Get project diagram (returns base64)

**Total in Stdio Mode: 8 tools (BEFORE FIX)**
**Total in HTTP Mode: 22 tools**

## Fixed State (After Implementation)

### Shared Tools (Available in Both Modes) - 7 tools
1. `get_cli_version` - Returns CLI version
2. `initialize_iriusrisk_workflow` - Workflow instructions
3. `analyze_source_material` - Source analysis instructions
4. `create_threat_model` - Threat model creation instructions
5. `threats_and_countermeasures` - T&C instructions
6. `architecture_and_design_review` - Architecture review guidance
7. `security_development_advisor` - Security guidance

### Stdio-Only Tools (Require Filesystem) - 7 tools
1. `sync` - Syncs data to `.iriusrisk/` directory
2. `import_otm` - Import OTM from file path ✅ **ADDED**
3. `search_components` - Search from local components.json ✅ **ADDED**
4. `get_trust_zones` - Get from local trust-zones.json ✅ **ADDED**
5. `search_threats` - Search from local threats.json ✅ **ADDED**
6. `search_countermeasures` - Search from local countermeasures.json ✅ **ADDED**
7. `get_component_categories` - Extract from local components.json ✅ **ADDED**

### HTTP-Only Tools (Stateless) - 15 tools
1. `get_project_overview` - Project stats and summary
2. `org_risk_snapshot` - Organization-wide risk view
3. `generate_report` - Generate reports (returns base64)
4. `list_projects` - List all projects
5. `search_projects` - Search projects by criteria
6. `search_components` - Search via API with caching
7. `get_trust_zones` - Get via API
8. `get_component_categories` - Get via API
9. `get_project` - Get project details
10. `search_threats` - Search via API with caching
11. `search_countermeasures` - Search via API with caching
12. `import_otm` - Import OTM from content string
13. `update_threat_status` - Update threat status
14. `update_countermeasure_status` - Update countermeasure status
15. `get_diagram` - Get project diagram (returns base64)

**Total in Stdio Mode: 14 tools (7 shared + 7 stdio-specific)** ✅
**Total in HTTP Mode: 22 tools (7 shared + 15 HTTP-specific)**

## Problem Analysis

### Missing from Stdio Mode
Many tools that should work in stdio mode are only available in HTTP mode:

1. **`import_otm`** - CRITICAL MISSING
   - Should accept file path in stdio mode (not content string)
   - User explicitly mentioned this is missing

2. **`search_components`** - Should be available
   - In stdio mode: reads from `.iriusrisk/components.json`
   - In HTTP mode: API calls with caching

3. **`get_trust_zones`** - Should be available
   - In stdio mode: reads from `.iriusrisk/trust-zones.json`
   - In HTTP mode: API calls

4. **`search_threats`** - Should be available
   - In stdio mode: reads from `.iriusrisk/threats.json`
   - In HTTP mode: API calls with caching

5. **`search_countermeasures`** - Should be available
   - In stdio mode: reads from `.iriusrisk/countermeasures.json`
   - In HTTP mode: API calls with caching

6. **`list_projects`** - Could be available
   - In stdio mode: API call (no filesystem dependency)
   - In HTTP mode: API call

7. **`search_projects`** - Could be available
   - In stdio mode: API call (no filesystem dependency)
   - In HTTP mode: API call

8. **`get_project`** - Could be available
   - In stdio mode: Could read from `.iriusrisk/project.json` OR API call
   - In HTTP mode: API call

9. **`update_threat_status`** - Should be available
   - In stdio mode: Updates API AND local `.iriusrisk/pending_updates.json`
   - In HTTP mode: Direct API update only

10. **`update_countermeasure_status`** - Should be available
    - In stdio mode: Updates API AND local `.iriusrisk/pending_updates.json`
    - In HTTP mode: Direct API update only

11. **`generate_report`** - Could be available
    - In stdio mode: Generate report, save to file, return path
    - In HTTP mode: Generate report, return base64

12. **`get_diagram`** - Could be available
    - In stdio mode: Get diagram, save to file, return path
    - In HTTP mode: Get diagram, return base64

13. **`get_project_overview`** - Could be available (less critical)
    - Same implementation in both modes

14. **`org_risk_snapshot`** - Could be available (less critical)
    - Same implementation in both modes

15. **`get_component_categories`** - Should be available
    - In stdio mode: Extract from `.iriusrisk/components.json`
    - In HTTP mode: API call

## Recommended Fix

### Priority 1 (Critical - User Explicitly Needs These)
1. **`import_otm`** - Add to stdio mode with file path parameter

### Priority 2 (High - Core Workflow Tools)
2. **`search_components`** - Add stdio version reading from local JSON
3. **`get_trust_zones`** - Add stdio version reading from local JSON
4. **`search_threats`** - Add stdio version reading from local JSON
5. **`search_countermeasures`** - Add stdio version reading from local JSON
6. **`get_component_categories`** - Add stdio version reading from local JSON

### Priority 3 (Medium - Status Update Tools)
7. **`update_threat_status`** - Add stdio version with local tracking
8. **`update_countermeasure_status`** - Add stdio version with local tracking

### Priority 4 (Nice to Have - API-Only Tools)
9. **`list_projects`** - Can share HTTP implementation
10. **`search_projects`** - Can share HTTP implementation
11. **`get_project`** - Add stdio version reading from local JSON
12. **`generate_report`** - Add stdio version saving to file
13. **`get_diagram`** - Add stdio version saving to file
14. **`get_project_overview`** - Can share HTTP implementation
15. **`org_risk_snapshot`** - Can share HTTP implementation

## Implementation Strategy

### Phase 1: Fix Critical Issue
- Add `import_otm` to stdio_tools.py with file path parameter

### Phase 2: Add Core Data Access Tools
- Add filesystem-based versions of search tools in stdio_tools.py
- These read from `.iriusrisk/*.json` files created by `sync`

### Phase 3: Add Status Update Tools
- Add stdio versions that track updates locally in `pending_updates.json`

### Phase 4: Share API-Only Tools
- Move pure API tools that don't need filesystem to shared_tools.py
- These work identically in both modes


