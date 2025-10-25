# Universal 1Password Agent Credential Broker

**Multi-Protocol Credential Broker supporting MCP, A2A, and ACP**

[![Status](https://img.shields.io/badge/status-operational-green)]()
[![Protocols](https://img.shields.io/badge/protocols-MCP%20%7C%20A2A%20%7C%20ACP-orange)]()
[![Python](https://img.shields.io/badge/python-3.12+-blue)]()

---

## 🎯 Overview

A universal credential broker that integrates with the AI agent ecosystem by supporting multiple communication protocols — **MCP** (Model Context Protocol), **A2A** (Agent-to-Agent), and **ACP** (Agent Communication Protocol) — enabling secure, ephemeral credential exchange across agent frameworks.

### Key Features

✨ **Multi-Protocol Support** - Single broker, three protocols (MCP, A2A, ACP)  
🔐 **Security-First** - Ephemeral JWT tokens, AES-256 encryption, <5 min TTL  
📊 **Full Observability** - 100% audit logging via 1Password Events API  
🚀 **Ecosystem Ready** - Compatible with CrewAI, LangChain, Claude, and more  
🎨 **Interactive Dashboard** - Real-time WebSocket dashboard for protocol visualization

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- 1Password Connect Server instance
- 1Password Connect API token
- Poetry (for dependency management)

### Installation

```bash
# 1. Clone and navigate to project
cd /Users/aniruth/projects/1password-demo

# 2. Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install backend dependencies
cd backend
poetry install

# 4. Configure environment
cp .env.example .env
# Edit .env with your 1Password credentials

# 5. Install frontend dependencies
cd ../frontend
poetry install
```

### Running the Services

#### Start All Services (Recommended)

```bash
cd backend

# Start backend servers (A2A, ACP)
./scripts/start-all.sh

# Check health
./scripts/health-check.sh

# In another terminal: Start dashboard
cd frontend
./start-fe.sh
```

#### Access Points

- **A2A Server**: http://localhost:8000
- **ACP Server**: http://localhost:8001
- **Dashboard**: http://localhost:3000
- **API Docs**: 
  - A2A: http://localhost:8000/docs
  - ACP: http://localhost:8001/docs

---

## 📚 Protocol Guide

### When to Use Each Protocol

| Protocol | Best For | Example Use Case |
|----------|----------|------------------|
| **MCP** | AI models calling credential tools | ChatGPT plugin requesting DB credentials |
| **A2A** | Agent-to-agent collaboration | Data agent requests creds from credential agent |
| **ACP** | Framework REST API integration | CrewAI agent using structured credential requests |

### MCP Example

```python
from mcp.client.session import ClientSession

async with ClientSession(read, write) as session:
    result = await session.call_tool(
        "get_credentials",
        resource_type="database",
        resource_name="prod-postgres",
        requesting_agent_id="assistant-001"
    )
    print(f"Token: {result['token']}")  # Expires in 5 minutes
```

### A2A Example

```python
import requests

# Discover agent
card = requests.get("http://localhost:8000/agent-card").json()

# Request credentials
response = requests.post("http://localhost:8000/task", json={
    "task_id": "task-123",
    "capability_name": "request_database_credentials",
    "parameters": {"database_name": "analytics-db"},
    "requesting_agent_id": "data-agent"
})
```

### ACP Example

```python
import requests

# Natural language request
response = requests.post("http://localhost:8001/run", json={
    "agent_name": "credential-broker",
    "input": [{
        "parts": [{
            "content": "I need database credentials for production-db",
            "content_type": "text/plain"
        }]
    }]
})
```

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│        Universal 1Password Credential Broker               │
│                                                            │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│  │   MCP   │    │   A2A   │    │   ACP   │                │
│  │  Server │    │  Server │    │  Server │                │
│  │  (Tool) │    │ (Agent) │    │  (REST) │                │
│  └────┬────┘    └────┬────┘    └────┬────┘                │
│       │              │              │                      │
│       └──────────────┴──────────────┘                      │
│                      │                                     │
│            ┌─────────▼─────────┐                           │
│            │ Credential Manager │                           │
│            │  - JWT (5min TTL) │                           │
│            │  - AES-256 Encrypt│                           │
│            │  - Audit Logging  │                           │
│            └─────────┬─────────┘                           │
│                      │                                     │
└──────────────────────┼─────────────────────────────────────┘
                       │
                       ▼
             ┌──────────────────┐
             │  1Password Vault │
             │   + Events API   │
             └──────────────────┘
```

---

## 📁 Project Structure

```
project-root/
├── README.md                    ← You are here
├── backend/                     ← Backend services
│   ├── src/
│   │   ├── core/               ← Core components
│   │   ├── mcp/                ← MCP server
│   │   ├── a2a/                ← A2A server
│   │   ├── acp/                ← ACP server
│   │   └── ui/                 ← Streamlit dashboard
│   ├── scripts/                ← Helper scripts
│   ├── tests/                  ← Test suite
│   ├── demos/                  ← Demo scenarios
│   └── pyproject.toml          ← Poetry dependencies
├── frontend/                    ← FastAPI + Tailwind dashboard
│   ├── app.py                  ← Main dashboard app
│   ├── pyproject.toml          ← Frontend dependencies
│   └── start-fe.sh             ← Startup script
└── docs/                        ← Documentation
```

---

## 🎨 Dashboard

### Features

- **Real-Time Metrics**: Live updates via WebSocket connections
- **Protocol Testing**: Interactive buttons to test MCP, A2A, and ACP protocols
- **Activity Feed**: Real-time visualization of credential access events
- **Token Display**: View and copy generated JWT tokens
- **Responsive Design**: Beautiful UI with Tailwind CSS

### Starting the Dashboard

```bash
cd frontend
./start-fe.sh
```

Then open http://localhost:3000 in your browser.

---

## 🔐 Security Features

- ✅ **Ephemeral Tokens:** Default 5-minute TTL, configurable
- ✅ **AES-256 Encryption:** Credential payloads encrypted in JWTs
- ✅ **Bearer Authentication:** All A2A/ACP endpoints protected
- ✅ **Zero Standing Privilege:** No credentials stored locally
- ✅ **Full Audit Trail:** 100% event logging to 1Password Events API
- ✅ **TLS/HTTPS:** Secure transport for all communications

---

## 📊 Environment Configuration

### Backend (.env)

```env
# 1Password Connect
OP_CONNECT_HOST=http://localhost:8080
OP_CONNECT_TOKEN=your-connect-token
OP_VAULT_ID=your-vault-id

# JWT Configuration
JWT_SECRET_KEY=your-32-character-secret-key
TOKEN_TTL_MINUTES=5

# Backend Servers
A2A_SERVER_URL=http://localhost:8000
ACP_SERVER_URL=http://localhost:8001
A2A_BEARER_TOKEN=dev-token-change-in-production
ACP_BEARER_TOKEN=dev-token-change-in-production
```

### Frontend (.env)

```env
# 1Password Connect
OP_CONNECT_HOST=http://localhost:8080
OP_CONNECT_TOKEN=your-connect-token
OP_VAULT_ID=your-vault-id

# JWT Configuration
JWT_SECRET_KEY=your-32-character-secret-key

# Backend Server URLs
A2A_SERVER_URL=http://localhost:8000
ACP_SERVER_URL=http://localhost:8001
A2A_BEARER_TOKEN=dev-token-change-in-production
ACP_BEARER_TOKEN=dev-token-change-in-production
```

---

## 🛠️ Helper Scripts

### Service Management

```bash
cd backend

# Start all services
./scripts/start-all.sh

# Stop all services
./scripts/stop-all.sh

# Check health
./scripts/health-check.sh

# Run demo
./scripts/demo.sh --iterations 10
```

### Individual Services

```bash
# MCP Server (interactive)
./scripts/mcp_server.sh

# A2A Server
./scripts/a2a_server.sh

# ACP Server
./scripts/acp_server.sh

# Dashboard
./scripts/run_dashboard.sh
```

---

## 🧪 Testing

### Manual Testing

```bash
# Test A2A
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token-change-in-production" \
  -d '{"task_id":"test","capability_name":"request_database_credentials","parameters":{"database_name":"test-db"},"requesting_agent_id":"test"}'

# Test ACP
curl -X POST http://localhost:8001/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token-change-in-production" \
  -d '{"agent_name":"credential-broker","input":[{"parts":[{"content":"I need database credentials for test-db","content_type":"text/plain"}]}]}'
```

### Automated Testing

```bash
# Run all tests
cd backend
make test

# Run with coverage
make test-cov

# Run demo script
./scripts/demo.sh --iterations 20 --delay 1
```

---

## 📊 Test Coverage

Current test coverage: **76%**

| Module | Coverage |
|--------|----------|
| audit_logger.py | 98% ✅ |
| credential_manager.py | 96% ✅ |
| token_manager.py | 94% ✅ |
| onepassword_client.py | 87% ✅ |
| mcp_server.py | 65% ✅ |

---

## 🐳 Docker Support

```bash
# Start with Docker
cd backend
./scripts/start-all.sh --docker --build

# Check Docker health
./scripts/health-check.sh --docker

# Stop Docker services
./scripts/stop-all.sh --docker --clean
```

---

## 🎬 Demo Scenarios

### Scenario 1: MCP Integration
**Demo:** AI assistant fetches ephemeral database credentials  
**File:** `backend/demos/mcp_demo.py`  
**Duration:** ~30 seconds

### Scenario 2: A2A Collaboration
**Demo:** Data agent discovers and requests credentials from broker  
**File:** `backend/demos/a2a_demo.py`  
**Duration:** ~45 seconds

### Scenario 3: ACP Session
**Demo:** CrewAI agent acquires SSH keys via natural language  
**File:** `backend/demos/acp_demo.py`  
**Duration:** ~30 seconds

---

## 📚 Additional Documentation

- **[docs/README.md](docs/README.md)** - Detailed documentation
- **[docs/TODO.md](docs/TODO.md)** - Implementation checklist
- **[backend/scripts/README.md](backend/scripts/README.md)** - Script documentation

---

## 🤝 Development

### Adding a New Protocol

1. Create server in `backend/src/<protocol>/`
2. Implement credential manager integration
3. Add tests in `backend/tests/`
4. Update dashboard UI
5. Add demo script

### Code Quality

```bash
# Format code
make format

# Run linter
make lint

# Type checking
make typecheck

# All quality checks
make qa
```

---

## 📝 License

This project is for demonstration and educational purposes.

---

## 🆘 Troubleshooting

### Services Won't Start

```bash
# Check prerequisites
poetry --version
python --version

# Verify .env configuration
cat .env

# Check port availability
lsof -i :8000  # A2A
lsof -i :8001  # ACP
lsof -i :3000  # Dashboard
```

### Protocol Tests Failing

```bash
# Check backend services
curl http://localhost:8000/health  # A2A
curl http://localhost:8001/health  # ACP

# Check bearer tokens in .env
grep BEARER_TOKEN .env

# Review logs
tail -f backend/logs/*.log
```

### Dashboard Not Loading

```bash
# Restart dashboard
cd frontend
./start-fe.sh

# Check WebSocket connection
# Open browser DevTools → Console
```

---

## 🎓 Learning Resources

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Agent2Agent Protocol (A2A)](https://a2aprotocol.ai)
- [Agent Communication Protocol (ACP)](https://agentcommunicationprotocol.dev)
- [1Password Connect API](https://developer.1password.com/docs/connect)
- [1Password Events API](https://developer.1password.com/docs/events-api)

---

**Last Updated:** October 24, 2025  
**Version:** 1.0.0  
**Status:** ✅ Operational
