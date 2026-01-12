# CI/CD Drift Detection Feature

**Status:** Ready for Implementation  
**Target:** v0.4.0  
**Purpose:** Design document for AI-powered security drift detection in CI/CD pipelines

**Implementation Approach:** Version-based comparison using IriusRisk project versions with local baseline caching

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
1. Compare current codebase against an approved baseline (using IriusRisk versions)
2. Surface architectural changes (components, dataflows, trust zones) AND security changes (threats, countermeasures)
3. Generate human-readable reports for manual review
4. Post findings to PRs/tickets for security team review

**Key Technical Approach:**
- Leverage IriusRisk project versions for baseline management
- Cache baseline locally for fast comparison
- Compare architecture (diagram XML) AND security (threats/countermeasures JSON)
- Isolated verification workspace (`.iriusrisk/verification/`) for safe operations

**NOT in scope for MVP:**
- Automated approval/rejection decisions
- Policy rule engines
- Enforcement gates
- Approved component lists

## High-Level Workflow

### One-Time Setup
1. Security team reviews and approves initial threat model in IriusRisk
2. Create version snapshot in IriusRisk (e.g., "v2.1-approved" or "baseline-2024-01-12")
3. Cache baseline locally:
   - Download diagram XML → `.iriusrisk/verification/baseline-diagram.xml`
   - Download threats → `.iriusrisk/verification/baseline-threats.json`
   - Download countermeasures → `.iriusrisk/verification/baseline-countermeasures.json`
   - Store version metadata → `.iriusrisk/verification/baseline-version.json`
4. Configure CI/CD to run AI verification on PRs/deployments

### Per-Deployment Workflow
1. **CI/CD triggers** → AI agent activates
2. **Load cached baseline** → Read from `.iriusrisk/verification/baseline-*` files (fast, no API call)
3. **AI generates OTM** → Analyzes current codebase state
4. **Import to IriusRisk** → Update project with new OTM, wait for threat computation
5. **Download current state** → Save to `.iriusrisk/verification/verification-*` files
   - verification-diagram.xml (architecture)
   - verification-threats.json (computed threats)
   - verification-countermeasures.json (computed countermeasures)
6. **Compare architecture** → Identify component, dataflow, trust zone changes
7. **Compare security** → Identify threat and countermeasure changes
8. **AI interprets** → Assesses security implications of changes
9. **Generate report** → Human-readable findings with full context
10. **Restore baseline** → Revert IriusRisk project to baseline version
11. **Cleanup** → Remove verification-* files
12. **Post results** → PR comment, Slack, ticket, etc.
13. **Human review** → Security team decides if acceptable

**Note:** Baseline is cached locally for speed; comparison includes both architectural changes and their security implications.

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

### Version-Based Comparison with Local Caching

The comparison leverages IriusRisk's version system combined with local caching:

**Architecture Comparison:**
- Parse and compare diagram XML files to identify component, dataflow, and trust zone changes
- Uses IriusRisk's diagram export format

**Security Comparison:**
- Compare threats and countermeasures JSON files
- Uses IriusRisk's computed threat model (not just architecture)

**Key Benefits:**
- **Fast:** Baseline cached locally, only download current state
- **Comprehensive:** Compares both architecture AND security implications
- **Safe:** Isolated workspace, never touches main files
- **Accurate:** Uses IriusRisk's threat computation engine
- **One project per app:** Maintains customer paradigm (no temporary projects)

### New MCP Tool: `ci_cd_verification`

**Purpose:** Guide AI agents through the drift detection workflow

**Workflow:**
1. Ensure baseline cached locally (download from IriusRisk version if needed)
2. Generate OTM from current codebase
3. Import OTM to IriusRisk project (triggers threat computation)
4. Download current state (diagram XML, threats, countermeasures)
5. Compare baseline vs current:
   - Architecture: components, dataflows, trust zones
   - Security: threats, countermeasures
6. Restore IriusRisk project to baseline version
7. Cleanup temporary verification files
8. Return comprehensive diff for AI interpretation

**AI Usage:**
- Analyze codebase to generate current OTM
- Interpret architectural changes (new components, dataflows)
- Interpret security changes (new threats, removed countermeasures)
- Assess relationship between architecture and security changes
- Generate report with context and recommendations

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

1. **Diagram Comparison Logic** (`utils/diagram_comparison.py`) - Parse and compare XML diagram files
2. **Threat Comparison Logic** (`utils/threat_comparison.py`) - Compare threats and countermeasures JSON
3. **Verification Manager** (`utils/verification_manager.py`) - Manage `.iriusrisk/verification/` workspace
4. **MCP Tool** (`mcp/tools/ci_cd_verification.py`) - Orchestrate workflow for AI agents
5. **MCP Prompt** (`prompts/ci_cd_verification.md`) - Detailed instructions for AI interpretation
6. **Documentation** - CI/CD setup guide and examples

## MVP Feature List

### Must Have
- [ ] Verification workspace manager (`utils/verification_manager.py`)
  - Context manager for safe file operations
  - Baseline caching and staleness detection
  - Automatic cleanup of temporary files
- [ ] Diagram comparison logic (`utils/diagram_comparison.py`)
  - Parse XML diagram files
  - Compare components, dataflows, trust zones
  - Identify added/removed/modified elements
- [ ] Threat comparison logic (`utils/threat_comparison.py`)
  - Compare threats JSON files
  - Compare countermeasures JSON files
  - Identify added/removed/modified items
- [ ] MCP tool: `ci_cd_verification()` for AI workflow orchestration
- [ ] MCP prompt: `ci_cd_verification.md` with detailed guidance
  - Architecture interpretation guidance
  - Security impact assessment guidance
  - Report formatting examples
- [ ] Documentation: CI/CD setup guide
- [ ] Example: GitHub Actions workflow

### Nice to Have (Post-MVP)
- CLI command for manual verification (`iriusrisk verify`)
- Pretty table output for comparisons
- Summary statistics dashboard (X threats added, Y removed, etc.)
- Diff visualization (side-by-side comparison)
- Documentation: GitLab CI example
- Documentation: Jenkins example

### Future Enhancements (Not MVP)
- Policy rule engine
- Automated approval/rejection
- Component approval lists
- Risk threshold configuration
- Compliance mapping
- Trend analysis over time

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
All baseline files are stored in `.iriusrisk/verification/` directory:
```
.iriusrisk/verification/
├── baseline-version.json          # Version ID, timestamp, approver
├── baseline-diagram.xml           # Architecture snapshot
├── baseline-threats.json          # Threats snapshot
└── baseline-countermeasures.json  # Countermeasures snapshot
```

### Initial Baseline Setup
1. Security team reviews and approves threat model in IriusRisk
2. Create version snapshot in IriusRisk:
   ```bash
   iriusrisk versions create --name "v2.1-approved" \
     --description "Approved baseline for production - 2024-01-12"
   ```
3. Cache baseline locally (automatic on first verification run):
   - Downloads diagram, threats, countermeasures from approved version
   - Stores in `.iriusrisk/verification/baseline-*` files
4. **Optional:** Commit baseline files to Git for team sharing
   - Or: Add to `.gitignore` and regenerate from IriusRisk version as needed

### Baseline Update Process
When architectural changes are approved:
1. Security team reviews changes in IriusRisk
2. If approved, create new version snapshot:
   ```bash
   iriusrisk versions create --name "v2.2-approved" \
     --description "Approved Redis integration - 2024-02-15"
   ```
3. Update project config to reference new baseline version
4. Next verification run will detect stale cache and download new baseline

### Version Naming Convention
- **Approved baselines:** `v2.1-approved`, `v2.2-approved`
- **Date-based:** `baseline-2024-01-12`, `baseline-2024-02-15`
- **Release-based:** `baseline-v1.0.0`, `baseline-v2.0.0`
- **Environment-specific:** `baseline-production`, `baseline-staging`

### Git Strategy Options

**Option A: Commit baseline files (recommended for teams)**
- Commit `.iriusrisk/verification/baseline-*` files
- All team members share same baseline
- Fast CI/CD (no download needed)
- Clear audit trail in Git history

**Option B: Regenerate from IriusRisk version**
- Add `.iriusrisk/verification/` to `.gitignore`
- Each environment downloads baseline from IriusRisk on first run
- Single source of truth (IriusRisk version)
- Requires IriusRisk API access from CI/CD

## Open Questions

1. **Frequency:**
   - Run on every PR? (Recommended for security-critical apps)
   - Only on deployment? (Minimum viable)
   - Periodic audits? (Weekly/monthly drift checks)
   - Configurable per-team? (Let teams decide)

2. **Concurrency:**
   - Multiple PRs running verification against same project will conflict
   - Need project locking mechanism?
   - Or: Queue verification jobs?
   - Or: Accept serial execution for MVP?

3. **Scope:**
   - Compare full project or just changed services?
   - For monorepos, per-service or whole repo?
   - How to handle microservices architectures?

4. **Performance:**
   - Full threat model generation can be slow (30-90 seconds)
   - Can we do incremental analysis? (Future enhancement)
   - Baseline caching helps (no re-download each time)

5. **False Positives:**
   - What if AI incorrectly flags benign changes?
   - How to suppress known-safe patterns? (Future: whitelist)
   - Feedback mechanism for AI improvement?

6. **Workspace Isolation:**
   - `.iriusrisk/verification/` keeps things clean
   - Should verification files be committed to Git?
   - Or regenerated from IriusRisk versions?

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
│                    CI/CD Verification Workflow                  │
└─────────────────────────────────────────────────────────────────┘

1. PR Created
   │
   ├─> CI/CD Triggered
   │
   ├─> Load Cached Baseline (Fast!)
   │   └─> .iriusrisk/verification/baseline-*
   │
   ├─> Generate OTM from PR Code
   │   └─> AI analyzes codebase
   │
   ├─> Import OTM to IriusRisk Project
   │   └─> IriusRisk computes threats/countermeasures (30s)
   │
   ├─> Download Current State
   │   ├─> verification-diagram.xml
   │   ├─> verification-threats.json
   │   └─> verification-countermeasures.json
   │
   ├─> Compare Baseline vs Current
   │   ├─> Architecture Diff (components, dataflows)
   │   └─> Security Diff (threats, countermeasures)
   │
   ├─> AI Interprets Changes
   │   └─> Generate human-readable report
   │
   ├─> Restore IriusRisk Project
   │   └─> Revert to baseline version
   │
   ├─> Cleanup
   │   └─> Delete verification-* files
   │
   └─> Post Report to PR
       └─> Security team reviews
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
└── verification/                   # CI/CD verification workspace
    ├── baseline-version.json       # metadata: version ID, timestamp, approver
    ├── baseline-diagram.xml        # baseline architecture (cached)
    ├── baseline-threats.json       # baseline threats (cached)
    ├── baseline-countermeasures.json
    │
    ├── verification-diagram.xml    # current architecture from PR (temp)
    ├── verification-threats.json   # current threats from PR (temp)
    ├── verification-countermeasures.json  # (temp)
    └── diff-results.json           # comparison output (optional, temp)
```

**Key Principles:**
- **Isolation:** Verification never touches main threats.json/countermeasures.json
- **Persistence:** baseline-* files are persistent cache
- **Temporary:** verification-* files are created and deleted during check
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

### Why Not Use IriusRisk Version Comparison API?
IriusRisk provides a version comparison API endpoint, but testing revealed reliability issues that make it unsuitable for CI/CD workflows. Our approach uses IriusRisk for threat computation (its core value) but performs comparison locally for reliability.

### Performance Considerations
- Baseline cache load: < 0.1 seconds (local files)
- IriusRisk OTM import + threat computation: 10-30 seconds
- Download current state (3 files): 2-5 seconds
- Comparison logic: < 1 second for typical projects
- AI interpretation time: Variable (30-60 seconds typical)
- **Total CI/CD overhead: ~45-90 seconds**

## Implementation Plan

### Phase 1: Core Functionality (MVP)
1. **Verification Manager** (`utils/verification_manager.py`)
   - Context manager for workspace management
   - Baseline caching with staleness detection
   - Automatic cleanup of temporary files
2. **Diagram Comparison** (`utils/diagram_comparison.py`)
   - XML parsing for diagram files
   - Component/dataflow/trust zone comparison
   - Generate structured diff
3. **Threat Comparison** (`utils/threat_comparison.py`)
   - JSON parsing for threats/countermeasures
   - Identify added/removed/modified items
   - Generate structured diff
4. **MCP Tool** (`mcp/tools/ci_cd_verification.py`)
   - Orchestrate full workflow
   - Manage IriusRisk API interactions
   - Return comprehensive diff
5. **MCP Prompt** (`prompts/ci_cd_verification.md`)
   - Guide AI interpretation
   - Report formatting examples
6. **Testing** with sample files

### Phase 2: Documentation & Examples
1. CI/CD setup guide
2. GitHub Actions workflow example
3. Usage documentation for AI agents
4. Baseline management guide
5. Video walkthrough

### Phase 3: Polish & Iteration
1. Gather customer feedback
2. Improve AI prompts based on usage patterns
3. Add CLI command for manual verification
4. Performance optimization
5. Support for concurrent PR checks

## Related Files

**To Create:**
- `src/iriusrisk_cli/utils/verification_manager.py` - Workspace and baseline management
- `src/iriusrisk_cli/utils/diagram_comparison.py` - Diagram XML comparison logic
- `src/iriusrisk_cli/utils/threat_comparison.py` - Threat/countermeasure comparison logic
- `src/iriusrisk_cli/mcp/tools/ci_cd_verification.py` - MCP tool implementation
- `src/iriusrisk_cli/prompts/ci_cd_verification.md` - AI workflow guidance
- `.github/workflows/security-drift-check.yml` - Example GitHub Action
- `tests/unit/test_verification_manager.py` - Unit tests
- `tests/unit/test_diagram_comparison.py` - Unit tests
- `tests/unit/test_threat_comparison.py` - Unit tests

**To Modify:**
- `src/iriusrisk_cli/commands/mcp.py` - Register new MCP tool
- `src/iriusrisk_cli/services/version_service.py` - Add restore helper if needed
- `.gitignore` - Add `.iriusrisk/verification/` (or document Git strategy)

**Documentation:**
- `README.md` - Add CI/CD verification section
- `CHANGELOG.md` - Add v0.4.0 entry
- New doc: `docs/CICD_VERIFICATION.md` - Detailed setup guide

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

### Baseline Cache Staleness
**Problem:** Cached baseline may be outdated if baseline version changes.

**Mitigation:**
- Store version ID in baseline-version.json
- Compare cached version with configured baseline version
- Auto-regenerate cache if mismatch detected

### Cleanup on Abort
**Problem:** If CI/CD job is cancelled mid-verification, temporary files may remain.

**Mitigation:**
- Context manager ensures cleanup in finally block
- Next run detects and cleans stale verification-* files
- Document manual cleanup procedure

## Risk & Mitigation

**Risk:** AI misinterprets changes, causes alert fatigue  
**Mitigation:** Provide clear guidance prompts, iterate based on feedback

**Risk:** Performance too slow for CI/CD  
**Mitigation:** Baseline caching reduces overhead; total time ~45-90 seconds is acceptable

**Risk:** Customers don't understand how to set baselines  
**Mitigation:** Clear documentation, video tutorials, examples, automated baseline caching

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

