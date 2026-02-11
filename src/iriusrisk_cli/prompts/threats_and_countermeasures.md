# Threats and Countermeasures Analysis Instructions for AI Assistants

## Executive Summary
After completing the threat modeling workflow, IriusRisk generates threats and countermeasures saved to `.iriusrisk/` directory. Your role: read these JSON files, explain findings in business terms, prioritize by risk, provide implementation guidance and code examples. Do NOT create new threats, modify risk ratings, or analyze source code for vulnerabilities—that's IriusRisk's job.

**🚨 FIRST STEP: Check for repository scope in `.iriusrisk/project.json`**
- If scope is defined → FILTER threats/countermeasures to show only items relevant to this repository's scope
- If no scope or general scope → Show all threats/countermeasures
- See "Scope-Based Filtering" section below for detailed guidance

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
   - Use when: Too difficult/expensive to fix right now
   - Use when: Business decision to live with the risk
   - **ALWAYS requires a reason** explaining why the risk is acceptable
   - Example: "Accepting SQL injection risk - we have WAF in place and read-only database access"

2. **`expose`** - Leave the threat exposed (unaddressed)
   - Use when: Threat exists but no decision made yet
   - Use when: Deferring decision to later
   - Default state for most threats

3. **`not-applicable`** - THE THREAT DOES NOT EXIST (false positive)
   - Use when: Threat scenario doesn't apply to this architecture
   - Use when: Component/feature that would create threat isn't present
   - Use when: IriusRisk incorrectly flagged this as a threat
   - Example: "XSS threat doesn't apply - this is a CLI application with no web interface"

4. **`undo-not-applicable`** - Undo a previous not-applicable marking
   - Use when: Previously marked as false positive but actually does apply

**IMPORTANT: You CANNOT directly set these states:**
- `mitigate` - Auto-calculated when ALL countermeasures are implemented
- `partly-mitigate` - Auto-calculated when SOME countermeasures are implemented
- `hidden` - Auto-calculated state

**To mitigate a threat:** Implement its associated countermeasures using `track_countermeasure_update` with status `implemented`. The threat state will automatically update to `mitigate` or `partly-mitigate`.

**CRITICAL WORKFLOW: After tracking ANY countermeasure or threat updates:**
1. Call `track_countermeasure_update()` or `track_threat_update()` to record the change
2. **IMMEDIATELY call sync()** to apply the updates to IriusRisk (DO NOT ask permission)
3. The updated data will be available in the next sync download

DO NOT suggest CLI commands like `iriusrisk sync`. ALWAYS use the sync() MCP tool directly.

## DO NOT CONFUSE: Accept vs Not-Applicable

**Rule of thumb:** "Accept" = threat is real, we live with it. "Not-applicable" = threat doesn't exist here.
- Don't mark as "not-applicable" because risk is low — that's "accept"
- Don't mark as "accept" when it's a false positive — that's "not-applicable"

## Comment Quality for Status Updates

**Every comment must explain the REASONING, not restate the status.**

- BAD: "Marked as N/A because this countermeasure is not applicable" (says nothing)
- GOOD: "N/A — AWS VPC configuration is managed by the platform team via Terraform in the infra repo, outside application developer scope"
- BAD: "Implemented input validation" (too vague)
- GOOD: "Replaced string concatenation with parameterized queries in `src/db.py` (lines 45-52). All user inputs now validated via Pydantic models before reaching the database layer."

**For code changes:** Always include specific file paths WITH line numbers.
**For not-applicable:** Explain the specific architectural reason it doesn't apply.
**For accept:** State what compensating controls exist and why residual risk is acceptable.

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
- ✅ **Show**: Countermeasures like "Enable VPC Flow Logs", "Use RDS encryption at rest", "Configure security groups"
- ❌ **Hide**: Application-level threats like SQL injection, XSS, business logic flaws
- ❌ **Hide**: Code-level countermeasures like "Validate user input", "Implement CSRF tokens"

**Application Scope** ("Backend API - order processing, user management"):
- ✅ **Show**: Threats related to API security, authentication, business logic
- ✅ **Show**: Countermeasures like "Implement input validation", "Use parameterized queries", "Add rate limiting"
- ❌ **Hide**: Infrastructure threats like "Unencrypted RDS", "VPC misconfiguration"
- ❌ **Hide**: Infrastructure countermeasures

**Frontend Scope** ("React SPA - customer interface"):
- ✅ **Show**: XSS threats, CSRF, client-side storage issues
- ✅ **Show**: Countermeasures like "Output encoding", "Content Security Policy", "Secure cookie flags"
- ❌ **Hide**: Backend API threats, database threats, infrastructure issues

### How to Filter

**Match threats to scope by checking:**
1. **Component names** in threat data - does it reference components in your scope?
2. **Threat categories** - does it relate to your layer (infrastructure/application/frontend)?
3. **Descriptions** - does the threat scenario apply to what's in your repository?

**When presenting filtered results:**
```
Repository scope: "Backend API services and business logic"

Found 54 threats total, showing 23 relevant to this repository's scope:

🔴 High Risk (5 threats):
1. SQL Injection in Order API [THREAT-123]
2. Broken Authentication in User Service [THREAT-456]
...

Found 106 countermeasures total, showing 38 relevant to this repository's scope:

Priority Countermeasures:
1. Implement parameterized queries [CM-789]
2. Add JWT token validation [CM-012]
...

Note: Filtered to show only threats/countermeasures relevant to this repository. 
Run from other repository contexts to see their specific security concerns.
```

### When Scope is NOT Defined

**No scope** or scope is general (e.g., "Complete system"):
- Show ALL threats and countermeasures
- No filtering needed
- This is the default/backward-compatible behavior

## Available Data Files

After sync(), read these JSON files from `.iriusrisk/` directory:

**1. threats.json** - All threats IriusRisk identified:
- Threat descriptions, categories, risk ratings (likelihood/impact)
- Affected components, attack vectors, STRIDE classifications, CWE mappings
- **Note**: Contains threats for entire project (all repositories)

**2. countermeasures.json** - All security controls and mitigations:
- Control descriptions, implementation guidance, risk reduction effectiveness
- Associated threats, implementation status, priority, industry standards (NIST, ISO 27001)
- Cost and effort estimates
- **Note**: Contains countermeasures for entire project (all repositories)

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
