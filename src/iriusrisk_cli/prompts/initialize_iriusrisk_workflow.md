# IriusRisk MCP Workflow Instructions for AI Assistants

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
