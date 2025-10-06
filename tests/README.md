# Test Suite Organization

This directory contains the comprehensive test suite for the IriusRisk CLI, organized for clarity and efficiency.

## Directory Structure

```
tests/
├── api/                    # API client tests
│   ├── test_api_client_*.py
│   └── test_api_contract_*.py
├── cli/                    # CLI command tests
│   ├── test_cli_*.py
│   └── (CLI integration tests)
├── integration/            # Full workflow tests
│   ├── test_business_logic*.py
│   ├── test_error_scenarios.py
│   └── test_centralized_error_handling.py
├── unit/                   # Unit tests for services
│   ├── test_*_service.py
│   └── (Individual component tests)
├── utils/                  # Test utilities and helpers
│   ├── fixtures.py         # Consolidated test fixtures
│   ├── helpers.py          # Test helper functions
│   └── assertions.py       # Custom assertion utilities
├── mocks/                  # Mock objects and data
├── fixtures/               # Test data and API responses
└── conftest.py            # Main pytest configuration
```

## Test Categories

### Unit Tests (`unit/`)
- Test individual services, repositories, and utilities
- Fast execution with mocked dependencies
- Focus on business logic and edge cases
- Use `ServiceTestBase` for consistent setup

### CLI Tests (`cli/`)
- Test command-line interface functionality
- Argument parsing and output formatting
- User experience and error messages
- Integration with the CLI context system

### API Tests (`api/`)
- Test API client functionality
- HTTP request/response handling
- Error handling and retries
- Contract validation with real API

### Integration Tests (`integration/`)
- End-to-end workflow testing
- Error handling across components
- Business logic validation
- Complete user scenarios

## Test Utilities

### Consolidated Fixtures (`utils/fixtures.py`)
- Common test data and mock objects
- Service and repository fixtures
- Environment and configuration mocks
- Eliminates duplication across tests

### Helper Functions (`utils/helpers.py`)
- Mock response creation
- Temporary project setup
- OTM file generation
- CLI output capture
- Base classes for consistent testing

### Assertion Utilities (`utils/assertions.py`)
- Custom assertions for API responses
- Data structure validation
- CLI output verification
- Project/threat/countermeasure validation

## Running Tests

### All Tests
```bash
pytest
```

### By Category
```bash
pytest tests/unit/          # Unit tests only
pytest tests/cli/           # CLI tests only
pytest tests/integration/   # Integration tests only
pytest tests/api/           # API tests only
```

### By Marker
```bash
pytest -m unit              # Unit tests
pytest -m integration       # Integration tests
pytest -m slow              # Slower tests
pytest -m network           # Network-dependent tests
```

### Performance Testing
```bash
pytest --durations=10       # Show slowest 10 tests
pytest -x --maxfail=5       # Stop after 5 failures
```

## Test Markers

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests for workflows
- `@pytest.mark.cli` - CLI command tests
- `@pytest.mark.api` - API client tests
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.network` - Tests requiring network (mocked)
- `@pytest.mark.performance` - Performance-sensitive tests

## Best Practices

1. **Use Consolidated Fixtures**: Import from `tests.utils.fixtures` instead of creating duplicates
2. **Inherit from Base Classes**: Use `ServiceTestBase` for service tests
3. **Organize by Concern**: Place tests in appropriate directories
4. **Use Descriptive Names**: Test methods should clearly describe what they test
5. **Mock External Dependencies**: Keep tests fast and reliable
6. **Validate Complete Structures**: Use assertion utilities for thorough validation

## Performance Optimizations

- Consolidated fixtures reduce setup overhead
- Organized directory structure improves test discovery
- Optimized pytest configuration for faster execution
- Parallel execution support (with pytest-xdist)
- Warning filters to reduce noise
- Efficient mocking strategies

## Maintenance

- Keep fixtures in sync with application changes
- Update assertion utilities when data structures change
- Review and consolidate duplicate test patterns
- Monitor test execution times and optimize slow tests
- Ensure comprehensive coverage of critical paths
