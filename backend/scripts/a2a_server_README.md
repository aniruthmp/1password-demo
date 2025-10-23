# A2A Server Launcher Script

## Overview

`a2a_server.sh` is a production-ready launcher script for the A2A (Agent-to-Agent) credential broker server. It provides environment validation, dependency checking, and graceful server startup with comprehensive error handling.

---

## Quick Start

```bash
cd backend

# Basic usage (default settings)
./scripts/a2a_server.sh

# Development mode with auto-reload
./scripts/a2a_server.sh --reload --log-level DEBUG

# Production mode with multiple workers
./scripts/a2a_server.sh --workers 4

# Custom port
./scripts/a2a_server.sh --port 8001
```

---

## Features

### Environment Validation
- ✅ Verifies `.env` file exists
- ✅ Checks required environment variables:
  - `OP_CONNECT_HOST`
  - `OP_CONNECT_TOKEN`
  - `OP_VAULT_ID`
  - `JWT_SECRET_KEY`
- ⚠️ Warns if `A2A_BEARER_TOKEN` not set (uses default)

### Dependency Checking
- ✅ Verifies Poetry installation
- ✅ Checks if dependencies are installed
- ✅ Auto-installs dependencies if missing

### Port Management
- ✅ Validates port number (1-65535)
- ✅ Checks if port is available before starting
- ✅ Suggests alternative port if occupied

### Server Configuration
- ✅ Displays all configuration settings
- ✅ Shows API endpoint URLs
- ✅ Provides link to auto-generated docs

### Graceful Operations
- ✅ Handles Ctrl+C gracefully
- ✅ Proper signal handling (SIGINT, SIGTERM)
- ✅ Clean shutdown messages

---

## Command Line Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--port PORT` | Server port | 8000 | `--port 8001` |
| `--host HOST` | Server host | 0.0.0.0 | `--host 127.0.0.1` |
| `--log-level LEVEL` | Logging level | INFO | `--log-level DEBUG` |
| `--reload` | Auto-reload on code changes | Disabled | `--reload` |
| `--workers N` | Number of worker processes | 1 | `--workers 4` |
| `-h, --help` | Show help message | N/A | `--help` |

### Valid Log Levels
- `DEBUG` - Detailed debugging information
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages only
- `CRITICAL` - Critical errors only

---

## Usage Examples

### Development Mode
```bash
# Auto-reload when code changes + debug logging
./scripts/a2a_server.sh --reload --log-level DEBUG
```

### Production Mode
```bash
# Multiple workers for better performance
./scripts/a2a_server.sh --workers 4 --log-level WARNING
```

### Custom Configuration
```bash
# Custom port + host + logging
./scripts/a2a_server.sh --port 9000 --host 127.0.0.1 --log-level INFO
```

### Testing Setup
```bash
# Terminal 1: Start server
./scripts/a2a_server.sh

# Terminal 2: Run tests
poetry run python scripts/test_phase3.py
```

---

## Output Example

```
============================================================
  1Password Credential Broker - A2A Server Launcher
============================================================

➜ Changing to backend directory...
✅ Working directory: /path/to/backend

➜ Checking for .env file...
✅ .env file found

➜ Loading environment variables from .env...
✅ Environment variables loaded

➜ Verifying required environment variables...
✅ All required environment variables present

➜ Checking for Poetry installation...
✅ Poetry is installed: Poetry (version 1.7.1)

➜ Checking Poetry dependencies...
✅ Dependencies are installed

➜ Verifying A2A server script...
✅ A2A server script found

➜ Checking if port 8000 is available...
✅ Port 8000 is available

============================================================
  Starting A2A Server
============================================================

Configuration:
  Host:             0.0.0.0
  Port:             8000
  Log Level:        INFO
  Connect Host:     http://localhost:8080
  Vault ID:         your-vault-id
  Workers:          1

API Endpoints:
  Agent Card:       http://0.0.0.0:8000/agent-card
  Task Execution:   http://0.0.0.0:8000/task
  Health Check:     http://0.0.0.0:8000/health
  API Docs:         http://0.0.0.0:8000/docs

Press Ctrl+C to stop the server

============================================================

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Troubleshooting

### Port Already in Use
```
❌ Port 8000 is already in use!

Please stop the service using port 8000 or use a different port:
  ./scripts/a2a_server.sh --port 8001
```

**Solution:**
1. Check what's using the port: `lsof -i :8000`
2. Stop the process or use a different port

### Missing Environment Variables
```
❌ Missing required environment variables:
  - OP_CONNECT_HOST
  - OP_CONNECT_TOKEN
  - JWT_SECRET_KEY
```

**Solution:**
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Fill in all required values
3. Run the script again

### Poetry Not Installed
```
❌ Poetry is not installed!

Please install Poetry:
  curl -sSL https://install.python-poetry.org | python3 -
```

**Solution:**
1. Install Poetry using the provided command
2. Restart your terminal
3. Run the script again

### Missing Dependencies
```
⚠️ Dependencies not installed or incomplete
➜ Installing dependencies...
```

This is automatically handled by the script. Dependencies will be installed if missing.

---

## Comparison with MCP Server Launcher

| Feature | mcp_server.sh | a2a_server.sh |
|---------|---------------|---------------|
| Transport | stdio | HTTP REST |
| Port | N/A | 8000 (configurable) |
| Workers | N/A | 1-N (configurable) |
| Auto-reload | Yes | Yes |
| Port checking | No | Yes |
| API Docs URL | No | Yes |
| Multiple workers | No | Yes |

---

## Integration with Testing

### With test_phase3.py
```bash
# Terminal 1: Start server
./scripts/a2a_server.sh

# Terminal 2: Run tests
poetry run python scripts/test_phase3.py
```

### With a2a_demo.py
```bash
# Terminal 1: Start server
./scripts/a2a_server.sh

# Terminal 2: Run demo
poetry run python demos/a2a_demo.py
```

### With curl
```bash
# Start server
./scripts/a2a_server.sh

# In another terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/agent-card
```

---

## Environment Variables

### Required
- `OP_CONNECT_HOST` - 1Password Connect server URL
- `OP_CONNECT_TOKEN` - 1Password Connect API token
- `OP_VAULT_ID` - 1Password vault ID
- `JWT_SECRET_KEY` - Secret key for JWT signing (min 32 chars)

### Optional
- `A2A_BEARER_TOKEN` - Bearer token for A2A authentication
  - Default: `dev-token-change-in-production`
  - **Important:** Change this in production!

### Example .env
```bash
# 1Password Connect Configuration
OP_CONNECT_HOST=http://localhost:8080
OP_CONNECT_TOKEN=your_connect_token_here
OP_VAULT_ID=your_vault_id_here

# JWT Configuration
JWT_SECRET_KEY=your_secret_key_at_least_32_characters_long

# A2A Configuration (optional)
A2A_BEARER_TOKEN=your_secure_bearer_token_here
```

---

## Security Notes

⚠️ **Important Security Considerations:**

1. **Bearer Token**: Always change `A2A_BEARER_TOKEN` in production
2. **Host Binding**: Use `--host 127.0.0.1` for local-only access
3. **HTTPS**: Use a reverse proxy (nginx/traefik) with TLS in production
4. **Environment Variables**: Never commit `.env` file to version control
5. **Log Level**: Use `WARNING` or `ERROR` in production to avoid sensitive data in logs

---

## Related Documentation

- **Main README:** `backend/README.md`
- **Testing Guide:** `scripts/README.md`
- **Phase 3 Docs:** `docs/PHASE3_COMPLETE.md`
- **A2A Server Code:** `src/a2a/a2a_server.py`
- **API Documentation:** http://localhost:8000/docs (when server is running)

---

## Script Maintenance

**Location:** `backend/scripts/a2a_server.sh`  
**Permissions:** Executable (`chmod +x`)  
**Shell:** Bash 3.2+  
**Dependencies:** Poetry, bash, lsof  

**Last Updated:** October 23, 2025  
**Version:** 1.0.0  

---

*For questions or issues, refer to the main project documentation.*

