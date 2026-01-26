# IriusRisk MCP Workflow Instructions for AI Assistants

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

### Example: Multi-Repository Scenario

**Situation**: Infrastructure threat model already exists. User now in application repo says:
> "We need to threat model the application stack"

**What AI should do**:
1. ✅ Call `sync()` - downloads current-threat-model.otm (infrastructure)
2. ✅ Call `create_threat_model()` - gets architecture workflow instructions
3. ✅ Read current-threat-model.otm (see existing infrastructure components)
4. ✅ Analyze application source code (extract API services, business logic)
5. ✅ Create merged OTM (application components + infrastructure components)
6. ✅ Call `import_otm()` - upload merged model
7. ✅ Stop and offer next steps

**What AI should NOT do**:
- ❌ Call `threats_and_countermeasures()` - user didn't ask for threat analysis
- ❌ Analyze threats.json - user wants to model architecture, not review threats
- ❌ Show diagram - premature, do this after import if needed
- ❌ Ask "What would you like to do?" - user already told you what to do

**The phrase "threat model the application stack" is a VERB (action) not NOUN (review).**

---

## Executive Summary
This MCP provides AI assistants with tools for professional threat modeling via IriusRisk CLI. Always use MCP tools and JSON files instead of direct CLI commands.

## CRITICAL: User Intent and Threat Modeling Workflow

### 🚨 EXPLICIT THREAT MODELING REQUESTS - HIGHEST PRIORITY

**When user explicitly requests threat modeling, ALWAYS call create_threat_model() workflow, even if threats.json exists:**

User says:
- "Create a threat model"
- "Threat model this code/application/system"
- "We need to threat model [the application/infrastructure/etc.]"
- "Update the threat model"
- "Add [X] to the threat model"

**Action: Immediately call create_threat_model() - DO NOT analyze existing threats**

1. Call `create_threat_model()` to get workflow instructions
2. Follow the threat modeling workflow (sync → analyze → create OTM → import)
3. **IGNORE the presence of threats.json/countermeasures.json** - user wants to model architecture, not analyze threats

**🚨 CRITICAL: User's explicit request to "threat model" means they want to CREATE/UPDATE the architecture model, NOT analyze existing threats.**

The presence of `threats.json` is irrelevant when user explicitly requests threat modeling. They want to update the model itself, not review threats.

---

### Decision Tree After sync()

**Check user's original request FIRST, then check files:**

#### Priority 1: Explicit Threat Modeling Request? (Architecture Creation/Update)
- User said "threat model", "create threat model", "update threat model", "we need to threat model [X]"?
- **YES** → Call `create_threat_model()` immediately
  - **Do NOT call threats_and_countermeasures()**
  - **Do NOT analyze threats.json**
  - **Do NOT show diagram**
  - **DO**: Analyze source code → Create/merge OTM → Import architecture
- **NO** → Continue to Priority 2

#### Priority 2: Explicit Threat Analysis Request? (Security Review)
- User said "show me threats", "what are the security issues", "review threats", "what's our security posture"?
- **YES** → Check if threats.json exists with data
  - If yes: Call `threats_and_countermeasures()` and analyze
  - If no: Explain no threats exist yet, offer to create threat model
- **NO** → Continue to Priority 3

#### Priority 3: General Architecture/Security Review? (Ambiguous)
- User said something vague: "review this", "look at my code", "explain the system"
- Check what files exist and assess intent (see scenarios below)

---

### Scenario A: User Wants Threat ANALYSIS (Not Threat MODELING)

**Indicators:**
- User said: "What threats exist?", "Show me security issues", "Review the threats", "What's the current security posture?"
- Files exist: `threats.json` and `countermeasures.json` with data

**Action: Analyze existing threats**
1. Call `threats_and_countermeasures()` for analysis guidance
2. Read and analyze threats.json and countermeasures.json files
3. Present security findings

**DO NOT use this scenario when user said "threat model" - that's Scenario B**

### Scenario B: User Wants Threat MODELING (Creating/Updating Architecture)

**Indicators:**
- User said: "Create threat model", "Threat model this", "Update the threat model", "We need to threat model [X]"
- **This applies even if threats.json exists** - they want to update the architecture model

**Action: Create or update threat model**
1. Call `create_threat_model()` to get workflow instructions
2. Check for `.iriusrisk/current-threat-model.otm`
3. If exists: MERGE your contribution with existing architecture
4. If not: CREATE new architecture model
5. Follow full workflow: analyze code → create OTM → import_otm()

### Scenario C: Vague Request, No Threats Downloaded

Files present:
- ✅ `project.json` but NO `threats.json` or empty
- ⚠️ `current-threat-model.otm` may or may not exist

**Action: Assess intent and ask permission**

User said something vague like "review this code" or "look at my architecture"
- Determine if security-focused or general review
- Ask permission before creating threat model

### Scenario C: No Threat Model, User Intent Unclear (Ask Permission)

User said something vague like:
- "Review the architecture" (not explicit about security)
- "How does this work?"
- "Explain the system"

**Response to user:**
```
"I can provide an architecture review. Would you also like me to create 
an IriusRisk threat model for systematic security analysis?"
```

**Wait for user response before creating threat model**

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
**NEVER** run CLI commands like `iriusrisk countermeasures list`, `iriusrisk threats list`, or `iriusrisk sync`.  
**ALWAYS** use MCP tools instead:
- Use `sync()` MCP tool (not `iriusrisk sync` CLI command)
- Read JSON files from `.iriusrisk/` directory (not CLI list commands)
- Call MCP tools directly without asking user permission

Example: Instead of suggesting "Run `iriusrisk sync`", immediately call `sync(project_path="/absolute/path")`

### 2. Countermeasure Updates Require Two Calls
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
12. **track_threat_update(threat_id, status, reason, project_path, context, comment)** - Track threat status changes for later sync (status: accept/mitigate/expose/partly-mitigate/hidden)
13. **track_countermeasure_update(countermeasure_id, status, reason, project_path, context, comment)** - Track countermeasure status changes (see Two-Call Rule above)
14. **get_pending_updates(project_path)** - Review pending updates before sync
15. **clear_updates(project_path)** - Clear update queue
16. **create_countermeasure_issue(countermeasure_id, project_path, issue_tracker_id)** - Queue issue tracker ticket creation

**CRITICAL:** Always pass `project_path` parameter with the ABSOLUTE path to the project directory (where `.iriusrisk` is located) to all update tracking functions.

### 3. Automatic Sync After Updates
**MANDATORY BEHAVIOR:** After calling `track_threat_update()` or `track_countermeasure_update()`, you MUST immediately call `sync()` to push changes to IriusRisk.

**Why this is required:**
- Updates are queued locally until sync() is called
- The user expects changes to be applied immediately after tracking
- Delaying sync creates confusion about whether changes were applied
- The workflow is incomplete without syncing

**DO NOT:**
- Ask "Would you like me to sync now?"
- Suggest the user runs a CLI command
- Wait to see if there are more updates coming
- Ask for permission to sync

**ALWAYS:**
- Call `sync(project_path="/absolute/path")` immediately after tracking updates
- Use the MCP tool, not CLI commands
- Complete the full workflow automatically

**Example correct behavior:**
```
1. User: "Mark countermeasure X as implemented"
2. AI calls: track_countermeasure_update(...)
3. AI immediately calls: sync(project_path="...")
4. AI reports: "✅ Countermeasure marked as implemented and synced to IriusRisk"
```

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
4. track_threat_update(..., project_path) / track_countermeasure_update(..., project_path) - Track changes (remember: two calls for countermeasures, always pass project_path)
5. **IMMEDIATELY call sync(project_path)** - Automatically apply updates to IriusRisk (DO NOT ask permission, just run it)
6. [Verify updated statuses in downloaded JSON]

**CRITICAL: After tracking ANY updates (threats or countermeasures), you MUST automatically call sync(project_path) to apply them to IriusRisk. DO NOT:**
- Ask the user if they want to sync
- Suggest running CLI commands like `iriusrisk sync`
- Wait or batch multiple updates (sync after each tracking operation)
- Require user permission to sync

**ALWAYS:** Immediately call the sync() MCP tool after tracking updates.

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
- **After tracking updates, immediately call sync()** - Don't batch, don't wait, don't ask permission
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
**AI:** Make two calls to track_countermeasure_update(), then immediately call sync():
1. Update status: `countermeasure_id="...", status="implemented", reason="Added input validation", project_path="/absolute/path/to/project"`
2. Add comment: `countermeasure_id="...", status="implemented", reason="Adding details", project_path="/absolute/path/to/project", comment="<p><strong>Implementation:</strong></p><ul><li>Added validation middleware in api.py</li></ul>"`
3. **Immediately call sync(project_path="/absolute/path/to/project")** to apply changes to IriusRisk (don't ask, just do it)

**User:** "Find the SQL injection countermeasure"  
**AI:** ✅ Read `.iriusrisk/countermeasures.json` and search programmatically  
(NOT: ❌ Run `iriusrisk countermeasures list`)

## Reference: Countermeasure Update Example

```python
# Step 1: Update status
track_countermeasure_update(
    countermeasure_id="abc-123",
    status="implemented",
    reason="Implemented input validation",
    project_path="/absolute/path/to/project"
)

# Step 2: Add detailed comment
track_countermeasure_update(
    countermeasure_id="abc-123",
    status="implemented",
    reason="Adding implementation details",
    project_path="/absolute/path/to/project",
    comment="<p><strong>Implementation:</strong></p><ul><li>Added middleware in <code>api.py</code></li><li>Uses pydantic validation</li></ul>"
)
```

## Technical Notes
- MCP communicates via stdio
- Logging: logs/mcp_server.log
- All tools are asynchronous and return strings
