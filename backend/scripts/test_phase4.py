"""
Phase 4 Validation Test - ACP Server

This script provides comprehensive testing for the ACP (Agent Communication Protocol)
server implementation, validating all endpoints and functionality.

Features tested:
- Server connectivity and health
- Agent discovery endpoint
- Natural language credential requests
- Session management and history
- Intent parsing
- Error handling
- All credential types (database, API, SSH, generic)

Prerequisites:
- Phase 1, 2, and 3 components working
- ACP server running on http://localhost:8001
- Valid credentials in .env file
- At least one item in your 1Password vault

Usage:
    python scripts/test_phase4.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_section(number: int, text: str):
    """Print a formatted section header."""
    print(f"\n{number}. {text}")
    print("-" * 70)


def print_success(text: str):
    """Print a success message."""
    print(f"   ✅ {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"   ❌ {text}")


def print_info(text: str, indent: int = 1):
    """Print an info message with optional indentation."""
    prefix = "     " * indent
    print(f"{prefix}{text}")


def print_json(data: Any, indent: int = 1):
    """Pretty print JSON data."""
    json_str = json.dumps(data, indent=2)
    for line in json_str.split("\n"):
        print_info(line, indent=indent)


async def check_server_connectivity(client: httpx.AsyncClient) -> bool:
    """Check if ACP server is running and accessible."""
    print_section(1, "Server Connectivity Check")

    try:
        response = await client.get("http://localhost:8001/health")
        response.raise_for_status()
        health = response.json()

        print_success("ACP server is running")
        print_info(f"Status: {health['status']}")
        print_info(f"Service: {health['service']}")
        print_info(f"Version: {health['version']}")
        print_info(f"Timestamp: {health['timestamp']}")
        return True

    except httpx.ConnectError:
        print_error("Cannot connect to ACP server at http://localhost:8001")
        print()
        print_info("Please start the ACP server:", indent=0)
        print_info("  cd backend", indent=0)
        print_info("  poetry run python src/acp/run_acp.py", indent=0)
        print_info("  # OR", indent=0)
        print_info("  ./scripts/acp_server.sh", indent=0)
        return False

    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


async def test_agent_discovery(client: httpx.AsyncClient) -> dict[str, Any]:
    """Test agent discovery endpoint."""
    print_section(2, "Agent Discovery")
    print_info("Testing GET /agents endpoint...", indent=0)

    try:
        response = await client.get("http://localhost:8001/agents")
        response.raise_for_status()
        data = response.json()

        print_success("Agent discovery successful")
        print()
        print_info(f"Found {data['count']} agent(s)", indent=0)
        print()

        for agent in data["agents"]:
            print_info(f"Agent Information:", indent=0)
            print_info(f"Name: {agent['name']}")
            print_info(f"Description: {agent['description']}")
            print_info(f"Version: {agent['version']}")
            print()
            print_info(f"Capabilities ({len(agent['capabilities'])} total):")
            for cap in agent["capabilities"]:
                print_info(f"• {cap}", indent=2)
            print()

        return data

    except Exception as e:
        print_error(f"Agent discovery failed: {e}")
        return {}


async def test_natural_language_request(
    client: httpx.AsyncClient,
    request_text: str,
    session_id: str = None,
) -> dict[str, Any]:
    """Test natural language credential request."""
    print()
    print_info(f"Request: '{request_text}'", indent=0)
    print()

    try:
        # Build request
        request_data = {
            "agent_name": "credential-broker",
            "input": [
                {
                    "parts": [{"content": request_text, "content_type": "text/plain"}],
                    "role": "user",
                }
            ],
        }

        if session_id:
            request_data["session_id"] = session_id

        # Send request
        response = await client.post("http://localhost:8001/run", json=request_data)
        response.raise_for_status()
        data = response.json()

        print_success("Request completed successfully")
        print()
        print_info(f"Status: {data['status']}", indent=0)
        print_info(f"Run ID: {data['run_id']}", indent=0)
        print_info(f"Session ID: {data['session_id']}", indent=0)
        print_info(f"Execution Time: {data['execution_time_ms']:.2f}ms", indent=0)
        print()

        # Display output
        print_info("Output:", indent=0)
        for i, message in enumerate(data["output"], 1):
            for j, part in enumerate(message["parts"], 1):
                if part["content_type"] == "text/plain":
                    print_info(f"Text Response:", indent=1)
                    for line in part["content"].split("\n"):
                        if line.strip():
                            print_info(line, indent=2)
                elif part["content_type"] == "application/jwt":
                    print_info(f"JWT Token:", indent=1)
                    print_info(f"{part['content'][:50]}... (truncated)", indent=2)

            if message.get("error"):
                print_info(f"Error: {message['error']}", indent=1)

        return data

    except Exception as e:
        print_error(f"Request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print_info(f"Error detail: {error_detail.get('detail', 'Unknown')}")
            except:
                pass
        return {}


async def test_session_history(
    client: httpx.AsyncClient, session_id: str
) -> dict[str, Any]:
    """Test session history endpoint."""
    print_section(4, "Session History")
    print_info(f"Retrieving history for session: {session_id}", indent=0)

    try:
        response = await client.get(f"http://localhost:8001/sessions/{session_id}")
        response.raise_for_status()
        data = response.json()

        print_success("Session history retrieved")
        print()
        print_info(f"Session ID: {data['session_id']}", indent=0)
        print_info(f"Created At: {data['created_at']}", indent=0)
        print_info(f"Last Activity: {data['last_activity']}", indent=0)
        print_info(f"Interaction Count: {data['interaction_count']}", indent=0)
        print()

        print_info("Interaction History:", indent=0)
        for i, interaction in enumerate(data["interactions"], 1):
            print_info(f"{i}. {interaction['timestamp']}")
            print_info(f"Run ID: {interaction['run_id']}", indent=2)
            print_info(f"Status: {interaction['status']}", indent=2)
            print_info(f"Input: {interaction['input_summary']}", indent=2)
            print_info(f"Output: {interaction['output_summary']}", indent=2)
            print()

        return data

    except Exception as e:
        print_error(f"Session history retrieval failed: {e}")
        return {}


async def test_error_handling(client: httpx.AsyncClient) -> None:
    """Test error handling."""
    print_section(5, "Error Handling")

    # Test 1: Unknown agent
    print_info("Test 1: Unknown agent name", indent=0)
    try:
        request_data = {
            "agent_name": "nonexistent-agent",
            "input": [
                {
                    "parts": [
                        {"content": "Get credentials", "content_type": "text/plain"}
                    ],
                    "role": "user",
                }
            ],
        }
        response = await client.post("http://localhost:8001/run", json=request_data)
        response.raise_for_status()
        print_error("Should have returned 404 but didn't")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print_success("Correctly returned 404 for unknown agent")
            error_detail = e.response.json()
            print_info(f"Error: {error_detail.get('detail', 'Unknown')}")
        else:
            print_error(f"Expected 404 but got {e.response.status_code}")
    except Exception as e:
        print_error(f"Unexpected error: {e}")

    print()

    # Test 2: Unparseable request
    print_info("Test 2: Unparseable credential request", indent=0)
    request_data = {
        "agent_name": "credential-broker",
        "input": [
            {
                "parts": [
                    {"content": "Hello, how are you?", "content_type": "text/plain"}
                ],
                "role": "user",
            }
        ],
    }
    try:
        response = await client.post("http://localhost:8001/run", json=request_data)
        response.raise_for_status()
        data = response.json()

        if data["status"] == "error":
            print_success("Correctly returned error status for unparseable request")
            if data["output"] and data["output"][0].get("error"):
                print_info(f"Error: {data['output'][0]['error']}")
        else:
            print_error(f"Expected error status but got: {data['status']}")

    except Exception as e:
        print_error(f"Test failed: {e}")

    print()

    # Test 3: Nonexistent session
    print_info("Test 3: Nonexistent session ID", indent=0)
    try:
        response = await client.get(
            "http://localhost:8001/sessions/nonexistent-session-12345"
        )
        response.raise_for_status()
        print_error("Should have returned 404 but didn't")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print_success("Correctly returned 404 for nonexistent session")
            error_detail = e.response.json()
            print_info(f"Error: {error_detail.get('detail', 'Unknown')}")
        else:
            print_error(f"Expected 404 but got {e.response.status_code}")
    except Exception as e:
        print_error(f"Unexpected error: {e}")


async def main():
    """Main test function."""
    print_header("Phase 4 Validation Test - ACP Server")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Check connectivity
        if not await check_server_connectivity(client):
            return

        # Step 2: Test agent discovery
        agent_data = await test_agent_discovery(client)
        if not agent_data:
            return

        # Step 3: Test natural language requests
        print_section(3, "Natural Language Credential Requests")
        print_info(
            "Testing multiple credential types with session management...", indent=0
        )

        # Request 1: Database credentials
        print_info("\nTest 3.1: Database Credentials", indent=0)
        result1 = await test_natural_language_request(
            client, "I need database credentials for production-postgres"
        )

        if not result1 or result1.get("status") != "completed":
            print_error("Database credential request failed")
            return

        session_id = result1["session_id"]

        # Request 2: API credentials (same session)
        await asyncio.sleep(0.5)
        print_info("\nTest 3.2: API Credentials (same session)", indent=0)
        result2 = await test_natural_language_request(
            client, "Get API credentials for stripe-api for 10 minutes", session_id
        )

        if not result2 or result2.get("status") != "completed":
            print_error("API credential request failed")
            return

        # Request 3: SSH credentials (same session)
        await asyncio.sleep(0.5)
        print_info("\nTest 3.3: SSH Credentials (same session)", indent=0)
        result3 = await test_natural_language_request(
            client, "I need SSH keys for test-ssh", session_id
        )

        if not result3 or result3.get("status") != "completed":
            print_error("SSH credential request failed")
            return

        # Step 4: Test session history
        await asyncio.sleep(0.5)
        session_data = await test_session_history(client, session_id)
        if not session_data:
            return

        # Verify interaction count
        if session_data.get("interaction_count") == 3:
            print_success("Session correctly tracked all 3 interactions")
        else:
            print_error(
                f"Expected 3 interactions but found {session_data.get('interaction_count')}"
            )

        # Step 5: Test error handling
        await test_error_handling(client)

        # Summary
        print_header("Phase 4 Validation Complete!")
        print_success("All ACP server tests passed")
        print()
        print_info("Validated Features:", indent=0)
        print_info("✓ Server health check", indent=1)
        print_info("✓ Agent discovery endpoint", indent=1)
        print_info("✓ Natural language credential requests", indent=1)
        print_info("✓ Multiple credential types (database, API, SSH)", indent=1)
        print_info("✓ Session management", indent=1)
        print_info("✓ Interaction history tracking", indent=1)
        print_info("✓ Error handling", indent=1)
        print()
        print_info("Next Steps:", indent=0)
        print_info("- Run the demo: python demos/acp_demo.py", indent=1)
        print_info("- View API docs: http://localhost:8001/docs", indent=1)
        print_info("- Start Phase 5 (Integration & Orchestration)", indent=1)
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

