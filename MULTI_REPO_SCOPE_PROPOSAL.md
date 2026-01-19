# Multi-Repository Threat Modeling with Scope Definitions

## Feature Proposal

**Status**: Draft  
**Created**: 2026-01-19  
**Author**: Feature discussion with customer feedback

---

## Problem Statement

Currently, the IriusRisk CLI maintains a one-to-one correlation between a code repository and an IriusRisk project (defined by `.iriusrisk/project.json`). However, real-world systems are often distributed across multiple repositories:

- **Microservices architectures**: Multiple service repositories contributing to a single system
- **Infrastructure as Code**: Terraform/CloudFormation separate from application code
- **Frontend/Backend separation**: Different repos for different tiers
- **Multi-language systems**: Python backend, React frontend, Go services, etc.

Each repository contains part of the overall system architecture, but customers need a **unified, comprehensive threat model** that represents the complete system across all repositories.

---

## Proposed Solution

Enable multiple repositories to contribute to a single IriusRisk project by introducing **scope definitions** that describe how each repository contributes to the unified threat model.

### Key Concepts

1. **Shared Project ID**: Multiple repositories reference the same `project_id`/`reference_id`
2. **Scope Definition**: Free-text field describing what part of the system this repository represents
3. **Incremental Contributions**: Each repository adds its perspective to the unified threat model
4. **AI-Driven Merging**: AI intelligently merges contributions based on scope context

---

## Design Details

### 1. Project Configuration Schema

Add `scope` field to `.iriusrisk/project.json`:

```json
{
  "name": "E-commerce Platform",
  "project_id": "abc-123-def-456",
  "reference_id": "ecommerce-platform",
  "scope": "AWS cloud infrastructure provisioned via Terraform. This includes ECS Fargate containers hosting the backend API (defined in api-backend repo), RDS PostgreSQL database cluster, ElastiCache Redis for session management, Application Load Balancer for traffic distribution, CloudFront CDN for frontend static assets (web-frontend repo), S3 buckets for user uploads, and VPC networking with public/private subnet isolation. Security groups enforce network-level isolation between application tiers. All application components defined in other repositories should be represented as running within their appropriate AWS service containers in the threat model.",
  "auto_version": true,
  "auto_version_prefix": "auto-backup-"
}
```

**Scope Field Specifications**:
- **Type**: String (free-text)
- **Optional**: Yes (defaults to all-encompassing if not specified)
- **Default**: Not specified (implies complete system view)
- **Purpose**: Provides context to AI for intelligent threat model merging

**Example Scope Definitions**:

- **Application Backend**:
  ```
  "This repository contains the Node.js REST API that implements the core business logic 
  for order processing, inventory management, and user account operations. The API exposes 
  endpoints consumed by the frontend web application (separate repository) and mobile apps. 
  The application connects to a PostgreSQL database and uses Redis for session management. 
  Infrastructure deployment (AWS ECS containers, load balancers, and networking) is defined 
  in a separate Terraform repository. This API runs in a containerized environment and 
  communicates with external payment and shipping providers."
  ```

- **Cloud Infrastructure**:
  ```
  "AWS cloud infrastructure defined in Terraform. This includes ECS Fargate containers 
  hosting the backend API (defined in api-backend repo), RDS PostgreSQL database cluster, 
  ElastiCache Redis for sessions, Application Load Balancer for traffic distribution, 
  CloudFront CDN for static assets, S3 buckets for file storage, and VPC networking with 
  public/private subnet isolation. The frontend SPA (React, separate repo) is deployed to 
  CloudFront. Security groups enforce network-level isolation between tiers. All application 
  components from other repositories should be placed within their appropriate AWS service 
  containers."
  ```

- **Frontend Application**:
  ```
  "React single-page application providing the customer-facing web interface. This includes 
  the shopping cart, product catalog, checkout flow, and user account management pages. 
  The SPA is deployed to CloudFront CDN (infrastructure defined in terraform repo) and 
  makes API calls to the backend REST API (api-backend repo). Uses JWT tokens stored in 
  localStorage for authentication. Integrates with Stripe.js for payment processing on 
  the client side. No server-side rendering - all business logic is in the backend API."
  ```

- **Microservice - Authentication**:
  ```
  "Authentication and authorization microservice for the e-commerce platform. Handles user 
  registration, login, password reset, and JWT token generation/validation. This service 
  is called by the API gateway (defined in api-gateway repo) for all authenticated requests. 
  Uses Auth0 as the identity provider and maintains a local user profile database. Other 
  microservices (order-service, inventory-service, payment-service in separate repos) 
  validate tokens against this service. Deployed as AWS Lambda functions (infrastructure 
  in terraform repo)."
  ```

- **Kubernetes Deployments**:
  ```
  "Kubernetes deployment configurations, Helm charts, and service mesh (Istio) setup for 
  all microservices. This defines how application services from other repositories are 
  deployed to our AKS cluster, including namespaces (production, staging, development), 
  network policies, service-to-service authentication via mTLS, ingress rules, and 
  horizontal pod autoscaling. Application code for each microservice lives in separate 
  repositories (auth-service, order-service, etc.). This repo only contains the Kubernetes 
  manifests and deployment configurations that orchestrate those services."
  ```

- **CI/CD Pipeline**:
  ```
  "GitHub Actions workflows and deployment automation for the entire platform. This includes 
  build pipelines for the frontend (web-frontend repo), backend API (api-backend repo), 
  infrastructure provisioning (terraform repo), security scanning, automated testing, and 
  deployment to staging and production environments. Also includes monitoring setup with 
  DataDog and alerting configurations. This is an operational/deployment scope that provides 
  visibility into how code from all other repositories flows through the pipeline and gets 
  deployed."
  ```

### 2. Multi-Repository Workflow

#### Scenario: E-commerce Platform Across 3 Repositories

**Repository 1: Application Code** (`api-backend/`)
```json
{
  "project_id": "ecommerce-platform",
  "scope": "Node.js REST API implementing core business logic for order processing, inventory management, and user accounts. Exposes REST endpoints consumed by web frontend (separate repo) and mobile apps. Connects to PostgreSQL database and Redis cache. Deployed as containerized service (infrastructure in terraform repo). Integrates with external payment gateway (Stripe) and shipping APIs."
}
```

**Repository 2: Infrastructure** (`terraform-aws/`)
```json
{
  "project_id": "ecommerce-platform",  // SAME project ID
  "scope": "AWS cloud infrastructure via Terraform. Provisions ECS Fargate containers for the API backend (api-backend repo), RDS PostgreSQL database, ElastiCache Redis, Application Load Balancer, CloudFront CDN for frontend static assets (web-frontend repo), S3 buckets, and VPC with public/private subnet isolation. Defines network security groups and IAM roles. All application components from other repos run within these AWS services."
}
```

**Repository 3: Frontend** (`web-frontend/`)
```json
{
  "project_id": "ecommerce-platform",  // SAME project ID
  "scope": "React SPA providing customer-facing web interface including product catalog, shopping cart, checkout flow, and user account management. Deployed to CloudFront CDN (terraform repo). Makes REST API calls to backend (api-backend repo) using JWT authentication. Integrates Stripe.js for client-side payment processing. All business logic resides in backend API, this is presentation layer only."
}
```

#### Threat Model Evolution

1. **After Repo 1 (Backend)**:
   - Components: "API Service", "Database Connection", "Auth Module"
   - Abstract level - no infrastructure detail

2. **After Repo 2 (Infrastructure)**:
   - "API Service" → wrapped in "AWS ECS Container"
   - "Database Connection" → becomes "AWS RDS PostgreSQL"
   - Added: "CloudFront CDN", "ALB", "VPC", security groups
   - Trust zones defined by AWS networking boundaries

3. **After Repo 3 (Frontend)**:
   - Added: "React SPA", "Browser Client"
   - Data flows: Browser → CloudFront → ALB → ECS
   - New threats: XSS, CSRF, client-side storage

**Result**: Single comprehensive threat model showing complete system across all layers.

---

## Implementation Requirements

### 1. CLI Command Updates

#### `iriusrisk init` Command

Add `--scope` parameter (optional):

```bash
# New project with scope
$ iriusrisk init -n "E-commerce Platform" --scope "Backend API services"

# Connect to existing project with scope
$ iriusrisk init -r "ecommerce-platform" --scope "AWS infrastructure"

# Interactive prompt for scope when connecting to existing project
$ iriusrisk init -r "ecommerce-platform"
Project found: E-commerce Platform
This repository will contribute to an existing threat model.
What is this repository's scope? (leave blank for complete system): AWS cloud infrastructure
```

**Behavior**:
- When creating new project: Scope is optional, defaults to unspecified
- When connecting to existing project: Prompt for scope to differentiate contribution
- Scope can be updated later by editing `project.json`

### 2. OTM Export Capability

**New MCP Tool**: `export_otm()`

```python
@mcp_server.tool()
async def export_otm(project_id: str = None, output_path: str = None) -> str:
    """Export the current threat model from IriusRisk as OTM format.
    
    This tool retrieves the existing threat model for a project and exports it
    as an OTM file. This is used when multiple repositories contribute to the
    same project - subsequent repos need to see the existing threat model.
    
    Args:
        project_id: Project ID or reference ID (optional if default project configured)
        output_path: Where to save the OTM file (optional, returns content if not specified)
        
    Returns:
        Status message with OTM export details, or OTM content if no output_path
    """
```

**API Support**: IriusRisk V2 API supports OTM export (confirmed).

### 3. MCP Prompt Updates

#### Update `create_threat_model.md` Prompt

Add section on multi-repository workflow:

```markdown
## Multi-Repository Threat Modeling

When working with projects that span multiple repositories:

1. **Check for Existing Project**:
   - Look for `project_id` in `.iriusrisk/project.json`
   - Check if project exists in IriusRisk using `project_status()` tool

2. **Export Existing Threat Model** (if project exists):
   - Use `export_otm()` tool to download current threat model
   - Review existing components, trust zones, and data flows

3. **Consider Repository Scope**:
   - Read `scope` field from `project.json`
   - Understand what this repository contributes to the overall system
   - Examples:
     - "Backend services" → Focus on business logic components
     - "AWS infrastructure" → Wrap existing components in cloud resources
     - "Frontend" → Add UI components and client-side flows

4. **Create Merged OTM**:
   - Incorporate existing threat model components
   - Add new components based on current repository analysis
   - Layer infrastructure/platform components appropriately
   - Preserve existing trust zones while adding new ones
   - Merge data flows intelligently

5. **Upload Merged Threat Model**:
   - Use `import_otm()` with merged OTM file
   - IriusRisk will update (not replace) the project

## Scope-Aware Merging Guidelines

**Infrastructure Scope** ("AWS infrastructure", "Kubernetes platform"):
- Wrap/contain application-level components
- Add platform services (load balancers, databases, message queues)
- Define trust zones based on network boundaries
- Show how abstract components are deployed

**Application Scope** ("Backend API", "Frontend SPA"):
- Define business logic components
- Show application-level data flows
- Focus on logical architecture
- May reference infrastructure abstractly

**Integration Scope** ("CI/CD pipeline", "Monitoring"):
- Add operational components
- Show deployment and monitoring flows
- Cross-cutting concerns

The AI should use its understanding of system architecture to merge appropriately.
```

#### Update `analyze_source_material.md` Prompt

Add guidance on scope-aware analysis:

```markdown
## Scope-Aware Source Analysis

When analyzing source code in a multi-repository context:

1. **Read the Scope Definition**:
   - Check `.iriusrisk/project.json` for `scope` field
   - This tells you what aspect of the system you're modeling

2. **Focus Your Analysis**:
   - If scope is "AWS infrastructure", focus on Terraform/CloudFormation
   - If scope is "Backend services", focus on API endpoints and business logic
   - If scope is "Frontend", focus on UI components and client-side interactions

3. **Consider Existing Components**:
   - If threat model already exists, your analysis should complement it
   - Look for components that need infrastructure detail
   - Find gaps that your repository fills

4. **Extract Scope-Relevant Components**:
   - Don't duplicate what other repositories already covered
   - Add detail or context to existing components
   - Introduce new components specific to your scope
```

### 4. Project Service Updates

#### `ProjectService` Enhancement

Add methods to support multi-repo workflow:

```python
class ProjectService:
    def export_otm(self, project_id: str, output_path: str = None) -> dict:
        """Export project threat model as OTM format.
        
        Args:
            project_id: Project UUID or reference ID
            output_path: Optional path to save OTM file
            
        Returns:
            Dict with OTM content and metadata
        """
        
    def get_project_scope(self, project_path: str = None) -> str:
        """Get scope definition from project.json.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Scope string or None if not defined
        """
```

### 5. API Client Updates

#### `ProjectApiClient` Enhancement

```python
class ProjectApiClient:
    def export_project_otm(self, project_id: str) -> str:
        """Export project as OTM format.
        
        Uses V2 API endpoint: GET /api/v2/projects/{id}/export/otm
        
        Args:
            project_id: Project UUID
            
        Returns:
            OTM content as JSON string
        """
```

---

## User Experience

### First Repository (Creating Project)

```bash
$ cd backend-api/
$ iriusrisk init -n "E-commerce Platform"
Enter scope for this repository (optional, press Enter for complete system view):
Node.js REST API implementing core business logic for orders, inventory, and user accounts. 
Exposes endpoints for frontend (separate repo) and mobile apps. Connects to PostgreSQL and Redis. 
Will be deployed via containerized infrastructure (terraform repo). Integrates with Stripe and 
shipping APIs.

✅ Project initialized: E-commerce Platform
📝 Scope configured (157 characters)

# AI creates threat model
$ cursor  # User asks AI: "Create a threat model for this API"
# AI analyzes code, creates OTM, uploads to IriusRisk
```

### Second Repository (Contributing to Existing)

```bash
$ cd ../terraform-aws/
$ iriusrisk init -r "ecommerce-platform"
Project found: E-commerce Platform (1 repository already contributing)

This project already has contributions from other repositories.
What is this repository's scope?
AWS infrastructure via Terraform. Provisions ECS Fargate for backend API (api-backend repo), 
RDS PostgreSQL, ElastiCache Redis, ALB, CloudFront for frontend assets (web-frontend repo), 
S3, and VPC with subnet isolation. All application components from other repos run within 
these AWS services.

✅ Connected to: E-commerce Platform
📝 Scope configured (267 characters)

# AI enhances threat model
$ cursor  # User asks AI: "Update the threat model with infrastructure details"
# AI exports existing OTM, analyzes Terraform, merges with application components, uploads
```

### Third Repository (Another Contribution)

```bash
$ cd ../web-frontend/
$ iriusrisk init -r "ecommerce-platform"
Project found: E-commerce Platform (2 repositories already contributing)

This project already has contributions from other repositories.
What is this repository's scope?
React SPA for customer web interface - product catalog, cart, checkout, account management. 
Deployed to CloudFront (terraform repo). Calls backend REST API (api-backend repo) with JWT 
auth. Integrates Stripe.js for payments. This is presentation layer only, all business logic 
in backend.

✅ Connected to: E-commerce Platform  
📝 Scope configured (241 characters)

# AI adds frontend perspective
$ cursor  # User asks AI: "Add frontend to the threat model"
# AI exports existing OTM, analyzes React code, adds UI components and flows, uploads merged model
```

---

## Technical Considerations

### 1. Scope is Advisory, Not Prescriptive

- Scope is **free text** to allow maximum flexibility
- AI interprets scope using its training and context understanding
- No rigid rules about how scopes must merge
- Users can provide detailed instructions in scope field

### 2. No Ownership Model

- First repository doesn't "own" the project
- All contributions are equal
- Order of contribution doesn't matter (though may affect default structure)
- Any repository can update any part of the threat model

### 3. Conflict Resolution

- Multiple components with similar names are allowed
- AI should make best effort to merge intelligently
- If unclear, AI can ask user for guidance
- IriusRisk handles duplicate component names naturally

### 4. OTM as Source of Truth

- Each import operation sends complete OTM
- IriusRisk merges/updates based on component IDs
- Components not in new OTM are preserved (not deleted)
- Clean merge semantics via OTM format

### 5. Versioning and Rollback

- Existing auto-versioning feature works with multi-repo
- Each import creates a version snapshot
- Can roll back to any previous state
- Version history shows contributions over time

---

## Implementation Phases

### Phase 1: Basic Infrastructure
- [ ] Add `scope` field to project.json schema
- [ ] Update `iriusrisk init` to support `--scope` parameter
- [ ] Add scope prompting when connecting to existing project
- [ ] Update Config class to read/write scope

### Phase 2: OTM Export
- [ ] Add OTM export endpoint to `ProjectApiClient`
- [ ] Create `export_otm()` MCP tool
- [ ] Add `export_otm()` method to `ProjectService`
- [ ] Add CLI command: `iriusrisk otm export`

### Phase 3: MCP Prompt Updates
- [ ] Update `create_threat_model.md` with multi-repo workflow
- [ ] Update `analyze_source_material.md` with scope awareness
- [ ] Add examples and guidelines for common scenarios
- [ ] Test prompts with various scope definitions

### Phase 4: Documentation and Testing
- [ ] Update README with multi-repo examples
- [ ] Create user guide for multi-repo workflows
- [ ] Add integration tests for multi-repo scenarios
- [ ] Document common patterns and best practices

---

## Example Scenarios

### Scenario 1: Microservices Architecture

```
ecommerce-system/
├── auth-service/          
│   scope: "Authentication and authorization microservice using OAuth2 and JWT. 
│          Validates user credentials, issues tokens, manages sessions. Called by 
│          api-gateway for all authenticated requests. Other services (order, inventory, 
│          notification) validate tokens against this service. Uses PostgreSQL for user 
│          profiles. Deployed as Kubernetes pods (k8s-config repo)."
│
├── order-service/         
│   scope: "Order processing microservice handling cart management, order submission, 
│          and payment coordination. Calls payment-gateway-service for processing, 
│          inventory-service for stock validation, and notification-service for 
│          confirmations. Publishes order events to Kafka. PostgreSQL for order 
│          persistence. Kubernetes deployment in k8s-config repo."
│
├── inventory-service/     
│   scope: "Product catalog and inventory management microservice. Provides product 
│          search, availability checks, and stock updates. Consumed by order-service 
│          and frontend. Uses Elasticsearch for search, PostgreSQL for inventory data. 
│          Real-time stock sync with warehouse API. Kubernetes deployment."
│
├── notification-service/  
│   scope: "Notification microservice for email and SMS delivery. Listens to Kafka 
│          events from order-service, payment-service. Integrates with SendGrid (email) 
│          and Twilio (SMS). Includes templates for order confirmations, shipping updates, 
│          password resets. Deployed as AWS Lambda (infrastructure in terraform repo)."
│
└── api-gateway/           
│   scope: "Kong API gateway providing single entry point for all client requests. 
│          Routes traffic to auth-service, order-service, inventory-service based on 
│          paths. Handles rate limiting, request logging, JWT validation (via auth-service). 
│          Deployed on dedicated EC2 instances (terraform repo). Web frontend and mobile 
│          apps (separate repos) connect through this gateway."
```

All share `project_id: "ecommerce-system"`, each contributes their service to the unified threat model.

### Scenario 2: Full-Stack with Infrastructure

```
web-app/
├── frontend/       
│   scope: "React SPA providing customer-facing web application. Includes dashboard, 
│          reporting interface, user settings. Deployed to CloudFront CDN (terraform repo). 
│          Authenticates via JWT tokens from backend API. Makes REST calls to backend 
│          (backend repo) for all data operations. Uses Material-UI component library. 
│          Integrates Google Analytics and Sentry for monitoring."
│
├── backend/        
│   scope: "Python Flask REST API implementing business logic for analytics platform. 
│          Processes data uploads, runs analytical models, generates reports. Connects 
│          to PostgreSQL for structured data, S3 for file storage (terraform repo). 
│          Background tasks use Celery with Redis. Deployed to EKS cluster (kubernetes repo). 
│          Exposes endpoints consumed by frontend SPA and external API clients."
│
├── terraform/      
│   scope: "AWS infrastructure provisioning. Includes EKS cluster for backend services 
│          (backend and kubernetes repos), RDS PostgreSQL with read replicas, ElastiCache 
│          Redis for Celery, S3 buckets for uploads and static assets, CloudFront CDN 
│          for frontend distribution (frontend repo), VPC with multi-AZ deployment, 
│          security groups, IAM roles, Route53 DNS. All application components run 
│          within these AWS resources."
│
└── kubernetes/     
│   scope: "Kubernetes deployment manifests for EKS cluster (terraform repo). Defines 
│          how backend Flask API (backend repo) is deployed including HPA, services, 
│          ingress, network policies. Also includes Celery worker deployments, Istio 
│          service mesh configuration for mTLS between pods, monitoring with Prometheus/Grafana. 
│          This is pure Kubernetes orchestration - application code in backend repo."
```

### Scenario 3: Platform and Applications

```
company-platform/
├── core-platform/     
│   scope: "Core platform services providing shared capabilities for all applications. 
│          Includes authentication service (OAuth2/SAML), centralized logging (ELK stack), 
│          monitoring and alerting (Prometheus/Grafana), secrets management (Vault), 
│          service mesh (Istio). All other applications (customer-portal, admin-dashboard, 
│          mobile-backend) depend on these services for auth, observability. Deployed to 
│          shared Kubernetes namespace across all environments."
│
├── customer-portal/   
│   scope: "Customer-facing web portal built with Vue.js. Provides account management, 
│          product browsing, support ticketing. Authenticates via core-platform auth service. 
│          Backend API in Node.js connects to customer database (PostgreSQL) and external 
│          CRM (Salesforce). Deployed as separate Kubernetes namespace. Uses core-platform 
│          logging and monitoring services."
│
├── admin-dashboard/   
│   scope: "Internal admin dashboard for customer support and operations teams. Angular 
│          SPA with Python Django backend. Requires elevated authentication via core-platform 
│          auth (SAML with Active Directory). Accesses data from customer-portal database 
│          (read-only replica) and admin-specific database. Audit logging via core-platform. 
│          Only accessible from internal VPN. Kubernetes deployment with restricted ingress."
│
└── mobile-backend/    
│   scope: "GraphQL API backend specifically for iOS and Android mobile applications 
│          (mobile app repos are separate). Aggregates data from customer-portal services 
│          and provides mobile-optimized responses. Handles push notifications via Firebase. 
│          Authenticates mobile clients using JWT tokens from core-platform auth service. 
│          Uses Redis for mobile session caching. Deployed to edge locations for low latency."
```

---

## Open Questions

1. **Scope Validation**: Should we validate scope format or leave completely free?
2. **Scope Templates**: Should we provide example scopes for common scenarios?
3. **Visualization**: Can IriusRisk UI show which repos contributed which components?
4. **Scope Conflicts**: What if two repos have overlapping scopes?
5. **CLI Discovery**: Should `iriusrisk` command detect other repos with same project_id?

---

## Success Metrics

- Users can successfully contribute to same project from multiple repositories
- Threat models show comprehensive view across all repositories
- AI successfully merges contributions based on scope definitions
- No confusion about which repository "owns" the project
- Clear documentation and examples for common patterns

---

## References

- OTM (Open Threat Model) Specification: https://github.com/iriusrisk/OpenThreatModel
- IriusRisk V2 API Documentation
- Current `iriusrisk init` command implementation
- MCP tool architecture and patterns

