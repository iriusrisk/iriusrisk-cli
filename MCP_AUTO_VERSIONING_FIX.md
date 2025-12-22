# MCP Auto-Versioning Fix

## Issue Summary

Auto-versioning was not working when updating existing projects via the MCP `import_otm` tool in stdio mode. The `auto_versioning` configuration parameter in `.iriusrisk/project.json` was being ignored during MCP-based OTM imports.

## Root Cause

The auto-versioning feature was implemented in the CLI command path (`src/iriusrisk_cli/commands/otm.py`) but was **never implemented in the MCP tool path** (`src/iriusrisk_cli/mcp/tools/stdio_tools.py`).

Both code paths ultimately call the same `api_client.import_otm_content()` method, but only the CLI command wrapped it with version creation logic. This created an inconsistency where:

- **Direct CLI**: `iriusrisk otm import` → ✅ Auto-versioning worked
- **MCP STDIO**: AI calls `import_otm` MCP tool → ❌ Auto-versioning did not work
- **MCP HTTP**: AI calls `import_otm` MCP tool → ❌ Auto-versioning not applicable (no local project.json)

## Solution Implemented

### STDIO Mode

Added auto-versioning logic to the `import_otm` tool in `src/iriusrisk_cli/mcp/tools/stdio_tools.py` (after line 250):

```python
# Check for auto-versioning configuration and create version if enabled
version_status = None
if result.get('action') == 'updated':
    try:
        # Read project config to check auto_versioning setting
        from ...config import Config
        
        config = Config()
        project_config = config.get_project_config()
        auto_versioning_enabled = project_config and project_config.get('auto_versioning', False)
        
        if auto_versioning_enabled:
            logger.info("Auto-versioning is enabled, creating version after successful update")
            
            from ...container import get_container
            from ...services.version_service import VersionService
            from datetime import datetime
            
            container = get_container()
            version_service = container.get(VersionService)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            version_name = f"After OTM import {timestamp}"
            
            # Get UUID from result (added by project_client during auto-update)
            project_uuid = result.get('uuid')
            if not project_uuid:
                logger.warning("Project UUID not available for version creation")
                version_status = "⚠️  Auto-versioning: Could not create backup (UUID not available)"
            else:
                version_service.create_version(
                    project_id=project_uuid,
                    name=version_name,
                    description="Auto-versioning backup created by MCP after OTM import",
                    wait=False,
                    timeout=300
                )
                logger.info("Auto-versioning: Backup version created successfully")
                version_status = "✅ Auto-versioning: Backup version created successfully"
    except Exception as e:
        # Don't fail the import if versioning fails
        logger.warning(f"Auto-versioning failed to create version after import: {e}")
        version_status = f"⚠️  Auto-versioning: Could not create backup - {str(e)}"
```

The version status is then included in the tool's output to inform the AI assistant whether auto-versioning succeeded.

### HTTP Mode

HTTP mode does **not** support auto-versioning because:
- HTTP mode is designed for remote AI assistant access
- There's no local filesystem access to read `.iriusrisk/project.json`
- Each HTTP request is independent with no persistent project context

Added a documentation comment in `src/iriusrisk_cli/mcp/tools/http_tools.py` to clarify this design decision.

## Files Modified

1. **`src/iriusrisk_cli/mcp/tools/stdio_tools.py`**
   - Added auto-versioning logic to `import_otm` tool (lines ~252-291)
   - Reads `auto_versioning` setting from `.iriusrisk/project.json`
   - Creates version after successful project update
   - Includes version status in output message

2. **`src/iriusrisk_cli/mcp/tools/http_tools.py`**
   - Added documentation comment explaining why auto-versioning is not supported in HTTP mode

## Behavior

### When Auto-Versioning is Enabled

If `.iriusrisk/project.json` contains `"auto_versioning": true`, and the MCP `import_otm` tool updates an existing project:

**Success case:**
```
✅ OTM import successful!
Action: Project updated
Project ID: abc-123-def
Project Name: My Application

✅ Auto-versioning: Backup version created successfully

💡 Next steps:
  1. Run sync() to download threats and countermeasures
  2. Review threats and countermeasures data in .iriusrisk/
```

**Failure case (version creation fails):**
```
✅ OTM import successful!
Action: Project updated
Project ID: abc-123-def
Project Name: My Application

⚠️  Auto-versioning: Could not create backup - Permission denied

💡 Next steps:
  1. Run sync() to download threats and countermeasures
  2. Review threats and countermeasures data in .iriusrisk/
```

### When Auto-Versioning is Disabled

If `auto_versioning` is `false` or not set in `project.json`, no version is created and no status message appears:

```
✅ OTM import successful!
Action: Project updated
Project ID: abc-123-def
Project Name: My Application

💡 Next steps:
  1. Run sync() to download threats and countermeasures
  2. Review threats and countermeasures data in .iriusrisk/
```

### New Project Creation

Auto-versioning is **only triggered for updates**, not for new project creation. When creating a new project, no version is created regardless of the `auto_versioning` setting (matching CLI behavior).

## Technical Details

### UUID Availability

The fix relies on the `uuid` field being present in the result dictionary returned by `api_client.import_otm_content()`. This field is populated during auto-update in `project_client.py` (line 415):

```python
result['uuid'] = project_uuid  # Add UUID for version operations
```

This UUID is required for version creation because the Version API expects a project UUID, not a reference ID.

### Graceful Degradation

Following the same pattern as the CLI command:
- If auto-versioning fails, the import still succeeds (version creation errors don't fail the import)
- Warning messages are logged and displayed to the user
- The AI assistant is informed of the failure through the status message

### Consistency with CLI

The implementation matches the CLI command behavior exactly:
- Same configuration source (`.iriusrisk/project.json`)
- Same version naming pattern (`After OTM import {timestamp}`)
- Same error handling approach
- Same graceful degradation strategy

## Testing

No new tests were added because:
1. The existing CLI test (`test_otm_import_with_auto_versioning_existing_project`) validates the underlying version creation logic
2. The MCP tool implementation reuses the same `VersionService` and `Config` classes
3. No MCP-specific tests existed for `import_otm` tool behavior

Manual testing confirmed the fix works as expected when:
- Auto-versioning is enabled in `project.json`
- An existing project is updated via MCP stdio `import_otm` tool
- The version is successfully created in IriusRisk

## User Experience

Users who previously configured `auto_versioning: true` in their `.iriusrisk/project.json` will now have automatic version creation working correctly when using AI assistants to update their threat models via MCP stdio mode.

The AI assistant will be informed about the auto-versioning status through the tool's output message, allowing it to:
- Confirm that backups are being created automatically
- Alert the user if version creation fails
- Provide appropriate guidance based on the outcome

## Related Documentation

- `OTM_AUTO_VERSIONING_FIX.md` - Original fix for CLI command auto-versioning
- `MCP_STDIO_FIX_SUMMARY.md` - Overview of MCP stdio mode implementation
- `README.md` - Configuration documentation for `auto_versioning` setting

