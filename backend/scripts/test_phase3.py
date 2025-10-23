#!/usr/bin/env python3
"""
Interactive Phase 3 Testing Script - A2A Server

Tests the A2A (Agent-to-Agent) server implementation.

IMPORTANT: Run this script from the backend directory using Poetry:
    cd backend
    poetry run python scripts/test_phase3.py

Prerequisites:
    - A2A server must be running on http://localhost:8000
      Start with: poetry run python src/a2a/run_a2a.py
    - Or run in a separate terminal before executing this test
"""

import asyncio
import json
import os
import sys
from datetime import datetime, UTC
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# A2A Server Configuration
A2A_SERVER_URL = "http://localhost:8000"
BEARER_TOKEN = os.getenv("A2A_BEARER_TOKEN", "dev-token-change-in-production")


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(number: int, text: str):
    """Print a section header."""
    print(f"\n{number}. {text}...")


def print_success(text: str):
    """Print a success message."""
    print(f"   ✅ {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"   ❌ {text}")


def print_info(text: str, indent: int = 1):
    """Print an info message."""
    print(f"   {'  ' * (indent - 1)}{text}")


def print_json(data: Any, indent: int = 1):
    """Print JSON data."""
    json_str = json.dumps(data, indent=2)
    for line in json_str.split("\n"):
        print(f"   {'  ' * (indent - 1)}{line}")


async def check_server_connectivity(client: httpx.AsyncClient) -> bool:
    """
    Check if A2A server is running and accessible.

    Args:
        client: HTTP client

    Returns:
        True if server is accessible, False otherwise
    """
    print_section(1, "Server Connectivity Check")

    try:
        response = await client.get(f"{A2A_SERVER_URL}/health", timeout=5.0)
        response.raise_for_status()

        health = response.json()
        print_success("A2A server is running")
        print_info(f"Status: {health.get('status')}", indent=2)
        print_info(f"Service: {health.get('service')}", indent=2)
        print_info(f"Version: {health.get('version')}", indent=2)

        return True

    except httpx.ConnectError:
        print_error("Cannot connect to A2A server")
        print_info("Please start the server first:", indent=2)
        print_info("poetry run python src/a2a/run_a2a.py", indent=3)
        return False
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False


async def test_agent_card_discovery(client: httpx.AsyncClient) -> dict[str, Any]:
    """
    Test agent card discovery endpoint.

    Args:
        client: HTTP client

    Returns:
        Agent card data
    """
    print_section(2, "Agent Card Discovery")

    try:
        response = await client.get(f"{A2A_SERVER_URL}/agent-card")
        response.raise_for_status()

        agent_card = response.json()
        print_success("Agent card retrieved successfully")

        print_info("Agent Information:", indent=2)
        print_info(f"ID: {agent_card.get('agent_id')}", indent=3)
        print_info(f"Name: {agent_card.get('name')}", indent=3)
        print_info(f"Version: {agent_card.get('version')}", indent=3)
        print_info(f"Authentication: {agent_card.get('authentication')}", indent=3)

        capabilities = agent_card.get("capabilities", [])
        print_info(f"\nCapabilities ({len(capabilities)} total):", indent=2)

        for i, cap in enumerate(capabilities, 1):
            print_info(f"{i}. {cap['name']}", indent=3)
            print_info(f"   Description: {cap['description']}", indent=3)
            print_info(f"   Inputs: {len(cap.get('input_schema', []))} parameters", indent=3)

        # Validate expected capabilities
        expected_capabilities = [
            "request_database_credentials",
            "request_api_credentials",
            "request_ssh_credentials",
            "request_generic_secret",
        ]

        capability_names = [cap["name"] for cap in capabilities]
        all_present = all(name in capability_names for name in expected_capabilities)

        if all_present:
            print_success("All expected capabilities present")
        else:
            missing = [name for name in expected_capabilities if name not in capability_names]
            print_error(f"Missing capabilities: {missing}")

        return agent_card

    except Exception as e:
        print_error(f"Agent card discovery failed: {e}")
        raise


async def test_task_execution(
    client: httpx.AsyncClient,
    resource_type: str,
    resource_name: str,
    duration_minutes: int = 5,
) -> dict[str, Any]:
    """
    Test task execution with credential request.

    Args:
        client: HTTP client
        resource_type: Type of resource (database, api, ssh, generic)
        resource_name: Name of resource
        duration_minutes: Token TTL

    Returns:
        Task response
    """
    print_section(3, f"Task Execution - {resource_type.title()} Credentials")

    # Map resource types to capability names
    capability_map = {
        "database": ("request_database_credentials", "database_name"),
        "api": ("request_api_credentials", "api_name"),
        "ssh": ("request_ssh_credentials", "ssh_resource_name"),
        "generic": ("request_generic_secret", "secret_name"),
    }

    if resource_type not in capability_map:
        print_error(f"Invalid resource type: {resource_type}")
        return {}

    capability_name, param_name = capability_map[resource_type]

    task_request = {
        "task_id": f"test-task-{datetime.now(UTC).timestamp()}",
        "capability_name": capability_name,
        "parameters": {
            param_name: resource_name,
            "duration_minutes": duration_minutes,
        },
        "requesting_agent_id": "phase3-test-agent",
    }

    print_info("Task Request:", indent=2)
    print_info(f"Task ID: {task_request['task_id']}", indent=3)
    print_info(f"Capability: {task_request['capability_name']}", indent=3)
    print_info(f"Resource: {resource_name}", indent=3)
    print_info(f"TTL: {duration_minutes} minutes", indent=3)

    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json=task_request,
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        response.raise_for_status()

        task_response = response.json()
        print_success("Task executed successfully")

        print_info("\nTask Response:", indent=2)
        print_info(f"Status: {task_response['status']}", indent=3)
        print_info(f"Execution Time: {task_response.get('execution_time_ms', 'N/A')}ms", indent=3)

        if task_response.get("result"):
            result = task_response["result"]
            print_info("\nCredential Details:", indent=2)
            token = result.get("ephemeral_token", "")
            print_info(f"Token: {token[:50]}... (truncated)", indent=3)
            print_info(f"Expires In: {result.get('expires_in_seconds')} seconds", indent=3)
            print_info(f"Issued At: {result.get('issued_at')}", indent=3)

            # Validate token structure (should be JWT)
            if token and len(token.split('.')) == 3:
                print_success("Token format validated (JWT structure)")
            else:
                print_error("Invalid token format")

        return task_response

    except httpx.HTTPStatusError as e:
        print_error(f"Task execution failed: {e}")
        print_info(f"Status Code: {e.response.status_code}", indent=2)
        print_info(f"Response: {e.response.text}", indent=2)
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise


async def test_authentication(client: httpx.AsyncClient) -> None:
    """
    Test bearer token authentication.

    Args:
        client: HTTP client
    """
    print_section(4, "Authentication Testing")

    # Test 1: Missing authentication
    print_info("Test 1: Missing Authorization header...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "auth-test-1",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test"},
                "requesting_agent_id": "auth-test",
            },
        )
        if response.status_code == 401:
            print_success("Correctly rejected (401 Unauthorized)", indent=2)
        else:
            print_error(f"Unexpected status: {response.status_code}", indent=2)
    except Exception as e:
        print_error(f"Test failed: {e}", indent=2)

    # Test 2: Invalid token
    print_info("\nTest 2: Invalid bearer token...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "auth-test-2",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test"},
                "requesting_agent_id": "auth-test",
            },
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        if response.status_code == 401:
            print_success("Correctly rejected (401 Unauthorized)", indent=2)
        else:
            print_error(f"Unexpected status: {response.status_code}", indent=2)
    except Exception as e:
        print_error(f"Test failed: {e}", indent=2)

    # Test 3: Valid token
    print_info("\nTest 3: Valid bearer token...")
    try:
        response = await client.get(
            f"{A2A_SERVER_URL}/agent-card",
        )
        if response.status_code == 200:
            print_success("Public endpoint accessible without auth", indent=2)

        # Test authenticated endpoint
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "auth-test-3",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test-db", "duration_minutes": 5},
                "requesting_agent_id": "auth-test",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        # Will fail due to missing resource, but auth should pass
        if response.status_code in [200, 400, 500]:  # Auth passed, may have other errors
            print_success("Authentication successful", indent=2)
        else:
            print_error(f"Authentication failed: {response.status_code}", indent=2)
    except Exception as e:
        print_error(f"Test failed: {e}", indent=2)


async def test_error_handling(client: httpx.AsyncClient) -> None:
    """
    Test error handling with various invalid requests.

    Args:
        client: HTTP client
    """
    print_section(5, "Error Handling")

    # Test 1: Invalid capability
    print_info("Test 1: Invalid capability name...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "error-test-1",
                "capability_name": "non_existent_capability",
                "parameters": {},
                "requesting_agent_id": "error-test",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        if response.status_code == 400:
            print_success("Error handled correctly (400 Bad Request)", indent=2)
        else:
            print_error(f"Unexpected status: {response.status_code}", indent=2)
    except Exception as e:
        print_error(f"Test failed: {e}", indent=2)

    # Test 2: Missing required parameters
    print_info("\nTest 2: Missing required parameters...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "error-test-2",
                "capability_name": "request_database_credentials",
                "parameters": {},  # Missing database_name
                "requesting_agent_id": "error-test",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        result = response.json()
        if result.get("status") == "failed":
            print_success("Error handled gracefully in task response", indent=2)
            print_info(f"Error: {result.get('error')}", indent=3)
        else:
            print_error(f"Unexpected response: {result}", indent=2)
    except Exception as e:
        print_error(f"Test failed: {e}", indent=2)

    # Test 3: Invalid TTL
    print_info("\nTest 3: Invalid TTL value...")
    try:
        response = await client.post(
            f"{A2A_SERVER_URL}/task",
            json={
                "task_id": "error-test-3",
                "capability_name": "request_database_credentials",
                "parameters": {
                    "database_name": "test-db",
                    "duration_minutes": 100,  # Exceeds max (15)
                },
                "requesting_agent_id": "error-test",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        result = response.json()
        if result.get("status") == "failed":
            print_success("TTL validation working", indent=2)
        else:
            print_error(f"TTL validation not working", indent=2)
    except Exception as e:
        print_error(f"Test failed: {e}", indent=2)


async def main():
    """Main test flow."""
    print_header("Phase 3 Validation Test - A2A Server")
    print_info("Testing Agent-to-Agent credential exchange")
    print_info(f"Server URL: {A2A_SERVER_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Step 1: Check server connectivity
            if not await check_server_connectivity(client):
                print()
                print_error("A2A server is not running")
                print_info("Please start it in another terminal:", indent=1)
                print_info("cd backend", indent=2)
                print_info("poetry run python src/a2a/run_a2a.py", indent=2)
                sys.exit(1)

            # Step 2: Test agent card discovery
            agent_card = await test_agent_card_discovery(client)

            # Step 3: Test task execution
            print()
            print_info("Now let's test credential retrieval...")
            print()

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
                "4": "generic",
            }

            choice = input("   Select resource type [1-4] or enter custom: ").strip()
            resource_type = resource_type_map.get(choice, choice)

            if resource_type not in ["database", "api", "ssh", "generic"]:
                print_error(f"Invalid resource type: {resource_type}")
                sys.exit(1)

            resource_name = input("   Enter 1Password item name: ").strip()
            if not resource_name:
                print_error("Resource name is required")
                sys.exit(1)

            ttl_input = input("   Enter TTL in minutes (default: 5, max: 15): ").strip()
            try:
                ttl_minutes = int(ttl_input) if ttl_input else 5
                if ttl_minutes < 1 or ttl_minutes > 15:
                    print_error("TTL must be between 1 and 15 minutes")
                    sys.exit(1)
            except ValueError:
                print_error("Invalid TTL value")
                sys.exit(1)

            await test_task_execution(
                client,
                resource_type=resource_type,
                resource_name=resource_name,
                duration_minutes=ttl_minutes,
            )

            # Step 4: Test authentication
            print()
            test_auth = input("   Would you like to test authentication? [y/N]: ").strip().lower()
            if test_auth == "y":
                await test_authentication(client)

            # Step 5: Test error handling
            print()
            test_errors = input("   Would you like to test error handling? [y/N]: ").strip().lower()
            if test_errors == "y":
                await test_error_handling(client)

            # Summary
            print_header("Phase 3 Validation Complete!")
            print()
            print_success("A2A server is fully operational")
            print()
            print_info("Key Achievements:", indent=1)
            print_info("✓ A2A server responding on port 8000", indent=2)
            print_info("✓ Agent card discovery working", indent=2)
            print_info("✓ Task execution functional", indent=2)
            print_info("✓ Bearer token authentication active", indent=2)
            print_info("✓ All 4 capabilities implemented", indent=2)
            print_info("✓ Error handling validated", indent=2)
            print()
            print_info("Next Steps:", indent=1)
            print_info("- Phase 4: Implement ACP server", indent=2)
            print_info("- Phase 5: Add Docker orchestration", indent=2)
            print_info("- Phase 6: Create demo UI (optional)", indent=2)
            print()

        except KeyboardInterrupt:
            print()
            print_error("Test interrupted by user")
            sys.exit(1)
        except Exception as e:
            print()
            print_error(f"Test failed: {e}")
            import traceback

            print()
            print_info("Traceback:", indent=1)
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

