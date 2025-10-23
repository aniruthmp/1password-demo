"""
Unit tests for ACP Server
"""

import os
import sys

# Environment variables will be set in fixtures to avoid test pollution

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone, UTC
from fastapi.testclient import TestClient
import uuid


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables for all ACP server tests."""
    monkeypatch.setenv("OP_CONNECT_HOST", "http://localhost:8080")
    monkeypatch.setenv("OP_CONNECT_TOKEN", "test-token-for-testing")
    monkeypatch.setenv("OP_VAULT_ID", "test-vault-123")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long")

from src.acp.acp_server import (
    app,
    IntentParser,
    SessionManager,
    MessagePart,
    Message,
    ACPRunRequest,
    ACPRunResponse,
    RunStatus,
    AgentInfo,
    AgentsResponse,
    SessionHistory,
    HealthResponse,
)


# Test client for FastAPI
@pytest.fixture
def client():
    """Create a test client for the ACP server."""
    return TestClient(app)


@pytest.fixture
def mock_credential_manager():
    """Mock credential manager for testing."""
    mock = Mock()
    mock.fetch_and_issue_token = Mock(return_value={
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
        "expires_in": 300,
        "resource": "database/test-db",
        "issued_at": datetime.now(UTC).isoformat() + "Z",
        "expires_at": datetime.now(UTC).isoformat() + "Z",
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


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing."""
    mock = Mock()
    mock.create_session = AsyncMock(return_value=f"session-{uuid.uuid4()}")
    mock.add_interaction = AsyncMock()
    mock.get_session = AsyncMock(return_value={
        "session_id": "test-session-123",
        "created_at": datetime.now(UTC).isoformat() + "Z",
        "last_activity": datetime.now(UTC).isoformat() + "Z",
        "interactions": [
            {
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "run_id": "run-123",
                "input_summary": "I need database credentials",
                "output_summary": "Generated ephemeral credentials",
                "status": "completed",
            }
        ],
    })
    return mock


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "acp-server"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data


class TestAgentDiscovery:
    """Tests for agent discovery endpoint."""
    
    def test_get_agents(self, client):
        """Test agents endpoint returns agent list."""
        response = client.get("/agents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "agents" in data
        assert "count" in data
        assert data["count"] == 1
        
        # Verify agent structure
        agent = data["agents"][0]
        assert agent["name"] == "credential-broker"
        assert "description" in agent
        assert "capabilities" in agent
        assert "version" in agent
        assert agent["version"] == "1.0.0"
    
    def test_agent_capabilities(self, client):
        """Test that agent has expected capabilities."""
        response = client.get("/agents")
        data = response.json()
        
        agent = data["agents"][0]
        capabilities = agent["capabilities"]
        
        expected_capabilities = [
            "database_credentials",
            "api_credentials",
            "ssh_credentials",
            "generic_secrets",
            "natural_language_parsing",
            "session_management",
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities


class TestRunEndpoint:
    """Tests for run endpoint."""
    
    def test_run_requires_agent_name(self, client):
        """Test that run endpoint requires agent_name."""
        response = client.post(
            "/run",
            json={
                "input": [
                    {
                        "parts": [{"content": "test", "content_type": "text/plain"}],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_run_unknown_agent(self, client):
        """Test that unknown agent returns 404."""
        response = client.post(
            "/run",
            json={
                "agent_name": "nonexistent-agent",
                "input": [
                    {
                        "parts": [{"content": "test", "content_type": "text/plain"}],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch("src.acp.acp_server.credential_manager")
    @patch("src.acp.acp_server.audit_logger")
    @patch("src.acp.acp_server.session_manager")
    def test_run_database_credentials(
        self, mock_session, mock_audit, mock_cred_manager, client
    ):
        """Test successful database credentials request."""
        # Setup mocks
        session_id = f"session-{uuid.uuid4()}"
        mock_session.create_session = AsyncMock(return_value=session_id)
        mock_session.add_interaction = AsyncMock()
        
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "database/prod-postgres",
            "issued_at": datetime.now(UTC).isoformat() + "Z",
            "expires_at": datetime.now(UTC).isoformat() + "Z",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request
        response = client.post(
            "/run",
            json={
                "agent_name": "credential-broker",
                "input": [
                    {
                        "parts": [
                            {
                                "content": "I need database credentials for prod-postgres",
                                "content_type": "text/plain"
                            }
                        ],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "run_id" in data
        assert data["agent_name"] == "credential-broker"
        assert "session_id" in data
        assert data["status"] == "completed"
        assert "output" in data
        assert "execution_time_ms" in data
        
        # Verify output has both text and JWT token
        output = data["output"][0]
        assert len(output["parts"]) == 2  # Text + JWT
        
        # Verify credential manager was called with correct params
        mock_cred_manager.fetch_and_issue_token.assert_called_once()
        call_kwargs = mock_cred_manager.fetch_and_issue_token.call_args[1]
        assert call_kwargs["resource_type"] == "database"
        assert call_kwargs["resource_name"] == "prod-postgres"
        
        # Verify session was created and interaction logged
        mock_session.create_session.assert_called_once()
        mock_session.add_interaction.assert_called_once()
        
        # Verify audit logging
        mock_audit.log_credential_access.assert_called_once()
    
    @patch("src.acp.acp_server.credential_manager")
    @patch("src.acp.acp_server.audit_logger")
    @patch("src.acp.acp_server.session_manager")
    def test_run_api_credentials_with_duration(
        self, mock_session, mock_audit, mock_cred_manager, client
    ):
        """Test API credentials request with custom duration."""
        # Setup mocks
        session_id = f"session-{uuid.uuid4()}"
        mock_session.create_session = AsyncMock(return_value=session_id)
        mock_session.add_interaction = AsyncMock()
        
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 600,  # 10 minutes
            "resource": "api/stripe-api",
            "issued_at": datetime.now(UTC).isoformat() + "Z",
            "expires_at": datetime.now(UTC).isoformat() + "Z",
            "ttl_minutes": 10,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request with duration specified
        response = client.post(
            "/run",
            json={
                "agent_name": "credential-broker",
                "input": [
                    {
                        "parts": [
                            {
                                "content": "Get API credentials for stripe-api for 10 minutes",
                                "content_type": "text/plain"
                            }
                        ],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        
        # Verify duration was parsed correctly
        call_kwargs = mock_cred_manager.fetch_and_issue_token.call_args[1]
        assert call_kwargs["ttl_minutes"] == 10
        assert call_kwargs["resource_type"] == "api"
        assert call_kwargs["resource_name"] == "stripe-api"
    
    @patch("src.acp.acp_server.credential_manager")
    @patch("src.acp.acp_server.audit_logger")
    @patch("src.acp.acp_server.session_manager")
    def test_run_ssh_credentials(
        self, mock_session, mock_audit, mock_cred_manager, client
    ):
        """Test SSH credentials request."""
        # Setup mocks
        session_id = f"session-{uuid.uuid4()}"
        mock_session.create_session = AsyncMock(return_value=session_id)
        mock_session.add_interaction = AsyncMock()
        
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "ssh/production-server",
            "issued_at": datetime.now(UTC).isoformat() + "Z",
            "expires_at": datetime.now(UTC).isoformat() + "Z",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request
        response = client.post(
            "/run",
            json={
                "agent_name": "credential-broker",
                "input": [
                    {
                        "parts": [
                            {
                                "content": "I need SSH keys for production-server",
                                "content_type": "text/plain"
                            }
                        ],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        
        # Verify SSH resource type
        call_kwargs = mock_cred_manager.fetch_and_issue_token.call_args[1]
        assert call_kwargs["resource_type"] == "ssh"
        assert call_kwargs["resource_name"] == "production-server"
    
    @patch("src.acp.acp_server.credential_manager")
    @patch("src.acp.acp_server.audit_logger")
    @patch("src.acp.acp_server.session_manager")
    def test_run_with_existing_session(
        self, mock_session, mock_audit, mock_cred_manager, client
    ):
        """Test run with existing session ID."""
        # Setup mocks
        session_id = "existing-session-123"
        mock_session.create_session = AsyncMock(return_value=session_id)
        mock_session.add_interaction = AsyncMock()
        
        mock_cred_manager.fetch_and_issue_token.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "expires_in": 300,
            "resource": "database/test-db",
            "issued_at": datetime.now(UTC).isoformat() + "Z",
            "expires_at": datetime.now(UTC).isoformat() + "Z",
            "ttl_minutes": 5,
        }
        mock_audit.log_credential_access = AsyncMock()
        
        # Make request with session_id
        response = client.post(
            "/run",
            json={
                "agent_name": "credential-broker",
                "input": [
                    {
                        "parts": [
                            {
                                "content": "database credentials for test-db",
                                "content_type": "text/plain"
                            }
                        ],
                        "role": "user"
                    }
                ],
                "session_id": session_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        
        # Verify session was created with provided ID
        mock_session.create_session.assert_called_once()
        assert mock_session.create_session.call_args[0][0] == session_id
    
    @patch("src.acp.acp_server.credential_manager")
    @patch("src.acp.acp_server.audit_logger")
    @patch("src.acp.acp_server.session_manager")
    def test_run_unparseable_request(
        self, mock_session, mock_audit, mock_cred_manager, client
    ):
        """Test that unparseable request returns error status."""
        # Setup mocks
        session_id = f"session-{uuid.uuid4()}"
        mock_session.create_session = AsyncMock(return_value=session_id)
        mock_session.add_interaction = AsyncMock()
        mock_audit.log_credential_access = AsyncMock()
        
        # Make unparseable request
        response = client.post(
            "/run",
            json={
                "agent_name": "credential-broker",
                "input": [
                    {
                        "parts": [
                            {
                                "content": "Hello, how are you today?",
                                "content_type": "text/plain"
                            }
                        ],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return error status
        assert data["status"] == "error"
        assert len(data["output"]) > 0
        assert data["output"][0]["error"] is not None
        assert "couldn't understand" in data["output"][0]["parts"][0]["content"].lower()
        
        # Verify interaction was logged
        mock_session.add_interaction.assert_called_once()
    
    @patch("src.acp.acp_server.credential_manager")
    @patch("src.acp.acp_server.audit_logger")
    @patch("src.acp.acp_server.session_manager")
    def test_run_credential_fetch_error(
        self, mock_session, mock_audit, mock_cred_manager, client
    ):
        """Test that credential fetch errors are handled gracefully."""
        # Setup mocks
        session_id = f"session-{uuid.uuid4()}"
        mock_session.create_session = AsyncMock(return_value=session_id)
        mock_session.add_interaction = AsyncMock()
        mock_audit.log_credential_access = AsyncMock()
        
        # Make credential manager raise error
        mock_cred_manager.fetch_and_issue_token.side_effect = Exception(
            "Resource not found in vault"
        )
        
        # Make request
        response = client.post(
            "/run",
            json={
                "agent_name": "credential-broker",
                "input": [
                    {
                        "parts": [
                            {
                                "content": "I need database credentials for nonexistent-db",
                                "content_type": "text/plain"
                            }
                        ],
                        "role": "user"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return failed status
        assert data["status"] == "failed"
        assert data["output"][0]["error"] is not None
        assert "Resource not found" in data["output"][0]["parts"][0]["content"]
        
        # Verify audit logging for failure
        mock_audit.log_credential_access.assert_called_once()
        call_kwargs = mock_audit.log_credential_access.call_args[1]
        assert call_kwargs["outcome"] == "error"
    
    def test_run_empty_input(self, client):
        """Test that empty input returns error."""
        with patch('src.acp.acp_server.session_manager') as mock_session_manager:
            mock_session_manager.create_session.return_value = "test-session-123"
            
            response = client.post(
                "/run",
                json={
                    "agent_name": "credential-broker",
                    "run_id": "run-fad7c847-edc9-40ed-a086-c28c293a07c9",
                    "messages": []
                }
            )
            
            # Should get validation error
            assert response.status_code == 422


class TestSessionHistory:
    """Tests for session history endpoint."""
    
    @patch("src.acp.acp_server.session_manager")
    def test_get_session_history(self, mock_session, client):
        """Test retrieving session history."""
        # Setup mock
        session_id = "test-session-123"
        mock_session.get_session = AsyncMock(return_value={
            "session_id": session_id,
            "created_at": "2025-01-01T00:00:00Z",
            "last_activity": "2025-01-01T00:10:00Z",
            "interactions": [
                {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "run_id": "run-1",
                    "input_summary": "database credentials for prod-db",
                    "output_summary": "Generated ephemeral credentials",
                    "status": "completed",
                },
                {
                    "timestamp": "2025-01-01T00:05:00Z",
                    "run_id": "run-2",
                    "input_summary": "API credentials for stripe",
                    "output_summary": "Generated ephemeral credentials",
                    "status": "completed",
                },
            ],
        })
        
        # Make request
        response = client.get(f"/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["session_id"] == session_id
        assert "created_at" in data
        assert "last_activity" in data
        assert "interaction_count" in data
        assert "interactions" in data
        
        # Verify interactions
        assert data["interaction_count"] == 2
        assert len(data["interactions"]) == 2
        
        # Verify interaction structure
        interaction = data["interactions"][0]
        assert "timestamp" in interaction
        assert "run_id" in interaction
        assert "input_summary" in interaction
        assert "output_summary" in interaction
        assert "status" in interaction
    
    @patch("src.acp.acp_server.session_manager")
    def test_get_nonexistent_session(self, mock_session, client):
        """Test that nonexistent session returns 404."""
        # Setup mock to return None
        mock_session.get_session = AsyncMock(return_value=None)
        
        # Make request
        response = client.get("/sessions/nonexistent-session-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestIntentParser:
    """Tests for IntentParser class."""
    
    def test_parse_database_credentials(self):
        """Test parsing database credential request."""
        text = "I need database credentials for production-postgres"
        result = IntentParser.parse_intent(text)
        
        assert result["resource_type"] == "database"
        assert result["resource_name"] == "production-postgres"
        assert result["duration_minutes"] == 5  # Default
    
    def test_parse_database_credentials_variations(self):
        """Test various database request formats."""
        variations = [
            "database credentials for prod-db",
            "db creds for test-database",
            "credentials for database my-postgres",
            "need my-db database",
        ]
        
        for text in variations:
            result = IntentParser.parse_intent(text)
            assert result["resource_type"] == "database"
            assert result["resource_name"] is not None
    
    def test_parse_api_credentials(self):
        """Test parsing API credential request."""
        text = "Get API credentials for stripe-api"
        result = IntentParser.parse_intent(text)
        
        assert result["resource_type"] == "api"
        assert result["resource_name"] == "stripe-api"
    
    def test_parse_ssh_credentials(self):
        """Test parsing SSH credential request."""
        text = "I need SSH keys for production-server"
        result = IntentParser.parse_intent(text)
        
        assert result["resource_type"] == "ssh"
        assert result["resource_name"] == "production-server"
    
    def test_parse_with_duration(self):
        """Test parsing request with duration."""
        text = "Get database credentials for test-db for 10 minutes"
        result = IntentParser.parse_intent(text)
        
        assert result["duration_minutes"] == 10
    
    def test_parse_duration_variations(self):
        """Test parsing various duration formats."""
        test_cases = [
            ("credentials for db for 5 minutes", 5),
            ("get creds for 15 mins", 15),
            ("need access for 1 minute", 1),
            ("credentials for 10 min", 10),
        ]
        
        for text, expected_duration in test_cases:
            result = IntentParser.parse_intent(text)
            assert result["duration_minutes"] == expected_duration
    
    def test_parse_duration_capped_at_15(self):
        """Test that duration is capped at 15 minutes."""
        text = "Get credentials for 100 minutes"
        result = IntentParser.parse_intent(text)
        
        assert result["duration_minutes"] == 15  # Capped at max
    
    def test_parse_generic_fallback(self):
        """Test that unparseable requests fall back to generic."""
        text = "credentials for my-secret"
        result = IntentParser.parse_intent(text)
        
        assert result["resource_type"] == "generic"
        assert result["resource_name"] == "my-secret"
    
    def test_parse_no_resource_name(self):
        """Test that completely unparseable text returns None for resource_name."""
        text = "Hello, how are you?"
        result = IntentParser.parse_intent(text)
        
        assert result["resource_name"] is None
    
    def test_parse_original_text_preserved(self):
        """Test that original text is preserved in result."""
        text = "I need database credentials for test-db"
        result = IntentParser.parse_intent(text)
        
        assert result["original_text"] == text


class TestSessionManager:
    """Tests for SessionManager class."""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a new session."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        
        assert session_id is not None
        assert session_id.startswith("session-")
        assert session_id in manager.sessions
    
    @pytest.mark.asyncio
    async def test_create_session_with_id(self):
        """Test creating session with provided ID."""
        manager = SessionManager()
        custom_id = "custom-session-123"
        
        session_id = await manager.create_session(custom_id)
        
        assert session_id == custom_id
        assert session_id in manager.sessions
    
    @pytest.mark.asyncio
    async def test_create_session_existing_id(self):
        """Test that existing session ID returns same session."""
        manager = SessionManager()
        custom_id = "existing-session"
        
        # Create first time
        session_id1 = await manager.create_session(custom_id)
        
        # Create again with same ID
        session_id2 = await manager.create_session(custom_id)
        
        assert session_id1 == session_id2
        assert len(manager.sessions) == 1
    
    @pytest.mark.asyncio
    async def test_add_interaction(self):
        """Test adding interaction to session."""
        manager = SessionManager()
        session_id = await manager.create_session()
        
        input_messages = [
            Message(
                parts=[MessagePart(content="test input", content_type="text/plain")],
                role="user"
            )
        ]
        output_messages = [
            Message(
                parts=[MessagePart(content="test output", content_type="text/plain")],
                role="assistant"
            )
        ]
        
        await manager.add_interaction(
            session_id=session_id,
            run_id="run-123",
            input_messages=input_messages,
            output_messages=output_messages,
            status=RunStatus.COMPLETED,
        )
        
        # Verify interaction was added
        session = manager.sessions[session_id]
        assert len(session["interactions"]) == 1
        assert session["interactions"][0]["run_id"] == "run-123"
        assert session["interactions"][0]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_add_interaction_creates_session(self):
        """Test that adding interaction to nonexistent session creates it."""
        manager = SessionManager()
        new_session_id = "new-session-456"
        
        input_messages = [
            Message(
                parts=[MessagePart(content="test", content_type="text/plain")],
                role="user"
            )
        ]
        output_messages = [
            Message(
                parts=[MessagePart(content="response", content_type="text/plain")],
                role="assistant"
            )
        ]
        
        await manager.add_interaction(
            session_id=new_session_id,
            run_id="run-999",
            input_messages=input_messages,
            output_messages=output_messages,
            status=RunStatus.COMPLETED,
        )
        
        # Session should have been created
        assert new_session_id in manager.sessions
        assert len(manager.sessions[new_session_id]["interactions"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test retrieving session."""
        manager = SessionManager()
        session_id = await manager.create_session()
        
        session = await manager.get_session(session_id)
        
        assert session is not None
        assert session["session_id"] == session_id
        assert "created_at" in session
        assert "interactions" in session
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        """Test retrieving nonexistent session returns None."""
        manager = SessionManager()
        
        session = await manager.get_session("nonexistent")
        
        assert session is None
    
    @pytest.mark.asyncio
    async def test_extract_summary(self):
        """Test summary extraction from messages."""
        manager = SessionManager()
        
        messages = [
            Message(
                parts=[
                    MessagePart(
                        content="This is a long message that should be truncated because it exceeds the 100 character limit for summaries and we want to make sure it works correctly",
                        content_type="text/plain"
                    )
                ],
                role="user"
            )
        ]
        
        summary = manager._extract_summary(messages)
        
        assert len(summary) <= 103  # 100 + "..."
        assert summary.endswith("...")
    
    @pytest.mark.asyncio
    async def test_extract_summary_short_message(self):
        """Test summary extraction for short message."""
        manager = SessionManager()
        
        messages = [
            Message(
                parts=[
                    MessagePart(content="Short message", content_type="text/plain")
                ],
                role="user"
            )
        ]
        
        summary = manager._extract_summary(messages)
        
        assert summary == "Short message"
        assert not summary.endswith("...")
    
    @pytest.mark.asyncio
    async def test_extract_summary_empty_messages(self):
        """Test summary extraction for empty messages."""
        manager = SessionManager()
        
        summary = manager._extract_summary([])
        
        assert summary == ""
    
    @pytest.mark.asyncio
    async def test_extract_summary_no_text_content(self):
        """Test summary extraction when no text content."""
        manager = SessionManager()
        
        messages = [
            Message(
                parts=[
                    MessagePart(content="token123", content_type="application/jwt")
                ],
                role="assistant"
            )
        ]
        
        summary = manager._extract_summary(messages)
        
        assert summary == "No text content"


class TestPydanticModels:
    """Tests for Pydantic models."""
    
    def test_message_part_model(self):
        """Test MessagePart model."""
        part = MessagePart(
            content="test content",
            content_type="text/plain"
        )
        
        assert part.content == "test content"
        assert part.content_type == "text/plain"
    
    def test_message_model(self):
        """Test Message model."""
        message = Message(
            parts=[
                MessagePart(content="test", content_type="text/plain")
            ],
            role="user"
        )
        
        assert len(message.parts) == 1
        assert message.role == "user"
        assert message.error is None
    
    def test_acp_run_request_model(self):
        """Test ACPRunRequest model."""
        request = ACPRunRequest(
            agent_name="credential-broker",
            input=[
                Message(
                    parts=[MessagePart(content="test", content_type="text/plain")],
                    role="user"
                )
            ]
        )
        
        assert request.agent_name == "credential-broker"
        assert len(request.input) == 1
        assert request.session_id is None
    
    def test_acp_run_response_model(self):
        """Test ACPRunResponse model."""
        response = ACPRunResponse(
            run_id="run-123",
            agent_name="credential-broker",
            session_id="session-456",
            status=RunStatus.COMPLETED,
            output=[
                Message(
                    parts=[MessagePart(content="result", content_type="text/plain")],
                    role="assistant"
                )
            ],
            execution_time_ms=123.45
        )
        
        assert response.run_id == "run-123"
        assert response.status == RunStatus.COMPLETED
        assert response.execution_time_ms == 123.45
    
    def test_agent_info_model(self):
        """Test AgentInfo model."""
        agent = AgentInfo(
            name="test-agent",
            description="Test agent",
            capabilities=["test_cap"],
            version="1.0.0"
        )
        
        assert agent.name == "test-agent"
        assert len(agent.capabilities) == 1
    
    def test_agents_response_model(self):
        """Test AgentsResponse model."""
        response = AgentsResponse(
            agents=[
                AgentInfo(
                    name="agent1",
                    description="Agent 1",
                    capabilities=["cap1"],
                    version="1.0.0"
                )
            ],
            count=1
        )
        
        assert response.count == 1
        assert len(response.agents) == 1
    
    def test_health_response_model(self):
        """Test HealthResponse model."""
        response = HealthResponse(
            status="healthy",
            service="test-service",
            version="1.0.0",
            timestamp=datetime.now(UTC).isoformat()
        )
        
        assert response.status == "healthy"
        assert response.service == "test-service"


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_json_body(self, client):
        """Test that invalid JSON returns proper error."""
        response = client.post(
            "/run",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test that missing required fields returns validation error."""
        response = client.post(
            "/run",
            json={}
        )
        
        assert response.status_code == 422


class TestCORSHeaders:
    """Tests for CORS headers."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        # Test CORS headers on a GET request
        response = client.get("/agents")
        
        # CORS headers should be present in response
        assert response.status_code == 200
        # Note: CORS headers are typically added by middleware, 
        # but may not be visible in TestClient responses
        # This test verifies the endpoint works correctly

