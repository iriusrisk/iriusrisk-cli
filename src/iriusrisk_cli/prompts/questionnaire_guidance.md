# Questionnaire Guidance Instructions for AI Assistants

## CRITICAL: Questionnaire Data Structure

**When READING questionnaires from `questionnaires.json`:**
- Use `questionnaire.groups[].questions` (groups, not steps!)
- Each group has a `text` field (the group name) and a `questions` array
- **WARNING**: The group name field is `text`, NOT `name`

**When SUBMITTING answers:**
- Use `answers_data = {"steps": [...]}` format
- The answer payload uses "steps" but the source data uses "groups"

**Common Errors**:
- Searching for `.steps[]` in questionnaires.json will find nothing. Use `.groups[]` instead.
- Using `group['name']` will fail. Use `group['text']` to get the group name.
- Using `answer['selected']` will fail. The field is `answer['answer']` (string "true"/"false").

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

**Each component typically has TWO question groups:**

1. **"Security Context" group** (HIGH PRIORITY) — Security-specific questions with 4 standardized answer options (not-applicable / required / recommended / implemented). These directly affect which threats and countermeasures IriusRisk generates. Examples:
   - S3 Bucket: Is encryption at rest enabled? Is public access blocked? Is S3 Object Lock active?
   - RDS Database: Is Multi-AZ deployed? Is TLS used for connections? Is encryption at rest enabled?
   - ECS Cluster: Is least privilege used for tasks? Are tasks restricted to private subnets?
   - REST API: Is rate limiting active? Is RBAC implemented? Is HTTPS enforced?
   - Web Client: Is JavaScript sandboxing used? Is HTTPS enforced with strong TLS?

2. **"Assets" group** — Data asset tracking questions with multi-select answers (Stored / Processed / Sent / Received). These map data flow through each component.

**Impact:** Affects threats for that specific component only.

**Scope filtering**: Only answer questionnaires for components in your repository's scope.

**CRITICAL**: You MUST look at ALL groups for each component. Do not stop after finding one group.

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

**CRITICAL: Questionnaire JSON Structure**

The questionnaire data downloaded from IriusRisk uses **"groups"** not "steps":
- `questionnaire.groups[].questions` (CORRECT - for reading questionnaires)
- `questionnaire.steps[].questions` (WRONG - will find nothing)

**When READING questionnaires** from `questionnaires.json`:
```python
# CORRECT way to iterate through questions
for group in questionnaire_data['questionnaire']['groups']:
    group_name = group['text']     # NOTE: field is 'text', NOT 'name'
    for question in group['questions']:
        question_text = question['text']
        question_ref = question['referenceId']
        for answer in question['answers']:
            answer_text = answer['text']
            answer_ref = answer['referenceId']
            current_value = answer['answer']  # NOTE: field is 'answer', NOT 'selected'
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
- **Reading** questionnaires: `groups` → `questions` (group name field: `text`, answer state field: `answer`)
- **Submitting** answers: `steps` → `questions`

### CRITICAL: Component Question Group Types

**Every component questionnaire has TWO groups that you MUST examine:**

1. **"Assets"** group — Questions about how data assets flow through this component
2. **"Security Context"** group — Security-specific questions about the component's configuration and controls

**You MUST iterate ALL groups for each component.** If you only look at the first group, you will miss the Security Context questions entirely (since Assets typically appears first).

#### "Security Context" Group (HIGH PRIORITY)

These are the questions that directly refine the threat model. They ask about specific security controls, configurations, and practices for the component type. Each question has **four standardized answer options**:

| Answer text | Reference ID suffix | Meaning |
|---|---|---|
| "No, and this is not applicable" | `.mark.as.not.applicable` | The control doesn't apply to this architecture |
| "No, but it is required" | `.mark.as.required` | Not yet implemented but should be |
| "Not sure" | `.mark.as.recommended` | Under analysis / uncertain |
| "Yes, it is implemented" | `.mark.as.implemented` | Already in place |

**Examples of Security Context questions (by component type):**
- **S3 Bucket**: "Is encryption of data at rest in Amazon S3 currently in use?", "Is S3 Object Lock active?", "Is the S3 bucket public access block implemented?"
- **RDS Database**: "Is Multi-AZ deployment enabled?", "Do you use TLS for all client connections?", "Is encryption at rest enabled?"
- **ECS Cluster**: "Do you configure auto scaling policies?", "Does the system use least privilege for tasks?"
- **Load Balancer**: "Is deletion protection activated?", "Is AWS WAF with managed rules deployed?"
- **RESTful API**: "Is rate limiting activated?", "Is Role-Based Access Control implemented?", "Is HTTPS encrypting all API communication?"
- **Web Client**: "Is JavaScript sandboxing used?", "Is sensitive data securely stored on the client side?"

#### "Assets" Group

These questions track how each data asset is handled by the component. Each question follows the pattern:
`"{asset_name}: How is it handled by this component?"`

with multi-select answers (`allowsMultipleAnswers: true`):
- "Stored" — Data is persisted in this component
- "Processed" — Data is transformed or used by this component
- "Sent from component" — Data flows out of this component
- "Received by component" — Data flows into this component

Asset questions have referenceIds starting with `asset.` (e.g., `asset.1`, `asset.2`).

### Actual questionnaires.json Structure

Here is the real JSON structure you will encounter:

```json
{
  "metadata": {
    "project_id": "uuid",
    "data_type": "questionnaires",
    "component_count": 9
  },
  "project": {
    "projectId": "uuid",
    "questionnaire": {
      "groups": [
        {
          "text": "Group Name Here",
          "questions": [
            {
              "referenceId": "question-ref-id",
              "text": "The question text?",
              "description": "",
              "priority": 4,
              "allowsMultipleAnswers": false,
              "required": false,
              "answers": [
                {
                  "referenceId": "answer-ref-id",
                  "text": "Answer option text",
                  "description": "",
                  "answer": "false"
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
      "componentName": "S3 Application Storage",
      "questionnaire": {
        "groups": [
          {
            "text": "Assets",
            "questions": [
              {
                "referenceId": "asset.1",
                "text": "UserData: How is it handled by this component?",
                "description": "",
                "priority": 2043,
                "allowsMultipleAnswers": true,
                "required": false,
                "answers": [
                  {"referenceId": "UserDataStored", "text": "Stored", "description": null, "answer": "false"},
                  {"referenceId": "UserDataProcessed", "text": "Processed", "description": null, "answer": "false"},
                  {"referenceId": "UserDataSent from component", "text": "Sent from component", "description": null, "answer": "false"},
                  {"referenceId": "UserDataReceived by component", "text": "Received by component", "description": null, "answer": "false"}
                ]
              }
            ]
          },
          {
            "text": "Security Context",
            "questions": [
              {
                "referenceId": "provided.question.C-AWS-S3-CNT-06",
                "text": "Is the encryption of data at rest in Amazon S3 currently in use?",
                "description": "",
                "priority": 7000,
                "allowsMultipleAnswers": false,
                "required": false,
                "answers": [
                  {"referenceId": "provided.question.C-AWS-S3-CNT-06.mark.as.not.applicable", "text": "No, and this is not applicable", "description": "This requirement cannot be implemented in this system or is out of scope", "answer": "false"},
                  {"referenceId": "provided.question.C-AWS-S3-CNT-06.mark.as.required", "text": "No, but it is required", "description": "This requirement has to be implemented", "answer": "false"},
                  {"referenceId": "provided.question.C-AWS-S3-CNT-06.mark.as.recommended", "text": "Not sure", "description": "This requirement is under analysis", "answer": "false"},
                  {"referenceId": "provided.question.C-AWS-S3-CNT-06.mark.as.implemented", "text": "Yes, it is implemented", "description": "", "answer": "true"}
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

Component-level:
Each component has two question groups: "Assets" (data flow tracking) and "Security Context" (security controls).

Security Context questions (these refine the threat model):
- S3 Application Storage (17 questions): encryption at rest, public access blocking, S3 Object Lock, access logging, IAM roles...
- RDS PostgreSQL Database (7 questions): Multi-AZ, TLS connections, encryption at rest, network restrictions...
- ECS Fargate Cluster (7 questions): auto scaling, least privilege, private subnets, monitoring...
- Application Load Balancer (5 questions): deletion protection, WAF, access logging, desync mitigation...
- Wildlife Tracker API (9 questions): rate limiting, RBAC, HTTPS, input sanitization, session management...

Asset questions (data flow mapping):
- All components share 46 asset tracking questions about how data flows through each component.

I'll analyze your source code to answer these. This will take a moment...
```

**IMPORTANT: You MUST iterate ALL groups for each component.** Do not stop after finding the "Assets" group. The "Security Context" group contains the high-value security questions that directly affect threat generation.

### Step 4: Analyze Source Code to Determine Answers

**CRITICAL: You MUST analyze the actual source code to determine truthful answers.**

**Process ALL groups for each component — both "Assets" and "Security Context".**

#### Answering Security Context Questions

Security Context questions have four answer options. Choose the one that best matches reality:

| If the code shows... | Select... |
|---|---|
| The security control is implemented and active | "Yes, it is implemented" |
| The control is needed but not yet in place | "No, but it is required" |
| The control doesn't apply to this architecture/component | "No, and this is not applicable" |
| You cannot determine from the code | "Not sure" |

**For each Security Context question:**
1. Identify what code, configuration, or infrastructure would indicate the control is in place
2. Search the codebase for relevant files, patterns, libraries, IaC definitions
3. Make an evidence-based determination
4. Document your reasoning in the context field

**Example analysis for "Is the encryption of data at rest in Amazon S3 currently in use?":**
```
# Search for S3 encryption configuration in:
# - Terraform/CloudFormation: server_side_encryption_configuration, SSEAlgorithm
# - AWS CDK: encryption property on S3 bucket constructs
# - AWS CLI scripts: --server-side-encryption flags
#
# Finding: terraform/s3.tf has server_side_encryption_configuration with aws:kms
# → ANSWER: "Yes, it is implemented" (*.mark.as.implemented)
```

**Example analysis for "Is rate limiting and IP blocking activated?":**
```
# Search for rate limiting in:
# - Application middleware: throttle, rate_limit decorators
# - API gateway config: throttling settings
# - Nginx/reverse proxy: limit_req_zone
# - WAF rules: rate-based rules
#
# Finding: No rate limiting middleware in app code, no WAF rules in IaC
# → ANSWER: "No, but it is required" (*.mark.as.required)
```

#### Answering Asset Questions

Asset questions track data flow. For each `"{asset_name}: How is it handled by this component?"`:
- Determine which of Stored / Processed / Sent / Received apply (multiple can be selected)
- Base this on how data actually flows through the component in the architecture
- For a database component: likely "Stored" and possibly "Processed"
- For an API component: likely "Processed", "Sent from component", "Received by component"
- For a storage component like S3: likely "Stored", "Received by component"

**DO NOT:**
- Guess or assume answers without checking code
- Answer "implemented" to make the user feel good
- Answer "not applicable" just because the answer seems hard to find
- Skip the Security Context group after processing Assets
- Skip the Assets group after processing Security Context

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

### Security Context Questions (4-Option Pattern)

These are the most impactful questions. They follow a consistent pattern with four answer options.

#### AWS Infrastructure Security Context Examples

**S3 Bucket questions** — search for:
- Terraform: `aws_s3_bucket`, `server_side_encryption_configuration`, `block_public_access`, `versioning`, `object_lock_configuration`, `logging`
- CloudFormation: `AWS::S3::Bucket`, `BucketEncryption`, `PublicAccessBlockConfiguration`

**RDS Database questions** — search for:
- Terraform: `aws_db_instance`, `multi_az`, `storage_encrypted`, `kms_key_id`, `iam_database_authentication_enabled`
- Connection strings: TLS/SSL parameters, `sslmode=require`

**ECS/Fargate questions** — search for:
- Terraform: `aws_ecs_task_definition`, `task_role_arn`, `network_mode`, `awsvpc`, subnet configurations
- IAM policies: least privilege task roles, execution roles

**Load Balancer questions** — search for:
- Terraform: `aws_lb`, `deletion_protection`, `access_logs`, `aws_wafv2_web_acl_association`
- Listener configurations: HTTPS, TLS policies

#### Application Security Context Examples

**RESTful API questions** — search for:
- Rate limiting: middleware, decorators (`@rate_limit`, `flask-limiter`, `express-rate-limit`)
- RBAC: role checks, permission decorators, authorization middleware
- HTTPS: server config, certificate setup, redirect rules
- Input sanitization: validation libraries (pydantic, marshmallow, joi), `@validate`, `sanitize()`
- Session management: session config, token expiration, secure cookie flags

**Web Client questions** — search for:
- Frame-busting: `X-Frame-Options`, CSP `frame-ancestors`, JavaScript frame detection
- JavaScript sandboxing: CSP policies, sandbox attributes, eval restrictions
- Client-side storage: localStorage/sessionStorage usage, sensitive data checks
- HTTPS enforcement: HSTS headers, redirect rules, `Strict-Transport-Security`

### Project-Level Question Patterns

#### Authentication Questions

**Question:** "Does the application implement authentication?"

**Analysis approach:**
- Search for: auth middleware, JWT usage, session management, login endpoints
- Check for: `@require_auth`, `@login_required`, `Authorization: Bearer`, passport.js
- Libraries: jsonwebtoken, passport, express-session, django.contrib.auth

**Answer YES if:** Auth middleware exists, JWT/session tokens used, protected routes, login endpoints
**Answer NO if:** No auth code found, all routes publicly accessible

#### Encryption/TLS Questions

**Question:** "Is TLS/HTTPS used for communications?"

**Analysis approach:**
- Check server config: nginx.conf, docker-compose.yml for https/ssl/tls/certificate
- Check API clients: https:// URLs, ssl=true, tls=enabled
- Check IaC: ALB listeners on port 443, certificate ARNs

**Answer YES if:** HTTPS URLs in config, SSL certificates configured, TLS enabled in servers
**Answer NO if:** HTTP URLs only, no SSL config

#### Input Validation Questions

**Question:** "Is input validation implemented?"

**Analysis approach:**
- Search for: validate, sanitize, validator, schema
- Libraries: joi, yup, express-validator, marshmallow, pydantic
- Decorators: @Valid, @validated, validate_request

**Answer YES if:** Validation library used, validation on input endpoints, schema validation
**Answer NO if:** No validation code, raw input used directly

### Asset Questions (Multi-Select Pattern)

For each `"{asset_name}: How is it handled by this component?"`:

**Determine which answers to select based on the component's role:**

| Component Type | Typical Asset Handling |
|---|---|
| Database (RDS, DynamoDB) | Stored, possibly Processed |
| Object Storage (S3) | Stored, Received by component |
| API Service | Processed, Sent from component, Received by component |
| Load Balancer | Sent from component, Received by component |
| Web Client | Processed, Sent from component, Received by component |
| Cache (Redis, ElastiCache) | Stored, Processed |
| Logging Service | Stored, Received by component |

**Analysis approach:**
- Review the OTM dataflows to understand what data moves between components
- Check the source code for data transformations, API calls, database writes
- For each asset, determine if the component stores, processes, sends, or receives it

## Handling Multiple Components

When a project has many components with questionnaires:

**Strategy 1: Prioritize Security Context, then Assets**
- Answer ALL Security Context questions first across all components (these refine the threat model)
- Then answer Asset questions (these track data flow)
- This ensures the highest-impact answers are completed even if interrupted

**Strategy 2: Group by component type**
- Answer all database component questions together (Security Context + Assets)
- Answer all API component questions together
- Efficient code analysis (search once, apply to all similar components)

**Strategy 3: Batch API calls**
- Track multiple component answers before syncing
- One sync at the end applies all updates

**Always inform user of progress — show both group types:**
```
Analyzing components:
✅ S3 Application Storage
   - Security Context: 17/17 questions answered (encryption, access control, monitoring...)
   - Assets: 46/46 asset flow questions answered
✅ RDS PostgreSQL Database
   - Security Context: 7/7 questions answered (Multi-AZ, TLS, encryption...)
   - Assets: 46/46 asset flow questions answered
⏳ Wildlife Tracker API (analyzing Security Context now...)
```

## Error Handling

**If you cannot determine an answer:**
1. Document what you searched for
2. Explain why it's unclear
3. Ask user for clarification
4. For Security Context questions: select "Not sure" (mark.as.recommended) — this flags the question for review without making false claims
5. For Asset questions: skip the asset if you cannot determine data flow

**Example (Security Context):**
```
I couldn't definitively determine if rate limiting is implemented for the Wildlife Tracker API.

What I checked:
- No rate limiting middleware found in src/middleware/
- No rate-limit packages in requirements.txt
- No rate limit configuration in nginx.conf or API gateway config

However, rate limiting might be configured at:
- Cloud provider level (AWS API Gateway, Cloudflare)
- Load balancer level
- Third-party service

Do you have rate limiting configured? If unsure, I'll answer "Not sure" 
(mark.as.recommended) so it stays flagged for review.
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
- ☐ Read questionnaires.json and summarize for user (show both Assets and Security Context groups)
- ☐ For each component, iterate ALL groups (do not stop at the first group)
- ☐ Answer Security Context questions (4-option pattern: not-applicable / required / recommended / implemented)
- ☐ Answer Asset questions (multi-select: Stored / Processed / Sent / Received)
- ☐ Track project questionnaire answers with context
- ☐ Track component questionnaire answers with context (include both groups)
- ☐ Immediately sync() to push answers (don't ask permission)
- ☐ Inform user of results and threat model changes
- ☐ Offer next steps (review threats, implement countermeasures)

Your goal: Make the threat model as accurate as possible by providing evidence-based questionnaire answers derived from actual code analysis.
