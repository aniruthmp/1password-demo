#!/usr/bin/env python3
"""
MCP Client Demo
Demonstrates how to interact with the 1Password Credential Broker MCP server.

This demo shows:
1. Connecting to the MCP server via stdio transport
2. Listing available tools
3. Calling the get_credentials tool
4. Handling the ephemeral token response
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_mcp_client():
    """
    Demonstrate MCP client interaction with the 1Password Credential Broker.
    """
    logger.info("=" * 60)
    logger.info("MCP Client Demo - 1Password Credential Broker")
    logger.info("=" * 60)
    
    # Configure server parameters for stdio transport
    # The server command runs the MCP server as a subprocess
    project_root = Path(__file__).parent.parent
    server_params = StdioServerParameters(
        command="python",
        args=[
            "-m",
            "src.mcp.run_mcp",
            "--log-level",
            "WARNING",  # Reduce server log noise
        ],
        env=None,  # Use current environment (includes .env variables)
    )
    
    try:
        logger.info("Connecting to MCP server via stdio transport...")
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                logger.info("✅ Connected to MCP server successfully\n")
                
                # Demo 1: List available tools
                logger.info("=" * 60)
                logger.info("Demo 1: Listing Available Tools")
                logger.info("=" * 60)
                
                tools_result = await session.list_tools()
                logger.info(f"Available tools: {len(tools_result.tools)}\n")
                
                for tool in tools_result.tools:
                    logger.info(f"Tool: {tool.name}")
                    logger.info(f"Description: {tool.description}")
                    logger.info(f"Input Schema: {json.dumps(tool.inputSchema, indent=2)}\n")
                
                # Demo 2: Request database credentials
                logger.info("=" * 60)
                logger.info("Demo 2: Requesting Database Credentials")
                logger.info("=" * 60)
                
                logger.info("Calling get_credentials tool...")
                logger.info("  Resource Type: database")
                logger.info("  Resource Name: test-database")
                logger.info("  Agent ID: mcp-demo-client")
                logger.info("  TTL: 5 minutes\n")
                
                try:
                    result = await session.call_tool(
                        "get_credentials",
                        arguments={
                            "resource_type": "database",
                            "resource_name": "test-database",
                            "requesting_agent_id": "mcp-demo-client",
                            "ttl_minutes": 5,
                        },
                    )
                    
                    logger.info("✅ Tool call succeeded!\n")
                    logger.info("Response:")
                    logger.info("-" * 60)
                    
                    # The result contains a list of content blocks
                    for content in result.content:
                        if hasattr(content, "text"):
                            logger.info(content.text)
                    
                    logger.info("-" * 60)
                    
                except Exception as e:
                    logger.error(f"❌ Tool call failed: {e}")
                
                # Demo 3: Request API credentials with different TTL
                logger.info("\n" + "=" * 60)
                logger.info("Demo 3: Requesting API Credentials (Custom TTL)")
                logger.info("=" * 60)
                
                logger.info("Calling get_credentials tool...")
                logger.info("  Resource Type: api")
                logger.info("  Resource Name: test-api")
                logger.info("  Agent ID: mcp-demo-client")
                logger.info("  TTL: 10 minutes\n")
                
                try:
                    result = await session.call_tool(
                        "get_credentials",
                        arguments={
                            "resource_type": "api",
                            "resource_name": "test-api",
                            "requesting_agent_id": "mcp-demo-client",
                            "ttl_minutes": 10,
                        },
                    )
                    
                    logger.info("✅ Tool call succeeded!\n")
                    logger.info("Response:")
                    logger.info("-" * 60)
                    
                    for content in result.content:
                        if hasattr(content, "text"):
                            logger.info(content.text)
                    
                    logger.info("-" * 60)
                    
                except Exception as e:
                    logger.error(f"❌ Tool call failed: {e}")
                
                # Demo 4: Error handling - Invalid resource type
                logger.info("\n" + "=" * 60)
                logger.info("Demo 4: Error Handling - Invalid Resource Type")
                logger.info("=" * 60)
                
                logger.info("Calling get_credentials tool with invalid resource type...")
                logger.info("  Resource Type: invalid_type (should fail)")
                logger.info("  Resource Name: test-resource")
                logger.info("  Agent ID: mcp-demo-client\n")
                
                try:
                    result = await session.call_tool(
                        "get_credentials",
                        arguments={
                            "resource_type": "invalid_type",
                            "resource_name": "test-resource",
                            "requesting_agent_id": "mcp-demo-client",
                            "ttl_minutes": 5,
                        },
                    )
                    
                    logger.info("Response:")
                    logger.info("-" * 60)
                    
                    for content in result.content:
                        if hasattr(content, "text"):
                            logger.info(content.text)
                    
                    logger.info("-" * 60)
                    
                except Exception as e:
                    logger.info(f"Expected validation error: {e}")
                
                logger.info("\n" + "=" * 60)
                logger.info("MCP Demo Complete!")
                logger.info("=" * 60)
                logger.info("\nKey Takeaways:")
                logger.info("✅ MCP server provides tool-based credential access")
                logger.info("✅ Ephemeral tokens are issued with configurable TTL")
                logger.info("✅ All access is logged to 1Password Events API")
                logger.info("✅ Error handling provides clear feedback")
                logger.info("\nNext Steps:")
                logger.info("- Integrate with AI models (Claude, GPT, etc.)")
                logger.info("- Use tokens to authenticate to target resources")
                logger.info("- Monitor audit logs in 1Password dashboard")
                
    except Exception as e:
        logger.error(f"Demo failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_mcp_client())

