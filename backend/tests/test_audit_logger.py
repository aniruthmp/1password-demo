"""
Unit tests for AuditLogger
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.core.audit_logger import (
    AuditLogger,
    EventOutcome,
    Protocol,
    create_audit_logger_from_env,
)


@pytest.fixture
def audit_logger():
    """Create AuditLogger instance for testing."""
    return AuditLogger(
        events_api_url="https://events.test.com/api/v1",
        events_api_token="test-token",
        enable_local_fallback=True,
        local_log_file="/tmp/test_audit.log",
    )


@pytest.fixture
def audit_logger_no_api():
    """Create AuditLogger without Events API configured."""
    return AuditLogger(
        events_api_url=None, events_api_token=None, enable_local_fallback=True
    )


class TestEnums:
    """Tests for enum definitions."""

    def test_event_outcome_values(self):
        """Test EventOutcome enum has expected values."""
        assert EventOutcome.SUCCESS.value == "success"
        assert EventOutcome.FAILURE.value == "failure"
        assert EventOutcome.DENIED.value == "denied"
        assert EventOutcome.ERROR.value == "error"

    def test_protocol_values(self):
        """Test Protocol enum has expected values."""
        assert Protocol.MCP.value == "mcp"
        assert Protocol.A2A.value == "a2a"
        assert Protocol.ACP.value == "acp"


class TestAuditLoggerInit:
    """Tests for AuditLogger initialization."""

    def test_init_with_params(self):
        """Test initialization with explicit parameters."""
        logger = AuditLogger(
            events_api_url="https://events.example.com",
            events_api_token="my-token",
            max_retries=5,
            retry_delay=2.0,
            enable_local_fallback=True,
            local_log_file="/tmp/audit.log",
        )

        assert logger.events_api_url == "https://events.example.com"
        assert logger.events_api_token == "my-token"
        assert logger.max_retries == 5
        assert logger.retry_delay == 2.0
        assert logger.enable_local_fallback is True
        assert logger.events_api_enabled is True

    def test_init_with_env_vars(self, monkeypatch):
        """Test initialization with environment variables."""
        monkeypatch.setenv("EVENTS_API_URL", "https://env-events.com")
        monkeypatch.setenv("EVENTS_API_TOKEN", "env-token")

        logger = AuditLogger()

        assert logger.events_api_url == "https://env-events.com"
        assert logger.events_api_token == "env-token"
        assert logger.events_api_enabled is True

    def test_init_without_api_config(self, caplog):
        """Test initialization without Events API configuration."""
        logger = AuditLogger(events_api_url=None, events_api_token=None)

        assert logger.events_api_enabled is False
        assert "Events API not configured" in caplog.text

    def test_init_creates_log_directory(self, tmp_path):
        """Test initialization creates log directory if it doesn't exist."""
        log_file = tmp_path / "subdir" / "audit.log"

        AuditLogger(enable_local_fallback=True, local_log_file=str(log_file))

        assert log_file.parent.exists()


class TestEventPayloadCreation:
    """Tests for event payload creation."""

    def test_create_event_payload(self, audit_logger):
        """Test creating structured event payload."""
        event = audit_logger._create_event_payload(
            event_type="credential_access",
            protocol="mcp",
            agent_id="test-agent",
            resource="database/prod-db",
            outcome="success",
        )

        assert event["event_type"] == "credential_access"
        assert event["protocol"] == "mcp"
        assert event["agent_id"] == "test-agent"
        assert event["resource"] == "database/prod-db"
        assert event["outcome"] == "success"
        assert event["source"] == "1password-credential-broker"
        assert event["version"] == "1.0.0"
        assert "timestamp" in event

    def test_create_event_payload_with_metadata(self, audit_logger):
        """Test creating event payload with metadata."""
        metadata = {"ttl_minutes": 5, "request_id": "12345"}

        event = audit_logger._create_event_payload(
            event_type="token_generation",
            protocol="a2a",
            agent_id="test-agent",
            resource="api/api-key",
            outcome="success",
            metadata=metadata,
        )

        assert event["metadata"] == metadata
        assert event["metadata"]["ttl_minutes"] == 5


class TestLocalLogging:
    """Tests for local file logging."""

    def test_log_event_locally(self, audit_logger, tmp_path):
        """Test logging event to local file."""
        log_file = tmp_path / "test.log"
        audit_logger.local_log_file = str(log_file)
        audit_logger.enable_local_fallback = True

        event = {"event_type": "test_event", "timestamp": datetime.now(UTC).isoformat()}

        audit_logger._log_event_locally(event)

        assert log_file.exists()
        content = log_file.read_text()
        assert "test_event" in content

    def test_log_event_locally_disabled(self, audit_logger):
        """Test local logging is skipped when disabled."""
        audit_logger.enable_local_fallback = False

        event = {"test": "data"}

        # Should not raise error even if file doesn't exist
        audit_logger._log_event_locally(event)

    def test_log_event_locally_handles_errors(self, audit_logger, caplog):
        """Test local logging handles write errors gracefully."""
        audit_logger.local_log_file = "/invalid/path/audit.log"
        audit_logger.enable_local_fallback = True

        event = {"test": "data"}

        audit_logger._log_event_locally(event)

        assert "Failed to log event locally" in caplog.text


class TestEventsAPIPosting:
    """Tests for Events API event posting."""

    @pytest.mark.asyncio
    async def test_post_event_success(self, audit_logger):
        """Test successful event posting to API."""
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        audit_logger.http_client = mock_client

        event = {"event_type": "test_event"}
        result = await audit_logger._post_event_to_api(event)

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_event_api_error(self, audit_logger):
        """Test event posting handles API errors."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection error")

        audit_logger.http_client = mock_client
        audit_logger.max_retries = 0  # Disable retries for this test

        event = {"event_type": "test_event"}
        result = await audit_logger._post_event_to_api(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_post_event_retry_logic(self, audit_logger):
        """Test event posting retry with exponential backoff."""
        mock_client = AsyncMock()
        # Fail first attempt, succeed on second
        mock_client.post.side_effect = [Exception("Timeout"), Mock(status_code=200)]

        audit_logger.http_client = mock_client
        audit_logger.max_retries = 2
        audit_logger.retry_delay = 0.01  # Fast retry for testing

        event = {"event_type": "test_event"}
        result = await audit_logger._post_event_to_api(event)

        assert result is True
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_post_event_no_api_configured(self, audit_logger_no_api):
        """Test event posting returns False when API not configured."""
        event = {"event_type": "test_event"}
        result = await audit_logger_no_api._post_event_to_api(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_post_event_bad_status_code(self, audit_logger):
        """Test event posting handles non-success status codes."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        audit_logger.http_client = mock_client
        audit_logger.max_retries = 0

        event = {"event_type": "test_event"}
        result = await audit_logger._post_event_to_api(event)

        assert result is False


class TestCredentialAccessLogging:
    """Tests for log_credential_access method."""

    @pytest.mark.asyncio
    async def test_log_credential_access_success(self, audit_logger, tmp_path):
        """Test logging credential access event."""
        log_file = tmp_path / "audit.log"
        audit_logger.local_log_file = str(log_file)

        mock_client = AsyncMock()
        mock_client.post.return_value = Mock(status_code=200)
        audit_logger.http_client = mock_client

        await audit_logger.log_credential_access(
            protocol="mcp",
            agent_id="test-agent",
            resource="database/prod-db",
            outcome="success",
        )

        # Check local log
        assert log_file.exists()
        content = log_file.read_text()
        assert "credential_access" in content
        assert "test-agent" in content

        # Check API call
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_credential_access_with_metadata(self, audit_logger, tmp_path):
        """Test logging credential access with metadata."""
        log_file = tmp_path / "audit.log"
        audit_logger.local_log_file = str(log_file)

        mock_client = AsyncMock()
        mock_client.post.return_value = Mock(status_code=200)
        audit_logger.http_client = mock_client

        metadata = {"error": "Permission denied"}

        await audit_logger.log_credential_access(
            protocol="a2a",
            agent_id="test-agent",
            resource="api/secret-key",
            outcome="denied",
            metadata=metadata,
        )

        content = log_file.read_text()
        assert "Permission denied" in content

    @pytest.mark.asyncio
    async def test_log_credential_access_api_failure_queues_event(self, audit_logger):
        """Test failed API post queues event for retry."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        audit_logger.http_client = mock_client
        audit_logger.max_retries = 0

        await audit_logger.log_credential_access(
            protocol="mcp",
            agent_id="test-agent",
            resource="database/test-db",
            outcome="success",
        )

        assert audit_logger.get_queue_size() == 1


class TestTokenLogging:
    """Tests for token generation and validation logging."""

    @pytest.mark.asyncio
    async def test_log_token_generation(self, audit_logger, tmp_path):
        """Test logging token generation event."""
        log_file = tmp_path / "audit.log"
        audit_logger.local_log_file = str(log_file)

        mock_client = AsyncMock()
        mock_client.post.return_value = Mock(status_code=200)
        audit_logger.http_client = mock_client

        await audit_logger.log_token_generation(
            protocol="a2a",
            agent_id="test-agent",
            resource="ssh/prod-server",
            ttl_minutes=10,
        )

        content = log_file.read_text()
        assert "token_generation" in content
        assert "10" in content  # TTL

    @pytest.mark.asyncio
    async def test_log_token_validation_success(self, audit_logger, tmp_path):
        """Test logging successful token validation."""
        log_file = tmp_path / "audit.log"
        audit_logger.local_log_file = str(log_file)

        mock_client = AsyncMock()
        mock_client.post.return_value = Mock(status_code=200)
        audit_logger.http_client = mock_client

        await audit_logger.log_token_validation(
            protocol="acp", agent_id="test-agent", success=True
        )

        content = log_file.read_text()
        assert "token_validation" in content
        assert "success" in content

    @pytest.mark.asyncio
    async def test_log_token_validation_failure(self, audit_logger, tmp_path):
        """Test logging failed token validation."""
        log_file = tmp_path / "audit.log"
        audit_logger.local_log_file = str(log_file)

        mock_client = AsyncMock()
        mock_client.post.return_value = Mock(status_code=200)
        audit_logger.http_client = mock_client

        metadata = {"error": "Token expired"}

        await audit_logger.log_token_validation(
            protocol="mcp", agent_id="test-agent", success=False, metadata=metadata
        )

        content = log_file.read_text()
        assert "failure" in content


class TestRetryMechanism:
    """Tests for failed event retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_failed_events_success(self, audit_logger):
        """Test retrying failed events successfully."""
        # Add events to queue with proper structure
        audit_logger.failed_events_queue.append({"event_type": "test_event_1"})
        audit_logger.failed_events_queue.append({"event_type": "test_event_2"})

        mock_client = AsyncMock()
        mock_client.post.return_value = Mock(status_code=200)
        audit_logger.http_client = mock_client

        successful = await audit_logger.retry_failed_events()

        assert successful == 2
        assert audit_logger.get_queue_size() == 0

    @pytest.mark.asyncio
    async def test_retry_failed_events_partial_success(self, audit_logger):
        """Test retrying failed events with partial success."""
        audit_logger.failed_events_queue.append({"event_type": "test_event_1"})
        audit_logger.failed_events_queue.append({"event_type": "test_event_2"})

        mock_client = AsyncMock()
        # First succeeds, second fails
        mock_client.post.side_effect = [Mock(status_code=200), Exception("API Error")]
        audit_logger.http_client = mock_client
        audit_logger.max_retries = 0

        successful = await audit_logger.retry_failed_events()

        assert successful == 1
        assert audit_logger.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_retry_failed_events_empty_queue(self, audit_logger):
        """Test retrying with empty queue."""
        successful = await audit_logger.retry_failed_events()

        assert successful == 0


class TestHTTPClientManagement:
    """Tests for HTTP client management."""

    @pytest.mark.asyncio
    async def test_get_http_client_creates_client(self, audit_logger):
        """Test HTTP client is created on first access."""
        assert audit_logger.http_client is None

        client = await audit_logger._get_http_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_get_http_client_reuses_client(self, audit_logger):
        """Test HTTP client is reused on subsequent calls."""
        client1 = await audit_logger._get_http_client()
        client2 = await audit_logger._get_http_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_client(self, audit_logger):
        """Test closing HTTP client."""
        await audit_logger._get_http_client()
        assert audit_logger.http_client is not None

        await audit_logger.close()

        assert audit_logger.http_client is None


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_get_queue_size(self, audit_logger):
        """Test getting failed events queue size."""
        assert audit_logger.get_queue_size() == 0

        audit_logger.failed_events_queue.append({"event": "1"})
        audit_logger.failed_events_queue.append({"event": "2"})

        assert audit_logger.get_queue_size() == 2

    def test_get_stats(self, audit_logger):
        """Test getting audit logger statistics."""
        audit_logger.failed_events_queue.append({"event": "1"})

        stats = audit_logger.get_stats()

        assert stats["events_api_enabled"] is True
        assert stats["failed_queue_size"] == 1
        assert stats["local_fallback_enabled"] is True
        assert "/tmp/test_audit.log" in stats["local_log_file"]


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_audit_logger_from_env(self, monkeypatch):
        """Test convenience function to create logger from environment."""
        monkeypatch.setenv("EVENTS_API_URL", "https://events.env.com")
        monkeypatch.setenv("EVENTS_API_TOKEN", "env-token")

        logger = create_audit_logger_from_env()

        assert isinstance(logger, AuditLogger)
        assert logger.events_api_url == "https://events.env.com"


class TestQueueLimits:
    """Tests for queue size limits."""

    @pytest.mark.asyncio
    async def test_queue_max_size(self, audit_logger):
        """Test queue respects maximum size."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        audit_logger.http_client = mock_client
        audit_logger.max_retries = 0

        # Add more events than max queue size (1000)
        for i in range(1100):
            await audit_logger.log_credential_access(
                protocol="mcp",
                agent_id=f"agent-{i}",
                resource="test",
                outcome="success",
            )

        # Queue should be capped at 1000
        assert audit_logger.get_queue_size() == 1000
