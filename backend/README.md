# Universal 1Password Agent Credential Broker - Backend

## Overview

This is the backend implementation of the Universal 1Password Agent Credential Broker, supporting three agent communication protocols:

- **MCP** (Model Context Protocol) - For AI models to request credentials as tools
- **A2A** (Agent-to-Agent Protocol) - For agent-to-agent collaboration
- **ACP** (Agent Communication Protocol) - For framework-agnostic REST API access

## Phase 1 Complete ✅

### Implemented Components

#### 1. Core Infrastructure (`src/core/`)

- **`onepassword_client.py`** - 1Password Connect API integration
  - Async vault and item retrieval
  - Health checks
  - Credential field extraction

- **`token_manager.py`** - JWT token management with AES-256 encryption
  - Ephemeral token generation (default 5 min TTL)
  - AES-256 credential encryption
  - Token validation and decryption

- **`credential_manager.py`** - Unified credential orchestration
  - Coordinates 1Password retrieval and token generation
  - Resource type validation (database, api, ssh, generic)
  - Health checks

- **`audit_logger.py`** - Event logging and audit trail
  - 1Password Events API integration
  - Async event posting with retry logic
  - Local file fallback logging
  - Structured JSON logging

- **`logging_config.py`** - Centralized logging configuration
  - Structured JSON logging
  - Per-protocol tagging
  - Configurable log levels and formats

## Project Structure

```
backend/
├── src/
│   ├── core/           # Phase 1: Core credential management ✅
│   ├── mcp/            # Phase 2: MCP server (TODO)
│   ├── a2a/            # Phase 3: A2A server (TODO)
│   ├── acp/            # Phase 4: ACP server (TODO)
│   └── ui/             # Phase 6: Demo UI (Optional)
├── tests/              # Unit and integration tests
├── demos/              # Demo scenarios
├── scripts/            # Utility scripts
├── config/             # Configuration files
├── requirements.txt    # Production dependencies
└── requirements-dev.txt # Development dependencies
```

## Environment Configuration

Copy `.env.example` and configure your credentials:

```bash
cp .env.example .env
```

**Prerequisites:**
- Python 3.12+

**Required environment variables:**
- `OP_CONNECT_HOST` - 1Password Connect server URL
- `OP_CONNECT_TOKEN` - Connect API token
- `OP_VAULT_ID` - Default vault ID
- `JWT_SECRET_KEY` - Secret for JWT signing (32+ chars recommended)

**Optional:**
- `EVENTS_API_URL` - 1Password Events API URL
- `EVENTS_API_TOKEN` - Events API token
- `TOKEN_TTL_MINUTES` - Token TTL (default: 5)
- `LOG_LEVEL` - Logging level (default: INFO)

## Installation

This project uses **Poetry** for dependency management.

1. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:
```bash
cd backend
poetry install
```

3. For development (includes testing and linting tools):
```bash
poetry install --with dev
```

4. Activate Poetry shell:
```bash
poetry shell
```

Alternatively, use the Makefile:
```bash
make install        # Install production dependencies
make install-dev    # Install with dev dependencies
```

## Usage Example

```python
from src.core.credential_manager import CredentialManager

# Initialize manager
manager = CredentialManager()

# Fetch credentials and issue token
token_data = manager.fetch_and_issue_token(
    resource_type="database",
    resource_name="prod-postgres",
    agent_id="my-agent-001",
    ttl_minutes=5
)

print(f"Token: {token_data['token']}")
print(f"Expires in: {token_data['expires_in']} seconds")

# Validate token
validation = manager.validate_token(token_data['token'])
print(f"Valid: {validation['valid']}")
print(f"Time remaining: {validation['time_remaining']} seconds")

# Get credentials from token
creds = manager.get_credentials_from_token(token_data['token'])
print(f"Username: {creds['credentials']['username']}")
```

## Security Features

- ✅ AES-256 encryption for credentials
- ✅ JWT tokens with <5 minute TTL by default
- ✅ Secure token validation
- ✅ Comprehensive audit logging
- ✅ No plaintext credential storage

## Next Steps

- **Phase 2**: Implement MCP server
- **Phase 3**: Implement A2A server
- **Phase 4**: Implement ACP server
- **Phase 5**: Docker integration and orchestration
- **Phase 6**: Demo UI (optional)
- **Phase 7**: Documentation and testing
- **Phase 8**: Final validation

## Development

### Makefile Quick Reference
```bash
make help         # Show all available commands
make install      # Install dependencies
make install-dev  # Install with dev dependencies
make test         # Run tests
make test-cov     # Run tests with coverage
make format       # Format code with black
make lint         # Run ruff linter
make lint-fix     # Fix linting issues
make typecheck    # Run mypy type checking
make qa           # Run all quality checks
make clean        # Remove temporary files
make shell        # Activate Poetry shell
```

### Running Tests

```bash
# Run all tests
make test

# Run tests with verbose output
make test-v

# Run tests with coverage report
make test-cov

# Using Poetry directly
poetry run pytest
poetry run pytest --cov=src --cov-report=term-missing
```

### Code Quality

```bash
# Format code with black
make format

# Run linters
make lint

# Fix linting issues automatically
make lint-fix

# Type checking
make typecheck

# Run all quality checks
make qa
```

### Using Poetry

```bash
# Add a new dependency
poetry add package-name

# Add a dev dependency
poetry add --group dev package-name

# Update dependencies
make update

# Shell with activated environment
make shell
```

## Documentation

- See `PRD-ver-1.0.md` for product requirements
- See `TODO.md` for detailed task breakdown
- See `PROJECT_ROADMAP.md` for implementation roadmap

## License

[Your License Here]

