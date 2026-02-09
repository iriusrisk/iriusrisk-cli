# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.5] - 2026-02-06

### Fixed

#### Prompt Optimization - Split Into Focused Tools

**Problem:** The `create_threat_model.md` prompt grew to 1,698 lines with 43 major sections, causing:
- AI attention degradation (critical validation rules buried at line 900+)
- Cognitive overload (too many concerns mixed together)
- Invalid OTM files (AI skipped validation, invented trust zone IDs and component types)
- Result: IriusRisk replaced components with "empty-component" and mapped zones incorrectly

**Solution - Two-Phase Approach:**

**Phase 1: Aggressive Condensing**
- Moved "🚨 CRITICAL VALIDATION RULES" to line 5 (immediately after title)
- Removed 351 lines of detailed layout algorithms (extracted to separate tool)
- Condensed "Critical Errors" section from 112 lines to 20 lines
- Condensed "Tags" section from 148 lines to 6 lines
- Reduced from 1,698 lines to 954 lines (44% reduction)

**Phase 2: Split Into Focused Tools**
- Created `otm_layout_guidance.md` (144 lines) - Positioning algorithms, size calculations, layout patterns
- Created `otm_validation_guidance.md` (220 lines) - Trust zone/component validation, filtering deprecated
- Added two new MCP tools: `otm_layout_guidance()` and `otm_validation_guidance()`
- AI calls these tools on-demand for detailed guidance

**New Structure:**
```
create_threat_model.md (954 lines)
├─ Critical validation rules (lines 5-24)
├─ Executive summary (lines 25-45)
├─ Quick workflow (lines 46-95)
├─ Common errors (condensed)
└─ References to specialized tools

otm_layout_guidance.md (144 lines)
└─ Detailed positioning algorithms

otm_validation_guidance.md (220 lines)
└─ Detailed validation examples
```

**Files Added:**
- `src/iriusrisk_cli/prompts/otm_layout_guidance.md` - Layout positioning guidance
- `src/iriusrisk_cli/prompts/otm_validation_guidance.md` - Validation guidance

**Files Updated:**
- `src/iriusrisk_cli/prompts/create_threat_model.md` - Reduced from 1,698 to 954 lines (44% reduction)
- `src/iriusrisk_cli/commands/mcp.py` - Added `otm_layout_guidance()` and `otm_validation_guidance()` tools

**Root Cause of Layout Problems:**

The layout itself isn't the problem - the problem is **invalid trust zone IDs and component types** that caused IriusRisk to replace components with "empty-component" and remap trust zones incorrectly. This made the carefully positioned layout meaningless.

**In the test case:**
- AI created layout (good)
- But used `"internet-tz"` instead of UUID `"b61d6911-338d-46a8-9f39-8dcd24abfe91"` (bad)
- And used `"CD-PYTHON-FLASK"` instead of correct referenceId (bad)
- IriusRisk couldn't find these, replaced with "empty-component" and wrong zones
- Result: Layout positions preserved but components in wrong zones

**Impact:** 
- AI sees critical validation rules immediately (line 5 vs line 900)
- Focused, modular prompts improve AI performance
- On-demand loading of detailed guidance reduces cognitive load
- **Validation rules are now followed correctly** (uses real UUIDs and referenceIds)
- Layout will work properly because components/zones will be correct

## [0.5.4] - 2026-02-06

### Added

#### OTM Schema Validation

**Automatic validation against official OTM JSON schema before import:**

Validates all OTM files against the official Open Threat Model JSON schema specification before import. This catches structural issues early and prevents data loss from malformed OTM files.

**Features:**
- Validates against official OTM schema (v0.2.0) from https://github.com/iriusrisk/OpenThreatModel
- Clear error messages showing exactly what's wrong and where
- Summary of OTM contents to help diagnose issues
- Graceful fallback if jsonschema package not available (logs warning)
- Validates before any modifications (layout reset, project ID override)

**Implementation:**
- `validate_otm_schema()` - Validates OTM content against JSON schema
- `get_otm_validation_summary()` - Provides overview of OTM contents
- Uses `jsonschema` library with Draft7Validator
- Schema file bundled with package: `src/iriusrisk_cli/otm_schema.json`

**Example validation error output:**
```
❌ OTM validation failed!

Validation errors:
  • At 'project': 'id' is a required property
  • At 'components -> 0': 'parent' is a required property
  • At 'dataflows -> 0 -> source': 'component-xyz' does not exist

OTM file summary:
  Project: My App (ID: None)
  Trust Zones: 2
  Components: 5
  Dataflows: 3
```

**Dependencies added:**
- `jsonschema>=4.0.0` - For JSON schema validation
- `pyyaml>=6.0.0` - For YAML parsing (already used, now explicit)

**Files Added:**
- `src/iriusrisk_cli/otm_schema.json` - Official OTM JSON schema

**Files Updated:**
- `src/iriusrisk_cli/utils/otm_utils.py` - Added validation functions
- `src/iriusrisk_cli/commands/otm.py` - Integrated validation before import
- `src/iriusrisk_cli/commands/mcp.py` - Integrated validation in MCP tool
- `setup.py` - Added jsonschema and pyyaml dependencies, included schema in package_data

**Impact:** Prevents import failures and data loss by catching OTM structural issues before they reach IriusRisk API. Clear error messages help users fix issues quickly.

#### Layout Reset Feature

**New capability to reset diagram layout when importing OTM files:**

Adds the ability to strip all layout/positioning data from OTM files before import, forcing IriusRisk to auto-layout the diagram from scratch. This is useful when diagrams become messy after multiple updates or when major architectural refactoring makes old positions irrelevant.

**Implementation:**

1. **New utility module** (`utils/otm_utils.py`):
   - `strip_layout_from_otm()` - Removes all `representation` sections from components, trust zones, and dataflows
   - `has_layout_data()` - Checks if OTM contains layout data
   - Uses PyYAML for proper parsing when available, falls back to regex

2. **CLI flag** (`--reset-layout`):
   ```bash
   iriusrisk otm import threat-model.otm --reset-layout
   ```

3. **MCP parameter** (`reset_layout`):
   ```python
   import_otm(otm_file_path, reset_layout=True)
   ```

4. **Config setting** (`auto_reset_layout` in project.json):
   ```json
   {
     "auto_reset_layout": false  // Set to true for automatic reset on all imports
   }
   ```

**Priority:** Parameter/flag takes precedence over config setting.

**Use cases:**
- Diagram has become messy after multiple updates
- Major architectural refactoring
- Want IriusRisk's auto-layout to reorganize everything
- Testing/debugging with fresh layout

**Files Added:**
- `src/iriusrisk_cli/utils/otm_utils.py` - New utility module for OTM manipulation

**Files Updated:**
- `src/iriusrisk_cli/commands/otm.py` - Added `--reset-layout` flag and logic
- `src/iriusrisk_cli/commands/mcp.py` - Added `reset_layout` parameter to `import_otm()` tool
- `src/iriusrisk_cli/prompts/create_threat_model.md` - Documented layout reset behavior
- `README.md` - Added Layout Reset Feature section with examples

**Impact:** Provides "escape hatch" for messy layouts while preserving architectural structure. Opt-in feature doesn't change default behavior.

### Changed

#### Non-Interactive Init Command

**Removed interactive scope prompts from `iriusrisk init` command:**

Previously, if `--scope` flag was not provided, the command would prompt for scope input from stdin. This caused issues for:
- Automated scripts and CI/CD pipelines
- Non-interactive environments
- Users who just wanted to skip scope definition

**Changes:**
- Removed `click.prompt()` calls for scope input
- Scope is now purely optional via `--scope` flag
- Command runs non-interactively when scope not provided
- No blocking prompts requiring Enter key

**Examples:**
```bash
# Now runs non-interactively (no prompts)
iriusrisk init -r "my-project-ref"

# Scope is optional via flag
iriusrisk init -r "my-project-ref" --scope "AWS infrastructure"
```

**Files Updated:**
- `src/iriusrisk_cli/commands/init.py` - Removed interactive scope prompts (lines 119-136, 179-190)

**Impact:** Enables automation and CI/CD usage without blocking on stdin prompts.

## [0.5.3] - 2026-02-06

### Fixed

#### OTM File Management - Unified Workflow and File Location

**Critical improvements to OTM file handling:**

1. **All OTM files now in `.iriusrisk/` directory**
   - AI creates temporary files with clear naming: `.iriusrisk/temp-update-YYYYMMDD-HHMMSS.otm`
   - Never creates files in repository root
   - Prevents confusion about which files are temporary vs authoritative

2. **Mandatory sync() first**
   - AI ALWAYS runs `sync()` before any threat modeling operation
   - Ensures it has the latest state from IriusRisk
   - Downloads `.iriusrisk/current-threat-model.otm` if project exists

3. **Identical merge logic for ALL updates**
   - Single-repo updates use SAME logic as multi-repo contributions
   - Always preserves existing components and their IDs
   - Always preserves layout positions (x, y, width, height)
   - Adds new components with calculated positions
   - Recalculates parent container sizes when needed

4. **Layout preservation**
   - Existing component positions are ALWAYS preserved
   - New components are positioned to fit with existing layout
   - Parent container sizes are recalculated bottom-up
   - Maintains visual consistency across updates

**Files Updated:**
- `src/iriusrisk_cli/prompts/create_threat_model.md` - Complete rewrite of OTM file management section, added "ALWAYS sync() first" requirement, unified merge logic
- `src/iriusrisk_cli/prompts/initialize_iriusrisk_workflow.md` - Updated workflow to mandate sync() first, clarified file locations and naming
- `README.md` - Updated OTM File Management Best Practices with new workflow

**Impact:** 
- Prevents data loss by ensuring latest state is always used
- Eliminates confusion about file locations and naming
- Ensures consistent behavior whether updating single-repo or multi-repo
- Preserves visual layout consistency

## [0.5.2] - 2026-02-06

### Fixed

#### OTM File Management - Initial Files Are Temporary

**Problem**: When AI created an initial OTM file in the repository root (e.g., `threat-model.otm`) and then updates were made to the threat model in IriusRisk (questionnaires answered, threats marked, countermeasures implemented), the AI was updating and reimporting the original OTM file. This caused data loss by overwriting IriusRisk changes with stale data.

**Solution**: Updated all prompt files and documentation to clarify that initial OTM files are **temporary bootstrap files** that become obsolete after import. The AI now:
- Treats initial OTM files as one-time-use bootstrap files
- Always uses `.iriusrisk/current-threat-model.otm` (downloaded by `sync()`) as the authoritative source for updates
- Never updates or reads the original OTM file after initial import
- Creates new OTM files for each update instead of overwriting the original

**Files Updated**:
- `src/iriusrisk_cli/prompts/create_threat_model.md` - Added "🚨 CRITICAL: Initial OTM Files Are Temporary" section with detailed workflow guidance
- `src/iriusrisk_cli/prompts/initialize_iriusrisk_workflow.md` - Added "🚨 CRITICAL: OTM File Management" section with correct/wrong workflow examples
- `README.md` - Added "OTM File Management Best Practices" section with user-facing guidance

**Impact**: Prevents data loss when updating threat models. Changes made in IriusRisk (questionnaires, threat status, countermeasures) are now preserved during AI-driven updates.

## [0.5.1] - 2026-02-04

Updated create_threat_model prompt to ignore deprecated components by default.

## [0.5.0] - 2026-01-27

### Added

#### CI/CD Drift Detection - Three-Tool Architecture

**1. `compare_versions` - Pure Comparison Tool**
- Compare any two threat model versions (or version vs current)
- Returns structured JSON diff showing architectural and security changes
- Detects components, dataflows, trust zones, threats, and countermeasures changes
- Data-focused tool for direct version comparison

**2. `countermeasure_verification` - Control Implementation Checker**
- Verify security controls are correctly implemented in code
- Links issue tracker references to countermeasures
- Guides AI through implementation analysis workflow
- Updates countermeasure test status (passed/failed) via API

**3. `ci_cd_verification` - Orchestration Workflow**
- Meta-tool that coordinates comprehensive security reviews
- Calls compare_versions + countermeasure_verification as needed
- Provides workflow guidance for CI/CD pipelines
- Generates unified security reports
- **Version-Based Comparison**: Compare threat model versions to identify architectural and security changes
- **Diagram Comparison**: Parse mxGraph XML diagrams to detect component, dataflow, and trust zone changes
- **Security Comparison**: Compare threats and countermeasures JSON to identify new threats, severity increases, and countermeasure removals
- **Structured Diff Output**: Python tool performs all parsing and comparison, returning structured JSON diff for AI interpretation
- **Verification Manager**: Context manager for safe download, comparison, and cleanup of temporary verification files
- **Multiple Comparison Modes**: 
  - Mode 3: Compare specific version against current project state (drift detection)
  - Mode 4: Compare two versions (historical audit)
- **AI Guidance**: Comprehensive prompt (`ci_cd_verification.md`) guides AI assistants on interpreting comparison results and generating human-readable reports

#### API Client Extensions
- **Diagram Content Retrieval**: New `get_diagram_content()` method retrieves diagram XML (mxGraph format) from current project
- **Version-Specific Diagram**: New `get_diagram_content_version()` method retrieves diagram XML from specific version snapshots
- **Version-Specific Threats**: New `get_threats_version()` method retrieves threats from specific version snapshots
- **Version-Specific Countermeasures**: New `get_countermeasures_version()` method retrieves countermeasures from specific version snapshots
- **Countermeasure Test Updates**: New `update_countermeasure_test()` method updates test status (passed/failed) for control verification

#### Utilities
- **Diagram Comparison** (`utils/diagram_comparison.py`): Parse and compare mxGraph XML diagrams
- **Threat Comparison** (`utils/threat_comparison.py`): Parse and compare threats/countermeasures JSON
- **Verification Manager** (`utils/verification_manager.py`): Manage verification workspace, downloads, and cleanup

### Technical Details

**Comparison Workflow:**
1. Download baseline and target states (diagram XML, threats JSON, countermeasures JSON)
2. Parse diagram XML to extract components, dataflows, trust zones
3. Compare baseline vs target to identify added/removed/modified elements
4. Return structured JSON diff with comprehensive metadata

**Tool Separation:**
- **compare_versions**: Pure comparison - downloads, parses, diffs, returns structured results
- **countermeasure_verification**: Control validation - guides AI through implementation verification
- **ci_cd_verification**: Orchestrator - coordinates full security review workflow

**Python Tool Responsibilities:**
- All deterministic operations (downloading, parsing, comparing)
- XML/JSON parsing and structural comparison
- Workspace management and file preservation
- API methods for test status updates

**AI Assistant Responsibilities:**
- Interpret structured diff results
- Verify control implementations in code
- Assess security implications of changes
- Generate human-readable reports
- Make recommendations for security team review

**Use Cases:**
- **compare_versions**: Direct version comparison, drift detection, historical audits
- **countermeasure_verification**: PR control verification, security fix validation
- **ci_cd_verification**: Complete CI/CD security gates, comprehensive pre-deployment reviews
- Compliance verification workflows

## [0.4.0] - 2026-01-26

### Added

#### Multi-Repository Threat Modeling
- **Repository Scope Definitions**: New `scope` field in `.iriusrisk/project.json` allows repositories to define their contribution to a unified threat model
- **Multi-Repo Support**: Multiple repositories can now contribute to a single IriusRisk project, enabling comprehensive threat modeling for microservices, infrastructure-as-code, and distributed architectures
- **Scope-Aware Init Command**: `iriusrisk init` now supports `--scope` parameter for defining repository contributions
- **Interactive Scope Prompting**: When connecting to existing projects, users are prompted to define how their repository contributes
- **OTM Export MCP Tool**: New `export_otm()` MCP tool enables AI assistants to retrieve existing threat models for intelligent merging
- **Config Scope Support**: `Config.get_project_scope()` method for reading scope definitions

#### Threat Modeling Prompt Improvements
- **Tag Usage Clarification**: Added comprehensive guidance on proper tag usage in OTM files
- **Architectural Tags Only**: Clear rules that tags describe architecture/purpose, NOT vulnerabilities
- **Vulnerability Tag Prohibition**: Explicit examples of what NOT to tag (sql-injection-vulnerable, etc.)
- **Tag Pollution Prevention**: Guidance prevents AI from cluttering diagrams with vulnerability labels
- **Updated Prompts**: `create_threat_model.md` and `analyze_source_material.md` with tag best practices

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

