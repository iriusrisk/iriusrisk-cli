# Developer Guide

Guide for contributing to the IriusRisk CLI.

## Quick Setup

```bash
# Clone and setup
git clone <repository-url>
cd iriusrisk_cli
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Run tests
pytest
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/          # Unit tests
pytest tests/cli/           # CLI tests
pytest tests/integration/   # Integration tests

# Run with coverage
pytest --cov=src/iriusrisk_cli

# Run specific test
pytest tests/unit/test_project_service.py::TestProjectService::test_list_projects
```

## Making Changes

### Development Workflow
1. Create a feature branch from `main`
2. Make your changes
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Standards
- Follow existing patterns in the codebase
- Write tests for new functionality
- Use type hints where appropriate
- Keep functions focused and small

### Adding New Commands
1. Add command function in appropriate `commands/` file
2. Register command in `main.py`
3. Add tests in `tests/cli/`
4. Update help text and examples

Example:
```python
# commands/projects.py
@click.command()
@click.argument('project_id')
def show(project_id):
    """Show project details."""
    # Implementation here
```

### Configuration

The CLI supports multiple configuration methods. For development:

```bash
# Option 1: User config (recommended for development)
iriusrisk config set-hostname https://your-instance.iriusrisk.com
iriusrisk config set-api-key  # prompts securely for API key

# Option 2: Project .env file
cat > .env << EOF
IRIUS_HOSTNAME=https://your-instance.iriusrisk.com
IRIUS_API_KEY=your-api-token-here
IRIUS_LOG_RESPONSES=true  # Optional: for debugging
EOF

# Option 3: Environment variables
export IRIUS_HOSTNAME=https://your-instance.iriusrisk.com
export IRIUS_API_KEY=your-api-token-here
```

Note: Both `IRIUS_API_KEY` and `IRIUS_API_TOKEN` are supported for backward compatibility.

## Debugging

### Enable API Logging
```bash
export IRIUS_LOG_RESPONSES=true
iriusrisk project list
# Check captured_responses/ directory
```

### Common Issues
- **Import errors**: Run `pip install -e .`
- **Test failures**: Check configuration using `iriusrisk config show`
- **API errors**: Verify credentials and network access
- **Config not found**: Ensure either user config (~/.iriusrisk/config.json), .env file, or environment variables are set

## Pull Request Guidelines

### Before Submitting
- [ ] All tests pass
- [ ] New functionality has tests
- [ ] Code follows existing patterns
- [ ] Clear commit messages

### PR Description
Include:
- What the change does
- Why it's needed
- How to test it
- Any breaking changes

### Review Process
1. Automated tests run
2. Code review by maintainers
3. Address feedback
4. Merge when approved

## Release Process

Maintainers handle releases:
1. Update version in `setup.py`
2. Create git tag
3. Publish to PyPI

## Getting Help

- **Issues**: Use GitHub issues for bugs and features
- **Questions**: Start a GitHub discussion
- **Code Review**: Submit a draft PR for early feedback