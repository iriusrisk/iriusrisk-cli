# Architecture and Design Review - Trigger Point

You've been asked to review architecture, design, or system structure.

## NEXT STEP: Call initialize_iriusrisk_workflow()

**Immediately call:**
```
initialize_iriusrisk_workflow()
```

That tool contains all the instructions for:
- How to check for existing threat model data
- Whether to use existing threat model or recommend creating one
- When to ask user permission vs. using automatically
- Complete workflow with proper sync() → check → decide → act

## Why?

The workflow tool has the complete decision logic for:
- Using existing threat models automatically (user's own work)
- Assessing user intent (security vs. general architecture request)
- Asking permission appropriately before creating new threat models
- Providing value regardless of user choice

## Remember

This tool is just a **trigger**. Don't try to replicate the workflow logic here. 
Call `initialize_iriusrisk_workflow()` immediately to get the full instructions.