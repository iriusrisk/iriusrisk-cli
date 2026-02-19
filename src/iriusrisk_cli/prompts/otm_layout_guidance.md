# OTM Layout and Positioning Guidance for AI Assistants

## When to Use This Tool

Call this tool when you need detailed guidance on:
- **Preserving layout** when updating existing threat models
- Positioning components in OTM diagrams
- Calculating parent container sizes
- Understanding the OTM representations schema

## ⚠️ CRITICAL: For NEW Threat Models, Do NOT Include Representations

**When creating a new threat model from scratch:**
- **Do NOT add `representations`** to components, trust zones, or dataflows
- **Do NOT add a top-level `representations` section**
- IriusRisk will automatically generate a clean diagram layout after import
- This avoids common schema validation errors

**Only include representations when UPDATING an existing model that already has them.**

## OTM Representations Schema (Required Structure When Updating)

If you DO need to include representations (for updates where the existing OTM has them),
you MUST follow this exact structure. Getting this wrong causes validation failures.

### Top-Level `representations` Section (REQUIRED if any component has representations)

You MUST define a top-level `representations` array that component-level entries reference:

```yaml
representations:
  - name: "Diagram Representation"
    id: "diagram-1"
    type: "diagram"
    size:
      width: 1000
      height: 800
```

### Component-Level `representations` (references top-level)

Each component's `representations` is an **array** (plural `representations:`, NOT singular `representation:`).
Each item in the array MUST have these two required fields:
- `representation`: A **string** referencing the `id` of a top-level representation (e.g., `"diagram-1"`)
- `id`: A unique element ID for this representation entry

Optional fields: `position` (with `x` and `y`), `size` (with `width` and `height`)

```yaml
components:
  - id: "ecs-cluster"
    name: "ECS Cluster"
    type: "CD-V2-AWS-ECS-CLUSTER"
    parent:
      trustZone: "b61d6911-338d-46a8-9f39-8dcd24abfe91"
    representations:
      - representation: "diagram-1"      # REQUIRED: references top-level representation id
        id: "ecs-cluster-diagram"         # REQUIRED: unique element id
        position: {x: 160, y: 160}
        size: {width: 300, height: 200}
```

### ❌ WRONG Structure (Common Mistakes That Cause Validation Failures)

```yaml
# ❌ WRONG - Using singular "representation:" as a direct object property
- id: "ecs-cluster"
  representation:
    position: {x: 160, y: 160}
    size: {width: 165, height: 165}

# ❌ WRONG - Missing required "representation" reference field
- id: "ecs-cluster"
  representations:
    - id: "ecs-cluster-diagram"
      position: {x: 160, y: 160}
      size: {width: 165, height: 165}
      # Missing: representation: "diagram-1"

# ❌ WRONG - Missing required "id" field
- id: "ecs-cluster"
  representations:
    - representation: "diagram-1"
      position: {x: 160, y: 160}
      size: {width: 165, height: 165}
      # Missing: id: "ecs-cluster-diagram"

# ❌ WRONG - No top-level representations section defined
# (component representations reference a top-level representation that doesn't exist)
components:
  - id: "ecs-cluster"
    representations:
      - representation: "diagram-1"  # This ID must exist in top-level representations!
        id: "ecs-cluster-diagram"
```

## Layout for New vs Updating

### For NEW Threat Models

**Do NOT include representations.** IriusRisk auto-layouts new models.

Simply create components with correct parent relationships and IriusRisk
will generate the diagram layout automatically. This is the recommended approach
for initial threat models — it avoids schema validation errors and produces
a clean diagram.

### For UPDATES (Existing layout present)

**🚨 CRITICAL: sync() BEFORE reading existing layout.**
Users frequently adjust component positions and sizes in the IriusRisk web interface. A local `current-threat-model.otm` file may contain outdated layout that does NOT reflect changes made in the UI. You MUST call sync() to download the latest OTM before reading or preserving any layout data — even if the file already exists locally.

**Preserve existing layout (from freshly synced OTM):**
- Keep existing component positions (x, y)
- Keep existing component sizes (width, height)
- Add new components with calculated positions that fit
- Recalculate parent container sizes when adding children
- Copy the top-level `representations` section from the existing OTM

## Component Sizes

**Standard sizes:**
- **Leaf components** (services, databases, APIs): 85x85 pixels
- **Container components** (infrastructure): Calculated from children (see algorithm below)

## Spacing Guidelines

- **Minimum spacing** between unrelated components: 50 pixels
- **Comfortable spacing**: 80-100 pixels
- **Visual grouping**: Related components can be closer (30-40 pixels)
- **Padding inside containers**: 30-40 pixels from parent edges

## Cascading Size Calculation Algorithm

**When adding components to nested hierarchies, recalculate sizes bottom-up:**

### Algorithm (work from leaf nodes up to root):

**Step 1: Identify leaf components** (no children):
- Set size to 85x85 pixels

**Step 2: For each parent component** (contains other components):
```
child_area_width = max(child.x + child.width) - min(child.x)
child_area_height = max(child.y + child.height) - min(child.y)

parent.width = child_area_width + (2 * 40)  # 40px padding
parent.height = child_area_height + (2 * 40)

# Minimum size for containers
parent.width = max(parent.width, 200)
parent.height = max(parent.height, 200)
```

**Step 3: Repeat for each level** moving up the hierarchy

## Layout Patterns

**Remember:** These patterns are for UPDATES only. For new models, omit representations entirely.

### Pattern A: Adding Infrastructure Around Applications

```yaml
# Top-level representations section (copy from existing OTM):
representations:
  - name: "Diagram Representation"
    id: "diagram-1"
    type: "diagram"
    size: {width: 1000, height: 800}

# Existing: API service at x:200, y:200, size 85x85
# Adding: ECS cluster to contain it

# Calculate ECS cluster:
# Child occupies x:200-285, y:200-285
# Add padding: 85 + (2*40) = 165x165
# Position 40px left/above: x:160, y:160

components:
  - id: "ecs-cluster"
    name: "ECS Cluster"
    type: "CD-V2-AWS-ECS-CLUSTER"
    parent:
      trustZone: "b61d6911-338d-46a8-9f39-8dcd24abfe91"
    representations:
      - representation: "diagram-1"
        id: "ecs-cluster-diagram"
        position: {x: 160, y: 160}
        size: {width: 165, height: 165}

  - id: "api-service"
    name: "API Service"
    type: "CD-V2-RESTFUL-WEB-SERVICE"
    parent:
      component: "ecs-cluster"
    representations:
      - representation: "diagram-1"
        id: "api-service-diagram"
        position: {x: 200, y: 200}  # Original preserved
        size: {width: 85, height: 85}
```

### Pattern B: Adding Peer Services Inside Container

```yaml
# Top-level representations section must exist (copy from existing OTM)

# Existing: auth-service at x:200, y:200 in ecs-cluster
# Adding: payment-service alongside

components:
  - id: "payment-service"
    name: "Payment Service"
    type: "CD-V2-WEB-SERVICE"
    parent:
      component: "ecs-cluster"
    representations:
      - representation: "diagram-1"
        id: "payment-service-diagram"
        position: {x: 335, y: 200}  # 200 + 85 + 50
        size: {width: 85, height: 85}

# Recalculate parent:
# Children occupy x:200-420, y:200-285
# Child area: 220x85
# Add padding: 300x165
  - id: "ecs-cluster"
    representations:
      - representation: "diagram-1"
        id: "ecs-cluster-diagram"
        position: {x: 160, y: 160}
        size: {width: 300, height: 200}  # RECALCULATED
```

### Pattern C: Adding Load Balancer (Peer Component)

```yaml
# Top-level representations section must exist (copy from existing OTM)

# Existing: backend at x:300, y:200
# Adding: ALB upstream

components:
  - id: "alb"
    name: "Application Load Balancer"
    type: "CD-V2-AWS-APPLICATION-LOAD-BALANCER"
    parent:
      trustZone: "b61d6911-338d-46a8-9f39-8dcd24abfe91"
    representations:
      - representation: "diagram-1"
        id: "alb-diagram"
        position: {x: 150, y: 200}  # To the left
        size: {width: 85, height: 85}

  - id: "backend"
    name: "Backend Service"
    type: "CD-V2-RESTFUL-WEB-SERVICE"
    parent:
      trustZone: "b61d6911-338d-46a8-9f39-8dcd24abfe91"
    representations:
      - representation: "diagram-1"
        id: "backend-diagram"
        position: {x: 300, y: 200}  # Original preserved
        size: {width: 85, height: 85}
```

## Layout Reset Option

If `reset_layout=True` or `auto_reset_layout: true` in config:
- **DO NOT** calculate positions
- **DO NOT** include `representations` sections
- Backend strips all layout data
- IriusRisk auto-layouts from scratch

## Key Rules

**DO:**
- ✅ Omit representations entirely for new threat models (let IriusRisk auto-layout)
- ✅ Preserve existing representations structure when updating
- ✅ Always include top-level `representations` section when using component-level representations
- ✅ Always include both `representation` (reference string) and `id` fields in each representation element
- ✅ Calculate container sizes from children (bottom-up)
- ✅ Add 40px padding around children
- ✅ Use 85x85 for leaf components
- ✅ Recalculate ALL ancestors when adding to nested hierarchy

**DON'T:**
- ❌ Add representations to new threat models (let IriusRisk auto-layout)
- ❌ Use singular `representation:` as a direct property (must be `representations:` array)
- ❌ Omit the `representation` or `id` fields from representation elements
- ❌ Omit the top-level `representations` section when components have representations
- ❌ Use fixed sizes for containers
- ❌ Forget to recalculate parent sizes
- ❌ Overlap components (unless parent/child)
- ❌ Place at x:0, y:0 unless intentional
- ❌ Stop at one level - cascade up entire tree
