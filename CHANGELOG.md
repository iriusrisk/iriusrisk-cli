# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

