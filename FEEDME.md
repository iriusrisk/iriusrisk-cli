# IriusRisk CLI - AI Architectural Guide

## Purpose

This document defines the architectural patterns, structures, and conventions that AI assistants should follow when making changes to the IriusRisk CLI codebase. It serves as the authoritative guide for maintaining consistency and quality.

## Core Architectural Principles

### 1. MCP Tool Architecture - Consistent User Experience Across Transports

**Philosophy: Maximum Feature Parity Between stdio and HTTP Modes**

The MCP (Model Context Protocol) server operates in two transport modes - stdio (for local AI assistants like Cursor, Claude Desktop) and HTTP (for remote/web access). **The goal is to provide as close to identical capabilities as possible**, regardless of which transport is used.

**Key Principle: Same Tool, Different Implementation**

A tool should be available in both modes unless there's a fundamental technical reason preventing it. The implementation may vary significantly, but the user experience should be consistent:

```python
# Example: search_components tool

# Stdio implementation - reads from local file
async def search_components_stdio(query: str, limit: int = 20):
    """Search from .iriusrisk/components.json"""
    with open('.iriusrisk/components.json') as f:
        components = json.load(f)
    return search_in_memory(components, query, limit)

# HTTP implementation - API call with caching
async def search_components_http(query: str, limit: int = 20):
    """Search via API with session caching"""
    components = await get_components_cached(api_client, mcp_server)
    return search_in_memory(components, query, limit)
```

Both implementations return the same JSON structure, use the same parameters, and provide the same user experience. The difference is invisible to the AI assistant.

**Decision Matrix: Should This Tool Be Available in Both Modes?**

Ask these questions when deciding tool availability:

1. **Can it work without filesystem state?** → Available in HTTP mode
2. **Can it work with filesystem state OR API calls?** → Available in stdio mode
3. **Is there a fundamental incompatibility?** → Mode-specific only

**Examples:**

| Tool | Stdio | HTTP | Reasoning |
|------|-------|------|-----------|
| `search_components` | ✅ | ✅ | Same data, different source (file vs API) |
| `list_projects` | ✅ | ✅ | API call works in both modes |
| `import_otm` | ✅ | ✅ | Takes file path (stdio) or content string (HTTP) |
| `sync` | ✅ | ❌ | Fundamentally requires filesystem to write `.iriusrisk/` |
| `update_threat_status` | ✅ | ✅ | Both can make API calls (stdio adds local tracking) |
| `generate_report` | ✅ | ✅ | Saves to file (stdio) or returns base64 (HTTP) |

**Tool Organization:**

Tools are organized into three categories:

1. **Shared Tools** (`mcp/tools/shared_tools.py`)
   - Available in both modes with identical implementation
   - Example: Guidance/instruction tools that return static markdown
   - No API calls, no filesystem access

2. **Mode-Specific Implementations** (same tool name, different files)
   - Tool available in both modes but with different implementations
   - Example: `search_components` (filesystem in stdio, API in HTTP)
   - Register in both `stdio_tools.py` and `http_tools.py`

3. **Truly Mode-Specific Tools** (rare)
   - Only when fundamentally incompatible with the other mode
   - Example: `sync` (requires filesystem write capability)

**Implementation Patterns:**

**Pattern 1: Data Access Tools (Different Sources, Same Interface)**
```python
# Stdio: Read from local .iriusrisk/*.json files
async def search_threats_stdio(query=None, risk_level=None, limit=20):
    threats = json.load(open('.iriusrisk/threats.json'))
    return _search_threats_in_memory(threats, query, risk_level, limit)

# HTTP: API call with caching
async def search_threats_http(project_id, query=None, risk_level=None, limit=20):
    threats = await _get_threats_cached(api_client, mcp_server, project_id)
    return _search_threats_in_memory(threats, query, risk_level, limit)
```

**Pattern 2: Output Format Variations**
```python
# Stdio: Save to file, return file path
async def generate_report_stdio(project_id, report_type, format):
    content = api_client.generate_report(...)
    filepath = save_to_file(content, f'.iriusrisk/reports/{report_type}.{format}')
    return f"✅ Report saved to: {filepath}"

# HTTP: Return base64 encoded content
async def generate_report_http(project_id, report_type, format):
    content = api_client.generate_report(...)
    encoded = base64.b64encode(content).decode('ascii')
    return f"✅ Report generated:\n{encoded}"
```

**Pattern 3: State Management Differences**
```python
# Stdio: Update API + track locally for future sync
async def update_threat_status_stdio(threat_id, status, reason):
    api_client.update_threat_status(threat_id, status)
    track_update_locally(threat_id, status, reason)  # For pending_updates.json
    return "✅ Status updated (will sync on next sync command)"

# HTTP: Direct API update only
async def update_threat_status_http(project_id, threat_id, status, reason):
    api_client.update_threat_status(project_id, threat_id, status)
    return "✅ Status updated"
```

**Benefits of This Approach:**

1. **Consistent UX**: AI assistants learn one set of tools, not two
2. **Mode switching**: Users can switch between stdio/HTTP without relearning
3. **Documentation**: One reference doc covers both modes
4. **Testing**: Shared logic can be tested once
5. **Flexibility**: Implementation can evolve independently per mode

**Anti-Pattern: Don't Create Mode-Specific Tool Names**

```python
# ❌ WRONG - Different tool names for same functionality
async def search_components_local(...)  # Stdio version
async def search_components_api(...)    # HTTP version

# ✅ CORRECT - Same tool name, register in both modes
async def search_components(...)        # Implementation varies by mode
```

**Documentation Requirement:**

When adding or modifying MCP tools, document:
1. Which modes support the tool
2. Any parameter differences between modes
3. Any output format differences
4. Why any mode-specific exclusions exist

**Exception: Search Tools in Stdio Mode**

One important exception to the "maximize feature parity" principle:

**Don't provide search/filter tools for local JSON files in stdio mode.**

When AI assistants have direct filesystem access (stdio mode), they can read `.iriusrisk/*.json` files directly and perform more flexible and powerful analysis than pre-built search tools can offer.

**Example - HTTP Mode (Needs Search Tools):**
```python
# HTTP mode: AI cannot read files, needs search tools
search_components(query="lambda", category="AWS", limit=20)
```

**Example - Stdio Mode (Direct File Access Better):**
```python
# Stdio mode: AI reads file directly, can do arbitrary analysis
components = json.load(open('.iriusrisk/components.json'))
aws_lambda = [c for c in components 
              if 'aws' in c['category'].lower() and 'lambda' in c['name'].lower()]
# AI can then cross-reference with other files, perform complex filtering, etc.
```

**Tools intentionally NOT in stdio mode:**
- `search_components` - AI reads `.iriusrisk/components.json` directly
- `get_component_categories` - AI extracts from components.json directly
- `get_trust_zones` - AI reads `.iriusrisk/trust-zones.json` directly
- `search_threats` - AI reads `.iriusrisk/threats.json` directly
- `search_countermeasures` - AI reads `.iriusrisk/countermeasures.json` directly

This provides better user experience because AI can perform more sophisticated analysis than pre-built search tools allow.

**Validation Checklist:**

Before finalizing MCP tool changes:
- [ ] Have I maximized feature parity between modes (except search tools for local JSON)?
- [ ] Are mode-specific exclusions justified by technical constraints or direct file access?
- [ ] Do both implementations return compatible data structures?
- [ ] Is the user experience consistent across modes?
- [ ] Have I documented any unavoidable differences?

### 2. Dependency Injection (DI) - MANDATORY

**Use the Container system exclusively** - never create instances directly.

```python
# ✅ CORRECT - Use dependency injection
from ..container import get_container

def my_command():
    container = get_container()
    project_service = container.get(ProjectService)
    api_client = container.get(IriusRiskApiClient)

# ❌ WRONG - Direct instantiation
def my_command():
    api_client = ProjectApiClient()  # NEVER DO THIS
    service = ProjectService()       # NEVER DO THIS
```

**Container Registration Pattern:**
- All services MUST be registered in `container.py`
- Use factory functions for complex initialization
- Maintain singleton lifecycle for stateful services

**Exception: MCP HTTP Mode Per-Request Authentication**

The MCP HTTP server (`mcp/http_server.py`, `mcp/auth.py`) is an accepted exception to the DI rule. In HTTP mode, each request carries its own credentials (either via OAuth token mapping or direct API key headers), requiring per-request API client instantiation:

```python
# ✅ ACCEPTED in mcp/auth.py and mcp/http_server.py ONLY
# HTTP mode creates request-scoped API clients because credentials vary per-request
config = Config()
config._api_key = credentials_from_request['api_key']
config._hostname = credentials_from_request['hostname']
api_client = IriusRiskApiClient(config)
```

This pattern is necessary because:
- The DI Container assumes application-wide configuration
- HTTP mode supports multi-tenant scenarios where each request may use different IriusRisk instances
- Credentials are extracted from request headers or OAuth token mappings at runtime

The stdio mode correctly uses the Container pattern since credentials are configured once at startup.

### 2. Configuration and Project Discovery

**Use Config class for all configuration access** - never access `os.environ` directly.

```python
# ✅ CORRECT - Use Config class
from ..config import Config

def get_project_info():
    config = Config()
    project_config = config.get_project_config()
    project_id = config.get_default_project_id()
    return project_config, project_id

# ❌ WRONG - Direct environment or filesystem access
import os
def get_project_info():
    return os.environ.get('PROJECT_ID')  # NEVER DO THIS
```

**Project Root Discovery:**

Use the centralized discovery utility from `utils/project_discovery.py`:

```python
# ✅ CORRECT - Use centralized discovery
from ..utils.project_discovery import find_project_root

def locate_project():
    project_root, config = find_project_root()
    if config:
        project_id = config.get('id')
    return project_root, config
```

The `find_project_root()` function provides sophisticated discovery:
- Checks workspace environment variables (IDEs like Cursor, VS Code)
- Walks up parent directories from current location
- Checks common project directories under home
- Returns project root path and parsed configuration

**Project ID Resolution:**

Use utilities from `utils/project_resolution.py`:

```python
# ✅ CORRECT - Use centralized resolution
from ..utils.project_resolution import (
    resolve_project_id_to_uuid_strict,
    is_uuid_format
)

# Convert reference ID to UUID (raises on failure)
uuid = resolve_project_id_to_uuid_strict(project_id, api_client)

# Check if string is UUID format
if is_uuid_format(project_id):
    # It's already a UUID
```

### 3. Error Handling - Use Structured Approach

**Always use the error handling infrastructure** from `utils/error_handling.py`.

```python
# ✅ CORRECT - Use structured error handling
from ..utils.error_handling import safe_api_call, log_error, ValidationError

try:
    result = safe_api_call(api_client.get_project, project_id, operation="get project")
except ValidationError as e:
    log_error(e, operation="project retrieval")
    raise
except IriusRiskApiError as e:
    log_error(e, operation="project retrieval")
    return None

# ❌ WRONG - Bare exception handling
try:
    result = api_client.get_project(project_id)
except Exception:  # NEVER DO THIS - too broad
    continue

# ❌ WRONG - Silent failures
try:
    result = api_client.get_project(project_id)
except Exception as e:
    pass  # NEVER swallow exceptions silently
```

**Exception Handling Patterns by Context:**

**In CLI Commands** - Convert to user-friendly errors:
```python
try:
    # Operation
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    click.echo(f"❌ Error: {e}", err=True)
    raise click.ClickException(str(e))
except IriusRiskApiError as e:
    logger.error(f"API error: {e}")
    click.echo(f"❌ API Error: {e}", err=True)
    raise click.ClickException(str(e))
```

**In MCP Tools** - Return error strings (don't raise):
```python
try:
    # Operation
    return "✅ Success message"
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return f"❌ Operation failed: {e}"
```

**In Services/Repositories** - Use specific exceptions, let them propagate:
```python
try:
    return api_client.get_data()
except requests.HTTPError as e:
    if e.response.status_code == 404:
        raise IriusRiskApiError("Resource not found", status_code=404)
    elif e.response.status_code == 401:
        raise IriusRiskApiError("Authentication failed", status_code=401)
    else:
        raise IriusRiskApiError(f"API error: {e}", status_code=e.response.status_code)
```

### 4. Logging - Use Centralized Configuration

**Always use the logging infrastructure** from `utils/logging_config.py`.

```python
# ✅ CORRECT - Use structured logging
from ..utils.logging_config import setup_logging, LoggedOperation
import logging

logger = logging.getLogger(__name__)

def my_operation():
    with LoggedOperation(logger, "project sync") as op:
        # Operation code here
        pass

# ❌ WRONG - Ad-hoc logging
import logging
logging.basicConfig()  # NEVER DO THIS
```

**MCP Logging:**

For MCP server commands, use the specialized MCP logging setup:

```python
from ..utils.mcp_logging import setup_mcp_logging

def mcp(cli_ctx):
    setup_mcp_logging(cli_ctx)
    # MCP server code
```

This ensures logging doesn't interfere with MCP protocol communication over stdout/stderr.

## Directory Structure and Organization

### Source Code Layout

```
src/iriusrisk_cli/
├── commands/           # CLI command implementations
├── api/               # API client implementations  
├── services/          # Business logic services
├── repositories/      # Data access layer
├── utils/            # Shared utilities
├── container.py      # DI container
├── config.py         # Configuration management
└── main.py           # Application entry point
```

### Module Responsibilities and Boundaries

Understanding where code belongs is critical for consistency.

**Commands (`commands/`):**
- **Purpose**: CLI interface implementation only
- **Responsibilities**:
  - Parse command-line arguments with Click
  - Get dependencies from DI container
  - Call service methods
  - Format and display output to user
  - Handle Click-specific errors
- **DO**: Handle user I/O, call services
- **DON'T**: Business logic, API calls, data transformation
- **Dependencies**: Services (via Container), utils for formatting

**Services (`services/`):**
- **Purpose**: Business logic and orchestration
- **Responsibilities**:
  - Implement complex business operations
  - Orchestrate multiple repositories
  - Handle cross-cutting concerns
  - Validate business rules
- **DO**: Business logic, coordinate repositories, complex operations
- **DON'T**: Direct API calls (use repositories), CLI formatting, direct instantiation
- **Dependencies**: Repositories (via constructor injection)

**Repositories (`repositories/`):**
- **Purpose**: Data access layer, abstract API details
- **Responsibilities**:
  - Wrap API client methods
  - Simple CRUD operations (Create, Read, Update, Delete)
  - Transform API responses to domain models
  - Handle pagination if needed
- **DO**: Simple data access, API client wrappers
- **DON'T**: Business logic, orchestration, call other repositories
- **Dependencies**: API clients (via constructor injection)

**API Clients (`api/`):**
- **Purpose**: HTTP communication with IriusRisk API
- **Responsibilities**:
  - Make HTTP requests
  - Handle authentication (tokens, headers)
  - Serialize requests, deserialize responses
  - Translate HTTP errors to domain exceptions
- **DO**: HTTP operations, error translation
- **DON'T**: Business logic, data transformation beyond basic serialization
- **Dependencies**: Config (for API URLs and tokens)

**Utils (`utils/`):**
- **Purpose**: Shared utility functions without state
- **Responsibilities**:
  - Pure functions (no side effects when possible)
  - Formatting, validation, conversion
  - Reusable helpers
- **DO**: Stateless functions, pure logic, formatting
- **DON'T**: Complex business logic (that belongs in services), maintain state
- **When util becomes service**: If it needs dependency injection, state, or orchestrates multiple operations

**Decision Tree - Where Does My Code Go?**
```
Is it CLI input/output? → Command
Is it business logic/orchestration? → Service
Is it data access/API wrapper? → Repository
Is it HTTP communication? → API Client
Is it a stateless helper? → Utils
```

## Coding Patterns and Standards

### 1. Understanding Config vs Container vs CLI Context

These three systems have distinct purposes - don't confuse them:

**Config (`config.py`):**
- **Purpose**: Access environment variables and configuration files
- **Scope**: Application-wide configuration (API URLs, tokens, project config)
- **Lifecycle**: Created per-operation or injected via Container
- **Use when**: Reading `.env` files, environment variables, `.iriusRisk/project.json`

```python
# ✅ CORRECT - Use Config class
from ..config import Config

def my_function():
    config = Config()  # Loads .env automatically
    api_url = config.api_base_url
    token = config.api_token
    project_id = config.get_default_project_id()

# ❌ WRONG - Direct environment access
import os
def my_function():
    api_url = os.environ.get('IRIUS_HOSTNAME')  # NEVER DO THIS
```

**Container (`container.py`):**
- **Purpose**: Dependency injection, manage service lifecycle
- **Scope**: Wiring dependencies, singleton management
- **Lifecycle**: One container per context (global default, or test-specific)
- **Use when**: Getting service instances, repositories, API clients

```python
# ✅ CORRECT - Use Container for services
from ..container import get_container
from ..services.project_service import ProjectService

def my_command():
    container = get_container()
    project_service = container.get(ProjectService)
    result = project_service.perform_operation()
```

**CLI Context (`cli_context.py`):**
- **Purpose**: Pass Click context and default values through command chain
- **Scope**: Per-CLI invocation session state
- **Lifecycle**: Created by Click at CLI entry, passed through commands
- **Use when**: Need default project ID, logging config, or values from parent commands

```python
# ✅ CORRECT - Use CLI Context for user session data
from ..cli_context import pass_cli_context

@click.command()
@click.option('--project-id')
@pass_cli_context
def my_command(cli_ctx, project_id):
    if not project_id:
        project_id = cli_ctx.get_default_project_id()  # From context
```

**Summary:**
- **Config** = Environment variables and config files
- **Container** = Service instances and dependency wiring
- **CLI Context** = User session state and defaults from parent commands

### 2. Project ID Resolution

**CRITICAL**: Always use centralized project resolution utilities from `utils/project_resolution.py`.

**The IriusRisk V2 API requires UUIDs in URL paths**, but users may provide reference IDs (like `badger-app-fgqj`). Resolution must happen **once, at the service layer, before any API calls**.

**Correct Pattern:**
```python
# ✅ CORRECT - Resolve once at the start of service method
from ..utils.project_resolution import resolve_project_id_to_uuid

def my_service_method(self, project_id: str):
    # Resolve FIRST, before any API calls
    logger.debug(f"Resolving project ID to UUID: {project_id}")
    final_project_id = resolve_project_id_to_uuid(project_id)
    logger.debug(f"Resolved to UUID: {final_project_id}")
    
    # Now use the UUID for all repository/API calls
    result = self.project_repository.get_artifacts(final_project_id)
    return result
```

**NEVER use try/catch fallback mechanisms:**
```python
# ❌ WRONG - Fallback mechanism (see "Try/Catch Fallback Mechanisms" anti-pattern)
def my_service_method(self, project_id: str):
    try:
        # Try with whatever we got
        result = self.project_repository.get_artifacts(project_id)
    except Exception as e:
        # Fallback: try to resolve if it failed
        if "404" in str(e) or "400" in str(e):  # NEVER DO THIS
            project_data = self.project_repository.get_by_id(project_id)
            final_id = project_data.get('id')
            result = self.project_repository.get_artifacts(final_id)
    return result
```

**Why this pattern is prohibited:**
This is a specific instance of the general "Try/Catch Fallback Mechanism" anti-pattern (see Anti-Patterns section). For project IDs specifically:
- Resolution logic should be explicit and upfront, not hidden in error paths
- The API requires UUIDs; we should provide them, not rely on error messages to discover format issues
- Resolution should happen once at service layer, not scattered across repositories

**Layer Responsibilities:**
- **Services**: MUST resolve project IDs to UUIDs before calling repositories
- **Repositories**: SHOULD assume they receive UUIDs, not perform resolution
- **API Clients**: MUST use exactly what they receive (no resolution logic)

**Available Resolution Functions:**
```python
from ..utils.project_resolution import (
    resolve_project_id_to_uuid,        # Returns best-effort UUID
    resolve_project_id_to_uuid_strict,  # Raises exception if not found
    is_uuid_format                      # Check if already a UUID
)
```

### 3. API Client Architecture (Composition Pattern)

**Understanding the API Client Structure:**

The codebase uses a composite API client pattern:
- `IriusRiskApiClient` (main client) contains specialized clients
- Each specialized client handles one domain (projects, threats, etc.)

```python
# ✅ CORRECT - Get specialized client from main client
from ..api_client import IriusRiskApiClient
from ..container import get_container

container = get_container()
main_client = container.get(IriusRiskApiClient)

# Access specialized clients
project_data = main_client.project_client.get_project(uuid)
threats = main_client.threat_client.get_threats(project_id)
```

**When creating repositories**, inject the specialized client:
```python
# In container.py
self._factories[ProjectRepository] = lambda: ProjectRepository(
    api_client=self.get(IriusRiskApiClient).project_client  # Note: .project_client
)
```

**Never create API clients directly** - always use Container:
```python
# ❌ WRONG - Direct instantiation
from ..api.project_client import ProjectApiClient
api_client = ProjectApiClient()  # NEVER DO THIS

# ✅ CORRECT - Use Container
from ..container import get_container
container = get_container()
project_service = container.get(ProjectService)  # Service has injected clients
```

### 4. Update Tracking Pattern

**For tracking threat and countermeasure status changes**, use the update tracker:

```python
# ✅ CORRECT - Use update tracker from utils
from ..utils.updates import get_update_tracker

def track_threat_status_change(threat_id: str, new_status: str, reason: str):
    tracker = get_update_tracker()
    tracker.track_threat_update(
        threat_id=threat_id,
        status=new_status,
        reason=reason,
        comment="Optional detailed comment"
    )
    # Updates are persisted to .iriusRisk/updates.json

def get_pending_updates():
    tracker = get_update_tracker()
    return tracker.get_pending_updates()
```

**Update Tracker Usage:**
- Tracks changes locally before syncing to IriusRisk API
- Stores updates in `.iriusRisk/updates.json`
- Provides `track_threat_update()`, `track_countermeasure_update()`, `track_issue_creation()`
- Used primarily in MCP commands for AI-driven status updates

### 5. File Operations

**Use Path objects** and proper error handling for all file operations.

```python
# ✅ CORRECT - Use Path and error handling
from pathlib import Path
from ..utils.error_handling import validate_file_exists

def read_config_file(file_path: str):
    path = Path(file_path)
    validate_file_exists(str(path), operation="read config")
    
    try:
        with path.open('r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {path}: {e}")

# ❌ WRONG - String paths and poor error handling
def read_config_file(file_path):
    with open(file_path, 'r') as f:  # No validation
        return json.load(f)          # No error handling
```

## Anti-Patterns to Avoid

### 1. Direct Instantiation
```python
# ❌ NEVER DO THIS
api_client = ProjectApiClient()
service = ProjectService()
```

### 2. Global State Access
```python
# ❌ NEVER DO THIS
from ..config import config  # Global instance (doesn't exist)
from ..service_factory import service_factory  # Global instance (doesn't exist)
```

### 3. Bare Exception Handling
```python
# ❌ NEVER DO THIS
try:
    risky_operation()
except Exception:
    pass  # Silent failures
```

### 4. Bypassing Abstraction Layers

**CRITICAL**: Each layer has a defined responsibility. Bypassing layers violates separation of concerns and makes code fragile.

**Common Layer Violations:**

```python
# ❌ NEVER DO THIS - Commands bypassing services
@click.command()
def my_command():
    # Command directly calling repository/API
    container = get_container()
    project_repository = container.get(ProjectRepository)  # Wrong layer!
    result = project_repository.get_by_id(project_id)
    
# ✅ CORRECT - Commands use services
@click.command()
def my_command():
    container = get_container()
    project_service = container.get(ProjectService)  # Correct!
    result = project_service.get_project(project_id)
```

```python
# ❌ NEVER DO THIS - Services making direct HTTP calls
class MyService:
    def process_data(self, project_id: str):
        # Service making HTTP request directly
        response = requests.get(f"{api_url}/projects/{project_id}")  # Wrong!
        return response.json()

# ✅ CORRECT - Services use repositories
class MyService:
    def __init__(self, project_repository: ProjectRepository):
        self.project_repository = project_repository
    
    def process_data(self, project_id: str):
        return self.project_repository.get_by_id(project_id)
```

```python
# ❌ NEVER DO THIS - Bypassing Config abstraction
import os
def get_api_settings():
    api_url = os.environ.get('IRIUSRISK_API_URL')  # Wrong!
    token = os.environ.get('IRIUSRISK_API_TOKEN')
    return api_url, token

# ✅ CORRECT - Use Config class
from ..config import Config
def get_api_settings():
    config = Config()
    return config.api_base_url, config.api_token
```

```python
# ❌ NEVER DO THIS - Repositories orchestrating multiple operations
class ProjectRepository:
    def get_project_with_threats(self, project_id: str):
        # Repository orchestrating multiple data sources - wrong layer!
        project = self.api_client.get_project(project_id)
        threats = self.threat_api_client.get_threats(project_id)
        return {**project, 'threats': threats}

# ✅ CORRECT - Services orchestrate, repositories fetch
class ProjectService:
    def __init__(self, project_repository, threat_repository):
        self.project_repository = project_repository
        self.threat_repository = threat_repository
    
    def get_project_with_threats(self, project_id: str):
        project = self.project_repository.get_by_id(project_id)
        threats = self.threat_repository.list_all(project_id)
        return {**project, 'threats': threats}
```

**Why this is prohibited:**
- **Tight coupling**: Bypassing layers creates dependencies that shouldn't exist
- **Harder to test**: Can't mock intermediate layers when they're bypassed
- **Violates single responsibility**: Each layer should have one clear purpose
- **Difficult to maintain**: Changes to lower layers break higher layers
- **Defeats architecture**: The layer structure exists for good reasons

**The Layer Contract:**
```
Commands → Services → Repositories → API Clients → HTTP
   ↓          ↓            ↓
  I/O    Business Logic   Data Access
```

Each layer should **only call the layer directly below it**, never skip layers.

### 5. Hardcoded Values
```python
# ❌ NEVER DO THIS
if len(project_id) == 36 and project_id.count('-') == 4:  # Magic numbers
    # UUID detection logic
```

### 6. Importing from Commands
```python
# ❌ NEVER DO THIS (except in tests)
from ..commands.mcp import _find_project_root_and_config

# ✅ DO THIS INSTEAD
from ..utils.project_discovery import find_project_root
```

### 7. Try/Catch Fallback Mechanisms

**CRITICAL**: Using try/catch as a fallback mechanism is prohibited. Error handling should be for **exceptional cases**, not for **control flow**.

**Fallback Mechanism Anti-Pattern:**
```python
# ❌ NEVER DO THIS - Using exceptions for control flow
def get_data(self, input_value: str):
    try:
        # Try optimistically with one assumption
        return self.api_client.get_by_uuid(input_value)
    except Exception as e:
        # Parse error and try alternate approach
        if "404" in str(e) or "400" in str(e) or "Not Found" in str(e):
            # Different approach
            resolved = self.resolve_to_uuid(input_value)
            return self.api_client.get_by_uuid(resolved)
        raise

# ❌ ALSO WRONG - Multiple fallback attempts
def process_item(self, identifier: str):
    try:
        return self.method_a(identifier)
    except:
        try:
            return self.method_b(identifier)
        except:
            return self.method_c(identifier)
```

**Correct Pattern - Determine Intent Upfront:**
```python
# ✅ CORRECT - Determine what to do BEFORE making calls
def get_data(self, input_value: str):
    # Validate and normalize input FIRST
    normalized_value = self.validate_and_normalize(input_value)
    
    # Now make the call with correct input
    return self.api_client.get_by_uuid(normalized_value)

# ✅ CORRECT - Use conditional logic, not exception handling
def process_item(self, identifier: str):
    # Determine the correct approach upfront
    if self.is_uuid_format(identifier):
        return self.process_by_uuid(identifier)
    elif self.is_reference_id_format(identifier):
        uuid = self.resolve_reference_to_uuid(identifier)
        return self.process_by_uuid(uuid)
    else:
        raise ValidationError(f"Invalid identifier format: {identifier}")
```

**Why fallback mechanisms are prohibited:**

1. **Fragile**: String matching on error messages (`"404" in str(e)`) breaks when API changes error format
2. **Slow**: Makes failed API calls before making correct ones (doubles latency, wastes resources)
3. **Violates separation of concerns**: Logic scattered across error paths instead of being explicit
4. **Unpredictable**: Same code behaves differently based on error responses
5. **Hard to debug**: Control flow depends on runtime failures rather than explicit logic
6. **Masks real errors**: Legitimate errors may be caught and handled incorrectly
7. **Poor performance under failure**: System is slowest when things go wrong

**When Error Handling IS Appropriate:**

Error handling should be used for **truly exceptional cases**:
```python
# ✅ CORRECT - Handling genuine errors
def get_project(self, project_uuid: str):
    try:
        return self.api_client.get_project(project_uuid)
    except NetworkError as e:
        # Network failure is exceptional
        logger.error(f"Network error fetching project: {e}")
        raise IriusRiskApiError(f"Failed to connect to API: {e}")
    except Timeout as e:
        # Timeout is exceptional
        logger.error(f"Timeout fetching project: {e}")
        raise IriusRiskApiError(f"API request timed out: {e}")
```

**The Principle:**
- **Exceptions are for exceptional circumstances** (network failures, timeouts, unexpected API changes)
- **Conditionals are for business logic** (UUID vs reference ID, different input formats, user choices)
- If you can determine what to do upfront, use conditional logic
- If you're catching exceptions to try alternate approaches, you're doing control flow wrong

**Common Indicators of Fallback Mechanism Abuse:**
- Comments like "First try..." or "If that fails..." or "Fallback to..."
- String matching on error messages
- Nested try/except blocks
- `except:` followed by alternate approach rather than error handling
- Same operation called twice with different parameters

## Testing Patterns

### 1. Use Dependency Injection in Tests

```python
# ✅ CORRECT - DI in tests
def test_my_function():
    container = Container()
    mock_service = Mock()
    container.register_instance(ProjectService, mock_service)
    
    result = my_function_with_container(container)
    assert result is not None

# ❌ WRONG - Global patching
@patch('module.ProjectService')
def test_my_function(mock_service):
    result = my_function()  # Uses global state
```

### 2. Avoid Wildcard Imports

```python
# ✅ CORRECT - Explicit imports
from tests.utils.fixtures import project_fixture, api_fixture

# ❌ WRONG - Wildcard imports
from tests.utils.fixtures import *  # Makes dependencies unclear
```

## Command Implementation Template

When creating new commands, follow this template:

```python
"""Command module docstring."""

import click
import logging
from typing import Optional

from ..cli_context import pass_cli_context
from ..container import get_container
from ..services.project_service import ProjectService
from ..utils.logging_config import LoggedOperation
from ..utils.error_handling import log_error
from ..exceptions import IriusRiskApiError, ValidationError

logger = logging.getLogger(__name__)

@click.command()
@click.option('--project-id', help='Project ID or reference')
@pass_cli_context
def my_command(cli_ctx, project_id: Optional[str] = None):
    """Command description."""
    
    # Get dependencies via DI container
    container = get_container()
    project_service = container.get(ProjectService)
    
    try:
        with LoggedOperation(logger, "my operation") as op:
            # Resolve project ID if needed
            if not project_id:
                project_id = cli_ctx.get_default_project_id()
                if not project_id:
                    raise ValidationError("No project ID provided and no default project configured")
            
            # Perform operation
            result = project_service.perform_operation(project_id)
            
            # Output results
            click.echo(f"Operation completed: {result}")
            
    except ValidationError as e:
        log_error(e, operation="my command")
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))
    except IriusRiskApiError as e:
        log_error(e, operation="my command")
        click.echo(f"API Error: {e}", err=True)
        raise click.ClickException(str(e))
    except Exception as e:
        log_error(e, operation="my command")
        click.echo(f"Unexpected error: {e}", err=True)
        raise
```

## Service Implementation Template

When creating new services, follow this template:

```python
"""Service module docstring."""

import logging
from typing import List, Optional, Dict, Any

from ..repositories.project_repository import ProjectRepository
from ..exceptions import IriusRiskApiError, ValidationError
from ..utils.error_handling import safe_api_call

logger = logging.getLogger(__name__)

class MyService:
    """Service description."""
    
    def __init__(self, project_repository: ProjectRepository):
        """Initialize service with dependencies."""
        self.project_repository = project_repository
    
    def perform_operation(self, project_id: str) -> Dict[str, Any]:
        """Perform business operation."""
        
        # Validate inputs
        if not project_id:
            raise ValidationError("Project ID is required")
        
        # Perform operation with error handling
        try:
            result = safe_api_call(
                self.project_repository.get_project,
                project_id,
                operation="get project"
            )
            
            # Business logic here
            processed_result = self._process_result(result)
            
            logger.info(f"Operation completed for project {project_id}")
            return processed_result
            
        except IriusRiskApiError as e:
            logger.error(f"API error in operation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in operation: {e}")
            raise
    
    def _process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Private method for result processing."""
        # Implementation here
        return result
```

## Validation Checklist

Before submitting any code changes, verify:

**Dependency Injection:**
- [ ] Uses DI Container for all services, repositories, and API clients
- [ ] No direct instantiation of API clients, services, or repositories
- [ ] No imports of deprecated globals

**Configuration & Discovery:**
- [ ] Uses Config class for all environment/config access (no direct `os.environ` access)
- [ ] Uses centralized utilities (no bypassing abstractions)
- [ ] Uses `is_uuid_format()` instead of magic number UUID detection
- [ ] Uses project resolution utilities from `utils/project_resolution.py`
- [ ] Project ID resolution happens ONCE at service layer
- [ ] Uses `find_project_root()` from `utils/project_discovery.py` for discovery
- [ ] Does NOT import from `commands/mcp.py` (except in tests)

**Error Handling:**
- [ ] Uses structured error handling from `utils/error_handling.py`
- [ ] No bare `except Exception:` without re-raising or logging
- [ ] No silent exception swallowing (`except: pass`)
- [ ] Specific exceptions (ValidationError, IriusRiskApiError) used appropriately
- [ ] No try/catch fallback mechanisms (exceptions are for errors, not control flow)
- [ ] Input validation and normalization happens upfront, not in error handlers

**Architecture & Organization:**
- [ ] Code is in correct module (command/service/repository/utils)
- [ ] Services contain business logic, not commands
- [ ] Repositories only do data access, no business logic
- [ ] Utils are stateless functions
- [ ] No layer bypassing (commands call services, services call repositories, etc.)
- [ ] Each layer only calls the layer directly below it
- [ ] Follows established naming conventions

**Code Quality:**
- [ ] Uses logging infrastructure properly (not print statements)
- [ ] Includes proper input validation
- [ ] Has appropriate error messages
- [ ] Uses Path objects for file operations
- [ ] No hardcoded values or magic numbers
- [ ] Proper type hints where applicable
- [ ] Includes docstrings for public functions/classes

## Quick Reference Guide

When making changes, remember these key principles:

**Getting Dependencies:**
```python
# ✅ Always do this
from ..container import get_container
container = get_container()
service = container.get(ProjectService)
```

**Getting Configuration:**
```python
# ✅ Always do this
from ..config import Config
config = Config()
api_url = config.api_base_url
```

**Project Discovery:**
```python
# ✅ Always do this
from ..utils.project_discovery import find_project_root
project_root, config = find_project_root()
```

**Checking UUIDs:**
```python
# ✅ Always do this
from ..utils.project_resolution import is_uuid_format
if is_uuid_format(value):
```

**Handling Errors:**
```python
# ✅ Always do this
from ..exceptions import IriusRiskApiError, ValidationError
try:
    # operation
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise
```

**NEVER Do These:**
- ❌ `api_client = ProjectApiClient()` - use Container
- ❌ `from ..config import config` - no global exists, use `Config()`
- ❌ `os.environ.get('VAR')` - use Config class (don't bypass abstractions)
- ❌ Commands calling repositories directly - use services (respect layer boundaries)
- ❌ `if len(x) == 36 and x.count('-') == 4:` - use `is_uuid_format()`
- ❌ `except Exception: pass` - always log or re-raise
- ❌ Import from `commands/mcp.py` - except in tests
- ❌ Try/catch fallback mechanisms - determine intent upfront, don't use exceptions for control flow

**Where Does My Code Go?**
- User I/O and CLI args → **Command**
- Business logic and orchestration → **Service**
- API wrappers and data access → **Repository**
- Stateless helpers → **Utils**

## Architectural Principles Summary

When in doubt about architectural decisions:

1. **Favor dependency injection** over direct instantiation
2. **Favor centralized utilities** over duplication
3. **Favor explicit error handling** over silent failures
4. **Favor structured logging** over print statements
5. **Favor configuration classes** over environment variables
6. **Favor Path objects** over string paths
7. **Favor specific exceptions** over generic ones
8. **Favor upfront validation** over try/catch fallback mechanisms
9. **Favor conditional logic** over exceptions for control flow
10. **Respect layer boundaries** - each layer only calls the layer directly below it

**If you're unsure**: Ask for clarification rather than guess. Check this guide first, then review existing properly-architected command files as examples.

---

This document should be updated as architectural patterns evolve. All AI assistants working on this codebase must reference this guide to maintain consistency and quality.
