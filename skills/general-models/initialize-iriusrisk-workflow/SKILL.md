---
name: initialize-iriusrisk-workflow
description: Complete workflow instructions for IriusRisk threat modeling. Use when starting any threat modeling task. Provides decision logic for using existing threat models, creating new ones, and when to ask permission.
disable-model-invocation: true
---

# IriusRisk MCP Workflow Instructions

## 🚨 CRITICAL: Distinguish "THREAT MODELING" vs "THREAT ANALYSIS"

### These are COMPLETELY DIFFERENT workflows:

**1. THREAT MODELING = Architecture Creation/Update**
- **User says**: 
  - "Threat model this"
  - "Create a threat model"
  - "We need to threat model [the application/infrastructure/etc.]"
  - "Update the threat model"
  - "Add [authentication/payments/frontend] to the threat model"
  - "Model the architecture for security"
  
- **What it means**: Model the ARCHITECTURE (components, data flows) - CREATE or UPDATE an OTM file
- **Tool to call**: `create_threat_model()` 
- **You analyze**: Source code → Extract architecture → Create/merge OTM → Import to IriusRisk
- **Ignore**: threats.json, countermeasures.json (not relevant for architecture modeling)
- **Even if**: threats.json exists, still do architecture modeling when explicitly requested

**2. THREAT ANALYSIS = Security Review of Existing Threats**
- **User says**: 
  - "What threats exist?"
  - "Show me the threats"
  - "Review security issues"
  - "What's our security posture?"
  - "What vulnerabilities did IriusRisk find?"
  - "Help me understand the threats"
  
- **What it means**: Analyze EXISTING threats that IriusRisk already generated
- **Tool to call**: `threats_and_countermeasures()`
- **You analyze**: threats.json and countermeasures.json files
- **Ignore**: Source code architecture (already modeled)
- **Prerequisites**: threats.json must exist with threat data

**🚨 KEY RULE: "Threat model" (verb) = architecture workflow. "Show threats" (noun) = analysis workflow.**

## Critical Rules

### 1. Use MCP Tools, Not CLI Commands
**NEVER** run CLI commands like `iriusrisk countermeasures list`, `iriusrisk threats list`, or `iriusrisk sync`.  
**ALWAYS** use MCP tools instead:
- Use `sync()` MCP tool (not `iriusrisk sync` CLI command)
- Read JSON files from `.iriusrisk/` directory (not CLI list commands)
- Call MCP tools directly without asking user permission

### 2. ALWAYS sync() First - Use Identical Merge Logic

**CRITICAL RULES:**
1. **ALWAYS call sync() FIRST** - before any threat modeling operation
2. **ALL updates use IDENTICAL merge logic** - whether single-repo or multi-repo
3. **ALL OTM files go in `.iriusrisk/` directory** with temporary naming
4. **ALWAYS preserve existing components and layout** when merging

### 3. Countermeasure Updates Require Two Calls
The IriusRisk API requires status updates and comments to be sent separately. For ANY countermeasure status change:

**Step 1:** Update status only (no comment parameter)
```
track_countermeasure_update(countermeasure_id="...", status="implemented", reason="Added input validation", project_path="/absolute/path/to/project")
```

**Step 2:** Add explanatory comment (with HTML formatting)
```
track_countermeasure_update(countermeasure_id="...", status="implemented", reason="Adding details", project_path="/absolute/path/to/project",
  comment="<p><strong>Implementation:</strong></p><ul><li>Added validation in api.py</li></ul>")
```

### 4. Automatic Sync After Updates
**MANDATORY BEHAVIOR:** After calling `track_threat_update()` or `track_countermeasure_update()`, you MUST immediately call `sync()` to push changes to IriusRisk.

**DO NOT:**
- Ask "Would you like me to sync now?"
- Suggest the user runs a CLI command
- Wait to see if there are more updates coming
- Ask for permission to sync

**ALWAYS:**
- Call `sync(project_path="/absolute/path")` immediately after tracking updates
- Use the MCP tool, not CLI commands
- Complete the full workflow automatically

## Decision Tree After sync()

**Check user's original request FIRST, then check files:**

### Priority 1: Explicit Threat Modeling Request? (Architecture Creation/Update)
- User said "threat model", "create threat model", "update threat model", "we need to threat model [X]"?
- **YES** → Call `create_threat_model()` immediately
  - **Do NOT call threats_and_countermeasures()**
  - **Do NOT analyze threats.json**
  - **Do NOT show diagram**
  - **DO**: Analyze source code → Create/merge OTM → Import architecture
- **NO** → Continue to Priority 2

### Priority 2: Explicit Threat Analysis Request? (Security Review)
- User said "show me threats", "what are the security issues", "review threats", "what's our security posture"?
- **YES** → Check if threats.json exists with data
  - If yes: Call `threats_and_countermeasures()` and analyze
  - If no: Explain no threats exist yet, offer to create threat model
- **NO** → Continue to Priority 3

### Priority 3: General Architecture/Security Review? (Ambiguous)
- User said something vague: "review this", "look at my code", "explain the system"
- Check what files exist and assess intent

## Available Tools

### Architecture & Design Review (START HERE for architecture questions)
1. **architecture_and_design_review()** - PRIMARY tool for architecture/design/security reviews

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

### Status Tracking Tools
12. **track_threat_update(threat_id, status, reason, project_path, context, comment)** - Track threat status changes
13. **track_countermeasure_update(countermeasure_id, status, reason, project_path, context, comment)** - Track countermeasure status changes

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
1. sync(project_path) - Download current threats/countermeasures
2. threats_and_countermeasures() - Get analysis guidance
3. [Implement security measures in code]
4. track_threat_update(..., project_path) / track_countermeasure_update(..., project_path) - Track changes
5. **IMMEDIATELY call sync(project_path)** - Automatically apply updates to IriusRisk
6. [Verify updated statuses in downloaded JSON]

## Key Best Practices
- Always call `sync()` FIRST to download available data
- Check what `sync()` downloaded to determine next steps
- Use MCP tools and JSON files, not CLI commands
- Use two separate calls for countermeasure status changes
- **After tracking updates, immediately call sync()** - Don't batch, don't wait, don't ask permission
- Use HTML formatting in comments (not Markdown)
- **DO NOT invent threats** - read them from `threats.json` or create OTM to generate them

---

This skill provides the complete workflow guidance for all IriusRisk threat modeling operations.
