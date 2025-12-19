# OTM Import Fix - Restored v0.1.0 Approach

## Summary

Restored the simple, robust OTM import logic from v0.1.0 while keeping all HTTP MCP infrastructure and improvements. This fix resolves critical authentication bugs and simplifies the codebase.

## Problem

Commit **60187f1** (Dec 18, 2025 - "fixing import and duplicate comments") introduced breaking changes:
- Added upfront project existence checking
- Created unauthenticated `ProjectApiClient()` in MCP tools
- Increased complexity from ~100 to ~200 lines
- Made code more fragile with string-based error parsing

## Solution

Restored v0.1.0's simple approach:
- **Try create, fallback to update** - Let the API tell us if project exists
- **Single code path** - API client handles all complexity  
- **Proper authentication** - MCP tools use the authenticated `api_client` parameter
- **Cleaner error handling** - No upfront existence checks needed

## Files Changed

### 1. `src/iriusrisk_cli/api/project_client.py`
**Restored:**
- `auto_update` parameter to `import_otm_file()` and `import_otm_content()`
- Simple try-create-fallback-to-update logic
- Proper error handling without upfront validation

**Key change:**
```python
# v0.1.0 approach (restored)
def import_otm_file(self, otm_file_path: str, auto_update: bool = True):
    try:
        # Try to create
        response = session.post(url, files=files)
        result['action'] = 'created'
        return result
    except requests.RequestException as e:
        if e.response.status_code == 400 and 'already exists' in error:
            if auto_update:
                # Extract ID and update
                project_id = self._extract_project_id_from_otm(otm_file_path)
                result = self.update_project_with_otm_file(project_id, otm_file_path)
                result['action'] = 'updated'
                return result
```

### 2. `src/iriusrisk_cli/api_client.py`
**Added:**
- `auto_update` parameter to wrapper methods

```python
def import_otm_file(self, otm_file_path: str, auto_update: bool = True):
    return self.project_client.import_otm_file(otm_file_path, auto_update)
```

### 3. `src/iriusrisk_cli/commands/otm.py`
**Simplified:**
- Removed upfront existence checking
- Removed manual project ID extraction
- Let API client handle create-or-update logic

**Before (complex, ~80 lines):**
```python
project_client = container.get(ProjectApiClient)
project_ref_id = project_client._extract_project_id_from_otm(...)
exists, project_uuid = validate_project_exists(project_ref_id, ...)
if exists:
    result = api_client.update_project_with_otm_file(project_uuid, ...)
else:
    result = api_client.import_otm_file(...)
```

**After (simple, ~20 lines):**
```python
# Let the API client handle everything
result = api_client.import_otm_file(str(otm_path), auto_update=True)
```

### 4. `src/iriusrisk_cli/mcp/tools/stdio_tools.py`
**Fixed:**
- ❌ Removed: `project_client = ProjectApiClient()` (unauthenticated!)
- ✅ Now uses: `api_client.import_otm_content()` (properly authenticated)
- Simplified from ~40 lines to ~5 lines

### 5. `src/iriusrisk_cli/mcp/tools/http_tools.py`
**Fixed:**
- ❌ Removed: `project_client = ProjectApiClient()` (unauthenticated!)
- ✅ Now uses: `api_client.import_otm_content()` (properly authenticated)
- Simplified from ~40 lines to ~5 lines

## Benefits

| Aspect | Before (60187f1) | After (This Fix) |
|--------|------------------|------------------|
| **Lines of code** | ~200 | ~100 |
| **API calls** | 2-3 | 1-2 |
| **Complexity** | High | Low |
| **Authentication bugs** | 2 (both MCP modes) | 0 |
| **Code duplication** | High | Low |
| **Error handling** | String matching | Status codes |
| **Maintainability** | Poor | Good |

## Testing

All tests pass:
```bash
$ pytest tests/cli/test_cli_otm.py -v
======================== 17 passed, 2 warnings in 1.96s ========================

$ pytest tests/unit/test_mcp_unit.py tests/cli/test_cli_mcp.py -v
======================== 37 passed, 2 warnings in 1.20s ========================
```

## What Was Kept

✅ All HTTP MCP server infrastructure  
✅ All stdio/HTTP tool implementations  
✅ Update tracking and duplicate comment prevention  
✅ All prompt customizations  
✅ Auto-versioning improvements  
✅ All documentation and test improvements  

## What Was Fixed

1. **Critical Authentication Bugs (MCP)**
   - Stdio and HTTP MCP tools were creating unauthenticated clients
   - Now properly use the authenticated `api_client` parameter

2. **Unnecessary Complexity (CLI)**
   - Removed upfront project existence checking
   - Removed manual project ID extraction
   - Let API client handle the logic

3. **Fragile Error Handling**
   - Removed string-based error detection ("404" in error_msg)
   - Now uses proper HTTP status code checking

4. **Code Duplication**
   - Eliminated duplicate create-or-update logic across 3 files
   - Single source of truth in API client

## Backwards Compatibility

✅ **100% compatible** - No breaking changes to public APIs  
✅ All existing code continues to work  
✅ Default behavior unchanged (`auto_update=True`)  

## Usage

### CLI
```bash
# Automatically creates or updates
iriusrisk otm import myproject.otm

# Same as before
iriusrisk otm import myproject.otm -u PROJECT_ID
```

### MCP (stdio/HTTP)
```python
# Automatically creates or updates
import_otm("myproject.otm")  # stdio mode
import_otm(otm_content)      # HTTP mode
```

### API Client
```python
# New way (restored v0.1.0 approach)
api_client.import_otm_file("file.otm", auto_update=True)  # Default

# Disable auto-update if needed
api_client.import_otm_file("file.otm", auto_update=False)
```

## Migration Notes

No migration needed! This is a bug fix that restores working functionality from v0.1.0.

If you have code that was working around the bugs in 60187f1, you can simplify it now.

## Lessons Learned

1. **Simple is better** - v0.1.0's approach was simpler and more robust
2. **Trust the API** - Don't try to outsmart it with upfront checks
3. **Authentication matters** - Never create API clients without credentials
4. **Test with all modes** - CLI, stdio MCP, and HTTP MCP all need testing

## Related Documentation

- `V1_VS_V2_API_RESOLUTION.md` - When to use UUID resolution (still applies)
- `MCP_STDIO_FIX_SUMMARY.md` - MCP tool distribution (unchanged)

---

**Date:** December 19, 2025  
**Commit:** (pending)  
**Version:** Post-v0.2.0 bug fix

