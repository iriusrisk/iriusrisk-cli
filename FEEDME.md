# IriusRisk CLI - AI Architectural Guide

## Purpose

This document defines the architectural patterns, structures, and conventions that AI assistants should follow when making changes to the IriusRisk CLI codebase. It serves as the authoritative guide for maintaining consistency and quality.

## Core Architectural Principles

### 1. Dependency Injection (DI) - MANDATORY

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

**Use centralized project resolution utilities** from `utils/project_resolution.py`.

```python
# ✅ CORRECT - Use utilities
from ..utils.project_resolution import resolve_project_id_to_uuid_strict

def handle_project(project_id: str):
    uuid = resolve_project_id_to_uuid_strict(project_id)
    return uuid

# ❌ WRONG - Inline resolution
def handle_project(project_id: str):
    if len(project_id) == 36 and project_id.count('-') == 4:  # NEVER DO THIS
        return project_id
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

### 4. Environment Variable Access
```python
# ❌ NEVER DO THIS
import os
api_url = os.environ.get('IRIUSRISK_API_URL')
```

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
- [ ] Uses Config class for all environment/config access
- [ ] No direct `os.environ` access
- [ ] Uses `is_uuid_format()` instead of magic number UUID detection
- [ ] Uses project resolution utilities from `utils/project_resolution.py`
- [ ] Uses `find_project_root()` from `utils/project_discovery.py` for discovery
- [ ] Does NOT import from `commands/mcp.py` (except in tests)

**Error Handling:**
- [ ] Uses structured error handling from `utils/error_handling.py`
- [ ] No bare `except Exception:` without re-raising or logging
- [ ] No silent exception swallowing (`except: pass`)
- [ ] Specific exceptions (ValidationError, IriusRiskApiError) used appropriately

**Architecture & Organization:**
- [ ] Code is in correct module (command/service/repository/utils)
- [ ] Services contain business logic, not commands
- [ ] Repositories only do data access, no business logic
- [ ] Utils are stateless functions
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
- ❌ `os.environ.get('VAR')` - use Config class
- ❌ `if len(x) == 36 and x.count('-') == 4:` - use `is_uuid_format()`
- ❌ `except Exception: pass` - always log or re-raise
- ❌ Import from `commands/mcp.py` - except in tests

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

**If you're unsure**: Ask for clarification rather than guess. Check this guide first, then review existing properly-architected command files as examples.

---

This document should be updated as architectural patterns evolve. All AI assistants working on this codebase must reference this guide to maintain consistency and quality.
