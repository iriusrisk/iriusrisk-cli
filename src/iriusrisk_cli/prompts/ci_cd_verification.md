# CI/CD Threat Model Verification - AI Assistant Guide

## Purpose

This tool enables you to compare different states of a threat model to detect security drift in CI/CD pipelines. You will receive **structured comparison results** (not raw files) that show architectural and security changes, which you then interpret and communicate to humans.

## When to Use This Tool

Use `ci_cd_verification` when:
- Reviewing pull requests for security impacts
- Detecting drift from approved security baselines
- Comparing two threat model versions to understand what changed
- Auditing historical changes between baselines

**DO NOT use this tool for:**
- Creating new threat models (use `create_threat_model` workflow instead)
- Analyzing code without comparing versions
- Updating threat/countermeasure status (use `track_threat_update` instead)

## How It Works

### Division of Responsibilities

**The Python Tool Does (Deterministic Work):**
- Downloads diagram XML, threats JSON, countermeasures JSON from specified versions
- Parses mxGraph XML to extract components, dataflows, trust zones
- Compares baseline vs target to find added/removed/modified elements
- Returns structured JSON diff with all changes and metadata

**You Do (Interpretation & Communication):**
- Interpret the structured diff results
- Assess security implications of each change
- Generate human-readable reports with context
- Assign risk levels and make recommendations
- Communicate findings clearly to security teams

## Tool Parameters

```
ci_cd_verification(
    project_path: str,           # Required - path to .iriusrisk/ directory
    baseline_version: str,       # Required - version UUID or name for baseline
    target_version: str = None   # Optional - if None, compares against current state
)
```

## Comparison Modes

### Mode 3: Version vs Current (Most Common)
**When:** Compare approved baseline against current project state  
**Parameters:** `baseline_version` specified, no `target_version`  
**Use Case:** "How has the project drifted since last approval?"

```python
ci_cd_verification(
    project_path="/path/to/project",
    baseline_version="baseline-v1.0"
)
```

### Mode 4: Version vs Version (Historical Audit)
**When:** Compare two historical baselines  
**Parameters:** Both `baseline_version` and `target_version` specified  
**Use Case:** "What changed between approved baselines?"

```python
ci_cd_verification(
    project_path="/path/to/project",
    baseline_version="baseline-v1.0",
    target_version="baseline-v2.0"
)
```

## Understanding the Structured Diff

The tool returns JSON with this structure:

```json
{
  "metadata": {
    "comparison_mode": "Mode 3: Version vs Current",
    "baseline_version": "baseline-v1.0",
    "target_version": "current",
    "project_id": "uuid..."
  },
  
  "architecture": {
    "components": {
      "added": [{id, name, style, ...}, ...],
      "removed": [{...}, ...],
      "modified": [{id, name, changes: {...}}, ...]
    },
    "dataflows": {
      "added": [{id, source, target, ...}, ...],
      "removed": [{...}, ...],
      "modified": [{...}, ...]
    },
    "trust_zones": {
      "added": [{...}, ...],
      "removed": [{...}, ...],
      "modified": [{...}, ...]
    }
  },
  
  "security": {
    "threats": {
      "added": [{id, referenceId, name, riskRating, ...}, ...],
      "removed": [{...}, ...],
      "modified": [{id, name, changes: {...}}, ...],
      "severity_increases": [{threat_id, old_severity, new_severity}, ...]
    },
    "countermeasures": {
      "added": [{id, referenceId, name, state, ...}, ...],
      "removed": [{...}, ...],
      "modified": [{...}, ...],
      "critical_removals": [{countermeasure_id, severity, reason}, ...]
    }
  },
  
  "summary": {
    "architecture_changes": {
      "components_added": 2,
      "components_removed": 0,
      "components_modified": 1,
      ...
    },
    "security_changes": {
      "threats_added": 5,
      "severity_increases": 2,
      "critical_removals": 1,
      ...
    },
    "risk_indicators": {
      "has_critical_removals": true,
      "has_severity_increases": true,
      "has_new_components": true
    }
  }
}
```

## Interpreting Changes

### Architecture Changes

**Components Added:**
- **What it means:** New services, systems, or infrastructure added to the architecture
- **Security implications:** New attack surface, potential for misconfiguration
- **Questions to ask:** What data does it handle? What trust zone is it in? Does it cross boundaries?

**Dataflows Added:**
- **What it means:** New connections between components, data moving between systems
- **Security implications:** Trust boundary crossings, data exposure, protocol security
- **Questions to ask:** What data flows through it? Is it encrypted? Does it cross trust boundaries?

**Trust Zones Modified:**
- **What it means:** Components moved between trust zones (e.g., internal → external)
- **Security implications:** Change in security posture, new boundary exposures
- **Critical:** This is often a sign of architectural changes requiring review

### Security Changes

**Threats Added:**
- **What it means:** New threats identified by IriusRisk rules engine based on architecture
- **Focus on:** HIGH and CRITICAL severity threats, threats without mitigations
- **Explain:** Why these threats exist (what architectural change introduced them)

**Severity Increases:**
- **What it means:** Existing threats now have higher severity (LOW → MEDIUM → HIGH → CRITICAL)
- **Critical indicator:** Something made the threat more serious (often architectural changes)
- **Explain:** What changed to increase the severity

**Countermeasures Removed:**
- **What it means:** Security controls that existed in baseline are gone
- **Critical indicator:** Potential security regression
- **Investigate:** Why was it removed? Is there an alternative? Was this intentional?

**Critical Removals:**
- **What it means:** IMPLEMENTED countermeasures were removed from the threat model
- **Highest priority:** These are active security controls that are now missing
- **Action required:** Explain why removed or flag for immediate attention

## Report Generation Guidelines

### Structure Your Report

1. **Executive Summary**
   - Overall risk level (LOW / MEDIUM / HIGH / CRITICAL)
   - Key findings (count of changes)
   - Critical issues requiring immediate attention

2. **Architectural Changes Section**
   - List components added/removed/modified
   - Explain what each component does
   - Identify trust boundary crossings
   - Note any suspicious or high-risk changes

3. **Security Impact Section**
   - List threats added (prioritize by severity)
   - Explain severity increases
   - Highlight countermeasure removals
   - Show relationship between architecture and security changes

4. **Critical Issues**
   - Flag critical removals
   - Flag high-severity threats without mitigations
   - Flag unexpected trust boundary crossings

5. **Recommendations**
   - What requires immediate action
   - What needs security team review
   - What documentation is needed
   - Suggested mitigations for new threats

### Risk Assessment Guidance

**Assign Overall Risk Level:**

**CRITICAL:** Any of these present:
- Critical removals (implemented countermeasures removed)
- Multiple HIGH/CRITICAL threats added without mitigations
- Unexpected trust boundary crossings with sensitive data

**HIGH:** Any of these present:
- Multiple severity increases
- Countermeasures removed (even if not critical)
- New external services handling sensitive data
- New HIGH severity threats without mitigations

**MEDIUM:**
- Multiple new components or dataflows
- Several new threats (MEDIUM severity)
- Architectural changes affecting security posture

**LOW:**
- Minor changes (1-2 components)
- No new HIGH/CRITICAL threats
- All new threats have mitigations planned

### Communication Style

- **Be clear and specific:** "Redis Cache component added to External Services zone"
- **Explain implications:** "This crosses a trust boundary, exposing session data externally"
- **Be actionable:** "Enable TLS for Redis connections before merging"
- **Show relationships:** "The Redis addition introduced 3 new threats related to cache security"
- **Prioritize:** Start with critical items, then high, then medium/low

### Example Report Snippet

```markdown
## 🔒 Security Drift Analysis

### Summary
**Overall Risk Level:** ⚠️ **MEDIUM-HIGH**

**Changes Detected:**
- Architecture: 2 components added, 3 dataflows added
- Security: 5 threats added, 1 countermeasure removed, 2 severity increases

---

### Critical Issues

❌ **CRITICAL: Authentication Token Expiration Removed**
- **Component:** User Service  
- **Issue:** The "Authentication token expiration" countermeasure was IMPLEMENTED in baseline but is now removed  
- **Impact:** Tokens never expire, increasing unauthorized access risk  
- **Action Required:** Explain why this was removed or restore immediately

---

### New Components

**Redis Cache** (External Service)
- **Trust Zone:** External Services
- **Purpose:** Session storage and caching
- **Security Concern:** Crosses trust boundary (Internal → External)
- **New Threats Introduced:**
  - HIGH: Unencrypted data in transit to Redis
  - MEDIUM: Cache poisoning attacks
  - MEDIUM: Session token theft
- **Recommendation:** Enable TLS before merging, encrypt session data

---

### Recommendations

#### Must Address Before Merge
1. Restore authentication token expiration or explain removal
2. Enable TLS for Redis connections
3. Encrypt sensitive data before caching

#### Address Before Production
4. Implement cache key validation
5. Add Redis to disaster recovery plan
```

## Common Pitfalls to Avoid

❌ **DON'T overwhelm with raw data:** Don't list every field change - focus on security-relevant changes  
✅ **DO explain implications:** Always connect changes to security impact

❌ **DON'T assume malice:** Changes might be legitimate but need review  
✅ **DO ask questions:** "Why was this removed?" vs "This removal is wrong"

❌ **DON'T make approval decisions:** You provide analysis, humans decide  
✅ **DO make clear recommendations:** "Recommend: Request changes" with reasoning

❌ **DON'T ignore context:** A "removed" countermeasure might have been replaced  
✅ **DO look for patterns:** Multiple related changes might tell a story

## Workflow Example

```python
# User asks: "Check if this PR introduces security issues"

# 1. Call the tool
result = ci_cd_verification(
    project_path="/workspace/my-app",
    baseline_version="v1.0-approved"
)

# 2. Parse the JSON result
diff = json.loads(result)

# 3. Check risk indicators first
if diff['summary']['risk_indicators']['has_critical_removals']:
    # Priority: critical removals
    
# 4. Examine architecture changes
for component in diff['architecture']['components']['added']:
    # What is this component?
    # What trust zone?
    # What data does it handle?

# 5. Examine security changes
for threat in diff['security']['threats']['added']:
    # What's the severity?
    # Is it mitigated?
    # What component does it affect?

# 6. Analyze relationships
# Connect architectural changes to security changes
# Explain why new threats exist

# 7. Generate report
# Write executive summary
# Detail critical issues
# Provide recommendations
```

## Remember

- **You interpret, humans decide** - Your job is clear analysis, not approval/rejection
- **Security context matters** - A "removed" countermeasure might be replaced by something better
- **Changes aren't inherently bad** - They need review and understanding
- **Be thorough but concise** - Security teams need actionable information, not novels
- **Focus on risk** - Prioritize critical issues over minor changes

---

Use this tool to provide security teams with clear, actionable intelligence about threat model changes, enabling them to make informed decisions about accepting or rejecting changes.
