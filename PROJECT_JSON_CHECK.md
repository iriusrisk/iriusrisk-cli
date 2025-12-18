# Project.json Initialization Check in Stdio Mode

## Summary

Added an early validation check in standard I/O mode to ensure that `project.json` exists before the MCP server starts processing requests. This prevents issues where operations would fail or create unintended duplicate projects due to missing project initialization.

## Problem

When running the MCP server in stdio mode without first running `iriusrisk init`, the following issues occurred:

1. No stable IriusRisk project ID available
2. Each operation (sync, OTM import) would attempt to create a NEW project
3. Cannot track threats, countermeasures, or project state across sessions
4. Sync operations would not function properly after threat model generation
5. Update tracking would fail

## Solution

### 1. Sync Tool Check (`src/iriusrisk_cli/mcp/tools/stdio_tools.py`)

Added validation in the `sync()` MCP tool that:

- Checks for `.iriusrisk/project.json` **before** performing any sync operations
- If missing: Returns a clear error message through the MCP protocol (visible to AI)
- If present: Proceeds with normal sync operations
- **Only applies to stdio mode** (not HTTP mode)

The error message includes:

- Clear explanation of why initialization matters
- Impact of missing initialization
- Required action (`iriusrisk init`)
- What the initialization command does
- Explicit instruction to NOT PROCEED until initialized

### 2. Initialize Workflow Tool Enhancement (`src/iriusrisk_cli/mcp/tools/shared_tools.py`)

Enhanced the `initialize_iriusrisk_workflow()` tool to:

- Perform runtime check for `.iriusrisk/project.json` in stdio mode
- If missing: Prepends critical warning to the workflow instructions
- If present: Returns normal workflow instructions
- Warning includes explicit "STOP HERE" directive for the AI

### 3. Updated Workflow Instructions (`src/iriusrisk_cli/prompts/initialize_iriusrisk_workflow.md`)

Enhanced the AI workflow instructions to include a new section:

**"CRITICAL: Check Project Initialization FIRST"**

This section instructs the AI to:

1. Check for `.iriusrisk/project.json` before doing anything else
2. If missing: Stop and inform the user to run `iriusrisk init`
3. If present: Continue with normal workflow

### 4. Stdio Server Logging (`src/iriusrisk_cli/mcp/stdio_server.py`)

Simplified stdio server to only log project.json status:

- Logs whether project.json exists (for debugging purposes)
- Does NOT print to stderr (ineffective in MCP stdio mode)
- Validation happens at tool invocation time, not server startup

### 5. Test Coverage (`tests/cli/test_cli_mcp.py`)

Updated tests:

- `test_mcp_starts_without_project_json`: Verifies server starts even without project.json
- `test_mcp_starts_with_project_json`: Verifies server starts normally with project.json
- Tools handle the validation, not server startup

## Implementation Details

### Error Message Format (Sync Tool)

The sync tool returns this error message through MCP when project.json is missing:

```
⚠️  CRITICAL: No project.json file found at <path>

This project has NOT been initialized with IriusRisk CLI.

WHY THIS MATTERS:
- Without project.json, there is no stable IriusRisk project ID
- Each operation will attempt to create a NEW project
- You cannot track threats, countermeasures, or project state across sessions
- Sync operations will not function properly after threat model generation

REQUIRED ACTION:
Please ask the user to run this command in the project directory:

    iriusrisk init

This command will:
1. Create a .iriusrisk/project.json file with a stable project reference ID
2. Allow proper project tracking across MCP sessions
3. Enable sync functionality to work correctly

DO NOT PROCEED with threat modeling until the project is initialized.
```

### Warning Message Format (Initialize Workflow Tool)

The initialize_iriusrisk_workflow tool prepends this warning to its instructions when project.json is missing:

```
🚨 CRITICAL RUNTIME CHECK: No project.json file detected!

The project at <path> has NOT been initialized.

⚠️  DO NOT PROCEED with any threat modeling activities until the user runs:

    iriusrisk init

Without this initialization:
- No stable project ID exists
- Operations will fail or create duplicate projects
- Cannot track threats/countermeasures across sessions

STOP HERE and inform the user they must initialize the project first.
```

### Key Design Decisions

1. **Tool-level validation**: Checks happen when tools are invoked, not at server startup
2. **MCP protocol visibility**: Error messages return through MCP tool responses (visible to AI)
3. **Non-blocking server**: Server still starts even without project.json
4. **Stdio-only**: This check only applies to stdio mode where project.json is expected and required
5. **Clear messaging**: Error messages are detailed and actionable, explaining both the "why" and the "how to fix"
6. **Multiple touchpoints**: Both sync() and initialize_iriusrisk_workflow() perform the check

## Files Modified

1. `src/iriusrisk_cli/mcp/tools/stdio_tools.py` - Added project.json validation to sync() tool
2. `src/iriusrisk_cli/mcp/tools/shared_tools.py` - Enhanced initialize_iriusrisk_workflow() with runtime check
3. `src/iriusrisk_cli/mcp/stdio_server.py` - Simplified to only log project.json status
4. `src/iriusrisk_cli/prompts/initialize_iriusrisk_workflow.md` - Enhanced workflow instructions
5. `tests/cli/test_cli_mcp.py` - Updated test coverage

## Testing

All tests pass (595 total):

```bash
pytest tests/cli/test_cli_mcp.py::TestMCPProjectInitializationCheck -v
# Result: 2/2 passed (server startup tests)

pytest tests/ -v
# Result: 595/595 passed
```

The tests verify that:
- MCP server starts successfully with or without project.json
- Tools (sync, initialize_iriusrisk_workflow) handle validation at invocation time
- Error messages are returned through MCP protocol (not stderr)

## Usage

### Scenario 1: Missing project.json

```bash
cd /path/to/project  # Directory without .iriusrisk/project.json
iriusrisk mcp
```

What happens:
1. Server starts successfully
2. When AI calls `initialize_iriusrisk_workflow()`: Returns instructions with critical warning prepended
3. When AI calls `sync()`: Returns error message, does NOT proceed with sync
4. AI sees error message and tells user to run `iriusrisk init`

### Scenario 2: project.json exists

```bash
cd /path/to/project  # Directory with .iriusrisk/project.json
iriusrisk mcp
```

What happens:
1. Server starts normally
2. When AI calls `initialize_iriusrisk_workflow()`: Returns normal workflow instructions
3. When AI calls `sync()`: Proceeds with sync operation normally
4. AI continues with normal threat modeling workflow

## Benefits

1. **Tool-level Validation**: Issues are caught when tools are invoked (sync, initialize_iriusrisk_workflow)
2. **MCP Protocol Visibility**: Error messages return through MCP tool responses, visible to AI
3. **Clear Guidance**: Users know exactly what to do to fix the issue (`iriusrisk init`)
4. **Prevents Duplicate Projects**: Stops operations before they create unintended projects
5. **Maintains Stability**: Ensures consistent project ID across sessions
6. **Better UX**: AI receives actionable error messages and can guide users properly
7. **Multiple Touchpoints**: Both workflow initialization and sync operations check for project.json

## Future Enhancements

Potential improvements that could be considered:

1. Add similar check for HTTP mode (if applicable)
2. Offer to automatically run `iriusrisk init` interactively
3. Add telemetry to track how often this warning is triggered
4. Provide project discovery suggestions if project.json exists in parent directories

