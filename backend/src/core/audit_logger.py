"""
Audit Logger with 1Password Events API Integration
Handles structured logging and event reporting for credential access tracking.
"""

import asyncio
import json
import logging
import os
from collections import deque
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EventOutcome(str, Enum):
    """Possible outcomes for credential access events."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"


class Protocol(str, Enum):
    """Supported protocols."""

    MCP = "mcp"
    A2A = "a2a"
    ACP = "acp"


class AuditLogger:
    """
    Audit logger for credential access events.

    Features:
    - Structured JSON logging
    - 1Password Events API integration
    - Async event posting with retry logic
    - Local queue for failed deliveries
    - Exponential backoff for retries
    """

    def __init__(
        self,
        events_api_url: str | None = None,
        events_api_token: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_local_fallback: bool = True,
        local_log_file: str = "logs/audit.log",
    ):
        """
        Initialize AuditLogger.

        Args:
            events_api_url: 1Password Events API URL (defaults to EVENTS_API_URL env)
            events_api_token: Events API token (defaults to EVENTS_API_TOKEN env)
            max_retries: Maximum retry attempts for failed event posts
            retry_delay: Initial retry delay in seconds (exponential backoff)
            enable_local_fallback: Enable local file logging as fallback
            local_log_file: Path to local audit log file
        """
        self.events_api_url = events_api_url or os.getenv("EVENTS_API_URL")
        self.events_api_token = events_api_token or os.getenv("EVENTS_API_TOKEN")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_local_fallback = enable_local_fallback
        self.local_log_file = local_log_file

        # Queue for failed events
        self.failed_events_queue: deque = deque(maxlen=1000)

        # HTTP client for async requests
        self.http_client: httpx.AsyncClient | None = None

        # Check if Events API is configured
        self.events_api_enabled = bool(self.events_api_url and self.events_api_token)

        if not self.events_api_enabled:
            logger.warning(
                "1Password Events API not configured. "
                "Events will only be logged locally."
            )
        else:
            logger.info(f"1Password Events API enabled: {self.events_api_url}")

        # Ensure local log directory exists
        if self.enable_local_fallback:
            import pathlib

            pathlib.Path(local_log_file).parent.mkdir(parents=True, exist_ok=True)

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.http_client is None:
            headers = {}
            if self.events_api_token:
                headers["Authorization"] = f"Bearer {self.events_api_token}"

            self.http_client = httpx.AsyncClient(
                headers=headers,
                timeout=10.0,
            )
        return self.http_client

    async def close(self):
        """Close HTTP client and cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    def _create_event_payload(
        self,
        event_type: str,
        protocol: str,
        agent_id: str,
        resource: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create structured event payload.

        Args:
            event_type: Type of event (credential_access, token_generation, etc.)
            protocol: Protocol used (mcp, a2a, acp)
            agent_id: Agent identifier
            resource: Resource identifier
            outcome: Event outcome (success, failure, etc.)
            metadata: Additional metadata

        Returns:
            Structured event dictionary
        """
        event = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "event_type": event_type,
            "protocol": protocol,
            "agent_id": agent_id,
            "resource": resource,
            "outcome": outcome,
            "source": "1password-credential-broker",
            "version": "1.0.0",
        }

        if metadata:
            event["metadata"] = metadata

        return event

    async def _post_event_to_api(
        self,
        event: dict[str, Any],
        retry_count: int = 0,
    ) -> bool:
        """
        Post event to 1Password Events API with retry logic.

        Args:
            event: Event payload
            retry_count: Current retry attempt

        Returns:
            True if successful, False otherwise
        """
        if not self.events_api_enabled:
            return False

        try:
            client = await self._get_http_client()
            response = await client.post(
                f"{self.events_api_url}/events",
                json=event,
            )

            if response.status_code in (200, 201, 202):
                logger.debug(f"Event posted to Events API: {event['event_type']}")
                return True
            else:
                logger.warning(
                    f"Events API returned {response.status_code}: {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to post event to API: {e}")

            # Retry with exponential backoff
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2**retry_count)
                logger.info(
                    f"Retrying event post in {delay}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                await asyncio.sleep(delay)
                return await self._post_event_to_api(event, retry_count + 1)

            return False

    def _log_event_locally(self, event: dict[str, Any]):
        """
        Log event to local file as fallback.

        Args:
            event: Event payload
        """
        if not self.enable_local_fallback:
            return

        try:
            with open(self.local_log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
            logger.debug(f"Event logged locally: {event['event_type']}")
        except Exception as e:
            logger.error(f"Failed to log event locally: {e}")

    async def log_credential_access(
        self,
        protocol: str,
        agent_id: str,
        resource: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Log a credential access event.

        Args:
            protocol: Protocol used (mcp, a2a, acp)
            agent_id: Agent identifier
            resource: Resource identifier (e.g., "database/prod-postgres")
            outcome: Event outcome (success, failure, denied, error)
            metadata: Additional metadata (e.g., error details)
        """
        event = self._create_event_payload(
            event_type="credential_access",
            protocol=protocol,
            agent_id=agent_id,
            resource=resource,
            outcome=outcome,
            metadata=metadata,
        )

        # Log locally first (always)
        self._log_event_locally(event)

        # Log structured message
        logger.info(
            f"AUDIT: credential_access | protocol={protocol} | "
            f"agent={agent_id} | resource={resource} | outcome={outcome}"
        )

        # Post to Events API (async, non-blocking)
        success = await self._post_event_to_api(event)
        if not success:
            self.failed_events_queue.append(event)
            logger.warning(
                f"Event queued for retry ({len(self.failed_events_queue)} in queue)"
            )

    async def log_token_generation(
        self,
        protocol: str,
        agent_id: str,
        resource: str,
        ttl_minutes: int,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Log a token generation event.

        Args:
            protocol: Protocol used
            agent_id: Agent identifier
            resource: Resource identifier
            ttl_minutes: Token TTL in minutes
            metadata: Additional metadata
        """
        event_metadata = {"ttl_minutes": ttl_minutes}
        if metadata:
            event_metadata.update(metadata)

        event = self._create_event_payload(
            event_type="token_generation",
            protocol=protocol,
            agent_id=agent_id,
            resource=resource,
            outcome=EventOutcome.SUCCESS.value,
            metadata=event_metadata,
        )

        # Log locally
        self._log_event_locally(event)

        # Log structured message
        logger.info(
            f"AUDIT: token_generation | protocol={protocol} | "
            f"agent={agent_id} | resource={resource} | ttl={ttl_minutes}min"
        )

        # Post to Events API
        success = await self._post_event_to_api(event)
        if not success:
            self.failed_events_queue.append(event)

    async def log_token_validation(
        self,
        protocol: str,
        agent_id: str,
        success: bool,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Log a token validation attempt.

        Args:
            protocol: Protocol used
            agent_id: Agent identifier
            success: Whether validation succeeded
            metadata: Additional metadata (e.g., error reason)
        """
        outcome = EventOutcome.SUCCESS.value if success else EventOutcome.FAILURE.value

        event = self._create_event_payload(
            event_type="token_validation",
            protocol=protocol,
            agent_id=agent_id,
            resource="token_validation",
            outcome=outcome,
            metadata=metadata,
        )

        # Log locally
        self._log_event_locally(event)

        # Log structured message
        logger.info(
            f"AUDIT: token_validation | protocol={protocol} | "
            f"agent={agent_id} | success={success}"
        )

        # Post to Events API
        success = await self._post_event_to_api(event)
        if not success:
            self.failed_events_queue.append(event)

    async def retry_failed_events(self) -> int:
        """
        Retry posting failed events from the queue.

        Returns:
            Number of events successfully posted
        """
        if not self.failed_events_queue:
            return 0

        logger.info(f"Retrying {len(self.failed_events_queue)} failed events...")

        successful = 0
        failed_again = []

        while self.failed_events_queue:
            event = self.failed_events_queue.popleft()
            success = await self._post_event_to_api(event)

            if success:
                successful += 1
            else:
                failed_again.append(event)

        # Re-queue events that failed again
        for event in failed_again:
            self.failed_events_queue.append(event)

        logger.info(
            f"Retry complete: {successful} succeeded, "
            f"{len(failed_again)} still queued"
        )

        return successful

    def get_queue_size(self) -> int:
        """Get the number of events waiting in the retry queue."""
        return len(self.failed_events_queue)

    def get_stats(self) -> dict[str, Any]:
        """
        Get audit logger statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "events_api_enabled": self.events_api_enabled,
            "failed_queue_size": len(self.failed_events_queue),
            "local_fallback_enabled": self.enable_local_fallback,
            "local_log_file": self.local_log_file,
        }


# Convenience function for creating logger from environment
def create_audit_logger_from_env() -> AuditLogger:
    """
    Create an AuditLogger using environment variables.

    Returns:
        Configured AuditLogger instance
    """
    return AuditLogger()
