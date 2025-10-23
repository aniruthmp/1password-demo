"""
ACP (Agent Communication Protocol) Demo

This demo showcases how to interact with the ACP credential broker server
using the Agent Communication Protocol for natural language credential requests
with session management.

Features demonstrated:
- Agent discovery via /agents endpoint
- Natural language credential requests via /run endpoint
- Session management and history tracking
- Multiple credential types (database, API, SSH)
- Token expiration and metadata

Prerequisites:
- ACP server running (python src/acp/run_acp.py)
- 1Password Connect configured
- Valid credentials in your 1Password vault

Usage:
    python demos/acp_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path

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


def print_section(text: str):
    """Print a formatted section header."""
    print("\n" + "-" * 70)
    print(f"  {text}")
    print("-" * 70 + "\n")


def print_success(text: str):
    """Print a success message."""
    print(f"✅ {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"❌ {text}")


def print_info(text: str, indent: int = 0):
    """Print an info message with optional indentation."""
    prefix = "  " * indent
    print(f"{prefix}{text}")


def print_json(data: dict, indent: int = 1):
    """Pretty print JSON data."""
    json_str = json.dumps(data, indent=2)
    for line in json_str.split("\n"):
        print_info(line, indent=indent)


async def demo_agent_discovery(client: httpx.AsyncClient, base_url: str):
    """Demonstrate agent discovery."""
    print_section("1. Agent Discovery")
    print_info("Discovering available agents via /agents endpoint...")

    try:
        response = await client.get(f"{base_url}/agents")
        response.raise_for_status()
        data = response.json()

        print_success(f"Found {data['count']} agent(s)")
        print()

        for agent in data["agents"]:
            print_info(f"Agent: {agent['name']}")
            print_info(f"Description: {agent['description']}", indent=1)
            print_info(f"Version: {agent['version']}", indent=1)
            print_info(f"Capabilities:", indent=1)
            for cap in agent["capabilities"]:
                print_info(f"- {cap}", indent=2)
            print()

        return True

    except httpx.HTTPError as e:
        print_error(f"Agent discovery failed: {e}")
        return False


async def demo_natural_language_request(
    client: httpx.AsyncClient,
    base_url: str,
    request_text: str,
    session_id: str = None,
):
    """Demonstrate natural language credential request."""
    print_section(f"Natural Language Request: '{request_text}'")

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
            print_info(f"Using existing session: {session_id}")
        else:
            print_info("Creating new session...")

        print()

        # Send request
        response = await client.post(f"{base_url}/run", json=request_data)
        response.raise_for_status()
        data = response.json()

        # Display results
        print_success(f"Request completed - Status: {data['status']}")
        print()
        print_info(f"Run ID:          {data['run_id']}")
        print_info(f"Session ID:      {data['session_id']}")
        print_info(f"Execution Time:  {data['execution_time_ms']:.2f}ms")
        print()

        # Display output messages
        print_info("Output Messages:")
        for i, message in enumerate(data["output"], 1):
            print_info(f"Message {i}:", indent=1)
            for j, part in enumerate(message["parts"], 1):
                print_info(f"Part {j} ({part['content_type']}):", indent=2)
                content = part["content"]
                if part["content_type"] == "application/jwt":
                    # Truncate JWT token
                    print_info(f"{content[:50]}... (truncated)", indent=3)
                else:
                    # Display text content
                    for line in content.split("\n"):
                        if line.strip():
                            print_info(line, indent=3)
                print()

            if message.get("error"):
                print_error(f"Error: {message['error']}")

        return data["session_id"]

    except httpx.HTTPError as e:
        print_error(f"Request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print_info(f"Error detail: {error_detail.get('detail', 'Unknown')}")
            except:
                pass
        return None


async def demo_session_history(
    client: httpx.AsyncClient, base_url: str, session_id: str
):
    """Demonstrate session history retrieval."""
    print_section(f"Session History: {session_id}")

    try:
        response = await client.get(f"{base_url}/sessions/{session_id}")
        response.raise_for_status()
        data = response.json()

        print_success("Session history retrieved")
        print()
        print_info(f"Session ID:        {data['session_id']}")
        print_info(f"Created At:        {data['created_at']}")
        print_info(f"Last Activity:     {data['last_activity']}")
        print_info(f"Interaction Count: {data['interaction_count']}")
        print()

        print_info("Interactions:")
        for i, interaction in enumerate(data["interactions"], 1):
            print_info(f"{i}. {interaction['timestamp']}", indent=1)
            print_info(f"Run ID:  {interaction['run_id']}", indent=2)
            print_info(f"Status:  {interaction['status']}", indent=2)
            print_info(f"Input:   {interaction['input_summary']}", indent=2)
            print_info(f"Output:  {interaction['output_summary']}", indent=2)
            print()

        return True

    except httpx.HTTPError as e:
        print_error(f"Failed to retrieve session history: {e}")
        return False


async def demo_error_handling(client: httpx.AsyncClient, base_url: str):
    """Demonstrate error handling."""
    print_section("Error Handling Test")

    # Test 1: Unknown agent
    print_info("Test 1: Unknown agent name")
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
        response = await client.post(f"{base_url}/run", json=request_data)
        response.raise_for_status()
        print_error("Should have failed but didn't!")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print_success(f"Correctly returned 404 for unknown agent")
            error_detail = e.response.json()
            print_info(f"Error: {error_detail.get('detail', 'Unknown')}", indent=1)
        else:
            print_error(f"Unexpected status code: {e.response.status_code}")

    print()

    # Test 2: Unparseable request
    print_info("Test 2: Unparseable credential request")
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
        response = await client.post(f"{base_url}/run", json=request_data)
        response.raise_for_status()
        data = response.json()

        if data["status"] == "error":
            print_success("Correctly returned error status for unparseable request")
            if data["output"] and data["output"][0].get("error"):
                print_info(f"Error: {data['output'][0]['error']}", indent=1)
        else:
            print_error(f"Expected error status but got: {data['status']}")

    except httpx.HTTPError as e:
        print_error(f"Unexpected HTTP error: {e}")

    print()

    # Test 3: Nonexistent session
    print_info("Test 3: Nonexistent session ID")
    try:
        response = await client.get(
            f"{base_url}/sessions/nonexistent-session-12345"
        )
        response.raise_for_status()
        print_error("Should have failed but didn't!")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print_success("Correctly returned 404 for nonexistent session")
            error_detail = e.response.json()
            print_info(f"Error: {error_detail.get('detail', 'Unknown')}", indent=1)
        else:
            print_error(f"Unexpected status code: {e.response.status_code}")


async def main():
    """Main demo function."""
    print_header("ACP (Agent Communication Protocol) Demo")

    base_url = "http://localhost:8001"
    print_info(f"ACP Server: {base_url}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check server health
        print_info("Checking server health...")
        try:
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
            health = response.json()
            print_success(
                f"Server is healthy - {health['service']} v{health['version']}"
            )
        except httpx.HTTPError as e:
            print_error(f"Server health check failed: {e}")
            print()
            print_info("Please ensure the ACP server is running:")
            print_info("  python src/acp/run_acp.py", indent=1)
            return

        # Demo 1: Agent Discovery
        success = await demo_agent_discovery(client, base_url)
        if not success:
            return

        # Demo 2: Natural Language Requests
        print_section("2. Natural Language Credential Requests")

        # Request 1: Database credentials
        session_id = await demo_natural_language_request(
            client,
            base_url,
            "I need database credentials for production-postgres",
        )

        if not session_id:
            return

        # Request 2: API credentials in same session
        await asyncio.sleep(1)  # Brief pause
        session_id = await demo_natural_language_request(
            client, base_url, "Get API credentials for stripe-api for 10 minutes", session_id
        )

        if not session_id:
            return

        # Request 3: SSH credentials in same session
        await asyncio.sleep(1)
        session_id = await demo_natural_language_request(
            client, base_url, "I need SSH keys for production-server", session_id
        )

        if not session_id:
            return

        # Demo 3: Session History
        await asyncio.sleep(1)
        await demo_session_history(client, base_url, session_id)

        # Demo 4: Error Handling
        await demo_error_handling(client, base_url)

        # Summary
        print_header("Demo Complete!")
        print_success("All ACP protocol features demonstrated successfully")
        print()
        print_info("Key Features Shown:")
        print_info("✓ Agent discovery", indent=1)
        print_info("✓ Natural language parsing", indent=1)
        print_info("✓ Multiple credential types (database, API, SSH)", indent=1)
        print_info("✓ Session management", indent=1)
        print_info("✓ Interaction history tracking", indent=1)
        print_info("✓ Error handling", indent=1)
        print()
        print_info("Next Steps:")
        print_info("- View API documentation: http://localhost:8001/docs", indent=1)
        print_info("- Check session history: GET /sessions/{session_id}", indent=1)
        print_info("- Try your own natural language requests!", indent=1)
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

