"""MCP (Model Context Protocol) command for IriusRisk CLI."""

import click
import asyncio
import sys
import logging
from typing import Any
from mcp.server.fastmcp import FastMCP
from .. import __version__
from ..cli_context import pass_cli_context
from .sync import _download_components_data, _download_trust_zones_data, _download_threats_data, _download_countermeasures_data, _ensure_iriusrisk_directory, _save_json_file
from ..utils.project import resolve_project_id, get_project_context_info
from ..utils.updates import get_update_tracker
from ..utils.project_resolution import resolve_project_id_to_uuid_strict, is_uuid_format
from ..utils.project_discovery import find_project_root
from ..utils.mcp_logging import setup_mcp_logging
from ..api.project_client import ProjectApiClient
import json

logger = logging.getLogger(__name__)


def _find_project_root_and_config():
    """Find the project root directory and read project.json if it exists.
    
    DEPRECATED: This function is maintained for backward compatibility.
    Use utils.project_discovery.find_project_root() instead.
    
    Returns:
        tuple: (project_root_path, project_config_dict or None)
    """
    return find_project_root()


def _apply_prompt_customizations(tool_name: str, base_prompt: str) -> str:
    """Apply any configured prompt customizations from project.json.
    
    This allows users to customize MCP tool prompts on a per-project basis by adding
    a 'prompts' section to their project.json file. Supports three actions:
    - prefix: Add text before the base prompt
    - postfix: Add text after the base prompt
    - replace: Completely replace the base prompt
    
    Args:
        tool_name: Name of the MCP tool function (e.g., 'threats_and_countermeasures')
        base_prompt: The default prompt text for the tool
        
    Returns:
        The customized prompt text, or the base prompt if no customizations exist
        
    Example project.json structure:
        {
          "prompts": {
            "threats_and_countermeasures": {
              "prefix": "Organization-specific rules here\\n\\n",
              "postfix": "\\n\\nAdditional requirements here"
            },
            "create_threat_model": {
              "replace": "Completely custom prompt"
            }
          }
        }
    """
    from pathlib import Path
    
    # Debug logging
    logger.info(f"_apply_prompt_customizations called for tool: {tool_name}")
    logger.info(f"Current working directory: {Path.cwd()}")
    
    # Use the same project discovery logic as other MCP tools
    project_root, project_config = find_project_root()
    logger.info(f"Project root found: {project_root}")
    logger.info(f"Project config loaded: {project_config is not None}")
    if project_config:
        logger.info(f"Project config keys: {list(project_config.keys())}")
        logger.info(f"Has prompts section: {'prompts' in project_config}")
    
    if not project_config:
        logger.info(f"No project config found, returning base prompt for {tool_name}")
        return base_prompt
    
    customizations = project_config.get('prompts', {}).get(tool_name, {})
    logger.info(f"Customizations for {tool_name}: {customizations}")
    
    if not customizations:
        logger.info(f"No customizations found for {tool_name}")
        return base_prompt
    
    # Handle replace first (it overrides everything)
    if 'replace' in customizations:
        logger.info(f"Applying 'replace' customization to {tool_name}")
        logger.info(f"Replace text length: {len(customizations['replace'])} characters")
        return customizations['replace']
    
    # Apply prefix and/or postfix
    result = base_prompt
    if 'prefix' in customizations:
        logger.info(f"Applying 'prefix' customization to {tool_name}")
        result = customizations['prefix'] + result
    if 'postfix' in customizations:
        logger.info(f"Applying 'postfix' customization to {tool_name}")
        result = result + customizations['postfix']
    
    return result


@click.command()
@pass_cli_context
def mcp(cli_ctx):
    """Start MCP (Model Context Protocol) server for AI integration.
    
    This command starts an MCP server that provides tools for AI assistants
    to interact with IriusRisk CLI functionality. The server communicates
    via stdio and is designed to be used by AI-enabled IDEs like Cursor.
    
    The MCP server provides:
    - Instructions for AI on how to use IriusRisk MCP tools
    - Version information for the IriusRisk CLI
    - Future: Additional IriusRisk-specific tools and capabilities
    
    This command is not intended for direct user interaction but rather
    for integration with AI systems that support MCP.
    """
    # Configure MCP logging based on CLI context
    setup_mcp_logging(cli_ctx)
    logger.info("Starting IriusRisk MCP server")
    
    # Store CLI context for use in MCP functions
    config = cli_ctx.get_config()
    
    # Get API client from container (used by MCP tools)
    from ..container import get_container
    from ..api_client import IriusRiskApiClient
    container = get_container()
    api_client = container.get(IriusRiskApiClient)
    
    # Initialize FastMCP server
    mcp_server = FastMCP("iriusrisk-cli")
    
    @mcp_server.tool()
    async def initialize_iriusrisk_workflow() -> str:
        """Initialize IriusRisk workflow and get critical usage instructions for AI assistants.
        
        MANDATORY: This tool must be called before using any other IriusRisk MCP tools.
        Provides essential workflow instructions and tool usage guidelines.
        
        Returns:
            Critical workflow instructions and tool usage guidelines for AI assistants.
        """
        logger.info("MCP tool invoked: initialize_iriusrisk_workflow")
        logger.debug("Providing workflow instructions to AI assistant")
        instructions = """# IriusRisk MCP Workflow Instructions for AI Assistants

## Executive Summary
This MCP provides AI assistants with tools for professional threat modeling via IriusRisk CLI. Key workflow: sync() → analyze source → create OTM → import_otm() → project_status() → sync() → analyze results. Always use MCP tools and JSON files instead of direct CLI commands. Call initialize_iriusrisk_workflow() first for complete instructions.

## CRITICAL: Determine If Complete Threat Model Exists and Get User Permission

**A complete threat model requires BOTH project initialization AND threat analysis in IriusRisk.**

### Step 1: Call sync() First

Always start by calling `sync()` to download latest data. This is safe whether or not a threat model exists.

### Step 2: Check What sync() Downloaded

After calling `sync()`, check what files exist in `.iriusrisk/` directory:

### Scenario A: Complete Threat Model Exists (Use Automatically)

Files present:
- ✅ `project.json` - Project initialized
- ✅ `threats.json` WITH actual threat data (not empty, has threat entries)
- ✅ `countermeasures.json` WITH actual countermeasure data (not empty, has countermeasure entries)
- ✅ `components.json` - Component library
- ✅ `trust-zones.json` - Trust zones

**Action: Use threat model automatically - NO permission needed**

The user has already created this threat model, so use it:
1. Call `threats_and_countermeasures()` for analysis guidance
2. Read and analyze the threats.json and countermeasures.json files
3. Present integrated architecture + security review with threat findings

### Scenario B: No Threat Model (Assess User Intent and Ask Permission)

Files present:
- Either `project.json` exists BUT `threats.json`/`countermeasures.json` are missing/empty
- OR no `project.json` at all

**Action: Determine user intent BEFORE proceeding**

#### B1: User Made EXPLICIT Security Request

User said: "Is this secure?", "Security review", "What are the security risks?", "Vulnerabilities", "Threats"

**Response to user:**
```
"To provide a comprehensive security assessment, I recommend creating a threat 
model with IriusRisk. This will give you professional threat analysis rather 
than generic security advice.

Would you like me to help create a threat model? This will:
- Systematically identify security threats specific to your architecture
- Provide prioritized countermeasures with implementation guidance
- Generate compliance reports (OWASP, PCI DSS, etc.)
- Take about 10-15 minutes to set up"
```

**Wait for user response:**
- If YES → Call `create_threat_model()` and proceed with workflow
- If NO → Provide general security guidance with disclaimer

#### B2: User Made GENERAL Architecture Request

User said: "Review the architecture", "How does this work?", "Explain the system", "What does this code do?"

**Response to user:**
```
"I can provide an architecture review. I notice this project doesn't have a 
threat model yet.

Would you also like a security-aware analysis? I can help create an IriusRisk 
threat model that integrates security findings with your architecture documentation.

Options:
1. Architecture review only (I'll explain the structure and components)
2. Architecture + threat modeling (adds systematic security analysis)

What would you prefer?"
```

**Wait for user response:**
- If option 2 → Call `create_threat_model()` and proceed with threat modeling
- If option 1 → Provide architecture review, note threat modeling available later

#### B3: User is Planning Security-Impacting Changes

User said: "I'm adding [payment integration]", "Building [authentication]", "Implementing [data handling]"

**Assess security impact:**

**High security impact** (external integrations, sensitive data, auth, public endpoints):
```
"This change has significant security implications. I strongly recommend 
creating/updating a threat model to identify potential security issues early.

Shall I help with that? It will save time fixing security issues later vs. in production."
```

**Wait for response** - if YES, proceed with workflow

**Medium/Low security impact** (internal refactoring, UI, docs):
```
[Provide requested guidance]

[Optional light mention: "If you want security analysis, I can help create a threat model."]
```

### Step 3: If User Agrees to Threat Modeling

**Call `create_threat_model()`** to get OTM creation instructions, then:
1. Create OTM file modeling the architecture
2. Call `import_otm()` to upload and trigger IriusRisk analysis  
3. Call `project_status()` to verify processing
4. Call `sync()` again to download generated threats/countermeasures
5. Present integrated architecture + security review

### Step 4: If User Declines or Just Wants Architecture Review

**Provide value anyway:**
```
[Provide architecture/security guidance based on code analysis]

Note: This is based on code-level review. For comprehensive threat analysis 
with IriusRisk's professional security assessment, I can help create a threat 
model anytime.
```

### Key Principles

1. **Existing threat models = use automatically** (user already invested effort, no permission needed)
2. **Security-explicit requests = recommend strongly** (user wants security focus, but still ask)
3. **General architecture = offer as option** (respect user autonomy)
4. **Always ask permission** before creating new threat models
5. **Provide value regardless** - useful guidance even without threat modeling

### Critical Notes

- **`project.json` alone does NOT mean a threat model exists!** 
- Threat model only exists if `threats.json` and `countermeasures.json` have actual data
- **DO NOT invent threats or countermeasures** - they come from IriusRisk after OTM import
- **DO NOT force threat modeling** - respect user choice and provide value either way

## Proactive Threat Model Engagement

**CRITICAL: Threat models are first-class architectural artifacts.** When users ask about architecture, design, security posture, or system understanding, proactively engage the threat model.

**Always suggest threat modeling when:**
- **Understanding architecture/design**: "Explain this system", "How does this work?", "What's the architecture?", "Review the codebase"
- **Assessing security posture**: "Is this secure?", "What are the risks?", "Security review", "Vulnerabilities"
- **Making architectural changes**: Adding services, modifying data flows, changing trust boundaries, infrastructure updates
- **Working with security-sensitive areas**: External integrations, data handling, auth/authz, public endpoints, admin interfaces

**Examples of when to engage:**
- User: "I want to understand this project's architecture" → Check for `.iriusrisk/` → Offer threat model review
- User: "What are the security concerns?" → Sync threats → Present findings
- User: "I'm adding [any feature]" → Assess security impact → Offer threat model update
- User: "How does authentication work?" → Check threat model for auth components → Explain with security context

**Action:** When detected, say: "I see this is an [architecture/security/change] question. Let me check your IriusRisk threat model for comprehensive security analysis." Then call appropriate MCP tools.

## Critical Rules

### 1. Use MCP Tools, Not CLI Commands
**NEVER** run CLI commands like `iriusrisk countermeasures list` or `iriusrisk threats list`.  
**ALWAYS** use MCP tools and read JSON files from `.iriusrisk/` directory instead.  
Example: Instead of CLI commands, read `.iriusrisk/countermeasures.json` directly.

### 2. Countermeasure Updates Require Two Calls
The IriusRisk API requires status updates and comments to be sent separately. For ANY countermeasure status change:

**Step 1:** Update status only (no comment parameter)
```
track_countermeasure_update(countermeasure_id="...", status="implemented", reason="Added input validation")
```

**Step 2:** Add explanatory comment (with HTML formatting)
```
track_countermeasure_update(countermeasure_id="...", status="implemented", reason="Adding details", 
  comment="<p><strong>Implementation:</strong></p><ul><li>Added validation in api.py</li></ul>")
```

**Why:** IriusRisk API design requires separate calls for status vs. comment updates.  
**HTML Required:** Comments must use HTML tags (`<p>`, `<strong>`, `<ul><li>`, `<code>`, `<pre>`) not Markdown.  
**Character Limit:** Keep comments under 1000 characters (IriusRisk database constraint).

## Overview
The IriusRisk MCP (Model Context Protocol) provides AI assistants with tools to interact with IriusRisk CLI functionality. This MCP server enables seamless integration between AI systems and IriusRisk threat modeling capabilities.

## Available Tools

### Architecture & Design Review (START HERE for architecture questions)
1. **architecture_and_design_review()** - PRIMARY tool for architecture/design/security reviews
   - Call when: "Review the architecture", "What does this do?", "How does this work?", "Is this secure?"
   - Guides you to check for existing threat models FIRST before any analysis
   - Provides instructions for security-aware architecture reviews

### Core Workflow Tools
2. **initialize_iriusrisk_workflow()** - Get these complete workflow instructions (call first for threat model creation)
3. **get_cli_version()** - Get IriusRisk CLI version
4. **sync(project_path)** - Download components, trust zones, and project data from IriusRisk
5. **import_otm(otm_file_path)** - Upload OTM file to create/update project in IriusRisk
6. **project_status(project_id)** - Check project details and processing status

### Analysis & Guidance Tools
7. **threats_and_countermeasures()** - Get instructions for analyzing security findings
8. **analyze_source_material()** - Get guidance for analyzing mixed repositories (code + infrastructure + policies)
9. **create_threat_model()** - Get step-by-step threat model creation instructions

### Reporting Tools
10. **list_standards(project_id)** - List available compliance standards (OWASP, PCI DSS, NIST, etc.)
11. **generate_report(report_type, format, project_id, output_path, standard)** - Generate/download reports (countermeasure, threat, compliance, risk-summary)

### Status Tracking Tools
12. **track_threat_update(threat_id, status, reason, context, comment)** - Track threat status changes for later sync (status: accept/mitigate/expose/partly-mitigate/hidden)
13. **track_countermeasure_update(countermeasure_id, status, reason, context, comment)** - Track countermeasure status changes (see Two-Call Rule above)
14. **get_pending_updates()** - Review pending updates before sync
15. **clear_updates()** - Clear update queue
16. **create_countermeasure_issue(countermeasure_id, issue_tracker_id)** - Queue issue tracker ticket creation

## Common Workflows

### Architecture/Design Review Workflow (MOST COMMON)
1. **architecture_and_design_review()** - Triggers threat model engagement
2. **initialize_iriusrisk_workflow()** - Get complete workflow instructions
3. **sync()** - ALWAYS call first to download available data
4. **Check downloaded files** in `.iriusrisk/` directory:
   - If `threats.json` and `countermeasures.json` have data → Read and present findings
   - If files missing/empty but `project.json` exists → Call `create_threat_model()` and import OTM
   - If no `project.json` → Call `create_threat_model()` and create from scratch

### Threat Model Creation Workflow
1. sync(project_path) - Download latest component library
2. analyze_source_material() - Get analysis guidance (for mixed repos)
3. create_threat_model() - Get OTM creation instructions
4. [Create OTM file based on guidance]
5. import_otm(otm_file_path) - Upload to IriusRisk
6. project_status() - Verify processing complete
7. sync(project_path) - Download generated threats/countermeasures
8. threats_and_countermeasures() - Get analysis instructions

### Security Implementation Tracking Workflow
1. sync() - Download current threats/countermeasures
2. threats_and_countermeasures() - Get analysis guidance
3. [Implement security measures in code]
4. track_threat_update() / track_countermeasure_update() - Track changes (remember: two calls for countermeasures)
5. get_pending_updates() - Review pending changes
6. sync() - Apply updates to IriusRisk
7. [Verify updated statuses in downloaded JSON]

### Report Generation Workflow
1. list_standards() - See available compliance standards
2. generate_report(report_type, format, standard) - Generate report
3. [Report downloaded to local file]

## Key Best Practices
- Always call `sync()` FIRST to download available data
- Check what `sync()` downloaded to determine next steps:
  - `threats.json` has data → Analyze and present
  - `threats.json` missing/empty → Create threat model with OTM
- Use MCP tools and JSON files, not CLI commands
- Never run CLI commands like `iriusrisk threats list`
- Use two separate calls for countermeasure status changes
- Batch updates together, then sync once
- Use HTML formatting in comments (not Markdown)
- Keep comments under 1000 characters
- **DO NOT invent threats** - read them from `threats.json` or create OTM to generate them

## Example Usage Scenarios

**User:** "I want to understand this project's architecture"  
**AI:** 
1. Call `architecture_and_design_review()` → Get trigger guidance
2. Call `initialize_iriusrisk_workflow()` → Get complete instructions  
3. Call `sync()` → Download available data
4. Check if `threats.json` has data:
   - YES → Call `threats_and_countermeasures()` → Present integrated review
   - NO → Call `create_threat_model()` → Guide OTM creation → import_otm() → Wait for processing → sync() again

**User:** "What does this codebase do?"  
**AI:** Same as above - sync() first, check what's downloaded, then either present findings or create threat model.

**User:** "Is this system secure? What are the risks?"  
**AI:** Call sync() → Check `threats.json`:
- If has data → Present risk analysis from actual threats
- If empty/missing → "No threat analysis yet. Let me help create a threat model..." → Follow creation workflow

**User:** "I want to create a threat model from my Node.js + Terraform repository"  
**AI:** Call sync() → analyze_source_material() → create_threat_model() → [create OTM] → import_otm() → project_status() → sync()

**User:** "I'm adding a new API endpoint"  
**AI:** Check threat model exists → Assess impact → "This changes your attack surface. Let me update the threat model..." → Guide OTM update.

**User:** "Help me understand the threats in my system"  
**AI:** Call threats_and_countermeasures() for analysis instructions, then read and analyze `.iriusrisk/threats.json`

**User:** "I've implemented input validation. How do I track this?"  
**AI:** Make two calls to track_countermeasure_update():
1. Update status: `status="implemented", reason="Added input validation"`
2. Add comment: `status="implemented", reason="Adding details", comment="<p><strong>Implementation:</strong></p><ul><li>Added validation middleware in api.py</li></ul>"`

**User:** "Find the SQL injection countermeasure"  
**AI:** ✅ Read `.iriusrisk/countermeasures.json` and search programmatically  
(NOT: ❌ Run `iriusrisk countermeasures list`)

## Reference: Countermeasure Update Example

```python
# Step 1: Update status
track_countermeasure_update(
    countermeasure_id="abc-123",
    status="implemented",
    reason="Implemented input validation"
)

# Step 2: Add detailed comment
track_countermeasure_update(
    countermeasure_id="abc-123",
    status="implemented",
    reason="Adding implementation details",
    comment="<p><strong>Implementation:</strong></p><ul><li>Added middleware in <code>api.py</code></li><li>Uses pydantic validation</li></ul>"
)
```

## Technical Notes
- MCP communicates via stdio
- Logging: logs/mcp_server.log
- All tools are asynchronous and return strings
"""
        logger.info("Provided critical IriusRisk workflow instructions to AI assistant")
        return _apply_prompt_customizations('initialize_iriusrisk_workflow', instructions)
    
    @mcp_server.tool()
    async def get_cli_version() -> str:
        """Get the current version of IriusRisk CLI.
        
        Returns:
            Version string of the IriusRisk CLI.
        """
        logger.info(f"Provided CLI version: {__version__}")
        return f"IriusRisk CLI version {__version__}"
    
    @mcp_server.tool()
    async def sync(project_path: str = None) -> str:
        """Synchronize with IriusRisk to pull down components, trust zones, and project data.
        
        This tool pulls down the IriusRisk component library, trust zones, and optionally
        syncs threats and countermeasures if a project already exists.
        
        Args:
            project_path: Full path to the project directory (where .iriusrisk should be created)
        
        Returns:
            Status message indicating what was synced and where files were saved.
        """
        from datetime import datetime
        from ..utils.logging_config import PerformanceTimer
        
        timer = PerformanceTimer()
        timer.start()
        
        logger.info("MCP tool invoked: sync")
        logger.debug(f"Sync parameters: project_path={project_path}")
        logger.info("Starting IriusRisk sync via MCP")
        
        try:
            from pathlib import Path
            from ..commands.sync import sync_data_to_directory
            
            # Determine output directory from project path
            if project_path:
                project_root = Path(project_path).resolve()
                if not project_root.exists():
                    error_msg = f"❌ Project path does not exist: {project_path}"
                    logger.error(error_msg)
                    return error_msg
                if not project_root.is_dir():
                    error_msg = f"❌ Project path is not a directory: {project_path}"
                    logger.error(error_msg)
                    return error_msg
                output_dir = str(project_root / '.iriusrisk')
            else:
                project_root = Path.cwd()
                output_dir = str(project_root / '.iriusrisk')
            
            # Read project.json to get project_id if available
            project_config = None
            project_json_path = project_root / '.iriusrisk' / 'project.json'
            logger.info(f"Looking for project.json at: {project_json_path}")
            if project_json_path.exists():
                try:
                    with open(project_json_path, 'r') as f:
                        project_config = json.load(f)
                    logger.info(f"Successfully loaded project.json: {project_config.get('name', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"Could not read project.json: {e}")
            else:
                logger.warning(f"project.json not found at: {project_json_path}")
            
            # Get project_id from project.json if available
            project_id = None
            if project_config:
                # Prefer project_id (UUID) for existing projects, fall back to reference_id
                project_id = project_config.get('project_id') or project_config.get('reference_id')
            
            # Use the shared sync logic
            results = sync_data_to_directory(
                project_id=project_id,
                output_dir=output_dir
            )
            
            # Format results for MCP display
            output_lines = []
            output_dir_display = results.get('output_directory', output_dir)
            output_lines.append(f"🔄 Synchronizing IriusRisk data to: {output_dir_display}")
            output_lines.append(f"⏰ Sync timestamp: {results.get('timestamp', 'Unknown')}")
            output_lines.append(f"🗂️  Working directory: {Path.cwd()}")
            output_lines.append(f"📁 Project root: {project_root}")
            output_lines.append(f"🔍 Looking for project.json at: {project_json_path}")
            output_lines.append(f"📄 project.json exists: {project_json_path.exists()}")
            
            if project_config:
                # Show the reference ID for display (more readable than UUID)
                display_id = project_config.get('reference_id') or project_config.get('project_id', 'Unknown')
                output_lines.append(f"📋 Using project: {project_config.get('name', 'Unknown')} (ID: {display_id})")
            else:
                output_lines.append("📋 No project.json found or could not read it")
            
            if results.get('project_id') and results.get('project_id') != project_id:
                output_lines.append(f"🔄 Using reference ID: {results['project_id']}")
            
            if results.get('project_resolution_error'):
                output_lines.append(f"⚠️  Project resolution warning: {results['project_resolution_error']}")
            
            output_lines.append("")
            
            # Show what was synced
            if results.get('components'):
                if 'error' in results['components']:
                    output_lines.append(f"❌ Failed to download components: {results['components']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['components']['count']} system components")
                    output_lines.append(f"📄 Components saved to: {results['components']['file']}")
            
            if results.get('trust_zones'):
                if 'error' in results['trust_zones']:
                    output_lines.append(f"❌ Failed to download trust zones: {results['trust_zones']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['trust_zones']['count']} system trust zones")
                    output_lines.append(f"📄 Trust zones saved to: {results['trust_zones']['file']}")
            
            if results.get('threats'):
                if 'error' in results['threats']:
                    output_lines.append(f"❌ Failed to download threats: {results['threats']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['threats']['count']} threats")
                    output_lines.append(f"📄 Threats saved to: {results['threats']['file']}")
            
            if results.get('countermeasures'):
                if 'error' in results['countermeasures']:
                    output_lines.append(f"❌ Failed to download countermeasures: {results['countermeasures']['error']}")
                else:
                    output_lines.append(f"✅ Downloaded {results['countermeasures']['count']} countermeasures")
                    output_lines.append(f"📄 Countermeasures saved to: {results['countermeasures']['file']}")
            
            # Show update results if any
            if results.get('updates_applied', 0) > 0 or results.get('updates_failed', 0) > 0:
                output_lines.append("")
                output_lines.append("🔄 Status Updates Applied:")
                if results.get('updates_applied', 0) > 0:
                    output_lines.append(f"✅ Successfully applied {results['updates_applied']} status updates")
                if results.get('updates_failed', 0) > 0:
                    output_lines.append(f"❌ Failed to apply {results['updates_failed']} status updates")
                    for failed_update in results.get('failed_updates', []):
                        output_lines.append(f"   • {failed_update}")
                
                # Show comment creation results
                if results.get('comment_results'):
                    output_lines.append("")
                    output_lines.append("💬 Comment Creation Results:")
                    for comment_result in results['comment_results']:
                        output_lines.append(f"   • {comment_result}")
                
                # Show debug messages
                if results.get('debug_messages'):
                    output_lines.append("")
                    output_lines.append("🐛 Debug Information:")
                    for debug_msg in results['debug_messages']:
                        output_lines.append(f"   • {debug_msg}")
            
            # Show errors if any
            if results.get('errors'):
                output_lines.append("")
                for error in results['errors']:
                    output_lines.append(f"⚠️  {error}")
            
            # Summary
            output_lines.append("")
            output_lines.append("🎉 Sync completed! You can now create threat models with access to:")
            output_lines.append("   • Latest IriusRisk component library")
            if results.get('project_id'):
                output_lines.append("   • Current project threats and countermeasures")
            else:
                output_lines.append("💡 Use 'iriusrisk init' to set up a project for full sync")
            
            sync_result = "\n".join(output_lines)
            
            # Log performance metrics
            duration = timer.stop()
            logger.info(f"IriusRisk sync completed successfully via MCP in {duration:.3f}s")
            logger.debug(f"Sync performance: {duration:.3f}s total")
            
            return sync_result
            
        except Exception as e:
            # Ensure we don't get type errors when handling the exception
            error_str = str(e) if e is not None else "Unknown error"
            error_msg = f"❌ Sync failed: {error_str}"
            
            # Log error with performance context
            duration = timer.elapsed() if 'timer' in locals() else 0
            logger.error(f"MCP sync failed after {duration:.3f}s: {error_str}")
            logger.debug(f"Sync error context: project_path={project_path}, duration={duration:.3f}s")
            
            return error_msg
    
    @mcp_server.tool()
    async def import_otm(otm_file_path: str) -> str:
        """Import an OTM file to create or update a project in IriusRisk.
        
        This tool imports an OTM (Open Threat Model) file to IriusRisk, creating a new
        project or updating an existing one if it already exists.
        
        Args:
            otm_file_path: Path to the OTM file to import
            
        Returns:
            Status message indicating the result of the import operation.
        """
        from pathlib import Path
        
        logger.info("MCP tool invoked: import_otm")
        logger.debug(f"Import parameters: otm_file_path={otm_file_path}")
        logger.info(f"Starting OTM import via MCP for file: {otm_file_path}")
        
        try:
            # Find project root and read project.json if it exists
            project_root, project_config = _find_project_root_and_config()
            
            # Validate file path
            otm_path = Path(otm_file_path)
            if not otm_path.exists():
                error_msg = f"❌ OTM file not found: {otm_file_path}"
                logger.error(error_msg)
                return error_msg
            
            if not otm_path.is_file():
                error_msg = f"❌ Path is not a file: {otm_file_path}"
                logger.error(error_msg)
                return error_msg
            
            results = []
            results.append(f"📤 Importing OTM file: {otm_path.name}")
            results.append(f"📂 File path: {otm_path.absolute()}")
            
            # Show project context if available
            if project_config:
                project_name = project_config.get('name', 'Unknown')
                project_id = project_config.get('project_id', 'Unknown')
                reference_id = project_config.get('reference_id')
                results.append(f"🎯 Target project: {project_name} (ID: {project_id})")
                if reference_id:
                    results.append(f"🔗 Reference ID: {reference_id}")
            
            results.append("")
            
            # Import the OTM file (auto-update if project exists) using container API client
            result = api_client.import_otm_file(str(otm_path), auto_update=True)
            
            # Extract key information
            project_id = result.get('id', 'Unknown')
            project_name = result.get('name', 'Unknown')
            action = result.get('action', 'processed')
            
            results.append(f"✅ Project successfully {action}!")
            results.append(f"   📋 ID: {project_id}")
            results.append(f"   📛 Name: {project_name}")
            
            if 'ref' in result:
                results.append(f"   🔗 Reference: {result['ref']}")
            
            results.append("")
            results.append("🎉 OTM import completed successfully!")
            results.append("   • IriusRisk is now processing your architecture")
            results.append("   • Threats and countermeasures are being generated automatically")
            results.append("   • Use sync() MCP tool to download the generated security data")
            
            import_result = "\n".join(results)
            logger.info(f"OTM import completed successfully via MCP: {project_id}")
            return import_result
            
        except Exception as e:
            error_msg = f"❌ OTM import failed: {e}"
            logger.error(f"MCP OTM import failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def project_status(project_id: str = None) -> str:
        """Check the status of a project in IriusRisk.
        
        This tool retrieves detailed information about a project to verify
        it exists, has been processed, and is ready for use.
        
        Args:
            project_id: Project ID or reference ID (optional if default project configured)
            
        Returns:
            Status message with project details and processing status.
        """
        logger.info(f"Checking project status via MCP for project: {project_id or 'default'}")
        
        try:
            # Resolve project ID from argument, project.json, or default configuration
            if project_id:
                resolved_project_id = project_id
            else:
                # Try to get project ID from project.json first
                from pathlib import Path
                project_json_path = Path.cwd() / '.iriusrisk' / 'project.json'
                resolved_project_id = None
                
                if project_json_path.exists():
                    try:
                        with open(project_json_path, 'r') as f:
                            project_config = json.load(f)
                        resolved_project_id = project_config.get('project_id')
                        logger.info(f"Using project ID from project.json: {resolved_project_id}")
                    except Exception as e:
                        logger.warning(f"Could not read project.json: {e}")
                
                # Fall back to config if no project.json
                if not resolved_project_id:
                    resolved_project_id = config.get_default_project_id()
                
                if not resolved_project_id:
                    error_msg = "❌ No project ID provided and no default project configured. Use project_status(project_id) or set up a project with 'iriusrisk init'."
                    logger.error(error_msg)
                    return error_msg
            
            results = []
            results.append(f"🔍 Checking project status: {resolved_project_id}")
            results.append("")
            
            # Try to get project details using container API client
            try:
                project_data = api_client.get_project(resolved_project_id)
            except Exception as direct_error:
                # If direct lookup fails, try searching by reference ID
                if "400" in str(direct_error) or "404" in str(direct_error) or "Bad Request" in str(direct_error) or "Not Found" in str(direct_error):
                    results.append(f"📋 Searching by reference ID: {resolved_project_id}")
                    
                    filter_expr = f"'referenceId'='{resolved_project_id}'"
                    response = api_client.get_projects(page=0, size=1, filter_expression=filter_expr)
                    
                    projects = response.get('_embedded', {}).get('items', [])
                    if not projects:
                        error_msg = f"❌ No project found with ID or reference: {resolved_project_id}"
                        logger.error(error_msg)
                        return error_msg
                    
                    project_data = projects[0]
                    results.append(f"✅ Found project by reference ID")
                else:
                    raise direct_error
            
            # Extract project information
            project_name = project_data.get('name', 'Unknown')
            project_uuid = project_data.get('id', 'Unknown')
            project_ref = project_data.get('referenceId', 'None')
            workflow_state = project_data.get('workflowState', {})
            workflow_name = workflow_state.get('name', 'Unknown') if workflow_state else 'Unknown'
            is_archived = project_data.get('isArchived', False)
            model_updated = project_data.get('modelUpdated', 'Unknown')
            
            results.append("📊 Project Status:")
            results.append(f"   📛 Name: {project_name}")
            results.append(f"   🆔 UUID: {project_uuid}")
            results.append(f"   🔗 Reference: {project_ref}")
            results.append(f"   🔄 Workflow State: {workflow_name}")
            results.append(f"   📅 Last Updated: {model_updated}")
            results.append(f"   📦 Archived: {'Yes' if is_archived else 'No'}")
            
            # Determine status
            if is_archived:
                results.append("")
                results.append("⚠️  Project is archived - it may not be actively processing")
            else:
                results.append("")
                results.append("✅ Project is active and ready for use")
                results.append("   • OTM import has been processed")
                results.append("   • Threats and countermeasures should be available")
                results.append("   • Ready for sync() to download generated data")
            
            status_result = "\n".join(results)
            logger.info(f"Project status check completed via MCP: {project_uuid}")
            return status_result
            
        except Exception as e:
            error_msg = f"❌ Failed to check project status: {e}"
            logger.error(f"MCP project status check failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def threats_and_countermeasures() -> str:
        """Get instructions for reading and exploring threats and countermeasures data.
        
        This tool provides comprehensive instructions for AI assistants on how to
        read, analyze, and help users explore the threats and countermeasures that
        IriusRisk automatically generated for their project.
        
        Returns:
            Detailed instructions for working with threats and countermeasures data.
        """
        logger.info("Providing threats and countermeasures instructions via MCP")
        
        instructions = """# Threats and Countermeasures Analysis Instructions for AI Assistants

## Executive Summary
After completing the threat modeling workflow, IriusRisk generates threats and countermeasures saved to `.iriusrisk/` directory. Your role: read these JSON files, explain findings in business terms, prioritize by risk, provide implementation guidance and code examples. Do NOT create new threats, modify risk ratings, or analyze source code for vulnerabilities—that's IriusRisk's job.

## Available Data Files

After sync(), read these JSON files from `.iriusrisk/` directory:

**1. threats.json** - All threats IriusRisk identified:
- Threat descriptions, categories, risk ratings (likelihood/impact)
- Affected components, attack vectors, STRIDE classifications, CWE mappings

**2. countermeasures.json** - All security controls and mitigations:
- Control descriptions, implementation guidance, risk reduction effectiveness
- Associated threats, implementation status, priority, industry standards (NIST, ISO 27001)
- Cost and effort estimates

**3. components.json** - Component library reference:
- Available component types, properties, configurations

## Your Role as AI Assistant

**Do:**
- Read and analyze JSON files when users ask about their threat model
- Explain threats in business terms for non-security experts
- Prioritize threats by risk level (focus on critical issues)
- Provide implementation guidance and code examples for countermeasures
- Create summaries and reports of security findings
- Reference specific threat/countermeasure IDs from the data

**Do NOT:**
- Create new threats or countermeasures (use only what IriusRisk generated)
- Modify risk ratings assigned by IriusRisk
- Ignore high-risk threats in favor of easier ones
- Analyze source code for vulnerabilities (that's IriusRisk's role)
- Speculate about potential security flaws not in the data

## Common User Questions & Responses

**Q: "What are the main security concerns with my system?"**  
A: Read threats.json → identify high-risk threats → group by category → provide prioritized summary with business impact

**Q: "Tell me more about the SQL injection threat"**  
A: Find threat in threats.json → explain attack scenario simply → show affected components → reference related countermeasures

**Q: "How do I implement input validation?"**  
A: Find countermeasure in countermeasures.json → provide code examples in their stack → explain best practices → reference industry standards

**Q: "What should I fix first?"**  
A: Sort threats by risk rating (likelihood × impact) → consider implementation effort → recommend prioritized action plan focusing on quick wins and critical issues

**Q: "Does this help with GDPR compliance?"**  
A: Review countermeasures for privacy controls → map threats to data protection requirements → identify gaps → suggest additional measures

## JSON File Structure Examples

### threats.json structure:
```json
{
  "metadata": {
    "project_id": "...",
    "total_count": 45,
    "sync_timestamp": "..."
  },
  "threats": [
    {
      "id": "threat-123",
      "name": "SQL Injection via User Input",
      "description": "Attackers can inject malicious SQL...",
      "riskRating": "HIGH",
      "likelihood": 4,
      "impact": 5,
      "components": ["web-app-component-id"],
      "categories": ["Input Validation", "Database Security"],
      "cwe": ["CWE-89"],
      "stride": ["Tampering", "Information Disclosure"]
    }
  ]
}
```

### countermeasures.json structure:
```json
{
  "metadata": {
    "project_id": "...",
    "total_count": 67,
    "sync_timestamp": "..."
  },
  "countermeasures": [
    {
      "id": "control-456",
      "name": "Input Validation and Sanitization",
      "description": "Implement comprehensive input validation...",
      "threats": ["threat-123", "threat-124"],
      "priority": "HIGH",
      "effort": "MEDIUM",
      "status": "NOT_IMPLEMENTED",
      "frameworks": ["NIST CSF", "OWASP Top 10"],
      "implementation": "Use parameterized queries..."
    }
  ]
}
```

## Response Templates

**Executive Summary:**
"IriusRisk identified [X] threats across [Y] categories. Highest priority:
1. [threat] - affects [components] - mitigate with [control]
2. [threat] - affects [components] - mitigate with [control]"

**Implementation Guide:**
"To implement [countermeasure]:
- **What it does**: [explanation from data]
- **Why it's important**: [risk context from threats.json]
- **How to implement**: [code example in their stack]
- **Testing**: [validation approach]
- **Standards**: [from countermeasures.json]"

**Risk Context:**
"This threat has [risk rating] because:
- Likelihood: [X/5] - [explanation from data]
- Impact: [Y/5] - [business impact]
- Affected: [components from threats.json]
- Action: [from countermeasures.json]"

## Code Generation Guidelines

When generating code examples:
1. Use countermeasure descriptions as requirements
2. Target their technology stack (ask if unclear)
3. Include error handling and security best practices
4. Add comments explaining security rationale
5. Reference the specific threat being mitigated

## Integration with Development Workflow

Help users integrate security practices:
- **Code reviews**: Generate security checklists from countermeasures
- **Testing**: Create security test cases from threat scenarios
- **Monitoring**: Suggest logging/alerting for threat detection
- **Documentation**: Generate security requirements from the data

Your role: Make IriusRisk's professional security analysis accessible and actionable for users' specific context.
"""
        
        logger.info("Provided threats and countermeasures instructions to AI assistant")
        return _apply_prompt_customizations('threats_and_countermeasures', instructions)
    
    @mcp_server.tool()
    async def show_diagram(project_id: str = None, size: str = "PREVIEW") -> str:
        """Download and display the project threat model diagram.
        
        This tool downloads the project's automatically generated threat model diagram
        as a PNG image. The diagram shows the architecture with components, trust zones,
        and data flows that were modeled in the OTM.
        
        Args:
            project_id: Project ID or reference ID (optional if project.json exists)
            size: Image size - ORIGINAL, PREVIEW, or THUMBNAIL (default: PREVIEW)
            
        Returns:
            Status message with diagram file location and details.
        """
        logger.info(f"Downloading project diagram via MCP for project: {project_id or 'default'}")
        
        try:
            from pathlib import Path
            import base64
            
            # Resolve project ID from argument, project.json, or default configuration
            if project_id:
                resolved_project_id = project_id
            else:
                # Try to get project ID from project.json first
                project_json_path = Path.cwd() / '.iriusrisk' / 'project.json'
                resolved_project_id = None
                
                if project_json_path.exists():
                    try:
                        with open(project_json_path, 'r') as f:
                            project_config = json.load(f)
                        resolved_project_id = project_config.get('project_id')
                        logger.info(f"Using project ID from project.json: {resolved_project_id}")
                    except Exception as e:
                        logger.warning(f"Could not read project.json: {e}")
                
                # Fall back to config if no project.json
                if not resolved_project_id:
                    resolved_project_id = config.get_default_project_id()
                
                if not resolved_project_id:
                    error_msg = "❌ No project ID provided and no default project configured. Use show_diagram(project_id) or set up a project with 'iriusrisk init'."
                    logger.error(error_msg)
                    return error_msg
            
            results = []
            results.append(f"🖼️  Downloading threat model diagram")
            results.append(f"📁 Project: {resolved_project_id}")
            results.append(f"📏 Size: {size}")
            results.append("")
            
            # Resolve project ID to UUID for V2 API (upfront, no fallback mechanism)
            from ..utils.project_resolution import resolve_project_id_to_uuid
            logger.debug(f"Resolving project ID to UUID: {resolved_project_id}")
            final_project_id = resolve_project_id_to_uuid(resolved_project_id, api_client)
            logger.debug(f"Resolved to UUID: {final_project_id}")
            
            # Get artifacts with the resolved UUID
            artifacts_response = api_client.get_project_artifacts(final_project_id, page=0, size=100)
            artifacts = artifacts_response.get('_embedded', {}).get('items', [])
            
            if not artifacts:
                error_msg = "❌ No diagram artifacts found for this project. Make sure the project has been synchronized and contains a threat model."
                logger.error(error_msg)
                return error_msg
            
            # Find the diagram artifact (usually the first visible one)
            diagram_artifact = None
            for artifact in artifacts:
                # Look for artifacts that are likely diagrams (visible artifacts are usually diagrams)
                if artifact.get('visible', True):
                    diagram_artifact = artifact
                    break
            
            if not diagram_artifact:
                # If no visible artifacts, take the first one
                diagram_artifact = artifacts[0]
            
            artifact_id = diagram_artifact.get('id')
            artifact_name = diagram_artifact.get('name', 'diagram')
            
            results.append(f"📊 Found diagram: {artifact_name}")
            results.append(f"🔍 Downloading {size.lower()} image...")
            
            # Get the artifact content (base64 encoded image)
            content_response = api_client.get_project_artifact_content(artifact_id, size=size.upper())
            
            if not content_response.get('successfulGeneration', True):
                results.append("⚠️  Warning: Diagram generation may not have been fully successful")
            
            # Extract base64 content
            base64_content = content_response.get('content')
            if not base64_content:
                error_msg = "❌ No image content found in diagram artifact"
                logger.error(error_msg)
                return error_msg
            
            # Create filename and determine project directory
            try:
                # Find the project directory by looking for .iriusrisk/project.json
                project_root = None
                current_dir = Path.cwd()
                
                # Check current directory and parent directories for .iriusrisk/project.json
                for check_dir in [current_dir] + list(current_dir.parents):
                    project_json_path = check_dir / '.iriusrisk' / 'project.json'
                    if project_json_path.exists():
                        project_root = check_dir
                        try:
                            with open(project_json_path, 'r') as f:
                                project_config = json.load(f)
                            project_name = project_config.get('name', 'project')
                            # Clean up project name for filename
                            clean_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            clean_name = clean_name.replace(' ', '-').lower()
                            filename = f"{clean_name}-diagram-{size.lower()}.png"
                            break
                        except (json.JSONDecodeError, OSError, IOError, KeyError) as e:
                            # If we can't read or parse project.json, continue looking
                            logger.debug(f"Failed to parse {project_json_path}: {e}")
                            continue
                
                if not project_root:
                    # Fallback to current directory if no project.json found
                    project_root = current_dir
                    filename = f"threat-model-diagram-{size.lower()}.png"
                    
            except (OSError, RuntimeError) as e:
                # If path operations fail, use current directory fallback
                logger.debug(f"Failed to determine project directory: {e}")
                project_root = Path.cwd()
                filename = f"threat-model-diagram-{size.lower()}.png"
            
            # Decode base64 and save to project directory
            try:
                image_data = base64.b64decode(base64_content)
                output_path = project_root / filename
                
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                
                results.append("")
                results.append("✅ Diagram downloaded successfully!")
                results.append(f"📁 File: {output_path.absolute()}")
                results.append(f"📂 Project: {project_root}")
                results.append(f"📊 Size: {len(image_data):,} bytes")
                results.append(f"🖼️  Format: PNG image ({size})")
                results.append("")
                results.append("💡 The diagram shows your threat model architecture:")
                results.append("   • Components and their relationships")
                results.append("   • Trust zones and boundaries") 
                results.append("   • Data flows between components")
                results.append("   • Generated automatically from your OTM file")
                
                diagram_result = "\n".join(results)
                logger.info(f"Diagram downloaded successfully via MCP: {filename}")
                return diagram_result
                
            except Exception as e:
                error_msg = f"❌ Failed to save diagram: {e}"
                logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"❌ Failed to download diagram: {e}"
            logger.error(f"MCP show_diagram failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def analyze_source_material() -> str:
        """Get comprehensive instructions for analyzing mixed source repositories.
        
        This tool provides AI assistants with detailed guidance on how to analyze
        repositories containing multiple source types (application code, infrastructure,
        policies, documentation) and extract all relevant components for a single,
        comprehensive threat model.
        
        Returns:
            Detailed instructions for analyzing mixed source repositories and extracting
            all component types for unified threat modeling.
        """
        logger.info("Providing source material analysis instructions via MCP")
        
        instructions = """# Source Material Analysis Instructions for AI Assistants

## Executive Summary
Analyze mixed repositories (application code + infrastructure + policies + docs) to extract ALL components for ONE unified threat model. Your role: architecture modeling only—extract components, trust zones, and data flows. Do NOT identify vulnerabilities or security flaws; IriusRisk handles that automatically. Create a single comprehensive threat model covering all layers.

## Critical Principle: One Comprehensive Threat Model
Create ONE unified threat model including ALL components from ALL source types. Do NOT create separate models for code vs. infrastructure—IriusRisk works best with a complete, holistic view of the entire system.

## Your Role: Architecture Modeling Only
**Do:** Extract components, trust zones, and data flows  
**Do NOT:** Identify vulnerabilities, threats, security flaws, or speculate about weaknesses  
**Why:** IriusRisk performs all security analysis automatically

## Component Types to Extract

### 1. Application/Functional Components
**From source code, APIs, microservices:**
- **Business Logic Components**: Payment processing, user authentication, order management, reporting engines
- **Application Services**: User management service, notification service, audit service, integration service
- **API Endpoints**: REST APIs, GraphQL endpoints, webhook receivers, internal APIs
- **Background Processes**: Batch jobs, scheduled tasks, data processing pipelines, cleanup services
- **Client Applications**: Web frontends, mobile apps, desktop applications, CLI tools

### 2. Data Components
**From databases, data flows, storage systems:**
- **Data Stores**: SQL databases, NoSQL databases, data warehouses, caches (Redis, Memcached)
- **Data Processing**: ETL pipelines, stream processing, data analytics engines, ML model training
- **Data Storage**: File systems, object storage (S3), content delivery networks, backup systems
- **Data Flows**: Customer data, transaction data, audit logs, analytics data, configuration data

### 3. Infrastructure/Network Components
**From Terraform, cloud configurations, network diagrams:**
- **Compute Resources**: Virtual machines, containers, serverless functions, auto-scaling groups
- **Network Infrastructure**: VPCs, subnets, NAT gateways, internet gateways, VPN connections
- **Load Balancing**: Application load balancers, network load balancers, API gateways, reverse proxies
- **Security Infrastructure**: Firewalls, security groups, NACLs, WAF, DDoS protection

### 4. Cloud Services Components
**From cloud provider configurations:**
- **Serverless**: Lambda functions, Step Functions, EventBridge, SQS, SNS
- **Managed Services**: RDS, DynamoDB, ElastiCache, Elasticsearch, CloudSearch
- **Storage Services**: S3 buckets, EFS, EBS volumes, Glacier, backup services
- **Monitoring/Logging**: CloudWatch, CloudTrail, X-Ray, application monitoring tools
- **Identity/Access**: IAM roles, Cognito, Active Directory, SSO providers

### 5. Integration Components
**From API configurations, message queues, external services:**
- **Message Queues**: SQS, RabbitMQ, Kafka, EventBridge, pub/sub systems
- **External APIs**: Third-party payment processors, social media APIs, mapping services
- **Integration Platforms**: API management platforms, ESBs, webhook processors
- **Communication**: Email services, SMS services, push notification services

### 6. Security/Compliance Components
**From security policies, compliance documentation:**
- **Authentication Systems**: OAuth providers, SAML IdPs, multi-factor authentication
- **Authorization Systems**: Role-based access control, attribute-based access control
- **Encryption Services**: Key management systems, HSMs, certificate authorities
- **Compliance Tools**: Audit logging, compliance monitoring, policy enforcement points

## Source Analysis Strategy

### Phase 1: Repository Scanning and Categorization
1. **Identify all source types** in the repository:
   - Application source code (multiple languages/frameworks)
   - Infrastructure as Code (Terraform, CloudFormation, Kubernetes)
   - Configuration files (Docker, CI/CD, environment configs)
   - Security policies and compliance documentation
   - Architecture documentation and diagrams
   - Database schemas and migration scripts

2. **Catalog components by source type**:
   - Create inventory of what each source type reveals
   - Note overlaps and relationships between sources
   - Identify gaps where components are referenced but not defined

### Phase 2: Component Extraction and Classification

**From Application Code:** Extract business logic (auth services, business domain services, API endpoints, background jobs, data access layers, integrations). Extract components separately from infrastructure—they'll be nested within infrastructure components (containers, VMs). Focus on what business functions exist and how they interact.

**From Infrastructure Code (Terraform/CloudFormation):** Extract cloud resources, security groups/ACLs, load balancers, database instances, monitoring configs, IAM roles, encryption configs.

**From Security Policies/Documentation:** Identify required controls, compliance frameworks, data classification, network segmentation policies, incident response procedures, third-party integration requirements, regulatory compliance (GDPR, HIPAA, SOX).

**From Configuration/Deployment Files:** Discover container definitions, orchestration, environment configs, CI/CD pipelines, monitoring/observability, backup/DR setups.

### Phase 3: Component Consolidation and Relationship Mapping

**1. Merge overlapping components:** Consolidate same logical component appearing in multiple sources into one with comprehensive properties.

**2. Plan nesting hierarchy:**
- Infrastructure layer → Cloud resources, VMs, containers, managed services
- Business logic layer → Application services nested within infrastructure
- Data layer → Databases/storage (nested or standalone)
- Integration layer → External APIs, message queues, third-party services

**3. Establish relationships:** Nesting (business logic within infrastructure), data flows (between components and data stores), network connections (between infrastructure), dependencies (microservices ↔ external APIs), trust relationships (between security domains).

**4. Define trust zones:**
- Internet Zone (trust rating: 1) - Public-facing components, external APIs
- DMZ Zone (3) - Load balancers, web servers, API gateways
- Application Zone (5) - Business logic services, application servers
- Data Zone (7) - Databases, caches, data processing
- Management Zone (8) - Admin interfaces, monitoring, logging
- Security Zone (10) - Authentication services, key management, audit systems

## Component Mapping to IriusRisk Types

**CRITICAL:** Always read `.iriusrisk/components.json` to find exact `referenceId` values. Search the JSON file for keywords related to your component (e.g., search for "payment", "database", "API", "lambda"). Use the exact `referenceId` field value as the component `type` in your OTM file.

**Mapping process:**
1. Identify component from source material (e.g., "payment processing service")
2. Search `.iriusrisk/components.json` for related keywords
3. Find matching component with appropriate `referenceId`
4. Use that exact `referenceId` as the `type` in OTM (e.g., `type: "CD-V2-PAYMENT-PROCESSOR"`)

**Common component categories to search for:**
- Business logic: payment, authentication, authorization, user management, audit
- Data: SQL database, NoSQL, document database, data warehouse, file storage
- Cloud: AWS/Azure/GCP services (lambda, S3, RDS, VPC, API gateway)
- Integration: message queue, external API, webhook, CDN

## Trust Zone Assignment

**Business Logic:** Assign based on data sensitivity
- Public APIs → DMZ or Application Zone (rating: 3-5)
- Internal services → Application Zone (5)
- Data processing → Data Zone (7)
- Admin functions → Management Zone (8)

**Infrastructure:** Assign based on network position
- Internet-facing → Internet or DMZ Zone (1-3)
- Internal networking → Application Zone (5)
- Data storage → Data Zone (7)
- Management tools → Management Zone (8)

**Cloud Services:** Consider managed service security
- Managed databases → Data Zone (7)
- Serverless functions → Application Zone (5)
- Object storage → Data Zone (7)

## Data Flow Patterns

**Cross-Layer Flows:**
1. User Request: Internet → Load Balancer → API Gateway → Business Logic → Database
2. Data Processing: Database → ETL → Analytics → Reporting
3. Integration: External API → Message Queue → Processor → Internal DB
4. Monitoring: All Components → Logging → Monitoring Dashboard → Alerts

**Security-Relevant Flows:** Authentication tokens, sensitive data (PII/financial), audit logs, secrets distribution, backup data

## Quality Assurance Checklist

Before creating OTM, verify:
- ☐ All source types analyzed (code, infrastructure, policies, docs)
- ☐ Component coverage: business logic, data, infrastructure, cloud, integration
- ☐ Data flows connect all related components
- ☐ Trust zones assigned appropriately based on security posture
- ☐ Overlapping components consolidated (no duplication)
- ☐ Single threat model covers entire system end-to-end

## Example: E-Commerce Multi-Source Analysis

**Sources:** Node.js app + Terraform AWS + security policies + API docs

**Extracted Components with Nesting:**
```yaml
components:
  # Infrastructure (from Terraform) - in trust zones
  - id: "ecs-cluster"
    type: "[exact referenceId from components.json]"
    parent: { trustZone: "application" }
  - id: "api-gateway"
    type: "[exact referenceId from components.json]"
    parent: { trustZone: "dmz" }
    
  # Business Logic (from code) - nested in infrastructure
  - id: "user-service"
    type: "[exact referenceId from components.json]"
    parent: { component: "ecs-cluster" }  # nested in ECS
  - id: "payment-processor"
    type: "[exact referenceId from components.json]"
    parent: { component: "ecs-cluster" }  # nested in ECS
    
  # Data Layer - can be nested or standalone
  - id: "user-database"
    type: "[exact referenceId from components.json]"
    parent: { trustZone: "data" }

dataflows:
  - id: "user-registration"
    source: "api-gateway"
    destination: "user-service"
  - id: "payment-processing"
    source: "payment-processor"
    destination: "payment-api"
```

## Workflow Integration

1. Call analyze_source_material() for guidance
2. Call create_threat_model() for OTM creation workflow
3. Execute: sync() → create OTM → import_otm() → project_status() → sync()

Result: Single, comprehensive threat model for holistic IriusRisk analysis across all system layers.
"""
        
        logger.info("Provided source material analysis instructions to AI assistant")
        return _apply_prompt_customizations('analyze_source_material', instructions)
    
    @mcp_server.tool()
    async def create_threat_model() -> str:
        """Get comprehensive instructions for creating an IriusRisk threat model.
        
        This tool provides step-by-step instructions for AI assistants on how to
        create a complete threat model using the IriusRisk CLI workflow.
        
        Returns:
            Detailed instructions for creating threat models from source material.
        """
        instructions = """# IriusRisk Threat Model Creation Instructions for AI Assistants

## Executive Summary
Create OTM files to model system architecture for IriusRisk threat analysis. Your role: architecture modeling only (components, trust zones, data flows). Do NOT create threats or controls—IriusRisk generates those automatically. Always: sync() first → create OTM → import_otm() → project_status() → sync() to download results.

**⚠️ CRITICAL: Dataflows ONLY connect components to components. NEVER use trust zone IDs in dataflows - this causes import failure.**

## Critical Error #1: Dataflows Connect Components, NOT Trust Zones

**Most common OTM import failure:** Using trust zone IDs in dataflows instead of component IDs.

```yaml
# ✅ CORRECT - Component to Component:
dataflows:
  - id: "user-to-app"
    source: "mobile-app"      # component ID
    destination: "web-server" # component ID

# ❌ WRONG - Trust Zone IDs (CAUSES IMPORT FAILURE):
dataflows:
  - id: "bad-flow"
    source: "internet"        # trust zone ID - FAILS!
    destination: "dmz"        # trust zone ID - FAILS!
```

**Rule:** Trust zones CONTAIN components. Dataflows CONNECT components directly.

## Critical Error #2: Component Types Must Use Exact referenceId

```yaml
# ✅ CORRECT:
type: "CD-V2-AWS-ECS-CLUSTER"  # exact referenceId from components.json

# ❌ WRONG:
type: "aws-ecs"  # abbreviated - causes mapping failure
```

**Rule:** Read `.iriusrisk/components.json`, find the `referenceId` field, use it exactly.

## Your Role: Architecture Modeling Only

**Do:**
- Extract components from source code, infrastructure, documentation
- Map components to IriusRisk types using exact referenceId values
- Define trust zones and component relationships
- Create data flows between components

**Do NOT:**
- Identify threats, vulnerabilities, or security flaws
- Create mitigations, controls, or countermeasures
- Add threats/mitigations sections to OTM file
- Analyze code for security issues
- Run CLI commands like `iriusrisk component search`

**Why:** IriusRisk automatically generates all threats and controls after OTM import.

## Required Workflow Checklist

Complete steps 0-7. Step 8 only when user requests security findings:

- ☐ Step 0: **sync(project_path)** - Download components & trust zones
- ☐ Step 1: Analyze source material - Identify architectural components
- ☐ Step 2: Check `.iriusrisk/project.json` - Read project name/ID if exists
- ☐ Step 3: Create OTM file - ONLY components, trust zones, dataflows (dataflows connect components ONLY)
- ☐ Step 4: Map components - Use exact referenceId from components.json
- ☐ Step 5: **import_otm()** - Upload OTM to IriusRisk
- ☐ Step 6: **project_status()** - Verify project ready
- ☐ Step 7: Present results - Offer options (refine OR download findings)
- ☐ Step 8: **sync()** again (only if user requests) - Download threats/countermeasures

## Detailed Workflow

### Step 0: sync(project_path) - Download Component Library

**Mandatory first step.** Call sync() with full absolute project path (e.g., `sync("/Users/username/my-project")`).

**What it does:**
- Downloads complete IriusRisk component library to `.iriusrisk/components.json`
- Downloads trust zones to `.iriusrisk/trust-zones.json`
- If project exists, also downloads current threats/countermeasures
- Prevents OTM import failures due to unknown component types

### Step 1-2: Analyze Source & Check Configuration

**Analyze source material:**
- Identify infrastructure (VMs, containers, databases, load balancers)
- Identify business logic (auth services, payment processing, user management)
- Identify data components (databases, storage, queues, caches)
- Identify external systems (third-party APIs, services)
- Plan nesting (business logic runs within infrastructure)
- Identify data flows between components
- **Do NOT identify threats or security issues**

**Check for existing project:**
- Look for `.iriusrisk/project.json`
- If exists, use `name` and `project_id` from that file
- If not exists, create descriptive names from source material

### Step 3: Create OTM File

**Use project.json if exists:** Read `.iriusrisk/project.json` and use `name` and `project_id` from that file. Otherwise, create descriptive names.

## Parent Relationship Rules

**Simple principle:** A component's parent represents WHERE it physically resides or executes.

**Use `parent: { trustZone: "zone-id" }` when:**
- The component is standalone infrastructure (VPCs, networks, databases, storage)
- The component is externally hosted (third-party APIs, SaaS services)
- The component has no containing infrastructure in your model

**Use `parent: { component: "component-id" }` when:**
- The component runs inside another component
- Examples: Application runs in VM, Service runs in container, Function runs in serverless platform

**Common patterns:**
- Network infrastructure → trust zone parent
- Compute infrastructure (VM, container platform) → trust zone parent
- Applications/services running on compute → component parent (the compute hosting it)
- Databases/storage → trust zone parent (unless hosted on specific infrastructure you're modeling)
- External/third-party services → trust zone parent (typically "internet" zone)

**⚠️ REMEMBER: Trust zones define LOCATION. Components define THINGS. Dataflows connect THINGS (components), not locations (trust zones).**

## Complete Example

```yaml
otmVersion: 0.1.0
project:
  name: "[from project.json or descriptive name]"
  id: "[from project.json or generate unique ID]"
  description: "[brief system description]"

trustZones:
  - id: "internet"
    name: "Internet"
    risk:
      trustRating: 1
  - id: "dmz"
    name: "DMZ"
    risk:
      trustRating: 3
  - id: "application"
    name: "Application Zone"
    risk:
      trustRating: 5
  - id: "data"
    name: "Data Zone"
    risk:
      trustRating: 7

components:
  # External client - in internet zone
  - id: "web-browser"
    name: "Web Browser"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "internet"
  
  # Load balancer - standalone in DMZ
  - id: "alb"
    name: "Application Load Balancer"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "dmz"
  
  # Container platform - standalone in application zone
  - id: "ecs-cluster"
    name: "ECS Cluster"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "application"
  
  # Application services - run inside container platform
  - id: "auth-service"
    name: "Authentication Service"
    type: "[exact referenceId from components.json]"
    parent:
      component: "ecs-cluster"  # runs in ECS
  
  - id: "api-service"
    name: "API Service"
    type: "[exact referenceId from components.json]"
    parent:
      component: "ecs-cluster"  # runs in ECS
  
  # Database - standalone in data zone
  - id: "user-db"
    name: "User Database"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "data"
  
  # External API - in internet zone
  - id: "payment-api"
    name: "Payment Processor API"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "internet"

dataflows:
  # ⚠️⚠️⚠️ CRITICAL: Dataflows ONLY connect components (never trust zones) ⚠️⚠️⚠️
  # Use component IDs like "web-browser", "alb", "api-service" (defined above)
  # NEVER use trust zone IDs like "internet", "dmz", "application" in dataflows
  
  - id: "user-request"
    source: "web-browser"      # component ID ✅
    destination: "alb"          # component ID ✅
  
  - id: "alb-to-api"
    source: "alb"               # component ID ✅
    destination: "api-service"  # component ID ✅
  
  - id: "api-to-auth"
    source: "api-service"       # component ID ✅
    destination: "auth-service" # component ID ✅
  
  - id: "auth-to-db"
    source: "auth-service"      # component ID ✅
    destination: "user-db"      # component ID ✅
  
  - id: "api-to-payment"
    source: "api-service"       # component ID ✅
    destination: "payment-api"  # component ID ✅

# Do NOT add: threats, mitigations, controls (IriusRisk generates these)
```

## Invalid Examples - Common Mistakes

```yaml
# ❌ WRONG: Using trust zone IDs in dataflows (MOST COMMON ERROR)
# This is the #1 cause of OTM import failures
dataflows:
  - id: "bad-flow"
    source: "internet"  # ❌ Trust zone ID - IMPORT WILL FAIL
    destination: "dmz"  # ❌ Trust zone ID - IMPORT WILL FAIL
  
  - id: "another-bad-flow"
    source: "application"  # ❌ Trust zone ID - IMPORT WILL FAIL
    destination: "data"    # ❌ Trust zone ID - IMPORT WILL FAIL

# Why wrong? Trust zones are containers/locations, not things that communicate.
# You can't send data "to DMZ" - you send it to a component IN the DMZ.

# ❌ WRONG: Service nested in load balancer
# Load balancers route TO services, they don't host them
- id: "my-service"
  parent:
    component: "load-balancer"  # WRONG

# ❌ WRONG: Abbreviated component type
- id: "my-db"
  type: "postgres"  # WRONG - not exact referenceId

# ✅ CORRECT alternatives:
# Service runs in compute infrastructure (VM/container/serverless)
- id: "my-service"
  parent:
    component: "ecs-cluster"  # Runs in ECS

# Or if no compute infrastructure is modeled:
- id: "my-service"
  parent:
    trustZone: "application"  # Standalone in app zone

# Dataflow connects components
dataflows:
  - id: "good-flow"
    source: "load-balancer"  # Component ID
    destination: "my-service"  # Component ID

# Use exact referenceId from components.json
- id: "my-db"
  type: "CD-V2-POSTGRESQL-DATABASE"  # Exact referenceId
```

### Step 4: Map Components to IriusRisk Types

**Read `.iriusrisk/components.json`** (created by sync() in Step 0). Do NOT run CLI commands.

**Process:**
1. Search components.json for keywords related to your component
2. Find the `referenceId` field in matching component
3. Use exact `referenceId` as `type` in OTM

**Example:**
```json
// In components.json:
{
  "name": "AWS ECS Cluster",
  "referenceId": "CD-V2-AWS-ECS-CLUSTER",
  "category": "Container Orchestration"
}
```

```yaml
# In your OTM:
- id: "my-cluster"
  type: "CD-V2-AWS-ECS-CLUSTER"  # exact referenceId ✅
  # NOT: type: "aws-ecs" ❌ (abbreviated - fails)
```

### Step 5: import_otm() - Upload to IriusRisk

Call **import_otm("[path-to-otm-file.otm]")**

What happens:
- Validates and uploads OTM file to IriusRisk
- Creates new project or updates existing
- Triggers automatic threat generation
- Returns project ID, name, and status

### Step 6: project_status() - Verify Success

Call **project_status()**

Verifies:
- Project exists and accessible
- Import processing complete
- Project ready for use
- No error messages

### Step 7: Present Results & Offer Options

**Do NOT automatically run sync** - let user decide:

**Summary:** List components mapped, trust zones defined, dataflows created, confirm successful import.

**Offer options:**
- **A:** Download generated threats/countermeasures (sync again)
- **B:** Refine architecture first
- **C:** Ask questions before proceeding

**Why wait:** Gives IriusRisk time to process, lets user control pace, allows architecture refinement.

### Step 8: sync() Again - Download Security Findings (User Requested Only)

When user requests, call **sync(project_path)** again to download:
- Generated threats (threats.json)
- Generated countermeasures (countermeasures.json)
- Complete threat model data

### Step 9: threats_and_countermeasures() - Analysis Guidance

After downloading security data, call **threats_and_countermeasures()** to get instructions for:
- Reading threats.json and countermeasures.json
- Explaining security findings to users
- Generating code examples and implementation guidance
- Security analysis best practices

## Trust Zone Guidelines
- Internet (rating: 1) - External-facing, public APIs
- DMZ (rating: 3) - Load balancers, web servers
- Internal (rating: 7) - Application servers, internal APIs
- Secure (rating: 10) - Databases, auth servers

## Final Validation Checklist

Before completing:
- ☐ Used sync() first - Downloaded components.json
- ☐ Read components.json for component mapping (not CLI commands)
- ☐ Created OTM with ONLY architecture (no threats/controls)
- ☐ **Validated all dataflows use component IDs (not trust zone IDs)**
- ☐ Used exact referenceId values for component types
- ☐ Used import_otm() to upload
- ☐ Used project_status() to verify
- ☐ Presented user with options

**Remember:**
- AI role: Architecture modeling only
- IriusRisk role: Threat identification and security analysis (automatic)
- **MOST COMMON ERROR: Using trust zone IDs in dataflows instead of component IDs**
- **Before submitting OTM: Verify EVERY dataflow source/destination is a component ID from the components section above, NOT a trust zone ID**
"""
        logger.info("Provided CreateThreatModel instructions to AI assistant")
        return _apply_prompt_customizations('create_threat_model', instructions)
    
    @mcp_server.tool()
    async def track_threat_update(threat_id: str, status: str, reason: str, context: str = None, comment: str = None) -> str:
        """Track a threat status update for later synchronization with IriusRisk.
        
        Use this tool when implementing security measures that address specific threats.
        The updates will be applied to IriusRisk when the user runs the sync command.
        
        Args:
            threat_id: The UUID of the threat to update (use the "id" field from threats.json, 
                      NOT the "referenceId" field. Must be a UUID like "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            status: New status (accept, mitigate, expose, partly-mitigate, hidden)
            reason: Brief explanation of why the status is being changed
            context: Optional context about what was implemented or changed
            comment: HTML-formatted comment with implementation details, code snippets, and technical notes.
                    Use HTML tags: <p>, <strong>, <ul><li>, <code>, <pre>
            
        Returns:
            Status message indicating the update was tracked
        """
        logger.info(f"Tracking threat update via MCP: {threat_id} -> {status}")
        
        try:
            # Find project root and get update tracker
            project_root, _ = _find_project_root_and_config()
            if not project_root:
                return "Error: Could not find project directory with .iriusrisk folder. Make sure you're in a project directory or have run sync() first."
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the update
            success = tracker.track_threat_update(threat_id, status, reason, context, comment)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked threat update: {threat_id} -> {status}\nReason: {reason}\nPending updates: {stats['pending_updates']}\nUse sync() to apply updates to IriusRisk."
            else:
                return f"❌ Failed to track threat update for {threat_id}"
                
        except ValueError as e:
            return f"❌ Invalid threat status: {e}"
        except Exception as e:
            logger.error(f"Error tracking threat update: {e}")
            return f"❌ Error tracking threat update: {e}"
    
    @mcp_server.tool()
    async def track_countermeasure_update(countermeasure_id: str, status: str, reason: str, context: str = None, comment: str = None) -> str:
        """Track a countermeasure status update for later synchronization with IriusRisk.
        
        Use this tool when implementing countermeasures or security controls.
        The updates will be applied to IriusRisk when the user runs the sync command.
        
        CRITICAL - TWO-STEP PROCESS FOR ALL STATUS CHANGES:
        1. FIRST CALL: Update status with brief reason (NO comment parameter)
        2. SECOND CALL: Add detailed explanatory comment (WITH comment parameter)
        
        REQUIRED COMMENTS FOR ALL STATUS CHANGES:
        - required: Why necessary, what risks it addresses, business justification
        - implemented: What was implemented, how it works, testing approach  
        - rejected: Why not applicable, alternatives considered, reasoning
        - recommended: Why suggested, benefits, implementation considerations
        
        MANDATORY HTML FORMATTING: Comments MUST use HTML format for proper rendering in IriusRisk.
        Use these HTML tags (NEVER use markdown or plain text):
        - <p>...</p> for paragraphs (REQUIRED for all text blocks)
        - <strong>...</strong> for bold text (NOT **bold**)
        - <ul><li>...</li></ul> for bullet lists (NOT - bullets)
        - <code>...</code> for inline code (NOT `code`)
        - <pre>...</pre> for code blocks (NOT ```code```)
        
        CHARACTER LIMIT: Keep comments under 1000 characters due to IriusRisk API limitations.
        
        Args:
            countermeasure_id: The UUID of the countermeasure to update (use the "id" field from countermeasures.json, 
                              NOT the "referenceId" field. Must be a UUID like "3dc8a266-a837-4356-ad9a-b446c1535f54")
            status: New status (required, recommended, implemented, rejected, not-applicable)
            reason: Brief explanation of why the status is being changed
            context: Optional context about what was implemented or changed
            comment: REQUIRED for 'implemented' status - HTML-formatted comment with implementation details, 
                    code snippets, configuration changes, file paths, and testing approach
            
        Returns:
            Status message indicating the update was tracked
        """
        logger.info(f"Tracking countermeasure update via MCP: {countermeasure_id} -> {status}")
        
        try:
            # Check comment length limit (IriusRisk has ~1000 character limit)
            if comment and len(comment) > 1000:
                return f"❌ Error: Comment is {len(comment)} characters, but IriusRisk has a 1000 character limit. Please shorten the comment and try again."
            
            # Find project root and get update tracker
            project_root, _ = _find_project_root_and_config()
            if not project_root:
                return "Error: Could not find project directory with .iriusrisk folder. Make sure you're in a project directory or have run sync() first."
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the update
            success = tracker.track_countermeasure_update(countermeasure_id, status, reason, context, comment)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked countermeasure update: {countermeasure_id} -> {status}\nReason: {reason}\nPending updates: {stats['pending_updates']}\nUse sync() to apply updates to IriusRisk."
            else:
                return f"❌ Failed to track countermeasure update for {countermeasure_id}"
                
        except ValueError as e:
            return f"❌ Invalid countermeasure status: {e}"
        except Exception as e:
            logger.error(f"Error tracking countermeasure update: {e}")
            return f"❌ Error tracking countermeasure update: {e}"
    
    @mcp_server.tool()
    async def create_countermeasure_issue(countermeasure_id: str, issue_tracker_id: str = None) -> str:
        """Track an issue creation request for a countermeasure.
        
        This tool tracks a request to create a ticket in the issue tracker for the specified
        countermeasure. The issue will be created when the user runs the sync command.
        
        Use this tool when you want to create tracking tickets for countermeasures that
        need to be implemented or addressed by the development team.
        
        Args:
            countermeasure_id: The UUID of the countermeasure to create an issue for
                              (use the "id" field from countermeasures.json, NOT the "referenceId" field.
                              Must be a UUID like "3dc8a266-a837-4356-ad9a-b446c1535f54")
            issue_tracker_id: Optional specific issue tracker ID to use (if not provided, uses default)
            
        Returns:
            Status message indicating whether the issue creation request was tracked
        """
        logger.info(f"Tracking issue creation request for countermeasure via MCP: {countermeasure_id}")
        
        try:
            # Find project root and get update tracker
            project_root, project_config = _find_project_root_and_config()
            if not project_root:
                return "❌ Error: Could not find project directory with .iriusrisk folder. Make sure you're in a project directory or have run sync() first."
            
            if not project_config:
                return "❌ Error: Could not find project configuration. Make sure you have a valid project setup."
            
            # Check if there's a default issue tracker configured (unless specific one provided)
            if not issue_tracker_id:
                default_tracker = project_config.get('default_issue_tracker')
                if not default_tracker:
                    return "❌ Error: No default issue tracker configured and no specific tracker provided. Use 'iriusrisk issue-tracker set-default <tracker-name>' to configure a default."
                issue_tracker_id = default_tracker.get('id')
                tracker_name = default_tracker.get('name', 'default')
            else:
                tracker_name = issue_tracker_id
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            # Track the issue creation request
            success = tracker.track_issue_creation(countermeasure_id, issue_tracker_id)
            
            if success:
                stats = tracker.get_stats()
                return f"✅ Tracked issue creation request for countermeasure {countermeasure_id}\nIssue tracker: {tracker_name}\nPending updates: {stats['pending_updates']}\nUse sync() to create the issue in IriusRisk."
            else:
                return f"❌ Failed to track issue creation request for countermeasure {countermeasure_id}"
                
        except Exception as e:
            logger.error(f"Error tracking issue creation request: {e}")
            return f"❌ Error tracking issue creation request for countermeasure {countermeasure_id}: {e}"
    
    @mcp_server.tool()
    async def get_pending_updates() -> str:
        """Get all pending threat and countermeasure updates that haven't been synced yet.
        
        Returns:
            Summary of pending updates and statistics
        """
        logger.info("Getting pending updates via MCP")
        
        try:
            # Find project root and get update tracker
            project_root, _ = _find_project_root_and_config()
            if not project_root:
                return "Error: Could not find project directory with .iriusrisk folder. Make sure you're in a project directory or have run sync() first."
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            pending_updates = tracker.get_pending_updates()
            stats = tracker.get_stats()
            
            if not pending_updates:
                return "No pending updates. All tracked changes have been synchronized with IriusRisk."
            
            result = f"📋 Pending Updates Summary:\n"
            result += f"Total pending: {stats['pending_updates']}\n"
            result += f"Threats: {len([u for u in pending_updates if u['type'] == 'threat'])}\n"
            result += f"Countermeasures: {len([u for u in pending_updates if u['type'] == 'countermeasure'])}\n\n"
            
            result += "Recent Updates:\n"
            # Show last 10 pending updates
            for update in pending_updates[-10:]:
                result += f"- {update['type'].title()}: {update['id'][:8]}... -> {update['new_status']}\n"
                result += f"  Reason: {update['reason'][:60]}{'...' if len(update['reason']) > 60 else ''}\n"
                if update.get('context'):
                    result += f"  Context: {update['context'][:60]}{'...' if len(update['context']) > 60 else ''}\n"
                result += "\n"
            
            if len(pending_updates) > 10:
                result += f"... and {len(pending_updates) - 10} more updates\n\n"
            
            result += "Use sync() to apply these updates to IriusRisk."
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pending updates: {e}")
            return f"❌ Error getting pending updates: {e}"
    
    @mcp_server.tool()
    async def clear_updates() -> str:
        """Clear all tracked updates (both pending and applied).
        
        Use this tool carefully - it will remove all tracked status changes.
        This is useful if you want to start fresh or if there are issues with the updates.
        
        Returns:
            Status message indicating how many updates were cleared
        """
        logger.info("Clearing all updates via MCP")
        
        try:
            # Find project root and get update tracker
            project_root, _ = _find_project_root_and_config()
            if not project_root:
                return "Error: Could not find project directory with .iriusrisk folder. Make sure you're in a project directory or have run sync() first."
            
            iriusrisk_dir = project_root / '.iriusrisk'
            tracker = get_update_tracker(iriusrisk_dir)
            
            cleared_count = tracker.clear_all_updates()
            
            return f"✅ Cleared {cleared_count} tracked updates. The updates queue is now empty."
            
        except Exception as e:
            logger.error(f"Error clearing updates: {e}")
            return f"❌ Error clearing updates: {e}"
    
    @mcp_server.tool()
    async def list_standards(project_id: str = None) -> str:
        """List available standards for compliance reports.
        
        This tool lists all available compliance standards that can be used when generating compliance reports.
        Standards include OWASP Top 10, PCI DSS, NIST frameworks, ISO standards, and more.
        
        Args:
            project_id: Project ID to list standards for. Uses current project if not specified.
        
        Returns:
            List of available standards with names, reference IDs, and UUIDs.
        """
        try:
            from ..utils.project import resolve_project_id
            from ..api.project_client import ProjectApiClient
            
            logger.info(f"MCP list_standards called: project_id={project_id}")
            
            # Resolve project ID
            try:
                resolved_project_id = resolve_project_id(project_id)
                project_uuid = resolve_project_id_to_uuid_strict(resolved_project_id, api_client.project_client)
            except Exception as e:
                return f"❌ Error resolving project ID: {str(e)}"
            
            # Get standards using container API client
            standards = api_client.get_project_standards(project_uuid)
            
            if not standards:
                return "❌ No standards found for this project."
            
            results = []
            results.append("📋 Available standards for compliance reports:")
            results.append("")
            
            for standard in standards:
                name = standard.get('name', 'Unknown')
                reference_id = standard.get('referenceId', 'Unknown')
                standard_id = standard.get('id', 'Unknown')
                
                results.append(f"• **{name}**")
                results.append(f"  - Reference ID: `{reference_id}`")
                results.append(f"  - UUID: `{standard_id}`")
                results.append("")
            
            results.append("💡 Use the reference ID (e.g., 'owasp-top-10-2021') when generating compliance reports.")
            
            logger.info(f"MCP list_standards returned {len(standards)} standards")
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error in list_standards MCP tool: {e}")
            return f"❌ Failed to list standards: {str(e)}"
    
    @mcp_server.tool()
    async def generate_report(report_type: str = "countermeasure", format: str = "pdf", project_id: str = None, output_path: str = None, standard: str = None) -> str:
        """Generate and download an IriusRisk report.
        
        This tool generates various types of reports from IriusRisk projects and downloads them to the specified location.
        Use this when asked to create reports like "Create a compliance report" or "Generate a countermeasure report".
        
        Args:
            report_type: Type of report to generate. Options: "countermeasure", "threat", "compliance", "risk-summary". 
                        Also accepts natural language like "compliance report", "countermeasure report", etc.
            format: Output format for the report. Options: "pdf", "html", "xlsx", "csv", "xls". Defaults to "pdf".
            project_id: Project ID to generate report for. Uses current project if not specified.
            output_path: Where to save the report file. Auto-generates filename if not provided.
            standard: Standard reference ID or UUID for compliance reports (required for compliance reports).
                     Use list_standards() to see available options. Examples: "owasp-top-10-2021", "pci-dss-v4.0"
        
        Returns:
            Status message indicating success or failure with details.
        """
        try:
            from ..utils.project import resolve_project_id
            from ..api.project_client import ProjectApiClient
            import time
            from pathlib import Path
            
            logger.info(f"MCP generate_report called: type={report_type}, format={format}, project_id={project_id}")
            
            # Report type mappings - handle natural language
            report_mappings = {
                'countermeasure': 'technical-countermeasure-report',
                'countermeasures': 'technical-countermeasure-report',
                'countermeasure report': 'technical-countermeasure-report',
                'countermeasures report': 'technical-countermeasure-report',
                'technical countermeasure': 'technical-countermeasure-report',
                'technical countermeasure report': 'technical-countermeasure-report',
                
                'threat': 'technical-threat-report',
                'threats': 'technical-threat-report', 
                'threat report': 'technical-threat-report',
                'threats report': 'technical-threat-report',
                'technical threat': 'technical-threat-report',
                'technical threat report': 'technical-threat-report',
                
                'compliance': 'compliance-report',
                'compliance report': 'compliance-report',
                
                'risk': 'residual-risk',
                'risk summary': 'residual-risk',
                'risk-summary': 'residual-risk',
                'current risk': 'residual-risk',
                'current risk summary': 'residual-risk',
                'residual risk': 'residual-risk'
            }
            
            # Normalize report type
            normalized_type = report_type.lower().strip()
            if normalized_type in report_mappings:
                api_report_type = report_mappings[normalized_type]
                display_type = normalized_type.replace(' report', '').replace('technical ', '')
            else:
                return f"❌ Unknown report type: {report_type}. Supported types: countermeasure, threat, compliance, risk-summary"
            
            # Validate format
            supported_formats = ['pdf', 'html', 'xlsx', 'csv', 'xls']
            if format.lower() not in supported_formats:
                return f"❌ Unsupported format: {format}. Supported formats: {', '.join(supported_formats)}"
            
            format = format.lower()
            
            # Resolve project ID
            try:
                resolved_project_id = resolve_project_id(project_id)
                project_uuid = resolve_project_id_to_uuid_strict(resolved_project_id, api_client)
            except Exception as e:
                return f"❌ Error resolving project ID: {str(e)}"
            
            # Handle compliance reports that require a standard
            standard_uuid = None
            if normalized_type in ['compliance', 'compliance report']:
                if not standard:
                    return f"❌ Compliance reports require a 'standard' parameter. Use list_standards() to see available options."
                
                # Resolve standard reference ID to UUID if needed using container API client
                try:
                    # If it looks like a UUID, use it directly
                    if is_uuid_format(standard):
                        standard_uuid = standard
                    else:
                        # It's likely a reference ID, look it up
                        standards = api_client.get_project_standards(project_uuid)
                        for std in standards:
                            if std.get('referenceId') == standard:
                                standard_uuid = std.get('id')
                                break
                        
                        if not standard_uuid:
                            return f"❌ Standard '{standard}' not found. Use list_standards() to see available options."
                except Exception as e:
                    return f"❌ Error resolving standard: {str(e)}"
            
            # Generate output filename if not specified
            if not output_path:
                output_path = f"{display_type}_report.{format}"
            
            output_file = Path(output_path)
            
            results = []
            results.append(f"🔄 Generating {display_type} report in {format.upper()} format...")
            if standard_uuid:
                results.append(f"📋 Using standard: {standard}")
            
            # Generate the report using container API client
            try:
                operation_id = api_client.generate_report(
                    project_id=project_uuid,
                    report_type=api_report_type,
                    format=format,
                    standard=standard_uuid
                )
                
                if not operation_id:
                    return "❌ Failed to start report generation - no operation ID returned"
                    
                results.append(f"📋 Report generation started (operation ID: {operation_id})")
                
                # Poll for completion with timeout
                timeout = 300  # 5 minutes
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    status_response = api_client.get_async_operation_status(operation_id)
                    status = status_response.get('status')
                    
                    if status == 'finished-success':
                        results.append("✅ Report generation completed!")
                        break
                    elif status in ['finished-error', 'finished-failure', 'failed']:
                        error_msg = status_response.get('errorMessage', 'Unknown error')
                        return f"❌ Report generation failed: {error_msg}"
                    elif status in ['pending', 'in-progress']:
                        # Continue polling
                        time.sleep(2)
                    else:
                        return f"❌ Unknown operation status: {status}"
                else:
                    return f"❌ Report generation timed out after {timeout} seconds"
                
                # Get the generated report
                reports = api_client.get_project_reports(project_uuid)
                if not reports:
                    return "❌ No reports found after generation"
                
                # Find the most recent report of the correct type
                target_report = None
                for report in reports:
                    if (report.get('reportType') == api_report_type and 
                        report.get('format') == format):
                        target_report = report
                        break
                
                if not target_report:
                    return "❌ Generated report not found in project reports"
                
                # Get download URL from the report links
                download_url = target_report.get('_links', {}).get('download', {}).get('href')
                if not download_url:
                    return "❌ No download link found for the report"
                
                # Download the report
                results.append(f"📥 Downloading report to {output_file}...")
                content = api_client.download_report_content_from_url(download_url)
                
                # Save to file
                output_file.write_bytes(content)
                
                results.append(f"✅ Report successfully saved to {output_file}")
                results.append(f"📊 Report size: {len(content):,} bytes")
                
                logger.info(f"MCP report generated successfully: {output_file}")
                return "\n".join(results)
                
            except Exception as e:
                error_msg = f"❌ Error during report generation: {str(e)}"
                logger.error(f"MCP generate_report failed: {e}")
                return error_msg
                
        except Exception as e:
            logger.error(f"Error in generate_report MCP tool: {e}")
            return f"❌ Failed to generate report: {str(e)}"
    
    @mcp_server.tool()
    async def architecture_and_design_review() -> str:
        """Provides guidance for architecture and design reviews with optional threat modeling.
        
        **CALL THIS TOOL FOR:**
        - Architecture reviews: "Review the architecture", "Explain the system design"
        - Codebase understanding: "What does this project do?", "How does this system work?"
        - Design analysis: "Analyze the design", "Show me the components"
        - Security assessment: "Is this secure?", "What are the risks?", "Security review"
        - System documentation: "Document the architecture", "Explain the structure"
        
        This tool helps AI assistants determine whether to use existing threat models or recommend
        threat model creation based on user intent and context.
        
        Returns:
            Instructions for conducting architecture reviews and when to recommend threat modeling.
        """
        logger.info("MCP architecture_and_design_review called")
        
        guidance = """# Architecture and Design Review - Trigger Point

You've been asked to review architecture, design, or system structure.

## NEXT STEP: Call initialize_iriusrisk_workflow()

**Immediately call:**
```
initialize_iriusrisk_workflow()
```

That tool contains all the instructions for:
- How to check for existing threat model data
- Whether to use existing threat model or recommend creating one
- When to ask user permission vs. using automatically
- Complete workflow with proper sync() → check → decide → act

## Why?

The workflow tool has the complete decision logic for:
- Using existing threat models automatically (user's own work)
- Assessing user intent (security vs. general architecture request)
- Asking permission appropriately before creating new threat models
- Providing value regardless of user choice

## Remember

This tool is just a **trigger**. Don't try to replicate the workflow logic here. 
Call `initialize_iriusrisk_workflow()` immediately to get the full instructions."""

        logger.info("Provided architecture and design review guidance")
        return _apply_prompt_customizations('architecture_and_design_review', guidance)
    
    @mcp_server.tool()
    async def security_development_advisor() -> str:
        """Provides security guidance and recommendations for development work.
        
        Call this tool when developers are:
        - Planning security-impacting changes (integrations, data handling, auth changes)
        - Asking about security implications of their work
        - Working on features that cross trust boundaries
        - Making architectural or infrastructure changes
        
        This tool helps assess security impact and recommend when threat modeling would be valuable,
        while respecting developer autonomy and workflow.
        
        Returns:
            Security assessment and guidance on when to recommend threat modeling.
        """
        
        guidance = """# Security Development Advisor

## Purpose

Help developers assess security impact of their work and recommend threat modeling when appropriate, while respecting their autonomy and workflow.

## Step 1: Check for Existing Threat Model

**Call sync() to see what exists**

### If Threat Model Exists (threats.json has data)

**Automatically use it for security guidance:**
- The developer has already invested in threat modeling
- Read threats.json and countermeasures.json
- Provide security guidance based on existing threat analysis
- Suggest updates if their planned work impacts the threat model

Example response:
```
"I see you have a threat model. Let me check what security considerations 
apply to [their work]...

[Provide guidance based on threat model data]

Note: Your planned change may require updating the threat model. Would you 
like help with that?"
```

## Step 2: Assess Security Impact (No Existing Threat Model)

**Categorize the developer's work:**

### High Security Impact
- Third-party integrations (payment processors, auth providers, external APIs)
- Sensitive data handling (PII, financial, health information, credentials)
- Authentication/authorization changes
- Public-facing endpoints or APIs
- Changes crossing trust boundaries

**Recommendation strength: STRONG**

Response:
```
"This work has significant security implications. I strongly recommend creating 
a threat model to identify potential issues early. This is especially important 
for [specific risk, e.g., 'payment integrations' or 'handling customer data'].

Benefits:
- Identify security issues during development, not in production
- Get specific countermeasure recommendations
- Meet compliance requirements (PCI DSS, SOC 2, etc.)
- Takes about 10-15 minutes to set up

Would you like me to help create a threat model?

[Wait for response]
- If YES → Call initialize_iriusrisk_workflow() and proceed
- If NO → Provide general security guidance with disclaimer about limitations
```

### Medium Security Impact  
- Internal API changes
- Database schema modifications
- Infrastructure updates
- Microservice additions

**Recommendation strength: MODERATE**

Response:
```
"For this type of work, a threat model would help identify security considerations.

I can help create one if you'd like, or provide general security guidance for now.
What would you prefer?

[Wait for response - proceed based on user choice]
```

### Low Security Impact
- UI changes
- Internal refactoring
- Documentation updates
- Performance optimizations

**Recommendation strength: LIGHT MENTION**

Response:
```
[Provide requested guidance]

[Optionally at end: "If you want a comprehensive security analysis for this project, 
I can help create a threat model. Just let me know."]
```

## Step 3: Provide Value Regardless of Choice

### If User Agrees to Threat Modeling

1. Call `initialize_iriusrisk_workflow()` for complete instructions
2. Follow the workflow to create/update threat model
3. Present integrated security guidance

### If User Declines

**Provide helpful security guidance anyway:**
- General security best practices for their work
- Common vulnerabilities to watch for
- Framework/library security recommendations
- Remind them: "Threat modeling is available anytime if you change your mind"

## Key Principles

1. **Use existing threat models automatically** - No permission needed
2. **High-impact changes = strong recommendation** - But still let user decide
3. **Medium-impact changes = offer as option** - Balanced suggestion
4. **Low-impact changes = light mention** - Don't be pushy
5. **Always provide value** - Security advice is useful even without threat modeling
6. **Respect workflow** - Don't disrupt developers who are in the zone

## DO NOT

- ❌ Force threat modeling on developers working on low-risk changes
- ❌ Automatically create threat models without permission
- ❌ Make developers feel guilty for declining
- ❌ Interrupt flow for trivial changes
- ✅ Make compelling case for high-risk work
- ✅ Provide useful security advice regardless of choice
- ✅ Remember threat modeling is available if they change their mind

## Example Scenarios

**Scenario 1: Adding Stripe integration**
→ High impact → Strong recommendation → Get permission → Proceed if YES

**Scenario 2: Refactoring internal function**
→ Low impact → Provide advice → Light mention of threat modeling available

**Scenario 3: Building new REST API**
→ Medium-high impact → Strong recommendation → Let user decide

**Scenario 4: User explicitly asks "Is this secure?"**
→ Clear security intent → Strong recommendation → Get permission → Proceed if YES"""

        logger.info("MCP security_development_advisor called")
        return _apply_prompt_customizations('security_development_advisor', guidance)
    
    @mcp_server.tool()
    async def list_project_versions(project_id: str = None) -> str:
        """List all version snapshots for a project.
        
        This tool lists all saved version snapshots of a project. Versions are point-in-time
        snapshots that can be used to track changes, compare different states, or restore
        previous configurations.
        
        Args:
            project_id: Project UUID or reference ID (optional if project.json exists in current directory)
            
        Returns:
            Formatted list of versions with details about each snapshot.
        """
        logger.info(f"MCP list_project_versions called with project_id={project_id}")
        
        try:
            from ..container import get_container
            from ..services.version_service import VersionService
            
            container = get_container()
            version_service = container.get(VersionService)
            
            # Resolve project ID
            if not project_id:
                project_root, project_config = find_project_root()
                if project_config:
                    project_id = project_config.get('project_id')
                
                if not project_id:
                    return "❌ No project ID provided and no project.json found in current directory"
            
            # Resolve to UUID
            resolved_project_id = resolve_project_id_to_uuid_strict(project_id)
            logger.info(f"Resolved project ID to UUID: {resolved_project_id}")
            
            # List versions
            result = version_service.list_versions(resolved_project_id, page=0, size=50)
            versions = result.get('versions', [])
            total = result.get('page_info', {}).get('totalElements', 0)
            
            if not versions:
                return f"📋 No versions found for project {project_id}\n\nℹ️  Versions are snapshots created manually or automatically during OTM imports when auto_versioning is enabled."
            
            # Format output
            output = [f"📋 Project Versions for {project_id}"]
            output.append(f"   Total versions: {total}")
            output.append("")
            
            for idx, version in enumerate(versions, 1):
                version_id = version.get('id', 'Unknown')
                name = version.get('name', 'Unnamed')
                description = version.get('description', 'No description')
                created = version.get('creationDate', 'Unknown')
                created_by = version.get('creationUser', 'Unknown')
                operation = version.get('operation', 'none')
                
                output.append(f"{idx}. {name}")
                output.append(f"   ID: {version_id}")
                output.append(f"   Description: {description}")
                output.append(f"   Created: {created}")
                output.append(f"   Created by: {created_by}")
                output.append(f"   Status: {operation}")
                output.append("")
            
            logger.info(f"Successfully listed {len(versions)} versions for project {resolved_project_id}")
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"❌ Failed to list project versions: {str(e)}"
            logger.error(f"MCP list_project_versions failed: {e}")
            return error_msg
    
    @mcp_server.tool()
    async def create_project_version(name: str, description: str = None, project_id: str = None) -> str:
        """Create a new version snapshot of a project.
        
        This tool creates a point-in-time snapshot of a project's current state. The snapshot
        includes all threat model data, components, threats, and countermeasures. This is useful
        for tracking changes over time or creating backups before making significant modifications.
        
        Args:
            name: Name for the version (e.g., "v1.0", "Before API refactor")
            description: Optional description of what this version represents
            project_id: Project UUID or reference ID (optional if project.json exists in current directory)
            
        Returns:
            Success message with version details or error message.
        """
        logger.info(f"MCP create_project_version called: name={name}, project_id={project_id}")
        
        try:
            from ..container import get_container
            from ..services.version_service import VersionService
            
            container = get_container()
            version_service = container.get(VersionService)
            
            # Resolve project ID
            if not project_id:
                project_root, project_config = find_project_root()
                if project_config:
                    project_id = project_config.get('project_id')
                
                if not project_id:
                    return "❌ No project ID provided and no project.json found in current directory"
            
            # Resolve to UUID
            resolved_project_id = resolve_project_id_to_uuid_strict(project_id)
            logger.info(f"Resolved project ID to UUID: {resolved_project_id}")
            
            # Create version (with wait=True to ensure it completes)
            result = version_service.create_version(
                project_id=resolved_project_id,
                name=name,
                description=description,
                wait=True,
                timeout=300
            )
            
            # Check if successful
            state = result.get('state', '').lower()
            if state == 'completed':
                output = [f"✅ Version created successfully!"]
                output.append(f"   Name: {name}")
                if description:
                    output.append(f"   Description: {description}")
                output.append(f"   Project: {project_id}")
                output.append("")
                output.append("ℹ️  The version snapshot has been saved and can be used for:")
                output.append("   • Comparing changes between versions")
                output.append("   • Restoring previous configurations (via UI)")
                output.append("   • Tracking threat model evolution")
                
                logger.info(f"Successfully created version '{name}' for project {resolved_project_id}")
                return "\n".join(output)
            else:
                error_msg = result.get('errorMessage', 'Unknown error')
                return f"❌ Version creation failed: {error_msg}"
            
        except Exception as e:
            error_msg = f"❌ Failed to create project version: {str(e)}"
            logger.error(f"MCP create_project_version failed: {e}")
            return error_msg

    try:
        logger.info("MCP server initialized successfully")
        # Run the MCP server with stdio transport
        mcp_server.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        click.echo(f"Error starting MCP server: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    mcp()
