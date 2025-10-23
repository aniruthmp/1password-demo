# Universal 1Password Agent Credential Broker - Backend

## Overview

This is the backend implementation of the Universal 1Password Agent Credential Broker, supporting three agent communication protocols:

- **MCP** (Model Context Protocol) - For AI models to request credentials as tools
- **A2A** (Agent-to-Agent Protocol) - For agent-to-agent collaboration
- **ACP** (Agent Communication Protocol) - For framework-agnostic REST API access

## Implementation Status

### Phase 1: Core Foundation ✅ Complete
### Phase 2: MCP Server ✅ Complete

---

## Phase 1: Core Foundation ✅

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

---

## Phase 2: MCP Server ✅

### Implemented Components

#### 2. MCP Protocol Implementation (`src/mcp/`)

- **`mcp_server.py`** - Model Context Protocol server
  - Lifespan management for resource initialization
  - `get_credentials` tool for AI models
  - `list_tools` endpoint for tool discovery
  - stdio transport for client communication
  - Comprehensive error handling
  - Integration with Phase 1 components

- **`run_mcp.py`** - MCP server entry point
  - CLI argument parsing (log level configuration)
  - Graceful shutdown handling
  - Professional logging and status output

#### MCP Server Features

✅ **Tool: get_credentials**
- Input parameters: resource_type, resource_name, requesting_agent_id, ttl_minutes
- Output: Ephemeral JWT token with metadata
- Validation: JSON schema with enum types
- Error handling: Graceful error messages

✅ **Protocol Support**
- stdio transport (default for MCP clients)
- Async/await throughout
- Request context management
- Health checks on startup

✅ **Integration**
- Uses CredentialManager for credential retrieval
- Uses AuditLogger for event logging
- Supports all Phase 1 resource types (database, api, ssh, generic)

## Project Structure

```
backend/
├── src/
│   ├── core/           # Phase 1: Core credential management ✅
│   ├── mcp/            # Phase 2: MCP server ✅
│   │   ├── mcp_server.py     # MCP protocol implementation
│   │   └── run_mcp.py        # Server entry point
│   ├── a2a/            # Phase 3: A2A server (TODO)
│   ├── acp/            # Phase 4: ACP server (TODO)
│   └── ui/             # Phase 6: Demo UI (Optional)
├── tests/              # Unit and integration tests
│   ├── test_mcp_server.py    # MCP server tests ✅
│   └── ...                   # Phase 1 tests ✅
├── demos/              # Demo scenarios
│   └── mcp_demo.py           # MCP client demo ✅
├── scripts/            # Interactive testing scripts
│   ├── test_phase1.py        # Phase 1 interactive test ✅
│   ├── test_phase2.py        # Phase 2 interactive test ✅
│   └── README.md             # Testing guide
├── config/             # Configuration files
├── pyproject.toml      # Poetry dependencies and configuration
└── poetry.lock         # Locked dependency versions
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

4. Activate Poetry environment:
```bash
poetry env activate
```

Alternatively, use the Makefile:
```bash
make install        # Install production dependencies
make install-dev    # Install with dev dependencies
```

## Testing & Validation

### Prerequisites Setup

1. **Start 1Password Connect Services:**
   ```bash
   cd backend
   docker-compose up -d
   ```

2. **Verify Connect API is running:**
   ```bash
   curl http://localhost:8080/health
   # Should return: {"status":"healthy"}
   ```

3. **Configure Environment:**
   ```bash
   # Copy and edit environment file
   cp .env.example .env
   # Edit .env with your actual values:
   # OP_CONNECT_HOST=http://localhost:8080
   # OP_CONNECT_TOKEN=your_connect_token
   # OP_VAULT_ID=your_vault_id
   # JWT_SECRET_KEY=your_32_char_secret_key
   ```

### Phase 1 Validation Tests

#### Test 1: Health Check
```bash
# Activate Poetry environment
poetry env activate

# Run health check
python3 -c "
from src.core.credential_manager import CredentialManager
manager = CredentialManager()
health = manager.health_check()
print('Health Status:', health['status'])
print('1Password:', health['components']['onepassword']['status'])
print('Token Manager:', health['components']['token_manager']['status'])
"
```

**Expected Output:**
```
Health Status: healthy
1Password: healthy
Token Manager: healthy
```

#### Test 2: Credential Retrieval
```bash
# Test credential fetching (replace 'your-item-name' with actual 1Password item)
python3 -c "
from src.core.credential_manager import CredentialManager
manager = CredentialManager()

# Fetch credentials for a database item
try:
    creds = manager.fetch_credentials('database', 'your-item-name')
    print('✅ Credentials fetched successfully')
    print('Fields found:', list(creds.keys()))
except Exception as e:
    print('❌ Failed to fetch credentials:', str(e))
"
```

#### Test 3: Token Generation & Validation
```bash
# Test full token lifecycle
python3 -c "
from src.core.credential_manager import CredentialManager
import json

manager = CredentialManager()

# Generate token
token_data = manager.fetch_and_issue_token(
    resource_type='database',
    resource_name='your-item-name',
    agent_id='test-agent-001',
    ttl_minutes=2
)

print('✅ Token generated successfully')
print('Token:', token_data['token'][:50] + '...')
print('Expires in:', token_data['expires_in'], 'seconds')
print('Resource:', token_data['resource'])

# Validate token
validation = manager.validate_token(token_data['token'])
print('✅ Token validation:', validation['valid'])
print('Agent ID:', validation['agent_id'])
print('Time remaining:', validation['time_remaining'], 'seconds')

# Decrypt credentials
creds = manager.get_credentials_from_token(token_data['token'])
print('✅ Credentials decrypted successfully')
print('Available fields:', list(creds['credentials'].keys()))
"
```

#### Test 4: Token Expiration
```bash
# Test token expiration (wait 2+ minutes after previous test)
python3 -c "
from src.core.credential_manager import CredentialManager
import time

manager = CredentialManager()

# Generate short-lived token
token_data = manager.fetch_and_issue_token(
    resource_type='database',
    resource_name='your-item-name',
    agent_id='test-agent-002',
    ttl_minutes=1  # 1 minute TTL
)

print('Token expires in:', token_data['expires_in'], 'seconds')
print('Waiting 70 seconds for expiration...')
time.sleep(70)

# Try to validate expired token
try:
    validation = manager.validate_token(token_data['token'])
    print('❌ Token should have expired!')
except Exception as e:
    print('✅ Token correctly expired:', str(e))
"
```

#### Test 5: Error Handling
```bash
# Test error scenarios
python3 -c "
from src.core.credential_manager import CredentialManager

manager = CredentialManager()

# Test invalid resource type
try:
    manager.fetch_credentials('invalid_type', 'test-item')
    print('❌ Should have failed for invalid resource type')
except ValueError as e:
    print('✅ Correctly rejected invalid resource type:', str(e))

# Test non-existent item
try:
    manager.fetch_credentials('database', 'non-existent-item')
    print('❌ Should have failed for non-existent item')
except ValueError as e:
    print('✅ Correctly rejected non-existent item:', str(e))

# Test invalid token
try:
    manager.validate_token('invalid.token.here')
    print('❌ Should have failed for invalid token')
except Exception as e:
    print('✅ Correctly rejected invalid token:', str(e))
"
```

### Interactive Testing Scripts

For easier testing, use the provided interactive scripts:

```bash
# Phase 1: Core components
poetry env activate
poetry run python scripts/test_phase1.py

# Phase 2: MCP server
poetry run python scripts/test_phase2.py
```

See `scripts/README.md` for detailed usage instructions.

---

## Running the MCP Server

### Quick Start (Recommended)

Use the provided startup script that handles all setup automatically:

```bash
cd backend
./scripts/mcp_server.sh
```

The script will:
- ✅ Verify and load .env configuration
- ✅ Check required environment variables
- ✅ Ensure Poetry and dependencies are installed
- ✅ Start the MCP server with proper settings

### With Custom Log Level

```bash
# Info level (default)
./scripts/mcp_server.sh --log-level INFO

# Debug level for troubleshooting
./scripts/mcp_server.sh --log-level DEBUG

# Error level for production
./scripts/mcp_server.sh --log-level ERROR

# Show help
./scripts/mcp_server.sh --help
```

### Manual Start (Alternative)

You can also start the server manually:

```bash
cd backend
poetry env activate
python src/mcp/run_mcp.py --log-level INFO
```

### Expected Output

```
============================================================
1Password Credential Broker - MCP Server
============================================================
Version: 1.0.0
Transport: stdio
Log Level: INFO
============================================================
INFO - MCP Server starting up - initializing resources...
INFO - 1Password Connect: Connected
INFO - MCP Server resources initialized successfully
INFO - Starting MCP Server on stdio transport...
```

The server is now ready to accept MCP client connections via stdio.

### Using with MCP Clients

The MCP server communicates via stdio, making it compatible with any MCP client:

**Example: Python MCP Client**
```python
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["src/mcp/run_mcp.py", "--log-level", "ERROR"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # List available tools
        tools = await session.list_tools()
        
        # Call get_credentials tool
        result = await session.call_tool(
            "get_credentials",
            arguments={
                "resource_type": "database",
                "resource_name": "prod-postgres",
                "requesting_agent_id": "my-agent",
                "ttl_minutes": 5
            }
        )
```

**Example: Using the Demo Client**
```bash
poetry env activate
python demos/mcp_demo.py
```

### Interactive Testing Script

For comprehensive interactive testing, use:

```bash
# Create test script
cat > test_phase1.py << 'EOF'
#!/usr/bin/env python3
"""
Interactive Phase 1 Testing Script
"""
import os
import sys
from src.core.credential_manager import CredentialManager

def main():
    print("🔐 Phase 1 Validation Test")
    print("=" * 40)
    
    # Test 1: Health Check
    print("\n1. Health Check...")
    try:
        manager = CredentialManager()
        health = manager.health_check()
        print(f"   Status: {health['status']}")
        print(f"   1Password: {health['components']['onepassword']['status']}")
        print(f"   Token Manager: {health['components']['token_manager']['status']}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test 2: Get user input
    print("\n2. Credential Testing...")
    resource_type = input("   Enter resource type (database/api/ssh/generic): ").strip()
    resource_name = input("   Enter 1Password item name: ").strip()
    agent_id = input("   Enter agent ID: ").strip() or "test-agent"
    
    if not resource_type or not resource_name:
        print("   ❌ Resource type and name are required")
        return
    
    # Test 3: Fetch credentials
    print(f"\n3. Fetching credentials for {resource_type}/{resource_name}...")
    try:
        creds = manager.fetch_credentials(resource_type, resource_name)
        print(f"   ✅ Success! Found {len(creds)} credential fields")
        print(f"   Fields: {list(creds.keys())}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Test 4: Generate token
    print(f"\n4. Generating token for agent {agent_id}...")
    try:
        token_data = manager.fetch_and_issue_token(
            resource_type=resource_type,
            resource_name=resource_name,
            agent_id=agent_id,
            ttl_minutes=5
        )
        print(f"   ✅ Token generated successfully")
        print(f"   Expires in: {token_data['expires_in']} seconds")
        print(f"   Resource: {token_data['resource']}")
    except Exception as e:
        print(f"   ❌ Token generation failed: {e}")
        return
    
    # Test 5: Validate token
    print(f"\n5. Validating token...")
    try:
        validation = manager.validate_token(token_data['token'])
        print(f"   ✅ Token is valid")
        print(f"   Agent: {validation['agent_id']}")
        print(f"   Time remaining: {validation['time_remaining']} seconds")
    except Exception as e:
        print(f"   ❌ Token validation failed: {e}")
        return
    
    # Test 6: Decrypt credentials
    print(f"\n6. Decrypting credentials...")
    try:
        decrypted = manager.get_credentials_from_token(token_data['token'])
        print(f"   ✅ Credentials decrypted successfully")
        print(f"   Available fields: {list(decrypted['credentials'].keys())}")
        
        # Show sample credentials (masked)
        for key, value in decrypted['credentials'].items():
            if isinstance(value, str) and len(value) > 4:
                masked_value = value[:2] + "*" * (len(value) - 4) + value[-2:]
                print(f"   {key}: {masked_value}")
            else:
                print(f"   {key}: {value}")
                
    except Exception as e:
        print(f"   ❌ Credential decryption failed: {e}")
        return
    
    print(f"\n🎉 Phase 1 validation completed successfully!")
    print(f"   All core components are working correctly.")

if __name__ == "__main__":
    main()
EOF

# Make executable and run
chmod +x scripts/test_phase1.py

# Option 1: Run directly with Poetry
poetry run python scripts/test_phase1.py

# Option 2: Activate Poetry environment first
poetry env activate
poetry run python scripts/test_phase1.py
```

### Phase 2: MCP Server Validation

Run the interactive Phase 2 test script:

```bash
poetry env activate
poetry run python scripts/test_phase2.py
```

This will test:
- ✅ MCP server startup and connectivity
- ✅ Tool discovery (`list_tools`)
- ✅ Credential retrieval via `get_credentials` tool
- ✅ Error handling with invalid resources
- ✅ Integration with Phase 1 components

### Validation Checklist

**Phase 1 (Core Components):**
- [✅] **1Password Connect API** is running and accessible
- [✅] **Environment variables** are properly configured
- [✅] **Health check** returns "healthy" status
- [✅] **Credential retrieval** works for existing 1Password items
- [✅] **Token generation** creates valid JWT tokens
- [✅] **Token validation** correctly validates tokens
- [✅] **Credential decryption** successfully decrypts embedded credentials
- [✅] **Token expiration** works correctly after TTL
- [✅] **Error handling** properly rejects invalid inputs
- [✅] **Audit logging** captures all operations (check logs/)

**Phase 2 (MCP Server):**
- [✅] **MCP server starts** via stdio transport
- [✅] **Tool discovery** returns get_credentials tool
- [✅] **Credential requests** work through MCP protocol
- [✅] **Error handling** returns clear error messages
- [✅] **Integration** with Phase 1 components verified

### Troubleshooting

**Common Issues:**

1. **Connect API not accessible:**
   ```bash
   # Check if services are running
   docker-compose ps
   
   # Check logs
   docker-compose logs connect-api
   ```

2. **Authentication errors:**
   - Verify `OP_CONNECT_TOKEN` is correct
   - Check `OP_VAULT_ID` exists and is accessible
   - Ensure `OP_CONNECT_HOST` points to running service

3. **Item not found:**
   - Verify item exists in specified vault
   - Check item title matches exactly (case-sensitive)
   - Ensure vault ID is correct

4. **Token validation fails:**
   - Check `JWT_SECRET_KEY` is consistent
   - Verify token hasn't expired
   - Ensure token wasn't modified

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
- ✅ stdio transport for MCP (secure process communication)

## Test Coverage

Current test coverage: **76%**

| Module | Tests | Coverage |
|--------|-------|----------|
| audit_logger.py | 31 | 98% ✅ |
| credential_manager.py | 25 | 96% ✅ |
| token_manager.py | 34 | 94% ✅ |
| onepassword_client.py | 16 | 87% ✅ |
| mcp_server.py | 6 | 65% ✅ |
| **Total** | **112** | **76%** |

Run tests:
```bash
make test          # Run all tests
make test-cov      # With coverage report
```

## Next Steps

- ✅ **Phase 1**: Core foundation (COMPLETE)
- ✅ **Phase 2**: MCP server (COMPLETE)
- ⏭️ **Phase 3**: A2A server implementation
- ⏭️ **Phase 4**: ACP server implementation
- ⏭️ **Phase 5**: Docker integration and orchestration
- ⏭️ **Phase 6**: Demo UI (optional)
- ⏭️ **Phase 7**: Documentation and testing
- ⏭️ **Phase 8**: Final validation

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
make shell        # Activate Poetry environment
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

