## Enhanced POC #1: Multi-Protocol Credential Broker (MCP + A2A/ACP)

Excellent idea! You can absolutely extend POC #1 to demonstrate understanding of the entire agent communication ecosystem. Here's how to create a **unified credential broker that supports MCP, A2A, and ACP** protocols—this will showcase exceptional technical breadth and align perfectly with 1Password's focus on emerging communication protocols.

***

## **Extended Architecture: Universal Agent Credential Broker**

### **High-Level Design**

```
┌─────────────────────────────────────────────────────────┐
│        Universal 1Password Credential Broker            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │   MCP    │  │   A2A    │  │   ACP    │               │
│  │  Server  │  │  Server  │  │  Server  │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
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

***

## **Protocol Comparison & Integration Strategy**

### **Understanding the Protocols**[1][2][3][4]

| Protocol | Primary Use Case | Architecture | Best For |
|----------|-----------------|--------------|----------|
| **MCP** | Agent ↔ Tool/Data | Client-Server (JSON-RPC) | Providing context and tools to AI models[5][2] |
| **A2A** | Agent ↔ Agent | Peer-to-Peer (JSON-RPC over HTTP/SSE) | Multi-agent collaboration, task delegation[1][6][7] |
| **ACP** | Agent ↔ Agent/App | RESTful HTTP | Structured messaging, session management, framework interoperability[2][3][8] |

### **Key Insight from Research**[2][4][7]

The academic and industry consensus is clear:

**"MCP is about providing context to a model, while ACP/A2A are about communication between agents"**[2]

**Recommended pattern**: "Use MCP for tools and A2A/ACP for agents"[2][7][9]

**Phased adoption roadmap**: "MCP for tool access → ACP for structured messaging → A2A for collaborative task execution"[4]

***

## **Implementation Plan: Extended POC**

### **Core Capabilities**

Your unified broker will support three interaction patterns:

1. **MCP Mode**: AI model requests credentials as a "tool call"
2. **A2A Mode**: Agent-to-agent collaboration where one agent requests credentials on behalf of another
3. **ACP Mode**: Framework-agnostic RESTful agent communication with session management

### **Component Breakdown**

#### **1. MCP Server Component** (Agent → Tool Pattern)

**Use Case**: AI agent uses 1Password as a credential retrieval tool[5][10]

```python
# mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import asyncio

server = Server("1password-mcp-server")

@server.tool()
async def get_credentials(
    resource_type: str,  # "database", "api", "ssh"
    resource_name: str,
    requesting_agent_id: str,
    ttl_minutes: int = 5
) -> dict:
    """MCP tool for retrieving ephemeral credentials from 1Password"""
    
    # Fetch from 1Password Connect API
    credentials = await fetch_from_1password(resource_type, resource_name)
    
    # Generate ephemeral token
    ephemeral_token = generate_jwt_token(
        credentials, 
        agent_id=requesting_agent_id,
        ttl=ttl_minutes
    )
    
    # Audit log
    await log_credential_access("MCP", requesting_agent_id, resource_name)
    
    return {
        "token": ephemeral_token,
        "expires_in": ttl_minutes * 60,
        "resource": resource_name
    }

@server.list_tools()
async def list_available_tools():
    return [
        Tool(
            name="get_credentials",
            description="Retrieve ephemeral credentials from 1Password vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string"},
                    "resource_name": {"type": "string"},
                    "requesting_agent_id": {"type": "string"},
                    "ttl_minutes": {"type": "integer", "default": 5}
                }
            }
        )
    ]
```

***

#### **2. A2A Server Component** (Agent ↔ Agent Pattern)

**Use Case**: Collaborative agents where a database agent requests credentials from your 1Password agent[1][6][7]

```python
# a2a_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI()

# A2A Agent Card (Discovery)
AGENT_CARD = {
    "agent_id": "1password-credential-broker",
    "name": "1Password Ephemeral Credential Agent",
    "description": "Provides just-in-time ephemeral credentials from 1Password vaults",
    "version": "1.0.0",
    "capabilities": [
        {
            "name": "request_database_credentials",
            "description": "Request temporary database credentials",
            "input_schema": {
                "database_name": "string",
                "duration_minutes": "integer"
            }
        },
        {
            "name": "request_api_credentials",
            "description": "Request temporary API access tokens",
            "input_schema": {
                "api_name": "string",
                "scopes": "array"
            }
        }
    ],
    "communication_modes": ["text", "json"],
    "authentication": "bearer_token"
}

@app.get("/agent-card")
async def get_agent_card():
    """A2A Discovery: Return agent capabilities"""
    return AGENT_CARD

class A2ATaskRequest(BaseModel):
    task_id: str
    capability_name: str
    parameters: dict
    requesting_agent_id: str

@app.post("/task")
async def execute_task(request: A2ATaskRequest):
    """A2A Task Execution: Handle credential requests from other agents"""
    
    if request.capability_name == "request_database_credentials":
        db_name = request.parameters.get("database_name")
        duration = request.parameters.get("duration_minutes", 5)
        
        # Fetch from 1Password
        credentials = await fetch_from_1password("database", db_name)
        
        # Generate ephemeral token
        token = generate_jwt_token(
            credentials,
            agent_id=request.requesting_agent_id,
            ttl=duration
        )
        
        # Audit log
        await log_credential_access("A2A", request.requesting_agent_id, db_name)
        
        return {
            "task_id": request.task_id,
            "status": "completed",
            "result": {
                "ephemeral_token": token,
                "expires_in_seconds": duration * 60,
                "database": db_name
            }
        }
    
    raise HTTPException(status_code=400, detail="Unknown capability")

@app.post("/task/{task_id}/stream")
async def stream_task_updates(task_id: str):
    """A2A Streaming: For long-running credential provisioning"""
    # SSE implementation for real-time updates
    pass
```

***

#### **3. ACP Server Component** (Framework-Agnostic Pattern)

**Use Case**: RESTful agent communication with session management[2][3][8][11]

```python
# acp_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI()

class MessagePart(BaseModel):
    content: str
    content_type: str = "text/plain"

class Message(BaseModel):
    parts: List[MessagePart]
    role: Optional[str] = "user"

class ACPRunRequest(BaseModel):
    agent_name: str
    input: List[Message]
    session_id: Optional[str] = None

@app.get("/agents")
async def list_agents():
    """ACP Discovery: List available agents"""
    return {
        "agents": [
            {
                "name": "credential-broker",
                "description": "Ephemeral credential provisioning from 1Password",
                "capabilities": ["database_creds", "api_tokens", "ssh_keys"]
            }
        ]
    }

@app.post("/run")
async def run_agent(request: ACPRunRequest):
    """ACP Execution: Process credential request with session management"""
    
    # Parse request
    user_message = request.input[0].parts[0].content
    session_id = request.session_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    # Extract intent (simple parsing - would use LLM in production)
    if "database" in user_message.lower():
        # Extract database name
        db_name = extract_database_name(user_message)
        
        # Fetch credentials
        credentials = await fetch_from_1password("database", db_name)
        token = generate_jwt_token(credentials, agent_id=session_id, ttl=5)
        
        # Audit log
        await log_credential_access("ACP", session_id, db_name)
        
        response_content = f"Generated ephemeral database credentials for {db_name}. Token expires in 5 minutes."
        
        return {
            "run_id": run_id,
            "agent_name": request.agent_name,
            "session_id": session_id,
            "status": "completed",
            "output": [
                {
                    "parts": [
                        {
                            "content": response_content,
                            "content_type": "text/plain"
                        },
                        {
                            "content": token,
                            "content_type": "application/jwt"
                        }
                    ],
                    "error": None
                }
            ]
        }
    
    return {
        "run_id": run_id,
        "session_id": session_id,
        "status": "error",
        "output": [{"error": "Could not parse credential request"}]
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """ACP Session Management: Track credential access history"""
    # Return session history for audit
    pass
```

***

## **Unified Credential Manager (Shared Core)**

```python
# credential_manager.py
import requests
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any

class CredentialManager:
    def __init__(self, op_connect_url: str, op_token: str, events_api_url: str):
        self.op_connect_url = op_connect_url
        self.op_token = op_token
        self.events_api_url = events_api_url
        self.secret_key = "your-jwt-secret"
    
    async def fetch_from_1password(self, resource_type: str, resource_name: str) -> Dict[str, Any]:
        """Fetch credentials from 1Password Connect API"""
        response = requests.get(
            f"{self.op_connect_url}/v1/vaults/{VAULT_ID}/items",
            headers={"Authorization": f"Bearer {self.op_token}"},
            params={"filter": f"title eq '{resource_name}'"}
        )
        
        if response.status_code != 200:
            raise Exception("Failed to fetch credentials from 1Password")
        
        return response.json()
    
    def generate_jwt_token(self, credentials: dict, agent_id: str, ttl: int) -> str:
        """Generate ephemeral JWT token"""
        payload = {
            "sub": agent_id,
            "credentials": credentials,  # In production, encrypt this
            "exp": datetime.utcnow() + timedelta(minutes=ttl),
            "iat": datetime.utcnow(),
            "iss": "1password-credential-broker"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    async def log_credential_access(self, protocol: str, agent_id: str, resource: str):
        """Log to 1Password Events API for SIEM integration"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "protocol": protocol,
            "actor": agent_id,
            "action": "credential_access",
            "resource": resource,
            "outcome": "success"
        }
        
        requests.post(
            f"{self.events_api_url}/audit",
            headers={"Authorization": f"Bearer {EVENTS_TOKEN}"},
            json=event
        )
```

***

## **Demo Scenarios for Interview**

### **Scenario 1: MCP - AI Agent Tool Use**
"An AI coding assistant needs database credentials to run migrations"

```bash
# Client code
from mcp.client import Client

client = Client("1password-mcp-server")
result = await client.call_tool(
    "get_credentials",
    resource_type="database",
    resource_name="production-postgres",
    requesting_agent_id="coding-assistant-001"
)
print(f"Token: {result['token']}")
```

### **Scenario 2: A2A - Multi-Agent Collaboration**
"A data analysis agent collaborates with your credential broker to access a data warehouse"

```bash
# Data agent discovers 1Password agent
agent_card = requests.get("http://localhost:8000/agent-card").json()
print(f"Found agent: {agent_card['name']}")

# Request credentials via A2A
task_response = requests.post("http://localhost:8000/task", json={
    "task_id": "task-123",
    "capability_name": "request_database_credentials",
    "parameters": {"database_name": "analytics-db", "duration_minutes": 10},
    "requesting_agent_id": "data-analyst-agent"
})
```

### **Scenario 3: ACP - Framework-Agnostic Integration**
"A CrewAI agent wrapped in ACP server requests SSH credentials"

```bash
# ACP client call
acp_response = requests.post("http://localhost:8001/run", json={
    "agent_name": "credential-broker",
    "input": [{
        "parts": [{
            "content": "I need SSH credentials for production-server-01",
            "content_type": "text/plain"
        }],
        "role": "user"
    }],
    "session_id": "session-abc-123"
})
```

***

## **Extended Job Description Coverage**

### **Additional Coverage Beyond POC #1:**

✅ **Emerging communication protocols** (explicit in JD)  
- A2A protocol implementation[1][6][7]
- ACP protocol implementation[2][3][8]
- Multi-protocol architecture[4]

✅ **Integration strategy across ecosystem**  
- Agent-to-agent collaboration patterns[1][12]
- Framework interoperability (CrewAI, LangChain, etc.)[8][13]
- Cross-platform communication[2][14]

✅ **Reference architectures**  
- Protocol selection decision framework[4][15]
- Phased adoption roadmap[4]
- Unified credential management pattern

✅ **Scalability and security**  
- Protocol-agnostic authentication[1][3]
- Session management across protocols[8]
- Decentralized agent discovery[1][6]

✅ **Technical evangelism**  
- Understanding of cutting-edge protocols (released 2024-2025)[1][8][12]
- Ability to compare and contrast standards[2][4][16]
- Industry thought leadership awareness

***

## **Implementation Timeline**

**Total: 6-8 hours** (feasible for tonight)

- **Hour 1-2**: Core credential manager + 1Password Connect integration
- **Hour 3-4**: MCP server implementation (highest priority)
- **Hour 5-6**: A2A server with Agent Card discovery
- **Hour 7-8**: ACP RESTful endpoints + demo scripts

**Minimum viable demo** (if time is tight): Focus on MCP + A2A with shared credential manager. This covers the two most distinct patterns and shows protocol comparison understanding.

***

## **Why This Extended POC is Powerful**

**Demonstrates Protocol Expertise**: You understand that MCP, A2A, and ACP solve different problems and can articulate when to use each[2][4][7]

**Shows Architectural Thinking**: Rather than building siloed implementations, you created a unified system with a shared core—exactly what 1Password needs for their "Partner Ecosystem Solutions"

**Covers Emerging Standards**: A2A was just announced by Google in April 2025, ACP was recently moved to Linux Foundation[8][12]—showing you're tracking the latest developments

**Addresses JD Explicitly**: The job description mentions "emerging communication protocols (e.g., MCP, A2A, ACP, et al.)"—you've built all three!

**Real-World Applicability**: This architecture mirrors how 1Password would actually integrate with the agent ecosystem: supporting multiple protocols for maximum partner compatibility[7][17]

This extended POC positions you as someone who not only can prototype quickly but also thinks strategically about ecosystem integration—exactly what a Principal Developer role requires.

Sources
[1] A2A Protocol - Agent2Agent Communication https://a2aprotocol.ai
[2] MCP and ACP: Decoding the language of models and agents - Outshift https://outshift.cisco.com/blog/mcp-acp-decoding-language-of-models-and-agents
[3] MCP, A2A, ACP: What does it all mean? - Akka https://akka.io/blog/mcp-a2a-acp-what-does-it-all-mean
[4] [2505.02279] A survey of agent interoperability protocols - arXiv https://arxiv.org/abs/2505.02279
[5] What Is the Model Context Protocol (MCP) and How It Works https://www.descope.com/learn/post/mcp
[6] a2aproject/A2A: An open protocol enabling communication ... - GitHub https://github.com/a2aproject/A2A
[7] Open Protocols for Agent Interoperability Part 4 - AWS https://aws.amazon.com/blogs/opensource/open-protocols-for-agent-interoperability-part-4-inter-agent-communication-on-a2a/
[8] i-am-bee/acp: Open protocol for communication between AI agents ... https://github.com/i-am-bee/acp
[9] Getting Started with Agent2Agent (A2A) Protocol: A Purchasing ... https://codelabs.developers.google.com/intro-a2a-purchasing-concierge
[10] Model Context Protocol (MCP) :: Spring AI Reference https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.html
[11] Agent Communication Protocol: Welcome https://agentcommunicationprotocol.dev
[12] Announcing the Agent2Agent Protocol (A2A) https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
[13] ACP: Agent Communication Protocol - Andrew Ng - X https://x.com/AndrewYNg/status/1937907934094360582
[14] IBM's Agent Communication Protocol (ACP) - WorkOS https://workos.com/blog/ibm-agent-communication-protocol-acp
[15] MCP vs A2A: A Guide to AI Agent Communication Protocols - Auth0 https://auth0.com/blog/mcp-vs-a2a/
[16] Comparison of Agent Protocols MCP, ACP and A2A | Niklas Heidloff https://heidloff.net/article/mcp-acp-a2a-agent-protocols/
[17] AI Agent Ecosystem: A Guide to MCP, A2A, and Agent ... - Addepto https://addepto.com/blog/ai-agent-ecosystem-a-guide-to-mcp-a2a-and-agent-communication-protocols/
[18] Comparison of MCP and ANP: What Kind of Communication ... https://www.agent-network-protocol.com/blogs/posts/mcp-anp-comparison.html
[19] A2A Protocol (Agent2Agent) Explained: How AI Agents Collaborate https://www.youtube.com/watch?v=Tud9HLTk8hg
[20] MCP, ANP, Agora, agents.json, LMOS, and AITP https://agent-network-protocol.com/blogs/posts/agent-communication-protocols-comparison.html
[21] A2A Protocol https://a2a-protocol.org
[22] What is Agent Communication Protocol (ACP)? - IBM https://www.ibm.com/think/topics/agent-communication-protocol
