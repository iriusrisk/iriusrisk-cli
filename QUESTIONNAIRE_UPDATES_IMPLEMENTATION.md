# Questionnaire Updates Implementation

## Overview

This document describes the implementation of questionnaire answer tracking in the IriusRisk CLI. This feature allows users to answer project and component questionnaires and have those answers synchronized back to IriusRisk via the updates JSON file mechanism.

## Implementation Details

### 1. UpdateTracker Class (`src/iriusrisk_cli/utils/updates.py`)

Added two new methods to track questionnaire updates:

#### `track_project_questionnaire_update(project_id, answers_data, context)`
- Tracks answers to project/architecture questionnaire questions
- Stores the project UUID, answers data structure, and optional context
- Removes any existing project questionnaire update for the same project before adding the new one

#### `track_component_questionnaire_update(component_id, answers_data, context)`
- Tracks answers to component-specific questionnaire questions
- Stores the component UUID, answers data structure, and optional context
- Removes any existing component questionnaire update for the same component before adding the new one

#### Updated `get_stats()` method
- Added counters for `project_questionnaire_updates` and `component_questionnaire_updates`
- Provides statistics on all update types including questionnaires

### 2. Sync Command (`src/iriusrisk_cli/commands/sync.py`)

#### Updated `_apply_pending_updates()` function
- Added handling for `project_questionnaire` update type
- Added handling for `component_questionnaire` update type
- Uses the `questionnaire_client` to push updates to IriusRisk API
- Displays appropriate success messages indicating that the rules engine will regenerate threats

### 3. MCP Tools (`src/iriusrisk_cli/commands/mcp.py`)

Added two new MCP tools for AI assistants:

#### `track_project_questionnaire_update(project_id, answers_data, project_path, context)`
- Allows AI to track project questionnaire answers
- Validates project path and tracks the update
- Returns success message with instruction to call sync()

#### `track_component_questionnaire_update(component_id, answers_data, project_path, context)`
- Allows AI to track component questionnaire answers
- Validates project path and tracks the update
- Returns success message with instruction to call sync()

#### Updated `get_pending_updates()` tool
- Now displays counts for project and component questionnaire updates
- Shows questionnaire updates in the recent updates list with appropriate formatting

### 4. CLI Updates Command (`src/iriusrisk_cli/commands/updates.py`)

Updated the `list` and `stats` commands to properly display questionnaire updates:

#### `list` command
- Displays questionnaire updates with appropriate formatting (no "status" field)
- Shows context for questionnaire updates instead of reason/status

#### `stats` command
- Includes counts for project and component questionnaire updates
- Shows questionnaire updates in applied updates history

## Data Structure

### Updates JSON Format

Questionnaire updates are stored in the `updates.json` file with the following structure:

```json
{
  "updates": [
    {
      "id": "project-uuid-or-component-uuid",
      "type": "project_questionnaire",  // or "component_questionnaire"
      "answers_data": {
        "steps": [
          {
            "questions": [
              {
                "referenceId": "question-ref-id",
                "answers": [
                  {
                    "referenceId": "answer-ref-id",
                    "value": "true"  // or "false"
                  }
                ]
              }
            ]
          }
        ]
      },
      "context": "Optional context explaining the analysis",
      "timestamp": "2026-01-06T12:34:56.789Z",
      "applied": false
    }
  ],
  "last_sync": null,
  "metadata": {
    "version": "1.0",
    "created": "2026-01-06T12:34:56.789Z"
  }
}
```

## API Integration

The implementation uses the existing `QuestionnaireApiClient` methods:

- `update_project_questionnaire(project_id, questionnaire_data)` - Updates project questionnaire
- `update_component_questionnaire(component_id, questionnaire_data)` - Updates component questionnaire

These API calls trigger IriusRisk's rules engine to regenerate the threat model based on the new answers.

## Workflow

1. **Download Questionnaires**: Run `iriusrisk sync` to download current questionnaires to `.iriusrisk/questionnaires.json`

2. **Analyze Source Code**: AI or user analyzes the codebase to determine answers to questionnaire questions

3. **Track Answers**: Use MCP tools or programmatically call `UpdateTracker` methods to track questionnaire answers:
   - `track_project_questionnaire_update()` for project/architecture questions
   - `track_component_questionnaire_update()` for component-specific questions

4. **Sync to IriusRisk**: Run `iriusrisk sync` to:
   - Apply all pending questionnaire updates to IriusRisk
   - Trigger rules engine to regenerate threat model
   - Download updated threats and countermeasures

5. **Review Changes**: The threat model is now updated based on the questionnaire answers

## Testing

The implementation was tested with:
- Project questionnaire tracking
- Component questionnaire tracking
- Mixed update types (threats, countermeasures, questionnaires)
- Updates file format validation
- All tests passed successfully

## Files Modified

1. `src/iriusrisk_cli/utils/updates.py` - Added questionnaire tracking methods
2. `src/iriusrisk_cli/commands/sync.py` - Added questionnaire update application
3. `src/iriusrisk_cli/commands/mcp.py` - Added MCP tools for questionnaire tracking
4. `src/iriusrisk_cli/commands/updates.py` - Updated CLI commands to display questionnaire updates

## Benefits

- **Automated Threat Model Refinement**: AI can analyze code and answer questionnaires to refine threat models
- **Consistent with Existing Pattern**: Uses the same updates.json mechanism as threats and countermeasures
- **Batch Processing**: Multiple questionnaire updates can be tracked and applied together
- **Error Handling**: Failed updates are preserved for retry
- **Auditability**: All questionnaire updates are tracked with timestamps and context

