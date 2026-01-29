# IriusRisk Threat Model Creation Instructions for AI Assistants

## Executive Summary
Create OTM files to model system architecture for IriusRisk threat analysis. Your role: architecture modeling only (components, trust zones, data flows). Do NOT create threats or controls—IriusRisk generates those automatically. 

**When user explicitly requests threat modeling** (e.g., "create a threat model", "threat model this code", "update the threat model"), **proceed immediately** with the workflow:

**Standard workflow:** sync() first → **check for .iriusrisk/current-threat-model.otm** → create/merge OTM → import_otm() → project_status() → **STOP and offer next steps**.

**🚨 CRITICAL DECISION POINT:**
- **If `.iriusrisk/current-threat-model.otm` exists** → You are UPDATING/MERGING with existing model
- **If no local OTM file** → You are CREATING a new threat model

**DO NOT ask user for permission when they've explicitly requested threat modeling.** The request IS the permission.

**Do NOT automatically download threats/countermeasures after import** - IriusRisk needs time to process. After import, STOP and offer options (questionnaires, download threats, etc.).

**⚠️ CRITICAL: Dataflows ONLY connect components to components. NEVER use trust zone IDs in dataflows - this causes import failure.**

## Multi-Repository Threat Modeling

**Multiple repositories can contribute to a SINGLE unified threat model.** This is essential for microservices, infrastructure-as-code, and multi-repository architectures.

### When to Use Multi-Repository Workflow

**FIRST: Check for existing threat model:**

1. **Check `.iriusrisk/current-threat-model.otm`** - If this file exists, it contains the current threat model from IriusRisk
   - This file is automatically downloaded by `sync()` 
   - It represents the latest state of the threat model
   - **You MUST use this as your starting point for updates**

2. **Read `.iriusrisk/project.json`**:
   - If it contains `project_id` or `reference_id`, a project exists
   - Check for `scope` field - indicates this is a multi-repo contribution
   
3. **Verify project status** - Call `project_status()` to confirm project is ready

**If `current-threat-model.otm` exists:**
- **This repository is updating an existing threat model**
- **You MUST read and merge with the existing OTM file**
- Your job is to ADD/ENHANCE the threat model, not replace it
- Preserve existing component IDs and add your contributions

**If no `current-threat-model.otm` but project.json exists:**
- Project may exist but hasn't been synced yet
- Call `sync()` first to download the current threat model
- Then proceed with merge workflow

### Multi-Repository Workflow (When Project Exists)

**MANDATORY steps when contributing to existing project:**

1. **Check for local OTM file FIRST** - Read `.iriusrisk/current-threat-model.otm`:
   - This file is automatically created when you run `sync()`
   - It contains the latest threat model from IriusRisk
   - **If this file exists, use it directly** - no need to call export_otm()
   - If file doesn't exist, you need to run `sync()` first

2. **Read the scope** from `.iriusrisk/project.json`:
   ```json
   {
     "name": "E-commerce Platform",
     "project_id": "abc-123",
     "reference_id": "ecommerce-platform",
     "scope": "AWS infrastructure via Terraform. Provisions ECS for backend API (api-backend repo), 
              RDS PostgreSQL, ALB, CloudFront for frontend (web-frontend repo). All application 
              components from other repos should be placed within appropriate AWS services."
   }
   ```

3. **Read the existing threat model:**
   
   **Option A (Preferred)**: Read local file:
   ```python
   # Read the downloaded OTM file
   with open('.iriusrisk/current-threat-model.otm', 'r') as f:
       existing_otm_content = f.read()
   ```
   
   **Option B (Fallback)**: Export if local file missing:
   ```python
   # Only if current-threat-model.otm doesn't exist
   # First call sync() to download it, or:
   existing_otm = export_otm(project_id="ecommerce-platform")
   ```

4. **Analyze the existing OTM:**
   - Identify existing components and their structure
   - Note existing trust zones
   - Understand existing data flows
   - Look for components mentioned in your repository's scope

4. **Understand your scope and how to merge:**
   
   **Infrastructure scope** (e.g., "AWS infrastructure", "Kubernetes platform"):
   - Add infrastructure components (ECS cluster, RDS, ALB, VPC, etc.)
   - Modify existing application components to show they run INSIDE your infrastructure
   - Example: Existing "API Service" component → make it a child of your "ECS Cluster" component
   - Add networking components (load balancers, CDN, etc.)
   - Define trust zones based on network boundaries (VPC, subnets, etc.)

   **Application scope** (e.g., "Backend API", "Frontend SPA"):
   - Add your application components
   - If infrastructure exists, make your components children of infrastructure components
   - If no infrastructure yet, use trust zones as parents
   - Add data flows between your components

   **Integration scope** (e.g., "CI/CD pipeline", "Monitoring"):
   - Add operational/supporting components
   - Show how they interact with application and infrastructure

5. **Create merged OTM file:**
   
   **CRITICAL RULES:**
   - **PRESERVE project.id** - use the EXACT same project.id from existing OTM or project.json reference_id
   - **INCLUDE existing components** - don't remove what's already there
   - **ADD your new components** - components from your repository analysis
   - **MODIFY parent relationships** - adjust existing components to fit within your contribution
   - **ADD new data flows** - show how new components connect to existing ones
   
   **Example merging pattern:**
   ```yaml
   # Existing OTM had this (from application repo):
   components:
     - id: "api-service"
       name: "API Service"
       type: "CD-V2-WEB-SERVICE"
       parent:
         trustZone: "public-cloud-uuid"  # Abstract parent
   
   # Your merged OTM (infrastructure repo) adds ECS and modifies parent:
   components:
     - id: "ecs-cluster"
       name: "ECS Fargate Cluster"
       type: "CD-V2-AWS-ECS-CLUSTER"
       parent:
         trustZone: "public-cloud-uuid"
     
     - id: "api-service"  # SAME ID - preserving existing component
       name: "API Service"
       type: "CD-V2-WEB-SERVICE"
       parent:
         component: "ecs-cluster"  # NEW PARENT - now shows it runs in ECS
     
     - id: "alb"  # NEW component from your analysis
       name: "Application Load Balancer"
       type: "CD-V2-AWS-APPLICATION-LOAD-BALANCER"
       parent:
         trustZone: "public-cloud-uuid"
   
   dataflows:
     - id: "alb-to-api"  # NEW dataflow
       source: "alb"
       destination: "api-service"
   ```

6. **Verify merge quality:**
   - All existing component IDs preserved (same IDs as before)
   - Your new components added with unique IDs
   - Parent relationships make architectural sense
   - Data flows connect existing and new components appropriately
   - Trust zones used consistently

### Scope-Based Merging Guidelines

**Use the scope description to guide your merging strategy:**

- **"AWS infrastructure for backend API (api-backend repo)"**:
  - Look for components named "api", "backend", "service" in existing OTM
  - Wrap those in your AWS components (ECS, ALB, etc.)
  
- **"Frontend SPA deployed to CloudFront (terraform repo)"**:
  - Look for "frontend", "web-app", "spa" components
  - Add CloudFront and make frontend a child or connected via dataflow
  
- **"Kubernetes deployment for microservices (auth-service, order-service)"**:
  - Look for services mentioned in scope
  - Add K8s components (namespaces, pods, services)
  - Make microservices children of K8s pod components

**If scope mentions other repositories:**
- Those components may already exist in the OTM
- Your job is to add context/infrastructure around them
- Don't delete or ignore them - incorporate them into your contribution

### Component Layout and Positioning When Merging

**⚠️ CRITICAL: OTM files include visual positioning data (x, y, width, height) for diagram layout.**

**⚠️ BEFORE WORKING ON LAYOUT: You MUST validate all component types and trust zone IDs against the actual JSON files:**
- **Every component `type`** must exist in `.iriusrisk/components.json` (exact `referenceId` match)
- **Every trust zone ID** must exist in `.iriusrisk/trust-zones.json` (exact `id` match)
- **DO NOT invent components or trust zones** - if you can't find an exact match, use a generic type or ask the user

When merging contributions from multiple repositories, you must intelligently manage component positioning to create a clear, well-organized diagram.

**Layout Management Strategy:**

1. **Preserve Existing Positions** - Keep existing components roughly where they are:
   ```yaml
   # Existing component from first repo
   - id: "api-service"
     representation:
       position:
         x: 100
         y: 100
       size:
         width: 120
         height: 80
   
   # Your merge: Keep it at roughly the same position
   - id: "api-service"
     representation:
       position:
         x: 100  # Preserved or slightly adjusted
         y: 100
       size:
         width: 120
         height: 80
   ```

2. **Create Space for New Components** - Adjust layout to accommodate additions:
   - If adding infrastructure that wraps applications, position infrastructure components to visually contain their children
   - If adding peer services, place them alongside existing components with appropriate spacing
   - Expand the overall diagram area if needed to prevent cramming
   - Use consistent spacing between components (e.g., 50-100 pixels between unrelated components)

3. **Maintain Architectural Clarity** - Position components to reflect relationships:
   - **Infrastructure wrapping applications**: Position parent infrastructure components to visually contain children
   - **Sequential data flows**: Arrange left-to-right or top-to-bottom to show flow direction
   - **Related components**: Group by function or trust zone (databases together, services together, etc.)
   - **Trust zone alignment**: Components in same trust zone should be visually grouped

4. **Smart Adjustment Patterns:**

   **Pattern A: Adding Infrastructure Around Applications**
   ```yaml
   # Original (application repo): API service at x:200, y:200, size 85x85
   # Your addition (infrastructure repo): ECS cluster must encompass it
   
   # STEP 1: Calculate ECS cluster size based on child
   # Child at x:200, y:200, size 85x85 means child occupies x:200-285, y:200-285
   # Add padding: width = 85 + (2*40) = 165, height = 85 + (2*40) = 165
   # Position parent 40px left/above child: x = 200-40 = 160, y = 200-40 = 160
   
   - id: "ecs-cluster"
     representation:
       position:
         x: 160    # 40px left of child
         y: 160    # 40px above child
       size:
         width: 165   # CALCULATED: child width + 2*padding
         height: 165  # CALCULATED: child height + 2*padding
   
   - id: "api-service"  # Existing component - no change needed
     parent:
       component: "ecs-cluster"
     representation:
       position:
         x: 200    # Original position preserved
         y: 200
       size:
         width: 85   # Standard leaf size
         height: 85
   ```

   **Pattern B: Adding Peer Services Inside Same Container**
   ```yaml
   # Existing auth-service at x:200, y:200 inside ecs-cluster
   # Adding payment-service alongside it
   # Container must GROW to accommodate both
   
   # STEP 1: Position new service
   - id: "payment-service"
     parent:
       component: "ecs-cluster"
     representation:
       position:
         x: 335    # 335 = 200 + 85 + 50 (spacing)
         y: 200    # Same vertical position (aligned)
       size:
         width: 85   # Standard leaf size
         height: 85
   
   # STEP 2: Recalculate parent size
   # Children now occupy: x:200-420 (335+85), y:200-285
   # Child area: 220x85
   # Add padding: width = 220 + 80 = 300, height = 85 + 80 = 165
   # Minimum: max(300, 200) = 300, max(165, 200) = 200
   
   - id: "ecs-cluster"
     representation:
       position:
         x: 160    # Adjust left to accommodate wider content
         y: 160
       size:
         width: 300   # RECALCULATED - grew from 165 to 300
         height: 200  # RECALCULATED - uses minimum
   
   # STEP 3: If ecs-cluster has a parent component, recalculate that too!
   ```

   **Pattern C: Adding Load Balancer in Front (Peer at Same Level)**
   ```yaml
   # Existing backend at x:300, y:200 (leaf component, size 85x85)
   # Adding ALB that routes to it (also a leaf component)
   
   - id: "alb"
     representation:
       position:
         x: 150    # To the left (upstream in data flow)
         y: 200    # Same vertical position
       size:
         width: 85   # Standard leaf size
         height: 85
   
   # Backend stays unchanged
   - id: "backend"
     representation:
       position:
         x: 300    # Original position
         y: 200
       size:
         width: 85   # Standard leaf size
         height: 85
   
   # If both are in a container, that container must fit both:
   # Container would need: width = (300+85-150) + 80 = 315, height = 85 + 80 = 165
   ```

5. **Typical Component Sizes:**
   - **Standard leaf components** (services, databases, APIs, load balancers): width: 85, height: 85
   - **Container components** (infrastructure that contains other components): Calculated based on children (see calculation algorithm below)

6. **Spacing Guidelines:**
   - **Minimum spacing** between unrelated components: 50 pixels
   - **Comfortable spacing**: 80-100 pixels
   - **Visual grouping**: Related components can be closer ( 30-40 pixels)
   - **Padding inside containers**: Child components should be 30-40 pixels from parent edges

7. **Cascading Size Calculation Algorithm:**

   **⚠️ CRITICAL: When adding components to nested hierarchies, you MUST recalculate sizes from bottom-up (leaves to root).**
   
   **⚠️ VALIDATION FIRST: Before applying this algorithm, VALIDATE every component type:**
   - Open `.iriusrisk/components.json`
   - For EACH component in your OTM, search for its `type` value in components.json
   - Verify the COMPLETE `referenceId` exists (e.g., "CD-V2-AWS-ECS-CLUSTER")
   - If not found, DO NOT use that component - find an alternative or use a generic type
   
   Components can be nested multiple levels deep (component in component in component in trust zone). When you add new child components, parent sizes must expand, which causes grandparent sizes to expand, etc.
   
   **Algorithm (work from leaf nodes up to root):**
   
   a. **Identify leaf components** (components with no children):
      - **VALIDATE**: Verify component type exists in components.json
      - Set size to 85x85 pixels (standard)
      
   b. **For each parent component** (components that contain other components):
      - **VALIDATE**: Verify parent component type exists in components.json
      - List all direct children
      - Calculate bounding box needed to contain all children with padding:
        ```
        child_area_width = max(child.x + child.width for all children) - min(child.x for all children)
        child_area_height = max(child.y + child.height for all children) - min(child.y for all children)
        
        parent.width = child_area_width + (2 * PADDING)   # PADDING = 40 pixels
        parent.height = child_area_height + (2 * PADDING)
        
        # Minimum size for containers
        parent.width = max(parent.width, 200)
        parent.height = max(parent.height, 200)
        ```
      
   c. **Repeat step b for each level** moving up the hierarchy:
      - First calculate sizes for components at depth N (deepest parents)
      - Then calculate sizes for components at depth N-1 (their parents)
      - Continue until reaching root components (those with trust zone parents)
   
   **Practical Example:**
   
   ```yaml
   # Scenario: Adding 2 new microservices to existing ECS cluster that already has 1 service
   
   # STEP 1: Position leaf components (the services)
   - id: "auth-service"    # Existing
     representation:
       position: {x: 220, y: 220}
       size: {width: 85, height: 85}    # Leaf component
   
   - id: "payment-service"  # New - position to the right
     representation:
       position: {x: 350, y: 220}       # 350 = 220 + 85 + 45 (component + width + spacing)
       size: {width: 85, height: 85}    # Leaf component
   
   - id: "order-service"    # New - position below
     representation:
       position: {x: 220, y: 350}       # 350 = 220 + 85 + 45 (component + height + spacing)
       size: {width: 85, height: 85}    # Leaf component
   
   # STEP 2: Calculate parent size based on children
   # Children occupy: x from 220 to 435 (350+85), y from 220 to 435 (350+85)
   # Child area: 215x215
   # Add padding: 215 + (2*40) = 295x295
   
   - id: "ecs-cluster"      # Parent container - SIZE MUST ADJUST
     representation:
       position: {x: 150, y: 150}       # Parent positioned to encompass children
       size: {width: 295, height: 295}  # CALCULATED from children, not hardcoded!
   
   # STEP 3: If ecs-cluster is inside another component, recalculate that component's size too
   # Continue up the tree...
   ```
   
   **Key Rules:**
   - **NEVER use fixed sizes for container components** - always calculate from children
   - **Always add padding** (30-40 pixels) around children
   - **Recalculate bottom-up** - start with deepest nested components first
   - **Adjust positions if needed** to maintain spacing when parent grows
   - If a parent component grows, its parent may need to grow too - cascade up the tree

**What NOT to Do:**
- ❌ **NEVER invent component types** - every `type` must exist in components.json
- ❌ **NEVER invent trust zone IDs** - every trust zone must exist in trust-zones.json
- ❌ Don't assume a component type exists without verifying in components.json
- ❌ Don't use abbreviated component types (must be COMPLETE referenceId)
- ❌ Don't use hardcoded/fixed sizes for container components (components with children)
- ❌ Don't forget to recalculate parent sizes when adding child components
- ❌ Don't cram all new components into a tiny corner
- ❌ Don't place components at x:0, y:0 unless intentional
- ❌ Don't overlap components (unless showing containment with parent/child)
- ❌ Don't ignore existing positioning data - work with it
- ❌ Don't create massive gaps between related components
- ❌ Don't stop at one level - cascade size adjustments up the entire tree

**What TO Do:**
- ✅ **FIRST: Open and read components.json - verify EVERY component type exists**
- ✅ **FIRST: Open and read trust-zones.json - verify EVERY trust zone ID exists**
- ✅ Search components.json for each component type before using it
- ✅ Copy COMPLETE referenceId from components.json (e.g., "CD-V2-AWS-ECS-CLUSTER")
- ✅ **ALWAYS calculate container sizes bottom-up** from their children
- ✅ Start with leaf components (85x85), then calculate parent sizes, then grandparent sizes
- ✅ Recalculate EVERY ancestor when adding components to a nested hierarchy
- ✅ Add appropriate padding (40 pixels) around children when calculating parent sizes
- ✅ Analyze existing component positions before planning your additions
- ✅ Position new components to reflect data flow and architecture relationships
- ✅ Use calculated size differences to show depth (deeper nesting = larger containers)
- ✅ Leave room for future additions from other repositories

**Critical Process for Nested Hierarchies:**

When you add components to a nested structure, follow this process:

1. **Identify the hierarchy depth:**
   ```
   Trust Zone
     └─ VPC Component (depth 1)
        └─ ECS Cluster Component (depth 2)
           └─ Service Components (depth 3 - leaves)
   ```

2. **Work bottom-up:**
   - Depth 3 (leaves): Set to 85x85
   - Depth 2 (ECS Cluster): Calculate from children + padding
   - Depth 1 (VPC): Calculate from ECS Cluster + padding
   - Trust Zone: Adjust if using visual representation

3. **Show your calculations:**
   ```
   # Adding 2 services to ECS cluster that has 1 existing service
   # Existing: auth-service at (200, 200)
   # New: payment-service at (335, 200), order-service at (200, 335)
   # 
   # Services occupy: x:200-420, y:200-420 = 220x220 area
   # ECS cluster needs: 220 + 80 (padding) = 300x300
   # ECS at (160, 160) to give 40px padding
   #
   # If ECS is inside VPC, VPC must now accommodate 300x300 cluster
   # VPC needs: 300 + 80 (padding) = 380x380
   # VPC at (120, 120) to give 40px padding
   ```

This algorithmic approach ensures diagrams remain organized even with deep nesting.

**Example Adjustment:**
```yaml
# Scenario: Infrastructure repo adding AWS components around existing application components

# Existing OTM had (from application repo):
components:
  - id: "auth-api"
    representation:
      position: {x: 200, y: 200}
      size: {width: 85, height: 85}
  - id: "user-api"
    representation:
      position: {x: 335, y: 200}  # 335 = 200 + 85 + 50
      size: {width: 85, height: 85}

# Your merged OTM (infrastructure repo) - SHOWING CALCULATION PROCESS:

# STEP 1: Calculate ECS cluster size to contain both APIs
# Children occupy: x from 200 to 420 (335+85), y from 200 to 285 (200+85)
# Child area: width = 420-200 = 220, height = 285-200 = 85
# Add padding: width = 220 + (2*40) = 300, height = 85 + (2*40) = 165
# Apply minimum: width = max(300, 200) = 300, height = max(165, 200) = 200
# Position: x = 200 - 40 = 160, y = 200 - 40 = 160

components:
  # New load balancer positioned upstream (leaf component)
  - id: "alb"
    representation:
      position: {x: 50, y: 200}  # To the left, aligned vertically
      size: {width: 85, height: 85}  # Standard leaf size
  
  # New infrastructure component - SIZE CALCULATED FROM CHILDREN
  - id: "ecs-cluster"
    representation:
      position: {x: 160, y: 160}  # 40px left/above leftmost/topmost child
      size: {width: 300, height: 200}  # CALCULATED: 220 + 80 padding, 85 + 80 + min
  
  # Existing components - preserved
  - id: "auth-api"
    parent:
      component: "ecs-cluster"
    representation:
      position: {x: 200, y: 200}  # Original position kept
      size: {width: 85, height: 85}
  
  - id: "user-api"
    parent:
      component: "ecs-cluster"
    representation:
      position: {x: 335, y: 200}  # Original position kept
      size: {width: 85, height: 85}
  
  # New database positioned to the right of cluster (leaf component)
  # Position: 160 (cluster x) + 300 (cluster width) + 50 (spacing) = 510
  - id: "rds-database"
    representation:
      position: {x: 510, y: 200}  # To the right with spacing
      size: {width: 85, height: 85}  # Standard leaf size
```

**Key Principle:** The goal is to create a diagram that looks intentionally designed, not randomly assembled. Each repository's contribution should integrate smoothly while maintaining visual consistency and architectural clarity.

### When NOT to Use Multi-Repository Workflow

**Use standard (single-repo) workflow when:**
- `.iriusrisk/project.json` doesn't exist (new project)
- `project_id` field is missing (project not yet created)
- No `scope` field present (single repository project)
- User explicitly states this is a new, independent project

## Critical Error #1: Dataflows Connect Components, NOT Trust Zones

**Most common OTM import failure:** Using trust zone IDs in dataflows instead of component IDs.

```yaml
# ✅ CORRECT - Component to Component:
dataflows:
  - id: "user-to-app"
    source: "mobile-app"      # component ID
    destination: "web-server" # component ID

# ❌ WRONG - Trust Zone IDs (CAUSES IMPORT FAILURE):
dataflows:
  - id: "bad-flow"
    source: "internet"        # trust zone ID - FAILS!
    destination: "dmz"        # trust zone ID - FAILS!
```

**Rule:** Trust zones CONTAIN components. Dataflows CONNECT components directly.

## Critical Error #2: Component Types Must Use COMPLETE, EXACT referenceId

**Most common component mapping failure:** Abbreviating, truncating, or INVENTING the referenceId instead of using the complete string from components.json.

**🚨 ABSOLUTE RULE: EVERY component type MUST exist in `.iriusrisk/components.json`. If it's not in that file, you CANNOT use it.**

```yaml
# ✅ CORRECT - Complete referenceId from components.json:
type: "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL"  # Full string, even though long

# ❌ WRONG - Abbreviated (common mistake):
type: "CD-V2-AWS-WAF"  # Missing "-WEB-APPLICATION-FIREWALL" - FAILS

# ❌ WRONG - Simplified:
type: "aws-ecs"  # Way too short - FAILS

# ❌ WRONG - Partially truncated:
type: "CD-V2-AWS-ECS"  # Missing "-CLUSTER" - FAILS

# ❌ WRONG - Invented based on pattern:
type: "CD-V2-AWS-FARGATE-SERVICE"  # Doesn't exist in components.json - FAILS

# ❌ WRONG - Made up descriptive name:
type: "CD-V2-CONTAINER-SERVICE"  # Not verified in components.json - FAILS
```

**Mandatory Validation Process:**
1. **BEFORE using any component type** - Open `.iriusrisk/components.json`
2. **Search for keywords** related to what you need (e.g., "ECS", "database", "WAF")
3. **Find the matching component** - Read the `name` field to confirm it's what you need
4. **Copy the COMPLETE `referenceId`** - Do not modify, abbreviate, or truncate it
5. **If not found** - Use a generic type or ask the user, DO NOT invent a type

**Rule:** Read `.iriusrisk/components.json`, find the `referenceId` field, **copy the ENTIRE string without modification**. Do not abbreviate, even if it looks redundant. **Never invent component types - they must exist in the file.**

## Critical Error #3: NEVER CHANGE PROJECT ID WHEN UPDATING

**🚨 ABSOLUTE RULE: The `project.id` field in an OTM file is SACRED and MUST NEVER BE CHANGED.**

### When Creating NEW Threat Models:
```yaml
# Read from .iriusrisk/project.json:
# reference_id: "my-app-xyz"

# Use that EXACT value in OTM:
project:
  id: "my-app-xyz"  # ✅ Taken from project.json reference_id
  name: "My App"
```

### When UPDATING Existing Threat Models:

**FORBIDDEN ACTIONS - NEVER DO THESE:**
- ❌ Changing project.id to make it "more descriptive"
- ❌ Adding version numbers to project.id (e.g., "my-app-v2")
- ❌ Changing project.id because of import errors
- ❌ Using a UUID instead of the reference_id
- ❌ Modifying project.id in ANY way for ANY reason

**REQUIRED ACTIONS:**
- ✅ Read existing OTM file if it exists
- ✅ **PRESERVE the exact project.id from existing OTM** 
- ✅ **OR use reference_id from project.json if OTM doesn't exist**
- ✅ **NEVER EVER EVER change the project.id once set**

```yaml
# Existing OTM has:
project:
  id: "badger-app-7ozf"  # This is GOSPEL - DO NOT CHANGE

# When updating to add features:
project:
  id: "badger-app-7ozf"  # ✅ SAME - NEVER CHANGED
  name: "Badger App with Payments"  # ← Name can change, ID CANNOT
```

**Why this matters:**
- The project.id links the OTM to the IriusRisk project
- Changing it breaks this connection and creates duplicate projects
- IriusRisk will reject updates with mismatched IDs
- The project.id from project.json is the source of truth

**If import_otm() fails:**
- ❌ **DO NOT** try changing the project.id to "fix" it
- ✅ **DO** stop and report the actual error
- ✅ **DO** tell the user to check project state in IriusRisk UI

The project.id is the ONLY field that must never be modified when updating. Treat it as immutable, permanent, and untouchable.

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

## 🚨 CRITICAL: Tags in OTM - Architecture ONLY, NOT Vulnerabilities

**Tags are for ARCHITECTURAL categorization, NOT for documenting vulnerabilities you find in code.**

### What Tags Are For

Tags describe the **purpose, function, or data sensitivity** of components and dataflows in the architecture:

```yaml
# ✅ CORRECT - Architectural/functional tags
components:
  - id: "payment-api"
    name: "Payment Service"
    type: "CD-V2-WEB-SERVICE"
    tags:
      - "pci-dss-scope"           # Compliance scope
      - "payment-processing"      # Business function
      - "customer-data"           # Data sensitivity
      - "high-availability"       # Operational requirement
      - "public-facing"           # Exposure level

dataflows:
  - id: "app-to-payment"
    source: "web-app"
    destination: "payment-api"
    tags:
      - "credit-card-data"        # Data type flowing
      - "encrypted-in-transit"    # Security control present
      - "pci-dss-boundary"        # Compliance boundary
```

### What Tags Are NOT For

**❌ NEVER use tags to document vulnerabilities or security flaws you find in code:**

```yaml
# ❌ WRONG - Vulnerability tags (DO NOT DO THIS)
components:
  - id: "flask-app"
    name: "Flask API"
    type: "CD-V2-WEB-SERVICE"
    tags:
      - "sql-injection-vulnerable"      # ❌ This is a THREAT, not architecture
      - "insecure-deserialization"      # ❌ This is a VULNERABILITY
      - "command-injection-vulnerable"  # ❌ This is a SECURITY FLAW
      - "sensitive-data-exposure"       # ❌ This is a WEAKNESS

dataflows:
  - id: "app-to-db"
    source: "flask-app"
    destination: "database"
    tags:
      - "sql-injection-vulnerable"   # ❌ NO! This is a threat
      - "no-parameterization"        # ❌ NO! This is an implementation flaw
      - "arbitrary-code-execution"   # ❌ NO! This is a vulnerability
```

### Why This Matters

1. **IriusRisk identifies vulnerabilities** - The threat library contains thousands of threats based on component types and patterns. Your job is to model the architecture correctly, and IriusRisk will identify the relevant threats.

2. **Tags clutter the diagram** - Vulnerability tags appear as labels on the diagram, making it unreadable and unprofessional.

3. **Mixes concerns** - The OTM describes "what is" (architecture), not "what's wrong" (threats). Threats come from IriusRisk's rules engine after import.

4. **Makes threat modeling subjective** - Different analysts would add different vulnerability tags. The architecture should be objective.

5. **Defeats the purpose** - If you manually tag all vulnerabilities, why use IriusRisk's automated threat detection?

### When You Find Vulnerabilities in Code

**If you notice vulnerabilities while analyzing source code (SQL injection, weak crypto, etc.):**

1. ✅ **DO** model the architecture accurately (component types, data flows)
2. ✅ **DO** use appropriate component types that will trigger threat detection (e.g., `CD-V2-WEB-SERVICE` for SQL injection prone components)
3. ✅ **DO** note code issues in your analysis comments or report to the user
4. ❌ **DO NOT** add vulnerability tags to the OTM
5. ❌ **DO NOT** try to manually enumerate threats in the architecture

**Trust IriusRisk to find the threats based on your accurate architecture modeling.**

### Good Tag Examples

**Architectural purpose:**
- `authentication-service`
- `payment-processing`
- `user-registration`
- `admin-functionality`

**Data sensitivity:**
- `pii-processing`
- `financial-data`
- `health-records`
- `customer-data`

**Compliance scope:**
- `pci-dss-scope`
- `hipaa-scope`
- `gdpr-relevant`
- `sox-controls`

**Operational characteristics:**
- `public-facing`
- `internal-only`
- `high-availability`
- `batch-processing`

**Network exposure:**
- `internet-accessible`
- `vpn-only`
- `private-network`

### Bad Tag Examples (NEVER USE)

**Vulnerability/weakness tags:**
- ❌ `sql-injection-vulnerable`
- ❌ `xss-vulnerable`
- ❌ `insecure-deserialization`
- ❌ `command-injection`
- ❌ `weak-crypto`
- ❌ `hardcoded-credentials`

**Implementation flaw tags:**
- ❌ `no-parameterization`
- ❌ `no-validation`
- ❌ `unauthenticated`
- ❌ `unencrypted`
- ❌ `pickle-serialization`

**Security finding tags:**
- ❌ `ssrf-vulnerable`
- ❌ `csrf-vulnerable`
- ❌ `arbitrary-code-execution`
- ❌ `untrusted-input`
- ❌ `sensitive-data-exposure`

### Rule of Thumb

**Ask yourself: "Is this tag describing WHAT the component IS, or WHAT'S WRONG with it?"**

- If it describes **what it is** → ✅ Good tag
- If it describes **what's wrong** → ❌ Bad tag (let IriusRisk find the vulnerability)

### Summary

**Tags = Architecture categorization**  
**Threats = IriusRisk's job**

Do not conflate these. Model the architecture accurately, use meaningful architectural tags, and trust IriusRisk to identify all the vulnerabilities.

## Required Workflow Checklist

**🚨 VALIDATION RULE - READ THIS FIRST:**
- **EVERY component type** you use MUST exist in `.iriusrisk/components.json` - Open the file and verify!
- **EVERY trust zone ID** you use MUST exist in `.iriusrisk/trust-zones.json` - Open the file and verify!
- **DO NOT invent components or trust zones** - If you can't find an exact match, use a generic type or ask
- This is THE MOST COMMON failure mode - always validate before creating OTM!

**Complete steps 0-8, then STOP and wait for user.** Step 9 only when user explicitly requests.

- ☐ Step 0: **sync(project_path)** - Download components, trust zones, AND current threat model OTM
- ☐ Step 1: **CHECK FOR `.iriusrisk/current-threat-model.otm`** - If exists, READ IT IMMEDIATELY
  - **If file exists**: You are in MERGE mode - read OTM, see existing components
  - **If file missing**: You are in CREATE mode - start from scratch
- ☐ Step 2: Analyze source material - Identify architectural components from THIS repository
- ☐ Step 3: Check `.iriusrisk/project.json` - Read project name/ID/scope if exists
- ☐ Step 4: Create OTM file:
  - **MERGE mode**: Include existing components + your new components, update parent relationships
  - **CREATE mode**: All components from your analysis
- ☐ Step 5: Map components - Use exact referenceId from components.json
- ☐ Step 6: **import_otm()** - Upload OTM to IriusRisk
- ☐ Step 7: **project_status()** - Verify project ready
- ☐ Step 8: Present results - Offer options - **STOP HERE and wait for user**
- ☐ Step 9: **sync()** again - **ONLY if user explicitly requests** - Download updated threats/countermeasures

**🚨 REMEMBER: If user said "threat model [X]", you are doing architecture modeling. DO NOT call threats_and_countermeasures() or analyze threats.json.**

## Detailed Workflow

### Step 0: sync(project_path) - Download Component Library, Trust Zones, AND Current Threat Model

**Mandatory first step.** Call sync() with full absolute project path (e.g., `sync("/Users/username/my-project")`).

**What it does:**
- Downloads complete IriusRisk component library to `.iriusrisk/components.json`
- Downloads trust zones to `.iriusrisk/trust-zones.json` ⚠️ CRITICAL
- **Downloads current threat model to `.iriusrisk/current-threat-model.otm`** ⚠️ NEW
- If project exists, also downloads current threats/countermeasures/questionnaires
- Prevents OTM import failures due to unknown component types or trust zones

**⚠️ CRITICAL FILES TO CHECK AFTER SYNC (THESE ARE YOUR VALIDATION SOURCES):**
1. **`.iriusrisk/trust-zones.json`** - ⚠️ EVERY trust zone ID MUST come from this file - DO NOT invent IDs
2. **`.iriusrisk/components.json`** - ⚠️ EVERY component type MUST exist in this file - DO NOT invent types
3. **`.iriusrisk/current-threat-model.otm`** - If exists, you are UPDATING existing model (merge required)
4. **`.iriusrisk/project.json`** - Check for scope definition

**VALIDATION REQUIREMENT:** Before creating your OTM, you MUST open components.json and trust-zones.json and verify every single component type and trust zone ID you plan to use actually exists in those files. This is not optional.

**Decision Logic After Step 0:**
- **If `current-threat-model.otm` exists**: This is an UPDATE/MERGE workflow - read and merge with existing OTM
- **If no `current-threat-model.otm`**: This is a NEW threat model - create from scratch

### Step 1: Check for Existing Threat Model (BEFORE analyzing source)

**🚨 MANDATORY FIRST STEP: Check for `.iriusrisk/current-threat-model.otm`**

```python
# Check if file exists
from pathlib import Path
otm_file = Path('.iriusrisk/current-threat-model.otm')
if otm_file.exists():
    # READ IT IMMEDIATELY
    with open(otm_file, 'r') as f:
        existing_otm = f.read()
    print(f"Found existing threat model: {len(existing_otm)} bytes")
    # YOU ARE IN MERGE MODE - preserve existing components
else:
    print("No existing threat model - creating from scratch")
    # YOU ARE IN CREATE MODE
```

**If this file exists:**
- ✅ **YOU ARE UPDATING/MERGING** with an existing threat model
- ✅ **READ the entire file** to understand existing components
- ✅ Your job is to ADD your contribution, not replace
- ✅ Parse the OTM to see: existing components, trust zones, dataflows
- ✅ Plan how to integrate your new components with existing ones

**If this file does NOT exist:**
- You are creating a new threat model from scratch
- Proceed with standard analysis

### Step 2: Analyze Source & Check Configuration

**FIRST: Check for existing threat model:**
- **You already checked for `.iriusrisk/current-threat-model.otm`** in Step 1
- If it exists and you read it, you know existing architecture
- Your analysis should focus on ADDING to it, not duplicating

**Check for existing project:**
- Look for `.iriusrisk/project.json`
- If exists, use `name` and `reference_id` from that file (the `reference_id` will be used as the OTM `project.id`)
- Check for `scope` field to understand this repository's role
- If not exists, create descriptive names from source material

**Analyze source material:**
- Identify infrastructure (VMs, containers, databases, load balancers)
- Identify business logic (auth services, payment processing, user management)
- Identify data components (databases, storage, queues, caches)
- Identify external systems (third-party APIs, services)
- Plan nesting (business logic runs within infrastructure)
- Identify data flows between components
- **If existing OTM exists**: Plan how to integrate your components with existing ones
- **Do NOT identify threats or security issues**

### Step 3: Create OTM File

**Use project.json if exists:** Read `.iriusrisk/project.json` and use `name` and `reference_id` from that file. The `reference_id` becomes the `project.id` in your OTM file. Otherwise, create descriptive names.

## CRITICAL: Trust Zone Setup

**⚠️ MANDATORY: Read `.iriusrisk/trust-zones.json` file FIRST**

**🚨 ABSOLUTE RULE: EVERY trust zone ID you use MUST exist in `.iriusrisk/trust-zones.json`. If it's not in that file, you CANNOT use it.**

Before creating your OTM file, you MUST:
1. **Open and read** `.iriusrisk/trust-zones.json` (created by sync() in Step 0)
2. **Identify which trust zones you need** from the available zones in the file
3. **Copy the EXACT `id` field values** from trust-zones.json (these are UUIDs like "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c")
4. **Verify each trust zone ID** before using it in your OTM

**DO NOT:**
- Invent trust zone names or IDs (e.g., "internet", "dmz", "application" - these are NOT IDs)
- Use descriptive names instead of actual UUID IDs
- Create new trust zones not in trust-zones.json
- Assume a trust zone exists without checking the file
- Use trust zone names as IDs (use the UUID from the `id` field, not the `name` field)

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
  
  # Load balancer - standalone in public cloud zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "alb"
    name: "Application Load Balancer"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "2ab4effa-40b4-45de-ba93-9e4c3d4db85a"  # Public Cloud zone ID from trust-zones.json
  
  # Container platform - standalone in public cloud zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "ecs-cluster"
    name: "ECS Cluster"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "2ab4effa-40b4-45de-ba93-9e4c3d4db85a"  # Public Cloud zone ID from trust-zones.json
  
  # Application services - run inside container platform
  - id: "auth-service"
    name: "Authentication Service"
    type: "[exact referenceId from components.json]"
    parent:
      component: "ecs-cluster"  # runs in ECS
  
  - id: "api-service"
    name: "API Service"
    type: "[exact referenceId from components.json]"
    parent:
      component: "ecs-cluster"  # runs in ECS
  
  # Database - standalone in private secured zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "user-db"
    name: "User Database"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "f0ba7722-39b6-4c81-8290-a30a248bb8d9"  # Private Secured zone ID from trust-zones.json
  
  # External API - in internet zone
  # ⚠️ trustZone value MUST be an ID from trust-zones.json
  - id: "payment-api"
    name: "Payment Processor API"
    type: "[exact referenceId from components.json]"
    parent:
      trustZone: "b61d6911-338d-11e8-8c37-ad2a1d5c1e0c"  # Internet zone ID from trust-zones.json

dataflows:
  # ⚠️⚠️⚠️ CRITICAL: Dataflows ONLY connect components (never trust zones) ⚠️⚠️⚠️
  # Use component IDs like "web-browser", "alb", "api-service" (defined above)
  # NEVER use trust zone IDs like "internet", "dmz", "application" in dataflows
  
  - id: "user-request"
    source: "web-browser"      # component ID ✅
    destination: "alb"          # component ID ✅
  
  - id: "alb-to-api"
    source: "alb"               # component ID ✅
    destination: "api-service"  # component ID ✅
  
  - id: "api-to-auth"
    source: "api-service"       # component ID ✅
    destination: "auth-service" # component ID ✅
  
  - id: "auth-to-db"
    source: "auth-service"      # component ID ✅
    destination: "user-db"      # component ID ✅
  
  - id: "api-to-payment"
    source: "api-service"       # component ID ✅
    destination: "payment-api"  # component ID ✅

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
    source: "load-balancer"  # Component ID
    destination: "my-service"  # Component ID

# Use exact referenceId from components.json
- id: "my-db"
  type: "CD-V2-POSTGRESQL-DATABASE"  # Exact referenceId
```

### Step 4: Map Components to IriusRisk Types and VALIDATE

**🚨 THIS IS THE MOST CRITICAL STEP - 80% OF FAILURES HAPPEN HERE**

**⚠️ MANDATORY: Open and read `.iriusrisk/components.json`** (created by sync() in Step 0). This file contains all valid component types.

**⚠️ CRITICAL: Use the COMPLETE referenceId - DO NOT abbreviate, truncate, shorten, or INVENT it.**

**⚠️ ABSOLUTE RULE: If a component type is NOT in components.json, you CANNOT use it. Do NOT invent component types.**

**Mapping and Validation Process (FOLLOW EVERY STEP):**
1. **Open `.iriusrisk/components.json`** in your editor/viewer
2. **For each component** you identified in Step 1, search the file for keywords (e.g., "WAF", "database", "ECS", "lambda")
3. **Find the matching component entry** - Read the `name` field to confirm it's what you need
4. **Copy the ENTIRE `referenceId` field value** - Do not modify, abbreviate, truncate, or invent anything
5. **Paste it exactly** as the `type` in your OTM component
6. **If no match found** - Use a generic component type OR ask the user - **DO NOT invent a type**
7. **Double-check** - Before moving to next component, verify you copied from the file (not from memory/pattern)

**VALIDATION CHECKPOINT:** Before proceeding to Step 5, go through your OTM and verify you can find EVERY component type in components.json. If you can't find it, you must change it.

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

**🚨 MOST IMPORTANT: PRESERVE PROJECT ID**

When updating an existing OTM file:
1. **Read the existing OTM file FIRST**
2. **Copy the EXACT project.id value** - this is sacred and immutable
3. **NEVER change project.id** even if you think it should be more descriptive
4. Make your changes ONLY to components, dataflows, trust zones, descriptions
5. Keep project.id exactly as it was

```yaml
# Existing OTM file:
project:
  id: "badger-app-7ozf"  # ← THIS NEVER CHANGES
  name: "Badger App"

# Updated OTM file (adding payment features):
project:
  id: "badger-app-7ozf"  # ← SAME ID - NEVER CHANGED
  name: "Badger App with Payments"  # ← Only name can change
  description: "Now includes payment processing"  # ← New features described here
```

**For existing projects:**
1. Read `.iriusrisk/project.json` to see current project structure
2. **Read existing OTM file if available to get current project.id**
3. If it exists, also check for an existing OTM export or component list
4. When referencing components in `parent: { component: "x" }` or dataflows, verify that component ID exists
5. When referencing trust zones in `parent: { trustZone: "x" }`, verify that trust zone ID exists in trust-zones.json

**Validation rules:**
- **PROJECT ID:** Must be EXACTLY the same as existing OTM or project.json reference_id
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

**🚨 CRITICAL: If import_otm() Fails**

When import fails with an error (401, 403, 400, etc.), you MUST:

✅ **DO:**
- STOP immediately - do not try again
- Report the exact error message to the user
- For 401/403 errors: Tell user the project may have pending changes in IriusRisk UI that need to be confirmed/discarded
- For 400 errors: Check OTM syntax (dataflows, component types, trust zones)
- Ask user to fix the underlying issue

❌ **NEVER DO:**
- Change the project.id and try again
- Modify the OTM file randomly hoping it will work
- Try different variations of project IDs
- Assume you can "fix" it by changing fields
- Make multiple import attempts with different IDs

**Common import failures:**
- **401 Unauthorized**: Project has uncommitted changes in IriusRisk UI, or locked/read-only
- **400 Bad Request**: OTM syntax error (dataflows using trust zone IDs, invalid component types)
- **Conflict**: Project ID mismatch between OTM and existing project

Report the error, explain what it likely means, and let the user resolve it. Do NOT attempt workarounds.

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
- User may want to complete questionnaires first for more accurate threat analysis
- User controls the pace and timing

**What to do:**
1. Summarize what was accomplished:
   - Number of components mapped
   - Trust zones used
   - Dataflows created
   - Successful import confirmation
   
2. **Present options and WAIT for user decision:**
   - **Option A:** "I can complete questionnaires to refine the threat model based on your actual implementation (RECOMMENDED - more accurate results)"
   - **Option B:** "I can download the generated threats and countermeasures now (IriusRisk may still be processing)"
   - **Option C:** "Would you like to refine the architecture before proceeding?"
   - **Option D:** "What would you like to do next?"

3. **WAIT for user response** - do not proceed automatically

**⚠️ IMPORTANT: Completing questionnaires (Option A) is RECOMMENDED before downloading threats because:**
- It makes the threat model more accurate by incorporating actual implementation details
- Reduces false positives (e.g., removes authentication threats if auth is implemented)
- Focuses threats on real gaps in security posture
- Only adds a few minutes but significantly improves quality of results

**If user chooses Option A (questionnaires):**
- Call **questionnaire_guidance()** to get detailed instructions on completing questionnaires
- This will guide you through analyzing code and answering questions to refine the threat model

### Step 8: sync() Again - Download Security Findings (ONLY When User Explicitly Requests)

**⚠️ Only proceed to this step when the user explicitly asks to download threats/countermeasures.**

When user requests, call **sync(project_path)** again to download:
- Generated threats (threats.json)
- Generated countermeasures (countermeasures.json)
- Complete threat model data

**Timing note:** If threats.json is empty after sync, IriusRisk may still be processing. Inform user to wait a minute and try again.

### Step 9: Analysis and Refinement

**After completing questionnaires (if user chose that option):**
- Threat model has been refined based on actual implementation
- False positives reduced
- Threats now focus on actual security gaps

**After downloading security data, you have two analysis tools:**

1. **questionnaire_guidance()** - For completing questionnaires (call this BEFORE downloading threats if possible):
   - Analyzes source code to answer architecture and component questions
   - Tracks questionnaire answers for sync back to IriusRisk
   - Significantly improves threat model accuracy
   - Reduces false positives

2. **threats_and_countermeasures()** - For analyzing downloaded threats:
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

**🚨 MANDATORY PRE-FLIGHT VALIDATION - DO NOT SKIP:**

**Component Type Validation (MOST COMMON FAILURE):**
- ☐ **Opened and read `.iriusrisk/components.json`**
- ☐ **For EVERY component in OTM: Searched components.json for the type**
- ☐ **For EVERY component in OTM: Verified COMPLETE referenceId exists** (not abbreviated, not invented)
- ☐ **If component type not found: Used generic alternative or asked user** (did NOT invent)

**Trust Zone Validation (SECOND MOST COMMON FAILURE):**
- ☐ **Opened and read `.iriusrisk/trust-zones.json`**
- ☐ **For EVERY trust zone in OTM: Verified exact UUID ID exists in trust-zones.json**
- ☐ **Used UUID IDs from `id` field** (not descriptive names from `name` field)
- ☐ **Did NOT invent trust zone IDs** (every ID came from the file)

**Initial Setup:**
- ☐ Used sync() first - Downloaded components.json AND trust-zones.json
- ☐ Read components.json for component type mapping (not CLI commands)
- ☐ Read trust-zones.json and identified available trust zones with their UUIDs
- ☐ If updating existing project: Read project.json or exported OTM to know existing component IDs

**OTM Structure:**
- ☐ Created OTM with ONLY architecture (no threats/controls)
- ☐ **Verified EVERY component has a parent (trustZone or component)**

**Reference Validation (CRITICAL):**
- ☐ **Verified all trust zone IDs in `parent: { trustZone: "x" }` exist in trust-zones.json**
- ☐ **Verified all component IDs in `parent: { component: "x" }` exist in the OTM's components section (defined earlier/above)**
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
- **TOP ERRORS TO AVOID (IN ORDER OF FREQUENCY):**
  1. **Inventing component types** - EVERY component type MUST exist in components.json - Open the file and verify BEFORE using!
  2. **Inventing trust zone IDs** - EVERY trust zone ID MUST exist in trust-zones.json - Open the file and verify BEFORE using!
  3. **Abbreviating component referenceIds** - Use COMPLETE string from components.json (e.g., "CD-V2-AWS-WAF-WEB-APPLICATION-FIREWALL" not "CD-V2-AWS-WAF")
  4. **Assuming components exist** - Never assume - always validate in components.json
  5. **Components without parents** - Every component MUST have trustZone or component parent
  6. **Referencing non-existent components** - All parent/dataflow component IDs must exist in OTM
  7. **Using trust zone IDs in dataflows** - Dataflows connect components only
- **MANDATORY PRE-SUBMISSION VALIDATION (DO NOT SKIP):**
  1. **Open components.json** - For EVERY component type in your OTM, search the file and verify exact referenceId exists
  2. **Open trust-zones.json** - For EVERY trust zone ID in your OTM, verify exact UUID exists in the file
  3. **If not found** - DO NOT use that component/trust zone - find alternative or ask user
  4. List all component IDs defined in your OTM
  5. Verify every parent component reference is in that list
  6. Verify every dataflow source/destination is in that list
  
**Validation is not optional - it is THE MOST CRITICAL step. 80% of OTM import failures are due to invented/invalid component types or trust zone IDs.**
