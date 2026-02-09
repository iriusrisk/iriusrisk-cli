# OTM Layout and Positioning Guidance for AI Assistants

## When to Use This Tool

Call this tool when you need detailed guidance on:
- **Creating initial layout** from scratch (new threat models)
- Positioning components in OTM diagrams
- Calculating parent container sizes
- Preserving existing layout when updating
- Handling nested component hierarchies

## Layout for New vs Updating

### For NEW Threat Models

**Create simple, organized layout:**
- Start external components at left (x: 100-300)
- Flow left-to-right (users → load balancer → services → databases)
- Use consistent spacing (80-100px between components)
- Group related components vertically
- Leaf components: 85x85 pixels
- Calculate container sizes from children

### For UPDATES (Existing layout present)

**Preserve existing layout:**
- Keep existing component positions (x, y)
- Keep existing component sizes (width, height)
- Add new components with calculated positions that fit
- Recalculate parent container sizes when adding children

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

### Pattern A: Adding Infrastructure Around Applications

```yaml
# Existing: API service at x:200, y:200, size 85x85
# Adding: ECS cluster to contain it

# Calculate ECS cluster:
# Child occupies x:200-285, y:200-285
# Add padding: 85 + (2*40) = 165x165
# Position 40px left/above: x:160, y:160

- id: "ecs-cluster"
  representation:
    position: {x: 160, y: 160}
    size: {width: 165, height: 165}

- id: "api-service"
  parent: {component: "ecs-cluster"}
  representation:
    position: {x: 200, y: 200}  # Original preserved
    size: {width: 85, height: 85}
```

### Pattern B: Adding Peer Services Inside Container

```yaml
# Existing: auth-service at x:200, y:200 in ecs-cluster
# Adding: payment-service alongside

- id: "payment-service"
  parent: {component: "ecs-cluster"}
  representation:
    position: {x: 335, y: 200}  # 200 + 85 + 50
    size: {width: 85, height: 85}

# Recalculate parent:
# Children occupy x:200-420, y:200-285
# Child area: 220x85
# Add padding: 300x165
- id: "ecs-cluster"
  representation:
    position: {x: 160, y: 160}
    size: {width: 300, height: 200}  # RECALCULATED
```

### Pattern C: Adding Load Balancer (Peer Component)

```yaml
# Existing: backend at x:300, y:200
# Adding: ALB upstream

- id: "alb"
  representation:
    position: {x: 150, y: 200}  # To the left
    size: {width: 85, height: 85}

- id: "backend"
  representation:
    position: {x: 300, y: 200}  # Original preserved
    size: {width: 85, height: 85}
```

## Layout Reset Option

If `reset_layout=True` or `auto_reset_layout: true` in config:
- **DO NOT** calculate positions
- **DO NOT** include `representation` sections
- Backend strips all layout data
- IriusRisk auto-layouts from scratch

## Key Rules

**DO:**
- ✅ Calculate container sizes from children (bottom-up)
- ✅ Preserve existing positions when updating
- ✅ Add 40px padding around children
- ✅ Use 85x85 for leaf components
- ✅ Recalculate ALL ancestors when adding to nested hierarchy

**DON'T:**
- ❌ Use fixed sizes for containers
- ❌ Forget to recalculate parent sizes
- ❌ Overlap components (unless parent/child)
- ❌ Place at x:0, y:0 unless intentional
- ❌ Stop at one level - cascade up entire tree
