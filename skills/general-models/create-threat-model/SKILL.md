---
name: create-threat-model
description: Step-by-step instructions for creating IriusRisk threat models (OTM files). Use when creating or updating threat models. Covers validation, component mapping, trust zones, and complete workflow from analysis to import.
---

# IriusRisk Threat Model Creation Instructions

## 🚨 CRITICAL VALIDATION RULES - READ FIRST

**Before creating ANY OTM file, you MUST:**

1. **Open and read `.iriusrisk/trust-zones.json`**
   - EVERY trust zone ID you use MUST be a UUID from this file's `id` field
   - Example: `"id": "b61d6911-338d-46a8-9f39-8dcd24abfe91"` (NOT "internet" or "public-cloud")
   - DO NOT invent trust zone IDs

2. **Open and read `.iriusrisk/components.json`**
   - EVERY component type you use MUST be a complete `referenceId` from this file
   - Filter out deprecated: skip if `category.name == "Deprecated"` or `name` starts with "Deprecated - "
   - Example: `"CD-V2-AWS-ECS-CLUSTER"` (NOT "CD-AWS-ECS" or "ecs-cluster")
   - DO NOT abbreviate or invent component types

3. **Validate EVERY component and trust zone before creating OTM**
   - Search components.json for each component type
   - Search trust-zones.json for each trust zone ID
   - If not found: use generic type or ask user

**These files are downloaded by sync() - you MUST read them before creating OTM.**

## 🚨 MANDATORY: ALWAYS sync() BEFORE MODIFYING THE THREAT MODEL

**The local `current-threat-model.otm` file may be STALE.** Users can modify the threat model via the IriusRisk web interface at any time (moving components, changing layout, adding/removing elements). A local OTM file only reflects the state at the time of the last sync — it does NOT automatically update.

**RULE: You MUST call sync() before every modification, even if `current-threat-model.otm` already exists locally.** Never assume the local file is current. The only safe source of truth is a fresh sync from IriusRisk.

**The ONLY exception:** If you JUST called sync() moments ago in the same operation (e.g., you synced, then immediately create the OTM in the same workflow). Even then, if there is any doubt, sync again.

## Executive Summary

Create OTM files to model system architecture for IriusRisk threat analysis. Your role: architecture modeling only (components, trust zones, data flows). Do NOT create threats or controls—IriusRisk generates those automatically.

**Standard workflow:** 
1. **sync()** - MANDATORY FIRST STEP. Downloads trust-zones.json, components.json, current-threat-model.otm. **Do this even if local files already exist — they may be stale.**
2. **READ trust-zones.json and components.json** - Validate IDs/types exist
3. Check `.iriusrisk/current-threat-model.otm` - Merge if exists (now guaranteed fresh from step 1)
4. Create OTM in `.iriusrisk/temp-*.otm` with validated IDs/types
5. import_otm() → project_status() → **STOP**

## Quick Reference

**File locations:**
- Save OTM to: `.iriusrisk/temp-initial.otm` or `.iriusrisk/temp-update-YYYYMMDD-HHMMSS.otm`
- Read current state from: `.iriusrisk/current-threat-model.otm` (after a fresh sync — NEVER trust a pre-existing local copy)

**Workflow:**
1. **sync() ALWAYS** (even if local files exist) → 2. Read validation files → 3. Create/merge OTM → 4. import_otm()

**Dataflows:** Connect components ONLY (never trust zones)

## Merge Logic - Single-Repo and Multi-Repo Are IDENTICAL

**Whether updating from same repo or different repo, the workflow is IDENTICAL:**
1. **sync() FIRST** — downloads fresh `.iriusrisk/current-threat-model.otm` from IriusRisk. **Do NOT skip this step even if the file already exists locally** — the user may have modified the model via the web interface since the last sync, and using a stale file will lose their changes (layout, new components, etc.)
2. If exists: READ it, preserve ALL components/IDs/layout, add NEW components
3. If not: CREATE initial model
4. Save to `.iriusrisk/temp-*.otm`

**For detailed layout guidance:** Call `otm_layout_guidance()` MCP tool
**For detailed validation guidance:** Call `otm_validation_guidance()` MCP tool

## Common Errors to Avoid

**Error 1: Dataflows use trust zone IDs**
- ❌ WRONG: `source: "internet"` (trust zone)
- ✅ CORRECT: `source: "mobile-app"` (component)
- Rule: Dataflows connect components ONLY

**Error 2: Abbreviated component types**
- ❌ WRONG: `type: "CD-AWS-ECS"` (abbreviated)
- ✅ CORRECT: `type: "CD-V2-AWS-ECS-CLUSTER"` (complete referenceId)
- Rule: Use COMPLETE referenceId from components.json

**Error 3: Using deprecated components**
- Filter out: `category.name == "Deprecated"` or `name` starts with "Deprecated - "
- ~40% of components are deprecated

**Error 4: Changing project.id**
- ❌ NEVER change project.id when updating
- ✅ ALWAYS preserve exact project.id from existing OTM or project.json reference_id

**Error 5: Skipping sync() when local OTM file already exists**
- ❌ WRONG: Seeing `current-threat-model.otm` locally and using it without syncing first
- ✅ CORRECT: ALWAYS run sync() before reading or modifying the threat model
- The user may have changed layout, added components, or modified the model via the IriusRisk web interface since the last sync. Using a stale file overwrites their changes.

## Your Role: Architecture Modeling Only

**Do:**
- Extract components from source code, infrastructure, documentation
- Map components to IriusRisk types using exact referenceId values
- Define trust zones and component relationships
- Create data flows between components

**Do NOT:**
- Identify threats, vulnerabilities, or security flaws
- Create mitigations, controls, or countermeasures
- Add threats/mitigations sections to OTM file
- Analyze code for security issues

**Why:** IriusRisk automatically generates all threats and controls after OTM import.

## Tags - Architecture ONLY

**Tags describe WHAT components ARE, not WHAT'S WRONG with them.**

**Good tags:** `payment-processing`, `pci-dss-scope`, `public-facing`, `customer-data`
**Bad tags:** `sql-injection-vulnerable`, `weak-crypto`, `no-validation`

IriusRisk finds vulnerabilities automatically - don't add them as tags.

## Required Workflow Checklist

**🚨 VALIDATION RULE - READ THIS FIRST:**
- **EVERY component type** you use MUST exist in `.iriusrisk/components.json` - Open the file and verify!
- **EVERY trust zone ID** you use MUST exist in `.iriusrisk/trust-zones.json` - Open the file and verify!
- **DO NOT invent components or trust zones** - If you can't find an exact match, use a generic type or ask

**Complete steps 0-8, then STOP and wait for user.** Step 9 only when user explicitly requests.

- ☐ Step 0: **sync(project_path)** - 🚨 MANDATORY FIRST STEP — NO EXCEPTIONS
  - Downloads components.json, trust-zones.json
  - Downloads current-threat-model.otm if project exists
  - **⚠️ You MUST run sync() even if local files already exist** — the user may have changed the model in the IriusRisk web interface. A pre-existing local `current-threat-model.otm` is NOT guaranteed to be current. Only a fresh sync is reliable.
  
- ☐ Step 1: **CHECK `.iriusrisk/current-threat-model.otm`** (freshly downloaded by sync in Step 0)
  - **If exists**: MERGE mode - read entire file, preserve everything (layout, components, IDs)
  - **If missing**: CREATE mode - but still check project.json
  
- ☐ Step 2: Analyze source material
  - Identify NEW components to add from THIS repository
  - If MERGE mode: Focus on what's NEW (don't duplicate existing)
  
- ☐ Step 3: Check `.iriusrisk/project.json` - Read project name/ID/scope
  
- ☐ Step 4: Create OTM file with VALIDATED IDs and types
  - **🚨 CRITICAL: Use validated trust zone UUIDs from trust-zones.json**
  - **🚨 CRITICAL: Use validated component referenceIds from components.json**
  - **MERGE mode**: Preserve ALL existing components, IDs, and layout; add NEW components
  - **CREATE mode**: All components from analysis with simple layout
  - **Save to**: `.iriusrisk/temp-update-YYYYMMDD-HHMMSS.otm` (or temp-initial.otm)
  
- ☐ Step 5: Validate components - Use exact referenceId from components.json
  
- ☐ Step 6: **import_otm(".iriusrisk/temp-update-*.otm")** - Upload temporary file
  - Backend automatically validates against OTM JSON schema
  
- ☐ Step 7: **project_status()** - Verify project ready
  
- ☐ Step 8: Present results - Offer options - **STOP HERE and wait for user**
  
- ☐ Step 9: **sync()** again - **ONLY if user explicitly requests** - Download updated threats/countermeasures

**🚨 REMEMBER: If user said "threat model [X]", you are doing architecture modeling. DO NOT call threats_and_countermeasures() or analyze threats.json.**

## CRITICAL: Trust Zone Setup

**⚠️ MANDATORY: Read `.iriusrisk/trust-zones.json` file FIRST**

**🚨 ABSOLUTE RULE: EVERY trust zone ID you use MUST exist in `.iriusrisk/trust-zones.json`. If it's not in that file, you CANNOT use it.**

Before creating your OTM file, you MUST:
1. **Open and read** `.iriusrisk/trust-zones.json` (created by sync() in Step 0)
2. **Identify which trust zones you need** from the available zones in the file
3. **Copy the EXACT `id` field values** from trust-zones.json (these are UUIDs)
4. **Verify each trust zone ID** before using it in your OTM

**DO NOT:**
- Invent trust zone names or IDs (e.g., "internet", "dmz", "application" - these are NOT IDs)
- Use descriptive names instead of actual UUID IDs
- Create new trust zones not in trust-zones.json
- Use trust zone names as IDs (use the UUID from the `id` field, not the `name` field)

## Parent Relationship Rules

**⚠️ CRITICAL: Every component MUST have a parent - either a trust zone ID or a component ID.**

**Simple principle:** A component's parent represents WHERE it physically resides or executes.

**Use `parent: { trustZone: "zone-id" }` when:**
- The component is standalone infrastructure (VPCs, networks, databases, storage)
- The component is externally hosted (third-party APIs, SaaS services)
- **IMPORTANT:** Use exact trust zone ID from trust-zones.json

**Use `parent: { component: "component-id" }` when:**
- The component runs inside another component
- Examples: Application runs in VM, Service runs in container
- **IMPORTANT:** The parent component must be defined before (above) this component in the OTM file

## Complete Example

**IMPORTANT:** This example uses placeholder trust zone IDs. In reality, you MUST read `.iriusrisk/trust-zones.json` and use the actual IDs from that file.

```yaml
otmVersion: 0.1.0
project:
  name: "[from project.json 'name' field or descriptive name]"
  id: "[from project.json 'reference_id' field or generate unique ID]"
  description: "[brief system description]"

trustZones:
  # ⚠️ These IDs are examples - read trust-zones.json for actual IDs
  - id: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Example: actual ID from trust-zones.json
    name: "Internet"
    risk:
      trustRating: 1

components:
  # External client - in internet zone
  - id: "web-browser"
    name: "Web Browser"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Internet zone ID from trust-zones.json

dataflows:
  # ⚠️⚠️⚠️ CRITICAL: Dataflows ONLY connect components (never trust zones) ⚠️⚠️⚠️
  - id: "user-request"
    source: "web-browser"      # component ID ✅
    destination: "alb"          # component ID ✅

# Do NOT add: threats, mitigations, controls (IriusRisk generates these)
```

## Final Validation Checklist

**🚨 MANDATORY PRE-FLIGHT VALIDATION - DO NOT SKIP:**

**Component Type Validation (MOST COMMON FAILURE):**
- ☐ **Opened and read `.iriusrisk/components.json`**
- ☐ **Filtered out deprecated components** (category.name !== "Deprecated" AND name does NOT start with "Deprecated - ")
- ☐ **For EVERY component in OTM: Searched components.json for ACTIVE (non-deprecated) type**
- ☐ **For EVERY component in OTM: Verified COMPLETE referenceId exists** (not abbreviated, not invented)

**Trust Zone Validation (SECOND MOST COMMON FAILURE):**
- ☐ **Opened and read `.iriusrisk/trust-zones.json`**
- ☐ **For EVERY trust zone in OTM: Verified exact UUID ID exists in trust-zones.json**
- ☐ **Used UUID IDs from `id` field** (not descriptive names from `name` field)
- ☐ **Did NOT invent trust zone IDs** (every ID came from the file)

**Remember:**
- **TOP ERRORS TO AVOID (IN ORDER OF FREQUENCY):**
  1. **Using deprecated components** (~40% are deprecated!)
  2. **Inventing component types** - EVERY type MUST exist in components.json
  3. **Inventing trust zone IDs** - EVERY ID MUST exist in trust-zones.json
  4. **Abbreviating component referenceIds** - Use COMPLETE string
  5. **Components without parents** - Every component MUST have trustZone or component parent
  6. **Using trust zone IDs in dataflows** - Dataflows connect components only

**Validation is not optional - it is THE MOST CRITICAL step. 80% of OTM import failures are due to:**
1. **Using deprecated components** (40% of components are deprecated - MUST filter them out)
2. **Invented/invalid component types or trust zone IDs**
