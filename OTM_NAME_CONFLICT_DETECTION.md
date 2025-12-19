# OTM Import Name Conflict Detection

## Overview

This document describes the improved name conflict detection logic for OTM imports, which ensures that projects are correctly identified by reference ID rather than just by name when auto-updating existing projects.

## The Problem

When importing an OTM file, IriusRisk can reject the import with a "project already exists" error. This error can occur in two distinct scenarios:

### Scenario 1: Same Project (Safe to Update)
- A project with **both the same name AND ref ID** already exists in IriusRisk
- This is the **same project**, just being updated with new data
- **Action**: Auto-update should proceed

### Scenario 2: Name Conflict (ERROR)
- A project with the **same name but DIFFERENT ref ID** exists in IriusRisk  
- These are **two different projects** that happen to have the same name
- **Action**: Must raise a clear error and ask the user to resolve the conflict

## The Solution

### Improved Logic Flow

When an OTM import fails with "project already exists":

1. **Extract ref ID** from the OTM file/content
2. **Validate existence by ref ID** using `validate_project_exists(project_id)`
3. **Decision**:
   - If `exists = True`: Project found by ref ID → **Proceed with auto-update**
   - If `exists = False`: Project NOT found by ref ID → **NAME CONFLICT error**

### Code Changes

#### In `project_client.py` (both `import_otm_file` and `import_otm_content`)

```python
if auto_update and (already_exists_error or 'already exists' in error_msg.lower()):
    # Extract project ID from OTM
    self.logger.info("Project already exists, checking if it's the same project by ref ID")
    project_id = self._extract_project_id_from_otm(otm_file_path)  # or from content
    
    if not project_id:
        raise RequestException(f"Project already exists but could not determine project ID from OTM file")
    
    # Check if a project with this ref ID actually exists
    from ..utils.api_helpers import validate_project_exists
    exists, project_uuid = validate_project_exists(project_id, self)
    
    if not exists:
        # NAME CONFLICT: project exists by name but not by ref ID
        project_name = self._extract_project_name_from_otm(otm_file_path) or "Unknown"
        raise RequestException(
            f"NAME CONFLICT: A project named '{project_name}' already exists in IriusRisk "
            f"but with a different reference ID than '{project_id}' in your OTM file. "
            f"This means you're trying to import a different project with the same name. "
            f"\n\nTo resolve this conflict, you must either:"
            f"\n  1. Rename your project in the OTM file to a unique name"
            f"\n  2. Change the reference ID in your OTM file"
            f"\n  3. Rename or delete the existing project in IriusRisk"
        )
    
    # Project exists by ref ID - safe to update
    try:
        self.logger.info(f"Project exists with matching ref ID '{project_id}', proceeding with auto-update")
        result = self.update_project_with_otm_file(project_id, otm_file_path)
        result['action'] = 'updated'
        return result
    except Exception as update_error:
        raise RequestException(f"Failed to create new project (already exists) and failed to update existing project: {str(update_error)}")
```

## User Experience

### Success Case: Auto-Update

```bash
$ iriusrisk-cli otm import my-project.otm
INFO: Project already exists, checking if it's the same project by ref ID
INFO: Project exists with matching ref ID 'my-app', proceeding with auto-update
INFO: Successfully updated project 'My Application' (ID: my-app)
Project updated successfully
```

### Error Case: Name Conflict

```bash
$ iriusrisk-cli otm import my-project.otm
ERROR: NAME CONFLICT: A project named 'My Application' already exists in IriusRisk 
but with a different reference ID than 'my-app-v2' in your OTM file. This means 
you're trying to import a different project with the same name.

To resolve this conflict, you must either:
  1. Rename your project in the OTM file to a unique name
  2. Change the reference ID in your OTM file
  3. Rename or delete the existing project in IriusRisk
```

## Benefits

1. **Prevents Accidental Updates**: Users cannot accidentally overwrite an unrelated project that happens to have the same name
2. **Clear Error Messages**: When conflicts occur, users get actionable guidance on how to resolve them
3. **Correct Project Identification**: Uses reference ID (the stable identifier) rather than name (which can be changed)
4. **Maintains Backward Compatibility**: Auto-update still works seamlessly for legitimate update scenarios

## Testing

### Test Coverage

1. **`test_import_otm_file_conflict_returns_error`**
   - Scenario: Project exists by name but NOT by ref ID (name conflict)
   - Expected: Raises `RequestException` with "NAME CONFLICT" message

2. **`test_import_otm_file_auto_update_success`**
   - Scenario: Project exists by ref ID (same project)
   - Expected: Successfully updates project, returns `action='updated'`

3. **`test_import_otm_file_new_project`**
   - Scenario: Project doesn't exist at all
   - Expected: Creates new project, returns `action='created'`

## Technical Notes

### Why Reference ID, Not Name?

- **Reference IDs are stable**: They don't change when users rename projects
- **Names can collide**: Multiple teams might choose the same project name
- **API design**: IriusRisk V1 API accepts reference IDs for OTM operations
- **OTM specification**: The `project.id` field in OTM is the reference ID

### Additional Metadata in Result

When a project is updated via auto-update, the result now includes:
- `result['action']`: Set to `'updated'` to indicate an update occurred
- `result['ref']`: The project reference ID (from OTM file)
- `result['uuid']`: The project UUID (from IriusRisk, required for version operations)

This additional metadata ensures that auto-versioning can correctly create backup versions using the UUID, which is required by the Version API.

### Integration Points

This logic applies to:
- CLI: `iriusrisk-cli otm import`
- Stdio MCP: `import_otm` tool
- HTTP MCP: `import_otm` tool
- API Client: `api_client.import_otm_file()` and `api_client.import_otm_content()`

All use the same underlying `project_client.py` methods, ensuring consistent behavior across all interfaces.

## Future Enhancements

Potential improvements:
1. Add a `--force-name-conflict` flag to allow overriding name conflicts (with strong warning)
2. Suggest available similar project names when conflicts occur
3. Provide project UUID in error message for easier identification in IriusRisk UI

