Here’s the **final, merged PRD** — combining the attached “Multi-Protocol Credential Broker” document with the refined structure, conciseness, and clarity of the “lightweight PRD” draft. The result keeps the full technical completeness of your original while aligning with best practices for brevity and executive readability.

***

# Product Requirements Document (PRD)  
**Project Title:** Universal 1Password Agent Credential Broker (MCP + A2A + ACP)  
**Version:** 1.1  
**Author:** [Your Name]  
**Date:** October 23, 2025  
**Status:** Review Ready  
**Reviewers:** Architecture, Security, Partner Integrations  

***

## 1. Overview

### Vision  
Build a **universal 1Password credential broker** that integrates seamlessly with the **AI agent ecosystem** by supporting multiple communication protocols — **MCP**, **A2A**, and **ACP** — enabling secure, ephemeral credential exchange across agent frameworks.

### Problem  
As AI agents become autonomous and diverse, they require **secure, protocol-agnostic credential access**. Existing systems are:  
- Protocol-specific, limiting interoperability  
- Lacking ephemeral credential issuance  
- Incomplete in unified auditing across protocols  

### Solution  
Develop a **multi-protocol credential broker** that connects once to the 1Password vault, issues **short-lived JWT credentials**, and logs all activity through the **1Password Events API**, ensuring end-to-end visibility, interoperability, and security.

***

## 2. Goals & Objectives

| Goal | Description | KPI |
|------|--------------|-----|
| Multi-Protocol Support | Implement MCP, A2A, and ACP endpoints in unified architecture | 3/3 protocols fully functioning |
| Security-first Architecture | All credentials ephemeral, encrypted, and logged | <5 min TTL, 100% logged |
| Ecosystem Readiness | Enable agent frameworks (CrewAI, LangChain, etc.) to easily connect | Compatible demos running |
| Partner Blueprint | Reusable reference architecture for 1Password ecosystem | Architecture shared internally |

***

## 3. Target Users

**AI Developers** – Need flexible credential retrieval for AI tooling and pipelines.  
**Platform Engineers** – Require scalable agent credential control and observability.  
**Security Teams** – Demand visibility, auditing, and rotation of ephemeral access.

***

## 4. User Stories

**MCP (Agent → Tool):**  
_As an AI assistant, I want to fetch credentials through a tool call so I can run database operations securely._

**A2A (Agent ↔ Agent):**  
_As a data analysis agent, I want to request credentials from another agent to enable secure data collaboration._

**ACP (Agent ↔ App):**  
_As a CrewAI-based agent, I want to obtain SSH credentials via REST APIs to deploy workloads securely._

**Cross-Cutting:**  
_As a security engineer, I want every credential access logged per agent, protocol, and timestamp for compliance._

***

## 5. Functional Requirements

### 5.1 MCP Server Component
- **get_credentials** tool: returns expiring JWT token  
- **list_tools** endpoint: exposes credential retrieval schema  
- Supports async JSON-RPC transport for AI models

### 5.2 A2A Server Component
- **/agent-card** endpoint: exposes capabilities and auth modes  
- **/task** endpoint: handles peer credential exchange (e.g., database, API)  
- **SSE streaming** for long-running credential provisioning

### 5.3 ACP Server Component
- **/agents** endpoint: lists registered agents  
- **/run** endpoint: accepts natural language or structured requests  
- **/sessions/{id}** endpoint: retrieves session history

### 5.4 Core Credential Manager
- Integrates with **1Password Connect API** for vault secrets  
- Generates **JWT tokens (default TTL: 5 min)** with encryption  
- Logs all access via **1Password Events API**

***

## 6. Non-Functional Requirements

| Category | Key Requirements |
|-----------|------------------|
| **Security** | AES-256 token encryption, bearer authentication, zero standing privilege |
| **Performance** | <500ms retrieval latency, token creation <100ms |
| **Reliability** | Health endpoints, auto-retry with exponential backoff |
| **Observability** | Structured logs, per-protocol metrics, audit traceability |

***

## 7. Architecture

```
         ┌──────────────────────────────────────────────────┐
         │   Universal 1Password Credential Broker           │
         │  (MCP + A2A + ACP)                                │
         │                                                   │
         │  ┌──────┐ ┌──────┐ ┌──────┐                       │
         │  │ MCP  │ │ A2A  │ │ ACP  │                       │
         │  └──┬───┘ └──┬───┘ └──┬───┘                       │
         │      │        │        │                          │
         │      └────────┴────────┘                          │
         │            Credential Manager                     │
         │  (Auth, Token, Audit, Connect Integration)        │
         └────────────────┬──────────────────────────────────┘
                          │
                          ▼
                 1Password Vault + Events API
```

**Tech Stack**: Python (FastAPI, AsyncIO, PyJWT, Cryptography), Docker Compose  
**Infra**: AWS container/Lambda compatible  
**Protocols Supported**: MCP (Model Context), A2A (Agent-to-Agent), ACP (Agent Comm Protocol)

***

## 8. Protocol Overview

| Protocol | Type | Best Use | Architecture |
|----------|------|-----------|---------------|
| MCP | Agent → Tool | LLMs or AI apps requesting credentials as “tools” | JSON-RPC (Client–Server) |
| A2A | Agent ↔ Agent | Collaboration among agents | JSON-RPC over HTTP/SSE |
| ACP | Agent ↔ App | Framework interoperability | REST API with session context |

_Recommended pattern_: MCP for AI tools, A2A for agent collaboration, ACP for framework integrations.

***

## 9. Implementation Plan

| Phase | Duration | Deliverables |
|--------|-----------|--------------|
| **1. Foundation** | 2–3 hrs | Credential Manager + 1Password Connect Integration |
| **2. MCP Server** | 1–2 hrs | get_credentials Tool + Demo |
| **3. A2A Server** | 2–3 hrs | Agent Card + Task Execution |
| **4. ACP Server** | 1–2 hrs | RESTful Run + Session APIs |
| **5. Integrations** | 1 hr | Docker Compose setup, unified logging |
| **6. Demo UI (Optional)** | 1–3 hrs | Interactive dashboard for protocol testing & audit visualization |

**Total Time:** 7–11 hours (6–8 hours core + 1–3 hours UI)

***

## 10. Demo Scenarios

**Scenario 1:** *MCP integration* – AI assistant fetches ephemeral DB credentials.  
**Scenario 2:** *A2A collaboration* – data and credential agents coordinate securely.  
**Scenario 3:** *ACP session* – CrewAI agent acquires SSH keys via RESTful endpoint.  

Each demo highlights token expiry, access logs, and interoperability across protocols.

**Optional UI Enhancement:** Interactive dashboard visualizes all three scenarios in real-time, showing protocol switching, token generation, and audit event streaming for non-technical stakeholders.

***

## 10.5 Demo UI Components (Optional)

To enhance the technical demo experience, two UI implementation options are provided. **Option 1 will be prioritized** for rapid implementation, with Option 2 as a time-permitting enhancement.

### **Option 1: Streamlit Real-Time Dashboard** (1–2 hours)

**Purpose:** Lightweight, Python-native dashboard for visualizing live credential flows and audit events.

**Key Features:**
- Real-time protocol usage metrics (MCP, A2A, ACP request counts)
- Live credential request simulator with interactive buttons
- Token display with expiry countdown
- Audit event stream showing 1Password Events API integration
- Security metrics dashboard (active tokens, success rates, average TTL)

**Implementation Highlights:**
```python
# dashboard.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="1Password Credential Broker", layout="wide")
st.title("🔐 Universal 1Password Credential Broker")

# Real-time metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Active Tokens", "12", "+3")
with col2:
    st.metric("Total Requests", "247", "+18")
    
# Protocol usage visualization
protocol_data = pd.DataFrame({
    'Protocol': ['MCP', 'A2A', 'ACP'],
    'Requests': [45, 32, 23]
})
st.bar_chart(protocol_data.set_index('Protocol'))

# Interactive protocol testing
if st.button("Simulate MCP Request"):
    result = requests.post("http://localhost:8000/mcp/get_credentials", ...)
    st.success(f"✅ Token issued: {result['token'][:20]}...")
```

**Advantages:**
- Zero frontend expertise required
- Auto-refreshing with `st.rerun()`
- Professional appearance with minimal code
- Can embed live API calls directly
- Ideal for technical stakeholder demos

**Deployment:** `streamlit run dashboard.py` (single command)

---

### **Option 2: FastAPI + Tailwind WebSocket Dashboard** (2–3 hours)

**Purpose:** Polished, production-like UI with WebSocket real-time updates.

**Key Features:**
- Single-page application with Tailwind CSS styling
- WebSocket-based live activity feed (no polling)
- Interactive protocol testing buttons (MCP/A2A/ACP)
- Token display with syntax highlighting
- Responsive design for multi-device demos
- Audit log stream with color-coded status indicators

**Implementation Highlights:**
```python
# ui_server.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50">
        <div class="container mx-auto p-8">
            <h1 class="text-3xl font-bold">🔐 1Password Credential Broker</h1>
            
            <!-- Protocol Selector -->
            <div class="grid grid-cols-3 gap-4 mb-8">
                <button onclick="testProtocol('MCP')" 
                        class="bg-blue-500 text-white p-4 rounded">
                    Test MCP Protocol
                </button>
                <!-- A2A and ACP buttons -->
            </div>
            
            <!-- Live Activity Feed -->
            <div id="activity-feed" class="bg-white rounded-lg shadow p-6">
                <h2 class="text-xl font-semibold mb-4">Live Activity</h2>
                <div id="feed" class="space-y-2 font-mono text-sm"></div>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8080/ws');
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addActivityLog(data);
            };
            
            function testProtocol(protocol) {
                fetch(`/test/${protocol}`).then(r => r.json());
            }
        </script>
    </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        event = await get_latest_audit_event()
        await websocket.send_json(event)
```

**Advantages:**
- More polished, production-like appearance
- True real-time updates via WebSockets (no page refresh)
- Better for executive/non-technical stakeholder demos
- Demonstrates full-stack integration capability
- Embeddable in larger applications

**Deployment:** Integrated with FastAPI servers (single port)

---

### **UI Component Value Proposition**

Both UI options provide:
1. **Visual Impact:** Real-time token issuance and protocol switching
2. **Protocol Comparison:** Side-by-side MCP vs A2A vs ACP demonstration
3. **Audit Visibility:** Live 1Password Events API integration
4. **Executive Engagement:** Non-technical stakeholders can understand value
5. **Demo Differentiation:** Moves beyond CLI-only demonstrations

**Recommended Strategy:**  
Implement **Option 1 (Streamlit)** first for rapid functional demo, upgrade to **Option 2 (FastAPI)** if time permits for enhanced visual polish.

***

## 11. Metrics of Success

| Metric | Target |
|--------|---------|
| Protocol Coverage | 3/3 protocols implemented |
| Credential Expiry | <5 min TTL enforced 100% |
| Event Logging | >99% delivery to 1Password Events API |
| Demo Reliability | 100% runnable end-to-end |
| UI Demo (Optional) | Real-time protocol visualization operational |

***

## 12. Out of Scope  
- Confidential computing and hardware attestation  
- Token revocation API  
- Multi-vault and tenant logic  
- **Production-grade UI dashboarding** (authentication, role-based access, multi-tenancy)

**Demo-Only Component:**  
Lightweight UI dashboard (Streamlit or FastAPI+Tailwind) for visualizing protocol usage and audit logs during technical demonstrations. Not intended for production deployment.

**Future Enhancements:**  
Integrate confidential computing modules, browser runtime controls (PAM-in-the-browser), confidential session evaluation, and enterprise-grade UI with full authentication and authorization.

***

## 13. Key Dependencies  
- 1Password Connect + Events APIs  
- Python 3.12+ environment  
- Docker & FastAPI runtime  
- MCP/A2A/ACP SDK libraries  
- **UI Components (Optional):** Streamlit, Tailwind CSS (CDN), WebSocket support  

***

## 14. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|---------|-------------|-------------|
| API rate limits | High | Medium | Throttling + caching layer |
| Protocol spec drift | Medium | Low | Lock SDK versions, monitor upstreams |
| Credential leaks | High | Low | AES payload encryption + TTL enforcement |
| Event delivery failure | Medium | Medium | Retry + local queue for logs |

***

## 15. References

- [1Password Connect API](https://developer.1password.com/docs/connect)  
- [1Password Events API](https://developer.1password.com/docs/events-api)  
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)  
- [Agent2Agent (A2A)](https://a2aprotocol.ai)  
- [Agent Communication Protocol (ACP)](https://agentcommunicationprotocol.dev)

***

### Document Summary
This **final PRD** merges your full technical specification with a cleaner executive structure, mapping tightly to 1Password’s **Extended Access Management** and **Partner Ecosystem Solutions** goals. It is concise enough for presentation but retains all references, functional details, and measurable success criteria from your original long-form version.

Sources
[1] PRD.md https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/23663750/a1c9316c-0071-4373-889f-ac8d466998ca/PRD.md
