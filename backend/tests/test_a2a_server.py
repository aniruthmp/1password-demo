"""
Unit tests for A2A Server
"""

import os
import sys

# Environment variables will be set in fixtures to avoid test pollution

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables for all A2A server tests."""
    monkeypatch.setenv("OP_CONNECT_HOST", "http://localhost:8080")
    monkeypatch.setenv("OP_CONNECT_TOKEN", "test-token-for-testing")
    monkeypatch.setenv("OP_VAULT_ID", "test-vault-123")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long")
    monkeypatch.setenv("A2A_BEARER_TOKEN", "dev-token-change-in-production")

from src.a2a.a2a_server import (
    app,
    AGENT_CARD,
    handle_database_credentials,
    handle_api_credentials,
    handle_ssh_credentials,
    handle_generic_secret,
    verify_bearer_token,
)


# Test client for FastAPI
@pytest.fixture
def client():
    """Create a test client for the A2A server."""
    return TestClient(app)


@pytest.fixture
def mock_credential_manager():
    """Mock credential manager for testing."""
    mock = Mock()
    mock.fetch_and_issue_token = Mock(return_value={
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
        "expires_in": 300,
        "resource": "database/test-db",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).isoformat(),
        "ttl_minutes": 5,
    })
    mock.health_check = Mock(return_value={
        "status": "healthy",
        "components": {
            "onepassword": {"status": "healthy"},
            "token_manager": {"status": "healthy"},
        }
    })
    return mock


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger for testing."""
    mock = Mock()
    mock.log_credential_access = AsyncMock()
    return mock


class TestAgentCard:
    """Tests for agent card discovery."""
    
    def test_get_agent_card(self, client):
        """Test agent card endpoint returns valid card."""
        response = client.get("/agent-card")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify agent card structure
        assert data["agent_id"] == "1password-credential-broker"
        assert data["name"] == "1Password Ephemeral Credential Agent"
        assert data["version"] == "1.0.0"
        assert data["authentication"] == "bearer_token"
        
        # Verify capabilities
        assert len(data["capabilities"]) == 4
        capability_names = [cap["name"] for cap in data["capabilities"]]
        assert "request_database_credentials" in capability_names
        assert "request_api_credentials" in capability_names
        assert "request_ssh_credentials" in capability_names
        assert "request_generic_secret" in capability_names
    
    def test_agent_card_capabilities_schema(self, client):
        """Test that each capability has proper input schema."""
        response = client.get("/agent-card")
        data = response.json()
        
        for capability in data["capabilities"]:
            assert "name" in capability
            assert "description" in capability
            assert "input_schema" in capability
            assert len(capability["input_schema"]) > 0
            
            # Verify input schema structure
            for input_param in capability["input_schema"]:
                assert "name" in input_param
                assert "type" in input_param
                assert "description" in input_param
                assert "required" in input_param


class TestTaskExecution:
    """Tests for task execution endpoint."""
    
    def test_task_execution_requires_auth(self, client):
        """Test that task execution requires bearer token."""
        response = client.post(
            "/task",
            json={
                "task_id": "test-123",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test-db"},
                "requesting_agent_id": "test-agent",
            }
        )
        
        assert response.status_code == 401
        assert "Authorization" in response.text or "authorization" in response.text.lower()
    
    def test_task_execution_invalid_token(self, client):
        """Test that invalid bearer token is rejected."""
        response = client.post(
            "/task",
            json={
                "task_id": "test-123",
                "capability_name": "request_database_credentials",
                "parameters": {"database_name": "test-db"},
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_database_credentials(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test successful database credentials request."""
        # Setup mocks
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "database/test-db",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request
        response = client.post(
            "/task",
            json={
                "task_id": "test-123",
                "capability_name": "request_database_credentials",
                "parameters": {
                    "database_name": "test-db",
                    "duration_minutes": 5,
                },
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["task_id"] == "test-123"
        assert data["status"] == "completed"
        assert "result" in data
        assert "execution_time_ms" in data
        
        # Verify result
        result = data["result"]
        assert "ephemeral_token" in result
        assert "expires_in_seconds" in result
        assert "database" in result
        assert result["database"] == "test-db"
        
        # Verify credential manager was called
        mock_cred_manager.fetch_and_issue_token.assert_called_once()
        
        # Verify audit logging
        mock_audit.log_credential_access.assert_called_once()
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_api_credentials(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test successful API credentials request."""
        # Setup mocks
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "api/test-api",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request
        response = client.post(
            "/task",
            json={
                "task_id": "test-456",
                "capability_name": "request_api_credentials",
                "parameters": {
                    "api_name": "test-api",
                    "scopes": ["read", "write"],
                    "duration_minutes": 5,
                },
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        result = data["result"]
        assert "ephemeral_token" in result
        assert "api" in result
        assert result["api"] == "test-api"
        assert "scopes" in result
        assert result["scopes"] == ["read", "write"]
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_ssh_credentials(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test successful SSH credentials request."""
        # Setup mocks
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "ssh/test-server",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request
        response = client.post(
            "/task",
            json={
                "task_id": "test-789",
                "capability_name": "request_ssh_credentials",
                "parameters": {
                    "ssh_resource_name": "test-server",
                    "duration_minutes": 5,
                },
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        result = data["result"]
        assert "ephemeral_token" in result
        assert "ssh_resource" in result
        assert result["ssh_resource"] == "test-server"
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_generic_secret(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test successful generic secret request."""
        # Setup mocks
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "generic/test-secret",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request
        response = client.post(
            "/task",
            json={
                "task_id": "test-101",
                "capability_name": "request_generic_secret",
                "parameters": {
                    "secret_name": "test-secret",
                    "duration_minutes": 5,
                },
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        result = data["result"]
        assert "ephemeral_token" in result
        assert "secret" in result
        assert result["secret"] == "test-secret"
    
    def test_task_execution_unknown_capability(self, client):
        """Test that unknown capability returns 400 error."""
        response = client.post(
            "/task",
            json={
                "task_id": "test-999",
                "capability_name": "unknown_capability",
                "parameters": {},
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        # The server actually catches this as HTTPException and returns 400
        # But the way FastAPI handles it, it might return 200 with error in body
        # Let's check both possibilities
        if response.status_code == 400:
            assert "Unknown capability" in response.text
        else:
            # If 200, should have failed status in response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert "error" in data
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_missing_parameters(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test that missing parameters returns failed status."""
        mock_audit.log_credential_access = AsyncMock()
        
        response = client.post(
            "/task",
            json={
                "task_id": "test-error",
                "capability_name": "request_database_credentials",
                "parameters": {},  # Missing database_name
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert "error" in data
        assert "database_name" in data["error"]
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_invalid_ttl(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test that invalid TTL returns failed status."""
        mock_audit.log_credential_access = AsyncMock()
        
        response = client.post(
            "/task",
            json={
                "task_id": "test-ttl",
                "capability_name": "request_database_credentials",
                "parameters": {
                    "database_name": "test-db",
                    "duration_minutes": 100,  # Exceeds max (15)
                },
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert "error" in data
        assert "duration_minutes" in data["error"]
    
    @patch("src.a2a.a2a_server.credential_manager")
    @patch("src.a2a.a2a_server.audit_logger")
    def test_task_execution_credential_fetch_error(
        self, mock_audit, mock_cred_manager, client
    ):
        """Test that credential fetch errors are handled gracefully."""
        # Setup mocks to raise error
        mock_cred_manager.fetch_and_issue_token.side_effect = Exception(
            "Resource not found"
        )
        mock_audit.log_credential_access = AsyncMock()
        
        response = client.post(
            "/task",
            json={
                "task_id": "test-error",
                "capability_name": "request_database_credentials",
                "parameters": {
                    "database_name": "nonexistent-db",
                    "duration_minutes": 5,
                },
                "requesting_agent_id": "test-agent",
            },
            headers={"Authorization": "Bearer dev-token-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert "error" in data
        
        # Verify audit logging for failure
        mock_audit.log_credential_access.assert_called_once()


class TestHealthEndpoints:
    """Tests for health and status endpoints."""
    
    @patch("src.a2a.a2a_server.credential_manager")
    def test_health_check_healthy(self, mock_cred_manager, client):
        """Test health check when all components are healthy."""
        mock_cred_manager.health_check.return_value = {
            "status": "healthy",
            "components": {
                "onepassword": {"status": "healthy"},
                "token_manager": {"status": "healthy"},
            }
        }
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "a2a-server"
        assert data["version"] == "1.0.0"
        assert "components" in data
    
    @patch("src.a2a.a2a_server.credential_manager")
    def test_health_check_unhealthy(self, mock_cred_manager, client):
        """Test health check when components are unhealthy."""
        mock_cred_manager.health_check.side_effect = Exception(
            "Connection failed"
        )
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert "error" in data
    
    def test_status_endpoint(self, client):
        """Test status endpoint returns server info."""
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "a2a-server"
        assert data["version"] == "1.0.0"
        assert "agent_card" in data
        assert data["agent_card"]["agent_id"] == "1password-credential-broker"
        assert data["agent_card"]["capabilities_count"] == 4


class TestCapabilityHandlers:
    """Tests for individual capability handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_database_credentials(
        self, mock_credential_manager, mock_audit_logger
    ):
        """Test database credentials handler."""
        with patch("src.a2a.a2a_server.credential_manager", mock_credential_manager):
            with patch("src.a2a.a2a_server.audit_logger", mock_audit_logger):
                result = await handle_database_credentials(
                    {"database_name": "test-db", "duration_minutes": 5},
                    "test-agent"
                )
        
        assert "ephemeral_token" in result
        assert "expires_in_seconds" in result
        assert "database" in result
        assert result["database"] == "test-db"
        assert "issued_at" in result
        
        # Verify audit logging
        mock_audit_logger.log_credential_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_api_credentials_with_scopes(
        self, mock_credential_manager, mock_audit_logger
    ):
        """Test API credentials handler with scopes."""
        with patch("src.a2a.a2a_server.credential_manager", mock_credential_manager):
            with patch("src.a2a.a2a_server.audit_logger", mock_audit_logger):
                result = await handle_api_credentials(
                    {
                        "api_name": "test-api",
                        "scopes": ["read", "write"],
                        "duration_minutes": 10
                    },
                    "test-agent"
                )
        
        assert result["api"] == "test-api"
        assert result["scopes"] == ["read", "write"]
        
        # Verify scopes were logged in metadata
        log_call = mock_audit_logger.log_credential_access.call_args[1]
        assert log_call["metadata"]["scopes"] == ["read", "write"]
    
    @pytest.mark.asyncio
    async def test_handle_ssh_credentials(
        self, mock_credential_manager, mock_audit_logger
    ):
        """Test SSH credentials handler."""
        with patch("src.a2a.a2a_server.credential_manager", mock_credential_manager):
            with patch("src.a2a.a2a_server.audit_logger", mock_audit_logger):
                result = await handle_ssh_credentials(
                    {"ssh_resource_name": "prod-server", "duration_minutes": 5},
                    "test-agent"
                )
        
        assert result["ssh_resource"] == "prod-server"
    
    @pytest.mark.asyncio
    async def test_handle_generic_secret(
        self, mock_credential_manager, mock_audit_logger
    ):
        """Test generic secret handler."""
        with patch("src.a2a.a2a_server.credential_manager", mock_credential_manager):
            with patch("src.a2a.a2a_server.audit_logger", mock_audit_logger):
                result = await handle_generic_secret(
                    {"secret_name": "my-secret", "duration_minutes": 5},
                    "test-agent"
                )
        
        assert result["secret"] == "my-secret"
    
    @pytest.mark.asyncio
    async def test_capability_handler_missing_param(
        self, mock_credential_manager, mock_audit_logger
    ):
        """Test that handlers raise ValueError for missing parameters."""
        with patch("src.a2a.a2a_server.credential_manager", mock_credential_manager):
            with patch("src.a2a.a2a_server.audit_logger", mock_audit_logger):
                with pytest.raises(ValueError, match="database_name"):
                    await handle_database_credentials(
                        {"duration_minutes": 5},  # Missing database_name
                        "test-agent"
                    )
    
    @pytest.mark.asyncio
    async def test_capability_handler_invalid_ttl(
        self, mock_credential_manager, mock_audit_logger
    ):
        """Test that handlers validate TTL range."""
        with patch("src.a2a.a2a_server.credential_manager", mock_credential_manager):
            with patch("src.a2a.a2a_server.audit_logger", mock_audit_logger):
                # Test TTL too high
                with pytest.raises(ValueError, match="duration_minutes"):
                    await handle_database_credentials(
                        {"database_name": "test-db", "duration_minutes": 100},
                        "test-agent"
                    )
                
                # Test TTL too low
                with pytest.raises(ValueError, match="duration_minutes"):
                    await handle_database_credentials(
                        {"database_name": "test-db", "duration_minutes": 0},
                        "test-agent"
                    )


class TestSSEStreaming:
    """Tests for SSE streaming endpoint."""
    
    def test_sse_stream_requires_auth(self, client):
        """Test that SSE streaming requires bearer token."""
        response = client.post("/task/test-123/stream")
        
        assert response.status_code == 401
    
    def test_sse_stream_endpoint_exists(self, client):
        """Test that SSE endpoint is available."""
        # This will fail auth but confirms endpoint exists
        response = client.post(
            "/task/test-123/stream",
            headers={"Authorization": "Bearer invalid"}
        )
        
        # Should get 401 (not 404), confirming endpoint exists
        assert response.status_code == 401


class TestAuthentication:
    """Tests for authentication."""
    
    @pytest.mark.asyncio
    async def test_verify_bearer_token_missing(self):
        """Test that missing authorization header is rejected."""
        with pytest.raises(Exception):  # Will raise HTTPException
            await verify_bearer_token(None)
    
    @pytest.mark.asyncio
    async def test_verify_bearer_token_invalid_format(self):
        """Test that invalid authorization format is rejected."""
        with pytest.raises(Exception):  # Will raise HTTPException
            await verify_bearer_token("InvalidFormat token")
    
    @pytest.mark.asyncio
    async def test_verify_bearer_token_wrong_scheme(self):
        """Test that non-Bearer scheme is rejected."""
        with pytest.raises(Exception):  # Will raise HTTPException
            await verify_bearer_token("Basic dGVzdDp0ZXN0")
    
    @pytest.mark.asyncio
    async def test_verify_bearer_token_invalid_token(self):
        """Test that invalid token is rejected."""
        with pytest.raises(Exception):  # Will raise HTTPException
            await verify_bearer_token("Bearer wrong-token")
    
    @pytest.mark.asyncio
    async def test_verify_bearer_token_valid(self):
        """Test that valid token is accepted."""
        agent_id = await verify_bearer_token(
            "Bearer dev-token-change-in-production"
        )
        assert agent_id == "authenticated-agent"


class TestDataModels:
    """Tests for data models and validation."""
    
    def test_agent_card_structure(self):
        """Test that AGENT_CARD has correct structure."""
        assert AGENT_CARD.agent_id == "1password-credential-broker"
        assert AGENT_CARD.version == "1.0.0"
        assert len(AGENT_CARD.capabilities) == 4
        assert AGENT_CARD.authentication == "bearer_token"
        
        # Verify all capabilities have required fields
        for capability in AGENT_CARD.capabilities:
            assert capability.name
            assert capability.description
            assert capability.input_schema
            assert len(capability.input_schema) > 0

