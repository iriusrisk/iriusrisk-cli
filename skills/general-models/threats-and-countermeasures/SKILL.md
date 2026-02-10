---
name: threats-and-countermeasures
description: Analyze IriusRisk-generated threats and countermeasures from JSON files. Use when user asks about threats, security issues, or wants to understand security findings. Read and explain findings, prioritize by risk, provide implementation guidance.
---

# Threats and Countermeasures Analysis Instructions

## Executive Summary
After completing the threat modeling workflow, IriusRisk generates threats and countermeasures saved to `.iriusrisk/` directory. Your role: read these JSON files, explain findings in business terms, prioritize by risk, provide implementation guidance and code examples. Do NOT create new threats, modify risk ratings, or analyze source code for vulnerabilities—that's IriusRisk's job.

**🚨 FIRST STEP: Check for repository scope in `.iriusrisk/project.json`**
- If scope is defined → FILTER threats/countermeasures to show only items relevant to this repository's scope
- If no scope or general scope → Show all threats/countermeasures

**⚠️ IMPORTANT: If questionnaires have NOT been completed yet, recommend completing them BEFORE analyzing threats:**
- Questionnaires refine the threat model based on actual implementation
- Results in fewer false positives and more accurate threats
- Call **questionnaire_guidance()** for instructions on completing questionnaires
- Takes only a few minutes but significantly improves threat quality

## CRITICAL: Understanding Threat States vs State Transitions

**Threat States (What You See in Data):**
- `expose` - Threat is unaddressed and exposed
- `accept` - Real threat exists, risk consciously accepted
- `mitigate` - Threat is fully mitigated (AUTO-CALCULATED)
- `partly-mitigate` - Threat is partially mitigated (AUTO-CALCULATED)
- `na` (not-applicable) - Threat is a false positive / doesn't apply
- `hidden` - Threat is hidden (AUTO-CALCULATED)

**State Transitions You Can Set (Via track_threat_update):**

1. **`accept`** - THE THREAT IS REAL, but accepting the risk
   - Use when: Threat exists but compensating controls are in place
   - Use when: Risk is not worth the resources to fix
   - **ALWAYS requires a reason** explaining why the risk is acceptable
   - Example: "Accepting SQL injection risk - we have WAF in place and read-only database access"

2. **`expose`** - Leave the threat exposed (unaddressed)
   - Use when: Threat exists but no decision made yet
   - Default state for most threats

3. **`not-applicable`** - THE THREAT DOES NOT EXIST (false positive)
   - Use when: Threat scenario doesn't apply to this architecture
   - Use when: Component/feature that would create threat isn't present
   - Example: "XSS threat doesn't apply - this is a CLI application with no web interface"

**IMPORTANT: You CANNOT directly set these states:**
- `mitigate` - Auto-calculated when ALL countermeasures are implemented
- `partly-mitigate` - Auto-calculated when SOME countermeasures are implemented

**To mitigate a threat:** Implement its associated countermeasures using `track_countermeasure_update` with status `implemented`.

**CRITICAL WORKFLOW: After tracking ANY countermeasure or threat updates:**
1. Call `track_countermeasure_update()` or `track_threat_update()` to record the change
2. **IMMEDIATELY call sync()** to apply the updates to IriusRisk (DO NOT ask permission)

## DO NOT CONFUSE: Accept vs Not-Applicable

**WRONG**: Marking a threat as "not-applicable" because the risk is low or acceptable
**RIGHT**: Mark as "accept" - the threat exists, we acknowledge it, we accept the risk

**WRONG**: Marking a threat as "accept" when it's a false positive
**RIGHT**: Mark as "not-applicable" - the threat doesn't actually exist in this context

## Scope-Based Filtering for Multi-Repository Projects

**CRITICAL**: Before analyzing threats/countermeasures, check for repository scope in `.iriusrisk/project.json`:

```python
# Read project.json to check for scope
import json
with open('.iriusrisk/project.json', 'r') as f:
    project_config = json.load(f)
    scope = project_config.get('scope')

if scope:
    print(f"Repository scope: {scope}")
    # FILTER threats and countermeasures based on this scope
```

### When Scope is Defined

**The sync command downloads ALL threats/countermeasures for the entire project**, but you should **only focus on threats/countermeasures relevant to this repository's scope**.

**Example Scenarios:**

**Infrastructure Scope** ("AWS infrastructure - ECS, RDS, VPC"):
- ✅ **Show**: Threats related to AWS components, network security, infrastructure configuration
- ✅ **Show**: Countermeasures like "Enable VPC Flow Logs", "Use RDS encryption at rest"
- ❌ **Hide**: Application-level threats like SQL injection, XSS, business logic flaws
- ❌ **Hide**: Code-level countermeasures like "Validate user input"

**Application Scope** ("Backend API - order processing, user management"):
- ✅ **Show**: Threats related to API security, authentication, business logic
- ✅ **Show**: Countermeasures like "Implement input validation", "Use parameterized queries"
- ❌ **Hide**: Infrastructure threats like "Unencrypted RDS", "VPC misconfiguration"

### When Scope is NOT Defined

**No scope** or scope is general:
- Show ALL threats and countermeasures
- No filtering needed
- This is the default behavior

## Available Data Files

After sync(), read these JSON files from `.iriusrisk/` directory:

**1. threats.json** - All threats IriusRisk identified:
- Threat descriptions, categories, risk ratings (likelihood/impact)
- Affected components, attack vectors, STRIDE classifications, CWE mappings

**2. countermeasures.json** - All security controls and mitigations:
- Control descriptions, implementation guidance, risk reduction effectiveness
- Associated threats, implementation status, priority, industry standards

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
A: Sort threats by risk rating (likelihood × impact) → consider implementation effort → recommend prioritized action plan

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

Your role: Make IriusRisk's professional security analysis accessible and actionable for users' specific context.
