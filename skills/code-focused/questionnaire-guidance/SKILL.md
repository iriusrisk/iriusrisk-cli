---
name: questionnaire-guidance
description: Analyze source code to answer IriusRisk questionnaires that refine threat models based on actual implementation. Use after creating threat model to reduce false positives and improve accuracy. Requires thorough code analysis.
---

# Questionnaire Guidance Instructions

## 🚨 CRITICAL: Questionnaire Data Structure

**When READING questionnaires from `questionnaires.json`:**
- Use `questionnaire.groups[].questions` (groups, not steps!)
- Each group has `name` field and `questions` array

**When SUBMITTING answers:**
- Use `answers_data = {"steps": [...]}` format
- The answer payload uses "steps" but the source data uses "groups"

**Common Error**: Searching for `.steps[]` in questionnaires.json will find nothing. Use `.groups[]` instead.

## Executive Summary

After creating a threat model in IriusRisk, questionnaires help refine the threat analysis based on actual implementation details. Your role: analyze source code to answer project and component questionnaires, then sync those answers back to IriusRisk to regenerate an improved threat model.

**🚨 FIRST STEP: Check for repository scope in `.iriusrisk/project.json`**
- If scope is defined → ONLY answer questionnaires relevant to this repository's scope
- If no scope or general scope → Answer all questionnaires

**Standard workflow:** 
1. Import OTM → project_status() → **Offer to complete questionnaires**
2. If accepted: sync() to download questionnaires → **check scope** → analyze code for relevant components → track answers → sync() to push answers
3. IriusRisk rules engine regenerates threat model based on answers

## Why Questionnaires Matter

**Before questionnaires:** IriusRisk generates threats based only on component types (e.g., "Database" → generic database threats)

**After questionnaires:** IriusRisk generates threats based on actual implementation:
- Is authentication implemented? → Removes unauthenticated access threats
- Is TLS enabled? → Removes plaintext communication threats  
- Is input validation present? → Removes certain injection threats
- What data is stored? → Adjusts data protection requirements

**Result:** More accurate threat model with fewer false positives and threats focused on actual risks.

## Scope-Based Questionnaire Filtering

**CRITICAL for Multi-Repository Projects**: Check for repository scope in `.iriusrisk/project.json` BEFORE answering questionnaires.

### When Scope is Defined

**Only answer questionnaires relevant to this repository's scope.**

**Infrastructure Scope** ("AWS infrastructure - ECS, RDS, VPC"):
- ✅ **Answer**: Component questionnaires for infrastructure components (RDS, ECS, VPC, etc.)
- ✅ **Answer**: Project questions about infrastructure
- ❌ **Skip**: Application-level questions (e.g., "Is input validation implemented?")
- ❌ **Skip**: Component questionnaires for application components you don't control

**Application Scope** ("Backend API services"):
- ✅ **Answer**: Component questionnaires for API/service components
- ✅ **Answer**: Project questions about authentication, authorization, business logic
- ❌ **Skip**: Infrastructure questions (e.g., "Is RDS encrypted?")
- ❌ **Skip**: Frontend questions

**Frontend Scope** ("React SPA"):
- ✅ **Answer**: Component questionnaires for frontend components
- ✅ **Answer**: Questions about client-side security, XSS protection
- ❌ **Skip**: Backend API implementation questions
- ❌ **Skip**: Infrastructure/database questions

## Available Questionnaires

### 1. Project Questionnaire (Architecture-level)
Located in `.iriusrisk/questionnaires.json` under `project` key.

**Common questions:**
- Does the application implement authentication?
- Is HTTPS/TLS used for all communications?
- Is there logging and monitoring?
- Are there data protection measures?

**Impact:** Affects threats across ALL components in the project.

### 2. Component Questionnaires
Located in `.iriusrisk/questionnaires.json` under `components` array.

**Each component may have specific questions like:**
- Database: Is encryption at rest enabled? Are backups automated?
- Web Service: Is input validation implemented? Is rate limiting in place?
- API: Is authentication required for all endpoints?

**Impact:** Affects threats for that specific component only.

## Workflow: Complete Questionnaires

### Step 1: Offer to Complete Questionnaires (After Import)

After successfully importing an OTM and checking project status, **always offer the user the option to complete questionnaires:**

```
Your threat model has been created successfully! 

To get more accurate threat analysis based on your actual implementation, 
I can analyze your source code and answer the questionnaires that IriusRisk 
uses to refine the threat model.

This typically results in:
- Fewer false positive threats
- More targeted security recommendations  
- Better alignment with your actual architecture

Would you like me to:
A) Complete the questionnaires now (analyzes your codebase)
B) Skip for now (you can do this later)

What would you prefer?
```

**DO NOT automatically complete questionnaires** - always ask the user first.

### Step 2: Download Questionnaires (If User Accepts)

Call **sync(project_path)** to download:
- Project questionnaire
- Component questionnaires for all components in the threat model
- Saved to `.iriusrisk/questionnaires.json`

### Step 3: Read and Summarize Questionnaires

Read `.iriusrisk/questionnaires.json` and provide a summary.

**🚨 CRITICAL: Questionnaire JSON Structure**

The questionnaire data uses **"groups"** not "steps":

```python
# CORRECT way to iterate through questions
for group in questionnaire_data['questionnaire']['groups']:
    group_name = group['name']
    for question in group['questions']:
        question_text = question['text']
        question_ref = question['referenceId']
```

### Step 4: Analyze Source Code to Determine Answers

**CRITICAL: You MUST analyze the actual source code to determine truthful answers.**

**For each question:**
1. Identify what code/configuration would indicate "yes" vs "no"
2. Search the codebase for relevant files, patterns, libraries
3. Make an evidence-based determination
4. Document your reasoning in the context field

**Example analysis for "Does the application implement authentication?":**

```python
# Search for authentication-related code
# Check for: auth middleware, JWT usage, session management, login endpoints

# Example findings:
# - Found authentication middleware in src/middleware/auth.py
# - JWT tokens used for API authentication
# - Login endpoint at POST /api/auth/login
# → ANSWER: YES (has-authentication-yes)
```

**DO NOT:**
- Guess or assume answers without checking code
- Answer "yes" to make the user feel good
- Answer "no" conservatively without checking
- Skip questions because they seem hard

**DO:**
- Search files for relevant patterns
- Check for libraries/frameworks that provide features
- Look at configuration files
- Examine infrastructure as code
- If uncertain after thorough analysis, explain to user and ask

### Step 5: Track Answers Using Update Tracker

For project questionnaire answers, use **track_project_questionnaire_update()**:

```python
project_id = "12345678-1234-1234-1234-123456789012"

answers_data = {
    "steps": [
        {
            "questions": [
                {
                    "referenceId": "has-authentication",
                    "answers": [
                        {
                            "referenceId": "has-authentication-yes",
                            "value": "true"  # or "false"
                        }
                    ]
                }
            ]
        }
    ]
}

context = """Analyzed codebase:
- Authentication: Found JWT-based auth in src/middleware/auth.py
- TLS: HTTPS enforced in nginx.conf
"""

track_project_questionnaire_update(
    project_id=project_id,
    answers_data=answers_data,
    project_path="/absolute/path/to/project",
    context=context
)
```

For component questionnaire answers, use **track_component_questionnaire_update()**.

**CRITICAL:** You can answer MULTIPLE questions in a single call by including multiple question objects in the `questions` array.

### Step 6: Sync to Push Answers (IMMEDIATE)

**After tracking answers, IMMEDIATELY call sync() without asking permission:**

```python
sync(project_path="/absolute/path/to/project")
```

**What happens:**
1. Sync pushes all questionnaire answers to IriusRisk
2. IriusRisk rules engine regenerates threat model
3. Threats are updated based on actual implementation
4. Updated threats/countermeasures are downloaded

**DO NOT:**
- Ask user permission to sync (just do it)
- Wait to batch with other operations
- Skip sync and leave answers pending

## Common Question Patterns and Analysis Approaches

### Authentication Questions

**Question:** "Does the application implement authentication?"

**Analysis approach:**
```bash
# Search for common auth patterns
grep -r "authenticate\|login\|jwt\|session" src/
grep -r "@require_auth\|@login_required" src/
grep "jsonwebtoken\|passport\|express-session" package.json
```

**Answer YES if:** Auth middleware exists, JWT/session tokens used, protected routes, login endpoints
**Answer NO if:** No auth code found, all routes publicly accessible

### Encryption/TLS Questions

**Question:** "Is TLS/HTTPS used for communications?"

**Analysis approach:**
```bash
# Check server config
grep -r "https:\|ssl\|tls\|certificate" nginx.conf docker-compose.yml

# Check API clients
grep -r "https://\|ssl.*true" src/

# Check environment configs
grep "SSL\|TLS\|HTTPS" .env*
```

**Answer YES if:** HTTPS URLs in config, SSL certificates configured, TLS enabled
**Answer NO if:** HTTP URLs only, no SSL config

### Input Validation Questions

**Question:** "Is input validation implemented?"

**Analysis approach:**
```bash
# Search for validation
grep -r "validate\|sanitize\|validator" src/

# Check for validation libraries
grep "joi\|yup\|express-validator\|pydantic" package.json requirements.txt

# Look for validation decorators
grep -r "@Valid\|@validated" src/
```

**Answer YES if:** Validation library used, validation on input endpoints
**Answer NO if:** No validation code, raw input used directly

### Database Security Questions

**Question:** "Is database encryption at rest enabled?"

**Analysis approach:**
```bash
# Check database config
grep -r "encrypt.*rest\|storage.*encrypt" terraform/

# Check cloud provider configs
grep "StorageEncrypted\|encrypted\|kms" terraform/

# Check database.yml
grep "encrypt\|ssl" config/database.yml
```

**Answer YES if:** Encryption flag set in IaC, KMS keys configured
**Answer NO if:** No encryption config found

## Best Practices

**DO:**
- ✅ Analyze actual code before answering
- ✅ Document your findings in context field
- ✅ Batch multiple questions in single API calls
- ✅ Sync immediately after tracking answers
- ✅ Explain to user what changed in threat model
- ✅ Be honest if you're uncertain

**DO NOT:**
- ❌ Guess answers without checking code
- ❌ Answer all "yes" to be optimistic
- ❌ Skip questions that seem hard
- ❌ Forget to sync after tracking answers
- ❌ Leave questionnaires incomplete

## Summary Checklist

When completing questionnaires:
- ☐ Offer to complete questionnaires after OTM import
- ☐ If accepted, sync() to download questionnaires
- ☐ Read questionnaires.json and summarize for user
- ☐ Analyze source code to determine truthful answers
- ☐ Track project questionnaire answers with context
- ☐ Track component questionnaire answers with context
- ☐ Immediately sync() to push answers (don't ask permission)
- ☐ Inform user of results and threat model changes
- ☐ Offer next steps (review threats, implement countermeasures)

Your goal: Make the threat model as accurate as possible by providing evidence-based questionnaire answers derived from actual code analysis.
