# IriusRisk CLI

An AI-powered threat modeling integration that brings IriusRisk security analysis directly into your development workflow. Designed primarily for use with AI-enabled IDEs through MCP (Model Context Protocol), this tool enables AI assistants to help you create threat models, analyze security risks, and implement countermeasures seamlessly within your coding environment.

> :warning: This software has been released IriusRisk Labs as public beta. It is provided as-is, without warranty or guarantee of any kind. Features may change, data structures may evolve, and occasional issues should be expected. Use at your own discretion.

> 🎉 **What's New in v0.3.0**: Questionnaire support for AI-guided threat model refinement, automatic threat model regeneration, simplified OTM import workflow, and enhanced auto-versioning. See [CHANGELOG.md](CHANGELOG.md) for full details.

## Primary Use Case: AI-Enabled IDE Integration

This tool is designed to work alongside AI assistants in your IDE, enabling:

- **AI-Guided Threat Modeling**: Let AI assistants analyze your code and automatically create comprehensive threat models
- **Intelligent Security Analysis**: Get AI-powered insights on threats and countermeasures specific to your codebase
- **Contextual Security Recommendations**: Receive security guidance based on your actual code changes and architecture
- **Automated Security Workflows**: Have AI assistants track threat status, implement countermeasures, and generate reports

## What You Can Do

- **Manage Projects**: List, view, and analyze your IriusRisk projects
- **Import/Export Threat Models**: Use OTM (Open Threat Model) format to create and update projects
- **Sync Project Data**: Download threats, countermeasures, questionnaires, and components locally
- **Answer Questionnaires**: Refine threat models by answering project and component questionnaires
- **Analyze Threats**: View, filter, search, and update threat status
- **Track Countermeasures**: Monitor implementation, update status, and create tracking issues
- **Manage Components**: View and search system components in your architecture
- **Generate Reports**: Create compliance and security reports in multiple formats (PDF, HTML, XLSX, CSV)
- **Version Control**: Create snapshots of your threat models to track changes over time
- **Issue Tracker Integration**: Connect countermeasures to your issue tracking system
- **Automate Workflows**: Script security processes with consistent CLI commands
- **MCP Integration**: Enable AI assistants to perform all operations through Model Context Protocol

## Key Features

### 🆕 Questionnaire-Driven Threat Model Refinement (v0.3.0)

IriusRisk questionnaires help refine your threat model based on your actual implementation details. The CLI downloads questionnaires during sync operations, and when using the MCP integration, AI assistants can analyze your source code to automatically answer these questions. Your answers trigger IriusRisk's rules engine to regenerate your threat model with more accurate, context-specific threats and countermeasures.

**How it works**:
1. Import or create your initial threat model
2. Run `iriusrisk sync` to download questionnaires
3. AI assistant analyzes your code and answers the questions
4. Sync automatically pushes answers back to IriusRisk
5. IriusRisk regenerates your threat model based on actual implementation

### 🔄 Automatic Threat Model Regeneration (v0.3.0)

The CLI now automatically triggers IriusRisk's rules engine to regenerate your threat model when needed—after answering questionnaires, making manual edits, or updating your architecture. The CLI monitors the regeneration process to ensure your threat model is ready before proceeding. This happens seamlessly during sync operations without manual intervention.

### 📦 Simplified OTM Import Workflow (v0.3.0)

The `iriusrisk otm import` command now automatically detects whether you're creating a new project or updating an existing one—no flags required. Just import your OTM file and the CLI handles the rest intelligently.

### 💾 Enhanced Auto-Versioning (v0.3.0)

When auto-versioning is enabled in your project configuration, the CLI automatically creates backup snapshots **before** any update operation. This ensures you can always roll back changes and track your threat model's evolution over time. Auto-versioning works consistently across all import scenarios (CLI commands, MCP tools, project updates).

**Enable auto-versioning** in `.iriusrisk/project.json`:
```json
{
  "auto_version": true,
  "auto_version_prefix": "auto-backup-"
}
```

### 🤖 AI-Powered Security Analysis

Through MCP integration, AI assistants can analyze your codebase, create threat models, answer questionnaires, implement countermeasures, and track progress—all within your IDE. The AI understands your code context and provides intelligent, specific security guidance.

# MCP Integration for AI-Enabled IDEs

## Setting Up MCP Integration

The IriusRisk CLI is designed to work with AI assistants through MCP (Model Context Protocol). This enables your AI assistant to:

- Analyze your codebase and create threat models automatically
- Provide security recommendations based on your specific code
- Track and update threat and countermeasure status
- Generate security reports and documentation

### Configuration for MCP

1. Install the IriusRisk CLI (see installation instructions below)
2. Configure your IriusRisk connection with environment variables
3. Your AI assistant will automatically detect and use the MCP integration

### AI Assistant Capabilities

When integrated through MCP, AI assistants can:

- **Analyze Source Code**: Examine your application code, infrastructure, and documentation to identify security-relevant components
- **Create Threat Models**: Generate comprehensive OTM (Open Threat Model) files from your codebase
- **Import to IriusRisk**: Automatically upload threat models to IriusRisk for professional analysis
- **Answer Questionnaires**: Analyze your code to answer project and component questionnaires, refining the threat model based on actual implementation details
- **Review Threats**: Help you understand and prioritize security threats identified by IriusRisk
- **Implement Countermeasures**: Guide you through implementing security controls and track their status
- **Sync Changes**: Automatically synchronize threat model updates between your local environment and IriusRisk
- **Generate Reports**: Create compliance reports and security documentation

## Example AI Workflow

1. **Code Analysis**: "Analyze my web application for security threats"
2. **Threat Model Creation**: AI examines your code and creates a comprehensive threat model
3. **IriusRisk Integration**: Threat model is uploaded to IriusRisk for professional analysis
4. **Questionnaire Completion**: AI analyzes your code to answer questionnaires, refining the threat model based on actual implementation
5. **Threat Review**: AI helps you understand the identified threats and their priorities
6. **Implementation Guidance**: AI guides you through implementing security countermeasures
7. **Status Tracking**: Progress is tracked and synchronized with IriusRisk
8. **Report Generation**: Compliance and security reports are generated automatically

# Using the CLI

## Installation

### From PyPI

Eventually users will be able to install the CLI using:

```bash
$ pip install iriusrisk-cli
```

For Mac users using Homebrew, we suggest installing it with:

```bash
$ pipx install iriusrisk-cli
```

### For Development

Clone this repository and install in development mode:

```bash
$ git clone <repository-url>

$ cd iriusrisk_cli
$ pip install -e .
```


## Configuration

Before using the CLI, you need to configure your IriusRisk connection. The CLI supports multiple configuration methods with a clear priority order.

### Recommended: User-Level Configuration

Set up your credentials once for use across all projects:

```bash
# Set your default IriusRisk hostname
iriusrisk config set-hostname https://your-instance.iriusrisk.com

# Set your API key (prompts securely, not stored in shell history)
iriusrisk config set-api-key

# View your current configuration
iriusrisk config show
```

This approach:
- Keeps your API key secure (not in project files)
- Works across all projects automatically
- Can be overridden per-project or per-session

### Configuration Priority

The CLI checks configuration sources in this order (highest to lowest):

1. **Environment variables** - `IRIUS_HOSTNAME` and `IRIUS_API_KEY` (or `IRIUS_API_TOKEN`)
2. **Project .env file** - `.env` in your project directory
3. **Project config** - `.iriusrisk/project.json` (hostname only, never API credentials)
4. **User config** - `~/.iriusrisk/config.json` (set via `iriusrisk config` commands)

Each setting is resolved independently, so you can mix sources (e.g., API key from user config, hostname from environment variable).

### Alternative Configuration Methods

#### Option 2: Project .env file

Create a `.env` file in your project directory:

```bash
cat > .env << EOF
IRIUS_HOSTNAME=https://your-instance.iriusrisk.com
IRIUS_API_KEY=your-api-token-here
EOF
```

**Warning**: If using `.env` files, add them to `.gitignore` to avoid committing credentials.

#### Option 3: Environment variables

```bash
export IRIUS_HOSTNAME=https://your-instance.iriusrisk.com
export IRIUS_API_KEY=your-api-token-here
```

#### Option 4: Project-specific hostname

For teams working with different IriusRisk instances, you can set a hostname in the project config:

```bash
# Manually edit .iriusrisk/project.json and add:
{
  "hostname": "https://dev-instance.iriusrisk.com",
  "project_id": "...",
  ...
}
```

**Note**: API credentials should never be stored in project config files.

## Logging and Output Control

The IriusRisk CLI provides flexible logging options to control output verbosity:

### Default Behavior
By default, the CLI operates quietly with minimal output - only showing command results and critical errors.

### Logging Options

```bash
# Enable verbose output (shows progress and status messages)
iriusrisk --verbose project list

# Enable debug output (shows detailed API calls and timing)
iriusrisk --debug project list

# Suppress all non-essential output (quiet mode)
iriusrisk --quiet project list

# Write logs to a specific file
iriusrisk --log-file debug.log --debug project list

# Set specific log level
iriusrisk --log-level INFO project list
```

### Environment Variables
You can also control logging through environment variables:

```bash
# Enable debug mode
export IRIUSRISK_DEBUG=1

# Set log file path
export IRIUSRISK_LOG_FILE=debug.log
```

### Output Destinations
- **stdout**: Command results and data (for piping/redirection)
- **stderr**: Status messages, progress, warnings, errors, debug info
- **Log files**: Only when explicitly requested via `--log-file`

## Testing API Connection

After configuration, test your connection to ensure everything is working correctly:

```bash
# Test your IriusRisk connection
iriusrisk test
```

This command will:
- Test connectivity to your IriusRisk instance
- Verify your authentication credentials
- Display your IriusRisk version information

Example output:
```
Testing connection to IriusRisk...
✓ Connection successful!
✓ IriusRisk version: 4.47.19-0-g41bcb27de1f-30/09/2025 17:48
```

If the test fails, it will provide specific error information to help you troubleshoot configuration issues.

## Getting help

Users can get help using the following commands:

```bash
$ iriusrisk help    # Detailed help with examples and configuration
$ iriusrisk --help  # Basic command help
$ iriusrisk --version  # Show version information
```

## Quick Start

After installation and configuration:

```bash
# Test the installation
$ iriusrisk --version

# Test your API connection
$ iriusrisk test

# Get detailed help
$ iriusrisk help

# Basic help
$ iriusrisk --help

# List projects
$ iriusrisk project list

# List projects with filtering
$ iriusrisk project list --name "web" --format json
```

## Available Commands

### Project Initialization

Initialize a new project or connect to an existing one:

```bash
# Initialize new project interactively
$ iriusrisk init

# Initialize with specific name
$ iriusrisk init -n "My Web Application"

# Initialize with name and project ID
$ iriusrisk init -n "My App" -p abc123

# Connect to existing project by reference ID
$ iriusrisk init -r "my-project-ref"

# Overwrite existing configuration
$ iriusrisk init --force
```

### Projects

```bash
# List all projects
$ iriusrisk project list

# List projects with pagination
$ iriusrisk project list --page 1 --size 10

# Filter by name (partial match)
$ iriusrisk project list --name "web application"

# Filter by tags
$ iriusrisk project list --tags "production critical"

# Filter by workflow state
$ iriusrisk project list --workflow-state "in-progress"

# Show only non-archived projects
$ iriusrisk project list --not-archived

# Include version information
$ iriusrisk project list --include-versions

# Output as JSON
$ iriusrisk project list --format json

# Output as CSV
$ iriusrisk project list --format csv

# Advanced filtering with custom expressions
$ iriusrisk project list --filter "'name'~'web':AND:'tags'~'prod'"

# Show detailed project information
$ iriusrisk project show <project_id>

# Show project info as JSON
$ iriusrisk project show <project_id> --format json
```

### OTM (Open Threat Model) Import/Export

Work with threat models using the standard OTM format:

```bash
# Generate example OTM file for reference
$ iriusrisk otm example

# Import OTM file (automatically creates new or updates existing project)
$ iriusrisk otm import example.otm

# Import with JSON output
$ iriusrisk otm import example.otm --format json

# Export project as OTM format
$ iriusrisk otm export PROJECT_ID

# Export to specific file
$ iriusrisk otm export PROJECT_ID -o threat-model.otm

# Export as JSON
$ iriusrisk otm export PROJECT_ID --format json
```

**Note**: The CLI automatically detects whether you're creating a new project or updating an existing one during import. If auto-versioning is enabled in your project configuration, a backup snapshot is automatically created before updates.

### Data Synchronization

Sync threat model data between IriusRisk and your local environment:

```bash
# Sync all data from default project
$ iriusrisk sync

# Sync specific project
$ iriusrisk sync <project_id>

# Sync only threats
$ iriusrisk sync --threats-only

# Sync only countermeasures
$ iriusrisk sync --countermeasures-only

# Sync only questionnaires
$ iriusrisk sync --questionnaires-only

# Sync only components
$ iriusrisk sync --components-only

# Sync to custom output directory
$ iriusrisk sync -o /path/to/output
```

The sync command downloads:
- **Threats**: All identified security threats for your project
- **Countermeasures**: Security controls and their implementation status
- **Questionnaires**: Questions to refine your threat model based on implementation details
- **Components**: System components from the IriusRisk library and your architecture

Data is saved to `.iriusrisk/` directory by default and can be used for offline analysis or AI-assisted review.

### Questionnaires

**New in 0.3.0**: Questionnaires help refine your threat model based on actual implementation details.

```bash
# Download questionnaires during sync
$ iriusrisk sync

# View questionnaires in .iriusrisk/questionnaires.json
```

Questionnaires are automatically downloaded during sync operations. When using the MCP integration, AI assistants can analyze your source code and automatically answer these questions, triggering IriusRisk's rules engine to regenerate your threat model with more accurate threats and countermeasures.

**How it works**:
1. Import or create a threat model
2. Run `iriusrisk sync` to download questionnaires
3. AI assistant analyzes your code to answer questions
4. Sync pushes answers back to IriusRisk
5. IriusRisk automatically regenerates threat model based on answers

### Threats

```bash
# List all threats from default project
$ iriusrisk threat list

# List threats from specific project
$ iriusrisk threat list <project_id>

# Show detailed threat information
$ iriusrisk threat show <threat_id>

# Search threats by keyword
$ iriusrisk threat search "SQL injection"

# Search with project specification
$ iriusrisk threat search "XSS" --project-id <project_id>

# Update threat status
$ iriusrisk threat update <threat_id> --status accept --reason "Mitigated by WAF"

# List threats with specific status
$ iriusrisk threat list --status required

# Output as JSON or CSV
$ iriusrisk threat list --format json
```

**Available threat statuses**: `required`, `recommended`, `accept`, `expose`, `not-applicable`

### Countermeasures

```bash
# List all countermeasures from default project
$ iriusrisk countermeasure list

# List countermeasures from specific project
$ iriusrisk countermeasure list <project_id>

# Show detailed countermeasure information
$ iriusrisk countermeasure show <countermeasure_id>

# Search countermeasures by keyword
$ iriusrisk countermeasure search "authentication"

# Update countermeasure status
$ iriusrisk countermeasure update <cm_id> --status implemented

# Create issue tracker ticket for countermeasure
$ iriusrisk countermeasure create-issue <cm_id>

# Create issue with specific tracker
$ iriusrisk countermeasure create-issue <cm_id> --tracker "Jira"

# List countermeasures by status
$ iriusrisk countermeasure list --status required

# Output as JSON or CSV
$ iriusrisk countermeasure list --format json
```

**Available countermeasure statuses**: `required`, `recommended`, `implemented`, `rejected`, `not-applicable`

### Components

View and search system components in your architecture:

```bash
# List all components
$ iriusrisk component list

# List components from specific project
$ iriusrisk component list <project_id>

# Show detailed component information
$ iriusrisk component show <component_id>

# Search components by keyword
$ iriusrisk component search "database"

# Filter by category
$ iriusrisk component list --category "Database"

# Filter by type
$ iriusrisk component list --type "project-component"

# Output as JSON
$ iriusrisk component list --format json
```

### Reports

Generate security and compliance reports:

```bash
# Generate default countermeasure report (PDF)
$ iriusrisk reports generate

# Generate threat report
$ iriusrisk reports generate --type threat

# Generate compliance report
$ iriusrisk reports generate --type compliance --standard owasp-top-10-2021

# Generate report in different format
$ iriusrisk reports generate --format html

# Save to specific location
$ iriusrisk reports generate -o /path/to/report.pdf

# List available report types
$ iriusrisk reports types

# List available compliance standards
$ iriusrisk reports standards

# List generated reports
$ iriusrisk reports list
```

**Available report types**: `countermeasure`, `threat`, `compliance`, `risk-summary`

**Available formats**: `pdf`, `html`, `xlsx`, `csv`, `xls`

### Project Versions

**New in 0.3.0**: Enhanced auto-versioning creates backup snapshots before updates.

```bash
# Create a version snapshot
$ iriusrisk project versions create "v1.0" --description "Initial release"

# List all versions for a project
$ iriusrisk project versions list

# List versions for specific project
$ iriusrisk project versions list <project_id>

# Show version details
$ iriusrisk project versions show <version_id>

# Compare two versions
$ iriusrisk project versions compare <version_id_1> <version_id_2>
```

**Auto-versioning**: Enable in `.iriusrisk/project.json`:

```json
{
  "auto_version": true,
  "auto_version_prefix": "auto-backup-"
}
```

When enabled, the CLI automatically creates version snapshots before OTM imports and updates, protecting your work.

### Updates Tracking

Track threat and countermeasure status changes before syncing to IriusRisk:

```bash
# View pending updates
$ iriusrisk updates show

# View updates for specific project
$ iriusrisk updates show <project_id>

# Clear all pending updates
$ iriusrisk updates clear

# Clear updates for specific project
$ iriusrisk updates clear <project_id>
```

Updates are tracked locally in `.iriusrisk/updates.json` and applied when you run sync commands or use MCP tools.

### Issue Tracker Integration

Connect countermeasures to your issue tracking system:

```bash
# List available issue tracker profiles
$ iriusrisk issue-tracker list

# Show issue tracker details
$ iriusrisk issue-tracker show <tracker-id>

# Set default issue tracker for project
$ iriusrisk issue-tracker set-default <tracker-name>

# Create issue for countermeasure (uses default tracker)
$ iriusrisk countermeasure create-issue <countermeasure_id>

# Create issue with specific tracker
$ iriusrisk countermeasure create-issue <cm_id> --tracker "Jira Production"
```

### MCP (Model Context Protocol)
```bash
# Generate example mcp.json configuration file
$ iriusrisk mcp-example

# Save mcp.json configuration to file
$ iriusrisk mcp-example > mcp.json
```

The `mcp-example` command generates a configuration file that can be used to set up the IriusRisk CLI as an MCP server for AI integration tools like Claude Desktop. The `iriusrisk mcp` command is not run directly by users - it's automatically invoked by AI tools through the MCP stdio transport when configured properly.

The generated configuration looks like:

```json
{
  "mcpServers": {
    "iriusrisk-cli": {
      "command": "iriusrisk",
      "args": [
        "mcp"
      ]
    }
  }
}
```

### Customizing MCP Prompts

You can customize the prompts that MCP tools provide to AI assistants by adding a `prompts` section to your `.iriusrisk/project.json` file. This allows you to add organization-specific security standards, compliance requirements, or technology constraints.

#### Inline String Customization

For short customizations, use strings directly in the configuration:

```json
{
  "name": "my-project",
  "project_id": "abc-123",
  "prompts": {
    "threats_and_countermeasures": {
      "prefix": "Organization Security Standards:\n- All implementations must use approved cryptography libraries\n- Follow ACME Corp Secure Coding Guidelines\n\n"
    },
    "security_development_advisor": {
      "postfix": "\n\nCompliance Note: This is a HIPAA-regulated application."
    }
  }
}
```

#### File-Based Customization

For complex or lengthy customizations, reference external files. Files are resolved relative to the `.iriusrisk` directory:

```json
{
  "name": "my-project",
  "project_id": "abc-123",
  "prompts": {
    "threats_and_countermeasures": {
      "prefix": {"file": "custom_prompts/threat_standards.md"}
    },
    "create_threat_model": {
      "replace": {"file": "custom_prompts/custom_workflow.md"}
    }
  }
}
```

**File path resolution:**
- Relative paths: Resolved from `.iriusrisk/` directory (e.g., `"custom_prompts/file.md"` → `.iriusrisk/custom_prompts/file.md`)
- Absolute paths: Used as-is (e.g., `"/path/to/file.md"`)

**Example directory structure:**
```
project/
├── .iriusrisk/
│   ├── project.json
│   └── custom_prompts/
│       ├── threat_standards.md
│       └── custom_workflow.md
```

#### Mixing String and File Customizations

You can combine inline strings and file references:

```json
{
  "prompts": {
    "threats_and_countermeasures": {
      "prefix": "Quick note: Check OWASP Top 10\n\n",
      "postfix": {"file": "custom_prompts/additional_guidelines.md"}
    }
  }
}
```

**Available actions:**
- `prefix` - Add text before the default prompt
- `postfix` - Add text after the default prompt  
- `replace` - Completely replace the default prompt

Each action accepts either:
- A string value (used directly)
- A dict with `file` key (loaded from file)

**Customizable tools:**
- `initialize_iriusrisk_workflow`
- `threats_and_countermeasures`
- `analyze_source_material`
- `create_threat_model`
- `architecture_and_design_review`
- `security_development_advisor`

## Planned Commands

These commands may be added in future versions:

```bash
$ iriusrisk threat list --top-10         # Filter to top 10 highest risk threats
$ iriusrisk countermeasure list --top-10 # Filter to top 10 highest priority countermeasures
```

Most planned features have been implemented. See the [CHANGELOG.md](CHANGELOG.md) for details on recent additions.

# API

## Authentication

Authentication is done using an API key. Configuration can be set via:

1. User config: `iriusrisk config set-hostname` and `iriusrisk config set-api-key`
2. Environment variables: `IRIUS_HOSTNAME` and `IRIUS_API_KEY` (or `IRIUS_API_TOKEN`)
3. Project .env file
4. Project config (hostname only)

See the Configuration section above for detailed setup instructions.



## Getting Help

- **MCP Integration**: The primary use case is through AI-enabled IDEs with MCP integration
- **CLI Usage**: Direct command-line usage is also supported for scripting and automation
- **Issues**: Report bugs and request features via GitHub Issues
- **Contributing**: See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for setup and contribution guidelines

## Architecture

This tool serves as a bridge between your development environment and IriusRisk's professional threat modeling platform:

```
Your IDE + AI Assistant
         ↓ (MCP)
    IriusRisk CLI
         ↓ (REST API)
    IriusRisk Platform
```

The MCP integration enables AI assistants to understand your code context and provide intelligent security guidance, while the CLI provides the underlying functionality for both interactive and automated use cases.
