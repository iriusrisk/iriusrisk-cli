# Questionnaire Prompts Update Summary

## Overview

Updated MCP prompts to guide AI assistants through the questionnaire completion workflow. This ensures AI can effectively analyze source code, answer questionnaires, and refine threat models based on actual implementation details.

## Files Created

### 1. **questionnaire_guidance.md** (NEW)
**Location:** `src/iriusrisk_cli/prompts/questionnaire_guidance.md`

**Purpose:** Comprehensive guide for AI assistants on completing questionnaires.

**Key Sections:**
- **Executive Summary**: Overview of questionnaire purpose and workflow
- **Why Questionnaires Matter**: Explains the value proposition (fewer false positives, more accurate threats)
- **Available Questionnaires**: Project-level and component-level questionnaires
- **Workflow Steps**:
  1. Offer to complete questionnaires (after OTM import)
  2. Download questionnaires via sync()
  3. Read and summarize questionnaires.json
  4. Analyze source code to determine truthful answers
  5. Track answers using update tracker
  6. Sync to push answers (immediate, no permission needed)
  7. Inform user of results
- **Common Question Patterns**: Authentication, encryption, input validation, logging, database security
- **Code Analysis Examples**: Specific grep commands and analysis approaches for each question type
- **Answer Data Structure**: Detailed examples of how to format questionnaire answers
- **Error Handling**: What to do when answers are uncertain
- **Integration with Threat Analysis**: How to show before/after improvements

**Key Messages to AI:**
- ✅ Always offer questionnaires after OTM import (but don't force it)
- ✅ Analyze actual code before answering (don't guess)
- ✅ Document findings in context field
- ✅ Batch multiple questions in single API calls
- ✅ Sync immediately after tracking (don't ask permission)
- ❌ Never guess without code analysis
- ❌ Never answer optimistically without evidence

## Files Modified

### 2. **create_threat_model.md** (UPDATED)
**Location:** `src/iriusrisk_cli/prompts/create_threat_model.md`

**Changes:**

#### Step 7: Present Results & Offer Options
**Before:**
- Simple options: download threats, refine architecture, or ask what's next

**After:**
- **Option A (NEW):** Complete questionnaires to refine threat model (RECOMMENDED)
- Explains why questionnaires are valuable (fewer false positives, more accurate)
- Added note: "If user chooses Option A, call questionnaire_guidance() for instructions"

#### Step 9: Analysis Guidance
**Before:**
- Only mentioned `threats_and_countermeasures()` tool

**After:**
- Renamed to "Analysis and Refinement"
- Added `questionnaire_guidance()` as the FIRST analysis tool (before downloading threats)
- Clarified that questionnaires should ideally be completed BEFORE downloading threats
- Kept `threats_and_countermeasures()` for analyzing downloaded threats

**Key Change:** Made questionnaires a prominent, recommended step in the workflow rather than an afterthought.

### 3. **threats_and_countermeasures.md** (UPDATED)
**Location:** `src/iriusrisk_cli/prompts/threats_and_countermeasures.md`

**Changes:**

#### Executive Summary
**Added:**
- Warning box at the top about questionnaires
- "If questionnaires have NOT been completed yet, recommend completing them BEFORE analyzing threats"
- Explains benefits: fewer false positives, more accurate threats
- Points to `questionnaire_guidance()` tool

**Key Change:** Ensures AI prompts user to complete questionnaires even if they skipped that step initially.

### 4. **mcp.py** (UPDATED)
**Location:** `src/iriusrisk_cli/commands/mcp.py`

**Changes:**

#### Added questionnaire_guidance() MCP Tool
**Location:** After `threats_and_countermeasures()` tool (around line 779)

**Implementation:**
```python
@mcp_server.tool()
async def questionnaire_guidance() -> str:
    """Get comprehensive instructions for completing questionnaires.
    
    This tool provides detailed guidance for AI assistants on how to analyze source code
    and complete project and component questionnaires. Questionnaires help IriusRisk
    refine the threat model based on actual implementation details.
    
    Returns:
        Detailed instructions for questionnaire completion workflow.
    """
    logger.info("Providing questionnaire guidance instructions via MCP")
    instructions = _load_prompt("questionnaire_guidance")
    logger.info("Provided questionnaire guidance instructions to AI assistant")
    return _apply_prompt_customizations('questionnaire_guidance', instructions)
```

**Key Features:**
- Loads the comprehensive questionnaire_guidance.md prompt
- Supports prompt customizations via project.json
- Provides logging for debugging

## Workflow Integration

### Complete User Journey

**Before (Old Workflow):**
1. Import OTM → project_status()
2. Present options → user chooses download threats
3. Sync to download threats
4. Analyze threats (may have many false positives)
5. (Questionnaires never mentioned or completed)

**After (New Workflow):**
1. Import OTM → project_status()
2. **Present options → RECOMMEND completing questionnaires first**
3. If user accepts questionnaires:
   a. Call `questionnaire_guidance()` for instructions
   b. Sync to download questionnaires
   c. Analyze code to answer questions
   d. Track answers with `track_project_questionnaire_update()` and `track_component_questionnaire_update()`
   e. Sync to push answers (triggers threat regeneration)
4. Download threats (now more accurate with fewer false positives)
5. Analyze refined threat model

### Key Decision Points for AI

**After OTM Import:**
```
✅ Threat model created successfully!

To get more accurate results, I recommend completing questionnaires first.
This analyzes your actual implementation and reduces false positives.

Would you like me to:
A) Complete questionnaires now (RECOMMENDED - 5-10 minutes)
B) Download threats now (may have false positives)
C) Refine architecture first
```

**If User Skips Questionnaires and Views Threats:**
```
⚠️ Note: I notice questionnaires haven't been completed yet.

Completing them would:
- Remove threats that don't apply to your implementation
- Adjust risk ratings based on existing controls
- Focus on actual security gaps

Would you like me to complete them now? It only takes a few minutes 
and significantly improves threat accuracy.
```

## Benefits of This Update

### For Users
- **More Accurate Threat Models**: Questionnaires are now a prominent, recommended step
- **Fewer False Positives**: Threats adjusted based on actual implementation
- **Better Prioritization**: Focus on real security gaps, not theoretical risks
- **Time Savings**: Less time filtering irrelevant threats

### For AI Assistants
- **Clear Guidance**: Comprehensive instructions on completing questionnaires
- **Code Analysis Patterns**: Specific grep commands and analysis approaches
- **Error Handling**: What to do when uncertain
- **Integration Points**: Clear workflow integration at multiple decision points

### For Workflow
- **Proactive Recommendations**: AI actively recommends questionnaires at appropriate times
- **Seamless Integration**: Questionnaires fit naturally into create → refine → analyze flow
- **Multiple Entry Points**: Can complete questionnaires at creation, before threat analysis, or after

## Testing Checklist

To verify the implementation works:

- [ ] Create a new threat model
- [ ] Verify AI offers questionnaire completion as Option A (recommended)
- [ ] If accepted, verify AI calls `questionnaire_guidance()`
- [ ] Verify AI syncs to download questionnaires
- [ ] Verify AI analyzes code and tracks answers
- [ ] Verify AI immediately syncs to push answers (without asking)
- [ ] Verify threat model is updated with refined threats
- [ ] If user skips initially, verify AI recommends questionnaires when viewing threats
- [ ] Verify all MCP tools work: `track_project_questionnaire_update()`, `track_component_questionnaire_update()`

## Example AI Conversation Flow

```
USER: Create a threat model for my project

AI: [Imports OTM successfully]
    ✅ Threat model created with 15 components!
    
    To get more accurate results, I recommend completing questionnaires 
    to refine the threat model based on your actual implementation.
    
    Would you like me to:
    A) Complete questionnaires now (RECOMMENDED)
    B) Download threats now
    C) Refine architecture first

USER: Yes, do A

AI: [Calls questionnaire_guidance()]
    [Syncs to download questionnaires]
    
    I found questionnaires to complete:
    
    Project-level (5 questions):
    - Authentication implementation
    - TLS/HTTPS usage
    - Logging and monitoring
    
    Component-level:
    - User Database (3 questions)
    - API Service (4 questions)
    
    Analyzing your source code now...
    
    [Analyzes code]
    [Tracks answers]
    [Syncs to push answers]
    
    ✅ Questionnaires completed!
    
    IriusRisk has regenerated your threat model based on your 
    actual implementation. The updated model should now:
    - Remove 12 authentication threats (auth is implemented)
    - Remove 8 encryption threats (TLS is enabled)
    - Focus on actual security gaps
    
    Would you like me to show you the updated threats?
```

## Summary

This update transforms questionnaires from an obscure optional feature into a **prominent, recommended step** in the threat modeling workflow. AI assistants now:

1. **Proactively recommend** questionnaires after OTM import
2. **Have clear guidance** on analyzing code and answering questions
3. **Seamlessly integrate** questionnaire completion into the workflow
4. **Remind users** if they skip questionnaires initially

The result is more accurate threat models with fewer false positives and better focus on actual security risks.

