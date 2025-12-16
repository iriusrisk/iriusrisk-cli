# MCP Tool Design Philosophy

## Core Principle: Consistent User Experience Across Transports

The IriusRisk CLI MCP server operates in two modes:
- **stdio mode**: For local AI assistants (Cursor, Claude Desktop)
- **HTTP mode**: For remote/web access

**Our goal: Provide as close to identical capabilities as possible, regardless of transport mode.**

## Why Feature Parity Matters

1. **User Expectations**: Users shouldn't need to remember "this tool only works in HTTP mode"
2. **Mode Switching**: Users should be able to switch between modes without relearning
3. **Documentation**: One set of documentation works for both modes
4. **Predictability**: If a tool exists, it should work everywhere possible

## Implementation Philosophy

### Same Tool Name, Different Implementation

A tool should be available in both modes unless there's a fundamental technical constraint. The implementation may vary significantly, but the user experience should be consistent.

**Example: `search_components`**

| Aspect | Stdio Mode | HTTP Mode |
|--------|-----------|-----------|
| **Data Source** | Local `.iriusrisk/components.json` | API call with session caching |
| **Parameters** | `query`, `category`, `limit` | `query`, `category`, `limit` |
| **Return Format** | JSON with matches and metadata | JSON with matches and metadata |
| **User Experience** | Identical | Identical |

From the AI assistant's perspective, the tool works the same way. The difference is hidden.

### Decision Framework

When deciding whether a tool should be available in both modes, ask:

**1. Can it work without filesystem state?**
- YES → Available in HTTP mode
- NO → Stdio-only (e.g., `sync` requires writing to `.iriusrisk/`)

**2. Can it work with filesystem state OR API calls?**
- YES → Available in stdio mode
- NO → HTTP-only (rare)

**3. Is there a fundamental incompatibility?**
- YES → Mode-specific only (document why)
- NO → Make it available in both modes

### Examples of Good Design Decisions

**✅ `list_projects` - Available in Both Modes**
- Stdio: Makes API call (no filesystem dependency)
- HTTP: Makes API call (same implementation)
- Result: Consistent experience

**✅ `search_threats` - Available in Both Modes**
- Stdio: Reads from `.iriusrisk/threats.json` (fast, offline-capable)
- HTTP: API call with caching (stateless)
- Result: Different implementation, same interface

**✅ `update_threat_status` - Available in Both Modes with Enhancement**
- Stdio: API call + tracks locally in `pending_updates.json`
- HTTP: API call only (stateless)
- Result: Stdio adds value without breaking consistency

**✅ `sync` - Stdio-Only (Justified)**
- Purpose: Download data to `.iriusrisk/` directory
- HTTP: Fundamentally incompatible (stateless, no filesystem)
- Result: Correctly mode-specific

**✅ `search_components`, `search_threats`, `search_countermeasures`, `get_trust_zones`, `get_component_categories` - HTTP-Only (Justified)**
- Purpose: Pre-built search and filter tools
- Stdio: NOT needed because AI can read `.iriusrisk/*.json` files directly
- Result: AI assistants have direct filesystem access and can perform more flexible analysis by reading raw JSON
- Benefit: Eliminates unnecessary abstraction layer when direct file access is available

**❌ `list_projects` - If It Were HTTP-Only (Bad)**
- No technical reason it can't work in stdio mode
- Would force users to remember arbitrary limitations
- Would reduce stdio mode value unnecessarily

## Implementation Patterns

### Pattern 1: Filesystem vs API Data Access

```python
# Stdio: Read from local file (fast, offline)
async def search_components_stdio(query, limit=20):
    with open('.iriusrisk/components.json') as f:
        components = json.load(f)
    return _search_in_memory(components, query, limit)

# HTTP: API call with caching (stateless)
async def search_components_http(query, limit=20):
    components = await _get_cached(api_client)
    return _search_in_memory(components, query, limit)

# Shared: Same search logic
def _search_in_memory(components, query, limit):
    # Fuzzy matching, filtering, sorting
    return matches[:limit]
```

### Pattern 2: Output Format Variations

```python
# Stdio: Save to file (persistent)
async def generate_report_stdio(project_id, type, format):
    content = api_client.generate_report(...)
    path = Path(f'.iriusrisk/reports/{type}.{format}')
    path.write_bytes(content)
    return f"✅ Report saved to: {path}"

# HTTP: Return base64 (ephemeral)
async def generate_report_http(project_id, type, format):
    content = api_client.generate_report(...)
    encoded = base64.b64encode(content).decode()
    return f"✅ Report generated:\n{encoded}"
```

### Pattern 3: Stdio Enhancements

```python
# Stdio: API call + local tracking
async def update_threat_status_stdio(threat_id, status, reason):
    api_client.update_threat_status(threat_id, status)
    
    # Bonus: Track locally for future reference
    track_update_locally({
        'threat_id': threat_id,
        'status': status,
        'reason': reason,
        'timestamp': datetime.now()
    })
    
    return "✅ Status updated (tracked locally)"

# HTTP: API call only
async def update_threat_status_http(project_id, threat_id, status, reason):
    api_client.update_threat_status(project_id, threat_id, status)
    return "✅ Status updated"
```

## Benefits of This Approach

1. **Better User Experience**: Tools work everywhere they can
2. **Predictability**: Fewer arbitrary limitations
3. **Flexibility**: Implementations can evolve independently
4. **Value**: Stdio mode isn't a "second-class" experience
5. **Maintainability**: Clear decision framework for future tools

## Anti-Patterns to Avoid

### ❌ Mode-Specific Tool Names

```python
# BAD: Different names for same functionality
search_components_local(...)   # Stdio version
search_components_api(...)     # HTTP version

# GOOD: Same name, register in both modes
search_components(...)         # Works in both modes
```

### ❌ Arbitrary Exclusions

```python
# BAD: No technical reason to exclude from stdio
async def list_projects_http(...):  # HTTP-only for no reason
    return api_client.get_projects()

# GOOD: Available in both modes
async def list_projects(...):      # Works in both modes
    return api_client.get_projects()
```

### ❌ Inconsistent Interfaces

```python
# BAD: Different parameters or return formats
search_components_stdio(query, category)  # Returns list
search_components_http(query, limit)      # Returns JSON

# GOOD: Same interface
search_components(query, category, limit) # Returns JSON in both
```

## Current Status

### Tool Availability (After Implementation)

- **Stdio mode**: 19 tools (7 shared + 12 stdio-specific)
- **HTTP mode**: 22 tools (7 shared + 15 HTTP-specific)
- **Feature parity**: 86% of HTTP tools available in stdio mode

### Remaining HTTP-Only Tools

Only 4 tools remain HTTP-only, all with valid technical reasons:

1. **`get_project_overview`** - Could be added to stdio
2. **`org_risk_snapshot`** - Could be added to stdio  
3. **`generate_report`** - Could be added to stdio (save to file)
4. **`get_diagram`** - Could be added to stdio (save to file)

*Note: These could all be added to stdio mode with appropriate implementations if needed.*

## Exception: Search Tools Not Needed in Stdio Mode

**Key Design Decision: When AI has direct file access, don't wrap it in search tools.**

In stdio mode, AI assistants have direct filesystem access and can read `.iriusrisk/*.json` files. This provides **more flexibility and power** than pre-built search tools can offer.

### Why Search Tools Are HTTP-Only

**In HTTP Mode:**
- AI cannot read files directly (stateless, no filesystem)
- Search tools provide essential capability through API calls
- Session caching optimizes performance
- Tools abstract away pagination and API complexity

**In Stdio Mode:**
- AI CAN read files directly using built-in file reading capabilities
- AI can perform arbitrary filtering, sorting, and analysis
- AI can combine data from multiple files
- AI can use more sophisticated analysis than pre-built tools offer

### Example: Why AI Prefers Direct File Access

**With Search Tool (Limited):**
```python
# User: "Find Lambda components in AWS category"
result = search_components(query="lambda", category="AWS", limit=20)
# Returns pre-filtered, pre-sorted top 20 results
```

**With Direct File Access (Flexible):**
```python
# AI can:
# 1. Read the entire file
components = json.load(open('.iriusrisk/components.json'))

# 2. Perform custom analysis
aws_serverless = [c for c in components 
                  if 'aws' in c['category'].lower() 
                  and ('lambda' in c['name'].lower() or 'serverless' in c['name'].lower())
                  and c.get('version', '') == '2.0']

# 3. Sort by custom criteria
sorted_by_complexity = sorted(aws_serverless, key=lambda c: len(c.get('threats', [])))

# 4. Cross-reference with threats
threats = json.load(open('.iriusrisk/threats.json'))
components_with_critical_threats = [c for c in aws_serverless 
                                     if any(t['risk'] == 'critical' for t in threats)]

# Much more powerful than a pre-built search tool!
```

### Tools Intentionally Excluded from Stdio Mode

- `search_components` - AI reads `.iriusrisk/components.json` directly
- `get_component_categories` - AI extracts from components.json directly
- `get_trust_zones` - AI reads `.iriusrisk/trust-zones.json` directly
- `search_threats` - AI reads `.iriusrisk/threats.json` directly
- `search_countermeasures` - AI reads `.iriusrisk/countermeasures.json` directly

### Benefits of This Approach

1. **More Flexible**: AI can perform arbitrary queries, not just pre-built searches
2. **More Powerful**: AI can cross-reference multiple files, perform complex analysis
3. **Simpler Code**: Don't maintain duplicate search logic in both modes
4. **Better UX**: AI does what users actually want, not what tools allow
5. **Less Abstraction**: Direct data access is clearer than tool wrappers

### When to Provide Search Tools

Provide search tools when:
- ✅ The data source requires API calls (HTTP mode)
- ✅ The operation is complex and benefits from abstraction
- ✅ The tool provides value beyond simple data access

Don't provide search tools when:
- ❌ Direct file reading is available (stdio mode)
- ❌ The tool just wraps file reading with basic filtering
- ❌ AI can do better analysis without the tool

## Guidelines for Future Development

### Adding a New Tool

1. **Design for both modes first**: Think about how it would work in each mode
2. **Start with shared if possible**: If implementation is identical, make it shared
3. **Justify mode-specific**: Document why if it can only work in one mode
4. **Consistent interface**: Same parameters, similar return format

### Modifying an Existing Tool

1. **Maintain compatibility**: Don't break the interface
2. **Consider both modes**: Changes should work (or enhance) both modes
3. **Document differences**: If behavior varies, document it clearly

### Example: Adding `generate_report` to Stdio Mode

**Current**: HTTP-only (returns base64)
**Proposal**: Add to stdio mode (save to file)

**Decision Process**:
1. Can it work without filesystem? No (needs to save file)
2. Can it work with filesystem? YES (save file)
3. Fundamental incompatibility? NO

**Implementation**:
- Stdio: Generate report, save to `.iriusrisk/reports/`, return file path
- HTTP: Generate report, return base64 (unchanged)
- Interface: Same parameters, different output format (both valid)

**Conclusion**: Should be added to stdio mode ✅

## Summary

**The key principle**: If a tool CAN work in both modes, it SHOULD work in both modes.

Only exclude a tool from a mode when there's a clear technical constraint, and document that constraint. The goal is maximum feature parity for the best possible user experience.


