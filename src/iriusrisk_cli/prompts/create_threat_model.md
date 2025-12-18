# IriusRisk Threat Model Creation Instructions for AI Assistants

## Executive Summary
Create OTM files to model system architecture for IriusRisk threat analysis. Your role: architecture modeling only (components, trust zones, data flows). Do NOT create threats or controls—IriusRisk generates those automatically. 

**Standard workflow:** sync() first → create OTM → import_otm() → project_status() → **STOP and ask user what to do next**.

**Do NOT automatically download threats/countermeasures** - IriusRisk needs time to process the threat model. Only download if user explicitly requests it.

**⚠️ CRITICAL: Dataflows ONLY connect components to components. NEVER use trust zone IDs in dataflows - this causes import failure.**

## Critical Error #1: Dataflows Connect Components, NOT Trust Zones

**Most common OTM import failure:** Using trust zone IDs in dataflows instead of component IDs.

```yaml
# ✅ CORRECT - Component to Component:
dataflows:
  - id: "user-to-app"
    name: "User to Application"  # REQUIRED field
    source: "mobile-app"      # component ID
    destination: "web-server" # component ID

# ❌ WRONG - Trust Zone IDs (CAUSES IMPORT FAILURE):
dataflows:
  - id: "bad-flow"
    name: "Bad Flow"
    source: "internet"        # trust zone ID - FAILS!
    destination: "dmz"        # trust zone ID - FAILS!
```

**Rule:** Trust zones CONTAIN components. Dataflows CONNECT components directly.

## Critical Error #2: Component Types Must Use COMPLETE, EXACT referenceId

**Most common component mapping failure:** Abbreviating or truncating the referenceId instead of using the complete string.

```yaml
# ✅ CORRECT - Complete referenceId from components.json:
type: "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL"  # Full string, even though long

# ❌ WRONG - Abbreviated (common mistake):
type: "CD-V2-AWS-WAF"  # Missing "-WEB-APPLICATION-FIREWALL" - FAILS

# ❌ WRONG - Simplified:
type: "aws-ecs"  # Way too short - FAILS

# ❌ WRONG - Partially truncated:
type: "CD-V2-AWS-ECS"  # Missing "-CLUSTER" - FAILS
```

**Rule:** Read `.iriusrisk/components.json`, find the `referenceId` field, **copy the ENTIRE string without modification**. Do not abbreviate, even if it looks redundant.

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
- Run CLI commands like `iriusrisk component search`

**Why:** IriusRisk automatically generates all threats and controls after OTM import.

## Required Workflow Checklist

**Complete steps 0-7, then STOP and wait for user.** Step 8 only when user explicitly requests.

- ☐ Step 0: **sync(project_path)** - Download components & trust zones
- ☐ Step 1: Analyze source material - Identify architectural components
- ☐ Step 2: Check `.iriusrisk/project.json` - Read project name/reference_id if exists
- ☐ Step 3: Create OTM file - ONLY components, trust zones, dataflows (dataflows connect components ONLY)
- ☐ Step 4: Map components - Use exact referenceId from components.json
- ☐ Step 5: **import_otm()** - Upload OTM to IriusRisk
- ☐ Step 6: **project_status()** - Verify project ready
- ☐ Step 7: Present results - Offer options - **STOP HERE and wait for user**
- ☐ Step 8: **sync()** again - **ONLY if user explicitly requests** - Download threats/countermeasures

## Detailed Workflow

### Step 0: sync(project_path) - Download Component Library AND Trust Zones

**Mandatory first step.** Call sync() with full absolute project path (e.g., `sync("/Users/username/my-project")`).

**What it does:**
- Downloads complete IriusRisk component library to `.iriusrisk/components.json`
- Downloads trust zones to `.iriusrisk/trust-zones.json` ⚠️ CRITICAL
- If project exists, also downloads current threats/countermeasures
- Prevents OTM import failures due to unknown component types or trust zones

**⚠️ CRITICAL:** You MUST read `.iriusrisk/trust-zones.json` to get valid trust zone IDs. Do NOT invent trust zone names or IDs - use only the exact IDs from this file.

### Step 1-2: Analyze Source & Check Configuration

**Analyze source material:**
- Identify infrastructure (VMs, containers, databases, load balancers)
- Identify business logic (auth services, payment processing, user management)
- Identify data components (databases, storage, queues, caches)
- Identify external systems (third-party APIs, services)
- Plan nesting (business logic runs within infrastructure)
- Identify data flows between components
- **Do NOT identify threats or security issues**

**Check for existing project:**
- Look for `.iriusrisk/project.json`
- If exists, use `name` and `reference_id` from that file
- **CRITICAL:** Use `reference_id` (NOT `project_id`) - this is the human-readable ID that goes in the OTM file
- If not exists, create descriptive names from source material

### Step 3: Create OTM File

**Use project.json if exists:** Read `.iriusrisk/project.json` and use `name` and `reference_id` from that file. 
**IMPORTANT:** The `reference_id` field from project.json becomes the `project.id` field in the OTM file. 
The `project_id` (UUID) field should NOT be used in OTM files - that's the internal IriusRisk UUID.
Otherwise, create descriptive names.

## CRITICAL: Trust Zone Setup

**⚠️ MANDATORY: Read `.iriusrisk/trust-zones.json` file FIRST**

Before creating your OTM file, you MUST:
1. Read `.iriusrisk/trust-zones.json` (created by sync() in Step 0)
2. Identify which trust zones you need from the available zones
3. Use the EXACT `id` field values from trust-zones.json in your OTM

**DO NOT:**
- Invent trust zone names or IDs
- Use descriptive names instead of actual IDs
- Create new trust zones not in trust-zones.json

**Trust zones in OTM file:**
```yaml
trustZones:
  # Copy trust zones you need from trust-zones.json
  # Use EXACT id values from that file
  - id: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Example: actual UUID from trust-zones.json
    name: "Internet"  # Can use descriptive name
    risk:
      trustRating: 1  # Use trustRating from trust-zones.json
```

**Example trust-zones.json structure:**
```json
[
  {
    "id": "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c",
    "name": "Internet",
    "risk": {
      "trustRating": 1
    }
  },
  {
    "id": "f0ba7722-39b6-4c81-8290-a30a248bb8d9",
    "name": "Public Cloud",
    "risk": {
      "trustRating": 5
    }
  }
]
```

## Parent Relationship Rules

**⚠️ CRITICAL: Every component MUST have a parent - either a trust zone ID or a component ID. Components cannot exist without a parent.**

**Simple principle:** A component's parent represents WHERE it physically resides or executes.

**Use `parent: { trustZone: "zone-id" }` when:**
- The component is standalone infrastructure (VPCs, networks, databases, storage)
- The component is externally hosted (third-party APIs, SaaS services)
- The component has no containing infrastructure in your model
- **IMPORTANT:** Use exact trust zone ID from trust-zones.json

**Use `parent: { component: "component-id" }` when:**
- The component runs inside another component
- Examples: Application runs in VM, Service runs in container, Function runs in serverless platform
- **IMPORTANT:** The parent component must be defined before (above) this component in the OTM file

**Common patterns:**
- Network infrastructure → trust zone parent (use ID from trust-zones.json)
- Compute infrastructure (VM, container platform) → trust zone parent (use ID from trust-zones.json)
- Applications/services running on compute → component parent (the compute hosting it)
- Databases/storage → trust zone parent (use ID from trust-zones.json)
- External/third-party services → trust zone parent (typically an "internet" or "external" zone ID from trust-zones.json)

**⚠️ REMEMBER: Trust zones define LOCATION. Components define THINGS. Dataflows connect THINGS (components), not locations (trust zones).**

## Optional Fields Reference

### Component Optional Fields

Components can include these optional fields for better documentation and organization:

```yaml
components:
  - id: "my-service"              # REQUIRED
    name: "My Service"            # REQUIRED
    type: "CD-V2-WEB-SERVICE"     # REQUIRED (exact referenceId)
    parent:                       # REQUIRED (trustZone or component)
      trustZone: "zone-id"
    description: "Detailed description of what this component does"  # OPTIONAL
    tags: ["api", "python", "rest"]  # OPTIONAL: helps categorize and search
```

### Dataflow Required and Optional Fields

Dataflows have both required and optional fields:

```yaml
dataflows:
  - id: "api-call"                    # REQUIRED: unique identifier
    name: "API Request"               # REQUIRED: descriptive name (this was causing your error!)
    source: "client"                  # REQUIRED: component ID
    destination: "server"             # REQUIRED: component ID
    tags: ["http", "rest", "public"]  # OPTIONAL: categorization tags
    bidirectional: false              # OPTIONAL: true for two-way communication (default: false)
```

### Trust Zone Optional Fields

Trust zones can include these fields:

```yaml
trustZones:
  - id: "uuid-from-trust-zones-json"  # REQUIRED: exact ID from trust-zones.json
    name: "Internet"                  # REQUIRED: descriptive name
    type: "uuid-from-trust-zones-json"  # OPTIONAL: often same as id
    risk:
      trustRating: 1                  # REQUIRED: 1 (untrusted) to 100 (fully trusted)
```

**Note:** The `representations` section (for diagram positioning) is typically added by IriusRisk and not required in your OTM files.

## Complete Example

**IMPORTANT:** This example uses placeholder trust zone IDs. In reality, you MUST read `.iriusrisk/trust-zones.json` and use the actual IDs from that file.

```yaml
otmVersion: 0.1.0
project:
  name: "[from project.json 'name' field or create descriptive name]"
  id: "[from project.json 'reference_id' field or generate unique ID like 'my-app-x7k2']"
  description: "[brief system description]"

trustZones:
  # ⚠️ These IDs are examples - read trust-zones.json for actual IDs
  # Copy the trust zones you need from trust-zones.json
  - id: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Example: actual ID from trust-zones.json
    name: "Internet"
    risk:
      trustRating: 1
  - id: "2ab4effa-40b4-45de-ba93-9e4c3d4db85a"  # Example: actual ID from trust-zones.json
    name: "Public Cloud"
    risk:
      trustRating: 3
  - id: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # Example: actual ID from trust-zones.json
    name: "Private Secured"
    risk:
      trustRating: 10

components:
  # External client - in internet zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "web-browser"
    name: "Web Browser"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Internet zone ID from trust-zones.json
    tags: ["client", "browser"]  # Optional tags for categorization
  
  # Load balancer - standalone in public cloud zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "alb"
    name: "Application Load Balancer"
    type: "[exact referenceId from components.json]"
    description: "AWS ALB distributing traffic to ECS containers"  # Optional description
    parent:
      trustZone: "2ab4effa-40b4-45de-ba93-9e4c3d4db85a"  # Public Cloud zone ID from trust-zones.json
    tags: ["load-balancer", "public-facing"]
  
  # Container platform - standalone in public cloud zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "ecs-cluster"
    name: "ECS Cluster"
    type: "[exact referenceId from components.json]"
    description: "Container orchestration platform"
    parent:
      trustZone: "2ab4effa-40b4-45de-ba93-9e4c3d4db85a"  # Public Cloud zone ID from trust-zones.json
    tags: ["compute", "container-orchestration"]
  
  # Application services - run inside container platform
  - id: "auth-service"
    name: "Authentication Service"
    type: "[exact referenceId from components.json]"
    description: "Handles user authentication and session management"
    parent:
      component: "ecs-cluster"  # runs in ECS
    tags: ["authentication", "api", "internal-service"]
  
  - id: "api-service"
    name: "API Service"
    type: "[exact referenceId from components.json]"
    description: "Main API endpoints for application functionality"
    parent:
      component: "ecs-cluster"  # runs in ECS
    tags: ["api", "rest", "internal-service"]
  
  # Database - standalone in private secured zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "user-db"
    name: "User Database"
    type: "[exact referenceId from components.json]"
    description: "PostgreSQL database storing user data and application state"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # Private Secured zone ID from trust-zones.json
    tags: ["database", "postgresql", "user-data"]
  
  # External API - in internet zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "payment-api"
    name: "Payment Processor API"
    type: "[exact referenceId from components.json]"
    description: "Third-party payment processing service"
    parent:
      trustZone: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Internet zone ID from trust-zones.json
    tags: ["external-api", "payment", "third-party"]

dataflows:
  # ⚠️⚠️⚠️ CRITICAL: Dataflows ONLY connect components (never trust zones) ⚠️⚠️⚠️
  # Use component IDs like "web-browser", "alb", "api-service" (defined above)
  # NEVER use trust zone IDs like "internet", "dmz", "application" in dataflows
  
  - id: "user-request"
    name: "User HTTP Requests"     # REQUIRED: Descriptive name
    source: "web-browser"           # component ID ✅
    destination: "alb"              # component ID ✅
    tags: ["http", "user-traffic"] # Optional: categorization tags
  
  - id: "alb-to-api"
    name: "Load Balanced Traffic"
    source: "alb"               # component ID ✅
    destination: "api-service"  # component ID ✅
    tags: ["internal-routing"]  # Optional tags
  
  - id: "api-to-auth"
    name: "Authentication Requests"
    source: "api-service"       # component ID ✅
    destination: "auth-service" # component ID ✅
    tags: ["authentication", "internal-service"]
  
  - id: "auth-to-db"
    name: "Database Queries"
    source: "auth-service"      # component ID ✅
    destination: "user-db"      # component ID ✅
    tags: ["database-access", "sql"]
    bidirectional: false        # Optional: set to true for two-way communication
  
  - id: "api-to-payment"
    name: "Payment API Calls"
    source: "api-service"       # component ID ✅
    destination: "payment-api"  # component ID ✅
    tags: ["external-integration", "payment"]

# Do NOT add: threats, mitigations, controls (IriusRisk generates these)
```

## Invalid Examples - Common Mistakes

```yaml
# ❌ WRONG #1: Inventing trust zone IDs instead of using trust-zones.json
# This causes "not existing TrustZone" errors
components:
  - id: "my-cluster"
    parent:
      trustZone: "application"  # ❌ Made-up name - FAILS
  - id: "my-db"
    parent:
      trustZone: "secure-zone"  # ❌ Invented ID - FAILS

# ✅ CORRECT: Read trust-zones.json and use actual IDs
components:
  - id: "my-cluster"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # ✅ Real ID from trust-zones.json
  - id: "my-db"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # ✅ Real ID from trust-zones.json

# ❌ WRONG #2: Referencing non-existent component in parent
# This causes import failures
components:
  - id: "my-service"
    parent:
      component: "my-container-platform"  # ❌ This component doesn't exist!

# ✅ CORRECT: Parent component must be defined first (earlier in components list)
components:
  - id: "my-container-platform"
    type: "CD-V2-CONTAINER-PLATFORM"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"
  
  - id: "my-service"
    parent:
      component: "my-container-platform"  # ✅ References component defined above

# ❌ WRONG #3: Referencing non-existent component in dataflow
# This causes import failures
dataflows:
  - id: "data-flow"
    name: "Data Flow"
    source: "api-gateway"  # ❌ This component doesn't exist in components section!
    destination: "my-service"

# ✅ CORRECT: Both components must exist in components section
components:
  - id: "api-gateway"
    type: "CD-V2-API-GATEWAY"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"
  - id: "my-service"
    type: "CD-V2-WEB-SERVICE"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"

dataflows:
  - id: "data-flow"
    name: "Data Flow"  # ✅ Has required name
    source: "api-gateway"  # ✅ Exists in components above
    destination: "my-service"  # ✅ Exists in components above

# ❌ WRONG #4: Component with no parent
- id: "my-service"
  name: "My Service"
  type: "CD-V2-WEB-SERVICE"
  # ❌ Missing parent! Every component MUST have a parent

# ✅ CORRECT: Every component has a parent
- id: "my-service"
  name: "My Service"
  type: "CD-V2-WEB-SERVICE"
  parent:
    trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # ✅ Has parent

# ❌ WRONG #5: Using trust zone IDs in dataflows (ALSO VERY COMMON)
dataflows:
  - id: "bad-flow"
    name: "Bad Flow"
    source: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # ❌ Trust zone ID - FAILS
    destination: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # ❌ Trust zone ID - FAILS

# Why wrong? Trust zones are containers/locations, not things that communicate.
# You can't send data "to a zone" - you send it to a component IN the zone.

# ❌ WRONG #6: Service nested in load balancer
# Load balancers route TO services, they don't host them
- id: "my-service"
  parent:
    component: "load-balancer"  # WRONG

# ❌ WRONG #7: Abbreviated or truncated component type
- id: "my-waf"
  type: "CD-V2-AWS-WAF"  # ❌ Truncated - missing rest of referenceId

- id: "my-db"
  type: "postgres"  # ❌ Wrong - not exact referenceId

- id: "my-cluster"
  type: "CD-V2-ECS"  # ❌ Abbreviated - not complete referenceId

# ✅ CORRECT - Use COMPLETE referenceId from components.json:
- id: "my-waf"
  type: "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL"  # ✅ Complete string

- id: "my-db"
  type: "CD-V2-POSTGRESQL-DATABASE"  # ✅ Full referenceId

- id: "my-cluster"
  type: "CD-V2-AWS-ECS-CLUSTER"  # ✅ Full referenceId

# ✅ CORRECT alternatives:
# Service runs in compute infrastructure (VM/container/serverless)
- id: "my-service"
  parent:
    component: "ecs-cluster"  # Runs in ECS

# Or if no compute infrastructure is modeled:
- id: "my-service"
  parent:
    trustZone: "application"  # Standalone in app zone

# Dataflow connects components
dataflows:
  - id: "good-flow"
    name: "Traffic Flow"  # Required name
    source: "load-balancer"  # Component ID
    destination: "my-service"  # Component ID

# Use exact referenceId from components.json
- id: "my-db"
  type: "CD-V2-POSTGRESQL-DATABASE"  # Exact referenceId
```

### Step 4: Map Components to IriusRisk Types and VALIDATE

**⚠️ MANDATORY: Open and read `.iriusrisk/components.json`** (created by sync() in Step 0). This file contains all valid component types.

**⚠️ CRITICAL: Use the COMPLETE referenceId - DO NOT abbreviate, truncate, or shorten it.**

**Mapping and Validation Process:**
1. **For each component** you identified in Step 1, open `.iriusrisk/components.json`
2. **Search the file** for keywords related to your component (e.g., "WAF", "database", "ECS", "lambda")
3. **Find the matching component entry** - look at the `name` field to confirm it matches
4. **Copy the ENTIRE `referenceId` field value** - do not modify, abbreviate, or truncate it
5. **Paste it exactly** as the `type` in your OTM component
6. **Verify** the referenceId you copied exists in components.json before using it

**Common error pattern - DO NOT DO THIS:**
```json
// In components.json you find:
{
  "name": "AWS WAF Web Application Firewall",
  "referenceId": "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL"
}
```

```yaml
# ❌ WRONG - Abbreviated/truncated:
- id: "my-waf"
  type: "CD-V2-AWS-WAF"  # FAILS - missing "-WEB-APPLICATION-FIREWALL"

# ❌ WRONG - Simplified:
- id: "my-waf"
  type: "CD-V2-WAF"  # FAILS - truncated

# ❌ WRONG - Made up based on pattern:
- id: "my-waf"
  type: "CD-V2-AWS-WAF-FIREWALL"  # FAILS - not the exact referenceId

# ✅ CORRECT - Complete referenceId copied EXACTLY from components.json:
- id: "my-waf"
  type: "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL"  # Full string from components.json
```

**More examples:**
```json
// In components.json:
{
  "name": "AWS ECS Cluster",
  "referenceId": "CD-V2-AWS-ECS-CLUSTER",
  "category": "Container Orchestration"
}
```

```yaml
# In your OTM:
- id: "my-cluster"
  type: "CD-V2-AWS-ECS-CLUSTER"  # exact referenceId ✅
  # NOT: type: "aws-ecs" ❌ (abbreviated - fails)
  # NOT: type: "CD-V2-AWS-ECS" ❌ (missing -CLUSTER - fails)
  # NOT: type: "CD-V2-ECS-CLUSTER" ❌ (missing AWS - fails)
```

**Validation checklist for EACH component:**
- ☐ Opened components.json and searched for related component
- ☐ Found exact match by reading `name` field
- ☐ Copied COMPLETE `referenceId` field value without modification
- ☐ Verified the referenceId exists in components.json (didn't make it up)

**Rule:** If the referenceId looks redundant or excessively long (e.g., "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL"), use it anyway. Do NOT try to "simplify" or "abbreviate" it. If you can't find a component in components.json, use a generic type or skip it - do NOT invent referenceIds.

### Step 4b: Validate References When Updating Existing Threat Models

**⚠️ CRITICAL for Updates:** If updating an existing project, you must verify all referenced IDs exist.

**For existing projects:**
1. Read `.iriusrisk/project.json` to see current project structure
2. If it exists, also check for an existing OTM export or component list
3. When referencing components in `parent: { component: "x" }` or dataflows, verify that component ID exists
4. When referencing trust zones in `parent: { trustZone: "x" }`, verify that trust zone ID exists in trust-zones.json

**Validation rules:**
- **Component parent references:** The parent component ID must exist either in the current OTM or be defined earlier in the same OTM file
- **Dataflow references:** Both source and destination component IDs must exist in the OTM's components section
- **Trust zone references:** The trust zone ID must exist in trust-zones.json AND in the OTM's trustZones section
- **Do NOT reference components that don't exist** - this causes import failures

### Step 5: import_otm() - Upload to IriusRisk

Call **import_otm("[path-to-otm-file.otm]")**

What happens:
- Validates and uploads OTM file to IriusRisk
- Creates new project or updates existing
- Triggers automatic threat generation
- Returns project ID, name, and status

### Step 6: project_status() - Verify Success

Call **project_status()**

Verifies:
- Project exists and accessible
- Import processing complete
- Project ready for use
- No error messages

### Step 7: Present Results & Offer Options - STOP HERE

**⚠️ CRITICAL: Do NOT automatically run sync() to download threats/countermeasures.**

**Why NOT automatic:**
- IriusRisk needs time to process the threat model and generate threats
- Running sync() immediately often results in empty threats (countermeasures may download, but threats will be empty)
- User may want to refine the architecture first
- User controls the pace and timing

**What to do:**
1. Summarize what was accomplished:
   - Number of components mapped
   - Trust zones used
   - Dataflows created
   - Successful import confirmation
   
2. **Present options and WAIT for user decision:**
   - **Option A:** "I can download the generated threats and countermeasures now (IriusRisk may still be processing)"
   - **Option B:** "Would you like to refine the architecture before downloading security findings?"
   - **Option C:** "What would you like to do next?"

3. **WAIT for user response** - do not proceed to Step 8 automatically

### Step 8: sync() Again - Download Security Findings (ONLY When User Explicitly Requests)

**⚠️ Only proceed to this step when the user explicitly asks to download threats/countermeasures.**

When user requests, call **sync(project_path)** again to download:
- Generated threats (threats.json)
- Generated countermeasures (countermeasures.json)
- Complete threat model data

**Timing note:** If threats.json is empty after sync, IriusRisk may still be processing. Inform user to wait a minute and try again.

### Step 9: threats_and_countermeasures() - Analysis Guidance

After downloading security data, call **threats_and_countermeasures()** to get instructions for:
- Reading threats.json and countermeasures.json
- Explaining security findings to users
- Generating code examples and implementation guidance
- Security analysis best practices

## Trust Zone Guidelines

**⚠️ DO NOT use these as literal trust zone IDs.** These are conceptual examples only.

**ALWAYS read `.iriusrisk/trust-zones.json` to find:**
- Available trust zones in your IriusRisk instance
- Exact `id` field values (usually UUIDs like "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c")
- Trust rating values for each zone
- Descriptive names to help you choose appropriate zones

**Common trust zone patterns (names may vary in your instance):**
- Internet/External (rating: 1) - External-facing, public APIs, third-party services
- DMZ/Public Cloud (rating: 3-5) - Load balancers, web servers, API gateways
- Internal/Application (rating: 5-7) - Application servers, internal APIs, business logic
- Secure/Private (rating: 7-10) - Databases, auth servers, sensitive data storage

**To use a trust zone:**
1. Read trust-zones.json
2. Find zone with appropriate name and trust rating
3. Copy its `id` value (not the `name`)
4. Use that exact `id` in your component's `parent: { trustZone: "id-here" }`

## Final Validation Checklist

Before completing, validate ALL references:

**Initial Setup:**
- ☐ Used sync() first - Downloaded components.json AND trust-zones.json
- ☐ **Read trust-zones.json and identified available trust zones with their IDs**
- ☐ Read components.json for component type mapping (not CLI commands)
- ☐ If updating existing project: Read project.json or exported OTM to know existing component IDs

**OTM Structure:**
- ☐ Created OTM with ONLY architecture (no threats/controls)
- ☐ **For EVERY component: Opened components.json, found the component, copied COMPLETE referenceId**
- ☐ **Verified each referenceId exists in components.json** (e.g., "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL", not "CD-V2-AWS-WAF")
- ☐ **Used EXACT trust zone IDs from trust-zones.json (not invented names)**
- ☐ **Verified EVERY component has a parent (trustZone or component)**

**Reference Validation (CRITICAL):**
- ☐ **Verified all trust zone IDs in `parent: { trustZone: "x" }` exist in trust-zones.json**
- ☐ **Verified all component IDs in `parent: { component: "x" }` exist in the OTM's components section (defined earlier/above)**
- ☐ **Verified EVERY dataflow has a `name` field** (REQUIRED - this was causing your import error!)
- ☐ **Verified all dataflow source IDs exist in the OTM's components section**
- ☐ **Verified all dataflow destination IDs exist in the OTM's components section**
- ☐ **Validated no dataflows use trust zone IDs (must use component IDs only)**

**Upload:**
- ☐ Used import_otm() to upload
- ☐ Used project_status() to verify
- ☐ Presented user with options and STOPPED (did not auto-sync)

**Remember:**
- AI role: Architecture modeling only
- IriusRisk role: Threat identification and security analysis (automatic)
- **TOP ERRORS TO AVOID:**
  1. **Abbreviating component referenceIds** - Use COMPLETE string from components.json (e.g., "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL" not "CD-V2-AWS-WAF")
  2. **Inventing component referenceIds** - Every referenceId MUST exist in components.json (open the file and verify)
  3. **Inventing trust zone IDs** - MUST read trust-zones.json and use exact IDs
  4. **Components without parents** - Every component MUST have trustZone or component parent
  5. **Referencing non-existent components** - All parent/dataflow component IDs must exist in OTM
  6. **Using trust zone IDs in dataflows** - Dataflows connect components only
- **Before submitting OTM - Cross-reference validation:**
  - Open components.json and verify EVERY component type referenceId exists in that file
  - List all component IDs defined in your OTM
  - Verify every parent component reference is in that list
  - Verify every dataflow source/destination is in that list
  - Verify every trust zone ID exists in trust-zones.json
