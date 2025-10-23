# Testing Scripts

This directory contains interactive testing scripts to validate each phase of the 1Password Credential Broker implementation.

---

## 📋 Available Scripts

### MCP Server Launcher
**Script:** `mcp_server.sh`  
**Purpose:** Start the MCP server with proper environment setup

```bash
cd backend
./scripts/mcp_server.sh

# With custom log level
./scripts/mcp_server.sh --log-level DEBUG

# Show help
./scripts/mcp_server.sh --help
```

**What it does:**
- ✅ Verifies .env file exists and loads environment variables
- ✅ Checks for required environment variables
- ✅ Verifies Poetry installation
- ✅ Ensures dependencies are installed
- ✅ Starts MCP server with proper configuration
- ✅ Handles graceful shutdown on Ctrl+C

**Prerequisites:**
- Poetry installed
- .env file configured with 1Password credentials
- Dependencies installed (`poetry install`)

---

### A2A Server Launcher
**Script:** `a2a_server.sh`  
**Purpose:** Start the A2A (Agent-to-Agent) server with proper environment setup

```bash
cd backend
./scripts/a2a_server.sh

# Custom port
./scripts/a2a_server.sh --port 8001

# Development mode with auto-reload
./scripts/a2a_server.sh --reload --log-level DEBUG

# Production mode with multiple workers
./scripts/a2a_server.sh --workers 4

# Show help
./scripts/a2a_server.sh --help
```

**What it does:**
- ✅ Verifies .env file exists and loads environment variables
- ✅ Checks for required environment variables
- ✅ Verifies Poetry installation
- ✅ Ensures dependencies are installed
- ✅ Checks if port is available before starting
- ✅ Starts A2A server with proper configuration
- ✅ Displays API endpoints and documentation URL
- ✅ Handles graceful shutdown on Ctrl+C

**Available Options:**
- `--port PORT` - Set server port (default: 8000)
- `--host HOST` - Set server host (default: 0.0.0.0)
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--reload` - Enable auto-reload for development
- `--workers N` - Number of worker processes (default: 1)

**Prerequisites:**
- Poetry installed
- .env file configured with 1Password credentials
- Dependencies installed (`poetry install`)
- Port 8000 available (or use `--port` to specify different port)

---

### Phase 1: Core Foundation Testing
**Script:** `test_phase1.py`  
**Tests:** Core credential management, token generation, encryption

```bash
cd backend
poetry env activate
python scripts/test_phase1.py
```

**What it tests:**
- ✅ Health checks for CredentialManager
- ✅ 1Password Connect API connectivity
- ✅ Credential retrieval from vault
- ✅ JWT token generation with encryption
- ✅ Token validation and expiration
- ✅ Credential decryption from tokens

**Prerequisites:**
- 1Password Connect server running
- Valid credentials in `.env` file
- At least one item in your 1Password vault

---

### Phase 2: MCP Server Testing
**Script:** `test_phase2.py`  
**Tests:** Model Context Protocol server implementation

```bash
cd backend
poetry env activate
python scripts/test_phase2.py
```

**What it tests:**
- ✅ MCP server startup and connectivity
- ✅ Tool discovery (`list_tools`)
- ✅ Credential retrieval via `get_credentials` tool
- ✅ Ephemeral token generation through MCP
- ✅ Error handling and validation
- ✅ Audit logging integration

**Prerequisites:**
- Phase 1 components working (run `test_phase1.py` first)
- 1Password Connect server running
- Valid credentials in `.env` file

---

## 🚀 Quick Start Guide

### First Time Setup

1. **Configure Environment**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your 1Password credentials
   ```

2. **Install Dependencies**
   ```bash
   poetry install
   ```

3. **Activate Poetry Environment**
   ```bash
   poetry env activate
   ```

### Testing Workflow

**Step 1: Test Phase 1 (Core Components)**
```bash
cd backend
poetry run python scripts/test_phase1.py
```

Follow the interactive prompts to:
- Verify health checks
- Enter a resource type (database/api/ssh/generic)
- Enter an existing 1Password item name
- Watch the credential retrieval and token generation process

**Example interaction:**
```
🔐 Phase 1 Validation Test
============================================

1. Health Check...
   Status: healthy
   1Password: healthy
   Token Manager: healthy

2. Credential Testing...
   Enter resource type (database/api/ssh/generic): database
   Enter 1Password item name: test-database
   Enter agent ID: test-agent

3. Fetching credentials for database/test-database...
   ✅ Success! Found 4 credential fields
   Fields: ['username', 'password', 'host', 'port']

... (continues with token generation and validation)
```

**Step 2: Test Phase 2 (MCP Server)**
```bash
cd backend
poetry run python scripts/test_phase2.py
```

Follow the interactive prompts to:
- Discover available MCP tools
- Select a resource type
- Request credentials via MCP protocol
- Optionally test error handling

**Step 3: Test Phase 3 (A2A Server)**

First, start the A2A server in a separate terminal:
```bash
cd backend

# Option 1: Use the launcher script (recommended)
./scripts/a2a_server.sh

# Option 2: Direct Python command
poetry run python src/a2a/run_a2a.py
```

Then run the test in another terminal:
```bash
cd backend
poetry run python scripts/test_phase3.py
```

Follow the interactive prompts to:
- Verify server connectivity
- Discover agent card
- Select a resource type
- Request credentials via A2A protocol
- Optionally test authentication and error handling

**Example interaction (Phase 2):**
```
============================================================
  Phase 2 Validation Test - MCP Server
============================================================

1. Connecting to MCP Server...
   ✅ Connected to MCP server successfully

2. Discovering Available Tools...
   ✅ Found 1 tool(s)
     Tool: get_credentials
     Description: Retrieve ephemeral credentials from 1Password vault...
     Required parameters: resource_type, resource_name, requesting_agent_id

3. Credential Request Test...
   Let's test retrieving credentials from 1Password

   Available resource types:
     1. database
     2. api
     3. ssh
     4. generic

   Select resource type [1-4] or enter custom: 1
   Enter 1Password item name: test-database
   Enter agent ID (default: phase2-tester): my-agent
   Enter TTL in minutes (default: 5, max: 15): 5

4. Requesting Credentials for database/test-database...
   ✅ Credential request completed!

   Response from MCP server:
   --------------------------------------------------------
   ✅ Ephemeral credentials generated successfully

   Resource: database/test-database
   Token: eyJhbGciOiJIUzI1N...
   Expires in: 300 seconds (5 minutes)
   ...
   --------------------------------------------------------

... (continues with optional error handling test)
```

---

### Phase 3: A2A Server Testing
**Script:** `test_phase3.py`  
**Tests:** Agent-to-Agent protocol server implementation

```bash
# Step 1: Start the A2A server (in a separate terminal)
cd backend

# Option 1: Use the launcher script (recommended)
./scripts/a2a_server.sh

# Option 2: Direct Python command
poetry run python src/a2a/run_a2a.py

# Step 2: Run the test script (in another terminal)
cd backend
poetry run python scripts/test_phase3.py
```

**What it tests:**
- ✅ A2A server connectivity and health
- ✅ Agent card discovery endpoint
- ✅ Task execution with capability routing
- ✅ Bearer token authentication
- ✅ All 4 capability handlers (database, api, ssh, generic)
- ✅ Error handling and validation
- ✅ Credential provisioning via A2A protocol

**Prerequisites:**
- Phase 1 and Phase 2 components working
- A2A server running on http://localhost:8000
- Valid credentials in `.env` file
- At least one item in your 1Password vault

**Example interaction:**
```
============================================================
  Phase 3 Validation Test - A2A Server
============================================================

1. Server Connectivity Check...
   ✅ A2A server is running
     Status: healthy
     Service: a2a-server
     Version: 1.0.0

2. Agent Card Discovery...
   ✅ Agent card retrieved successfully
     Agent Information:
       ID: 1password-credential-broker
       Name: 1Password Ephemeral Credential Agent
       Version: 1.0.0
       Authentication: bearer_token

     Capabilities (4 total):
       1. request_database_credentials
          Description: Request temporary database credentials...
       2. request_api_credentials
       3. request_ssh_credentials
       4. request_generic_secret

3. Task Execution - Database Credentials...
   Select resource type [1-4]: 1
   Enter 1Password item name: test-database
   Enter TTL in minutes (default: 5, max: 15): 5

   ✅ Task executed successfully
     Status: completed
     Execution Time: 245.32ms
     
     Credential Details:
       Token: eyJhbGciOiJIUzI1N... (truncated)
       Expires In: 300 seconds
       Issued At: 2025-10-23T12:34:56Z

... (continues with optional tests)
```

---

### Phase 4: ACP Server Testing
**Script:** `test_phase4.py`  
**Tests:** Agent Communication Protocol server implementation

```bash
# Step 1: Start the ACP server (in a separate terminal)
cd backend

# Option 1: Use the launcher script (recommended)
./scripts/acp_server.sh

# Option 2: Direct Python command
poetry run python src/acp/run_acp.py

# Step 2: Run the test script (in another terminal)
cd backend
poetry run python scripts/test_phase4.py
```

**What it tests:**
- ✅ ACP server connectivity and health
- ✅ Agent discovery via /agents endpoint
- ✅ Natural language credential requests
- ✅ Intent parsing (database, API, SSH extraction)
- ✅ Session management and tracking
- ✅ Interaction history retrieval
- ✅ Multiple credential types in same session
- ✅ Error handling and validation
- ✅ Credential provisioning via ACP protocol

**Prerequisites:**
- Phase 1, 2, and 3 components working
- ACP server running on http://localhost:8001
- Valid credentials in `.env` file
- At least one item in your 1Password vault

**Example interaction:**
```
============================================================
  Phase 4 Validation Test - ACP Server
============================================================

1. Server Connectivity Check
----------------------------------------------------------------------
   ✅ ACP server is running
     Status: healthy
     Service: acp-server
     Version: 1.0.0

2. Agent Discovery
----------------------------------------------------------------------
   ✅ Agent discovery successful
     Found 1 agent(s)

     Agent Information:
       Name: credential-broker
       Description: Ephemeral credential provisioning from...
       Version: 1.0.0

     Capabilities (6 total):
       • database_credentials
       • api_credentials
       • ssh_credentials
       • generic_secrets
       • natural_language_parsing
       • session_management

3. Natural Language Credential Requests
----------------------------------------------------------------------
   Testing multiple credential types with session management...

   Test 3.1: Database Credentials
     Request: 'I need database credentials for production-postgres'

   ✅ Request completed successfully
     Status: completed
     Run ID: run-123e4567...
     Session ID: session-123e4567...
     Execution Time: 234.56ms

     Output:
       Text Response:
         ✅ Generated ephemeral database credentials for production-postgres.
         Token expires in 5 minutes (300 seconds).
       JWT Token:
         eyJhbGciOiJIUzI1N... (truncated)

... (continues with API and SSH credential tests)

4. Session History
----------------------------------------------------------------------
   ✅ Session history retrieved
     Session ID: session-123e4567...
     Interaction Count: 3

     Interaction History:
       1. 2025-10-23T12:34:56Z
          Run ID: run-abc...
          Status: completed
          Input: I need database credentials for...
          Output: Generated ephemeral database credentials...

... (continues with error handling tests)
```

---

### ACP Server Launcher
**Script:** `acp_server.sh`  
**Purpose:** Start the ACP (Agent Communication Protocol) server with proper environment setup

```bash
cd backend

# Basic usage (default settings)
./scripts/acp_server.sh

# Custom port
./scripts/acp_server.sh --port 8002

# Development mode with auto-reload
./scripts/acp_server.sh --reload --log-level DEBUG

# Production mode with multiple workers
./scripts/acp_server.sh --workers 4

# Show help
./scripts/acp_server.sh --help
```

**What it does:**
- ✅ Verifies .env file exists and loads environment variables
- ✅ Checks for required environment variables
- ✅ Verifies Poetry installation
- ✅ Ensures dependencies are installed
- ✅ Checks if port is available before starting
- ✅ Starts ACP server with proper configuration
- ✅ Displays API endpoints and documentation URL
- ✅ Handles graceful shutdown on Ctrl+C

**Available Options:**
- `--port PORT` - Set server port (default: 8001)
- `--host HOST` - Set server host (default: 0.0.0.0)
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--reload` - Enable auto-reload for development
- `--workers N` - Number of worker processes (default: 1)

**Prerequisites:**
- Poetry installed
- .env file configured with 1Password credentials
- Dependencies installed (`poetry install`)
- Port 8001 available (or use `--port` to specify different port)

---

## 🔧 Troubleshooting

### Common Issues

#### "Import Error: Missing dependencies"
**Solution:**
```bash
cd backend
poetry install
poetry env activate
```

#### "1Password Connect health check failed"
**Causes:**
- 1Password Connect server not running
- Invalid `OP_CONNECT_HOST` or `OP_CONNECT_TOKEN` in `.env`
- Network connectivity issues

**Solution:**
1. Verify 1Password Connect is running
2. Check `.env` configuration
3. Test connectivity: `curl $OP_CONNECT_HOST/health`

#### "Resource not found in 1Password vault"
**Causes:**
- Item name doesn't exist in vault
- Case sensitivity mismatch
- Item in different vault

**Solution:**
1. Check item exists in 1Password
2. Use exact item title (case-sensitive)
3. Verify `OP_VAULT_ID` in `.env`

#### "MCP server connection failed"
**Causes:**
- Server failed to start
- Permission issues
- Missing MCP SDK

**Solution:**
```bash
# Reinstall MCP SDK
poetry add mcp

# Run with debug logging
python scripts/test_phase2.py
# (script uses ERROR level by default, modify for DEBUG if needed)
```

#### "A2A server not accessible"
**Causes:**
- A2A server not running
- Port 8000 already in use
- Firewall blocking connections

**Solution:**
```bash
# Check if server is running
curl http://localhost:8000/health

# Start the server if not running
poetry run python src/a2a/run_a2a.py

# Check if port 8000 is in use
lsof -i :8000

# Try a different port
poetry run python src/a2a/run_a2a.py --port 8001
```

#### "Authentication failed (401)"
**Causes:**
- Missing or invalid bearer token
- Token mismatch between client and server

**Solution:**
1. Check `.env` file for `A2A_BEARER_TOKEN`
2. Ensure test scripts use the same token
3. Default token: `dev-token-change-in-production`

#### "Task execution failed"
**Causes:**
- Invalid capability name
- Missing required parameters
- Resource not found in vault

**Solution:**
1. Check capability names in agent card
2. Verify all required parameters provided
3. Ensure resource exists in 1Password vault

#### "ACP server not accessible"
**Causes:**
- ACP server not running
- Port 8001 already in use
- Firewall blocking connections

**Solution:**
```bash
# Check if server is running
curl http://localhost:8001/health

# Start the server if not running
poetry run python src/acp/run_acp.py

# Check if port 8001 is in use
lsof -i :8001

# Try a different port
poetry run python src/acp/run_acp.py --port 8002
```

#### "Intent parsing failed"
**Causes:**
- Request text too vague or ambiguous
- Resource name not recognized
- Missing keywords

**Solution:**
1. Use clear, specific language:
   - ✅ "I need database credentials for production-postgres"
   - ❌ "Get me some creds"
2. Include resource type keywords (database, api, ssh)
3. Include resource name explicitly
4. Check demo examples for proper formatting

#### "Session not found"
**Causes:**
- Session ID doesn't exist
- Session expired
- Server restarted (in-memory sessions lost)

**Solution:**
1. Verify session ID is correct
2. Check if server was restarted
3. Create new session if needed (omit session_id in request)

---

## 📊 Test Coverage

### Phase 1 Tests Cover:
- CredentialManager initialization
- OnePasswordClient connectivity
- TokenManager encryption/decryption
- AuditLogger event posting
- End-to-end credential flow

### Phase 2 Tests Cover:
- MCP server initialization
- stdio transport communication
- Tool registration and discovery
- Credential retrieval via MCP protocol
- Error handling and validation
- Integration with Phase 1 components

### Phase 3 Tests Cover:
- A2A server initialization and health
- Agent card discovery and validation
- Task execution with capability routing
- Bearer token authentication
- All 4 capability handlers:
  - Database credentials
  - API credentials
  - SSH credentials
  - Generic secrets
- Error handling and validation
- SSE streaming support (via endpoints)
- Integration with Phase 1 components

### Phase 4 Tests Cover:
- ACP server initialization and health
- Agent discovery via /agents endpoint
- Natural language intent parsing:
  - Database credential requests
  - API credential requests
  - SSH key requests
  - Generic secret requests
- Session management and creation
- Interaction history tracking
- Multi-request sessions (conversation context)
- Session history retrieval
- Error handling:
  - Unknown agent names
  - Unparseable requests
  - Nonexistent sessions
- Integration with Phase 1 components
- All REST endpoints (/agents, /run, /sessions/{id}, /health)

---

## 🎯 Next Steps

After successfully running all test scripts:

1. ✅ **Phase 1:** Core Foundation ✅ COMPLETE
2. ✅ **Phase 2:** MCP Server ✅ COMPLETE
3. ✅ **Phase 3:** A2A Server ✅ COMPLETE
4. ✅ **Phase 4:** ACP Server ✅ COMPLETE
5. **Phase 5:** Add Docker orchestration
6. **Phase 6:** Create demo UI (optional)
7. **Phase 7:** Complete documentation
8. **Phase 8:** Final validation

**Current Progress:** 4/8 phases complete (50%)

---

## 📝 Notes

- **Test scripts are interactive** - They require user input during execution
- **Safe to run multiple times** - No destructive operations
- **Production credentials** - Use test credentials only
- **Audit logs** - All credential access is logged to 1Password Events API
- **Token expiry** - Test tokens expire after configured TTL (default 5 minutes)

---

## 🆘 Getting Help

If you encounter issues:

1. Check the error message carefully
2. Review the troubleshooting section above
3. Verify all prerequisites are met
4. Check `.env` configuration
5. Review the main README in `backend/README.md`

---

**Last Updated:** October 23, 2025  
**Status:** Phase 1, 2, 3 & 4 Complete ✅  
**Progress:** 4/8 phases (50%)

