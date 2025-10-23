"""
MCP Server Implementation
Provides credential retrieval tools for AI models and agents via the Model Context Protocol.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from ..core.audit_logger import AuditLogger
from ..core.credential_manager import CredentialManager, ResourceType

logger = logging.getLogger(__name__)


@asynccontextmanager
async def server_lifespan(_server: Server) -> AsyncIterator[dict[str, Any]]:
    """
    Manage server startup and shutdown lifecycle.
    
    Initializes shared resources (CredentialManager, AuditLogger) on startup
    and cleans them up on shutdown.
    """
    logger.info("MCP Server starting up - initializing resources...")
    
    # Initialize resources on startup
    credential_manager = CredentialManager()
    audit_logger = AuditLogger()
    
    try:
        # Verify connectivity to 1Password
        health = credential_manager.health_check()
        if health["status"] != "healthy":
            logger.warning(
                f"1Password Connect health check status: {health['status']}"
            )
            logger.warning(
                f"Components: {health.get('components', {})}"
            )
            # Allow server to start even if degraded (for development/testing)
            logger.info("MCP Server starting in degraded mode")
        else:
            logger.info("MCP Server resources initialized successfully")
            logger.info("1Password Connect: Connected")
        
        yield {
            "credential_manager": credential_manager,
            "audit_logger": audit_logger,
        }
    finally:
        # Clean up on shutdown
        logger.info("MCP Server shutting down - cleaning up resources...")


# Initialize the MCP server with lifespan management
server = Server("1password-credential-broker", lifespan=server_lifespan)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools for credential retrieval.
    
    Returns:
        List of Tool definitions with input/output schemas
    """
    logger.info("MCP: Handling list_tools request")
    
    return [
        types.Tool(
            name="get_credentials",
            description=(
                "Retrieve ephemeral credentials from 1Password vault. "
                "Returns a short-lived JWT token (default 5 minutes) containing "
                "encrypted credentials for the requested resource. "
                "Supports database, API, SSH, and generic credential types."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "enum": ["database", "api", "ssh", "generic"],
                        "description": "Type of credential resource to retrieve",
                    },
                    "resource_name": {
                        "type": "string",
                        "description": "Name/title of the credential item in 1Password vault",
                    },
                    "requesting_agent_id": {
                        "type": "string",
                        "description": "Unique identifier of the requesting agent (for audit logging)",
                    },
                    "ttl_minutes": {
                        "type": "integer",
                        "description": "Token time-to-live in minutes (default: 5, max: 15)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 15,
                    },
                },
                "required": ["resource_type", "resource_name", "requesting_agent_id"],
            },
        )
    ]


async def _handle_get_credentials(
    arguments: dict[str, Any],
    credential_manager: CredentialManager,
    audit_logger: AuditLogger,
) -> list[types.TextContent]:
    """
    Internal handler for get_credentials tool logic.
    
    Separated from the decorator to make testing easier.
    
    Args:
        arguments: Tool arguments from the client
        credential_manager: Credential manager instance
        audit_logger: Audit logger instance
        
    Returns:
        List of TextContent with the ephemeral token and metadata
    """
    
    # Extract arguments
    resource_type = arguments["resource_type"]
    resource_name = arguments["resource_name"]
    requesting_agent_id = arguments["requesting_agent_id"]
    ttl_minutes = arguments.get("ttl_minutes", 5)
    
    try:
        # Step 1: Fetch credentials from 1Password
        logger.info(
            f"MCP: Fetching credentials for {resource_type}/{resource_name} "
            f"(agent: {requesting_agent_id})"
        )
        credentials = credential_manager.fetch_credentials(
            resource_type=resource_type,
            resource_name=resource_name,
        )
        
        # Step 2: Generate ephemeral JWT token
        logger.info(
            f"MCP: Generating ephemeral token with TTL={ttl_minutes} minutes"
        )
        token_data = credential_manager.issue_ephemeral_token(
            credentials=credentials,
            agent_id=requesting_agent_id,
            resource_type=resource_type,
            resource_name=resource_name,
            ttl_minutes=ttl_minutes,
        )
        
        # Step 3: Log credential access to 1Password Events API
        logger.info("MCP: Logging credential access event")
        await audit_logger.log_credential_access(
            protocol="MCP",
            agent_id=requesting_agent_id,
            resource=f"{resource_type}/{resource_name}",
            outcome="success",
            metadata={
                "action": "credential_retrieval",
                "ttl_minutes": ttl_minutes,
                "expires_at": token_data["expires_at"],
            },
        )
        
        # Format response with clear structure
        response_text = (
            f"✅ Ephemeral credentials generated successfully\n\n"
            f"Resource: {resource_type}/{resource_name}\n"
            f"Token: {token_data['token'][:20]}...{token_data['token'][-20:]}\n"
            f"Expires in: {token_data['expires_in']} seconds ({ttl_minutes} minutes)\n"
            f"Issued at: {token_data['issued_at']}\n"
            f"Expires at: {token_data['expires_at']}\n\n"
            f"⚠️  This token is ephemeral and will expire automatically.\n"
            f"Use the token to authenticate to the {resource_type} resource."
        )
        
        logger.info(
            f"MCP: Successfully issued token for {resource_type}/{resource_name} "
            f"to agent {requesting_agent_id}"
        )
        
        return [
            types.TextContent(
                type="text",
                text=response_text,
            )
        ]
        
    except ValueError as e:
        # Handle validation errors (invalid resource type, not found, etc.)
        error_msg = f"❌ Validation error: {str(e)}"
        logger.warning(f"MCP: Validation error for {resource_type}/{resource_name}: {e}")
        
        # Log failed attempt
        await audit_logger.log_credential_access(
            protocol="MCP",
            agent_id=requesting_agent_id,
            resource=f"{resource_type}/{resource_name}",
            outcome="failure",
            metadata={"action": "credential_retrieval", "error": str(e)},
        )
        
        return [types.TextContent(type="text", text=error_msg)]
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"❌ Error retrieving credentials: {str(e)}"
        logger.error(
            f"MCP: Unexpected error for {resource_type}/{resource_name}: {e}",
            exc_info=True,
        )
        
        # Log failed attempt
        await audit_logger.log_credential_access(
            protocol="MCP",
            agent_id=requesting_agent_id,
            resource=f"{resource_type}/{resource_name}",
            outcome="error",
            metadata={"action": "credential_retrieval", "error": str(e)},
        )
        
        return [types.TextContent(type="text", text=error_msg)]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """
    Handle tool execution for credential retrieval.
    
    This is the decorator-registered handler that extracts context
    and delegates to the internal handler.
    
    Args:
        name: Tool name to execute
        arguments: Tool arguments from the client
        
    Returns:
        List of TextContent with the ephemeral token and metadata
        
    Raises:
        ValueError: If tool name is unknown or arguments are invalid
    """
    if name != "get_credentials":
        raise ValueError(f"Unknown tool: {name}")
    
    logger.info(f"MCP: Handling call_tool request for '{name}'")
    logger.debug(f"MCP: Tool arguments: {arguments}")
    
    # Access lifespan context
    ctx = server.request_context
    credential_manager: CredentialManager = ctx.lifespan_context["credential_manager"]
    audit_logger: AuditLogger = ctx.lifespan_context["audit_logger"]
    
    # Delegate to internal handler
    return await _handle_get_credentials(arguments, credential_manager, audit_logger)


async def run_mcp_server():
    """
    Run the MCP server with stdio transport.
    
    This is the main entry point for the MCP server. It uses stdio (standard input/output)
    for communication with MCP clients.
    """
    logger.info("Starting MCP Server on stdio transport...")
    
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("MCP Server stdio transport initialized")
            
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="1password-credential-broker",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"MCP Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Run the server
    asyncio.run(run_mcp_server())

