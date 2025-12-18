# Duplicate Comment Fix

## Problem

When using STDIO MCP mode, countermeasure and threat status updates were creating duplicate comments in IriusRisk. The same comment would appear twice on the same countermeasure/threat.

### Root Cause

The STDIO MCP tools (`update_countermeasure_status` and `update_threat_status`) were:
1. Immediately applying updates to IriusRisk (including creating comments)
2. Tracking the updates in `updates.json` with `"applied": false`

When `sync` ran, it would:
1. Read all updates from `updates.json` where `"applied": false`
2. Re-apply them to IriusRisk, creating duplicate comments

This was an architectural mismatch between:
- **STDIO tools**: Stateful, apply immediately + track for audit
- **Sync process**: Assumes all updates in `updates.json` are unapplied

## Solution

The fix leverages existing infrastructure in the `UpdateTracker` class:

### Changes Made

#### 1. STDIO Tools Mark Updates as Applied

**File**: `src/iriusrisk_cli/mcp/tools/stdio_tools.py`

Both `update_countermeasure_status` and `update_threat_status` now call `mark_update_applied()` immediately after successfully applying an update:

```python
# Track locally using UpdateTracker
try:
    from ...utils.updates import get_update_tracker
    project_root, _ = find_project_root()
    if project_root:
        iriusrisk_dir = project_root / '.iriusrisk'
        tracker = get_update_tracker(iriusrisk_dir)
        tracker.track_countermeasure_update(
            countermeasure_id=countermeasure_id,
            status=status,
            reason=reason,
            comment=comment
        )
        # Mark as applied immediately since we just applied it (prevents duplicate comments on sync)
        tracker.mark_update_applied(countermeasure_id, "countermeasure")
        logger.info(f"Tracked and marked countermeasure update as applied in {iriusrisk_dir / 'updates.json'}")
except Exception as track_error:
    logger.warning(f"Could not track update locally: {track_error}")
```

#### 2. Sync Already Filters Applied Updates

**File**: `src/iriusrisk_cli/commands/sync.py`

The sync command already had the correct behavior:
- Line 412: `pending_updates = tracker.get_pending_updates()` - only gets updates where `"applied": false`
- Lines 573-576: Clears applied updates after successful sync

No changes were needed to the sync command.

### How It Works Now

1. **STDIO MCP Tool** applies update:
   - Updates status in IriusRisk
   - Creates comment in IriusRisk
   - Tracks update in `updates.json` with `"applied": false`
   - **NEW**: Marks update as `"applied": true` immediately
   - Update remains in `updates.json` for audit trail

2. **Sync** runs:
   - Reads `updates.json`
   - Filters to only `"applied": false` updates (skips STDIO-applied ones)
   - Applies pending updates
   - Marks them as applied
   - Clears applied updates from the file

### Benefits

1. ✅ **No duplicate comments** - Updates are only applied once
2. ✅ **Audit trail preserved** - Updates stay in `updates.json` until cleaned up
3. ✅ **Minimal code changes** - Uses existing infrastructure
4. ✅ **Clean separation** - STDIO applies immediately, sync handles pending
5. ✅ **Handles retries** - If someone manually sets `applied: false`, sync will reapply

## Testing

Created comprehensive test suite in `tests/unit/test_duplicate_comment_fix.py`:

- ✅ `test_update_tracker_marks_as_applied` - Verifies marking mechanism
- ✅ `test_threat_update_marks_as_applied` - Tests threat updates
- ✅ `test_clear_applied_updates_removes_only_applied` - Tests cleanup
- ✅ `test_multiple_updates_same_id_replaces_and_resets_applied` - Tests update replacement
- ✅ `test_stdio_tool_workflow_prevents_duplicates` - Integration test verifying the fix

All 600 tests pass, including the new ones.

## Files Modified

1. `src/iriusrisk_cli/mcp/tools/stdio_tools.py`
   - Added `tracker.mark_update_applied()` calls in both update functions
   - Lines 598 and 685

2. `tests/unit/test_duplicate_comment_fix.py` (new file)
   - Comprehensive test coverage for the fix

## Migration Notes

No migration needed. Existing `updates.json` files will work correctly:
- Old updates with `"applied": false` will be processed by sync
- New updates from STDIO tools will be marked as applied immediately
- The cleanup process removes applied updates automatically

## Future Considerations

The `updates.json` file serves dual purposes:
1. **Pending queue** - Updates waiting to be applied
2. **Audit trail** - Record of what was changed

Currently, applied updates are cleared after sync. If longer-term audit trail is needed, consider:
- Adding a separate `audit.json` file
- Archiving applied updates instead of deleting them
- Adding a retention policy for audit records

