# CI/CD Drift Detection Feature

**Status:** In Development  
**Target:** v0.5.0  
**Purpose:** Design document for AI-powered security drift detection in CI/CD pipelines

**Implementation Approach:** Version-based comparison using IriusRisk project versions

## Problem Statement

Customers need AI-powered verification in CI/CD pipelines to detect when code being deployed diverges from approved security baselines. Engineering teams make architectural changes (adding components, modifying dataflows) without security review, and these changes aren't caught until much later.

### Key Pain Points
- Developers add unapproved components (Redis, external APIs, new services)
- Security-relevant architectural changes go unnoticed
- Security reviews happen too late in the process
- No automated visibility into drift from approved state

## Solution Approach

**Core Concept:** Visibility, not enforcement

Provide AI agents with the ability to:
1. Compare different states of a threat model (versions, current state, proposed changes)
2. Surface architectural changes (components, dataflows, trust zones) AND security changes (threats, countermeasures)
3. Generate human-readable reports for manual review
4. Post findings to PRs/tickets for security team review

**Key Technical Approach:**
- Leverage IriusRisk project versions for baseline management
- Support multiple comparison modes (see Comparison Modes section)
- Compare architecture (diagram XML) AND security (threats/countermeasures JSON)
- Isolated verification workspace (`.iriusrisk/verification/`) for safe operations
- Python tool does heavy lifting (parsing, diffing), AI does interpretation

**NOT in scope for MVP:**
- Automated approval/rejection decisions
- Policy rule engines
- Enforcement gates
- Approved component lists

## Comparison Modes

The tool supports four distinct comparison scenarios:

### Mode 1: Current Project vs. New Changes (OTM)
**Use Case:** PR review, local development changes
**Baseline:** Current IriusRisk project state (no version specified)
**Target:** AI-generated OTM from code changes

**Workflow:**
1. AI analyzes code changes and generates OTM
2. Tool downloads current project state (diagram, threats, countermeasures)
3. Tool imports OTM to IriusRisk (triggers threat computation)
4. Tool creates temporary version snapshot of OTM state
5. Tool compares current vs. temporary version
6. Tool restores project to current state
7. Tool deletes temporary version
8. AI interprets diff

**Parameters:**
- `otm_content`: AI-generated OTM
- `baseline_version`: None (use current project state)

### Mode 2: Specific Version vs. New Changes (OTM)
**Use Case:** CI/CD comparing PR against approved baseline
**Baseline:** Tagged version (e.g., "v2.1-approved")
**Target:** AI-generated OTM from code changes

**Workflow:**
1. AI analyzes code changes and generates OTM
2. Tool downloads baseline version state (diagram, threats, countermeasures)
3. Tool imports OTM to IriusRisk (triggers threat computation)
4. Tool creates temporary version snapshot of OTM state
5. Tool compares baseline version vs. temporary version
6. Tool restores project to baseline version
7. Tool deletes temporary version
8. AI interprets diff

**Parameters:**
- `otm_content`: AI-generated OTM
- `baseline_version`: Version ID (e.g., UUID or "v2.1-approved")

**Note:** This is the primary CI/CD use case from the original design.

### Mode 3: Specific Version vs. Current Project
**Use Case:** "How has the project drifted since last approval?"
**Baseline:** Tagged version (e.g., "baseline-2024-01-12")
**Target:** Current IriusRisk project state

**Workflow:**
1. Tool downloads baseline version state
2. Tool downloads current project state
3. Tool compares baseline version vs. current state
4. AI interprets diff
5. No import, no restoration, no temporary version needed

**Parameters:**
- `otm_content`: None
- `baseline_version`: Version ID
- `comparison_target`: "current" (default)

**Note:** Read-only operation, safest mode.

### Mode 4: Version vs. Version
**Use Case:** "What changed between two approved baselines?"
**Baseline:** Older version (e.g., "baseline-v1.0")
**Target:** Newer version (e.g., "baseline-v2.0")

**Workflow:**
1. Tool downloads baseline version state
2. Tool downloads target version state
3. Tool compares baseline version vs. target version
4. AI interprets diff
5. No import, no restoration, no temporary version needed

**Parameters:**
- `otm_content`: None
- `baseline_version`: Version ID (older)
- `target_version`: Version ID (newer)

**Note:** Completely read-only, useful for auditing historical changes.

### Comparison Mode Summary

| Mode | Baseline Source | Target Source | OTM Import? | Restoration? | Temp Version? | Risk Level |
|------|----------------|---------------|-------------|--------------|---------------|------------|
| 1 | Current project | New OTM | Yes | Yes | Yes | Medium |
| 2 | Version | New OTM | Yes | Yes | Yes | Medium |
| 3 | Version | Current project | No | No | No | Low |
| 4 | Version | Version | No | No | No | Low |

**Implementation Priority:**
- **MVP:** Mode 2 (CI/CD primary use case)
- **Phase 2:** Mode 3 (drift detection)
- **Phase 3:** Mode 1 and 4 (advanced use cases)

## High-Level Workflow

### One-Time Setup
1. Security team reviews and approves initial threat model in IriusRisk
2. Create version snapshot in IriusRisk (e.g., "v2.1-approved" or "baseline-2024-01-12")
3. Configure CI/CD to reference the approved baseline version
4. Configure CI/CD to run AI verification on PRs/deployments

### General Verification Workflow

**Example: CI/CD PR Review (Mode 2 - Version vs. OTM)**

1. **CI/CD triggers** → AI agent activates
2. **AI generates OTM** → Analyzes PR code changes
3. **AI calls `ci_cd_verification` tool** with OTM and baseline version → Python tool:
   - Downloads baseline version state
   - Imports OTM, waits for threat computation
   - Creates temporary version snapshot
   - Downloads target state
   - Parses and compares both states (diagram XML, threats, countermeasures)
   - Generates structured diff
   - Restores project to baseline
   - Deletes temporary version
   - Cleans up verification files
   - Returns structured diff to AI
4. **AI interprets structured diff** → Assesses security implications
5. **AI generates report** → Human-readable findings with context
6. **Post results** → PR comment, Slack, ticket, etc.
7. **Human review** → Security team decides if acceptable

**Example: Drift Detection (Mode 3 - Version vs. Current)**

1. **Security team or scheduled job** → Triggers drift check
2. **AI calls `ci_cd_verification` tool** with baseline version only → Python tool:
   - Downloads baseline version state
   - Downloads current project state
   - Parses and compares both states
   - Generates structured diff
   - Returns results (no restoration, no temporary version)
3. **AI interprets structured diff** → Identifies accumulated drift
4. **AI generates report** → Summary of changes since baseline
5. **Report sent to security team** → Email, Slack, dashboard

**Example: Version Comparison (Mode 4 - Version vs. Version)**

1. **Security audit or review** → Need to understand changes between baselines
2. **AI calls `ci_cd_verification` tool** with baseline and target versions → Python tool:
   - Downloads baseline version state
   - Downloads target version state
   - Parses and compares both states
   - Generates structured diff
   - Returns results (read-only, no changes to project)
3. **AI interprets structured diff** → Analyzes evolution of threat model
4. **AI generates report** → Historical change analysis

**Division of Labor:**
- **Python:** Deterministic operations, parsing, diffing, API orchestration, state management
- **AI:** Codebase analysis (when needed), interpretation, communication, decision support

**Note:** Both baseline and verification files are temporary working storage, created and deleted during each verification run.

### What AI Reports

**Architectural Changes:**
- Components added/removed/modified (type, trust zone, purpose)
- Dataflows added/removed/modified (source, destination, data types)
- Trust zone changes (components moved, new zones)

**Security Changes:**
- Threats added/removed/modified (severity, affected components)
- Countermeasures added/removed/modified (status, effectiveness)
- Risk level changes

**Context and Assessment:**
- Security impact assessment for each change
- Relationship between architectural and security changes
- Recommendations for security review

### Human Decision Points
- Is the new component acceptable?
- Are the architectural changes appropriate?
- Do new threats have adequate mitigations?
- Does this require architecture review?

## Technical Components

### Version-Based Comparison

The comparison leverages IriusRisk's version system:

**Architecture Comparison:**
- Parse and compare diagram XML files to identify component, dataflow, and trust zone changes
- Uses IriusRisk's diagram export format

**Security Comparison:**
- Compare threats and countermeasures JSON files
- Uses IriusRisk's computed threat model (not just architecture)

**Key Benefits:**
- **Ephemeral:** Fresh baseline download each run, no stale data
- **Comprehensive:** Compares both architecture AND security implications
- **Safe:** Isolated workspace, never touches main files
- **Accurate:** Uses IriusRisk's threat computation engine
- **One project per app:** Maintains customer paradigm (no temporary projects)

### New MCP Tool: `ci_cd_verification`

**Purpose:** Orchestrate threat model comparison and provide structured diff results to AI

**Parameters:**
- `project_path` (required): Path to `.iriusrisk/` directory
- `baseline_version` (optional): Version ID to use as baseline. If not provided:
  - **With OTM:** Uses current project state
  - **Without OTM:** Error (must specify version for version-to-version comparison)
- `otm_content` (optional): OTM content to import as comparison target. If not provided:
  - Compares baseline_version against current project state (Mode 3)
  - Or compares two versions if `target_version` is provided (Mode 4)
- `target_version` (optional): Version ID for version-to-version comparison (Mode 4 only)

**What the Python Tool Does (Heavy Lifting):**

**Step 1: Determine Comparison Mode**
- Mode 1: `otm_content` provided, no `baseline_version` → Current vs. OTM
- Mode 2: `otm_content` provided, `baseline_version` specified → Version vs. OTM
- Mode 3: No `otm_content`, `baseline_version` specified, no `target_version` → Version vs. Current
- Mode 4: No `otm_content`, both `baseline_version` and `target_version` → Version vs. Version

**Step 2: Download Baseline**
- Download baseline state (diagram XML, threats JSON, countermeasures JSON)
- Source: Version snapshot (if `baseline_version`) or current project

**Step 3: Prepare Target (mode-dependent)**
- **Mode 1/2 (OTM provided):**
  - Import OTM to IriusRisk (triggers threat computation)
  - Wait for computation completion
  - Create temporary version snapshot
  - Download target state
- **Mode 3 (version-to-current):**
  - Download current project state
- **Mode 4 (version-to-version):**
  - Download target version state

**Step 4: Parse and Compare (programmatic diff)**
- Parse diagram XML (mxGraph/Draw.io format)
- Identify components: added, removed, modified (properties changed)
- Identify dataflows: added, removed, modified (source/dest/data changed)
- Identify trust zones: added, removed, components moved between zones
- Parse threats JSON: added, removed, modified (severity/state changes)
- Parse countermeasures JSON: added, removed, modified (status changes)

**Step 5: Generate Structured Diff**
- Components: `{"added": [...], "removed": [...], "modified": [...]}`
- Dataflows: `{"added": [...], "removed": [...], "modified": [...]}`
- Trust zones: `{"added": [...], "removed": [...], "modified": [...]}`
- Threats: `{"added": [...], "removed": [...], "modified": [...]}`
- Countermeasures: `{"added": [...], "removed": [...], "modified": [...]}`

**Step 6: Cleanup (mode-dependent)**
- **Mode 1/2:** Restore project, delete temporary version
- **Mode 3/4:** No restoration needed (read-only)
- Always cleanup `.iriusrisk/verification/` files

**Step 7: Return Results**
- Structured diff with rich metadata for each change
- Metadata includes: comparison mode, baseline source, target source, timestamps

**What the AI Does (Interpretation & Communication):**
- Analyze codebase to generate OTM (if comparing against code changes)
- Call `ci_cd_verification` tool with appropriate parameters for desired comparison mode
- **Receive structured diff results** (not raw files)
- Interpret security implications of each change
- Assess relationships between architectural and security changes
- Generate human-readable report with context and recommendations
- Assign severity/risk levels to changes
- Provide actionable guidance for security team

**Key Principle:** Python does deterministic diffing, AI does contextual interpretation

### New MCP Prompt: `ci_cd_verification.md`

**Purpose:** Guide AI on security drift analysis in CI/CD context

**Content:**
- When to use this workflow (PR reviews, deployments, audits)
- Step-by-step verification process
- How to interpret different change types
- Decision criteria for pass/warn/block recommendations
- Report formatting guidance for security teams

### Implementation Components

**Core functionality:**

1. **Diagram Comparison Logic** (`utils/diagram_comparison.py`)
   - Parse mxGraph/Draw.io XML format
   - Extract components, dataflows, trust zones
   - Compare baseline vs current: identify added/removed/modified elements
   - Return structured diff with rich metadata for each change
   - **Output:** `{"components": {"added": [...], "removed": [...], "modified": [...]}, ...}`

2. **Threat Comparison Logic** (`utils/threat_comparison.py`)
   - Parse threats and countermeasures JSON files
   - Match items by ID and referenceId
   - Identify added/removed/modified threats and countermeasures
   - Detect critical changes (removed countermeasures, increased severity)
   - **Output:** `{"threats": {"added": [...], "removed": [...], "modified": [...]}, ...}`

3. **Verification Manager** (`utils/verification_manager.py`)
   - Context manager for workspace lifecycle
   - Download baseline from IriusRisk version (diagram XML, threats/countermeasures JSON)
   - Download current state after OTM import
   - Automatic cleanup of all temporary files (even on failure)
   - **Returns:** Baseline and current file paths for comparison

4. **MCP Tool** (`mcp/tools/ci_cd_verification.py`)
   - Orchestrate full workflow (download, import, compare, restore, cleanup)
   - Call diagram and threat comparison utilities
   - Aggregate all comparison results into single structured response
   - **Input:** OTM content from AI + baseline version ID
   - **Output:** Structured diff with all changes (components, threats, etc.)

5. **MCP Prompt** (`prompts/ci_cd_verification.md`)
   - Guide AI on when/how to use `ci_cd_verification` tool
   - Explain how to interpret structured diff results
   - Provide report formatting examples and templates
   - Define decision criteria for risk assessment

6. **Documentation** - CI/CD setup guide and examples

## MVP Feature List

### Must Have (Mode 2: Version vs. OTM - Primary CI/CD Use Case)
- [ ] **Verification workspace manager** (`utils/verification_manager.py`)
  - Context manager for safe file operations
  - Download baseline/target states from IriusRisk (version or current)
  - Handle temporary version creation and deletion
  - Automatic cleanup of all temporary files (baseline-* and verification-*)
  - Support for restoration to baseline version
  
- [ ] **Diagram comparison logic** (`utils/diagram_comparison.py`)
  - Parse mxGraph/Draw.io XML diagram files
  - Extract components, dataflows, trust zones
  - Compare baseline vs. target: identify added/removed/modified elements
  - Return structured diff with metadata for each change
  
- [ ] **Threat comparison logic** (`utils/threat_comparison.py`)
  - Parse threats and countermeasures JSON files
  - Match items by ID and referenceId
  - Identify added/removed/modified threats and countermeasures
  - Detect critical changes (removed countermeasures, severity increases)
  - Return structured diff with metadata
  
- [ ] **MCP tool: `ci_cd_verification()`** (`mcp/tools/ci_cd_verification.py`)
  - Support Mode 2 (version vs. OTM) for MVP
  - Accept parameters: project_path, baseline_version, otm_content
  - Orchestrate workflow: download, import, compare, restore, cleanup
  - Return structured diff (JSON format) with all changes
  
- [ ] **MCP prompt: `ci_cd_verification.md`**
  - When to use this tool (CI/CD, drift detection, audits)
  - How to interpret structured diff results
  - Architecture vs. security change interpretation
  - Report formatting examples and templates
  - Risk assessment decision criteria
  
- [ ] **API client extensions** (`api/project_client.py`)
  - Add `get_diagram_content()` method for XML diagram retrieval
  - Add `get_diagram_content_version()` for version-specific diagrams
  - Support version parameter on existing endpoints if needed
  
- [ ] **Documentation: CI/CD setup guide**
  - Baseline version creation and management
  - GitHub Actions workflow example
  - Environment variable configuration
  - Troubleshooting common issues
  
- [ ] **Tests** for core comparison logic
  - Unit tests for diagram parsing and comparison
  - Unit tests for threat/countermeasure comparison
  - Integration test with sample baseline and target data

### Nice to Have (Post-MVP)
- **Mode 3 support** (Version vs. Current) for drift detection
  - No OTM import required
  - Read-only comparison
  - Useful for "how have we drifted?" questions
  
- **Mode 1 support** (Current vs. OTM) for local development
  - Compare against uncommitted project state
  - Useful for pre-PR validation
  
- **Mode 4 support** (Version vs. Version) for auditing
  - Compare two historical baselines
  - Useful for "what changed between approvals?"
  
- **CLI command** for manual verification (`iriusrisk verify`)
  - Non-MCP interface for direct CLI usage
  - Same comparison engine, different interface
  
- **Pretty table output** for comparisons in terminal
  
- **Summary statistics** in diff results (X threats added, Y removed, etc.)
  
- **Diff visualization** (side-by-side comparison in reports)
  
- **Additional CI/CD examples:**
  - GitLab CI workflow
  - Jenkins pipeline
  - Azure DevOps pipeline
  
- **Comparison result caching** to avoid redundant API calls

### Future Enhancements (Beyond v1)
- **Policy rule engine** for automated pass/fail decisions
  - Configurable rules (e.g., "fail if countermeasure removed")
  - Severity thresholds (e.g., "warn if high-severity threat added")
  
- **Component approval lists** (allowlist/denylist)
  - Pre-approved components bypass review
  - Denied components automatically flag
  
- **Risk threshold configuration**
  - Define acceptable risk levels per environment
  - Automated scoring based on changes
  
- **Compliance mapping** in diff results
  - Show which compliance controls are affected
  - OWASP Top 10, PCI DSS impact analysis
  
- **Trend analysis over time**
  - Track security posture evolution
  - Metrics dashboard (threat count over time, etc.)
  
- **Incremental comparison** (performance optimization)
  - Compare only changed components/dataflows
  - Reduce computation time for large projects
  
- **Multi-project support**
  - Compare threat models across related projects
  - Microservices architecture analysis

## Use Cases

### Use Case 1: PR Verification
**Actor:** Development team member creates PR  
**Flow:**
1. PR created
2. GitHub Action triggers
3. AI agent runs verification
4. Comparison shows: Added Redis component, 8 new threats
5. AI generates report with security implications
6. Report posted as PR comment
7. Security team reviews, approves/requests changes

### Use Case 2: Pre-Deployment Check
**Actor:** Release engineer triggers deployment  
**Flow:**
1. Deployment pipeline started
2. AI verification runs
3. Comparison shows: Removed authentication countermeasure
4. AI flags as high-risk change
5. Report sent to security team
6. Deployment paused pending review
7. Security team investigates, makes decision

### Use Case 3: Periodic Audit
**Actor:** Security team runs scheduled audit  
**Flow:**
1. Weekly cron job triggers
2. AI compares production vs baseline
3. Accumulated drift detected over multiple deployments
4. Comprehensive report generated
5. Security team reviews for patterns
6. Update baseline or require remediation

## Example AI Report

```markdown
## 🔒 Security Drift Analysis - PR #1234

### Summary
**Baseline:** v2.1-approved (created 2024-01-05)  
**Current:** PR #1234 - Add Redis caching  
**Comparison Date:** 2024-02-15 14:32 UTC

**Changes Detected:**
- Architecture: 2 components added, 3 dataflows added, 1 trust zone modified
- Security: 8 threats added, 5 countermeasures added, 1 countermeasure removed

---

### 📐 Architectural Changes

#### Components Added

**1. Redis Cache** (External Service)
- **Trust Zone:** External Services
- **Purpose:** Session storage and caching
- **Added by:** Commit a3f9d2c

**2. Stripe Payment API** (External Service)
- **Trust Zone:** Third-Party Services
- **Purpose:** Payment processing
- **Added by:** Commit b7e4f1a

#### Dataflows Added

**1. User Service → Redis Cache**
- **Data:** Session tokens, user preferences
- **Protocol:** TCP/6379
- **Trust Boundary Crossed:** Yes (Internal → External)

**2. Payment Service → Stripe API**
- **Data:** Credit card data, transaction info
- **Protocol:** HTTPS
- **Trust Boundary Crossed:** Yes (Internal → Third-Party)

**3. API Gateway → Redis Cache**
- **Data:** API rate limit data
- **Protocol:** TCP/6379

---

### 🔒 Security Impact

#### New Threats (8 total)

**HIGH Severity (3):**
- **Unencrypted data in transit to Redis**
  - Component: Redis Cache
  - Related to: Dataflow User Service → Redis
  - Mitigation status: ❌ Not implemented
  - Recommendation: Enable TLS for Redis connections
  
- **Third-party data exposure via Stripe**
  - Component: Stripe Payment API
  - Related to: Dataflow Payment Service → Stripe
  - Mitigation status: ⚠️ Partial (HTTPS, but need PCI compliance verification)
  - Recommendation: Verify Stripe PCI-DSS compliance documentation

- **Session token theft**
  - Component: Redis Cache
  - Related to: Session data stored externally
  - Mitigation status: ❌ Not implemented
  - Recommendation: Encrypt session data before caching

**MEDIUM Severity (5):**
- Cache poisoning attacks (Redis Cache)
- Denial of service via cache (Redis Cache)
- Payment data interception (Stripe API - mitigated by HTTPS)
- ... (3 more)

#### Countermeasures Added (5 total)
- HTTPS for Stripe communication (✅ Implemented)
- Rate limiting via Redis (⚠️ Recommended)
- Cache key validation (⚠️ Recommended)
- Payment data encryption (⚠️ Recommended)
- API key rotation (⚠️ Recommended)

#### ⚠️ Countermeasures Removed (1 total)

**CRITICAL - Security Regression:**
- **Authentication token expiration** (Component: User Service)
  - Previous state: ✅ Implemented (15 minute timeout)
  - Current state: ❌ Removed
  - **Impact:** Tokens never expire, increasing risk of unauthorized access
  - **Action Required:** Explain why this was removed or restore immediately

---

### 🎯 Recommendations

#### Critical (Must Address Before Merge)
1. **Restore authentication token expiration** - Security regression detected
2. **Explain session storage security model** - How are session tokens protected in Redis?
3. **Enable TLS for Redis** - Unencrypted connection crosses trust boundary

#### High Priority (Address Before Production)
4. **Verify Stripe PCI-DSS compliance** - Document compliance status
5. **Encrypt sensitive data in cache** - Session tokens should be encrypted at rest
6. **Implement cache key validation** - Prevent cache poisoning attacks

#### Documentation Needed
7. Update security runbook with Redis operations
8. Document Stripe integration security controls
9. Update data flow diagrams
10. Add Redis to disaster recovery plan

---

### 📊 Assessment

**Overall Risk Level:** ⚠️ **MEDIUM-HIGH**

This PR introduces two external dependencies (Redis, Stripe) that cross trust boundaries and handle sensitive data. While some security controls are in place (HTTPS for Stripe), several critical gaps exist:

1. The removal of token expiration is a **security regression** that must be explained
2. Redis communication lacks encryption despite crossing trust boundaries
3. PCI-DSS compliance for Stripe needs verification

**Recommendation:** Request changes before approval. Security team review required.

---

### 🔗 Links
- [View threat model diagram](https://iriusrisk.com/projects/abc-123/diagram)
- [Compare versions in IriusRisk](https://iriusrisk.com/projects/abc-123/versions)
- [PR #1234 on GitHub](https://github.com/company/repo/pull/1234)
```

## Baseline Management Strategy

### Baseline Storage Location
Baseline files are temporary working storage in `.iriusrisk/verification/` directory:
```
.iriusrisk/verification/
├── baseline-diagram.xml           # Downloaded from IriusRisk version (temp)
├── baseline-threats.json          # Downloaded from IriusRisk version (temp)
└── baseline-countermeasures.json  # Downloaded from IriusRisk version (temp)
```

### Initial Baseline Setup
1. Security team reviews and approves threat model in IriusRisk
2. Create version snapshot in IriusRisk:
   ```bash
   iriusrisk versions create --name "v2.1-approved" \
     --description "Approved baseline for production - 2024-01-12"
   ```
3. Configure CI/CD to reference this version ID as the approved baseline

### Baseline Update Process
When architectural changes are approved:
1. Security team reviews changes in IriusRisk
2. If approved, create new version snapshot:
   ```bash
   iriusrisk versions create --name "v2.2-approved" \
     --description "Approved Redis integration - 2024-02-15"
   ```
3. Update CI/CD configuration to reference new baseline version

### Version Naming Convention
- **Approved baselines:** `v2.1-approved`, `v2.2-approved`
- **Date-based:** `baseline-2024-01-12`, `baseline-2024-02-15`
- **Release-based:** `baseline-v1.0.0`, `baseline-v2.0.0`
- **Environment-specific:** `baseline-production`, `baseline-staging`

## Open Questions

1. **Comparison Mode Selection:**
   - Should AI automatically detect which mode to use based on context?
   - Or should users explicitly specify the mode?
   - How to guide users to pick the right mode for their use case?

2. **Temporary Version Management (Modes 1/2):**
   - Naming convention for temporary versions? (e.g., "temp-verification-{timestamp}")
   - How long should temporary versions exist if cleanup fails?
   - Should we track/garbage collect orphaned temporary versions?
   - Should temporary versions be visible in UI or hidden?

3. **Concurrency (Modes 1/2 only):**
   - Multiple PRs running Mode 2 against same project will conflict (project modification)
   - Mode 3/4 are safe (read-only)
   - Need project locking mechanism for modes that modify state?
   - Or: Queue verification jobs?
   - Or: Accept serial execution for MVP?
   - Alternative: Use separate "verification project" that's cloned for each run?

4. **Frequency and Triggers:**
   - Mode 2: Run on every PR? (Recommended for security-critical apps)
   - Mode 3: Periodic drift detection? (Weekly/monthly scheduled jobs)
   - Mode 4: On-demand only? (Manual audits)
   - Configurable per-team? (Let teams decide)

5. **Scope:**
   - Compare full project or just changed services?
   - For monorepos, per-service or whole repo?
   - How to handle microservices architectures?
   - Should we support filtering (e.g., only compare specific components)?

6. **Performance:**
   - Mode 2: Full threat model generation (30-90 seconds) + comparison
   - Mode 3/4: Only comparison (~5-10 seconds) - much faster!
   - Baseline/target download: 2-5 seconds per state
   - Can we do incremental analysis? (Future enhancement)

7. **False Positives:**
   - What if AI incorrectly flags benign changes?
   - How to suppress known-safe patterns? (Future: whitelist)
   - Feedback mechanism for AI improvement?
   - Should comparison logic have confidence scores?

8. **Error Handling (Modes 1/2):**
   - If restoration fails after OTM import, project is in modified state
   - Should we create backup version before any modification?
   - Alert security team if restoration fails?
   - Document manual recovery procedure?

9. **Version Baseline Lifecycle:**
   - How often should security teams create new approved baselines?
   - What's the process for "promoting" a verified OTM to approved baseline?
   - Should old baselines be archived or deleted?
   - How many baselines should we keep?

10. **Multi-Mode Support Priority:**
    - MVP: Mode 2 only (CI/CD primary use case)
    - When to add Mode 3? (Drift detection is very useful)
    - When to add Modes 1 and 4? (Less common but valuable)
    - Can we design the tool to easily add modes later?

## Success Metrics

### MVP Success Criteria
- Customers can run drift detection in CI/CD
- AI successfully identifies architectural changes
- Reports are actionable for security teams
- Setup takes < 30 minutes

### Post-MVP Metrics
- % of security-relevant changes caught
- Time to detect drift (days → minutes)
- Reduction in post-deployment security incidents
- Security team review efficiency improvement

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              CI/CD Verification Workflow (Mode 2)               │
│         Python Tool (Heavy Lifting) + AI (Interpretation)       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ AI LAYER                                                         │
└─────────────────────────────────────────────────────────────────┘

1. PR Created → CI/CD Triggered
   │
2. AI Analyzes Codebase
   ├─> Reads code changes in PR
   ├─> Identifies components, dataflows, trust zones
   └─> Generates OTM file
   │
3. AI Calls MCP Tool: ci_cd_verification()
   ├─> Parameters: project_path, baseline_version, otm_content
   └─> Hands off to Python tool...

┌─────────────────────────────────────────────────────────────────┐
│ PYTHON TOOL LAYER (Deterministic Operations)                    │
└─────────────────────────────────────────────────────────────────┘

4. Download Baseline State
   ├─> GET /projects/{id}/diagram/content?version={baseline}
   ├─> GET /projects/{id}/threats?version={baseline}
   └─> GET /projects/{id}/countermeasures?version={baseline}
   └─> Save to: .iriusrisk/verification/baseline-*
   │
5. Import OTM to IriusRisk
   ├─> POST /products/otm/{project-id} (OTM content)
   ├─> IriusRisk computes threats/countermeasures (10-30s)
   └─> Wait for completion
   │
6. Create Temporary Version Snapshot
   ├─> POST /projects/{id}/versions
   └─> Name: "temp-verification-{timestamp}"
   │
7. Download Target State
   ├─> GET /projects/{id}/diagram/content
   ├─> GET /projects/{id}/threats
   └─> GET /projects/{id}/countermeasures
   └─> Save to: .iriusrisk/verification/verification-*
   │
8. Parse & Compare (Programmatic Diff)
   ├─> Parse Diagram XML (mxGraph format)
   │   ├─> Extract components (baseline vs target)
   │   ├─> Extract dataflows (baseline vs target)
   │   └─> Extract trust zones (baseline vs target)
   │
   ├─> Compare Architecture
   │   ├─> Components: added/removed/modified
   │   ├─> Dataflows: added/removed/modified
   │   └─> Trust zones: added/removed/modified
   │
   ├─> Parse Threats/Countermeasures JSON
   │   ├─> Match by ID and referenceId
   │   └─> Identify property changes
   │
   └─> Compare Security
       ├─> Threats: added/removed/modified
       ├─> Countermeasures: added/removed/modified
       ├─> Detect severity increases
       └─> Flag critical removals
   │
9. Generate Structured Diff
   ├─> Architecture changes: {added: [...], removed: [...], modified: [...]}
   ├─> Security changes: {threats: {...}, countermeasures: {...}}
   └─> Summary: {counts, risk_indicators}
   │
10. Restore Project State
    ├─> POST /projects/{id}/versions/{baseline}/restore
    └─> Revert to approved baseline
    │
11. Delete Temporary Version
    ├─> DELETE /projects/{id}/versions/{temp-version-id}
    └─> Clean up temporary snapshot
    │
12. Cleanup Workspace
    ├─> Delete .iriusrisk/verification/baseline-*
    └─> Delete .iriusrisk/verification/verification-*
    │
13. Return Structured Diff to AI
    └─> JSON format with all changes and metadata

┌─────────────────────────────────────────────────────────────────┐
│ AI LAYER (Interpretation & Communication)                       │
└─────────────────────────────────────────────────────────────────┘

14. AI Receives Structured Diff
    ├─> Parses JSON response
    └─> Has all changes with full context
    │
15. AI Interprets Security Implications
    ├─> Assess risk of each architectural change
    ├─> Analyze threat/countermeasure relationships
    ├─> Identify critical issues (removed countermeasures, severity increases)
    ├─> Evaluate trust boundary crossings
    └─> Determine overall risk level
    │
16. AI Generates Human-Readable Report
    ├─> Executive summary
    ├─> Architectural changes section
    ├─> Security impact section
    ├─> Critical issues highlighted
    ├─> Recommendations for security team
    └─> Links to IriusRisk and PR
    │
17. Post Report
    ├─> PR comment (GitHub/GitLab)
    ├─> Slack notification
    └─> Or email to security team
    │
18. Human Review & Decision
    └─> Security team approves/requests changes

┌─────────────────────────────────────────────────────────────────┐
│ DIVISION OF LABOR SUMMARY                                       │
└─────────────────────────────────────────────────────────────────┘

Python Tool (Steps 4-13):
✓ All API interactions
✓ File downloads and cleanup
✓ XML/JSON parsing
✓ Deterministic diffing
✓ State management (temporary versions, restoration)
✓ Error handling and logging
✓ Return structured data

AI Agent (Steps 1-3, 14-18):
✓ Codebase analysis (generate OTM)
✓ Tool invocation
✓ Interpret structured diff
✓ Assess security implications
✓ Generate human-readable reports
✓ Communicate with humans
✓ Provide recommendations
```

## Directory Structure

### `.iriusrisk/verification/` Workspace

All CI/CD verification files are isolated in a dedicated directory:

```
.iriusrisk/
├── project.json                    # existing - project metadata
├── threats.json                    # existing - working copy for normal ops
├── countermeasures.json            # existing - working copy for normal ops
├── updates.json                    # existing - tracked changes
│
└── verification/                   # CI/CD verification workspace (temporary)
    ├── baseline-diagram.xml        # baseline architecture (temp, from IriusRisk version)
    ├── baseline-threats.json       # baseline threats (temp, from IriusRisk version)
    ├── baseline-countermeasures.json  # (temp, from IriusRisk version)
    │
    ├── verification-diagram.xml    # current architecture from PR (temp)
    ├── verification-threats.json   # current threats from PR (temp)
    ├── verification-countermeasures.json  # (temp)
    └── diff-results.json           # comparison output (optional, temp)
```

**Key Principles:**
- **Isolation:** Verification never touches main threats.json/countermeasures.json
- **Ephemeral:** ALL files in verification/ are temporary (created and deleted each run)
- **Fresh data:** Baseline downloaded from IriusRisk version every run
- **Safety:** Context manager ensures cleanup even on failure

## Technical Notes

### File Formats

**Diagram XML:**
- IriusRisk's diagram export format
- Contains components, dataflows, trust zones
- Represents architecture/design

**Threats JSON:**
- IriusRisk's threat export format
- Computed by IriusRisk rules engine
- Each threat has: id, referenceId, name, description, riskRating, state, etc.

**Countermeasures JSON:**
- IriusRisk's countermeasure export format
- Security controls/mitigations
- Each countermeasure has: id, referenceId, name, description, state, implementationStatus, etc.

### Comparison Algorithm

**Architecture Comparison (XML):**
- Parse baseline-diagram.xml and verification-diagram.xml
- Extract components, dataflows, trust zones
- Match by ID or referenceId
- Identify: added, removed, modified (property changes)

**Security Comparison (JSON):**
- Parse threat/countermeasure JSON files
- Match by id or referenceId
- Identify: added, removed, modified
- Detect critical changes: countermeasures removed, threat severity increased

### Matching Strategy
- Primary key: `id` field (UUID)
- Fallback: `referenceId` field (human-readable)
- For dataflows: Match by source+destination+data type

## Structured Diff Output Format

The Python tool returns a structured JSON diff to the AI. This format is designed to be:
- **Comprehensive:** All changes with full metadata
- **Categorized:** Grouped by change type (added/removed/modified)
- **Rich context:** Each item includes properties for AI interpretation
- **Consistent:** Same structure across all comparison modes

### Example Structured Diff Response

```json
{
  "metadata": {
    "comparison_mode": "version_vs_otm",
    "baseline_source": {
      "type": "version",
      "version_id": "a3b4c5d6-...",
      "version_name": "v2.1-approved",
      "created": "2024-01-12T10:30:00Z"
    },
    "target_source": {
      "type": "otm_import",
      "temporary_version_id": "d6e7f8a9-...",
      "imported_at": "2024-02-15T14:32:00Z"
    },
    "comparison_timestamp": "2024-02-15T14:32:15Z",
    "project_restored": true
  },
  
  "architecture": {
    "components": {
      "added": [
        {
          "id": "comp-123",
          "name": "Redis Cache",
          "type": "external-service",
          "trust_zone": "External Services",
          "properties": {
            "description": "Session storage and caching",
            "technology": "Redis 7.0"
          }
        },
        {
          "id": "comp-124",
          "name": "Stripe Payment API",
          "type": "external-service",
          "trust_zone": "Third-Party Services",
          "properties": {
            "description": "Payment processing",
            "technology": "Stripe API v2023"
          }
        }
      ],
      "removed": [],
      "modified": [
        {
          "id": "comp-100",
          "name": "User Service",
          "changes": {
            "description": {
              "old": "User authentication and profile management",
              "new": "User authentication, profile management, and session handling"
            },
            "trust_zone": {
              "old": "Internal Services",
              "new": "Internal Services"
            }
          }
        }
      ]
    },
    
    "dataflows": {
      "added": [
        {
          "id": "flow-456",
          "source": "User Service",
          "destination": "Redis Cache",
          "data_types": ["Session tokens", "User preferences"],
          "protocol": "TCP/6379",
          "crosses_trust_boundary": true,
          "trust_boundary_crossed": "Internal Services → External Services"
        },
        {
          "id": "flow-457",
          "source": "Payment Service",
          "destination": "Stripe Payment API",
          "data_types": ["Credit card data", "Transaction info"],
          "protocol": "HTTPS",
          "crosses_trust_boundary": true,
          "trust_boundary_crossed": "Internal Services → Third-Party Services"
        }
      ],
      "removed": [],
      "modified": []
    },
    
    "trust_zones": {
      "added": [
        {
          "id": "tz-789",
          "name": "Third-Party Services",
          "type": "external",
          "description": "External third-party service providers"
        }
      ],
      "removed": [],
      "modified": [],
      "component_moves": [
        {
          "component_id": "comp-105",
          "component_name": "API Gateway",
          "old_trust_zone": "DMZ",
          "new_trust_zone": "Internal Services"
        }
      ]
    }
  },
  
  "security": {
    "threats": {
      "added": [
        {
          "id": "threat-001",
          "referenceId": "CACHE-001",
          "name": "Unencrypted data in transit to Redis",
          "description": "Session data transmitted without encryption",
          "riskRating": "HIGH",
          "state": "required",
          "affected_components": ["Redis Cache", "User Service"],
          "related_dataflows": ["flow-456"],
          "categories": ["Information Disclosure", "Network Security"]
        },
        {
          "id": "threat-002",
          "referenceId": "PAYMENT-001",
          "name": "Third-party data exposure via Stripe",
          "description": "Payment data sent to third-party service",
          "riskRating": "HIGH",
          "state": "partly-mitigated",
          "affected_components": ["Stripe Payment API", "Payment Service"],
          "related_dataflows": ["flow-457"],
          "categories": ["Data Privacy", "Third-Party Risk"]
        }
      ],
      "removed": [],
      "modified": [
        {
          "id": "threat-050",
          "referenceId": "AUTH-001",
          "name": "Session token theft",
          "changes": {
            "riskRating": {
              "old": "MEDIUM",
              "new": "HIGH",
              "reason": "Session tokens now stored externally in Redis"
            },
            "state": {
              "old": "mitigated",
              "new": "required",
              "reason": "External storage introduced new attack vector"
            }
          }
        }
      ],
      "severity_increases": [
        {
          "threat_id": "threat-050",
          "threat_name": "Session token theft",
          "old_severity": "MEDIUM",
          "new_severity": "HIGH"
        }
      ]
    },
    
    "countermeasures": {
      "added": [
        {
          "id": "cm-301",
          "referenceId": "NET-HTTPS",
          "name": "HTTPS for Stripe communication",
          "description": "Use TLS for all payment API communication",
          "state": "implemented",
          "risk_mitigation": ["threat-002"]
        },
        {
          "id": "cm-302",
          "referenceId": "CACHE-TLS",
          "name": "TLS for Redis connections",
          "description": "Enable TLS for Redis client connections",
          "state": "recommended",
          "risk_mitigation": ["threat-001"]
        }
      ],
      "removed": [
        {
          "id": "cm-100",
          "referenceId": "AUTH-EXPIRY",
          "name": "Authentication token expiration",
          "description": "Tokens expire after 15 minutes",
          "state": "implemented",
          "risk_mitigation": ["threat-050"],
          "removal_reason": "CRITICAL - Security regression"
        }
      ],
      "modified": [
        {
          "id": "cm-200",
          "referenceId": "AUTH-VALIDATE",
          "name": "Authentication token validation",
          "changes": {
            "state": {
              "old": "implemented",
              "new": "recommended",
              "reason": "Implementation moved to external service"
            },
            "description": {
              "old": "Validate tokens in User Service",
              "new": "Validate tokens in User Service and verify Redis storage"
            }
          }
        }
      ],
      "critical_removals": [
        {
          "countermeasure_id": "cm-100",
          "countermeasure_name": "Authentication token expiration",
          "severity": "CRITICAL",
          "impacted_threats": ["threat-050"]
        }
      ]
    }
  },
  
  "summary": {
    "architecture_changes": {
      "components_added": 2,
      "components_removed": 0,
      "components_modified": 1,
      "dataflows_added": 2,
      "dataflows_removed": 0,
      "dataflows_modified": 0,
      "trust_zones_added": 1,
      "trust_zones_removed": 0,
      "trust_boundary_crossings_added": 2
    },
    "security_changes": {
      "threats_added": 2,
      "threats_removed": 0,
      "threats_modified": 1,
      "severity_increases": 1,
      "countermeasures_added": 2,
      "countermeasures_removed": 1,
      "countermeasures_modified": 1,
      "critical_removals": 1
    },
    "risk_indicators": {
      "has_critical_removals": true,
      "has_severity_increases": true,
      "has_new_trust_boundary_crossings": true,
      "high_severity_threats_added": 2
    }
  }
}
```

### Field Descriptions

**Metadata:**
- `comparison_mode`: Which of the 4 modes was used
- `baseline_source`: Where baseline came from (version or current)
- `target_source`: Where target came from (OTM import, version, or current)
- `project_restored`: Whether project was restored after comparison (relevant for modes 1/2)

**Architecture Changes:**
- `added`: New items that didn't exist in baseline
- `removed`: Items that existed in baseline but not in target
- `modified`: Items that exist in both but have property changes

**Security Changes:**
- Similar structure to architecture
- Additional arrays: `severity_increases`, `critical_removals` for quick identification
- Each threat/countermeasure includes affected components and dataflows for traceability

**Summary:**
- Counts for quick assessment
- `risk_indicators`: Boolean flags for high-priority concerns
- Used by AI to determine overall risk level and prioritize report sections

This structured format allows the AI to:
1. Quickly assess overall scope of changes
2. Identify critical issues (severity increases, countermeasure removals)
3. Trace relationships (which threats affect which components)
4. Generate contextual explanations
5. Prioritize report sections by impact

### Why Not Use IriusRisk Version Comparison API?
IriusRisk provides a version comparison API endpoint, but testing revealed reliability issues that make it unsuitable for CI/CD workflows. Our approach uses IriusRisk for threat computation (its core value) but performs comparison locally for reliability.

### Performance Considerations
- Download baseline from IriusRisk version (3 files): 2-5 seconds
- IriusRisk OTM import + threat computation: 10-30 seconds
- Download current state (3 files): 2-5 seconds
- Comparison logic: < 1 second for typical projects
- AI interpretation time: Variable (30-60 seconds typical)
- **Total CI/CD overhead: ~45-95 seconds**

## Implementation Plan

### Phase 1: Core Functionality (MVP - Mode 2 Only)

**Week 1-2: Comparison Engine**
1. **Diagram Comparison** (`utils/diagram_comparison.py`)
   - mxGraph/Draw.io XML parser
   - Component extraction and comparison (added/removed/modified)
   - Dataflow extraction and comparison
   - Trust zone extraction and comparison
   - Return structured diff with metadata
   - Unit tests with sample diagram XML files

2. **Threat Comparison** (`utils/threat_comparison.py`)
   - Threats JSON parser and comparison
   - Countermeasures JSON parser and comparison
   - Identify critical changes (removed countermeasures, severity increases)
   - Return structured diff with metadata
   - Unit tests with sample threat/countermeasure JSON files

**Week 2-3: Orchestration & State Management**
3. **Verification Manager** (`utils/verification_manager.py`)
   - Context manager for workspace lifecycle
   - Download baseline from version or current project
   - Download target from version or current project
   - Handle temporary version creation (for OTM import)
   - Handle temporary version deletion
   - Project restoration to baseline version
   - Automatic cleanup (even on failure)
   - Integration tests

4. **API Client Extensions** (`api/project_client.py`)
   - Add `get_diagram_content(project_id)` → returns XML string
   - Add `get_diagram_content_version(project_id, version_id)` → returns XML string
   - Handle version parameter on threat/countermeasure endpoints (may already exist)
   - Unit tests with mocked responses

**Week 3-4: MCP Tool & AI Integration**
5. **MCP Tool** (`mcp/tools/ci_cd_verification.py`)
   - Implement Mode 2: Version vs. OTM (CI/CD use case)
   - Accept parameters: project_path, baseline_version, otm_content
   - Orchestrate workflow: download → import → compare → restore → cleanup
   - Error handling and logging
   - Return structured diff (JSON format)
   - Integration tests with real IriusRisk API (test environment)

6. **MCP Prompt** (`prompts/ci_cd_verification.md`)
   - When/how to use ci_cd_verification tool
   - How to interpret structured diff results
   - Report formatting templates and examples
   - Risk assessment guidance
   - Examples for different change types

**Week 4: Documentation & Examples**
7. **CI/CD Setup Guide** (documentation)
   - Baseline version creation and management
   - Environment variable configuration
   - GitHub Actions workflow example
   - Troubleshooting guide

8. **Testing & Validation**
   - End-to-end test with sample PR
   - Validate AI report generation
   - Performance benchmarking
   - Bug fixes and polish

### Phase 2: Additional Comparison Modes

**Mode 3: Version vs. Current (Drift Detection)**
1. Extend MCP tool to support Mode 3
   - No OTM import, no restoration needed
   - Read-only comparison
   - Much faster execution
2. Add drift detection scheduling examples
3. Documentation and examples

**Mode 1: Current vs. OTM (Local Development)**
1. Extend MCP tool to support Mode 1
   - Similar to Mode 2 but baseline is current project
2. Documentation for pre-PR validation workflow

**Mode 4: Version vs. Version (Auditing)**
1. Extend MCP tool to support Mode 4
   - Completely read-only
   - Compare two historical snapshots
2. Documentation for audit use cases

### Phase 3: Polish & Advanced Features
1. Gather customer feedback from Phase 1 deployment
2. Improve AI prompts based on usage patterns
3. Add CLI command for manual verification (`iriusrisk verify`)
4. Performance optimization (caching, incremental comparison)
5. Concurrency handling (project locking or queueing)
6. Pretty-printed diff output for terminal
7. Summary statistics in diff results
8. Additional CI/CD platform examples (GitLab, Jenkins, Azure DevOps)

### Phase 4: Future Enhancements
1. Policy rule engine for automated decisions
2. Component approval lists
3. Risk threshold configuration
4. Compliance mapping
5. Trend analysis over time
6. Multi-project comparison support

## Related Files

**To Create:**

Core Comparison Logic:
- `src/iriusrisk_cli/utils/diagram_comparison.py` - mxGraph XML parsing and comparison
- `src/iriusrisk_cli/utils/threat_comparison.py` - Threat/countermeasure JSON comparison
- `src/iriusrisk_cli/utils/verification_manager.py` - Workspace, state management, restoration

MCP Integration:
- `src/iriusrisk_cli/mcp/tools/ci_cd_verification.py` - MCP tool implementation (orchestrates workflow)
- `src/iriusrisk_cli/prompts/ci_cd_verification.md` - AI guidance for interpretation and reporting

Tests:
- `tests/unit/test_diagram_comparison.py` - Unit tests for XML parsing and diffing
- `tests/unit/test_threat_comparison.py` - Unit tests for JSON comparison
- `tests/unit/test_verification_manager.py` - Unit tests for state management
- `tests/integration/test_ci_cd_verification.py` - End-to-end workflow tests
- `tests/fixtures/diagrams/` - Sample diagram XML files for testing
- `tests/fixtures/threats/` - Sample threat/countermeasure JSON for testing

Documentation:
- `docs/CICD_VERIFICATION.md` - Detailed setup and usage guide
- `docs/COMPARISON_MODES.md` - Explanation of 4 comparison modes
- `.github/workflows/security-drift-check.yml` - Example GitHub Action (Mode 2)
- `.github/workflows/security-drift-detection.yml` - Example scheduled drift check (Mode 3)

**To Modify:**

API Client (Add diagram XML endpoints):
- `src/iriusrisk_cli/api/project_client.py`
  - Add `get_diagram_content(project_id)` → Returns diagram XML (mxGraph format)
  - Add `get_diagram_content_version(project_id, version_id)` → Returns version-specific diagram XML
  - Verify version parameter support on threat/countermeasure endpoints

Version Service (Add temporary version helpers):
- `src/iriusrisk_cli/services/version_service.py`
  - Add `create_temporary_version(project_id, name)` → Creates snapshot
  - Add `delete_version(project_id, version_id)` → Removes version
  - Add `restore_to_version(project_id, version_id)` → Reverts project state
  - May need corresponding repository methods in `repositories/version_repository.py`

MCP Command Registration:
- `src/iriusrisk_cli/commands/mcp.py`
  - Register `ci_cd_verification` tool
  - Add prompt loading for `ci_cd_verification.md`

Configuration:
- `.gitignore` - Add `.iriusrisk/verification/` to ignore temporary files
- `manifest.json` - Add MCP tool metadata for `ci_cd_verification`

Documentation:
- `README.md` - Add CI/CD Drift Detection section with quick start
- `CHANGELOG.md` - Add v0.4.0 entry with feature description
- `AGENTS.md` - Update with ci_cd_verification tool usage examples

**API Endpoints to Verify/Document:**

Need to confirm IriusRisk API support for:
- `GET /api/v2/projects/{project-id}/diagram/content` → mxGraph XML (confirmed exists)
- `GET /api/v2/projects/{project-id}/diagram/content?version={version-id}` → Version-specific diagram (confirmed exists)
- `GET /api/v2/projects/{project-id}/threats?version={version-id}` → Version-specific threats (need to verify)
- `GET /api/v2/projects/{project-id}/countermeasures?version={version-id}` → Version-specific countermeasures (need to verify)
- `POST /api/v2/projects/{project-id}/versions/{version-id}/restore` → Restore project to version (need to verify endpoint)
- `DELETE /api/v2/projects/{project-id}/versions/{version-id}` → Delete version (need to verify)

## Edge Cases & Limitations

### Concurrent PR Checks
**Problem:** Multiple PRs running verification against same IriusRisk project will conflict (each updates and restores the project).

**Solutions:**
- **MVP Approach:** Document that verification jobs must run serially
- **Future:** Implement project locking mechanism
- **Future:** Queue verification jobs
- **Alternative:** Use separate IriusRisk projects per environment (prod-baseline, staging-baseline)

### Restore Failure
**Problem:** If project restore fails, IriusRisk project is left in modified state.

**Mitigation:**
- Robust error handling with logging
- Alert security team if restore fails
- Document manual restore procedure
- Consider version snapshots before verification

### Cleanup on Abort
**Problem:** If CI/CD job is cancelled mid-verification, temporary files may remain.

**Mitigation:**
- Context manager ensures cleanup in finally block
- Next run detects and cleans stale files from `.iriusrisk/verification/`
- Document manual cleanup procedure

## Risk & Mitigation

**Risk:** AI misinterprets changes, causes alert fatigue  
**Mitigation:** Provide clear guidance prompts, iterate based on feedback

**Risk:** Performance too slow for CI/CD  
**Mitigation:** Total time ~45-95 seconds is acceptable for security-critical checks

**Risk:** Customers don't understand how to set baselines  
**Mitigation:** Clear documentation, video tutorials, examples showing version creation and configuration

**Risk:** False sense of security if not reviewed  
**Mitigation:** Emphasize "visibility not enforcement" in docs, require human review step

**Risk:** Concurrent PR checks corrupt IriusRisk project  
**Mitigation:** Document serial execution requirement for MVP; add locking in future

## Notes

- This is **visibility tooling**, not a security gate
- Humans make all accept/reject decisions
- Focus on making security team's job easier
- Leverage IriusRisk's existing computation power
- AI's value is in interpretation and communication

