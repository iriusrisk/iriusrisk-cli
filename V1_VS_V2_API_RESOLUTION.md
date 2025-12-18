# V1 vs V2 API: When to Use UUID Resolution

## TL;DR - Quick Reference

**DO NOT** use `resolve_project_id_to_uuid_strict()` for:
- ❌ V1 OTM API endpoints (`/products/otm/...`)
- ❌ OTM import operations (`import_otm`, `update_project_with_otm_*`)

**DO** use `resolve_project_id_to_uuid_strict()` for:
- ✅ V2 API endpoints (`/v2/projects/{uuid}/...`)
- ✅ Threat operations (`get_threats`, `update_threat_state`)
- ✅ Countermeasure operations (`get_countermeasures`, `update_countermeasure_state`)
- ✅ Project details (`get_project`)
- ✅ Reports and diagrams

---

## The Problem

This codebase has a **recurring issue** where UUID resolution gets added to V1 OTM operations, breaks functionality, gets removed, then someone adds it back thinking it's missing. This document explains why this happens and how to avoid it.

## Background: Two Different APIs

IriusRisk has two API versions that handle project identification differently:

### V1 API (Legacy)
- Endpoints: `/api/v1/products/...`
- Example: `PUT /api/v1/products/otm/{project_id}`
- **Accepts BOTH UUIDs AND Reference IDs in the URL path**
- Examples:
  - UUID: `PUT /products/otm/550e8400-e29b-41d4-a716-446655440000` ✅ Works
  - Ref ID: `PUT /products/otm/my-project-ref` ✅ Works

### V2 API (Current)
- Endpoints: `/api/v2/...`
- Example: `GET /api/v2/projects/{uuid}/threats`
- **Only accepts UUIDs in the URL path**
- Examples:
  - UUID: `GET /v2/projects/550e8400-e29b-41d4-a716-446655440000/threats` ✅ Works
  - Ref ID: `GET /v2/projects/my-project-ref/threats` ❌ Fails (404 Not Found)

## The UUID Resolution Function

`resolve_project_id_to_uuid_strict()` from `utils/project_resolution.py`:
- Takes a project identifier (UUID or reference ID)
- If it's already a UUID, returns it as-is
- If it's a reference ID, **makes an API call** to look up the project and get its UUID
- Throws an exception if the project doesn't exist

## When UUID Resolution Is Required

Use `resolve_project_id_to_uuid_strict()` when calling **V2 API endpoints**:

```python
# ✅ CORRECT: V2 endpoint needs UUID
from ...utils.project_resolution import resolve_project_id_to_uuid_strict

project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)
threats = api_client.get_threats(project_uuid)  # V2: /v2/projects/{uuid}/threats
```

### Examples in the codebase:
- `mcp/tools/stdio_tools.py` line 510: `update_threat_status()` - needs UUID for V2 threat API
- `mcp/tools/stdio_tools.py` line 599: `update_countermeasure_status()` - needs UUID for V2 countermeasure API
- `mcp/tools/stdio_tools.py` line 439: `get_project()` - needs UUID for V2 project API
- `mcp/tools/stdio_tools.py` line 680: `generate_report()` - needs UUID for V2 report API
- `mcp/tools/stdio_tools.py` line 804: `get_diagram()` - needs UUID for V2 artifacts API

## When UUID Resolution Breaks Things

**DO NOT** use `resolve_project_id_to_uuid_strict()` when calling **V1 OTM endpoints**:

```python
# ❌ WRONG: Adds unnecessary lookup that can fail
from ...utils.project_resolution import resolve_project_id_to_uuid_strict

project_uuid = resolve_project_id_to_uuid_strict(project_id, api_client)  # ❌ Lookup fails!
result = api_client.update_project_with_otm_content(project_uuid, otm_content)

# ✅ CORRECT: V1 endpoint accepts reference IDs directly
result = api_client.update_project_with_otm_content(project_id, otm_content)
```

### Why this breaks:

1. **Unnecessary API call**: The V1 API already handles reference IDs, so the lookup is wasted work
2. **Fails when it shouldn't**: Resolution tries to find the project, but the project might not exist yet or might only be known by reference ID
3. **Confusing error messages**: User gets "Project not found" when the actual API call would have worked
4. **Inconsistent with CLI**: The CLI commands work fine without resolution, but MCP fails

### Example failure scenario:

```
User calls: import_otm("file.otm", project_id="badger-app-poug")

With resolution (WRONG):
1. resolve_project_id_to_uuid_strict("badger-app-poug", api_client)
2. Makes API call: GET /projects?filter='referenceId'='badger-app-poug'
3. No projects found (maybe project doesn't exist yet)
4. ❌ Exception: "Project with reference ID 'badger-app-poug' not found"
5. User confused: "But I just want to update the project!"

Without resolution (CORRECT):
1. Pass "badger-app-poug" directly to API
2. Makes API call: PUT /products/otm/badger-app-poug
3. ✅ V1 API handles the reference ID internally
4. Update succeeds!
```

## Code Locations to Preserve

These locations **correctly** do NOT use resolution (DO NOT "fix" them):

### MCP Tools - stdio_tools.py
- Line 260: `import_otm()` tool - V1 OTM API
  - **DO NOT** add `resolve_project_id_to_uuid_strict()` before line 261
  - See comprehensive comments at lines 237-271

### MCP Tools - http_tools.py  
- Line 967: `import_otm()` tool - V1 OTM API
  - **DO NOT** add `resolve_project_id_to_uuid_strict()` before line 968
  - See comprehensive comments at lines 944-977

### CLI Commands - otm.py
- Line 125: `import_cmd()` - V1 OTM API
  - **DO NOT** add resolution before calling `update_project_with_otm_file()`
  - See comment at lines 123-124

### API Client - project_client.py
These methods document that they accept both formats:
- Line 387: `update_project_with_otm_file()` - See docstring
- Line 444: `update_project_with_otm_content()` - See docstring

## How to Avoid Breaking This Again

### If you're adding a new operation:

1. **Check which API version it uses**:
   - Look at the endpoint URL in the API client method
   - V1: `/api/v1/products/...` → No resolution needed
   - V2: `/api/v2/projects/{uuid}/...` → Resolution needed

2. **Follow existing patterns**:
   - Look at similar operations in the codebase
   - If similar operations don't use resolution, neither should yours

3. **Read the docstrings**:
   - API client methods document whether they need UUIDs or accept reference IDs

### If you think you found missing resolution:

1. **Stop and check**:
   - Is this a V1 or V2 endpoint?
   - Do similar operations use resolution?
   - Are there comments explaining why it's not there?

2. **Test with reference IDs**:
   - Try calling the operation with a reference ID (e.g., "my-project-ref")
   - If it works, resolution isn't needed!

3. **Check the CLI**:
   - Does the CLI command use resolution?
   - If the CLI works without it, MCP should too

### Red flags that you're about to break it:

- You're adding resolution to `import_otm()` or OTM update operations
- You're "fixing" code that has detailed comments explaining why resolution isn't used
- Tests start failing with "Project not found" errors after your change
- The CLI command does the same thing without resolution

## Testing

When working with project IDs, test with BOTH formats:

```python
# Test with UUID
import_otm("file.otm", project_id="550e8400-e29b-41d4-a716-446655440000")  # Should work

# Test with reference ID  
import_otm("file.otm", project_id="my-project-ref")  # Should work

# Test without project_id (create new)
import_otm("file.otm")  # Should work
```

If the reference ID test fails but the UUID test works, you've probably added resolution where it doesn't belong.

## Summary

- **V1 OTM API**: Accepts both UUIDs and reference IDs → **NO resolution needed**
- **V2 API**: Only accepts UUIDs → **Resolution required**
- This is a **known recurring issue** - don't "fix" what isn't broken
- When in doubt, check if the CLI command uses resolution
- Read the comments in the code - they're there for a reason!

---

*If you're reading this because you just broke OTM import by adding resolution: Remove the `resolve_project_id_to_uuid_strict()` call and the operation will work again. We've all been there. 🙂*
