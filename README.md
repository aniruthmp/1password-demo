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

## 📖 API Documentation

### MCP Server (Model Context Protocol)

The MCP server provides tools for AI models to request credentials through the Model Context Protocol.

#### Tools Available

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `get_credentials` | Retrieve ephemeral credentials for a resource | `resource_type`, `resource_name`, `requesting_agent_id` |
| `list_resources` | List available resources in the vault | `requesting_agent_id` |
| `get_resource_info` | Get detailed information about a specific resource | `resource_name`, `requesting_agent_id` |

#### Example Usage

```python
from mcp.client.session import ClientSession

async with ClientSession(read, write) as session:
    # List available resources
    resources = await session.call_tool(
        "list_resources",
        requesting_agent_id="assistant-001"
    )
    
    # Get credentials for a database
    result = await session.call_tool(
        "get_credentials",
        resource_type="database",
        resource_name="prod-postgres",
        requesting_agent_id="assistant-001"
    )
    
    print(f"Token: {result['token']}")
    print(f"Expires in: {result['expires_in']} seconds")
```

#### Response Format

```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 300,
    "resource": "database/prod-postgres",
    "agent_id": "assistant-001",
    "issued_at": "2025-01-24T10:30:00Z"
}
```

---

### A2A Server (Agent-to-Agent Protocol)

The A2A server enables agent-to-agent communication for credential requests.

#### Base URL
```
http://localhost:8000
```

#### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer dev-token-change-in-production
```

#### Endpoints

##### 1. Agent Card Discovery
**GET** `/agent-card`

Discover the credential broker agent's capabilities.

**Response:**
```json
{
    "agent_id": "1password-credential-broker",
    "name": "1Password Credential Broker",
    "version": "1.0.0",
    "capabilities": [
        "request_database_credentials",
        "request_api_credentials", 
        "request_ssh_credentials",
        "request_general_credentials"
    ],
    "supported_protocols": ["A2A"],
    "endpoints": {
        "task_execution": "/task",
        "health_check": "/health"
    }
}
```

##### 2. Task Execution
**POST** `/task`

Execute a credential request task.

**Request Body:**
```json
{
    "task_id": "unique-task-id",
    "capability_name": "request_database_credentials",
    "parameters": {
        "database_name": "production-db",
        "duration_minutes": 5
    },
    "requesting_agent_id": "data-processing-agent"
}
```

**Response:**
```json
{
    "task_id": "unique-task-id",
    "status": "completed",
    "result": {
        "ephemeral_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "expires_in": 300,
        "resource": "database/production-db",
        "agent_id": "data-processing-agent"
    },
    "execution_time_ms": 150,
    "timestamp": "2025-01-24T10:30:00Z"
}
```

##### 3. Health Check
**GET** `/health`

Check server health and status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-24T10:30:00Z",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "active_connections": 5
}
```

#### Error Responses

**401 Unauthorized:**
```json
{
    "error": "unauthorized",
    "message": "Invalid or missing bearer token"
}
```

**400 Bad Request:**
```json
{
    "error": "bad_request",
    "message": "Invalid task parameters",
    "details": {
        "missing_fields": ["task_id", "capability_name"]
    }
}
```

**500 Internal Server Error:**
```json
{
    "error": "internal_error",
    "message": "Failed to retrieve credentials from 1Password",
    "request_id": "req-123456"
}
```

---

### ACP Server (Agent Communication Protocol)

The ACP server provides REST API endpoints for natural language credential requests.

#### Base URL
```
http://localhost:8001
```

#### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer dev-token-change-in-production
```

#### Endpoints

##### 1. Agent Discovery
**GET** `/agents`

List available agents and their capabilities.

**Response:**
```json
{
    "agents": [
        {
            "name": "credential-broker",
            "description": "1Password Credential Broker for secure credential management",
            "capabilities": [
                "database_credentials",
                "api_credentials",
                "ssh_credentials",
                "general_credentials"
            ],
            "version": "1.0.0"
        }
    ]
}
```

##### 2. Run Agent
**POST** `/run`

Execute a natural language request with an agent.

**Request Body:**
```json
{
    "agent_name": "credential-broker",
    "input": [
        {
            "parts": [
                {
                    "content": "I need database credentials for the production database",
                    "content_type": "text/plain"
                }
            ]
        }
    ],
    "session_id": "session-123"
}
```

**Response:**
```json
{
    "run_id": "run-456",
    "session_id": "session-123",
    "status": "completed",
    "output": [
        {
            "parts": [
                {
                    "content": "I've retrieved the database credentials for the production database. Here are the details:",
                    "content_type": "text/plain"
                },
                {
                    "content": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "content_type": "application/jwt"
                }
            ]
        }
    ],
    "execution_time_ms": 200,
    "timestamp": "2025-01-24T10:30:00Z"
}
```

##### 3. Session History
**GET** `/sessions/{session_id}`

Retrieve the history of interactions for a session.

**Response:**
```json
{
    "session_id": "session-123",
    "interactions": [
        {
            "run_id": "run-456",
            "timestamp": "2025-01-24T10:30:00Z",
            "request_summary": "I need database credentials for the production database",
            "response_summary": "Retrieved database credentials",
            "status": "completed"
        }
    ],
    "total_interactions": 1,
    "created_at": "2025-01-24T10:30:00Z"
}
```

##### 4. Health Check
**GET** `/health`

Check server health and status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-24T10:30:00Z",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "active_sessions": 3
}
```

#### Error Responses

**401 Unauthorized:**
```json
{
    "error": "unauthorized",
    "message": "Invalid or missing bearer token"
}
```

**400 Bad Request:**
```json
{
    "error": "bad_request",
    "message": "Invalid request format",
    "details": {
        "missing_fields": ["agent_name", "input"]
    }
}
```

**404 Not Found:**
```json
{
    "error": "not_found",
    "message": "Agent not found",
    "details": {
        "agent_name": "non-existent-agent"
    }
}
```

---

## 🚀 Deployment Guide

### Production Deployment

This guide covers deploying the Universal 1Password Agent Credential Broker in production environments.

#### Prerequisites

- Docker and Docker Compose
- 1Password Connect Server (self-hosted or cloud)
- Valid 1Password Connect API token
- Domain name and SSL certificates (for production)
- Reverse proxy (nginx/traefik) for load balancing

#### Environment Setup

##### 1. 1Password Connect Server

**Self-Hosted Option:**
```bash
# Download 1Password Connect Server
wget https://cache.agilebits.com/dist/1P/op2/pkg/v2.24.0/op2_linux_amd64_v2.24.0.zip
unzip op2_linux_amd64_v2.24.0.zip
sudo mv op2 /usr/local/bin/

# Start Connect Server
op2 connect server --config /etc/1password/connect.json
```

**Cloud Option:**
Use 1Password's managed Connect service.

##### 2. Environment Variables

Create production `.env` file:

```env
# 1Password Connect Configuration
OP_CONNECT_HOST=https://your-connect-server.com
OP_CONNECT_TOKEN=your-production-connect-token
OP_VAULT_ID=your-production-vault-id

# JWT Configuration
JWT_SECRET_KEY=your-32-character-production-secret-key
TOKEN_TTL_MINUTES=5

# Server Configuration
A2A_SERVER_URL=https://your-domain.com/a2a
ACP_SERVER_URL=https://your-domain.com/acp
A2A_BEARER_TOKEN=your-production-a2a-bearer-token
ACP_BEARER_TOKEN=your-production-acp-bearer-token

# Security
ALLOWED_ORIGINS=https://your-domain.com,https://your-dashboard.com
CORS_ENABLED=true

# Logging
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true
```

#### Docker Deployment

##### 1. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  a2a-server:
    build:
      context: .
      dockerfile: docker/Dockerfile.a2a
    ports:
      - "8000:8000"
    environment:
      - OP_CONNECT_HOST=${OP_CONNECT_HOST}
      - OP_CONNECT_TOKEN=${OP_CONNECT_TOKEN}
      - OP_VAULT_ID=${OP_VAULT_ID}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - A2A_BEARER_TOKEN=${A2A_BEARER_TOKEN}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  acp-server:
    build:
      context: .
      dockerfile: docker/Dockerfile.acp
    ports:
      - "8001:8001"
    environment:
      - OP_CONNECT_HOST=${OP_CONNECT_HOST}
      - OP_CONNECT_TOKEN=${OP_CONNECT_TOKEN}
      - OP_VAULT_ID=${OP_VAULT_ID}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ACP_BEARER_TOKEN=${ACP_BEARER_TOKEN}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  dashboard:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - A2A_SERVER_URL=${A2A_SERVER_URL}
      - ACP_SERVER_URL=${ACP_SERVER_URL}
      - A2A_BEARER_TOKEN=${A2A_BEARER_TOKEN}
      - ACP_BEARER_TOKEN=${ACP_BEARER_TOKEN}
    restart: unless-stopped
    depends_on:
      - a2a-server
      - acp-server

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    restart: unless-stopped
    depends_on:
      - a2a-server
      - acp-server
      - dashboard
```

##### 2. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream a2a_backend {
        server a2a-server:8000;
    }
    
    upstream acp_backend {
        server acp-server:8001;
    }
    
    upstream dashboard_backend {
        server dashboard:3000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # A2A API
        location /a2a/ {
            proxy_pass http://a2a_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # ACP API
        location /acp/ {
            proxy_pass http://acp_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Dashboard
        location / {
            proxy_pass http://dashboard_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

##### 3. Deploy with Docker Compose

```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Check service health
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Kubernetes Deployment

##### 1. Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: 1password-broker
```

##### 2. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: broker-config
  namespace: 1password-broker
data:
  OP_CONNECT_HOST: "https://your-connect-server.com"
  OP_VAULT_ID: "your-vault-id"
  TOKEN_TTL_MINUTES: "5"
  LOG_LEVEL: "INFO"
```

##### 3. Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: broker-secrets
  namespace: 1password-broker
type: Opaque
data:
  OP_CONNECT_TOKEN: <base64-encoded-token>
  JWT_SECRET_KEY: <base64-encoded-secret>
  A2A_BEARER_TOKEN: <base64-encoded-token>
  ACP_BEARER_TOKEN: <base64-encoded-token>
```

##### 4. A2A Server Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: a2a-server
  namespace: 1password-broker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: a2a-server
  template:
    metadata:
      labels:
        app: a2a-server
    spec:
      containers:
      - name: a2a-server
        image: your-registry/1password-broker:a2a-latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: broker-config
        - secretRef:
            name: broker-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: a2a-service
  namespace: 1password-broker
spec:
  selector:
    app: a2a-server
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

##### 5. ACP Server Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acp-server
  namespace: 1password-broker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: acp-server
  template:
    metadata:
      labels:
        app: acp-server
    spec:
      containers:
      - name: acp-server
        image: your-registry/1password-broker:acp-latest
        ports:
        - containerPort: 8001
        envFrom:
        - configMapRef:
            name: broker-config
        - secretRef:
            name: broker-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: acp-service
  namespace: 1password-broker
spec:
  selector:
    app: acp-server
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

##### 6. Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: broker-ingress
  namespace: 1password-broker
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: broker-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /a2a
        pathType: Prefix
        backend:
          service:
            name: a2a-service
            port:
              number: 8000
      - path: /acp
        pathType: Prefix
        backend:
          service:
            name: acp-service
            port:
              number: 8001
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dashboard-service
            port:
              number: 3000
```

#### Security Best Practices

##### 1. Network Security

- Use TLS/HTTPS for all communications
- Implement network segmentation
- Use firewall rules to restrict access
- Enable DDoS protection

##### 2. Authentication & Authorization

- Use strong, unique bearer tokens
- Implement token rotation
- Use RBAC for Kubernetes deployments
- Enable audit logging

##### 3. Secrets Management

- Store secrets in secure vaults (HashiCorp Vault, AWS Secrets Manager)
- Use Kubernetes secrets with encryption at rest
- Implement secret rotation
- Never commit secrets to version control

##### 4. Monitoring & Observability

- Enable comprehensive logging
- Implement metrics collection (Prometheus/Grafana)
- Set up alerting for failures
- Monitor resource usage

#### Monitoring Setup

##### 1. Prometheus Configuration

```yaml
global:
  scrape_interval: 15s

scrape_configs:
- job_name: 'a2a-server'
  static_configs:
  - targets: ['a2a-server:8000']
  metrics_path: /metrics

- job_name: 'acp-server'
  static_configs:
  - targets: ['acp-server:8001']
  metrics_path: /metrics
```

##### 2. Grafana Dashboard

Create dashboards for:
- Request rate and latency
- Error rates
- Token generation metrics
- Resource utilization
- Audit log events

##### 3. Alerting Rules

```yaml
groups:
- name: broker-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service is down"
```

#### Backup & Recovery

##### 1. Configuration Backup

```bash
# Backup environment configuration
kubectl get configmap broker-config -o yaml > backup/configmap.yaml
kubectl get secret broker-secrets -o yaml > backup/secret.yaml
```

##### 2. Disaster Recovery

- Maintain backup 1Password Connect Server
- Document recovery procedures
- Test recovery processes regularly
- Implement automated failover

#### Troubleshooting

##### Common Issues

**1. Services Not Starting**
```bash
# Check logs
docker-compose logs a2a-server
kubectl logs -f deployment/a2a-server

# Verify environment variables
docker-compose exec a2a-server env | grep OP_
```

**2. Authentication Failures**
```bash
# Test 1Password Connect
curl -H "Authorization: Bearer $OP_CONNECT_TOKEN" \
     "$OP_CONNECT_HOST/v1/vaults"

# Verify bearer tokens
curl -H "Authorization: Bearer $A2A_BEARER_TOKEN" \
     "http://localhost:8000/health"
```

**3. Performance Issues**
```bash
# Check resource usage
docker stats
kubectl top pods

# Monitor request latency
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/health"
```

#### Production Checklist

- [ ] SSL certificates configured
- [ ] Environment variables set
- [ ] Health checks working
- [ ] Monitoring configured
- [ ] Backup procedures tested
- [ ] Security review completed
- [ ] Load testing performed
- [ ] Documentation updated

---

**Last Updated:** October 24, 2025  
**Version:** 1.0.0  
**Status:** ✅ Operational