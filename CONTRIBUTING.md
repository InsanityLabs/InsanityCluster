# Contributing to Insanity Cluster

Thank you for your interest in contributing to Insanity Cluster! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check the [issue tracker](https://github.com/insanity-cluster/insanity-cluster/issues) for existing reports
2. Try the latest version to see if the issue persists
3. Collect relevant information (logs, error messages, steps to reproduce)

**Bug Report Template:**

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.11.5]
- Insanity Cluster version: [e.g. 1.0.0]
- Docker version: [e.g. 24.0.5]

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other context about the problem.
```

### Suggesting Features

Before suggesting a feature:
1. Check if it's already been suggested
2. Consider if it fits the project's goals
3. Think about how it would work

**Feature Request Template:**

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other context or screenshots.
```

### Pull Requests

1. **Fork the repository**
2. **Create a branch** from `develop`:
   ```bash
   git checkout -b feature/my-feature develop
   ```
3. **Make your changes**
4. **Write tests** for your changes
5. **Run tests** to ensure they pass
6. **Commit your changes** with clear messages
7. **Push to your fork**
8. **Create a Pull Request**

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Make (optional)

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/insanity-cluster/insanity-cluster.git
   cd insanity-cluster
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Copy environment template:**
   ```bash
   cp .env.template .env
   ```

6. **Start services:**
   ```bash
   docker-compose up -d postgres redis qdrant
   ```

7. **Initialize database:**
   ```bash
   python scripts/init_database.py
   alembic upgrade head
   ```

8. **Run tests:**
   ```bash
   pytest
   ```

## Code Style

### Python

We follow [PEP 8](https://pep8.org/) with some modifications:

- Line length: 100 characters
- Use type hints
- Use docstrings for all public functions/classes
- Use f-strings for string formatting

**Example:**

```python
from typing import Optional

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str
) -> float:
    """
    Calculate the cost of a model inference.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name
    
    Returns:
        Cost in USD
    
    Raises:
        ValueError: If model is not found
    """
    pricing = get_pricing(model)
    return (
        input_tokens * pricing.input_cost_per_token +
        output_tokens * pricing.output_cost_per_token
    )
```

### Formatting

We use the following tools:

- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

**Run formatters:**

```bash
# Format code
black insanity_cluster tests

# Sort imports
isort insanity_cluster tests

# Check linting
flake8 insanity_cluster tests

# Check types
mypy insanity_cluster
```

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(pan): add support for Gemini models

Implement GeminiAdapter for Google's Gemini models.
Includes streaming support and proper error handling.

Closes #123
```

```
fix(surface): handle WebSocket disconnections gracefully

Add reconnection logic with exponential backoff.
Improve error messages for connection failures.

Fixes #456
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_command_parser.py

# Run with coverage
pytest --cov=insanity_cluster --cov-report=html

# Run specific test
pytest tests/test_command_parser.py::test_parse_simple_command
```

### Writing Tests

**Test Structure:**

```python
import pytest
from insanity_cluster.surface.command_parser import CommandParser

class TestCommandParser:
    """Tests for CommandParser"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return CommandParser()
    
    def test_parse_simple_command(self, parser):
        """Test parsing a simple command"""
        result = parser.parse("Write a Python function")
        
        assert result.intent == "code_generation"
        assert result.confidence > 0.8
        assert "python" in result.parameters
    
    def test_parse_invalid_command(self, parser):
        """Test parsing an invalid command"""
        with pytest.raises(ParseError):
            parser.parse("")
    
    @pytest.mark.asyncio
    async def test_async_parsing(self, parser):
        """Test async parsing"""
        result = await parser.parse_async("Write a function")
        assert result is not None
```

**Test Coverage:**

- Aim for 80%+ code coverage
- Test happy paths and error cases
- Test edge cases and boundary conditions
- Mock external dependencies

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_task_execution():
    """Test complete task execution flow"""
    # Create task
    task_id = await create_task("Write a Python function")
    
    # Wait for completion
    result = await wait_for_completion(task_id, timeout=30)
    
    # Verify result
    assert result.status == "completed"
    assert result.output is not None
    assert result.cost > 0
```

## Documentation

### Code Documentation

Use docstrings for all public functions and classes:

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.
    
    Longer description if needed. Can span multiple lines
    and include examples.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param2 is negative
        TypeError: When param1 is not a string
    
    Example:
        >>> my_function("test", 42)
        True
    """
    pass
```

### User Documentation

- Write clear, concise documentation
- Include examples and use cases
- Add screenshots where helpful
- Keep documentation up to date with code changes

### API Documentation

- Document all REST API endpoints
- Include request/response examples
- Document error codes and messages
- Keep OpenAPI spec up to date

## Project Structure

```
insanity-cluster/
├── insanity_cluster/          # Main package
│   ├── surface/               # SURFACE layer
│   ├── inner/                 # INNER layer
│   ├── crust/                 # CRUST layer
│   ├── pan/                   # PAN layer
│   ├── table/                 # TABLE layer
│   └── common/                # Shared utilities
├── tests/                     # Test files
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py            # Test configuration
├── docs/                      # Documentation
│   ├── api/                   # API documentation
│   ├── guides/                # User guides
│   └── developer/             # Developer docs
├── scripts/                   # Utility scripts
├── k8s/                       # Kubernetes manifests
├── .github/                   # GitHub Actions
├── alembic/                   # Database migrations
├── docker-compose.yml         # Docker Compose config
├── requirements.txt           # Python dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml             # Project configuration
├── pytest.ini                 # Pytest configuration
└── README.md                  # Project README
```

## Review Process

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with `develop`
- [ ] No merge conflicts
- [ ] CI/CD pipeline passes

### Review Guidelines

When reviewing PRs:

- Be constructive and respectful
- Focus on code quality and maintainability
- Check for potential bugs and edge cases
- Verify tests are comprehensive
- Ensure documentation is clear

### Approval Process

1. **Automated checks** must pass (CI/CD)
2. **At least one approval** from a maintainer
3. **No unresolved comments**
4. **Up to date** with target branch

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md**
3. **Create release branch**: `release/v1.2.3`
4. **Run full test suite**
5. **Create tag**: `git tag v1.2.3`
6. **Push tag**: `git push origin v1.2.3`
7. **Create GitHub release**
8. **Deploy to production**

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Discord**: Real-time chat and support
- **Email**: developers@insanitycluster.com

### Getting Help

- Check the [documentation](https://docs.insanitycluster.com)
- Search [existing issues](https://github.com/insanity-cluster/insanity-cluster/issues)
- Ask in [Discord](https://discord.gg/insanity-cluster)
- Email support@insanitycluster.com

## Recognition

Contributors are recognized in:

- CONTRIBUTORS.md file
- Release notes
- Project README
- Annual contributor highlights

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, please:

1. Check this document
2. Search existing issues
3. Ask in Discord
4. Email developers@insanitycluster.com

Thank you for contributing to Insanity Cluster! 🚀
