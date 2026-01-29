# CI/CD Security Verification - AI Assistant Guide (Orchestrator)

## Purpose

This is a **meta-workflow tool** that orchestrates comprehensive CI/CD security reviews by combining version comparison, control verification, risk analysis, and reporting. Use this when you need a complete, automated security assessment.

## When to Use This Tool

Use `ci_cd_verification` when:
- Running in automated CI/CD pipeline (headless, comprehensive review)
- User requests "full security review" or "complete security assessment"
- Pre-deployment security gate requiring thorough analysis
- User says "run all security checks" or similar

**Use individual tools instead when:**
- Just want to compare versions → Use `compare_versions`
- Just want to verify controls → Use `countermeasure_verification`
- User has specific, narrow request → Use appropriate specific tool

## How It Works

This tool **guides you through a multi-step workflow**, calling other tools as needed:

### Step 1: Architectural Drift Detection
**Tool:** `compare_versions`  
**Action:** Compare baseline version against current/PR state  
**Output:** Structured diff showing what changed

### Step 2: Control Implementation Verification
**Tool:** `countermeasure_verification`  
**Action:** Verify countermeasures are correctly implemented  
**Condition:** Only if PR/changes are linked to issue tracker tasks  
**Output:** Implementation verification results

### Step 3: Risk Delta Analysis
**Action:** Analyze comparison results for security implications  
**Process:** Interpret structured diff, assess risk changes, identify critical issues

### Step 4: Generate Comprehensive Report
**Action:** Create human-readable security report  
**Output:** Unified report covering all findings

## Orchestration Workflow

```python
# User: "Run full CI/CD security verification"

# The tool returns workflow guidance:
result = ci_cd_verification(baseline_version="v1.0-approved")

# You then execute the workflow:

# STEP 1: Architectural drift
version_diff = compare_versions(baseline_version="v1.0-approved")
diff = json.loads(version_diff)

# Analyze the diff
architecture_changes = diff['architecture']
security_changes = diff['security']

# STEP 2: Control verification (if applicable)
# Check if PR has issue tracker references
issue_refs = extract_issue_refs_from_git()  # Your text parsing

if issue_refs:
    cm_verification = countermeasure_verification(issue_references=issue_refs)
    # Analyze and update test statuses
    
# STEP 3: Risk analysis
# Interpret the diffs, assess security impact

# STEP 4: Generate unified report
# Combine all findings into one comprehensive report
```

## When Each Sub-Tool Is Needed

### compare_versions - ALWAYS
**Always call this** - it's the foundation of the security review
- Shows what changed architecturally
- Shows new threats/countermeasures
- Provides structured data for analysis

### countermeasure_verification - CONDITIONAL
**Call only if:**
- PR has issue tracker references (PROJ-1234 in branch/commits)
- Countermeasures are linked to those issues
- PR claims to implement specific controls

**Skip if:**
- No issue tracker integration
- PR is purely architectural (new features, not security fixes)
- No countermeasures linked to PR's issues

### Risk Analysis & Reporting - ALWAYS
**Always do this** - synthesize findings into actionable report

## Comprehensive Report Structure

Your final report should combine findings from all steps:

```markdown
# 🚨 CI/CD Security Verification Report

## Executive Summary
- Overall risk level (CRITICAL/HIGH/MEDIUM/LOW)
- Key findings count
- Recommendation (APPROVE/REQUEST CHANGES/REJECT)

## Architectural Changes
[From compare_versions output]
- Components added/removed/modified
- Dataflows added/removed/modified  
- Trust zone changes

## Security Impact
[From compare_versions output]
- New threats introduced
- Severity increases
- Countermeasures removed
- Risk indicators

## Control Implementation Verification
[From countermeasure_verification output - if applicable]
- Controls verified
- Implementation status (passed/failed)
- Evidence and findings

## Risk Delta Analysis
[Your interpretation]
- How do changes affect overall security posture?
- Relationship between architecture and security changes
- Critical issues requiring attention

## Recommendations
- What must be fixed before merge
- What should be addressed before production
- What documentation is needed
```

## Comparison vs Orchestration

**compare_versions (focused):**
- One specific task: compare two states
- Returns data, minimal interpretation
- User wants specific comparison

**ci_cd_verification (comprehensive):**
- Multiple tasks orchestrated
- Full security review workflow
- User wants complete assessment

## Example Usage Scenarios

### Scenario A: Developer Wants Quick Comparison
```
User: "What changed since baseline?"
You: Call compare_versions(baseline_version="baseline")
     Interpret results, show summary
```

### Scenario B: CI/CD Pipeline Full Review
```
User: "Run CI/CD security checks"
You: Call ci_cd_verification(baseline_version="v1.0-approved")
     Follow orchestration guidance
     Call compare_versions
     Call countermeasure_verification (if relevant)
     Generate comprehensive report
```

### Scenario C: Developer Implementing Control
```
User: "Did I implement PROJ-1234 correctly?"
You: Call countermeasure_verification(issue_references="PROJ-1234")
     Analyze code vs countermeasure requirement
     Update test status
```

## Remember

- **This is an orchestrator** - it coordinates other tools, doesn't do the work itself
- **Be flexible** - Not every workflow needs all steps
- **Use judgment** - Skip irrelevant steps (e.g., no control verification if no issue tracker)
- **Comprehensive output** - Final report should cover all security aspects
- **Automated context** - In CI/CD, you have full autonomy to run complete workflow

---

Use this tool for comprehensive, automated CI/CD security reviews that combine multiple analyses into one thorough security assessment.
