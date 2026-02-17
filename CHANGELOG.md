# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.1] - 2026-02-17

### Fixed

- **Project reference ID resolution** - Fixed a bug where the MCP `import_otm` tool could pick up the wrong `project.json` from an unrelated directory, causing the OTM project ID to be overwritten with a stale reference ID from a different project. The tool now reads project config only from the OTM file's own `.iriusrisk/` directory.
- **Removed global project discovery from all MCP tools** - MCP tools no longer search parent directories or `~/src/*` for `project.json`. Tools that need a project ID (`project_status`, `export_otm`, `list_project_versions`, `create_project_version`) now require it as a parameter. The AI reads `.iriusrisk/project.json` directly and passes the value.
- **OTM format preservation** - `_modify_otm_project_id` now preserves the original format (JSON stays JSON, YAML stays YAML) instead of converting everything to YAML via `yaml.dump`.
- **OTM import transport** - `import_otm_content` and `update_project_with_otm_content` now use multipart file upload (matching `import_otm_file`) instead of sending raw text with `Content-Type: text/plain`.

### Changed

- Updated `create_threat_model` and `initialize_iriusrisk_workflow` prompts to explicitly instruct AI to pass `reference_id` from `project.json` when calling `project_status()` and other tools.

## [0.6.0] - 2026-02-10

### Added

#### Agent Skills - Portable AI Workflows

**All MCP workflow prompts are now available as portable Agent Skills following the [Agent Skills open standard](https://agentskills.io).**

Agent Skills are portable, version-controlled packages that teach AI agents how to perform domain-specific tasks. They work across any agent that supports the standard (Cursor, Windsurf, Cline, etc.) and can be shared, versioned, and reused.

**Skills organized by LLM capability:**

**Reasoning Models** (complex analysis, multi-step workflows):
- `ci-cd-verification` - Orchestrate comprehensive CI/CD security reviews
- `compare-versions` - Compare threat model versions, interpret structured diffs
- `countermeasure-verification` - Verify security controls are correctly implemented in code

**General Models** (standard workflows for most LLMs):
- `architecture-design-review` - Architecture/design review trigger point
- `initialize-iriusrisk-workflow` - Complete workflow instructions for all IriusRisk operations
- `analyze-source-material` - Analyze repositories to extract components for threat modeling
- `create-threat-model` - Step-by-step OTM file creation with validation
- `threats-and-countermeasures` - Analyze threats/countermeasures, provide implementation guidance
- `security-development-advisor` - Help developers assess security impact

**Code-Focused** (heavy code analysis):
- `questionnaire-guidance` - Analyze source code to answer IriusRisk questionnaires

**Shared** (reference material for all models):
- `otm-layout-guidance` - Detailed OTM component layout and positioning guidance
- `otm-validation-guidance` - Validation rules for trust zones and component types

**Benefits:**
- **Portable**: Works across any agent supporting the Agent Skills standard
- **Version-controlled**: Skills are tracked in Git alongside code
- **Organized**: Categorized by model capability (reasoning, general, code-focused)
- **Discoverable**: Agents automatically find and apply skills based on context
- **Reusable**: Share skills across projects and teams

#### MCP Tool Filtering

**Control which MCP tools are exposed to AI clients by filtering based on categories or specific tool names.** Useful for reducing scope, using custom workflows, or exposing only specific functionality.

**Tool Categories:**
- `workflow` - AI workflow guidance and instructions (11 tools)
- `project` - Project management and data synchronization (5 tools)
- `threats-and-controls` - Threat and countermeasure tracking (5 tools)
- `questionnaires` - Questionnaire updates (2 tools)
- `reporting` - Report generation (2 tools)
- `versioning` - Version management and comparison (3 tools)
- `utility` - Utility functions (1 tool)

**Filtering Options:**
```bash
# Exclude workflow guidance tools
iriusrisk mcp --exclude-tags workflow

# Only expose project and reporting tools
iriusrisk mcp --include-tags project --include-tags reporting

# Exclude specific tools
iriusrisk mcp --exclude-tools sync --exclude-tools import_otm

# List all available tools and their categories
iriusrisk mcp --list-tools
```

**MCP Configuration Example:**
```json
{
  "mcpServers": {
    "iriusrisk-cli": {
      "command": "iriusrisk",
      "args": [
        "mcp",
        "--exclude-tags", "workflow"
      ]
    }
  }
}
```

**Use Cases:**
- Reduce tool scope for specific AI clients
- Use custom workflow instructions instead of built-in guidance
- Expose only reporting functionality for compliance teams
- Create specialized MCP configurations for different roles

## [0.5.5] - 2026-02-06

### Fixed

#### Improved Threat Model Creation Accuracy

**Problem:** The threat model creation prompt had grown too large, causing AI assistants to miss critical validation rules. This led to invalid OTM files where components were replaced with "empty-component" and trust zones were mapped incorrectly in IriusRisk.

**Solution:**
- Critical validation rules are now presented first, so AI assistants see them immediately
- Detailed layout and validation guidance has been split into separate on-demand tools (`otm_layout_guidance` and `otm_validation_guidance`), reducing cognitive load
- Overall prompt size reduced by 44%

**Result:** AI assistants now correctly use valid trust zone IDs and component types, producing OTM files that import cleanly into IriusRisk without component replacement or zone remapping issues.

## [0.5.4] - 2026-02-06

### Added

#### OTM Schema Validation

**Automatic validation against the official OTM JSON schema before import.** Catches structural issues early and prevents data loss from malformed OTM files.

- Validates against the official Open Threat Model schema (v0.2.0)
- Clear error messages showing exactly what's wrong and where
- Summary of OTM contents to help diagnose issues
- Graceful fallback if `jsonschema` package is not installed

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
- `jsonschema>=4.0.0`
- `pyyaml>=6.0.0` (now explicit)

#### Layout Reset Feature

**Reset diagram layout when importing OTM files.** Forces IriusRisk to auto-layout the diagram from scratch, useful when diagrams become messy after multiple updates or after major architectural changes.

**Usage:**

CLI flag:
```bash
iriusrisk otm import threat-model.otm --reset-layout
```

MCP parameter:
```python
import_otm(otm_file_path, reset_layout=True)
```

Config setting (in `project.json`):
```json
{
  "auto_reset_layout": false
}
```

The flag/parameter takes precedence over the config setting.

### Changed

#### Non-Interactive Init Command

Removed interactive scope prompts from `iriusrisk init`. The command no longer blocks waiting for input, making it safe for automated scripts and CI/CD pipelines.

```bash
# Runs non-interactively (no prompts)
iriusrisk init -r "my-project-ref"

# Scope is optional via flag
iriusrisk init -r "my-project-ref" --scope "AWS infrastructure"
```

## [0.5.3] - 2026-02-06

### Fixed

#### OTM File Management - Unified Workflow and File Location

**Critical improvements to how OTM files are managed:**

1. **All OTM files now stored in `.iriusrisk/` directory** - AI creates temporary files with clear naming (`temp-update-YYYYMMDD-HHMMSS.otm`), never in the repository root

2. **Mandatory sync before updates** - AI always runs `sync()` before any threat modeling operation, ensuring it has the latest state from IriusRisk

3. **Consistent merge logic** - Single-repo and multi-repo updates now use the same merge logic, always preserving existing components, their IDs, and layout positions

4. **Layout preservation** - Existing component positions are always preserved; new components are positioned to fit with the existing layout

## [0.5.2] - 2026-02-06

### Fixed

#### OTM File Management - Initial Files Are Temporary

**Problem:** When the AI created an initial OTM file and later updates were made in IriusRisk (questionnaires answered, threats marked, countermeasures implemented), the AI was reimporting the original stale OTM file, overwriting those changes.

**Solution:** Initial OTM files are now treated as one-time bootstrap files. After import, the AI always uses the authoritative `.iriusrisk/current-threat-model.otm` (downloaded by `sync()`) as the source for any updates, preventing data loss.

## [0.5.1] - 2026-02-04

### Fixed

- Updated threat model creation prompts to ignore deprecated components by default.

## [0.5.0] - 2026-01-27

### Added

#### CI/CD Drift Detection

Three new MCP tools for CI/CD security verification:

**`compare_versions`** - Compare any two threat model versions (or a version against the current state). Returns a structured diff showing changes to components, dataflows, trust zones, threats, and countermeasures.

**`countermeasure_verification`** - Verify that security controls are correctly implemented in code. Links issue tracker references to countermeasures and guides AI through implementation analysis.

**`ci_cd_verification`** - Orchestrates comprehensive security reviews by coordinating version comparison and countermeasure verification. Designed for use in CI/CD pipelines as a security gate.

**Comparison Modes:**
- Compare a specific version against the current project state (drift detection)
- Compare two versions against each other (historical audit)

**Use Cases:**
- Pre-deployment security gates in CI/CD pipelines
- Detecting architectural drift from the approved threat model
- Verifying security controls are implemented before release
- Compliance verification workflows

#### API Extensions for Version Comparison
- Retrieve diagram content (mxGraph format) from current project or specific versions
- Retrieve threats and countermeasures from specific version snapshots
- Update countermeasure test status (passed/failed) for control verification

## [0.4.0] - 2026-01-26

### Added

#### Multi-Repository Threat Modeling

Multiple repositories can now contribute to a single IriusRisk project, enabling comprehensive threat modeling for microservices, infrastructure-as-code, and distributed architectures.

- **Repository Scope Definitions**: New `scope` field in `.iriusrisk/project.json` lets each repository define its contribution to the unified threat model
- **Scope-Aware Init**: `iriusrisk init` supports a `--scope` parameter for defining repository contributions
- **OTM Export**: New `export_otm()` MCP tool for retrieving existing threat models, enabling intelligent merging across repositories
- **Automatic OTM Download**: `sync` now downloads the current threat model as `current-threat-model.otm`, making it immediately available for AI-assisted merging

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

**Use Cases:**
- Microservices architectures with separate service repositories
- Infrastructure-as-code (Terraform/CloudFormation) separate from application code
- Frontend/backend repository separation
- Platform services shared across multiple applications
- CI/CD and operational tooling as separate concerns

#### Threat Modeling Prompt Improvements
- Clarified that OTM tags should describe architecture and purpose, not vulnerabilities
- Prevents AI from cluttering diagrams with vulnerability labels like "sql-injection-vulnerable"

#### AI Workflow Enhancements
- AI assistants now proceed directly when users explicitly request threat modeling, eliminating unnecessary permission prompts
- Clear separation between "threat modeling" (architecture creation/update) and "threat analysis" (reviewing existing threats)
- Scope-based filtering shows only items relevant to the current repository when working in multi-repo projects
- Improved layout management with bottom-up size calculations for nested component hierarchies

### Fixed
- Fixed questionnaire parsing where prompts documented the wrong data structure, causing AI assistants to fail when reading questionnaires

## [0.3.0] - 2025-01-07

**Note**: Version 0.2.0 was skipped as it contained experimental features that were subsequently removed.

### Added

#### Questionnaire Support
- **Interactive Questionnaires**: Complete support for IriusRisk questionnaires that refine threat models based on your actual implementation details
- **AI-Guided Completion**: AI assistants can analyze your source code and automatically answer questionnaire questions via MCP
- **Automatic Sync**: Questionnaire answers are downloaded during `iriusrisk sync` and pushed back when updated
- **Two Types Supported**: Project-level (architecture) and component-specific questionnaires

#### Automatic Threat Model Regeneration
- IriusRisk's rules engine is automatically triggered to regenerate your threat model after questionnaire answers or manual edits
- Happens seamlessly during sync operations
- Status monitoring ensures the threat model is ready before proceeding

### Changed

#### Simplified OTM Import
- Removed the `--update` flag from `iriusrisk otm import`
- The CLI now automatically detects whether you're creating a new project or updating an existing one

#### Enhanced Auto-Versioning
- Version snapshots are now created automatically *before* any update operation
- Works reliably across all import scenarios (CLI commands, MCP tools, project updates)
- Project reference IDs from local configuration take priority, preventing accidental project disconnections

#### Improved CLI Display
- Better table formatting for threat and countermeasure lists
- Smarter column sizing for long text content

### Fixed

#### Auto-Versioning Reliability
- Fixed 401 authentication errors during OTM imports with auto-versioning enabled
- Corrected handling of asynchronous operations - the CLI now properly waits for version creation to complete
- Eliminated silent failures during version creation
- Fixed project status checking to ensure projects are unlocked before operations

#### MCP Workflow Fixes
- Fixed issue where AI assistants would ask permission instead of automatically completing sync operations
- Prevented AI from accidentally modifying project IDs during troubleshooting
- Improved error reporting and recovery in MCP tools

#### Threat Management
- Fixed validation of threat status changes to prevent invalid state transitions
- Improved reliability of threat and countermeasure update tracking

## [0.1.1] - 2024-11-19

### Fixed
- Fixed MCP file operations writing to the wrong directory. Threat and countermeasure updates were being saved to the home directory instead of the project directory. All MCP tools that write files now require an explicit `project_path` parameter.

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
- Full Model Context Protocol (MCP) server for AI assistant integration
- AI-guided threat modeling workflow
- Automated security analysis from source code
- OTM (Open Threat Model) file import/export
- Threat and countermeasure status tracking
- Diagram generation and visualization
- Custom prompt support for organization-specific requirements
- Security development advisor guidance
- Architecture and design review capabilities

#### Developer Experience
- Comprehensive test suite
- Flexible logging with verbosity controls
- Multiple output formats (table, JSON, CSV)
- Secure credential management
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

[0.6.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.6.0
[0.5.5]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.5.5
[0.5.4]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.5.4
[0.5.3]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.5.3
[0.5.2]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.5.2
[0.5.1]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.5.1
[0.5.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.5.0
[0.4.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.4.0
[0.3.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.3.0
[0.1.1]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.1.1
[0.1.0]: https://github.com/iriusrisk/iriusrisk_cli/releases/tag/v0.1.0
