# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **OTM Import Simplification**: Removed `--update` flag from `iriusrisk otm import` command. Import now automatically updates existing projects without requiring explicit flag.
- **Auto-Versioning Enhancement**: Auto-versioning now works consistently for all import scenarios:
  - Automatic updates when project exists (no flag needed)
  - Reference ID override from project.json
  - MCP `import_otm` tool
- **Proactive Version Creation**: Version snapshots are now created proactively before any update operation when auto-versioning is enabled, rather than only when using explicit `--update` flag.
- **MCP Sync Workflow Clarification**: Enhanced MCP AI instructions to automatically call `sync()` after tracking threat/countermeasure updates without asking permission. This fixes confusion where AI would suggest CLI commands or ask for user permission instead of completing the workflow automatically.
- **MCP Project ID Preservation**: Added critical instructions that the OTM `project.id` field must NEVER be changed when updating existing threat models. The project ID is now treated as sacred and immutable, with explicit warnings against modifying it for any reason.

### Fixed
- **Auto-Versioning Not Triggering**: Fixed critical issue where auto-versioning would not create backup versions during OTM imports unless the `--update` flag was explicitly used. Now properly detects existing projects and creates versions before any update operation.
- **MCP Auto-Versioning**: Fixed missing auto-versioning support in MCP `import_otm` tool. Now respects `auto_versioning` setting in project.json.
- **Auto-Versioning Critical Fixes**: Fixed multiple critical bugs causing instant 401 errors during OTM imports with auto-versioning enabled:
  1. **Never Actually Waited**: Code checked `result.get('id')` but API returns `'operationId'`, so wait condition was always False. Version creation returned immediately without waiting, causing instant 401 when import tried to proceed on locked project. Now checks `result.get('operationId')` correctly.
  2. **Silent Failure**: MCP `import_otm` was catching ALL exceptions from version creation and continuing with import anyway. Now properly stops and reports the error.
  3. **UUID Resolution**: `create_version()` was creating a new API client to resolve UUIDs, which could fail silently and pass reference IDs to UUID-only endpoints. Now uses the injected project_repository's API client.
  4. **Async Poll Field**: Code was reading wrong field (`'state'` instead of `'status'`) from async operation responses. Now reads `'status'` field correctly.
  5. **Project Lock Polling**: After async operation completes, now actively polls project status (`operation='none'`, `isThreatModelLocked=false`, `readOnly=false`) to ensure project is truly unlocked before import.
- **MCP Sync Behavior**: Fixed issue where AI would not automatically run sync after tracking updates, instead suggesting CLI commands or asking user permission. Updated prompts and tool return messages to enforce immediate sync() calls after any update tracking.
- **MCP Project ID Modification**: Fixed critical issue where AI would attempt to change the OTM `project.id` when import failures occurred, breaking the connection to existing IriusRisk projects. Added explicit instructions to preserve project IDs and stop on errors rather than attempting workarounds.

## [0.1.1] - 2024-11-19

### Fixed
- **MCP Path Resolution**: Fixed critical issue where threat and countermeasure updates were being written to the user's home directory (`~/.iriusrisk/updates.json`) instead of the project directory. All MCP file operation functions now require explicit `project_path` parameter with validation, ensuring updates are tracked in the correct project location.
  - Updated `track_threat_update()`, `track_countermeasure_update()`, `create_countermeasure_issue()`, `get_pending_updates()`, `clear_updates()`, `show_diagram()`, and `generate_report()` to accept `project_path` parameter
  - Added path validation with clear error messages for invalid paths
  - Updated MCP manifest and AI prompts to reflect parameter changes
  - Removed unreliable `find_project_root()` fallback logic in favor of explicit paths

## [0.1.0] - 2025-11-12

### Added

#### Core CLI Features
- Project management commands (`list`, `show`)
- Threat viewing and status updates
- Countermeasure tracking and management
- Report generation in multiple formats (PDF, HTML, XLSX, CSV)
- Project version snapshots (create, list, compare)
- Configuration management with multiple sources (user config, .env, environment variables)
- API connection testing

#### MCP Integration
- Full Model Context Protocol (MCP) server implementation for AI assistant integration
- AI-guided threat modeling workflow
- Automated security analysis from source code
- OTM (Open Threat Model) file import/export
- Threat and countermeasure status tracking
- Diagram generation and visualization
- Custom prompt support for organization-specific requirements
- Security development advisor guidance
- Architecture and design review capabilities

#### Developer Experience
- Comprehensive test suite (unit, CLI, integration tests)
- Flexible logging with verbosity controls
- Multiple output formats (table, JSON, CSV)
- Secure credential management
- Configuration priority system
- Rich help documentation

### Security
- Secure API key handling with masked input
- Credentials stored separately from project files
- Environment variable support for CI/CD
- No credentials in version control

### Documentation
- Complete README with usage examples
- Developer guide for contributors
- MCP integration examples
- Configuration best practices
- AI workflow examples

[0.1.1]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.1.1
[0.1.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.1.0

