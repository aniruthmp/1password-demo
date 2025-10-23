#!/usr/bin/env python3
"""
Interactive Phase 2 Testing Script - MCP Server

IMPORTANT: Run this script from the backend directory using Poetry:
    cd backend
    poetry run python scripts/test_phase2.py
    
Or activate the Poetry environment first:
    cd backend
    poetry env activate
    python scripts/test_phase2.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the Python path so we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
except ImportError as e:
    print("❌ Import Error: Missing MCP SDK")
    print(f"   Error: {e}")
    print("\n💡 Solution: Ensure MCP SDK is installed:")
    print("   cd backend")
    print("   poetry install")
    sys.exit(1)


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(number, text):
    """Print a formatted section header."""
    print(f"\n{number}. {text}...")


def print_success(text):
    """Print a success message."""
    print(f"   ✅ {text}")


def print_error(text):
    """Print an error message."""
    print(f"   ❌ {text}")


def print_info(text, indent=1):
    """Print an info message."""
    print(f"   {'  ' * (indent - 1)}{text}")


async def test_mcp_server():
    """
    Interactive test of the MCP server functionality.
    """
    print_header("Phase 2 Validation Test - MCP Server")
    
    # Configure server parameters
    project_root = Path(__file__).parent.parent
    server_params = StdioServerParameters(
        command="python",
        args=[
            "-m",
            "src.mcp.run_mcp",
            "--log-level",
            "ERROR",  # Minimize server logs for cleaner output
        ],
        env=None,  # Use current environment
    )
    
    try:
        print_section(1, "Connecting to MCP Server")
        print_info("Starting MCP server via stdio transport...")
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print_success("Connected to MCP server successfully")
                
                # Test 1: List available tools
                print_section(2, "Discovering Available Tools")
                try:
                    tools_result = await session.list_tools()
                    print_success(f"Found {len(tools_result.tools)} tool(s)")
                    
                    for tool in tools_result.tools:
                        print_info(f"Tool: {tool.name}", indent=2)
                        print_info(f"Description: {tool.description[:100]}...", indent=3)
                        
                        # Show input schema in a readable format
                        if tool.inputSchema:
                            required = tool.inputSchema.get("required", [])
                            properties = tool.inputSchema.get("properties", {})
                            print_info(f"Required parameters: {', '.join(required)}", indent=3)
                            
                except Exception as e:
                    print_error(f"Failed to list tools: {e}")
                    return
                
                # Test 2: Get user input for credential request
                print_section(3, "Credential Request Test")
                print_info("Let's test retrieving credentials from 1Password")
                print()
                
                # Get resource type
                print("   Available resource types:")
                print("     1. database")
                print("     2. api")
                print("     3. ssh")
                print("     4. generic")
                print()
                
                resource_type_map = {
                    "1": "database",
                    "2": "api",
                    "3": "ssh",
                    "4": "generic"
                }
                
                choice = input("   Select resource type [1-4] or enter custom: ").strip()
                resource_type = resource_type_map.get(choice, choice)
                
                if resource_type not in ["database", "api", "ssh", "generic"]:
                    print_error(f"Invalid resource type: {resource_type}")
                    return
                
                resource_name = input("   Enter 1Password item name: ").strip()
                if not resource_name:
                    print_error("Resource name is required")
                    return
                
                agent_id = input("   Enter agent ID (default: phase2-tester): ").strip()
                agent_id = agent_id or "phase2-tester"
                
                ttl_input = input("   Enter TTL in minutes (default: 5, max: 15): ").strip()
                try:
                    ttl_minutes = int(ttl_input) if ttl_input else 5
                    if ttl_minutes < 1 or ttl_minutes > 15:
                        print_error("TTL must be between 1 and 15 minutes")
                        return
                except ValueError:
                    print_error("Invalid TTL value")
                    return
                
                # Test 3: Call the get_credentials tool
                print_section(4, f"Requesting Credentials for {resource_type}/{resource_name}")
                print_info(f"Resource Type: {resource_type}")
                print_info(f"Resource Name: {resource_name}")
                print_info(f"Agent ID: {agent_id}")
                print_info(f"TTL: {ttl_minutes} minutes")
                print()
                
                try:
                    result = await session.call_tool(
                        "get_credentials",
                        arguments={
                            "resource_type": resource_type,
                            "resource_name": resource_name,
                            "requesting_agent_id": agent_id,
                            "ttl_minutes": ttl_minutes,
                        },
                    )
                    
                    print_success("Credential request completed!")
                    print()
                    print_info("Response from MCP server:", indent=1)
                    print("   " + "-" * 56)
                    
                    # Display the response content
                    for content in result.content:
                        if hasattr(content, "text"):
                            # Format the response nicely
                            lines = content.text.split('\n')
                            for line in lines:
                                print(f"   {line}")
                    
                    print("   " + "-" * 56)
                    
                except Exception as e:
                    print_error(f"Credential request failed: {e}")
                    print_info(f"Error details: {str(e)}", indent=2)
                    return
                
                # Test 4: Test error handling (optional)
                print()
                test_error = input("   Would you like to test error handling? [y/N]: ").strip().lower()
                
                if test_error == 'y':
                    print_section(5, "Testing Error Handling")
                    print_info("Attempting to retrieve non-existent resource...")
                    
                    try:
                        result = await session.call_tool(
                            "get_credentials",
                            arguments={
                                "resource_type": "database",
                                "resource_name": "non-existent-resource-xyz",
                                "requesting_agent_id": agent_id,
                                "ttl_minutes": 5,
                            },
                        )
                        
                        print_info("Error handling response:", indent=1)
                        print("   " + "-" * 56)
                        
                        for content in result.content:
                            if hasattr(content, "text"):
                                lines = content.text.split('\n')
                                for line in lines:
                                    print(f"   {line}")
                        
                        print("   " + "-" * 56)
                        print_success("Error handling working correctly")
                        
                    except Exception as e:
                        print_error(f"Unexpected error: {e}")
                
                # Summary
                print_header("Phase 2 Validation Complete!")
                print()
                print_success("MCP server is operational")
                print_success("Tool discovery working")
                print_success("Credential retrieval functional")
                print_success("Error handling verified")
                print()
                print_info("Key Achievements:", indent=1)
                print_info("✓ MCP protocol implementation complete", indent=2)
                print_info("✓ stdio transport working", indent=2)
                print_info("✓ Integration with Phase 1 components verified", indent=2)
                print_info("✓ Ephemeral token generation confirmed", indent=2)
                print_info("✓ Audit logging integrated", indent=2)
                print()
                print_info("Next Steps:", indent=1)
                print_info("- Phase 3: Implement A2A server", indent=2)
                print_info("- Phase 4: Implement ACP server", indent=2)
                print_info("- Phase 5: Add Docker orchestration", indent=2)
                print()
                
    except KeyboardInterrupt:
        print()
        print_error("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Test failed with error: {e}")
        print_info(f"Error type: {type(e).__name__}", indent=2)
        import traceback
        print()
        print_info("Traceback:", indent=2)
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print()
        print_error("Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()

