# CI/CD Drift Detection Feature

**Status:** Ready for Implementation  
**Target:** v0.4.0  
**Purpose:** Design document for AI-powered security drift detection in CI/CD pipelines

**Implementation Approach:** Client-side OTM comparison (not using IriusRisk server-side version comparison API)

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
1. Compare current codebase against an approved baseline
2. Surface architectural and security changes
3. Generate human-readable reports for manual review
4. Post findings to PRs/tickets for security team review

**NOT in scope for MVP:**
- Automated approval/rejection decisions
- Policy rule engines
- Enforcement gates
- Approved component lists

## High-Level Workflow

### One-Time Setup
1. Security team reviews and approves initial threat model
2. Save baseline threat model (OTM file) in repository
3. Configure CI/CD to run AI verification on PRs/deployments

### Per-Deployment Workflow
1. **CI/CD triggers** → AI agent activates
2. **AI generates OTM** → Analyzes current codebase state
3. **Load baseline** → Retrieve approved baseline OTM from repository
4. **Compare threat models** → Client-side comparison of current vs baseline
5. **AI interprets** → Assesses security implications of changes
6. **Generate report** → Human-readable findings
7. **Post results** → PR comment, Slack, ticket, etc.
8. **Human review** → Security team decides if acceptable

**Note:** Comparison is performed locally (not via IriusRisk API) to ensure reliability and avoid dependency on server-side features.

### What AI Reports
- Components added/removed/edited
- Dataflows added/removed/edited
- Threats added/removed/edited
- Countermeasures added/removed/edited
- Security impact assessment
- Risk level changes

### Human Decision Points
- Is the new component acceptable?
- Are the architectural changes appropriate?
- Do new threats have adequate mitigations?
- Does this require architecture review?

## Technical Components

### OTM File Comparison (Client-Side)

The comparison is performed by comparing OTM (Open Threat Model) files directly, without relying on IriusRisk server-side APIs. This approach provides:
- **Reliability:** No dependency on server-side features
- **Speed:** Local comparison is fast
- **Transparency:** Clear diff of JSON structures
- **Portability:** Works offline or with any OTM source

**Note:** IriusRisk's version comparison API endpoint has limitations that make it unsuitable for CI/CD workflows. Client-side OTM comparison is the recommended approach.

### New MCP Tool: `ci_cd_verification`

**Purpose:** Guide AI agents through the drift detection workflow

**Workflow:**
1. Generate OTM from current codebase
2. Load baseline OTM from repository
3. Compare the two OTM files (components, threats, dataflows, countermeasures)
4. Identify security-relevant changes
5. Generate human-readable report

**AI Usage:**
- Analyze codebase to generate current OTM
- Compare against baseline OTM
- Interpret changes for security implications
- Generate report with recommendations

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

1. **OTM Comparison Logic** - Client-side diff of threat models
2. **MCP Tool** - `ci_cd_verification()` for AI workflow guidance
3. **MCP Prompt** - Detailed instructions for AI agents
4. **CLI Helper** - Optional command for manual comparison
5. **Documentation** - CI/CD setup guide and examples

## MVP Feature List

### Must Have
- [ ] OTM file comparison logic (components, threats, dataflows, countermeasures)
- [ ] MCP tool: `ci_cd_verification()` for AI workflow
- [ ] MCP prompt: `ci_cd_verification.md` with detailed guidance
- [ ] Baseline OTM management (save/load from repository)
- [ ] Documentation: CI/CD setup guide
- [ ] Example: GitHub Actions workflow

### Nice to Have (Post-MVP)
- CLI command for manual OTM comparison
- Pretty table output for comparisons
- Summary statistics (X threats added, Y removed, etc.)
- Baseline versioning and history
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
## 🔒 Security Drift Analysis

### Summary
Comparison against baseline: v2.1-approved (created 2025-01-05)

**Changes detected:**
- 2 components added
- 8 threats added
- 5 countermeasures added
- 1 countermeasure removed

### Architectural Changes

**Components Added:**
1. **Redis Cache** (External Service)
   - Used for session storage
   - Crosses trust boundary: Application → External Service
   
2. **Stripe Payment API** (External Service)
   - Used for payment processing
   - Handles sensitive data: credit card information

### Security Impact

**New Threats:**
- **HIGH:** Unencrypted data in transit to Redis
  - Session tokens transmitted without TLS
  - Recommendation: Enable TLS for Redis connections
  
- **HIGH:** Third-party data exposure via Stripe
  - Credit card data sent to external service
  - Recommendation: Verify Stripe PCI-DSS compliance
  
- **MEDIUM:** Cache poisoning attacks
  - Redis cache could be manipulated
  - Recommendation: Implement cache validation

**Countermeasures Removed:**
- **Authentication token expiration** (Component: User Service)
  - Was: 15 minute timeout
  - Now: Removed
  - **CRITICAL:** This creates a security regression

### Recommendations

**Requires Security Review:**
1. Why was authentication token expiration removed?
2. Redis security configuration needs verification
3. Stripe integration requires PCI-DSS assessment

**Suggested Actions:**
- Restore authentication token expiration
- Enable TLS for Redis
- Document Stripe PCI compliance
- Update security runbook

### Links
- [Full threat model comparison](https://iriusrisk.com/projects/abc-123/compare)
- [Threat model diagram](https://iriusrisk.com/projects/abc-123/diagram)
```

## Baseline Management Strategy

### Baseline OTM File
The **baseline OTM file** is the security-approved reference point:
1. Security team reviews and approves initial threat model
2. Generate OTM: `iriusrisk otm export threat-model.otm`
3. Store in repository: `.iriusrisk/baseline.otm` or `.security/baseline-threat-model.otm`
4. Commit to version control with approval documentation
5. Update baseline when major architectural changes are approved

### OTM File Naming Convention
For storing multiple baselines or history:
- **Approved Baseline:** `baseline.otm` or `baseline-approved-2024-01-12.otm`
- **PR Snapshots:** `pr-1234-threat-model.otm` (temporary, for comparison)
- **Release Baselines:** `baseline-v1.0.0.otm`, `baseline-v2.0.0.otm`
- **Environment Baselines:** `baseline-production.otm`, `baseline-staging.otm`

### Baseline Update Process
When architectural changes are approved:
1. Generate new OTM from current state
2. Security team reviews changes
3. If approved, replace `baseline.otm` with new version
4. Commit with clear message: "Update security baseline - approved Redis integration"
5. Tag commit for audit trail

### Storage Recommendations
- **Version Control:** Store baseline in Git alongside code
- **Location:** `.iriusrisk/baseline.otm` (hidden) or `.security/threat-model.otm` (visible)
- **Backup:** Keep historical baselines with version tags
- **Documentation:** Include README explaining when baseline was last approved

## Open Questions

1. **Frequency:**
   - Run on every PR?
   - Only on deployment?
   - Periodic audits?
   - Configurable per-team?

3. **Scope:**
   - Compare full project or just changed services?
   - For monorepos, per-service or whole repo?
   - How to handle microservices architectures?

4. **Performance:**
   - Full threat model generation can be slow
   - Can we do incremental analysis?
   - Cache OTM files between runs?

5. **False Positives:**
   - What if AI incorrectly flags benign changes?
   - How to suppress known-safe patterns?
   - Feedback mechanism for AI improvement?

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

## Technical Notes

### OTM File Structure
The Open Threat Model (OTM) format is a JSON structure containing:
- **Components:** System components (services, databases, APIs)
- **Dataflows:** Data movement between components
- **Threats:** Security threats identified by IriusRisk
- **Countermeasures:** Security controls/mitigations
- **Trust Zones:** Security boundaries in the architecture

### Comparison Algorithm
Client-side comparison logic identifies:
- **Added:** New elements in current OTM not in baseline
- **Removed:** Elements in baseline missing from current OTM
- **Modified:** Elements with changed properties (name, description, risk rating)

### Why Not Use IriusRisk Version Comparison API?
IriusRisk provides a version comparison API endpoint, but testing revealed it's not suitable for CI/CD workflows due to reliability issues. The client-side OTM comparison approach is more reliable and doesn't depend on server-side processing.

### Performance Considerations
- OTM file parsing: < 1 second for typical projects
- Comparison logic: < 1 second for files up to 1000 elements
- Total overhead in CI/CD: ~ 2-5 seconds
- AI interpretation time: Variable (30-60 seconds typical)

## Implementation Plan

### Phase 1: Core Functionality (MVP)
1. Create OTM comparison logic module
2. Implement MCP tool `ci_cd_verification()`
3. Create MCP prompt `ci_cd_verification.md`
4. Add baseline OTM management utilities
5. Testing with sample OTM files

### Phase 2: Documentation & Examples
1. CI/CD setup guide
2. GitHub Actions workflow example
3. Usage documentation for AI agents
4. Video walkthrough

### Phase 3: Polish & Iteration
1. Gather customer feedback
2. Improve AI prompts based on usage patterns
3. Add CLI command for manual comparison
4. Performance optimization

## Related Files

**To Create:**
- `src/iriusrisk_cli/prompts/ci_cd_verification.md` - AI workflow guidance
- `src/iriusrisk_cli/utils/otm_comparison.py` - OTM diff logic
- `src/iriusrisk_cli/mcp/tools/ci_cd_verification.py` - MCP tool implementation
- `.github/workflows/security-drift-check.yml` - Example GitHub Action

**To Modify:**
- `commands/mcp.py` - Register new MCP tool
- `commands/otm.py` - Add baseline save/load helpers (optional)

**Documentation:**
- `README.md` - Add CI/CD verification section
- `CHANGELOG.md` - Add v0.4.0 entry
- New doc: `docs/CICD_VERIFICATION.md` - Detailed setup guide

## Risk & Mitigation

**Risk:** AI misinterprets changes, causes alert fatigue  
**Mitigation:** Provide clear guidance prompts, iterate based on feedback

**Risk:** Performance too slow for CI/CD  
**Mitigation:** Optimize OTM generation, consider incremental analysis

**Risk:** Customers don't understand how to set baselines  
**Mitigation:** Clear documentation, video tutorials, examples

**Risk:** False sense of security if not reviewed  
**Mitigation:** Emphasize "visibility not enforcement" in docs

## Notes

- This is **visibility tooling**, not a security gate
- Humans make all accept/reject decisions
- Focus on making security team's job easier
- Leverage IriusRisk's existing computation power
- AI's value is in interpretation and communication

