# Updates File Fix Summary

## Problem Identified

The MCP tools in `stdio_tools.py` were writing to the **wrong file** for tracking threat and countermeasure updates:

- **Wrong**: Writing to `.iriusrisk/pending_updates.json` (hardcoded, non-existent in design)
- **Correct**: Should write to `.iriusrisk/updates.json` (what sync command reads)

This was a pre-existing bug that caused updates made via MCP tools to be ignored by the sync command.

## Root Cause

The MCP tools (`update_threat_status()` and `update_countermeasure_status()`) were:
1. **Not using the `UpdateTracker` class** from `utils/updates.py`
2. **Manually writing JSON files** with hardcoded path `pending_updates.json`
3. **Using wrong data structure** (simple list vs. UpdateTracker's structured format)

Meanwhile, the `sync` command correctly uses:
- `get_update_tracker()` helper function
- Reads from `.iriusrisk/updates.json`
- Proper `UpdateTracker` class with methods like `track_threat_update()`, `track_countermeasure_update()`

## How It Should Work

```
User/AI → MCP tool → UpdateTracker.track_countermeasure_update()
                   → writes to .iriusrisk/updates.json
                   
Later...

User runs: iriusrisk sync
         → reads .iriusrisk/updates.json via get_update_tracker()
         → applies updates to IriusRisk API
         → downloads fresh data
         → writes to .iriusrisk/countermeasures.json (fresh from API)
         → writes to .iriusrisk/threats.json (fresh from API)
```

## Files Fixed

### 1. `src/iriusrisk_cli/mcp/tools/stdio_tools.py`

#### Changed: `update_threat_status()`
**Before:**
```python
# Manual JSON file writing
updates_file = project_root / '.iriusrisk' / 'pending_updates.json'
updates = []
if updates_file.exists():
    with open(updates_file, 'r') as f:
        updates = json.load(f)
updates.append({...})
with open(updates_file, 'w') as f:
    json.dump(updates, f, indent=2)
```

**After:**
```python
# Use UpdateTracker class
from ...utils.updates import get_update_tracker
iriusrisk_dir = project_root / '.iriusrisk'
tracker = get_update_tracker(iriusrisk_dir)
tracker.track_threat_update(
    threat_id=threat_id,
    status=status,
    reason=reason,
    comment=comment
)
```

#### Changed: `update_countermeasure_status()`
Same fix - now uses `tracker.track_countermeasure_update()` instead of manual JSON writing.

#### Updated Docstrings
Changed references from `pending_updates.json` → `updates.json`

### 2. `src/iriusrisk_cli/prompts/initialize_iriusrisk_workflow.md`

Added critical section under "Use MCP Tools, Not CLI Commands":

```markdown
**CRITICAL - Do NOT Write to Data Files Directly:**
- ❌ NEVER write to `.iriusrisk/countermeasures.json` - this is READ-ONLY data from IriusRisk
- ❌ NEVER write to `.iriusrisk/threats.json` - this is READ-ONLY data from IriusRisk  
- ❌ NEVER write to `.iriusrisk/components.json` - this is READ-ONLY library data
- ✅ ONLY use `track_threat_update()` or `track_countermeasure_update()` MCP tools
- ✅ These tools write to `.iriusrisk/updates.json` which sync() processes

**Why:** The JSON files in `.iriusrisk/` are downloaded FROM IriusRisk and must not be 
modified directly. Status changes go through the update tracking system.
```

### 3. `src/iriusrisk_cli/prompts/threats_and_countermeasures.md`

Added to "Do NOT" list:
- **NEVER write directly to threats.json or countermeasures.json** - these are READ-ONLY
- **NEVER modify the JSON files directly** - use MCP tools only

## Benefits

1. **Updates now sync properly** - MCP tool updates will be processed by `iriusrisk sync`
2. **Consistent architecture** - All code uses `UpdateTracker` class, not ad-hoc JSON writes
3. **Proper data structure** - UpdateTracker format includes metadata, versioning, timestamps
4. **Clear AI instructions** - Prompts explicitly forbid direct file writes to data files
5. **Single source of truth** - `utils/updates.py` is the only place that writes to `updates.json`

## File Roles Clarified

| File | Role | Written By | Read By |
|------|------|------------|---------|
| `updates.json` | Pending status changes | MCP tools via UpdateTracker | sync command |
| `countermeasures.json` | Current countermeasures data | sync command (from API) | AI for analysis |
| `threats.json` | Current threats data | sync command (from API) | AI for analysis |
| `components.json` | Component library | sync command (from API) | AI for threat modeling |
| `trust-zones.json` | Trust zones library | sync command (from API) | AI for threat modeling |
| `project.json` | Project metadata | init/sync commands | Config system |

## Testing Recommendations

1. **Test update tracking:**
```bash
# Via MCP tool (stdio mode)
# AI calls: update_countermeasure_status(...)

# Check file exists and has correct structure
cat .iriusrisk/updates.json
```

2. **Test sync applies updates:**
```bash
iriusrisk sync
# Should show "Applying X pending updates..."
# Should then download fresh data
```

3. **Verify file separation:**
```bash
# updates.json should have pending changes
cat .iriusrisk/updates.json

# countermeasures.json should have current state from API
cat .iriusrisk/countermeasures.json
```

## What Changed vs. Original Transparency Work

The original transparency improvements added:
- ✅ Better docstrings and warnings
- ✅ Transparency requirements in prompts
- ✅ Comment failure handling

This fix addresses:
- ✅ **Wrong file name** (`pending_updates.json` → `updates.json`)
- ✅ **Not using UpdateTracker class** (now uses it)
- ✅ **AI confusion about which files to write** (added explicit DO NOT instructions)

Both changes are necessary and complementary.

