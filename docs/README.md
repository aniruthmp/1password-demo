# Universal 1Password Agent Credential Broker

**Multi-Protocol Credential Broker supporting MCP, A2A, and ACP**

[![Status](https://img.shields.io/badge/status-planning_complete-green)]()
[![Phase](https://img.shields.io/badge/phase-ready_for_implementation-blue)]()
[![Protocols](https://img.shields.io/badge/protocols-MCP%20%7C%20A2A%20%7C%20ACP-orange)]()

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
✅  Phase 1: Foundation & Core (100%)
□  Phase 2: MCP Server (0%)
□  Phase 3: A2A Server (0%)
□  Phase 4: ACP Server (0%)
□  Phase 5: Integration (0%)
□  Phase 6: Demo UI (Optional) (0%)
□  Phase 7: Documentation & Testing (0%)
□  Phase 8: Final Validation (0%)
```

**Current Status:** 🏗️ Phase 1 Complete - Foundation Ready, Starting Phase 2  
**Next Step:** Begin Phase 2, Task 2.1.1 (MCP Server Implementation)  
**Estimated Time to MVP:** 6-8 hours

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
| Protocol Coverage | 3/3 | 0/3 |
| Credential TTL | <5 min | N/A |
| Event Logging | >99% | N/A |
| Retrieval Latency | <500ms | N/A |
| Token Generation | <100ms | N/A |

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
├── demos/                             ← Demo scripts (to be created)
├── tests/                             ← Test suite (to be created)
└── docker/                            ← Dockerfiles (to be created)
```

---

## 🚦 Current Status

**Planning Phase:** ✅ **COMPLETE** (100%)  
**Implementation Phase:** 🏗️ **IN PROGRESS** (12.5% - Phase 1 Complete)  
**Estimated Completion:** 5-7 hours remaining

---

## 📞 Next Steps

1. ✅ **Review documentation** - Read TODO.md for detailed tasks
2. ✅ **Set up environment** - Install dependencies, configure 1Password
3. ✅ **Start Phase 1** - Begin with Task 1.1.1 (project structure)
4. ⏭️ **Start Phase 2** - Begin MCP Server implementation (Task 2.1.1)
5. ⏭️ **Track progress** - Update IMPLEMENTATION_CHECKLIST.md as you go

---

**Created:** October 23, 2025  
**Last Updated:** October 23, 2025  
**Status:** 🚀 Ready for Implementation

---

*For detailed implementation instructions, see [TODO.md](TODO.md)*

