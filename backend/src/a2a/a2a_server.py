"""
A2A (Agent-to-Agent) Server Implementation

Implements the Agent2Agent communication protocol for agent-to-agent credential exchange.
Provides:
- Agent Card discovery endpoint
- Task execution with capability routing
- SSE streaming for long-running operations
- Bearer token authentication
"""

import asyncio
import logging
import os
import time
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..core.credential_manager import CredentialManager, ResourceType
from ..core.audit_logger import AuditLogger
from ..core.metrics import get_metrics_collector, MetricsTimer
from ..core.logging_config import configure_logging

# Configure centralized logging
configure_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="1Password A2A Credential Broker",
    description="Agent-to-Agent credential provisioning service",
    version="1.0.0",
)

# Configure CORS for agent-to-agent communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components lazily to avoid import-time errors
credential_manager: Optional[CredentialManager] = None
audit_logger: Optional[AuditLogger] = None


def get_credential_manager() -> CredentialManager:
    """Get or initialize the credential manager."""
    global credential_manager
    if credential_manager is None:
        credential_manager = CredentialManager()
    return credential_manager


def get_audit_logger() -> AuditLogger:
    """Get or initialize the audit logger."""
    global audit_logger
    if audit_logger is None:
        audit_logger = AuditLogger()
    return audit_logger

# Bearer token for authentication (in production, use proper auth)
BEARER_TOKEN = os.getenv("A2A_BEARER_TOKEN", "dev-token-change-in-production")


# ============================================================================
# Data Models
# ============================================================================


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CapabilityInput(BaseModel):
    """Input schema for a capability."""

    name: str
    type: str
    description: str
    required: bool = True


class Capability(BaseModel):
    """Agent capability definition."""

    name: str
    description: str
    input_schema: list[CapabilityInput]
    output_schema: dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """A2A Agent Card for discovery."""

    agent_id: str
    name: str
    description: str
    version: str
    capabilities: list[Capability]
    communication_modes: list[str]
    authentication: str


class A2ATaskRequest(BaseModel):
    """A2A task execution request."""

    task_id: str
    capability_name: str
    parameters: dict[str, Any]
    requesting_agent_id: str


class A2ATaskResponse(BaseModel):
    """A2A task execution response."""

    task_id: str
    status: TaskStatus
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


# ============================================================================
# Agent Card Definition
# ============================================================================

AGENT_CARD = AgentCard(
    agent_id="1password-credential-broker",
    name="1Password Ephemeral Credential Agent",
    description=(
        "Provides just-in-time ephemeral credentials from 1Password vaults. "
        "Supports multiple resource types (database, API, SSH, generic) with "
        "configurable TTL and automatic audit logging."
    ),
    version="1.0.0",
    capabilities=[
        Capability(
            name="request_database_credentials",
            description="Request temporary database credentials with configurable TTL",
            input_schema=[
                CapabilityInput(
                    name="database_name",
                    type="string",
                    description="Name of the database resource in 1Password",
                    required=True,
                ),
                CapabilityInput(
                    name="duration_minutes",
                    type="integer",
                    description="Token duration in minutes (1-15, default: 5)",
                    required=False,
                ),
            ],
            output_schema={
                "ephemeral_token": "string (JWT)",
                "expires_in_seconds": "integer",
                "database": "string",
                "issued_at": "string (ISO 8601)",
            },
        ),
        Capability(
            name="request_api_credentials",
            description="Request temporary API access tokens",
            input_schema=[
                CapabilityInput(
                    name="api_name",
                    type="string",
                    description="Name of the API resource in 1Password",
                    required=True,
                ),
                CapabilityInput(
                    name="scopes",
                    type="array",
                    description="Optional API scopes",
                    required=False,
                ),
                CapabilityInput(
                    name="duration_minutes",
                    type="integer",
                    description="Token duration in minutes (1-15, default: 5)",
                    required=False,
                ),
            ],
            output_schema={
                "ephemeral_token": "string (JWT)",
                "expires_in_seconds": "integer",
                "api": "string",
                "issued_at": "string (ISO 8601)",
            },
        ),
        Capability(
            name="request_ssh_credentials",
            description="Request temporary SSH credentials",
            input_schema=[
                CapabilityInput(
                    name="ssh_resource_name",
                    type="string",
                    description="Name of the SSH resource in 1Password",
                    required=True,
                ),
                CapabilityInput(
                    name="duration_minutes",
                    type="integer",
                    description="Token duration in minutes (1-15, default: 5)",
                    required=False,
                ),
            ],
            output_schema={
                "ephemeral_token": "string (JWT)",
                "expires_in_seconds": "integer",
                "ssh_resource": "string",
                "issued_at": "string (ISO 8601)",
            },
        ),
        Capability(
            name="request_generic_secret",
            description="Request any generic secret from 1Password",
            input_schema=[
                CapabilityInput(
                    name="secret_name",
                    type="string",
                    description="Name of the secret in 1Password",
                    required=True,
                ),
                CapabilityInput(
                    name="duration_minutes",
                    type="integer",
                    description="Token duration in minutes (1-15, default: 5)",
                    required=False,
                ),
            ],
            output_schema={
                "ephemeral_token": "string (JWT)",
                "expires_in_seconds": "integer",
                "secret": "string",
                "issued_at": "string (ISO 8601)",
            },
        ),
    ],
    communication_modes=["text", "json"],
    authentication="bearer_token",
)


# ============================================================================
# Authentication
# ============================================================================


async def verify_bearer_token(authorization: str = Header(None)) -> str:
    """
    Verify bearer token authentication.

    Args:
        authorization: Authorization header

    Returns:
        Agent ID extracted from token or header

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")

        # In production, validate the token properly
        # For now, just verify it matches our expected token
        if token != BEARER_TOKEN:
            raise ValueError("Invalid token")

        # Return agent ID (in production, extract from JWT)
        return "authenticated-agent"

    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# Capability Handlers
# ============================================================================


async def handle_database_credentials(
    parameters: dict[str, Any],
    requesting_agent_id: str,
) -> dict[str, Any]:
    """
    Handle request_database_credentials capability.

    Args:
        parameters: Capability parameters
        requesting_agent_id: Requesting agent ID

    Returns:
        Credential response with ephemeral token
    """
    database_name = parameters.get("database_name")
    duration_minutes = parameters.get("duration_minutes", 5)

    if not database_name:
        raise ValueError("database_name is required")

    # Validate TTL
    if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 15:
        raise ValueError("duration_minutes must be between 1 and 15")

    # Fetch credentials and issue token
    token_data = get_credential_manager().fetch_and_issue_token(
        resource_type=ResourceType.DATABASE.value,
        resource_name=database_name,
        agent_id=requesting_agent_id,
        ttl_minutes=duration_minutes,
    )

    # Log to audit trail
    await get_audit_logger().log_credential_access(
        protocol="A2A",
        agent_id=requesting_agent_id,
        resource=f"database/{database_name}",
        outcome="success",
    )

    return {
        "ephemeral_token": token_data["token"],
        "expires_in_seconds": token_data["expires_in"],
        "database": database_name,
        "issued_at": datetime.now(UTC).isoformat() + "Z",
    }


async def handle_api_credentials(
    parameters: dict[str, Any],
    requesting_agent_id: str,
) -> dict[str, Any]:
    """
    Handle request_api_credentials capability.

    Args:
        parameters: Capability parameters
        requesting_agent_id: Requesting agent ID

    Returns:
        Credential response with ephemeral token
    """
    api_name = parameters.get("api_name")
    duration_minutes = parameters.get("duration_minutes", 5)
    scopes = parameters.get("scopes", [])

    if not api_name:
        raise ValueError("api_name is required")

    # Validate TTL
    if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 15:
        raise ValueError("duration_minutes must be between 1 and 15")

    # Fetch credentials and issue token
    token_data = get_credential_manager().fetch_and_issue_token(
        resource_type=ResourceType.API.value,
        resource_name=api_name,
        agent_id=requesting_agent_id,
        ttl_minutes=duration_minutes,
    )

    # Log to audit trail
    await get_audit_logger().log_credential_access(
        protocol="A2A",
        agent_id=requesting_agent_id,
        resource=f"api/{api_name}",
        outcome="success",
        metadata={"scopes": scopes} if scopes else None,
    )

    return {
        "ephemeral_token": token_data["token"],
        "expires_in_seconds": token_data["expires_in"],
        "api": api_name,
        "issued_at": datetime.now(UTC).isoformat() + "Z",
        "scopes": scopes,
    }


async def handle_ssh_credentials(
    parameters: dict[str, Any],
    requesting_agent_id: str,
) -> dict[str, Any]:
    """
    Handle request_ssh_credentials capability.

    Args:
        parameters: Capability parameters
        requesting_agent_id: Requesting agent ID

    Returns:
        Credential response with ephemeral token
    """
    ssh_resource_name = parameters.get("ssh_resource_name")
    duration_minutes = parameters.get("duration_minutes", 5)

    if not ssh_resource_name:
        raise ValueError("ssh_resource_name is required")

    # Validate TTL
    if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 15:
        raise ValueError("duration_minutes must be between 1 and 15")

    # Fetch credentials and issue token
    token_data = get_credential_manager().fetch_and_issue_token(
        resource_type=ResourceType.SSH.value,
        resource_name=ssh_resource_name,
        agent_id=requesting_agent_id,
        ttl_minutes=duration_minutes,
    )

    # Log to audit trail
    await get_audit_logger().log_credential_access(
        protocol="A2A",
        agent_id=requesting_agent_id,
        resource=f"ssh/{ssh_resource_name}",
        outcome="success",
    )

    return {
        "ephemeral_token": token_data["token"],
        "expires_in_seconds": token_data["expires_in"],
        "ssh_resource": ssh_resource_name,
        "issued_at": datetime.now(UTC).isoformat() + "Z",
    }


async def handle_generic_secret(
    parameters: dict[str, Any],
    requesting_agent_id: str,
) -> dict[str, Any]:
    """
    Handle request_generic_secret capability.

    Args:
        parameters: Capability parameters
        requesting_agent_id: Requesting agent ID

    Returns:
        Credential response with ephemeral token
    """
    secret_name = parameters.get("secret_name")
    duration_minutes = parameters.get("duration_minutes", 5)

    if not secret_name:
        raise ValueError("secret_name is required")

    # Validate TTL
    if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 15:
        raise ValueError("duration_minutes must be between 1 and 15")

    # Fetch credentials and issue token
    token_data = get_credential_manager().fetch_and_issue_token(
        resource_type=ResourceType.GENERIC.value,
        resource_name=secret_name,
        agent_id=requesting_agent_id,
        ttl_minutes=duration_minutes,
    )

    # Log to audit trail
    await get_audit_logger().log_credential_access(
        protocol="A2A",
        agent_id=requesting_agent_id,
        resource=f"generic/{secret_name}",
        outcome="success",
    )

    return {
        "ephemeral_token": token_data["token"],
        "expires_in_seconds": token_data["expires_in"],
        "secret": secret_name,
        "issued_at": datetime.now(UTC).isoformat() + "Z",
    }


# Capability routing map
CAPABILITY_HANDLERS = {
    "request_database_credentials": handle_database_credentials,
    "request_api_credentials": handle_api_credentials,
    "request_ssh_credentials": handle_ssh_credentials,
    "request_generic_secret": handle_generic_secret,
}


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/agent-card", response_model=AgentCard)
async def get_agent_card():
    """
    A2A Discovery: Return agent capabilities.

    Returns:
        AgentCard with full capability definitions
    """
    logger.info("Agent card requested")
    return AGENT_CARD


@app.post("/task", response_model=A2ATaskResponse)
async def execute_task(
    request: A2ATaskRequest,
    agent_id: str = Depends(verify_bearer_token),
):
    """
    A2A Task Execution: Handle credential requests from other agents.

    Args:
        request: Task execution request
        agent_id: Authenticated agent ID

    Returns:
        Task execution response with credentials or error
    """
    start_time = time.time()
    resource_type = "unknown"

    # Determine resource type from capability name
    if "database" in request.capability_name:
        resource_type = "database"
    elif "api" in request.capability_name:
        resource_type = "api"
    elif "ssh" in request.capability_name:
        resource_type = "ssh"
    else:
        resource_type = "generic"

    logger.info(
        f"Task execution requested: task_id={request.task_id}, "
        f"capability={request.capability_name}, agent={request.requesting_agent_id}"
    )

    try:
        # Validate capability
        if request.capability_name not in CAPABILITY_HANDLERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown capability: {request.capability_name}",
            )

        # Execute capability handler
        handler = CAPABILITY_HANDLERS[request.capability_name]
        result = await handler(request.parameters, request.requesting_agent_id)

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Record success metrics
        metrics = get_metrics_collector()
        metrics.record_request("a2a", resource_type, True, execution_time)

        logger.info(
            f"Task completed successfully: task_id={request.task_id}, "
            f"execution_time={execution_time:.2f}ms"
        )

        return A2ATaskResponse(
            task_id=request.task_id,
            status=TaskStatus.COMPLETED,
            result=result,
            execution_time_ms=execution_time,
        )

    except ValueError as e:
        execution_time = (time.time() - start_time) * 1000
        
        # Record failure metrics
        metrics = get_metrics_collector()
        metrics.record_request("a2a", resource_type, False, execution_time)
        
        logger.error(f"Task failed (validation error): task_id={request.task_id}, error={e}")

        # Log failed attempt
        await get_audit_logger().log_credential_access(
            protocol="A2A",
            agent_id=request.requesting_agent_id,
            resource=f"{request.capability_name}",
            outcome="failure",
            metadata={"error": str(e)},
        )

        return A2ATaskResponse(
            task_id=request.task_id,
            status=TaskStatus.FAILED,
            error=str(e),
            execution_time_ms=execution_time,
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Task failed (unexpected error): task_id={request.task_id}, error={e}")

        # Log failed attempt
        await get_audit_logger().log_credential_access(
            protocol="A2A",
            agent_id=request.requesting_agent_id,
            resource=f"{request.capability_name}",
            outcome="failure",
            metadata={"error": str(e)},
        )

        return A2ATaskResponse(
            task_id=request.task_id,
            status=TaskStatus.FAILED,
            error=f"Internal error: {str(e)}",
            execution_time_ms=execution_time,
        )


@app.post("/task/{task_id}/stream")
async def stream_task_updates(
    task_id: str,
    agent_id: str = Depends(verify_bearer_token),
):
    """
    A2A Streaming: Server-Sent Events for long-running credential provisioning.

    Args:
        task_id: Task identifier
        agent_id: Authenticated agent ID

    Returns:
        SSE stream with progress updates
    """
    logger.info(f"SSE stream requested for task_id={task_id}")

    async def event_generator():
        """Generate SSE events for task progress."""
        try:
            # Initial status
            yield f"data: {{'status': 'started', 'task_id': '{task_id}', 'timestamp': '{datetime.now(UTC).isoformat()}Z'}}\n\n"
            await asyncio.sleep(0.5)

            # Progress update
            yield f"data: {{'status': 'provisioning', 'task_id': '{task_id}', 'progress': 50, 'timestamp': '{datetime.now(UTC).isoformat()}Z'}}\n\n"
            await asyncio.sleep(0.5)

            # Completion
            yield f"data: {{'status': 'completed', 'task_id': '{task_id}', 'progress': 100, 'timestamp': '{datetime.now(UTC).isoformat()}Z'}}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task_id={task_id}")
            yield f"data: {{'status': 'cancelled', 'task_id': '{task_id}', 'timestamp': '{datetime.now(UTC).isoformat()}Z'}}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error for task_id={task_id}: {e}")
            yield f"data: {{'status': 'error', 'task_id': '{task_id}', 'error': '{str(e)}', 'timestamp': '{datetime.now(UTC).isoformat()}Z'}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status of A2A server and dependencies
    """
    try:
        # Check credential manager health
        cm_health = get_credential_manager().health_check()

        return {
            "status": "healthy",
            "service": "a2a-server",
            "version": "1.0.0",
            "components": {
                "credential_manager": cm_health,
                "audit_logger": {"status": "healthy"},
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "a2a-server",
            "error": str(e),
        }


@app.get("/status")
async def get_status():
    """
    Get server status and metrics.

    Returns:
        Server status with comprehensive metrics
    """
    metrics = get_metrics_collector()
    metrics_data = metrics.get_metrics_dict()
    
    return {
        "service": "a2a-server",
        "version": "1.0.0",
        "protocol": "A2A",
        "agent_card": {
            "agent_id": AGENT_CARD.agent_id,
            "capabilities_count": len(AGENT_CARD.capabilities),
        },
        **metrics_data,
    }


# ============================================================================
# Lifespan Events
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize server components on startup."""
    logger.info("A2A Server starting up...")
    logger.info(f"Agent ID: {AGENT_CARD.agent_id}")
    logger.info(f"Capabilities: {len(AGENT_CARD.capabilities)}")
    logger.info("A2A Server ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    logger.info("A2A Server shutting down...")

