# Transparency and Updates File Fix

## Issues Fixed

### Issue 1: Missing Transparency in Status Updates
AI assistants were not consistently adding comments when updating threats/countermeasures, making it impossible to audit what was changed and why.

### Issue 2: Wrong Updates File  
MCP tools were writing to `pending_updates.json` instead of `updates.json`, causing updates to be ignored by sync command.

### Issue 3: Not Using UpdateTracker Class
MCP tools manually wrote JSON instead of using the existing `UpdateTracker` utility class.

### Issue 4: Unclear AI Instructions
Prompts didn't explicitly forbid direct writes to data files, potentially causing AI to modify read-only data files.

---

## Solution Part 1: Transparency Requirements

### Changes to FEEDME.md
Added "Transparency and Documentation - CRITICAL" as first core architectural principle with:
- All status changes MUST include detailed comments
- Comments must use HTML formatting
- Comments must include file names, implementation details, AI attribution
- Comments required for: implemented status, risk acceptance, rejections
- Character limit: 1000 chars (IriusRisk constraint)

### Changes to Prompt Files

**initialize_iriusrisk_workflow.md:**
- Enhanced countermeasure update section with TRANSPARENCY REQUIRED header
- Added comprehensive comment templates (implementation, risk acceptance, rejection)
- Added "Why Comments Are Mandatory" section
- Updated all examples to show detailed comments

**threats_and_countermeasures.md:**
- Added "CRITICAL: Transparency Requirements" section
- Updated "Your Role as AI Assistant" with transparency rules
- Added detailed examples of proper comment structure
- Emphasized NEVER update without comment

**security_development_advisor.md:**
- Added "Transparency Requirements for Implementations" section
- Showed how to gather implementation details before documenting
- Added examples of asking clarifying questions
- Emphasized never accepting vague updates

### Changes to MCP Tools (stdio_tools.py and http_tools.py)

**update_countermeasure_status():**
- Added "TRANSPARENCY REQUIREMENT" to docstring
- Made comment parameter effectively required in description
- Added warning logs when no comment provided
- Separate exception handling for comment creation
- Enhanced return messages with transparency warnings

**update_threat_status():**
- Same transparency enhancements as countermeasure
- CRITICAL warning for risk acceptance without comment (compliance issue)

### Comment Requirements

All comments must include:
1. HTML formatting (`<p>`, `<ul><li>`, `<code>`, `<strong>`)
2. What was changed and why
3. File names and paths modified
4. Implementation details
5. AI attribution ("AI-Assisted Implementation")

---

## Solution Part 2: Updates File Fix

### Changes to MCP Tools (stdio_tools.py)

**update_threat_status():**

Before:
```python
updates_file = project_root / '.iriusrisk' / 'pending_updates.json'  # WRONG FILE
# Manual JSON writing with simple list structure
```

After:
```python
from ...utils.updates import get_update_tracker
iriusrisk_dir = project_root / '.iriusrisk'
tracker = get_update_tracker(iriusrisk_dir)
tracker.track_threat_update(
    threat_id=threat_id,
    status=status,
    reason=reason,
    comment=comment
)  # Writes to .iriusrisk/updates.json with proper structure
```

**update_countermeasure_status():**
Same fix - now uses `UpdateTracker` class

**Docstrings:**
Changed references: `pending_updates.json` → `updates.json`

### Changes to Prompts

**initialize_iriusrisk_workflow.md:**
Added new section under "Use MCP Tools, Not CLI Commands":

```markdown
**CRITICAL - Do NOT Write to Data Files Directly:**
- ❌ NEVER write to `.iriusrisk/countermeasures.json` - READ-ONLY
- ❌ NEVER write to `.iriusrisk/threats.json` - READ-ONLY
- ❌ NEVER write to `.iriusrisk/components.json` - READ-ONLY
- ✅ ONLY use track_threat_update() or track_countermeasure_update() 
- ✅ These write to .iriusrisk/updates.json which sync() processes
```

**threats_and_countermeasures.md:**
Added to "Do NOT" list:
- NEVER write directly to threats.json or countermeasures.json
- NEVER modify the JSON files directly - use MCP tools only

---

## How The System Works Now

### File Roles

| File | Role | Written By | Read By |
|------|------|------------|---------|
| `updates.json` | Pending status changes | MCP tools via UpdateTracker | sync command |
| `countermeasures.json` | Current data from IriusRisk | sync (downloads from API) | AI (read-only) |
| `threats.json` | Current data from IriusRisk | sync (downloads from API) | AI (read-only) |
| `components.json` | Component library | sync (downloads from API) | AI (read-only) |
| `trust-zones.json` | Trust zones | sync (downloads from API) | AI (read-only) |
| `project.json` | Project metadata | init/sync commands | Config |

### Workflow

```
1. AI reads threats.json / countermeasures.json (data from IriusRisk)
2. AI calls track_countermeasure_update() with detailed comment
3. UpdateTracker writes to updates.json
4. User runs: iriusrisk sync
5. Sync reads updates.json
6. Sync applies updates to IriusRisk API (with comments)
7. Sync downloads fresh data from IriusRisk
8. Sync overwrites countermeasures.json and threats.json
9. Loop: AI reads updated data...
```

### Key Principles

1. **Read-only data files**: `threats.json`, `countermeasures.json`, `components.json`, `trust-zones.json`
2. **Write-only tracking**: `updates.json` (via UpdateTracker only)
3. **Transparency mandatory**: All updates include detailed comments
4. **Single source of truth**: UpdateTracker class handles all update tracking
5. **Sync is the bridge**: Only sync command talks to IriusRisk API for status updates

---

## Files Modified

1. `FEEDME.md` - Added transparency principle
2. `src/iriusrisk_cli/mcp/tools/stdio_tools.py` - Fixed file path & use UpdateTracker
3. `src/iriusrisk_cli/mcp/tools/http_tools.py` - Added transparency warnings
4. `src/iriusrisk_cli/prompts/initialize_iriusrisk_workflow.md` - Transparency + file write rules
5. `src/iriusrisk_cli/prompts/threats_and_countermeasures.md` - Transparency + no direct writes
6. `src/iriusrisk_cli/prompts/security_development_advisor.md` - Transparency requirements

---

## Testing

### Test 1: Transparency Warnings
```python
# Call MCP tool without comment
update_countermeasure_status(
    project_id="...",
    countermeasure_id="...",
    status="implemented",
    reason="Added validation"
    # No comment
)
# Expected: Warning in return message
```

### Test 2: Correct File Usage
```bash
# Have AI update a countermeasure
# Check updates.json exists and has proper structure
cat .iriusrisk/updates.json

# Should show UpdateTracker format:
{
  "updates": [...],
  "last_sync": null,
  "metadata": {...}
}
```

### Test 3: Sync Processes Updates
```bash
iriusrisk sync
# Should show: "Applying X pending updates to IriusRisk..."
# Then download fresh data
# updates.json should be marked as applied
```

### Test 4: Data Files Not Modified Directly
```bash
# Verify AI doesn't write to these files
ls -la .iriusrisk/
# countermeasures.json should only change after sync (from API)
# threats.json should only change after sync (from API)
```

---

## Impact

**Before:**
- ❌ AI could update status without comments (no audit trail)
- ❌ MCP updates written to wrong file (ignored by sync)
- ❌ Manual JSON writing (inconsistent with architecture)
- ❌ Unclear instructions (AI might write to wrong files)

**After:**
- ✅ All updates require detailed comments (full transparency)
- ✅ MCP updates written to correct file (processed by sync)
- ✅ Uses UpdateTracker class (consistent architecture)
- ✅ Clear instructions forbid direct data file writes
- ✅ Proper separation: data files (read-only) vs updates file (write)
- ✅ Complete audit trail for all AI-assisted changes

