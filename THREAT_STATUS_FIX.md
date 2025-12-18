# Threat Status Fix: Adding 'not-applicable' Support

## Issue Summary

The CLI was missing support for the `not-applicable` threat state, which exists in the IriusRisk core API. This caused confusion when AI assistants or users tried to mark threats as not applicable - the system would either reject the status or incorrectly fall back to `accept`.

**Critical Distinction:**
- `not-applicable`: The threat doesn't apply to this system/architecture
- `accept`: The threat IS real but we're accepting the risk

These are NOT synonymous and have completely different security implications!

## Root Cause

The IriusRisk core code (`ThreatStateEnum.java`) defines 6 valid threat states:
```java
EXPOSE("expose"),
ACCEPT("accept"),
PARTLYMITIGATE("partly-mitigate"),
MITIGATE("mitigate"),
NA("not-applicable"),  // ← This was missing in CLI!
HIDDEN("hidden");
```

But the CLI implementation only supported 5 states, missing `not-applicable`.

## Files Changed

### 1. **src/iriusrisk_cli/commands/threats.py** (Line 268)
Added `'not-applicable'` to the CLI command choices for threat status updates.

### 2. **src/iriusrisk_cli/mcp/tools/stdio_tools.py** (Line 533)
Updated MCP tool docstring to include `not-applicable` in status documentation.

### 3. **src/iriusrisk_cli/mcp/tools/http_tools.py** (Lines 791, 1047)
Updated MCP HTTP tool docstrings to include `not-applicable` in status documentation.

### 4. **tests/utils/assertions.py** (Line 185)
Updated test assertions to include `not-applicable` as a valid threat state.

### 5. **tests/api/test_api_contract_validation.py** (Line 230)
Updated API contract validation to expect `not-applicable` as a valid threat state.

### 6. **tests/integration/test_business_logic_validation.py** (Line 218)
Updated business logic tests to validate `not-applicable` status transitions.

### 7. **src/iriusrisk_cli/prompts/threats_and_countermeasures.md**
Added comprehensive documentation explaining:
- What each threat status means semantically
- The critical difference between `not-applicable` vs `accept`
- When to use each status
- Examples of proper usage

### 8. **src/iriusrisk_cli/api/threat_client.py** (Line 47)
Added comment explaining why default filter excludes `accept` and `not-applicable` states
(to focus on actionable threats).

## Threat Status Semantics (For AI and Users)

### `not-applicable` 
**Meaning:** This threat doesn't exist in our architecture  
**When to use:** The threat is irrelevant for technical/architectural reasons  
**Example:** "SQL injection" when you don't use SQL databases

### `accept`
**Meaning:** This threat IS real, but we're accepting the risk  
**When to use:** After risk analysis, decided to live with the risk  
**Example:** Accepting a low-severity threat after cost/benefit analysis  
**Requires:** Justification and detailed comment

### Other States
- `expose`: Threat is exposed and needs attention (default)
- `mitigate`: Implementing countermeasures
- `partly-mitigate`: Partially mitigated
- `hidden`: Hidden from standard views but tracked

## Testing

All tests pass with the new changes:
- ✅ CLI threat command tests (7 tests)
- ✅ Business logic validation tests (2 tests)
- ✅ API contract validation tests (12 tests)

## Impact

**Before:** AI assistants trying to mark threats as not applicable would either get an error or incorrectly mark them as `accept`, leading to incorrect risk assessments.

**After:** Full support for `not-applicable` status with clear documentation about when to use it vs `accept`.

## Related Documentation

See `src/iriusrisk_cli/prompts/threats_and_countermeasures.md` for the full AI assistant guidance on threat status usage.

