"""
Unit tests for MCP Server
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from src.mcp.mcp_server import server, handle_list_tools, handle_call_tool, _handle_get_credentials


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns the get_credentials tool."""
    tools = await handle_list_tools()
    
    assert len(tools) == 1
    assert tools[0].name == "get_credentials"
    assert "ephemeral credentials" in tools[0].description.lower()
    
    # Verify input schema
    schema = tools[0].inputSchema
    assert schema["type"] == "object"
    assert "resource_type" in schema["properties"]
    assert "resource_name" in schema["properties"]
    assert "requesting_agent_id" in schema["properties"]
    assert "ttl_minutes" in schema["properties"]
    
    # Verify required fields
    assert "resource_type" in schema["required"]
    assert "resource_name" in schema["required"]
    assert "requesting_agent_id" in schema["required"]
    
    # Verify resource_type enum
    assert schema["properties"]["resource_type"]["enum"] == [
        "database", "api", "ssh", "generic"
    ]


@pytest.mark.asyncio
async def test_call_tool_unknown_tool():
    """Test that calling an unknown tool raises ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await handle_call_tool("unknown_tool", {})


@pytest.mark.asyncio
async def test_call_tool_success():
    """Test successful credential retrieval via MCP tool."""
    # Mock credential manager
    mock_credential_manager = Mock()
    
    # Mock fetch_credentials
    mock_credential_manager.fetch_credentials.return_value = {
        "username": "test_user",
        "password": "test_password",
        "host": "localhost",
        "port": "5432",
    }
    
    # Mock issue_ephemeral_token
    mock_credential_manager.issue_ephemeral_token.return_value = {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
        "expires_in": 300,
        "resource": "database/test-db",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Mock audit logger
    mock_audit_logger = Mock()
    mock_audit_logger.log_credential_access = AsyncMock()
    
    # Call the internal handler directly (no context var needed)
    result = await _handle_get_credentials(
        {
            "resource_type": "database",
            "resource_name": "test-db",
            "requesting_agent_id": "test-agent",
            "ttl_minutes": 5,
        },
        mock_credential_manager,
        mock_audit_logger,
    )
    
    # Verify the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert "✅" in result[0].text
    assert "test-db" in result[0].text
    
    # Verify credential manager was called correctly
    mock_credential_manager.fetch_credentials.assert_called_once_with(
        resource_type="database",
        resource_name="test-db",
    )
    
    mock_credential_manager.issue_ephemeral_token.assert_called_once()
    call_kwargs = mock_credential_manager.issue_ephemeral_token.call_args[1]
    assert call_kwargs["agent_id"] == "test-agent"
    assert call_kwargs["resource_type"] == "database"
    assert call_kwargs["resource_name"] == "test-db"
    assert call_kwargs["ttl_minutes"] == 5
    
    # Verify audit logging was called
    mock_audit_logger.log_credential_access.assert_called_once()
    log_call = mock_audit_logger.log_credential_access.call_args[1]
    assert log_call["protocol"] == "MCP"
    assert log_call["agent_id"] == "test-agent"
    assert log_call["resource"] == "database/test-db"
    assert log_call["outcome"] == "success"


@pytest.mark.asyncio
async def test_call_tool_validation_error():
    """Test that validation errors are handled gracefully."""
    # Mock credential manager
    mock_credential_manager = Mock()
    
    # Mock fetch_credentials to raise ValueError
    mock_credential_manager.fetch_credentials.side_effect = ValueError(
        "Invalid resource_type"
    )
    
    # Mock audit logger
    mock_audit_logger = Mock()
    mock_audit_logger.log_credential_access = AsyncMock()
    
    # Call the internal handler directly
    result = await _handle_get_credentials(
        {
            "resource_type": "invalid_type",
            "resource_name": "test-db",
            "requesting_agent_id": "test-agent",
            "ttl_minutes": 5,
        },
        mock_credential_manager,
        mock_audit_logger,
    )
    
    # Verify error response
    assert len(result) == 1
    assert result[0].type == "text"
    assert "❌" in result[0].text
    assert "Validation error" in result[0].text
    
    # Verify audit logging for failure
    mock_audit_logger.log_credential_access.assert_called_once()
    log_call = mock_audit_logger.log_credential_access.call_args[1]
    assert log_call["outcome"] == "failure"


@pytest.mark.asyncio
async def test_call_tool_unexpected_error():
    """Test that unexpected errors are handled gracefully."""
    # Mock credential manager
    mock_credential_manager = Mock()
    
    # Mock fetch_credentials to raise unexpected error
    mock_credential_manager.fetch_credentials.side_effect = Exception(
        "Unexpected error"
    )
    
    # Mock audit logger
    mock_audit_logger = Mock()
    mock_audit_logger.log_credential_access = AsyncMock()
    
    # Call the internal handler directly
    result = await _handle_get_credentials(
        {
            "resource_type": "database",
            "resource_name": "test-db",
            "requesting_agent_id": "test-agent",
            "ttl_minutes": 5,
        },
        mock_credential_manager,
        mock_audit_logger,
    )
    
    # Verify error response
    assert len(result) == 1
    assert result[0].type == "text"
    assert "❌" in result[0].text
    assert "Error retrieving credentials" in result[0].text
    
    # Verify audit logging for error
    mock_audit_logger.log_credential_access.assert_called_once()
    log_call = mock_audit_logger.log_credential_access.call_args[1]
    assert log_call["outcome"] == "error"


@pytest.mark.asyncio
async def test_call_tool_custom_ttl():
    """Test credential retrieval with custom TTL."""
    # Mock credential manager
    mock_credential_manager = Mock()
    
    # Mock fetch_credentials
    mock_credential_manager.fetch_credentials.return_value = {
        "api_key": "test_key",
    }
    
    # Mock issue_ephemeral_token
    mock_credential_manager.issue_ephemeral_token.return_value = {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
        "expires_in": 600,  # 10 minutes
        "resource": "api/test-api",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Mock audit logger
    mock_audit_logger = Mock()
    mock_audit_logger.log_credential_access = AsyncMock()
    
    # Call the internal handler directly
    result = await _handle_get_credentials(
        {
            "resource_type": "api",
            "resource_name": "test-api",
            "requesting_agent_id": "test-agent",
            "ttl_minutes": 10,
        },
        mock_credential_manager,
        mock_audit_logger,
    )
    
    # Verify the token TTL was passed correctly
    call_kwargs = mock_credential_manager.issue_ephemeral_token.call_args[1]
    assert call_kwargs["ttl_minutes"] == 10
    
    # Verify audit log includes TTL metadata
    log_call = mock_audit_logger.log_credential_access.call_args[1]
    assert log_call["metadata"]["ttl_minutes"] == 10

