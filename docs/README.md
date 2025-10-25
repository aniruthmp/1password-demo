# Documentation Archive

> **⚠️ Note:** This is historical/planning documentation. For the current project documentation, see **[README.md](../README.md)** at the project root.

---

## 📚 Historical Documentation

This directory contains planning, implementation, and reference documentation from the project's development phases.

### Documents

| Document | Purpose | Status |
|----------|---------|--------|
| **[TODO.md](TODO.md)** | Comprehensive task list (100+ tasks, 8 phases) | ✅ Historical reference |
| **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** | Progress tracking | ✅ Historical reference |
| **[PROJECT_ROADMAP.md](PROJECT_ROADMAP.md)** | Visual roadmap, architecture | ✅ Historical reference |
| **[PLANNING_SUMMARY.md](PLANNING_SUMMARY.md)** | Coverage verification | ✅ Historical reference |
| **[PRD-ver-1.0.md](PRD-ver-1.0.md)** | Product requirements document | ✅ Historical reference |
| **[poc.md](poc.md)** | Proof-of-concept technical details | ✅ Historical reference |

---

## 🎯 Project Overview

A universal credential broker that integrates with the **AI agent ecosystem** by supporting multiple communication protocols — **MCP** (Model Context Protocol), **A2A** (Agent-to-Agent), and **ACP** (Agent Communication Protocol) — enabling secure, ephemeral credential exchange across agent frameworks.

### Key Features

✨ **Multi-Protocol Support** - Single broker, three protocols (MCP, A2A, ACP)  
🔐 **Security-First** - Ephemeral JWT tokens, AES-256 encryption, <5 min TTL  
📊 **Full Observability** - 100% audit logging via 1Password Events API  
🚀 **Ecosystem Ready** - Compatible with CrewAI, LangChain, Claude, and more  
🎨 **Interactive UI** - Real-time dashboard for protocol visualization (optional)

---

## 📚 Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[TODO.md](TODO.md)** | Comprehensive task list (100+ tasks, 8 phases) | Implementation - follow step-by-step |
| **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** | Quick reference, progress tracking | Quick lookups, status updates |
| **[PROJECT_ROADMAP.md](PROJECT_ROADMAP.md)** | Visual roadmap, architecture, demo flow | Understanding architecture, planning |
| **[PLANNING_SUMMARY.md](PLANNING_SUMMARY.md)** | Coverage verification, certification | Validation that nothing is missed |
| **[PRD-ver-1.0.md](PRD-ver-1.0.md)** | Product requirements document | Understanding requirements |
| **[poc.md](poc.md)** | Proof-of-concept technical details | Implementation reference |

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

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- 1Password Connect Server instance
- 1Password Connect API token
- Docker & Docker Compose (optional)

### Installation

```bash
# 1. Clone the repository
cd /Users/aniruth/projects/1password-demo

# 2. Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
cd backend
poetry install

# 4. Configure environment
cp .env.example .env
# Edit .env with your 1Password credentials

# 5. Activate Poetry shell
poetry shell
```

### Running the Servers

```bash
# Quick start with helper scripts (recommended)
cd backend
./scripts/start-all.sh

# Check health
./scripts/health-check.sh

# Run demo
./scripts/demo.sh --iterations 10

# Start dashboard
./scripts/run_dashboard.sh

# Stop all services
./scripts/stop-all.sh
```

### Manual Server Start (Alternative)

```bash
# Terminal 1 - MCP Server
python src/mcp/run_mcp.py

# Terminal 2 - A2A Server
python src/a2a/run_a2a.py

# Terminal 3 - ACP Server
python src/acp/run_acp.py

# (Optional) Terminal 4 - UI Dashboard
streamlit run src/ui/dashboard.py
```

### Running with Docker

```bash
# Start all services with helper script
cd backend
./scripts/start-all.sh --docker --build

# Check Docker health
./scripts/health-check.sh --docker

# Stop Docker services
./scripts/stop-all.sh --docker
```

### Manual Docker (Alternative)

```bash
# Start all services
docker-compose up --build

# Check health
curl http://localhost:8000/health  # A2A
curl http://localhost:8001/health  # ACP
```

---

## 📖 Protocol Guide

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

## 🎯 Implementation Status

### Phase Completion

```
✅ Phase 0: Planning Complete (100%)
✅ Phase 1: Foundation & Core (100%)
✅ Phase 2: MCP Server (100%)
✅ Phase 3: A2A Server (100%)
✅ Phase 4: ACP Server (100%)
✅ Phase 5: Integration (100%)
✅ Phase 6: Demo UI (Optional) (100%)
□  Phase 7: Documentation & Testing (0%)
□  Phase 8: Final Validation (0%)
```

**Current Status:** 🏗️ Phase 6 Complete - Demo UI Operational, Starting Phase 7  
**Next Step:** Begin Phase 7, Task 7.1.1 (Documentation & Testing)  
**Estimated Time to MVP:** 1-2 hours

---

## 🔐 Security Features

- ✅ **Ephemeral Tokens:** Default 5-minute TTL, configurable
- ✅ **AES-256 Encryption:** Credential payloads encrypted in JWTs
- ✅ **Bearer Authentication:** All A2A/ACP endpoints protected
- ✅ **Zero Standing Privilege:** No credentials stored locally
- ✅ **Full Audit Trail:** 100% event logging to 1Password Events API
- ✅ **TLS/HTTPS:** Secure transport for all communications

---

## 📊 Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Protocol Coverage | 3/3 | 3/3 |
| Credential TTL | <5 min | ✅ |
| Event Logging | >99% | ✅ |
| Retrieval Latency | <500ms | ✅ |
| Token Generation | <100ms | ✅ |

---

## 🛠️ Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Core Framework** | FastAPI | 0.115+ |
| **MCP Protocol** | MCP Python SDK | Latest |
| **1Password Integration** | 1Password Connect SDK | Latest |
| **JWT Handling** | python-jose | Latest |
| **Encryption** | cryptography | Latest |
| **Async HTTP** | httpx | Latest |
| **UI (Option 1)** | Streamlit | Latest |
| **UI (Option 2)** | FastAPI + Tailwind CSS | Latest |
| **Container Runtime** | Docker Compose | Latest |

---

## 🎬 Demo Scenarios

### Scenario 1: MCP Integration
**Demo:** AI assistant fetches ephemeral database credentials  
**File:** `demos/mcp_demo.py`  
**Duration:** ~30 seconds  
**Highlights:** Tool discovery, token generation, expiry enforcement

### Scenario 2: A2A Collaboration
**Demo:** Data agent discovers and requests credentials from broker  
**File:** `demos/a2a_demo.py`  
**Duration:** ~45 seconds  
**Highlights:** Agent card discovery, task execution, audit logging

### Scenario 3: ACP Session
**Demo:** CrewAI agent acquires SSH keys via natural language  
**File:** `demos/acp_demo.py`  
**Duration:** ~30 seconds  
**Highlights:** Intent parsing, session tracking, structured response

---

## 📚 Learning Resources

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Agent2Agent Protocol (A2A)](https://a2aprotocol.ai)
- [Agent Communication Protocol (ACP)](https://agentcommunicationprotocol.dev)
- [1Password Connect API](https://developer.1password.com/docs/connect)
- [1Password Events API](https://developer.1password.com/docs/events-api)

---

## 🤝 Contributing

This is currently a proof-of-concept project for demonstration purposes. For the implementation:

1. Follow the task list in [TODO.md](TODO.md)
2. Update progress in [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)
3. Refer to [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for architecture context
4. Test after each phase using the validation checkpoints

---

## 📝 License

This project is for demonstration and educational purposes.

---

## 🎓 Project Structure

```
project-root/
├── README.md                          ← You are here
├── TODO.md                            ← Detailed task list (start here!)
├── IMPLEMENTATION_CHECKLIST.md        ← Quick reference & progress tracking
├── PROJECT_ROADMAP.md                 ← Visual roadmap & architecture
├── PLANNING_SUMMARY.md                ← Certification & coverage verification
├── PRD-ver-1.0.md                     ← Product requirements
├── poc.md                             ← Technical proof-of-concept
├── pyproject.toml                     ← Poetry dependencies
├── .env.example                       ← Environment template (to be created)
├── docker-compose.yml                 ← Docker orchestration (to be created)
├── src/                               ← Source code (to be created)
│   ├── core/                          ← Core components
│   ├── mcp/                           ← MCP server
│   ├── a2a/                           ← A2A server
│   ├── acp/                           ← ACP server
│   └── ui/                            ← Dashboard (optional)
├── demos/                             ← Demo scripts ✅
├── tests/                             ← Test suite ✅
├── scripts/                           ← Helper scripts ✅
└── docker/                            ← Dockerfiles ✅
```

---

## 🚦 Current Status

**Planning Phase:** ✅ **COMPLETE** (100%)  
**Implementation Phase:** 🏗️ **IN PROGRESS** (25% - Phase 2 Complete)  
**Estimated Completion:** 4-6 hours remaining

---

## 📞 Next Steps

1. ✅ **Review documentation** - Read TODO.md for detailed tasks
2. ✅ **Set up environment** - Install dependencies, configure 1Password
3. ✅ **Complete Phase 1** - Foundation & Core Infrastructure
4. ✅ **Complete Phase 2** - MCP Server Implementation
5. ⏭️ **Start Phase 3** - Begin A2A Server implementation (Task 3.1.1)

---

**Created:** October 23, 2025  
**Last Updated:** October 23, 2025  
**Status:** 🚀 Phase 6 Complete - Demo UI Operational

---

*For detailed implementation instructions, see [TODO.md](TODO.md)*

