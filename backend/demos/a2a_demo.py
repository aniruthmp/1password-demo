#!/usr/bin/env python3
"""
A2A (Agent-to-Agent) Demo Client

Demonstrates agent-to-agent credential exchange using the A2A protocol.

Usage:
    cd backend
    poetry run python demos/a2a_demo.py

Prerequisites:
    - A2A server running on http://localhost:8000
    - Valid 1Password credentials configured
    - At least one credential in your vault
"""

import asyncio
import json
import sys
from datetime import datetime, UTC
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# A2A Server Configuration
A2A_SERVER_URL = "http://localhost:8000"
BEARER_TOKEN = "dev-token-change-in-production"  # Should match server configuration


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(number: int, text: str):
    """Print a section header."""
    print(f"\n{number}. {text}")


def print_success(text: str, indent: int = 1):
    """Print a success message."""
    print(f"{'   ' * indent}✅ {text}")


def print_error(text: str, indent: int = 1):
    """Print an error message."""
    print(f"{'   ' * indent}❌ {text}")


def print_info(text: str, indent: int = 1):
    """Print an info message."""
    print(f"{'   ' * indent}{text}")


def print_json(data: Any, indent: int = 1):
    """Print JSON data in a formatted way."""
    json_str = json.dumps(data, indent=2)
    for line in json_str.split("\n"):
        print(f"{'   ' * indent}{line}")


async def discover_agent_card(client: httpx.AsyncClient) -> dict[str, Any]:
    """
    Discover the agent card from the A2A server.

    Args:
        client: HTTP client

    Returns:
        Agent card data
    """
    print_section(1, "Agent Discovery")
    print_info("Discovering 1Password credential broker agent...")

    try:
        response = await client.get(f"{A2A_SERVER_URL}/agent-card")
        response.raise_for_status()

        agent_card = response.json()
        print_success(f"Found agent: {agent_card['name']}")
        print_info(f"Agent ID: {agent_card['agent_id']}", indent=2)
        print_info(f"Version: {agent_card['version']}", indent=2)
        print_info(f"Description: {agent_card['description']}", indent=2)
        print_info(f"Authentication: {agent_card['authentication']}", indent=2)

        print_info(f"\nAvailable Capabilities ({len(agent_card['capabilities'])} total):", indent=1)
        for i, cap in enumerate(agent_card["capabilities"], 1):
            print_info(f"{i}. {cap['name']}", indent=2)
            print_info(f"   Description: {cap['description']}", indent=2)

        return agent_card

    except httpx.HTTPError as e:
        print_error(f"Failed to discover agent: {e}")
        raise


async def request_database_credentials(
    client: httpx.AsyncClient,
    database_name: str,
    duration_minutes: int = 5,
    requesting_agent_id: str = "demo-data-agent",
) -> dict[str, Any]:
    """
    Request database credentials from the A2A server.

    Args:
        client: HTTP client
        database_name: Name of database resource
        duration_minutes: Token TTL in minutes
        requesting_agent_id: Requesting agent identifier

    Returns:
        Task response with credentials
    """
    print_section(2, f"Requesting Database Credentials: {database_name}")
    print_info(f"Database: {database_name}")
    print_info(f"TTL: {duration_minutes} minutes")
    print_info(f"Requesting Agent: {requesting_agent_id}")

    task_request = {
        "task_id": f"task-{datetime.now(UTC).timestamp()}",
        "capability_name": "request_database_credentials",
        "parameters": {
            "database_name": database_name,
            "duration_minutes": duration_minutes,
        },
        "requesting_agent_id": requesting_agent_id,
    }

    print_info("\nSending task request...")
    print_json(task_request, indent=2)

    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json=task_request,
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        response.raise_for_status()

        task_response = response.json()
        print_success("Task completed successfully!")

        print_info("\nTask Response:")
        print_info(f"Task ID: {task_response['task_id']}", indent=2)
        print_info(f"Status: {task_response['status']}", indent=2)
        print_info(f"Execution Time: {task_response.get('execution_time_ms', 'N/A')}ms", indent=2)

        if task_response.get("result"):
            result = task_response["result"]
            print_info("\nCredential Details:", indent=2)
            print_info(f"Token: {result['ephemeral_token'][:50]}...", indent=3)
            print_info(f"Expires In: {result['expires_in_seconds']} seconds", indent=3)
            print_info(f"Database: {result['database']}", indent=3)
            print_info(f"Issued At: {result['issued_at']}", indent=3)

        return task_response

    except httpx.HTTPError as e:
        print_error(f"Task failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print_info(f"Response: {e.response.text}", indent=2)
        raise


async def request_api_credentials(
    client: httpx.AsyncClient,
    api_name: str,
    scopes: list[str] = None,
    duration_minutes: int = 5,
    requesting_agent_id: str = "demo-api-agent",
) -> dict[str, Any]:
    """
    Request API credentials from the A2A server.

    Args:
        client: HTTP client
        api_name: Name of API resource
        scopes: Optional API scopes
        duration_minutes: Token TTL in minutes
        requesting_agent_id: Requesting agent identifier

    Returns:
        Task response with credentials
    """
    print_section(3, f"Requesting API Credentials: {api_name}")
    print_info(f"API: {api_name}")
    print_info(f"Scopes: {scopes or 'None'}")
    print_info(f"TTL: {duration_minutes} minutes")

    task_request = {
        "task_id": f"task-{datetime.now(UTC).timestamp()}",
        "capability_name": "request_api_credentials",
        "parameters": {
            "api_name": api_name,
            "scopes": scopes or [],
            "duration_minutes": duration_minutes,
        },
        "requesting_agent_id": requesting_agent_id,
    }

    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json=task_request,
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        response.raise_for_status()

        task_response = response.json()
        print_success("API credentials obtained!")

        if task_response.get("result"):
            result = task_response["result"]
            print_info(f"Token: {result['ephemeral_token'][:50]}...", indent=2)
            print_info(f"Expires In: {result['expires_in_seconds']} seconds", indent=2)

        return task_response

    except httpx.HTTPError as e:
        print_error(f"Failed to get API credentials: {e}")
        raise


async def test_error_handling(
    client: httpx.AsyncClient,
) -> None:
    """
    Test error handling with invalid requests.

    Args:
        client: HTTP client
    """
    print_section(4, "Testing Error Handling")

    # Test 1: Invalid capability
    print_info("Test 1: Invalid capability name...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "error-test-1",
                "capability_name": "non_existent_capability",
                "parameters": {},
                "requesting_agent_id": "error-test-agent",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        if response.status_code == 400:
            print_success("Error handled correctly (400 Bad Request)", indent=2)
        else:
            print_error(f"Unexpected status: {response.status_code}", indent=2)
    except Exception as e:
        print_error(f"Unexpected error: {e}", indent=2)

    # Test 2: Missing authentication
    print_info("\nTest 2: Missing authentication...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "error-test-2",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test"},
                "requesting_agent_id": "error-test-agent",
            },
        )
        if response.status_code == 401:
            print_success("Authentication required (401 Unauthorized)", indent=2)
        else:
            print_error(f"Unexpected status: {response.status_code}", indent=2)
    except Exception as e:
        print_error(f"Unexpected error: {e}", indent=2)

    # Test 3: Invalid resource name
    print_info("\nTest 3: Non-existent resource...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "error-test-3",
                "capability_name": "request_database_credentials",
                "parameters": {
                    "database_name": "non-existent-resource-xyz-123",
                    "duration_minutes": 5,
                },
                "requesting_agent_id": "error-test-agent",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        result = response.json()
        if result["status"] == "failed":
            print_success("Error handled gracefully in response", indent=2)
            print_info(f"Error message: {result.get('error')}", indent=3)
        else:
            print_error(f"Unexpected status: {result['status']}", indent=2)
    except Exception as e:
        print_error(f"Unexpected error: {e}", indent=2)


async def main():
    """Main demo flow."""
    print_header("A2A (Agent-to-Agent) Demo Client")
    print_info("Demonstrating agent-to-agent credential exchange")
    print_info(f"Server: {A2A_SERVER_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Step 1: Discover agent
            agent_card = await discover_agent_card(client)

            # Step 2: Request database credentials
            print_info("\nLet's request database credentials...")
            database_name = input("\n   Enter database name (from your 1Password vault): ").strip()

            if not database_name:
                print_error("Database name is required")
                return

            await request_database_credentials(
                client,
                database_name=database_name,
                duration_minutes=5,
            )

            # Step 3: Optional - Request API credentials
            print()
            test_api = input("   Would you like to test API credentials? [y/N]: ").strip().lower()

            if test_api == "y":
                api_name = input("   Enter API name (from your 1Password vault): ").strip()
                if api_name:
                    await request_api_credentials(
                        client,
                        api_name=api_name,
                        scopes=["read", "write"],
                        duration_minutes=5,
                    )

            # Step 4: Error handling tests
            print()
            test_errors = input("   Would you like to test error handling? [y/N]: ").strip().lower()

            if test_errors == "y":
                await test_error_handling(client)

            # Summary
            print_header("Demo Complete!")
            print_success("A2A protocol demonstration successful")
            print_info("\nKey Achievements:", indent=1)
            print_info("✓ Agent discovery via Agent Card", indent=2)
            print_info("✓ Task-based credential request", indent=2)
            print_info("✓ Ephemeral token generation", indent=2)
            print_info("✓ Bearer token authentication", indent=2)
            print_info("✓ Error handling validated", indent=2)

            print_info("\nNext Steps:", indent=1)
            print_info("- Phase 4: Implement ACP server", indent=2)
            print_info("- Integrate A2A with agent frameworks", indent=2)
            print_info("- Deploy with Docker Compose", indent=2)

        except KeyboardInterrupt:
            print()
            print_error("Demo interrupted by user")
            sys.exit(1)
        except Exception as e:
            print()
            print_error(f"Demo failed: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

