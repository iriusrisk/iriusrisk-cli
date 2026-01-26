# Source Material Analysis Instructions for AI Assistants

## Executive Summary
Analyze mixed repositories (application code + infrastructure + policies + docs) to extract ALL components for ONE unified threat model. Your role: architecture modeling only—extract components, trust zones, and data flows. Do NOT identify vulnerabilities or security flaws; IriusRisk handles that automatically. Create a single comprehensive threat model covering all layers.

## Critical Principle: One Comprehensive Threat Model
Create ONE unified threat model including ALL components from ALL source types. Do NOT create separate models for code vs. infrastructure—IriusRisk works best with a complete, holistic view of the entire system.

## Scope-Aware Analysis for Multi-Repository Projects

**FIRST: Check for repository scope definition** in `.iriusrisk/project.json`:

```json
{
  "name": "E-commerce Platform",
  "reference_id": "ecommerce-platform",
  "scope": "AWS cloud infrastructure via Terraform. Provisions ECS for backend API 
           (api-backend repo), RDS PostgreSQL, ALB, CloudFront for frontend static 
           assets (web-frontend repo). All application components from other repos 
           should run within these AWS services."
}
```

### When Scope is Defined

**Your analysis must be FOCUSED on the scope:**

1. **Understand the scope boundaries:**
   - What is THIS repository responsible for?
   - What components from OTHER repositories are mentioned?
   - What is the architectural relationship to other parts?

2. **Focus your component extraction:**
   - Extract components relevant to THIS repository's scope
   - Note references to components from other repositories
   - Understand how your components relate to the broader system

3. **Scope-specific extraction strategies:**

   **Infrastructure scope** (e.g., "AWS infrastructure", "Kubernetes platform"):
   - **Primary focus**: Cloud resources, networking, compute platforms
   - **Extract**: VPCs, load balancers, container orchestration, managed databases, CDN, storage services
   - **Note**: Application components mentioned in scope (e.g., "backend API from api-backend repo")
   - **Expectation**: Your components will CONTAIN or HOST application components from other repos

   **Application scope** (e.g., "Backend API", "Payment service"):
   - **Primary focus**: Business logic, services, APIs
   - **Extract**: Service endpoints, business logic components, data access layers, auth modules
   - **Note**: Infrastructure mentioned in scope (e.g., "deployed to ECS from terraform repo")
   - **Expectation**: Your components will RUN INSIDE infrastructure components from other repos

   **Frontend scope** (e.g., "React SPA", "Mobile app"):
   - **Primary focus**: Client-side components, UI layers
   - **Extract**: Frontend application, API clients, authentication flows, client-side state management
   - **Note**: Backend services and CDN mentioned in scope
   - **Expectation**: Your components connect to backend APIs and run on CDN/infrastructure

   **Integration/Operations scope** (e.g., "CI/CD pipeline", "Monitoring"):
   - **Primary focus**: Operational/supporting components
   - **Extract**: Build/deploy tools, monitoring systems, logging infrastructure
   - **Note**: Application and infrastructure components mentioned
   - **Expectation**: Your components OBSERVE or OPERATE ON other components

4. **Cross-reference analysis:**
   - If scope mentions "backend API from api-backend repo", look for how your components interact with it
   - If scope says "deploys to ECS from terraform repo", understand you're providing application logic that needs container hosting
   - Document expected touchpoints with other repositories' contributions

### When Scope is NOT Defined

**Use comprehensive, all-encompassing analysis:**
- Extract ALL components from ALL source types
- Create complete, holistic threat model
- Include application, infrastructure, data, and integration layers
- Standard single-repository analysis approach

## Your Role: Architecture Modeling Only
**Do:** Extract components, trust zones, and data flows  
**Do NOT:** Identify vulnerabilities, threats, security flaws, or speculate about weaknesses  
**Why:** IriusRisk performs all security analysis automatically

## Component Types to Extract

### 1. Application/Functional Components
**From source code, APIs, microservices:**
- **Business Logic Components**: Payment processing, user authentication, order management, reporting engines
- **Application Services**: User management service, notification service, audit service, integration service
- **API Endpoints**: REST APIs, GraphQL endpoints, webhook receivers, internal APIs
- **Background Processes**: Batch jobs, scheduled tasks, data processing pipelines, cleanup services
- **Client Applications**: Web frontends, mobile apps, desktop applications, CLI tools

### 2. Data Components
**From databases, data flows, storage systems:**
- **Data Stores**: SQL databases, NoSQL databases, data warehouses, caches (Redis, Memcached)
- **Data Processing**: ETL pipelines, stream processing, data analytics engines, ML model training
- **Data Storage**: File systems, object storage (S3), content delivery networks, backup systems
- **Data Flows**: Customer data, transaction data, audit logs, analytics data, configuration data

### 3. Infrastructure/Network Components
**From Terraform, cloud configurations, network diagrams:**
- **Compute Resources**: Virtual machines, containers, serverless functions, auto-scaling groups
- **Network Infrastructure**: VPCs, subnets, NAT gateways, internet gateways, VPN connections
- **Load Balancing**: Application load balancers, network load balancers, API gateways, reverse proxies
- **Security Infrastructure**: Firewalls, security groups, NACLs, WAF, DDoS protection

### 4. Cloud Services Components
**From cloud provider configurations:**
- **Serverless**: Lambda functions, Step Functions, EventBridge, SQS, SNS
- **Managed Services**: RDS, DynamoDB, ElastiCache, Elasticsearch, CloudSearch
- **Storage Services**: S3 buckets, EFS, EBS volumes, Glacier, backup services
- **Monitoring/Logging**: CloudWatch, CloudTrail, X-Ray, application monitoring tools
- **Identity/Access**: IAM roles, Cognito, Active Directory, SSO providers

### 5. Integration Components
**From API configurations, message queues, external services:**
- **Message Queues**: SQS, RabbitMQ, Kafka, EventBridge, pub/sub systems
- **External APIs**: Third-party payment processors, social media APIs, mapping services
- **Integration Platforms**: API management platforms, ESBs, webhook processors
- **Communication**: Email services, SMS services, push notification services

### 6. Security/Compliance Components
**From security policies, compliance documentation:**
- **Authentication Systems**: OAuth providers, SAML IdPs, multi-factor authentication
- **Authorization Systems**: Role-based access control, attribute-based access control
- **Encryption Services**: Key management systems, HSMs, certificate authorities
- **Compliance Tools**: Audit logging, compliance monitoring, policy enforcement points

## Source Analysis Strategy

### Phase 1: Repository Scanning and Categorization
1. **Identify all source types** in the repository:
   - Application source code (multiple languages/frameworks)
   - Infrastructure as Code (Terraform, CloudFormation, Kubernetes)
   - Configuration files (Docker, CI/CD, environment configs)
   - Security policies and compliance documentation
   - Architecture documentation and diagrams
   - Database schemas and migration scripts

2. **Catalog components by source type**:
   - Create inventory of what each source type reveals
   - Note overlaps and relationships between sources
   - Identify gaps where components are referenced but not defined

### Phase 2: Component Extraction and Classification

**From Application Code:** Extract business logic (auth services, business domain services, API endpoints, background jobs, data access layers, integrations). Extract components separately from infrastructure—they'll be nested within infrastructure components (containers, VMs). Focus on what business functions exist and how they interact.

**From Infrastructure Code (Terraform/CloudFormation):** Extract cloud resources, security groups/ACLs, load balancers, database instances, monitoring configs, IAM roles, encryption configs.

**From Security Policies/Documentation:** Identify required controls, compliance frameworks, data classification, network segmentation policies, incident response procedures, third-party integration requirements, regulatory compliance (GDPR, HIPAA, SOX).

**From Configuration/Deployment Files:** Discover container definitions, orchestration, environment configs, CI/CD pipelines, monitoring/observability, backup/DR setups.

### Phase 3: Component Consolidation and Relationship Mapping

**1. Merge overlapping components:** Consolidate same logical component appearing in multiple sources into one with comprehensive properties.

**2. Plan nesting hierarchy:**
- Infrastructure layer → Cloud resources, VMs, containers, managed services
- Business logic layer → Application services nested within infrastructure
- Data layer → Databases/storage (nested or standalone)
- Integration layer → External APIs, message queues, third-party services

**3. Establish relationships:** Nesting (business logic within infrastructure), data flows (between components and data stores), network connections (between infrastructure), dependencies (microservices ↔ external APIs), trust relationships (between security domains).

**4. Define trust zones:**
- Internet Zone (trust rating: 1) - Public-facing components, external APIs
- DMZ Zone (3) - Load balancers, web servers, API gateways
- Application Zone (5) - Business logic services, application servers
- Data Zone (7) - Databases, caches, data processing
- Management Zone (8) - Admin interfaces, monitoring, logging
- Security Zone (10) - Authentication services, key management, audit systems

## Component Types to Identify

**Your focus:** Identify what components exist in the architecture, not how to map them to IriusRisk (that comes later).

**Common component categories to extract:**
- **Business logic:** Payment processing, authentication services, authorization, user management, audit logging
- **Data stores:** SQL databases, NoSQL databases, document databases, data warehouses, file storage, caches
- **Cloud services:** Lambda functions, S3 buckets, RDS instances, VPCs, API gateways
- **Infrastructure:** Load balancers, web servers, application servers, container platforms, VMs
- **Integration:** Message queues, external APIs, webhooks, CDNs, third-party services

**Example extraction:**
From Terraform you see: AWS WAF, ALB, ECS Cluster, RDS Database
From code you see: Authentication Service, Payment Service, User API
Result: List these as architectural components (mapping to IriusRisk types happens in the next step)

## Trust Zone Assignment

**Business Logic:** Assign based on data sensitivity
- Public APIs → DMZ or Application Zone (rating: 3-5)
- Internal services → Application Zone (5)
- Data processing → Data Zone (7)
- Admin functions → Management Zone (8)

**Infrastructure:** Assign based on network position
- Internet-facing → Internet or DMZ Zone (1-3)
- Internal networking → Application Zone (5)
- Data storage → Data Zone (7)
- Management tools → Management Zone (8)

**Cloud Services:** Consider managed service security
- Managed databases → Data Zone (7)
- Serverless functions → Application Zone (5)
- Object storage → Data Zone (7)

## Data Flow Patterns

**Cross-Layer Flows:**
1. User Request: Internet → Load Balancer → API Gateway → Business Logic → Database
2. Data Processing: Database → ETL → Analytics → Reporting
3. Integration: External API → Message Queue → Processor → Internal DB
4. Monitoring: All Components → Logging → Monitoring Dashboard → Alerts

**Security-Relevant Flows:** Authentication tokens, sensitive data (PII/financial), audit logs, secrets distribution, backup data

## Quality Assurance Checklist

Before creating OTM, verify:
- ☐ All source types analyzed (code, infrastructure, policies, docs)
- ☐ Component coverage: business logic, data, infrastructure, cloud, integration
- ☐ Data flows connect all related components
- ☐ Trust zones assigned appropriately based on security posture
- ☐ Overlapping components consolidated (no duplication)
- ☐ Single threat model covers entire system end-to-end

## Example: E-Commerce Multi-Source Analysis

**Sources:** Node.js app + Terraform AWS + security policies + API docs

**Extracted Components with Nesting:**
```yaml
components:
  # Infrastructure (from Terraform) - in trust zones
  - id: "ecs-cluster"
    type: "[exact referenceId from components.json]"
    parent: { trustZone: "application" }
  - id: "api-gateway"
    type: "[exact referenceId from components.json]"
    parent: { trustZone: "dmz" }
    
  # Business Logic (from code) - nested in infrastructure
  - id: "user-service"
    type: "[exact referenceId from components.json]"
    parent: { component: "ecs-cluster" }  # nested in ECS
  - id: "payment-processor"
    type: "[exact referenceId from components.json]"
    parent: { component: "ecs-cluster" }  # nested in ECS
    
  # Data Layer - can be nested or standalone
  - id: "user-database"
    type: "[exact referenceId from components.json]"
    parent: { trustZone: "data" }

dataflows:
  - id: "user-registration"
    source: "api-gateway"
    destination: "user-service"
  - id: "payment-processing"
    source: "payment-processor"
    destination: "payment-api"
```

## Workflow Integration

1. Call analyze_source_material() for guidance
2. Call create_threat_model() for OTM creation workflow
3. Execute: sync() → create OTM → import_otm() → project_status() → sync()

Result: Single, comprehensive threat model for holistic IriusRisk analysis across all system layers.
