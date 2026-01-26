# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-01-26

### Added

#### Multi-Repository Threat Modeling
- **Repository Scope Definitions**: New `scope` field in `.iriusrisk/project.json` allows repositories to define their contribution to a unified threat model
- **Multi-Repo Support**: Multiple repositories can now contribute to a single IriusRisk project, enabling comprehensive threat modeling for microservices, infrastructure-as-code, and distributed architectures
- **Scope-Aware Init Command**: `iriusrisk init` now supports `--scope` parameter for defining repository contributions
- **Interactive Scope Prompting**: When connecting to existing projects, users are prompted to define how their repository contributes
- **OTM Export MCP Tool**: New `export_otm()` MCP tool enables AI assistants to retrieve existing threat models for intelligent merging
- **Config Scope Support**: `Config.get_project_scope()` method for reading scope definitions

#### AI Workflow Enhancements
- **Multi-Repo AI Workflows**: AI assistants can now intelligently merge contributions from multiple repositories based on scope definitions
- **Enhanced Prompts**: Updated `create_threat_model.md` and `analyze_source_material.md` with comprehensive multi-repository workflow guidance
- **Scope-Aware Analysis**: AI assistants focus their analysis based on repository scope (infrastructure vs application vs frontend)
- **Automatic OTM Download**: The `sync` command now automatically downloads the current threat model as `current-threat-model.otm`, making it immediately available for AI assistants to merge contributions without additional API calls
- **Explicit Intent Recognition**: AI assistants now proceed directly when users explicitly request threat modeling (e.g., "threat model this code"), eliminating unnecessary permission prompts
- **Workflow Disambiguation**: Clear separation between "threat modeling" (architecture creation/update) and "threat analysis" (reviewing existing threats) - AI no longer confuses these workflows
- **Scope-Based Filtering**: When analyzing threats, countermeasures, or questionnaires in multi-repository projects, AI assistants now filter to show only items relevant to the current repository's scope (e.g., infrastructure repo sees infrastructure threats, application repo sees application threats)
- **Intelligent Layout Management with Cascading Calculations**: AI assistants now use a bottom-up algorithmic approach to manage component positioning when merging threat models. The system calculates container sizes from their children (85x85 for leaf components, calculated for containers), adds appropriate padding (40 pixels), and cascades size adjustments up nested hierarchies. This prevents cramped layouts in multi-level nested structures (component in component in component) by recalculating parent sizes when children are added.

### Fixed
- **Questionnaire Structure Documentation**: Fixed critical documentation bug where prompts showed questionnaire data structure using "steps" when it actually uses "groups". This caused AI assistants to fail parsing questionnaires because they couldn't find the questions. Added prominent warnings and correct examples showing `questionnaire.groups[].questions` is the correct path.

### Changed
- **Init Command**: Enhanced to support multi-repository workflows while maintaining backward compatibility
- **Documentation**: README updated with multi-repository examples and usage patterns

### Technical Details

**Use Cases Enabled:**
- Microservices architectures with separate service repositories
- Infrastructure-as-code (Terraform/CloudFormation) separate from application code
- Frontend/backend repository separation
- Platform services shared across multiple applications
- CI/CD and operational tooling as separate concerns

**Example Configuration:**
```json
{
  "name": "E-commerce Platform",
  "reference_id": "ecommerce-platform",
  "scope": "AWS infrastructure via Terraform. Provisions ECS for backend API 
           (api-backend repo), RDS PostgreSQL, ALB, CloudFront for frontend 
           (web-frontend repo). All application components from other repos 
           run within these AWS services."
}
```

See the Multi-Repository Threat Modeling section in the README for detailed examples and usage patterns.

## [0.3.0] - 2025-01-07

**Note**: Version 0.2.0 was skipped as it contained experimental features that were subsequently removed. This release builds directly on 0.1.1.

### Added

#### Questionnaire Support for Threat Model Refinement
- **Interactive Questionnaires**: Complete support for IriusRisk questionnaires that help refine threat models based on your actual implementation details
- **AI-Guided Completion**: When using the MCP integration, AI assistants can now analyze your source code and automatically answer questionnaire questions
- **Automatic Sync**: Questionnaire answers are downloaded during `iriusrisk sync` and pushed back to IriusRisk when you update them
- **Two Types Supported**: Both project-level (architecture) questionnaires and component-specific questionnaires

#### Automatic Threat Model Regeneration
- **Smart Updates**: The CLI now automatically triggers IriusRisk's rules engine to regenerate your threat model when needed (e.g., after answering questionnaires or making manual edits)
- **Seamless Integration**: Happens automatically during sync operations - no manual intervention required
- **Status Monitoring**: Actively monitors update completion to ensure your threat model is ready before proceeding

### Changed

#### Simplified OTM Import Workflow
- **No More Flags**: Removed the `--update` flag from `iriusrisk otm import` command
- **Automatic Detection**: The CLI now automatically detects whether you're creating a new project or updating an existing one
- **Smarter Behavior**: Import intelligently handles both scenarios without requiring you to specify intent

#### Enhanced Auto-Versioning
- **Proactive Backups**: Version snapshots are now created automatically *before* any update operation when auto-versioning is enabled
- **Consistent Behavior**: Auto-versioning works reliably across all import scenarios (CLI commands, MCP tools, project updates)
- **Better Project Tracking**: Project reference IDs from your local configuration now take priority, preventing accidental project disconnections

#### Improved CLI Display
- **Better Tables**: Enhanced table formatting for threat and countermeasure lists
- **Smarter Column Sizing**: Better handling of long text content in table displays
- **Clearer Output**: More readable information when working with threats and countermeasures

### Fixed

#### Critical Auto-Versioning Issues
- **Project Locking**: Fixed critical bugs that caused 401 authentication errors during OTM imports with auto-versioning enabled
- **Async Operations**: Corrected handling of IriusRisk's asynchronous operations - the CLI now properly waits for version creation to complete
- **Silent Failures**: Eliminated cases where version creation would fail silently and allow imports to proceed incorrectly
- **Status Polling**: Fixed project status checking to ensure projects are truly unlocked before attempting operations

#### MCP Workflow Improvements
- **Automatic Sync**: Fixed issue where AI assistants would ask permission instead of automatically completing sync operations
- **Project ID Preservation**: Prevented AI from accidentally modifying project IDs during troubleshooting, which would break connections to existing projects
- **Better Error Handling**: Improved error reporting and recovery in MCP tools

#### Threat Management
- **Status Validation**: Fixed validation of threat status changes to prevent invalid state transitions
- **Better Tracking**: Improved reliability of threat and countermeasure update tracking

## [0.1.1] - 2024-11-19

### Fixed
- **MCP Path Resolution**: Fixed critical issue where threat and countermeasure updates were being written to the user's home directory (`~/.iriusrisk/updates.json`) instead of the project directory. All MCP file operation functions now require explicit `project_path` parameter with validation, ensuring updates are tracked in the correct project location.
  - Updated `track_threat_update()`, `track_countermeasure_update()`, `create_countermeasure_issue()`, `get_pending_updates()`, `clear_updates()`, `show_diagram()`, and `generate_report()` to accept `project_path` parameter
  - Added path validation with clear error messages for invalid paths
  - Updated MCP manifest and AI prompts to reflect parameter changes
  - Removed unreliable `find_project_root()` fallback logic in favor of explicit paths

## [0.1.0] - 2024-11-12

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

[0.4.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.4.0
[0.3.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.3.0
[0.1.1]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.1.1
[0.1.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.1.0

