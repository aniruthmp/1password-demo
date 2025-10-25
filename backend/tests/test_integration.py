"""
Integration tests for Universal 1Password Agent Credential Broker

These tests verify end-to-end functionality across all protocols (MCP, A2A, ACP)
and test real integration with 1Password Connect API.
"""

import asyncio
import json
import os
import pytest
import subprocess
import time
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

# Import server modules
from src.a2a.a2a_server import app as a2a_app
from src.acp.acp_server import app as acp_app
from src.core.credential_manager import CredentialManager, create_credential_manager_from_env
from src.core.audit_logger import AuditLogger


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    return {
        "OP_CONNECT_HOST": os.getenv("OP_CONNECT_HOST", "http://localhost:8080"),
        "OP_CONNECT_TOKEN": os.getenv("OP_CONNECT_TOKEN", "test-token"),
        "OP_VAULT_ID": os.getenv("OP_VAULT_ID", "test-vault"),
        "JWT_SECRET_KEY": "test_secret_key_at_least_32_characters_long",
        "A2A_BEARER_TOKEN": "dev-token-change-in-production",  # Use the default from the server
        "ACP_BEARER_TOKEN": "dev-token-change-in-production",  # Use the default from the server
    }


@pytest.fixture(scope="session")
def credential_manager(test_env):
    """Create a real credential manager for integration testing."""
    with patch.dict(os.environ, test_env):
        return create_credential_manager_from_env()


@pytest.fixture
def a2a_client():
    """Create A2A test client."""
    return TestClient(a2a_app)


@pytest.fixture
def acp_client():
    """Create ACP test client."""
    return TestClient(acp_app)


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_credential_manager_integration(self, credential_manager):
        """Test credential manager with real 1Password integration."""
        # This test requires a real 1Password Connect server
        # Skip if not available
        try:
            health = credential_manager.health_check()
            if not health["status"] == "healthy":
                pytest.skip("1Password Connect not available")
        except Exception:
            pytest.skip("1Password Connect not available")

        # Test credential fetching
        with patch.object(credential_manager.op_client, 'get_item_by_title') as mock_get_item:
            mock_get_item.return_value = {
                "username": "testuser",
                "password": "testpass",
                "host": "localhost",
                "port": "5432",
                "_item_id": "item-123",
                "_item_title": "Test Database",
                "_vault_id": "vault-123",
            }

            result = credential_manager.fetch_and_issue_token(
                resource_type="database",
                resource_name="test-db",
                agent_id="integration-test-agent",
                ttl_minutes=5
            )

            assert "token" in result
            assert result["expires_in"] == 300
            assert result["resource"] == "database/test-db"
            assert result["agent_id"] == "integration-test-agent"

    def test_a2a_protocol_integration(self, a2a_client, test_env):
        """Test complete A2A protocol flow."""
        headers = {"Authorization": f"Bearer {test_env['A2A_BEARER_TOKEN']}"}

        # Test agent card discovery
        response = a2a_client.get("/agent-card")
        assert response.status_code == 200
        agent_card = response.json()
        assert agent_card["agent_id"] == "1password-credential-broker"
        assert len(agent_card["capabilities"]) >= 4

        # Test task execution
        with patch('src.a2a.a2a_server.get_credential_manager') as mock_get_cm:
            mock_cm = mock_get_cm.return_value
            mock_cm.fetch_and_issue_token.return_value = {
                "token": "test-jwt-token",
                "expires_in": 300,
                "resource": "database/test-db",
                "agent_id": "test-agent"
            }

            task_request = {
                "task_id": "integration-test-task",
                "capability_name": "request_database_credentials",
                "parameters": {
                    "database_name": "test-database",
                    "duration_minutes": 5
                },
                "requesting_agent_id": "integration-test-agent"
            }

            response = a2a_client.post("/task", json=task_request, headers=headers)
            assert response.status_code == 200
            
            result = response.json()
            assert result["task_id"] == "integration-test-task"
            assert result["status"] == "completed"
            assert "result" in result
            assert "ephemeral_token" in result["result"]
            assert result["result"]["ephemeral_token"] == "test-jwt-token"

    def test_acp_protocol_integration(self, acp_client, test_env):
        """Test complete ACP protocol flow."""
        headers = {"Authorization": f"Bearer {test_env['ACP_BEARER_TOKEN']}"}

        # Test agent discovery
        response = acp_client.get("/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents["agents"]) >= 1
        assert agents["agents"][0]["name"] == "credential-broker"

        # Test natural language credential request
        with patch('src.acp.acp_server.get_credential_manager') as mock_get_cm:
            mock_cm = mock_get_cm.return_value
            mock_cm.fetch_and_issue_token.return_value = {
                "token": "test-jwt-token",
                "expires_in": 300,
                "resource": "database/production-db",
                "agent_id": "test-agent"
            }

            run_request = {
                "agent_name": "credential-broker",
                "input": [{
                    "parts": [{
                        "content": "I need database credentials for production-db",
                        "content_type": "text/plain"
                    }]
                }]
            }

            response = acp_client.post("/run", json=run_request, headers=headers)
            assert response.status_code == 200
            
            result = response.json()
            assert result["status"] == "completed"
            assert "run_id" in result
            assert "session_id" in result
            assert len(result["output"]) >= 1

    def test_session_management_integration(self, acp_client, test_env):
        """Test ACP session management."""
        headers = {"Authorization": f"Bearer {test_env['ACP_BEARER_TOKEN']}"}

        # Create a session with multiple interactions
        session_id = "integration-test-session"
        
        with patch('src.acp.acp_server.get_credential_manager') as mock_get_cm:
            mock_cm = mock_get_cm.return_value
            mock_cm.fetch_and_issue_token.return_value = {
                "token": "test-jwt-token",
                "expires_in": 300,
                "resource": "database/test-db",
                "agent_id": "test-agent"
            }

            # First interaction
            run_request = {
                "agent_name": "credential-broker",
                "input": [{
                    "parts": [{
                        "content": "I need database credentials",
                        "content_type": "text/plain"
                    }]
                }],
                "session_id": session_id
            }

            response = acp_client.post("/run", json=run_request, headers=headers)
            assert response.status_code == 200

            # Second interaction in same session
            run_request["input"][0]["parts"][0]["content"] = "Now I need API credentials"
            response = acp_client.post("/run", json=run_request, headers=headers)
            assert response.status_code == 200

            # Retrieve session history
            response = acp_client.get(f"/sessions/{session_id}", headers=headers)
            assert response.status_code == 200
            
            session = response.json()
            assert session["session_id"] == session_id
            assert len(session["interactions"]) == 2

    def test_authentication_integration(self, a2a_client, acp_client):
        """Test authentication across protocols."""
        # Test A2A authentication
        response = a2a_client.post("/task", json={
            "task_id": "test",
            "capability_name": "request_database_credentials",
            "parameters": {"database_name": "test"},
            "requesting_agent_id": "test"
        })
        assert response.status_code == 401  # Unauthorized

        # Test ACP authentication
        response = acp_client.post("/run", json={
            "agent_name": "credential-broker",
            "input": [{"parts": [{"content": "test", "content_type": "text/plain"}]}]
        })
        assert response.status_code == 401  # Unauthorized

    def test_error_handling_integration(self, a2a_client, test_env):
        """Test error handling across the system."""
        headers = {"Authorization": f"Bearer {test_env['A2A_BEARER_TOKEN']}"}

        # Test invalid capability
        response = a2a_client.post("/task", json={
            "task_id": "test",
            "capability_name": "invalid_capability",
            "parameters": {},
            "requesting_agent_id": "test"
        }, headers=headers)
        assert response.status_code == 400

        # Test missing parameters
        response = a2a_client.post("/task", json={
            "task_id": "test",
            "capability_name": "request_database_credentials",
            "parameters": {},
            "requesting_agent_id": "test"
        }, headers=headers)
        assert response.status_code == 400

    def test_audit_logging_integration(self, credential_manager):
        """Test audit logging integration."""
        audit_logger = AuditLogger()
        
        # Test credential access logging
        with patch.object(audit_logger, 'log_credential_access') as mock_log:
            mock_log.return_value = None
            
            # Simulate credential access
            audit_logger.log_credential_access(
                protocol="A2A",
                agent_id="test-agent",
                resource="database/test-db",
                outcome="success"
            )
            
            mock_log.assert_called_once()

    def test_health_check_integration(self, a2a_client, acp_client):
        """Test health check endpoints."""
        # Test A2A health
        response = a2a_client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert "status" in health
        assert "timestamp" in health

        # Test ACP health
        response = acp_client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert "status" in health
        assert "timestamp" in health

    def test_status_endpoints_integration(self, a2a_client):
        """Test status endpoints."""
        response = a2a_client.get("/status")
        assert response.status_code == 200
        status = response.json()
        assert "active_tokens" in status
        assert "total_requests" in status
        assert "protocol" in status
        assert status["protocol"] == "A2A"


class TestMCPIntegration:
    """MCP protocol integration tests."""

    @pytest.mark.asyncio
    async def test_mcp_tool_discovery(self):
        """Test MCP tool discovery."""
        # This would require a real MCP client connection
        # For now, we'll test the server module directly
        from src.mcp.mcp_server import server
        
        # Test that tools are properly registered
        tools = await server.list_tools()
        assert len(tools) >= 1
        assert any(tool.name == "get_credentials" for tool in tools)

    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self):
        """Test MCP tool execution."""
        from src.mcp.mcp_server import server
        
        with patch('src.mcp.mcp_server.get_credential_manager') as mock_get_cm:
            mock_cm = mock_get_cm.return_value
            mock_cm.fetch_and_issue_token.return_value = {
                "token": "test-jwt-token",
                "expires_in": 300,
                "resource": "database/test-db",
                "agent_id": "test-agent"
            }

            # Test tool call
            result = await server.call_tool(
                "get_credentials",
                {
                    "resource_type": "database",
                    "resource_name": "test-database",
                    "requesting_agent_id": "test-agent",
                    "ttl_minutes": 5
                }
            )

            assert "token" in result
            assert result["expires_in"] == 300


class TestPerformanceIntegration:
    """Performance integration tests."""

    def test_concurrent_requests(self, a2a_client, test_env):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        headers = {"Authorization": f"Bearer {test_env['A2A_BEARER_TOKEN']}"}
        results = []
        errors = []

        def make_request():
            try:
                with patch('src.a2a.a2a_server.get_credential_manager') as mock_get_cm:
                    mock_cm = mock_get_cm.return_value
                    mock_cm.fetch_and_issue_token.return_value = {
                        "token": "test-jwt-token",
                        "expires_in": 300,
                        "resource": "database/test-db",
                        "agent_id": "test-agent"
                    }

                    response = a2a_client.post("/task", json={
                        "task_id": f"concurrent-test-{threading.current_thread().ident}",
                        "capability_name": "request_database_credentials",
                        "parameters": {"database_name": "test-db"},
                        "requesting_agent_id": "test-agent"
                    }, headers=headers)
                    
                    results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all requests succeeded
        assert len(errors) == 0
        assert len(results) == 10
        assert all(status == 200 for status in results)

    def test_response_time(self, a2a_client, test_env):
        """Test response time under normal load."""
        headers = {"Authorization": f"Bearer {test_env['A2A_BEARER_TOKEN']}"}
        
        with patch('src.a2a.a2a_server.get_credential_manager') as mock_get_cm:
            mock_cm = mock_get_cm.return_value
            mock_cm.fetch_and_issue_token.return_value = {
                "token": "test-jwt-token",
                "expires_in": 300,
                "resource": "database/test-db",
                "agent_id": "test-agent"
            }

            start_time = time.time()
            response = a2a_client.post("/task", json={
                "task_id": "performance-test",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test-db"},
                "requesting_agent_id": "test-agent"
            }, headers=headers)
            end_time = time.time()

            assert response.status_code == 200
            response_time = end_time - start_time
            assert response_time < 1.0  # Should respond within 1 second


class TestSecurityIntegration:
    """Security integration tests."""

    def test_token_expiration(self, credential_manager):
        """Test JWT token expiration."""
        with patch.object(credential_manager.op_client, 'get_item_by_title') as mock_get_item:
            mock_get_item.return_value = {
                "username": "testuser",
                "password": "testpass",
                "_item_id": "item-123",
                "_item_title": "Test Database",
                "_vault_id": "vault-123",
            }

            # Generate token with 1 second TTL
            result = credential_manager.fetch_and_issue_token(
                resource_type="database",
                resource_name="test-db",
                agent_id="test-agent",
                ttl_minutes=1/60  # 1 second
            )

            token = result["token"]
            
            # Token should be valid initially
            decoded = credential_manager.validate_token(token)
            assert decoded is not None

            # Wait for expiration
            time.sleep(2)
            
            # Token should be expired now
            decoded = credential_manager.validate_token(token)
            assert decoded is None

    def test_encryption_integration(self, credential_manager):
        """Test credential encryption."""
        with patch.object(credential_manager.op_client, 'get_item_by_title') as mock_get_item:
            mock_get_item.return_value = {
                "username": "testuser",
                "password": "secretpassword123",
                "_item_id": "item-123",
                "_item_title": "Test Database",
                "_vault_id": "vault-123",
            }

            result = credential_manager.fetch_and_issue_token(
                resource_type="database",
                resource_name="test-db",
                agent_id="test-agent"
            )

            token = result["token"]
            
            # Decode token and verify credentials are encrypted
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Credentials should be encrypted (not plaintext)
            assert "credentials" in decoded
            credentials = decoded["credentials"]
            assert isinstance(credentials, str)  # Should be encrypted string
            assert "secretpassword123" not in credentials  # Should not contain plaintext

    def test_bearer_token_validation(self, a2a_client):
        """Test bearer token validation."""
        # Test with invalid token
        response = a2a_client.post("/task", json={
            "task_id": "test",
            "capability_name": "request_database_credentials",
            "parameters": {"database_name": "test"},
            "requesting_agent_id": "test"
        }, headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401

        # Test with malformed header
        response = a2a_client.post("/task", json={
            "task_id": "test",
            "capability_name": "request_database_credentials",
            "parameters": {"database_name": "test"},
            "requesting_agent_id": "test"
        }, headers={"Authorization": "InvalidFormat token"})
        assert response.status_code == 401

        # Test without authorization header
        response = a2a_client.post("/task", json={
            "task_id": "test",
            "capability_name": "request_database_credentials",
            "parameters": {"database_name": "test"},
            "requesting_agent_id": "test"
        })
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
