# Helper Scripts

This directory contains comprehensive helper scripts for managing, testing, and operating the Universal 1Password Credential Broker.

---

## 📋 Available Scripts

### Service Management Scripts

#### Start All Services
**Script:** `start-all.sh`  
**Purpose:** Start all services (A2A, ACP) with comprehensive setup and health checks

```bash
cd backend
./scripts/start-all.sh

# Docker mode
./scripts/start-all.sh --docker

# Build Docker images
./scripts/start-all.sh --docker --build

# Foreground mode (Docker)
./scripts/start-all.sh --docker --foreground

# Skip specific services
./scripts/start-all.sh --without-a2a
./scripts/start-all.sh --without-acp

# Custom log level
./scripts/start-all.sh --log-level DEBUG

# Show help
./scripts/start-all.sh --help
```

**What it does:**
- ✅ Verifies .env file exists and loads environment variables
- ✅ Checks for required environment variables
- ✅ Verifies Poetry installation and dependencies
- ✅ Creates necessary directories (logs, data)
- ✅ Starts A2A server on port 8000
- ✅ Starts ACP server on port 8001
- ✅ Displays service status and endpoints
- ✅ Runs health checks
- ✅ Supports Docker mode with container orchestration

**Prerequisites:**
- Poetry installed
- .env file configured with 1Password credentials
- Dependencies installed (`poetry install`)
- Ports 8000 and 8001 available (or use Docker mode)

---

#### Stop All Services
**Script:** `stop-all.sh`  
**Purpose:** Gracefully stop all services with cleanup options

```bash
cd backend
./scripts/stop-all.sh

# Docker mode
./scripts/stop-all.sh --docker

# Force kill processes
./scripts/stop-all.sh --force

# Clean log files
./scripts/stop-all.sh --clean-logs

# Docker cleanup (remove volumes)
./scripts/stop-all.sh --docker --clean

# Docker purge (remove volumes and images)
./scripts/stop-all.sh --docker --purge

# Quiet mode
./scripts/stop-all.sh --quiet

# Show help
./scripts/stop-all.sh --help
```

**What it does:**
- ✅ Gracefully stops A2A and ACP servers
- ✅ Removes PID files
- ✅ Handles both Docker and non-Docker modes
- ✅ Optional log file cleanup
- ✅ Optional Docker volume/image cleanup
- ✅ Force kill option for stubborn processes

---

#### Health Check
**Script:** `health-check.sh`  
**Purpose:** Verify all services are running and healthy

```bash
cd backend
./scripts/health-check.sh

# Docker mode
./scripts/health-check.sh --docker

# Quiet mode (minimal output)
./scripts/health-check.sh --quiet

# Show help
./scripts/health-check.sh --help
```

**What it checks:**
- ✅ Service process status (non-Docker) or container status (Docker)
- ✅ HTTP health endpoints
- ✅ Service response validation
- ✅ Overall system health status

**Prerequisites:**
- Services must be running (start with `./scripts/start-all.sh`)

---

### Individual Server Scripts

#### MCP Server Launcher
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

#### A2A Server Launcher
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

#### ACP Server Launcher
**Script:** `acp_server.sh`  
**Purpose:** Start the ACP (Agent Communication Protocol) server with proper environment setup

```bash
cd backend
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

### Dashboard Script

#### Dashboard Launcher
**Script:** `run_dashboard.sh`  
**Purpose:** Start the Streamlit dashboard with proper environment setup

```bash
cd backend
./scripts/run_dashboard.sh
```

**What it does:**
- ✅ Checks for .env file and loads environment variables
- ✅ Verifies Poetry installation
- ✅ Installs UI dependencies (`poetry install --extras ui`)
- ✅ Finds available port (8501, 8503, 8504)
- ✅ Starts Streamlit dashboard with proper configuration
- ✅ Displays dashboard URL

**Prerequisites:**
- Poetry installed
- .env file configured
- UI dependencies will be installed automatically

**Access**: Dashboard will be available at http://localhost:8501 (or alternative port)

---

### Testing & Demo Scripts

#### Automated Demo Script
**Script:** `demo.sh`  
**Purpose:** Generate random traffic to all servers for dashboard metrics

```bash
cd backend
./scripts/demo.sh

# Custom iterations and delay
./scripts/demo.sh --iterations 20 --delay 1

# Continuous mode
./scripts/demo.sh --continuous

# Show help
./scripts/demo.sh --help
```

**What it does:**
- ✅ Checks server availability (A2A, ACP, MCP)
- ✅ Generates random credential requests across all protocols
- ✅ Tests various resource types (database, API, SSH)
- ✅ Provides real-time success/failure statistics
- ✅ Supports continuous mode for ongoing testing
- ✅ Compatible with dashboard metrics collection

**Test Types:**
- **A2A Tests**: Agent card discovery, database credentials, API credentials
- **ACP Tests**: Agent discovery, natural language requests, session management
- **MCP Tests**: Protocol communication via Poetry stdio

**Prerequisites:**
- A2A server running on port 8000
- ACP server running on port 8001
- Poetry available for MCP testing
- Valid 1Password credentials in .env

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

3. **Start All Services**
   ```bash
   ./scripts/start-all.sh
   ```

4. **Check Health**
   ```bash
   ./scripts/health-check.sh
   ```

5. **Run Demo**
   ```bash
   ./scripts/demo.sh --iterations 10
   ```

6. **Start Dashboard**
   ```bash
   ./scripts/run_dashboard.sh
   ```

### Common Workflows

#### Development Workflow
```bash
# Start services in development mode
./scripts/a2a_server.sh --reload --log-level DEBUG
./scripts/acp_server.sh --reload --log-level DEBUG

# Run tests
./scripts/demo.sh --iterations 5

# Check health
./scripts/health-check.sh

# Stop services
./scripts/stop-all.sh
```

#### Production Workflow
```bash
# Start with multiple workers
./scripts/a2a_server.sh --workers 4 --log-level INFO
./scripts/acp_server.sh --workers 4 --log-level INFO

# Monitor health
./scripts/health-check.sh --quiet

# Stop gracefully
./scripts/stop-all.sh
```

#### Docker Workflow
```bash
# Start with Docker
./scripts/start-all.sh --docker --build

# Check Docker health
./scripts/health-check.sh --docker

# Stop Docker services
./scripts/stop-all.sh --docker --clean
```

---

## 🔧 Troubleshooting

### Common Issues

#### "Service not responding"
**Causes:**
- Service failed to start
- Port already in use
- Environment variables missing

**Solution:**
```bash
# Check health
./scripts/health-check.sh

# Check logs
tail -f logs/*.log

# Restart services
./scripts/stop-all.sh
./scripts/start-all.sh
```

#### "Port already in use"
**Causes:**
- Another service using the port
- Previous service not stopped properly

**Solution:**
```bash
# Use different port
./scripts/a2a_server.sh --port 8001

# Or stop existing services
./scripts/stop-all.sh --force
```

#### "Poetry not found"
**Causes:**
- Poetry not installed
- Poetry not in PATH

**Solution:**
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Verify installation
poetry --version
```

#### "Dependencies not installed"
**Causes:**
- Poetry dependencies not installed
- Virtual environment not created

**Solution:**
```bash
# Install dependencies
poetry install

# For UI dependencies
poetry install --extras ui
```

#### "Environment variables missing"
**Causes:**
- .env file not found
- Required variables not set

**Solution:**
```bash
# Create .env file
cp .env.example .env

# Edit with your values
nano .env
```

---

## 📊 Script Features

### Error Handling
- ✅ Comprehensive error checking
- ✅ Graceful failure handling
- ✅ Clear error messages
- ✅ Exit codes for automation

### Logging
- ✅ Structured output with colors
- ✅ Progress indicators
- ✅ Success/failure status
- ✅ Debug information

### Port Management
- ✅ Port availability checking
- ✅ Automatic port selection (dashboard)
- ✅ Port conflict resolution

### Environment Management
- ✅ Automatic .env loading
- ✅ Environment variable validation
- ✅ Poetry environment activation

### Docker Support
- ✅ Full Docker Compose integration
- ✅ Container health checking
- ✅ Volume management
- ✅ Image building

---

## 🎯 Next Steps

After successfully using the helper scripts:

1. ✅ **Service Management** - Start/stop/health check services
2. ✅ **Individual Servers** - Run MCP, A2A, ACP servers
3. ✅ **Dashboard** - Monitor with real-time UI
4. ✅ **Testing** - Automated demo and validation
5. **Integration** - Connect with your AI agents
6. **Production** - Deploy with proper configuration

**Current Progress:** All helper scripts operational ✅

---

## 📝 Notes

- **Scripts are safe to run multiple times** - No destructive operations
- **Production credentials** - Use test credentials only
- **Audit logs** - All credential access is logged to 1Password Events API
- **Token expiry** - Test tokens expire after configured TTL (default 5 minutes)
- **Docker support** - Full container orchestration available

---

## 🆘 Getting Help

If you encounter issues:

1. Check the error message carefully
2. Review the troubleshooting section above
3. Verify all prerequisites are met
4. Check `.env` configuration
5. Review the main README in `backend/README.md`
6. Use `--help` flag with any script for usage information

---

**Last Updated:** October 23, 2025  
**Status:** All Scripts Complete ✅  
**Progress:** 8/8 scripts operational (100%)

