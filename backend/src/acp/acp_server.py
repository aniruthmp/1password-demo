"""
ACP (Agent Communication Protocol) Server Implementation

This module implements a RESTful API server that follows the Agent Communication Protocol (ACP)
specification for framework-agnostic agent communication with session management.

Key Features:
- Agent discovery via /agents endpoint
- Natural language credential requests via /run endpoint
- Session management and history tracking
- Intent parsing for credential requests
- Integration with core CredentialManager

Protocol: ACP (Agent Communication Protocol)
Transport: HTTP REST API
Port: 8001 (default)
"""

import asyncio
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from enum import Enum
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.credential_manager import CredentialManager
from src.core.audit_logger import AuditLogger
from src.core.logging_config import configure_logging

# Setup logging
configure_logging(log_level="INFO")
logger = logging.getLogger("acp-server")

# Global instances (initialized in lifespan)
credential_manager: Optional[CredentialManager] = None
audit_logger: Optional[AuditLogger] = None
session_manager: Optional["SessionManager"] = None


# ============================================================================
# Pydantic Models for ACP Protocol
# ============================================================================


class ContentType(str, Enum):
    """Supported content types for message parts."""

    TEXT_PLAIN = "text/plain"
    APPLICATION_JSON = "application/json"
    APPLICATION_JWT = "application/jwt"


class MessagePart(BaseModel):
    """A part of a message in ACP protocol."""

    content: str = Field(..., description="The content of the message part")
    content_type: str = Field(
        default="text/plain",
        description="MIME type of the content (e.g., text/plain, application/json)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "I need database credentials for production-db",
                    "content_type": "text/plain",
                }
            ]
        }
    }


class Message(BaseModel):
    """A message in ACP protocol (input or output)."""

    parts: list[MessagePart] = Field(..., description="List of message parts")
    role: Optional[str] = Field(
        default="user", description="Role of the message sender (user, assistant, system)"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "parts": [
                        {
                            "content": "I need database credentials for production-db",
                            "content_type": "text/plain",
                        }
                    ],
                    "role": "user",
                    "error": None,
                }
            ]
        }
    }


class ACPRunRequest(BaseModel):
    """Request body for /run endpoint."""

    agent_name: str = Field(..., description="Name of the agent to execute")
    input: list[Message] = Field(..., description="List of input messages")
    session_id: Optional[str] = Field(
        default=None, description="Optional session ID for continuing a session"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_name": "credential-broker",
                    "input": [
                        {
                            "parts": [
                                {
                                    "content": "I need database credentials for production-db",
                                    "content_type": "text/plain",
                                }
                            ],
                            "role": "user",
                        }
                    ],
                    "session_id": None,
                }
            ]
        }
    }


class RunStatus(str, Enum):
    """Status of a run execution."""

    COMPLETED = "completed"
    RUNNING = "running"
    ERROR = "error"
    FAILED = "failed"


class ACPRunResponse(BaseModel):
    """Response from /run endpoint."""

    run_id: str = Field(..., description="Unique identifier for this run")
    agent_name: str = Field(..., description="Name of the agent that executed")
    session_id: str = Field(..., description="Session ID for this interaction")
    status: RunStatus = Field(..., description="Status of the run execution")
    output: list[Message] = Field(..., description="Output messages from the agent")
    execution_time_ms: Optional[float] = Field(
        default=None, description="Execution time in milliseconds"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "run_id": "run-123e4567-e89b-12d3-a456-426614174000",
                    "agent_name": "credential-broker",
                    "session_id": "session-123e4567-e89b-12d3-a456-426614174000",
                    "status": "completed",
                    "output": [
                        {
                            "parts": [
                                {
                                    "content": "Generated ephemeral database credentials for production-db",
                                    "content_type": "text/plain",
                                }
                            ],
                            "role": "assistant",
                            "error": None,
                        }
                    ],
                    "execution_time_ms": 245.32,
                }
            ]
        }
    }


class AgentInfo(BaseModel):
    """Information about an available agent."""

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    capabilities: list[str] = Field(..., description="List of agent capabilities")
    version: str = Field(default="1.0.0", description="Agent version")


class AgentsResponse(BaseModel):
    """Response from /agents endpoint."""

    agents: list[AgentInfo] = Field(..., description="List of available agents")
    count: int = Field(..., description="Number of available agents")


class SessionInteraction(BaseModel):
    """A single interaction in a session."""

    timestamp: str = Field(..., description="ISO 8601 timestamp of the interaction")
    run_id: str = Field(..., description="Run ID for this interaction")
    input_summary: str = Field(..., description="Summary of the input")
    output_summary: str = Field(..., description="Summary of the output")
    status: RunStatus = Field(..., description="Status of the interaction")


class SessionHistory(BaseModel):
    """Session history response."""

    session_id: str = Field(..., description="Session identifier")
    created_at: str = Field(..., description="Session creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    interaction_count: int = Field(..., description="Number of interactions")
    interactions: list[SessionInteraction] = Field(..., description="List of interactions")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Current timestamp")


# ============================================================================
# Session Manager
# ============================================================================


class SessionManager:
    """Manages ACP sessions and interaction history."""

    def __init__(self):
        self.sessions: dict[str, dict[str, Any]] = {}
        self.session_lock = asyncio.Lock()
        logger.info("SessionManager initialized")

    async def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session or retrieve existing one."""
        if session_id and session_id in self.sessions:
            logger.debug(f"Using existing session: {session_id}")
            return session_id

        new_session_id = session_id or f"session-{uuid.uuid4()}"

        async with self.session_lock:
            self.sessions[new_session_id] = {
                "session_id": new_session_id,
                "created_at": datetime.now(UTC).isoformat(),
                "last_activity": datetime.now(UTC).isoformat(),
                "interactions": [],
            }

        logger.info(f"Created new session: {new_session_id}")
        return new_session_id

    async def add_interaction(
        self,
        session_id: str,
        run_id: str,
        input_messages: list[Message],
        output_messages: list[Message],
        status: RunStatus,
    ):
        """Add an interaction to a session."""
        # Ensure session exists first (without holding lock)
        if session_id not in self.sessions:
            await self.create_session(session_id)

        async with self.session_lock:
            # Extract summaries
            input_summary = self._extract_summary(input_messages)
            output_summary = self._extract_summary(output_messages)

            interaction = {
                "timestamp": datetime.now(UTC).isoformat(),
                "run_id": run_id,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "status": status.value,
            }

            self.sessions[session_id]["interactions"].append(interaction)
            self.sessions[session_id]["last_activity"] = datetime.now(UTC).isoformat()

        logger.debug(f"Added interaction to session {session_id}: {run_id}")

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session history."""
        async with self.session_lock:
            return self.sessions.get(session_id)

    def _extract_summary(self, messages: list[Message]) -> str:
        """Extract a summary from messages."""
        if not messages:
            return ""

        # Get first text part from first message
        for message in messages:
            for part in message.parts:
                if part.content_type == "text/plain" and part.content:
                    # Truncate to 100 chars
                    content = part.content.strip()
                    return content[:100] + "..." if len(content) > 100 else content

        return "No text content"

    async def expire_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        # TODO: Implement session expiration logic
        pass


# ============================================================================
# Intent Parser
# ============================================================================


class IntentParser:
    """Parse natural language requests to extract credential request intent."""

    # Regex patterns for credential types
    PATTERNS = {
        "database": [
            r"database\s+(?:credentials?|creds?|access)\s+for\s+(\S+)",
            r"db\s+(?:credentials?|creds?|access)\s+for\s+(\S+)",
            r"(?:credentials?|creds?|access)\s+for\s+(?:database|db)\s+(\S+)",
            r"need\s+(\S+)\s+database",
            r"(\S+)\s+database\s+(?:credentials?|creds?)",
        ],
        "api": [
            r"api\s+(?:credentials?|creds?|access|token)\s+for\s+(\S+)",
            r"(?:credentials?|creds?|access|token)\s+for\s+(?:api|API)\s+(\S+)",
            r"need\s+(\S+)\s+api",
            r"(\S+)\s+api\s+(?:credentials?|creds?|token)",
        ],
        "ssh": [
            r"ssh\s+(?:credentials?|creds?|key|keys?|access)\s+for\s+(\S+)",
            r"(?:credentials?|creds?|key|keys?|access)\s+for\s+(?:ssh|SSH)\s+(\S+)",
            r"need\s+(\S+)\s+ssh",
            r"(\S+)\s+ssh\s+(?:credentials?|creds?|key|keys?)",
        ],
    }

    @staticmethod
    def parse_intent(text: str) -> dict[str, Any]:
        """
        Parse natural language text to extract credential request intent.

        Returns:
            dict with keys: resource_type, resource_name, duration_minutes
        """
        text_lower = text.lower()

        # Extract resource type and name
        resource_type = None
        resource_name = None

        for res_type, patterns in IntentParser.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    resource_type = res_type
                    resource_name = match.group(1)
                    break
            if resource_type:
                break

        # Default to generic if no specific type found
        if not resource_type:
            resource_type = "generic"
            # Try to extract a name after common keywords
            generic_patterns = [
                r"credentials?\s+for\s+(\S+)",
                r"creds?\s+for\s+(\S+)",
                r"access\s+to\s+(\S+)",
                r"secret\s+for\s+(\S+)",
            ]
            for pattern in generic_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    resource_name = match.group(1)
                    break

        # Extract duration if specified
        duration_minutes = 5  # Default
        duration_match = re.search(
            r"(\d+)\s*(?:minute|min|minutes|mins)", text_lower, re.IGNORECASE
        )
        if duration_match:
            duration_minutes = int(duration_match.group(1))
            # Cap at 15 minutes
            duration_minutes = min(duration_minutes, 15)

        return {
            "resource_type": resource_type,
            "resource_name": resource_name,
            "duration_minutes": duration_minutes,
            "original_text": text,
        }


# ============================================================================
# FastAPI Application
# ============================================================================


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[dict[str, Any]]:
    """Manage application startup and shutdown lifecycle."""
    global credential_manager, audit_logger, session_manager

    logger.info("ACP Server starting up...")

    # Initialize components
    try:
        credential_manager = CredentialManager()
        audit_logger = AuditLogger()
        session_manager = SessionManager()

        logger.info("✅ Core components initialized successfully")

        # Health check
        health = credential_manager.health_check()
        if health["status"] != "healthy":
            logger.warning(f"⚠️  Health check warning: {health}")
        else:
            logger.info("✅ Health check passed")

    except Exception as e:
        logger.error(f"❌ Failed to initialize components: {e}")
        raise

    yield {
        "credential_manager": credential_manager,
        "audit_logger": audit_logger,
        "session_manager": session_manager,
    }

    # Cleanup on shutdown
    logger.info("ACP Server shutting down - cleaning up resources...")


# Initialize FastAPI app
app = FastAPI(
    title="1Password ACP Credential Broker",
    description="Agent Communication Protocol server for ephemeral credential provisioning",
    version="1.0.0",
    lifespan=app_lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service health status and basic information.
    """
    return HealthResponse(
        status="healthy",
        service="acp-server",
        version="1.0.0",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/agents", response_model=AgentsResponse)
async def list_agents():
    """
    ACP Discovery: List available agents.

    Returns information about agents available in this ACP server,
    including their capabilities and descriptions.
    """
    logger.info("Agent discovery request received")

    agents = [
        AgentInfo(
            name="credential-broker",
            description=(
                "Ephemeral credential provisioning from 1Password vaults. "
                "Provides just-in-time credentials with automatic expiration for "
                "databases, APIs, SSH, and generic secrets."
            ),
            capabilities=[
                "database_credentials",
                "api_credentials",
                "ssh_credentials",
                "generic_secrets",
                "natural_language_parsing",
                "session_management",
            ],
            version="1.0.0",
        )
    ]

    return AgentsResponse(agents=agents, count=len(agents))


@app.post("/run", response_model=ACPRunResponse)
async def run_agent(request: ACPRunRequest):
    """
    ACP Execution: Process credential request with session management.

    Accepts natural language or structured credential requests and provisions
    ephemeral credentials with automatic expiration.

    Supports:
    - Natural language parsing (e.g., "I need database credentials for prod-db")
    - Session tracking for conversation context
    - Multiple resource types (database, api, ssh, generic)
    - Configurable token TTL (1-15 minutes)
    """
    start_time = time.time()
    run_id = f"run-{uuid.uuid4()}"

    logger.info(f"Run request received - Agent: {request.agent_name}, Run ID: {run_id}")

    # Validate agent name
    if request.agent_name != "credential-broker":
        logger.warning(f"Unknown agent requested: {request.agent_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{request.agent_name}' not found. Available agents: credential-broker",
        )

    # Create or retrieve session
    session_id = await session_manager.create_session(request.session_id)

    try:
        # Extract user message
        if not request.input or not request.input[0].parts:
            raise ValueError("No input message provided")

        user_message = request.input[0].parts[0].content
        logger.debug(f"Processing user message: {user_message[:100]}...")

        # Parse intent
        intent = IntentParser.parse_intent(user_message)
        logger.info(f"Parsed intent: {intent}")

        if not intent["resource_name"]:
            # Could not parse - return error
            output_messages = [
                Message(
                    parts=[
                        MessagePart(
                            content=(
                                "I couldn't understand your credential request. "
                                "Please specify what credentials you need, for example:\n"
                                "- 'I need database credentials for prod-postgres'\n"
                                "- 'Get API credentials for stripe-api'\n"
                                "- 'Request SSH keys for production-server'\n"
                                "- 'Provide credentials for generic-secret-name'"
                            ),
                            content_type="text/plain",
                        )
                    ],
                    role="assistant",
                    error="Could not parse credential request",
                )
            ]

            # Log interaction
            await session_manager.add_interaction(
                session_id=session_id,
                run_id=run_id,
                input_messages=request.input,
                output_messages=output_messages,
                status=RunStatus.ERROR,
            )

            execution_time = (time.time() - start_time) * 1000

            return ACPRunResponse(
                run_id=run_id,
                agent_name=request.agent_name,
                session_id=session_id,
                status=RunStatus.ERROR,
                output=output_messages,
                execution_time_ms=execution_time,
            )

        # Fetch credentials and issue token
        token_data = credential_manager.fetch_and_issue_token(
            resource_type=intent["resource_type"],
            resource_name=intent["resource_name"],
            agent_id=session_id,
            ttl_minutes=intent["duration_minutes"],
        )

        # Log to audit trail
        await audit_logger.log_credential_access(
            protocol="ACP",
            agent_id=session_id,
            resource=f"{intent['resource_type']}/{intent['resource_name']}",
            outcome="success",
            metadata={
                "run_id": run_id,
                "ttl_minutes": intent["duration_minutes"],
                "expires_at": token_data["expires_at"],
            },
        )

        # Build success response
        response_text = (
            f"✅ Generated ephemeral {intent['resource_type']} credentials for {intent['resource_name']}.\n\n"
            f"Token expires in {intent['duration_minutes']} minutes ({token_data['expires_in']} seconds).\n"
            f"Issued at: {token_data['issued_at']}"
        )

        output_messages = [
            Message(
                parts=[
                    MessagePart(content=response_text, content_type="text/plain"),
                    MessagePart(
                        content=token_data["token"], content_type="application/jwt"
                    ),
                ],
                role="assistant",
                error=None,
            )
        ]

        # Log interaction
        await session_manager.add_interaction(
            session_id=session_id,
            run_id=run_id,
            input_messages=request.input,
            output_messages=output_messages,
            status=RunStatus.COMPLETED,
        )

        execution_time = (time.time() - start_time) * 1000

        logger.info(
            f"✅ Run completed successfully - Run ID: {run_id}, Execution time: {execution_time:.2f}ms"
        )

        return ACPRunResponse(
            run_id=run_id,
            agent_name=request.agent_name,
            session_id=session_id,
            status=RunStatus.COMPLETED,
            output=output_messages,
            execution_time_ms=execution_time,
        )

    except Exception as e:
        logger.error(f"❌ Run execution failed: {e}", exc_info=True)

        # Log to audit trail
        await audit_logger.log_credential_access(
            protocol="ACP",
            agent_id=session_id,
            resource=f"{intent.get('resource_type', 'unknown')}/{intent.get('resource_name', 'unknown')}",
            outcome="error",
            metadata={"run_id": run_id, "error": str(e)},
        )

        # Build error response
        output_messages = [
            Message(
                parts=[
                    MessagePart(
                        content=f"Failed to provision credentials: {str(e)}",
                        content_type="text/plain",
                    )
                ],
                role="assistant",
                error=str(e),
            )
        ]

        # Log interaction
        await session_manager.add_interaction(
            session_id=session_id,
            run_id=run_id,
            input_messages=request.input,
            output_messages=output_messages,
            status=RunStatus.FAILED,
        )

        execution_time = (time.time() - start_time) * 1000

        return ACPRunResponse(
            run_id=run_id,
            agent_name=request.agent_name,
            session_id=session_id,
            status=RunStatus.FAILED,
            output=output_messages,
            execution_time_ms=execution_time,
        )


@app.get("/sessions/{session_id}", response_model=SessionHistory)
async def get_session_history(session_id: str):
    """
    ACP Session Management: Retrieve session history.

    Returns the complete interaction history for a given session,
    including all credential requests and responses.
    """
    logger.info(f"Session history request for: {session_id}")

    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Convert to SessionHistory model
    interactions = [
        SessionInteraction(
            timestamp=interaction["timestamp"],
            run_id=interaction["run_id"],
            input_summary=interaction["input_summary"],
            output_summary=interaction["output_summary"],
            status=RunStatus(interaction["status"]),
        )
        for interaction in session["interactions"]
    ]

    return SessionHistory(
        session_id=session["session_id"],
        created_at=session["created_at"],
        last_activity=session["last_activity"],
        interaction_count=len(interactions),
        interactions=interactions,
    )


# ============================================================================
# Entry Point (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    port = int(os.getenv("ACP_PORT", "8001"))

    logger.info(f"Starting ACP server on port {port}")
    uvicorn.run(
        "acp_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )

