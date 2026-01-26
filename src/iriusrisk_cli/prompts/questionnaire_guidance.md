# Questionnaire Guidance Instructions for AI Assistants

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
- See "Scope-Based Questionnaire Filtering" section below for guidance

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

```python
# Read scope from project.json
import json
with open('.iriusrisk/project.json', 'r') as f:
    project_config = json.load(f)
    scope = project_config.get('scope')
```

### When Scope is Defined

**Only answer questionnaires relevant to this repository's scope.**

**Infrastructure Scope** ("AWS infrastructure - ECS, RDS, VPC"):
- ✅ **Answer**: Component questionnaires for infrastructure components (RDS, ECS, VPC, etc.)
- ✅ **Answer**: Project questions about infrastructure (e.g., "Is infrastructure as code used?", "Are security groups configured?")
- ❌ **Skip**: Application-level questions (e.g., "Is input validation implemented?", "Is CSRF protection enabled?")
- ❌ **Skip**: Component questionnaires for application components you don't control

**Application Scope** ("Backend API services"):
- ✅ **Answer**: Component questionnaires for API/service components
- ✅ **Answer**: Project questions about authentication, authorization, business logic
- ❌ **Skip**: Infrastructure questions (e.g., "Is RDS encrypted?", "Are VPCs isolated?")
- ❌ **Skip**: Frontend questions (e.g., "Is Content Security Policy enabled?")

**Frontend Scope** ("React SPA"):
- ✅ **Answer**: Component questionnaires for frontend components
- ✅ **Answer**: Questions about client-side security, XSS protection, secure storage
- ❌ **Skip**: Backend API implementation questions
- ❌ **Skip**: Infrastructure/database questions

**When presenting questionnaires:**
```
Repository scope: "Backend API services and business logic"

Found 15 questionnaire questions total. Filtering to 8 questions relevant to this scope:

Project Questions (3):
- Does the application implement authentication? 
- Is input validation performed on all user inputs?
- Are API endpoints documented?

Component Questions (5):
- API Service: Is rate limiting implemented?
- Auth Service: Are passwords hashed with strong algorithms?
...

Note: Skipped 7 infrastructure-related questions not relevant to this repository.
```

### When Scope is NOT Defined

**No scope** or general scope:
- Answer ALL questionnaires
- No filtering needed
- Standard behavior

## Available Questionnaires

### 1. Project Questionnaire (Architecture-level)
Located in `.iriusrisk/questionnaires.json` under `project` key.

**Common questions:**
- Does the application implement authentication?
- Is HTTPS/TLS used for all communications?
- Is there logging and monitoring?
- Are there data protection measures?
- Is there an incident response plan?

**Impact:** Affects threats across ALL components in the project.

**Scope filtering**: In multi-repo projects, only answer if question relates to your scope.

### 2. Component Questionnaires
Located in `.iriusrisk/questionnaires.json` under `components` array.

**Each component may have specific questions like:**
- Database: Is encryption at rest enabled? Are backups automated?
- Web Service: Is input validation implemented? Is rate limiting in place?
- API: Is authentication required for all endpoints? Is there API documentation?

**Impact:** Affects threats for that specific component only.

**Scope filtering**: Only answer questionnaires for components in your repository's scope.

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

The questionnaire data downloaded from IriusRisk uses **"groups"** not "steps":
- ✅ `questionnaire.groups[].questions` (CORRECT - for reading questionnaires)
- ❌ `questionnaire.steps[].questions` (WRONG - will find nothing)

**When READING questionnaires** from `questionnaires.json`:
```python
# CORRECT way to iterate through questions
for group in questionnaire_data['questionnaire']['groups']:
    group_name = group['name']
    for question in group['questions']:
        question_text = question['text']
        question_ref = question['referenceId']
        # Process question...
```

**When SUBMITTING answers** (answer format uses "steps"):
```python
# Answer format for API uses "steps" not "groups"
answers_data = {
    "steps": [  # ← Uses "steps" for answers
        {
            "questions": [...]
        }
    ]
}
```

**Summary:**
- **Reading** questionnaires: `groups` → `questions`
- **Submitting** answers: `steps` → `questions`

When parsing questionnaires to find questions, use:

```json
{
  "metadata": {
    "project_id": "uuid",
    "data_type": "questionnaires",
    "component_count": 5
  },
  "project": {
    "projectId": "uuid",
    "questionnaire": {
      "ref": "project-questionnaire",
      "groups": [
        {
          "name": "Architecture Questions",
          "questions": [
            {
              "referenceId": "has-authentication",
              "text": "Does the application implement authentication?",
              "answers": [
                {
                  "referenceId": "has-authentication-yes",
                  "text": "Yes",
                  "selected": false
                },
                {
                  "referenceId": "has-authentication-no",
                  "text": "No",
                  "selected": false
                }
              ]
            }
          ]
        }
      ]
    }
  },
  "components": [
    {
      "componentId": "uuid",
      "componentName": "User Database",
      "questionnaire": {
        "ref": "database-questionnaire",
        "groups": [
          {
            "name": "Database Security",
            "questions": [
              {
                "referenceId": "db-encryption-at-rest",
                "text": "Is encryption at rest enabled?",
                "answers": [
                  {
                    "referenceId": "db-encryption-yes",
                    "text": "Yes",
                    "selected": false
                  }
                ]
              }
            ]
          }
        ]
      }
    }
  ]
}
```

**Provide a summary like:**
```
I found questionnaires to complete:

Project-level (5 questions):
- Authentication implementation
- TLS/HTTPS usage
- Logging and monitoring
- Data protection measures
- Incident response

Component-level:
- User Database (3 questions): encryption, backups, access controls
- API Service (4 questions): authentication, rate limiting, input validation
- Web Application (6 questions): session management, XSS protection, CSRF tokens

I'll analyze your source code to answer these. This will take a moment...
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
# - Protected routes require authentication
# → ANSWER: YES (has-authentication-yes)
```

**DO NOT:**
- Guess or assume answers without checking code
- Answer "yes" to make the user feel good
- Answer "no" conservatively without checking
- Skip questions because they seem hard

**DO:**
- Search files for relevant patterns (grep, file reads)
- Check for libraries/frameworks that provide features
- Look at configuration files (nginx, docker-compose, etc.)
- Examine infrastructure as code (terraform, cloudformation)
- If truly uncertain after thorough analysis, explain to user and ask

### Step 5: Track Answers Using Update Tracker

For project questionnaire answers, use **track_project_questionnaire_update()**:

```python
# Example: Answering project authentication question
project_id = "12345678-1234-1234-1234-123456789012"  # From questionnaires.json

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
                },
                {
                    "referenceId": "has-tls",
                    "answers": [
                        {
                            "referenceId": "has-tls-yes",
                            "value": "true"
                        }
                    ]
                }
            ]
        }
    ]
}

context = """Analyzed codebase:
- Authentication: Found JWT-based auth in src/middleware/auth.py
- TLS: HTTPS enforced in nginx.conf and all API clients use https://
"""

# Track the answers
track_project_questionnaire_update(
    project_id=project_id,
    answers_data=answers_data,
    project_path="/absolute/path/to/project",
    context=context
)
```

For component questionnaire answers, use **track_component_questionnaire_update()**:

```python
# Example: Answering database encryption question
component_id = "87654321-4321-4321-4321-210987654321"  # From questionnaires.json

answers_data = {
    "steps": [
        {
            "questions": [
                {
                    "referenceId": "db-encryption-at-rest",
                    "answers": [
                        {
                            "referenceId": "db-encryption-yes",
                            "value": "true"
                        }
                    ]
                }
            ]
        }
    ]
}

context = """Analyzed database configuration:
- Encryption at rest: Enabled in RDS config (encrypted: true in terraform)
"""

# Track the answers
track_component_questionnaire_update(
    component_id=component_id,
    answers_data=answers_data,
    project_path="/absolute/path/to/project",
    context=context
)
```

**Answer Data Structure Rules:**
- `referenceId` at question level: From questionnaires.json question object
- `referenceId` at answer level: From questionnaires.json answer object  
- `value`: Always string "true" or "false" (not boolean)
- `context`: Your analysis notes explaining how you determined the answers

**CRITICAL:** You can answer MULTIPLE questions in a single call by including multiple question objects in the `questions` array. This is more efficient than one call per question.

### Step 6: Sync to Push Answers (IMMEDIATE)

**After tracking answers, IMMEDIATELY call sync() without asking permission:**

```python
# This is REQUIRED - the MCP tool will remind you
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

### Step 7: Inform User of Results

After sync completes:

```
✅ Questionnaires completed and synced to IriusRisk!

I answered:
- Project-level: 5 questions (authentication, TLS, logging, etc.)
- User Database: 3 questions (encryption, backups, access)
- API Service: 4 questions (auth, rate limiting, validation)
- Web Application: 6 questions (sessions, XSS, CSRF)

IriusRisk has regenerated the threat model based on your actual implementation.

The updated threat model should now:
- Remove threats that don't apply (e.g., no unauthenticated access threats since auth is implemented)
- Adjust risk ratings based on existing controls
- Focus on actual gaps in your security posture

Would you like me to:
A) Show you the updated threats and what changed
B) Focus on the remaining high-priority threats
C) Generate implementation guidance for countermeasures

What would be most helpful?
```

## Common Question Patterns and Analysis Approaches

### Authentication Questions

**Question:** "Does the application implement authentication?"

**Analysis approach:**
```bash
# Search for common auth patterns
grep -r "authenticate\|login\|jwt\|session\|passport\|auth0" src/
grep -r "@require_auth\|@login_required\|@authenticated" src/
grep -r "Authorization:\|Bearer\|token" src/

# Check for auth libraries
grep "jsonwebtoken\|passport\|express-session\|django.contrib.auth" package.json requirements.txt

# Check middleware/guards
find src/ -name "*auth*.py" -o -name "*guard*.ts" -o -name "*middleware*.js"
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
grep -r "https://\|ssl.*true\|tls.*enabled" src/

# Check environment configs
grep "SSL\|TLS\|HTTPS" .env* config/*
```

**Answer YES if:** HTTPS URLs in config, SSL certificates configured, TLS enabled in servers
**Answer NO if:** HTTP URLs only, no SSL config

### Input Validation Questions

**Question:** "Is input validation implemented?"

**Analysis approach:**
```bash
# Search for validation
grep -r "validate\|sanitize\|validator\|schema" src/

# Check for validation libraries
grep "joi\|yup\|express-validator\|marshmallow\|pydantic" package.json requirements.txt

# Look for validation decorators/middleware
grep -r "@Valid\|@validated\|validate_request" src/
```

**Answer YES if:** Validation library used, validation on input endpoints, schema validation
**Answer NO if:** No validation code, raw input used directly

### Logging/Monitoring Questions

**Question:** "Is there logging and monitoring?"

**Analysis approach:**
```bash
# Search for logging
grep -r "logger\|log\.\|console.log\|logging\|winston\|pino" src/

# Check for monitoring services
grep "datadog\|newrelic\|sentry\|prometheus\|cloudwatch" package.json

# Look for log configs
find . -name "*log*.config.*" -o -name "*logging*.yml"
```

**Answer YES if:** Logger configured, monitoring service integrated, structured logging
**Answer NO if:** Only console.log or no logging

### Database Security Questions

**Question:** "Is database encryption at rest enabled?"

**Analysis approach:**
```bash
# Check database config
grep -r "encrypt.*rest\|storage.*encrypt\|encrypted.*true" terraform/ cloudformation/

# Check cloud provider configs
grep "StorageEncrypted\|encrypted\|kms" terraform/ aws/ gcp/

# Check database.yml or similar
grep "encrypt\|ssl" config/database.yml .env
```

**Answer YES if:** Encryption flag set in IaC, KMS keys configured, encrypted storage enabled
**Answer NO if:** No encryption config found

## Handling Multiple Components

When a project has many components with questionnaires:

**Strategy 1: Group by component type**
- Answer all database component questions together
- Answer all API component questions together
- Efficient code analysis (search once, apply to all similar components)

**Strategy 2: Prioritize critical components**
- Start with components handling sensitive data
- Then public-facing components
- Finally internal infrastructure

**Strategy 3: Batch API calls**
- Track multiple component answers before syncing
- One sync at the end applies all updates

**Always inform user of progress:**
```
Analyzing components:
✅ User Database (3/3 questions answered)
✅ API Service (4/4 questions answered)
⏳ Web Application (analyzing now...)
```

## Error Handling

**If you cannot determine an answer:**
1. Document what you searched for
2. Explain why it's unclear
3. Ask user for clarification
4. Provide a conservative default (usually "no")

**Example:**
```
I couldn't definitively determine if rate limiting is implemented for the API Service.

What I checked:
- No rate limiting middleware found in src/middleware/
- No rate-limit packages in package.json
- No rate limit configuration in nginx.conf or API gateway config

However, rate limiting might be configured at:
- Cloud provider level (AWS API Gateway, Cloudflare)
- Load balancer level
- Third-party service

Do you have rate limiting configured? If unsure, I'll answer "no" (conservative) 
and IriusRisk will flag it as a potential risk to address.
```

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

## Integration with Threat Analysis

After completing questionnaires and syncing:

1. **Compare before/after:**
   - Old threats.json vs new threats.json
   - Show user which threats were removed/adjusted

2. **Highlight improvements:**
   - "Your authentication implementation removed 12 unauthenticated access threats"
   - "TLS usage eliminated 8 man-in-the-middle threats"

3. **Focus on remaining gaps:**
   - "Here are the 5 high-priority threats that still need addressing..."

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
