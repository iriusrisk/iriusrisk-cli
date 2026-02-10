---
name: countermeasure-verification
description: Verify that security controls (countermeasures) linked to issue tracker tasks are correctly implemented in code. Use when reviewing PRs that claim to implement specific security controls or validating documented controls match implementation.
---

# Countermeasure Implementation Verification

## Purpose

Verify that security controls (countermeasures) linked to issue tracker tasks are correctly implemented in code. This workflow helps validate that when a developer claims "Fixed PROJ-1234: Implemented TLS for Redis", they actually did implement it correctly.

## When to Use This Skill

Use `countermeasure-verification` when:
- Reviewing PR that claims to implement specific security controls
- Developer working on issue tracker tasks linked to countermeasures
- Code review of security-critical changes
- Validating that documented controls match implementation

**DO NOT use when:**
- No issue tracker integration (no issueId fields in countermeasures)
- Just want to see what countermeasures exist (use threats-and-countermeasures instead)
- Comparing versions (use compare-versions instead)

## How It Works

### Division of Responsibilities

**The Tool Provides:**
- Access to countermeasures.json data
- Filtering by issue tracker references
- Workflow guidance for verification process

**You Do (AI Analysis):**
- Extract issue references from git context
- Read countermeasure requirements
- Analyze code changes vs requirements
- Determine if implementation is correct (pass/fail)
- Update test status via API (when test ID available)

## Workflow

### Step 1: Extract Issue References

**From Git Context (No code needed - just text parsing):**

```bash
# Branch name
feature/PROJ-1234-add-redis-tls → Extract: "PROJ-1234"

# Commit messages
git log --oneline -10
> Fix PROJ-1234: Enable TLS for Redis connections
> Implement PROJ-1235: Add input validation
Extract: "PROJ-1234", "PROJ-1235"

# PR title/description  
User provides or you extract from PR context
```

**Call the tool:**
```python
countermeasure_verification(issue_references="PROJ-1234,PROJ-1235")
```

**Or let the tool guide you if no references provided:**
```python
countermeasure_verification()
# Returns: Extract issue refs from git, then call again
```

### Step 2: Analyze Countermeasure Requirements

**The tool returns linked countermeasures:**
```json
{
  "linked_countermeasures": 2,
  "countermeasures": [
    {
      "id": "cm-123",
      "name": "Enable TLS encryption for Redis connections",
      "description": "<p>Configure Redis client to use TLS...</p>",
      "state": "implemented",
      "issueId": "PROJ-1234",
      "issueLink": "https://jira.company.com/browse/PROJ-1234",
      "_links": {
        "test": {"href": "https://.../tests/test-456"}
      }
    }
  ]
}
```

**For each countermeasure:**
1. Read the `description` - What needs to be implemented?
2. Read the `name` - What control is this?
3. Note the `issueId` - Confirms linkage
4. Extract `test` link - You'll need this to update test status

### Step 3: Verify Implementation in Code

**Analyze the code changes:**

```python
# Example: "Enable TLS for Redis connections"

# 1. Find Redis configuration in PR changes
# Look for: redis.conf, connection strings, environment variables

# 2. Check if TLS is actually enabled
redis_config = read_file('config/redis.conf')
if 'tls-port 6380' in redis_config and 'tls-cert-file' in redis_config:
    implementation_status = "PASSED"
    evidence = "TLS configured on port 6380 with certificate"
else:
    implementation_status = "FAILED"
    evidence = "TLS not configured, still using port 6379 without encryption"

# 3. Document your analysis
verification_notes = f"""
Countermeasure: Enable TLS for Redis
Issue: PROJ-1234
Analysis: {evidence}
Files checked: config/redis.conf, docker-compose.yml
Result: {implementation_status}
"""
```

### Step 4: Update Test Status (When Test ID Available)

**If countermeasure has `_links.test`:**

Extract test ID from the URL:
```python
test_url = countermeasure['_links']['test']['href']
# https://release.iriusrisk.com/api/v2/projects/countermeasures/tests/test-456
test_id = "test-456"  # Extract from URL
```

**Update test status via API:**

**Option A: Use existing track_countermeasure_update tool:**
```python
track_countermeasure_update(
    countermeasure_id="cm-123",
    status="implemented",  # Update state if needed
    reason="Verified implementation in PR",
    comment=verification_notes
)
```

**Option B: Future tool (if we add it):**
```python
update_countermeasure_test_status(
    test_id="test-456",
    test_result="passed",  # or "failed"
    notes=verification_notes
)
```

### Step 5: Generate Verification Report

**Report what you found:**

```markdown
## Control Implementation Verification Report

**Issue:** PROJ-1234 - Add TLS for Redis  
**Status:** ✅ VERIFIED

### Countermeasure: Enable TLS encryption for Redis connections
- **Implementation Status:** ✅ PASSED
- **Evidence:** 
  - Redis configured with TLS on port 6380
  - Certificate files present in config/certs/
  - Connection string updated to use rediss:// protocol
  - Environment variable `REDIS_TLS_ENABLED=true` set
- **Files Modified:**
  - config/redis.conf (added TLS configuration)
  - docker-compose.yml (added certificate volumes)
  - src/database.py (updated connection string)
- **Test Status:** Updated to PASSED

---

**Issue:** PROJ-1235 - Add input validation  
**Status:** ⚠️ PARTIALLY IMPLEMENTED

### Countermeasure: Validate and sanitize all user inputs
- **Implementation Status:** ⚠️ PARTIALLY PASSED
- **Evidence:**
  - Input validation added to 3 out of 5 endpoints
  - Missing validation on /admin/stats endpoint
  - Missing validation on /webhook endpoint
- **Files Modified:**
  - src/app.py (added validation to user registration, login, profile update)
- **Issues Found:**
  - Lines 104, 225: No input validation on admin and webhook endpoints
- **Test Status:** Updated to PARTIALLY-TESTED
- **Action Required:** Add validation to remaining endpoints
```

## Verification Criteria

### What "Correctly Implemented" Means

**For configuration controls:**
- Config files match countermeasure requirements
- Settings are actually applied (not just documented)
- No backdoors or bypass mechanisms

**For code controls:**
- Required functions/checks are present
- Applied to all relevant code paths (not just some)
- No obvious bugs or logic errors

**For infrastructure controls:**
- Resources provisioned as required
- Security groups/policies correctly configured
- No exceptions or overrides that defeat the control

### Pass/Fail Decision Criteria

**PASSED:**
- Control is fully implemented
- Covers all required scenarios
- No obvious bypasses or weaknesses
- Configuration matches requirements

**PARTIALLY-TESTED:**
- Control is mostly implemented
- Some edge cases or scenarios missing
- Minor issues that don't defeat the control

**FAILED:**
- Control not implemented
- Major gaps in implementation
- Obvious bypasses or errors
- Configuration incorrect or missing

## Common Verification Patterns

### TLS/Encryption Verification
```
Check: Config files (tls-port, certificates)
Check: Connection strings (rediss://, ssl=true)
Check: Environment variables (TLS_ENABLED)
Evidence: Port numbers, cert paths, protocol in code
```

### Input Validation Verification
```
Check: All endpoints validate input
Check: Validation libraries used (not regex)
Check: No raw user input in sensitive operations
Evidence: Function calls, import statements, parameter checks
```

### Authentication Verification
```
Check: All protected endpoints require auth
Check: Token/session validation present
Check: No auth bypass mechanisms
Evidence: Middleware, decorators, before_request hooks
```

### Parameterized Queries Verification
```
Check: No string concatenation in SQL
Check: Using ORM or parameterized queries
Check: All database operations covered
Evidence: Query syntax, library usage, no f-strings in SQL
```

## Limitations

**This is code-level verification, not runtime testing:**
- You verify code SAYS it does something
- You don't execute tests or run the application
- You can't verify runtime behavior
- You analyze static code only

**Example:**
- ✅ Can verify: TLS configured in redis.conf
- ❌ Cannot verify: TLS handshake actually works at runtime
- ✅ Can verify: Input validation function is called
- ❌ Cannot verify: Validation regex is bulletproof

## Remember

- **You verify claims, not discover issues** - Focus on what the issue/PR claims to implement
- **Evidence-based analysis** - Point to specific files, lines, configurations
- **Be honest about limitations** - If you can't verify something statically, say so
- **Update test status** - Record your findings so they're tracked in IriusRisk
- **Generate clear reports** - Security teams need actionable verification results

---

Use this skill when reviewing PRs that claim to implement security controls, enabling fast, automated verification of control implementation before human security review.
