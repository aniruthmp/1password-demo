# Product Requirements Document: Multi-Protocol Credential Broker

## 1. Product Overview

### Vision
Build a universal 1Password credential broker that seamlessly integrates with the emerging agent ecosystem by supporting multiple communication protocols (MCP, A2A, and ACP), enabling AI agents to securely access ephemeral credentials through their native protocol.

### Problem Statement
As AI agents become increasingly autonomous and diverse in their framework implementations, they need secure, protocol-agnostic access to credentials. Current solutions are either:
- Protocol-specific (limiting agent interoperability)
- Lack ephemeral credential generation
- Don't provide unified audit trails across different communication patterns

### Solution
A unified credential broker that speaks all three major agent communication protocols while maintaining a single, secure connection to 1Password vaults, with built-in ephemeral token generation and comprehensive audit logging.

---

## 2. Objectives

### Primary Goals
- **Demonstrate multi-protocol expertise**: Support MCP, A2A, and ACP in a single unified architecture
- **Maximize agent ecosystem compatibility**: Enable any agent, regardless of framework, to securely access credentials
- **Enhance security posture**: Generate ephemeral, short-lived credentials instead of sharing long-lived secrets
- **Provide visibility**: Comprehensive audit logging for all credential access across protocols

### Success Criteria
- All three protocol servers operational and responding to requests
- Successful credential retrieval from 1Password Connect API
- JWT-based ephemeral token generation with configurable TTL
- Audit events logged for all credential access
- Clear demo scenarios showing each protocol in action

---

## 3. Target Users

### Primary Personas

**1. AI Agent Developers**
- Need credentials for their agents to access external resources
- Want protocol flexibility to match their framework choice
- Require security best practices built-in

**2. Platform Engineers**
- Deploying agent infrastructures at scale
- Need centralized credential management
- Require audit trails for compliance

**3. Security Teams**
- Need visibility into agent credential access
- Want short-lived, just-in-time credentials
- Require integration with existing SIEM tools

---

## 4. User Stories

### MCP Protocol (Agent → Tool Pattern)
```
As an AI coding assistant,
I want to retrieve database credentials as a tool call,
So that I can run migrations without having credentials hardcoded.
```

### A2A Protocol (Agent ↔ Agent Pattern)
```
As a data analysis agent,
I want to discover and request credentials from a specialized credential agent,
So that I can access data warehouses through agent collaboration.
```

### ACP Protocol (Framework-Agnostic Pattern)
```
As a CrewAI-based agent,
I want to request SSH credentials through a RESTful interface,
So that I can deploy applications without framework-specific integrations.
```

### Cross-Cutting Concerns
```
As a security engineer,
I want all credential access logged with protocol, agent ID, and timestamp,
So that I can audit agent behavior and detect anomalies.
```

---

## 5. Functional Requirements

### 5.1 MCP Server Component

**FR-1.1**: Implement MCP JSON-RPC server supporting `get_credentials` tool call
- **Input**: `resource_type`, `resource_name`, `requesting_agent_id`, `ttl_minutes`
- **Output**: Ephemeral JWT token with expiration time

**FR-1.2**: Implement MCP tool discovery endpoint (`list_tools`)
- Return schema for available credential retrieval tools

**FR-1.3**: Support async communication pattern
- Non-blocking credential retrieval

### 5.2 A2A Server Component

**FR-2.1**: Implement Agent Card endpoint (`/agent-card`)
- Expose agent capabilities, authentication methods, and communication modes

**FR-2.2**: Implement task execution endpoint (`/task`)
- Support capabilities: `request_database_credentials`, `request_api_credentials`
- Handle peer-to-peer agent requests

**FR-2.3**: Support SSE streaming for long-running operations
- Stream status updates for credential provisioning

### 5.3 ACP Server Component

**FR-3.1**: Implement agent discovery endpoint (`/agents`)
- List available agents and their capabilities

**FR-3.2**: Implement run endpoint (`/run`)
- Accept natural language or structured credential requests
- Support session management via `session_id`

**FR-3.3**: Implement session tracking endpoint (`/sessions/{session_id}`)
- Return credential access history for a given session

### 5.4 Core Credential Manager

**FR-4.1**: 1Password Connect API integration
- Fetch credentials by resource type and name
- Support vault filtering

**FR-4.2**: Ephemeral token generation
- Generate JWT tokens with configurable TTL (default: 5 minutes)
- Include agent ID, credentials (encrypted), and expiration in payload

**FR-4.3**: Audit logging
- Log all credential access to 1Password Events API
- Include: timestamp, protocol, agent ID, resource name, outcome

---

## 6. Non-Functional Requirements

### 6.1 Security

**NFR-1.1**: All protocol endpoints must authenticate requests
- Bearer token authentication for API endpoints
- MCP transport-layer security

**NFR-1.2**: Credentials in JWT tokens must be encrypted
- Use strong encryption (AES-256) for credential payload

**NFR-1.3**: Minimum privilege access
- Each agent receives only requested credentials
- Token revocation capability

### 6.2 Performance

**NFR-2.1**: Credential retrieval latency < 500ms (p95)
**NFR-2.2**: Support concurrent requests across protocols
**NFR-2.3**: Token generation < 100ms

### 6.3 Reliability

**NFR-3.1**: Graceful error handling for 1Password API failures
**NFR-3.2**: Health check endpoints for all protocol servers
**NFR-3.3**: Retry logic with exponential backoff for external API calls

### 6.4 Observability

**NFR-4.1**: Structured logging for all operations
**NFR-4.2**: Metrics: requests per protocol, latency, error rates
**NFR-4.3**: Protocol-specific request tracing

---

## 7. Technical Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│        Universal 1Password Credential Broker            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   MCP    │  │   A2A    │  │   ACP    │              │
│  │  Server  │  │  Server  │  │  Server  │              │
│  │  :8080   │  │  :8000   │  │  :8001   │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │             │              │                    │
│       └─────────────┴──────────────┘                    │
│                     │                                   │
│          ┌──────────▼──────────┐                        │
│          │  Credential Manager │                        │
│          │  - Auth & Authz     │                        │
│          │  - Token Generation │                        │
│          │  - Audit Logging    │                        │
│          └──────────┬──────────┘                        │
│                     │                                   │
│          ┌──────────▼──────────┐                        │
│          │  1Password Connect  │                        │
│          │       API Client    │                        │
│          └─────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
            1Password Vault (Secrets)
```

### Technology Stack

**Backend Framework**
- FastAPI (A2A, ACP servers) - async-first, high performance
- MCP Python SDK (MCP server) - official protocol implementation

**Authentication & Security**
- PyJWT for token generation
- Cryptography library for payload encryption

**API Integration**
- Requests library for 1Password Connect API
- Async HTTP clients for concurrent requests

**Infrastructure**
- Docker Compose for multi-service orchestration
- Environment-based configuration

---

## 8. Protocol Comparison & Selection Guide

### When to Use Each Protocol

| Protocol | Use Case | Architecture | Best For |
|----------|----------|--------------|----------|
| **MCP** | Agent → Tool | Client-Server (JSON-RPC) | AI models requesting tools/context |
| **A2A** | Agent ↔ Agent | Peer-to-Peer (JSON-RPC/HTTP) | Multi-agent collaboration, task delegation |
| **ACP** | Agent ↔ Agent/App | RESTful HTTP | Framework interoperability, session management |

### Recommended Pattern
- **MCP** for tool access (credentials as a capability)
- **A2A** for agent-to-agent collaboration
- **ACP** for framework-agnostic integrations (CrewAI, LangChain, etc.)

---

## 9. Implementation Phases

### Phase 1: Foundation (2-3 hours)
- Core `CredentialManager` class
- 1Password Connect API integration
- JWT token generation with encryption
- Basic audit logging structure

**Deliverable**: Credential manager that can fetch from 1Password and generate ephemeral tokens

### Phase 2: MCP Implementation (1-2 hours)
- MCP server setup
- `get_credentials` tool implementation
- Tool discovery endpoint
- MCP client demo script

**Deliverable**: Working MCP server with demo scenario

### Phase 3: A2A Implementation (2-3 hours)
- A2A server setup
- Agent Card discovery endpoint
- Task execution endpoint for credential requests
- A2A client demo script

**Deliverable**: Working A2A server with agent-to-agent credential sharing

### Phase 4: ACP Implementation (1-2 hours)
- ACP server setup
- Agent discovery and run endpoints
- Session management
- ACP client demo script

**Deliverable**: Working ACP server with session-based credential access

### Phase 5: Integration & Polish (1 hour)
- Unified Docker Compose configuration
- Comprehensive README with all demo scenarios
- Health check endpoints
- Error handling improvements

**Total Estimated Time**: 6-8 hours

---

## 10. Demo Scenarios

### Scenario 1: MCP - AI Tool Integration
**Context**: AI coding assistant needs database credentials to run migrations

```python
# Client demonstrates tool-based credential access
result = await mcp_client.call_tool(
    "get_credentials",
    resource_type="database",
    resource_name="production-postgres",
    requesting_agent_id="coding-assistant-001"
)
```

**Expected Outcome**: Ephemeral JWT token returned, valid for 5 minutes

### Scenario 2: A2A - Agent Collaboration
**Context**: Data analysis agent discovers and collaborates with credential broker

```python
# Agent discovers capabilities
agent_card = requests.get("/agent-card").json()

# Agent requests credentials
task_response = requests.post("/task", json={
    "capability_name": "request_database_credentials",
    "parameters": {"database_name": "analytics-db"}
})
```

**Expected Outcome**: Task completed with ephemeral token, logged in audit trail

### Scenario 3: ACP - Framework Integration
**Context**: CrewAI agent requests SSH credentials through RESTful interface

```python
# Natural language request
acp_response = requests.post("/run", json={
    "agent_name": "credential-broker",
    "input": [{
        "parts": [{
            "content": "I need SSH credentials for production-server-01"
        }]
    }],
    "session_id": "session-abc-123"
})
```

**Expected Outcome**: Credentials returned with session tracking

---

## 11. Success Metrics

### Technical Metrics
- **Protocol Coverage**: 3/3 protocols implemented (MCP, A2A, ACP)
- **Response Time**: < 500ms for credential retrieval (p95)
- **Uptime**: 99%+ for all protocol servers
- **Token Validity**: 0% expired tokens used (enforcement)

### Security Metrics
- **Audit Coverage**: 100% of credential access logged
- **Token Lifetime**: < 5 minutes default TTL
- **Failed Auth Attempts**: Tracked and alerted

### Demonstration Metrics
- **Demo Success Rate**: 3/3 scenarios executable
- **Code Quality**: Linting passes, type hints present
- **Documentation**: All endpoints documented

---

## 12. Out of Scope (v1)

### Explicitly Not Included
- Production-grade token encryption (using simple JWT for demo)
- Rate limiting per agent
- Token revocation API
- Advanced credential rotation logic
- Multi-vault support
- GraphQL endpoints
- Webhook notifications
- UI dashboard for audit logs
- Multi-tenancy
- Advanced RBAC beyond agent ID

### Future Considerations
- Integration with additional protocols (ANP, LMOS, etc.)
- Agent marketplace integration
- Credential pre-fetching and caching
- Advanced analytics on agent behavior
- Support for hardware security modules (HSM)

---

## 13. Dependencies

### External Services
- **1Password Connect API**: Primary credential source
- **1Password Events API**: Audit logging destination

### Development Dependencies
- Python 3.12+
- MCP Python SDK
- FastAPI framework
- Docker & Docker Compose

### Configuration Requirements
- 1Password Connect URL
- 1Password Connect token
- 1Password Events API token
- Vault ID
- JWT secret key

---

## 14. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 1Password API rate limits | High | Medium | Implement caching layer, request throttling |
| Protocol spec changes | Medium | Low | Pin SDK versions, monitor spec repos |
| Token expiration handling | Medium | High | Clear error messages, auto-refresh logic |
| Concurrent request failures | High | Low | Implement circuit breaker pattern |
| Audit log delivery failure | Medium | Medium | Local buffering, retry queue |

---

## 15. References & Resources

### Protocol Specifications
- [MCP Protocol](https://modelcontextprotocol.io)
- [A2A Protocol](https://a2aprotocol.ai)
- [ACP Specification](https://agentcommunicationprotocol.dev)

### 1Password Documentation
- [1Password Connect API](https://developer.1password.com/docs/connect)
- [1Password Events API](https://developer.1password.com/docs/events-api)

### Industry Analysis
- "MCP and ACP: Decoding the language of models and agents" - Outshift/Cisco
- "A survey of agent interoperability protocols" - arXiv 2505.02279
- AWS Blog: "Open Protocols for Agent Interoperability"

---

## Document Control

**Version**: 1.0  
**Last Updated**: October 23, 2025  
**Status**: Draft  
**Owner**: Technical Implementation  
**Reviewers**: Architecture Team, Security Team

