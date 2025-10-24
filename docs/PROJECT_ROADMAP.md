# Universal 1Password Agent Credential Broker - Project Roadmap

**Version:** 1.0  
**Date:** October 23, 2025  
**Status:** ✅ Planning Complete - Ready for Implementation

---

## 🗺️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│          Universal 1Password Credential Broker                       │
│         (Multi-Protocol: MCP + A2A + ACP)                            │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │   MCP Server   │  │   A2A Server   │  │   ACP Server   │         │
│  │                │  │                │  │                │         │
│  │  JSON-RPC      │  │  Agent Card    │  │  RESTful API   │         │
│  │  Tool Calls    │  │  Task Exec     │  │  Sessions      │         │
│  │  Port: stdio   │  │  Port: 8000    │  │  Port: 8001    │         │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘         │
│          │                   │                    │                 │
│          └───────────────────┴────────────────────┘                 │
│                              │                                      │
│                              ▼                                      │
│                  ┌───────────────────────┐                          │
│                  │  Credential Manager   │                          │
│                  │  ┌─────────────────┐  │                          │
│                  │  │  Auth & AuthZ   │  │                          │
│                  │  │  Token Gen/Val  │  │                          │
│                  │  │  AES-256 Encrypt│  │                          │
│                  │  │  Audit Logging  │  │                          │
│                  │  └─────────────────┘  │                          │
│                  └──────────┬────────────┘                          │
│                             │                                       │
│                             ▼                                       │
│              ┌──────────────────────────────┐                       │
│              │  1Password Connect Client    │                       │
│              │  - Vault Access              │                       │
│              │  - Item Retrieval            │                       │
│              │  - Events API Logging        │                       │
│              └──────────────┬───────────────┘                       │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  1Password Vault │
                    │    + Events API  │
                    └──────────────────┘
```

---

## 🎯 Implementation Phases

### **Phase 1: Foundation (2-3 hours)** ✅
**Goal:** Build the core credential management engine

```
[Environment Setup] → [1Password Integration] → [JWT Engine] → [Audit Logger]
     (30 min)              (30 min)                (40 min)        (45 min)

Output: Working credential manager with token generation and logging
```

**Key Deliverables:**
- ✅ Project structure with dependencies
- ✅ OnePasswordClient for vault access
- ✅ TokenManager with AES-256 encryption
- ✅ CredentialManager orchestration layer
- ✅ AuditLogger with Events API integration

**Testing Checkpoint:** 
```python
# Can we retrieve a credential and generate a JWT?
token = credential_manager.issue_ephemeral_token(
    resource_type="database",
    resource_name="test-db",
    agent_id="test-agent",
    ttl=5
)
assert token is not None
assert jwt.decode(token)["exp"] - jwt.decode(token)["iat"] == 300  # 5 min
```

---

### **Phase 2: MCP Server (1-2 hours)** ✅
**Goal:** Enable AI models to request credentials as tools

```
[MCP SDK Setup] → [Tool Definition] → [Server Config] → [Demo Client]
    (5 min)          (30 min)           (20 min)         (20 min)

Output: AI-accessible credential retrieval tool
```

**Key Deliverables:**
- ✅ MCP Server with `get_credentials` tool
- ✅ list_tools endpoint for discovery
- ✅ JSON-RPC transport (stdio)
- ✅ Demo: AI assistant fetching DB credentials
- ✅ Testing and validation complete

**Testing Checkpoint:**
```python
# Can an AI model discover and call the tool?
tools = await mcp_client.list_tools()
assert "get_credentials" in [t.name for t in tools]

result = await mcp_client.call_tool(
    "get_credentials",
    resource_type="database",
    resource_name="prod-postgres",
    requesting_agent_id="assistant-001"
)
assert result["token"]
assert result["expires_in"] == 300
```

---

### **Phase 3: A2A Server (2-3 hours)** 🤝
**Goal:** Enable agent-to-agent credential collaboration

```
[FastAPI Setup] → [Agent Card] → [Task Execution] → [SSE Streaming] → [Demo]
   (20 min)        (40 min)        (60 min)           (30 min)        (25 min)

Output: Collaborative agent credential exchange
```

**Key Deliverables:**
- ✅ Agent Card discovery endpoint
- ✅ Task execution with capability routing
- ✅ SSE streaming for long operations
- ✅ Bearer token authentication
- ✅ Demo: Data agent requesting credentials

**Testing Checkpoint:**
```python
# Can agents discover and collaborate?
card = requests.get("http://localhost:8000/agent-card").json()
assert card["agent_id"] == "1password-credential-broker"
assert "request_database_credentials" in [c["name"] for c in card["capabilities"]]

response = requests.post("http://localhost:8000/task", json={
    "task_id": "task-123",
    "capability_name": "request_database_credentials",
    "parameters": {"database_name": "analytics-db"},
    "requesting_agent_id": "data-agent"
})
assert response.json()["status"] == "completed"
```

---

### **Phase 4: ACP Server (1-2 hours)** ✅
**Goal:** Framework-agnostic REST API with session management

```
[FastAPI Setup] → [Agent Listing] → [Run Endpoint] → [Intent Parser] → [Sessions] → [Demo]
   (15 min)         (15 min)         (35 min)         (20 min)         (40 min)    (20 min)

Output: REST API with natural language support
```

**Key Deliverables:**
- ✅ /agents discovery endpoint
- ✅ /run execution with natural language parsing
- ✅ Session tracking and history
- ✅ /sessions/{id} retrieval
- ✅ Demo: CrewAI agent with SSH credentials

**Testing Checkpoint:**
```python
# Can frameworks interact naturally?
agents = requests.get("http://localhost:8001/agents").json()
assert "credential-broker" in [a["name"] for a in agents["agents"]]

response = requests.post("http://localhost:8001/run", json={
    "agent_name": "credential-broker",
    "input": [{
        "parts": [{
            "content": "I need database credentials for production-db",
            "content_type": "text/plain"
        }]
    }]
})
result = response.json()
assert result["status"] == "completed"
assert result["session_id"]
```

---

### **Phase 5: Integration (1 hour)** ✅ **COMPLETE**
**Goal:** Unified deployment and observability ✅ **COMPLETE**

```
[Docker Config] → [Compose Setup] → [Logging] → [Metrics] → [Health Checks]
   (20 min)         (25 min)         (20 min)    (25 min)      (25 min)

Output: Production-ready deployment package
```

**Key Deliverables:**
- ✅ Dockerfiles for all services
- ✅ Docker Compose orchestration
- ✅ Centralized structured logging
- ✅ Metrics collection and exposure
- ✅ Health check endpoints

**Testing Checkpoint:**
```bash
# Can we deploy everything with one command?
docker-compose up --build

# Verify all services healthy
curl http://localhost:8000/health  # A2A
curl http://localhost:8001/health  # ACP

# Check metrics
curl http://localhost:8000/status
# Expected: {"active_tokens": 0, "total_requests": 0, "uptime": "...", ...}
```

---

### **Phase 6: Demo UI (1-3 hours)** ✅ **COMPLETE**
**Goal:** Interactive visualization for stakeholder demos ✅ **COMPLETE**

```
Option 1 (Streamlit - Priority):
[Setup] → [Metrics Dashboard] → [Protocol Testing] → [Event Stream]
 (10m)       (45 min)              (45 min)           (45 min)

Option 2 (FastAPI + Tailwind - If Time Permits):
[UI Server] → [HTML/CSS] → [WebSocket] → [JavaScript] → [Polish]
  (15m)       (40 min)     (35 min)      (35 min)       (25 min)

Output: Real-time protocol visualization dashboard
```

**Key Deliverables:**
- ✅ Live metrics (active tokens, requests, success rate)
- ✅ Protocol comparison charts (MCP vs A2A vs ACP)
- ✅ Interactive testing buttons
- ✅ Audit event stream
- ✅ Token display with countdown

**Testing Checkpoint:**
```bash
# Launch dashboard
streamlit run src/ui/dashboard.py
# Visit http://localhost:8501

# Click "Test MCP" button → See token generated
# Watch metrics update in real-time
# Observe audit events flowing
```

---

### **Phase 7: Documentation & Testing (1-2 hours)** 📝
**Goal:** Production-grade documentation and test coverage

```
[README] → [API Docs] → [Deployment Guide] → [Unit Tests] → [Integration Tests]
 (30 min)   (25 min)      (20 min)           (30 min)        (30 min)

Output: Comprehensive documentation and test suite
```

**Key Deliverables:**
- ✅ README with quick start
- ✅ API documentation for all endpoints
- ✅ Deployment guide (Docker + manual)
- ✅ Unit tests for core components
- ✅ Integration tests for end-to-end flows

---

### **Phase 8: Final Validation (30 min)** ✅
**Goal:** Verify all success criteria met

```
[E2E Testing] → [Performance Validation] → [Security Review] → [Demo Prep]
   (15 min)          (10 min)                 (35 min via       (15 min)
                                               Phase 7)

Output: Demo-ready, validated system
```

---

## 📊 Progress Tracking Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  MILESTONE TRACKER                                              │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Foundation Complete                          [Phase 1 Done]  │
│    └─ 1Password integration working                             │
│    └─ JWT tokens generating                                     │
│    └─ Audit logging active                                      │
│                                                                 │
│  ✅ MCP Protocol Operational                     [Phase 2 Done]  │
│    └─ Tool discoverable by AI models                            │
│    └─ Credentials retrievable via tool call                     │
│    └─ Demo scenario 1 working                                   │
│                                                                 │
│  ✅ A2A Protocol Operational                     [Phase 3 Done]  │
│    └─ Agent card published                                      │
│    └─ Agent-to-agent collaboration working                      │
│    └─ Demo scenario 2 working                                   │
│                                                                 │
│  ✅ ACP Protocol Operational                     [Phase 4 Done]  │
│    └─ REST endpoints responding                                 │
│    └─ Session management working                                │
│    └─ Demo scenario 3 working                                   │
│                                                                 │
│  ✅ Production Ready                             [Phase 5 Done]  │
│    └─ Docker Compose deployment working                         │
│    └─ All services healthy                                      │
│    └─ Logs and metrics collecting                               │
│                                                                 │
│  ✅ Demo UI Ready (Optional)                     [Phase 6 Done]  │
│    └─ Dashboard accessible                                      │
│    └─ Real-time updates working                                 │
│    └─ Protocol testing functional                               │
│                                                                 │
│  □ Documentation Complete                       [Phase 7 Done]  │
│    └─ README published                                          │
│    └─ Tests passing                                             │
│    └─ Deployment guide validated                                │
│                                                                 │
│  □ DEMO READY ✓                                 [Phase 8 Done]  │
│    └─ All 3 protocols demonstrate end-to-end                    │
│    └─ Performance targets met                                   │
│    └─ Security checklist complete                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Critical Success Metrics

### **Protocol Coverage**
```
✅ MCP Server: get_credentials tool operational
✅ A2A Server: Agent card + task execution
✅ ACP Server: /agents + /run + /sessions

Target: 3/3 protocols complete (100%)
```

### **Security**
```
✓ JWT TTL < 5 minutes enforced
✓ AES-256 credential encryption
✓ Bearer token authentication
✓ Zero plaintext credential storage

Target: All checks passing ✅
```

### **Performance**
```
✓ Credential retrieval < 500ms
✓ Token generation < 100ms
✓ Health checks responding

Target: All metrics within SLA ✅
```

### **Observability**
```
✓ 100% credential access logged
✓ Events API integration active
✓ Structured JSON logging
✓ Per-protocol metrics tracked

Target: >99% log delivery ✅
```

---

## 🚀 Quick Start Command Sequence

```bash
# 1. Clone and setup
cd /Users/aniruth/projects/1password-demo
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
cd backend
poetry install

# 2. Configure
cp .env.example .env
vim .env  # Add your 1Password credentials

# 3. Test foundation
python -c "from src.core.credential_manager import CredentialManager; print('✓ Foundation ready')"

# 4. Start services
python src/mcp/run_mcp.py &      # Terminal 1
python src/a2a/run_a2a.py &      # Terminal 2
python src/acp/run_acp.py &      # Terminal 3

# 5. Run demos
python demos/mcp_demo.py         # See MCP in action
python demos/a2a_demo.py         # See A2A in action
python demos/acp_demo.py         # See ACP in action

# 6. Launch dashboard (optional)
streamlit run src/ui/dashboard.py

# 7. Production deployment
docker-compose up --build
```

---

## 📋 Pre-Implementation Checklist

Before starting implementation, ensure:

### **Environment**
- [ ] Python 3.12+ installed
- [ ] Docker & Docker Compose available
- [ ] Code editor configured (VS Code recommended)
- [ ] Git initialized

### **1Password Setup**
- [ ] 1Password Connect server running
- [ ] Connect API token obtained
- [ ] Test vault created with sample credentials
- [ ] Events API access configured (optional)

### **Development Tools**
- [ ] Postman/Thunder Client for API testing
- [ ] Terminal multiplexer (tmux/screen) for multiple servers
- [ ] Web browser for dashboard testing

---

## 🎓 Learning Path

**For team members ramping up:**

1. **Day 1 - Protocols Understanding**
   - Read: MCP specification
   - Read: A2A protocol docs
   - Read: ACP protocol docs
   - Understand: When to use each

2. **Day 2 - 1Password Integration**
   - Review: Connect API docs
   - Practice: Vault operations
   - Learn: Events API logging

3. **Day 3 - Implementation**
   - Follow: TODO.md phases
   - Build: Core → MCP → A2A → ACP
   - Test: Each phase incrementally

---

## 🎬 Demo Presentation Flow

**For stakeholder presentations:**

### **Opening (2 min)**
- Problem: Agents need secure credential access
- Solution: Universal broker supporting 3 protocols
- Value: Unified security, audit, and ephemeral access

### **Technical Demo (10 min)**

**Demo 1: MCP (3 min)**
```
"Here's an AI assistant requesting database credentials as a tool call.
Notice the token expires in 5 minutes and everything is logged."

[Show: MCP client → tool call → token returned → audit log]
```

**Demo 2: A2A (3 min)**
```
"Here's two agents collaborating - a data agent discovers our
credential broker and requests access. No hardcoded secrets."

[Show: Agent card discovery → task submission → credential exchange]
```

**Demo 3: ACP (3 min)**
```
"Here's a framework making a natural language request. The system
parses intent and provisions credentials with session tracking."

[Show: Natural language input → parsing → credential issuance → session history]
```

**Dashboard (1 min)** [If implemented]
```
"This real-time dashboard shows all three protocols in action,
with live metrics and audit events streaming."

[Show: Protocol comparison chart → active tokens → event stream]
```

### **Closing (3 min)**
- Architecture benefits: Protocol-agnostic, unified security
- Business value: Future-proof agent ecosystem integration
- Next steps: Production hardening, scaling, additional protocols

---

## 🔮 Future Enhancements (Out of Scope for MVP)

### **Phase 9+** (Not in current plan)
- Confidential computing integration
- Hardware attestation (TPM/SGX)
- Token revocation API
- Multi-vault and multi-tenant support
- Browser runtime controls (PAM-in-the-browser)
- Horizontal scaling with Redis
- Production UI with authentication
- Role-based access control (RBAC)
- Kubernetes deployment manifests
- Terraform infrastructure-as-code

---

## ✅ Final Verification Checklist

Before considering project complete:

- [ ] All 8 phases marked complete
- [ ] All 3 demo scenarios pass end-to-end
- [ ] All security requirements verified
- [ ] All performance targets met
- [ ] Documentation reviewed and accurate
- [ ] Docker Compose deployment tested
- [ ] Code committed to Git with tags
- [ ] Demo presentation rehearsed
- [ ] Stakeholder feedback incorporated

---

**Project Status:** ✅ ROADMAP COMPLETE - PHASE 6 COMPLETE  
**Next Action:** Begin Phase 7, Task 7.1.1 (Documentation & Testing)  
**Estimated Completion:** 1-2 hours remaining  
**Success Probability:** High (comprehensive planning + clear execution path)

---

**Created:** October 23, 2025  
**Last Updated:** October 23, 2025  
**Maintained By:** Project Team  
**Questions?** See TODO.md for detailed task breakdown

