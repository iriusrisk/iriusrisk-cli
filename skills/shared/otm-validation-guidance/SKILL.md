---
name: otm-validation-guidance
description: Detailed validation rules for OTM files. Use when validating trust zone IDs, component types, and filtering deprecated components. Critical for preventing import failures.
---

# OTM Validation Guidance

## When to Use This Skill

Call this skill when you need detailed guidance on:
- Validating trust zone IDs from trust-zones.json
- Validating component types from components.json
- Filtering deprecated components
- Understanding validation requirements

**This skill provides detailed validation instructions and examples.**

## Critical Validation Rules

### Trust Zone IDs - Must Use UUIDs from trust-zones.json

**ABSOLUTE RULE:** EVERY trust zone ID MUST come from `.iriusrisk/trust-zones.json`

**Process:**
1. Open `.iriusrisk/trust-zones.json` (downloaded by sync())
2. Search for the zone you need by reading `name` field
3. Copy the COMPLETE `id` field value (UUID format)
4. Use that exact UUID in your OTM

**Example from trust-zones.json:**
```json
{
  "id": "b61d6911-338d-46a8-9f39-8dcd24abfe91",
  "referenceId": "public-cloud",
  "name": "Public Cloud",
  "risk": {"trustRating": 60}
}
```

**In your OTM:**
```yaml
trustZones:
  - id: "b61d6911-338d-46a8-9f39-8dcd24abfe91"  # ✅ UUID from file
    name: "Public Cloud"
    risk: {trustRating: 60}

components:
  - id: "my-service"
    parent:
      trustZone: "b61d6911-338d-46a8-9f39-8dcd24abfe91"  # ✅ UUID
```

**WRONG:**
```yaml
trustZones:
  - id: "public-cloud"  # ❌ referenceId, not id
  - id: "internet-tz"  # ❌ Invented
  - id: "application"   # ❌ Descriptive name, not UUID
```

### Component Types - Must Use Complete referenceId from components.json

**ABSOLUTE RULE:** EVERY component type MUST be the COMPLETE `referenceId` from `.iriusrisk/components.json`

**Process:**
1. Open `.iriusrisk/components.json` (downloaded by sync())
2. Search for keywords (e.g., "ECS", "database", "Flask")
3. **Filter out deprecated:**
   - Skip if `category.name == "Deprecated"`
   - Skip if `name` starts with "Deprecated - "
4. Find the matching ACTIVE component
5. Copy the COMPLETE `referenceId` field (do NOT abbreviate)
6. Use that exact referenceId in your OTM

**Example from components.json:**
```json
{
  "name": "AWS ECS Cluster",
  "referenceId": "CD-V2-AWS-ECS-CLUSTER",
  "category": {"name": "Container Orchestration"}
}
```

**In your OTM:**
```yaml
components:
  - id: "my-cluster"
    type: "CD-V2-AWS-ECS-CLUSTER"  # ✅ Complete referenceId
```

**WRONG:**
```yaml
components:
  - id: "my-cluster"
    type: "CD-AWS-ECS"  # ❌ Abbreviated
    type: "ecs-cluster"  # ❌ Descriptive name
    type: "CD-V2-ECS"    # ❌ Missing -AWS-
    type: "CD-V2-AWS-ECS"  # ❌ Missing -CLUSTER
```

### Filtering Deprecated Components

**~40% of components are deprecated - you MUST filter them out:**

```python
# When searching components.json:
for component in components:
    # Skip deprecated
    if component['category']['name'] == 'Deprecated':
        continue
    if component['name'].startswith('Deprecated - '):
        continue
    
    # This is an active component - safe to use
    referenceId = component['referenceId']
```

**Example deprecated component:**
```json
{
  "name": "Deprecated - Azure Web Apps",
  "referenceId": "microsoft-azure-web-apps",
  "category": {"name": "Deprecated"}
}
```

**Use the active version instead:**
```json
{
  "name": "Azure Web Apps",
  "referenceId": "CD-V2-AZURE-WEB-APPS",
  "category": {"name": "Microsoft Azure"}
}
```

## Validation Checklist

**Before creating OTM, verify:**

**Trust Zones:**
- ☐ Opened trust-zones.json
- ☐ For EACH trust zone: Found exact UUID in file
- ☐ Copied complete `id` field (not `referenceId` or `name`)
- ☐ Did NOT invent any trust zone IDs

**Component Types:**
- ☐ Opened components.json
- ☐ For EACH component: Searched for matching type
- ☐ Filtered out deprecated components
- ☐ Copied COMPLETE `referenceId` (not abbreviated)
- ☐ Did NOT invent any component types

**Structure:**
- ☐ Every component has a parent (trustZone or component)
- ☐ Every dataflow source/destination exists in components list
- ☐ No dataflows use trust zone IDs (only component IDs)

## Common Mistakes

**Mistake 1: Using referenceId instead of id for trust zones**
```yaml
# ❌ WRONG
trustZone: "public-cloud"  # This is referenceId

# ✅ CORRECT
trustZone: "b61d6911-338d-46a8-9f39-8dcd24abfe91"  # This is id
```

**Mistake 2: Abbreviating component types**
```yaml
# ❌ WRONG
type: "CD-AWS-ECS"  # Abbreviated

# ✅ CORRECT
type: "CD-V2-AWS-ECS-CLUSTER"  # Complete referenceId
```

**Mistake 3: Using deprecated components**
```yaml
# ❌ WRONG
type: "microsoft-azure-web-apps"  # Deprecated

# ✅ CORRECT
type: "CD-V2-AZURE-WEB-APPS"  # Active version
```

**Mistake 4: Inventing IDs**
```yaml
# ❌ WRONG - Invented IDs
trustZone: "internet-tz"
trustZone: "application-layer"
type: "flask-api"
type: "postgres-db"

# ✅ CORRECT - From actual files
trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"
type: "CD-V2-PYTHON-FLASK"
type: "CD-V2-POSTGRESQL-DATABASE"
```

## How to Search the Files

**Trust zones - search by name:**
```python
# Look for "Internet" zone
grep -i "internet" .iriusrisk/trust-zones.json
# Find the entry, copy the "id" field (UUID)
```

**Components - search by keywords:**
```python
# Look for Flask component
grep -i "flask" .iriusrisk/components.json
# Find active (non-deprecated) entry
# Copy the complete "referenceId" field
```

## Validation is Mandatory

The backend validates OTM files against JSON schema before import. But schema validation does NOT check:
- Whether trust zone UUIDs exist in trust-zones.json
- Whether component types exist in components.json
- Whether components are deprecated

**You MUST do this validation yourself before creating the OTM.**
