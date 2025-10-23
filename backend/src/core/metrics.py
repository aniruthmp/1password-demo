"""
Metrics Collection System
Tracks key performance indicators and operational metrics across all protocols.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """A snapshot of metrics at a point in time."""

    timestamp: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    active_tokens: int
    total_tokens_generated: int
    avg_token_ttl_minutes: float
    avg_response_time_ms: float
    protocol_breakdown: dict[str, int] = field(default_factory=dict)
    resource_type_breakdown: dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """
    Centralized metrics collection for the credential broker.

    Tracks:
    - Request counts (total, success, failure)
    - Token generation statistics
    - Response times
    - Protocol usage breakdown
    - Resource type distribution
    """

    def __init__(self):
        """Initialize the metrics collector."""
        self._lock = Lock()

        # Request metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0

        # Token metrics
        self._active_tokens = 0
        self._total_tokens_generated = 0
        self._token_ttl_sum = 0.0  # Sum of all token TTLs for average calculation

        # Timing metrics
        self._response_times = []  # List of response times in milliseconds
        self._max_response_times = 1000  # Keep last 1000 response times

        # Protocol breakdown
        self._protocol_counts = defaultdict(int)  # Protocol -> count

        # Resource type breakdown
        self._resource_type_counts = defaultdict(int)  # Resource type -> count

        # Startup time
        self._startup_time = datetime.now(UTC)

        logger.info("MetricsCollector initialized")

    def record_request(
        self,
        protocol: str,
        resource_type: str,
        success: bool,
        response_time_ms: float,
    ) -> None:
        """
        Record a credential request.

        Args:
            protocol: Protocol used (mcp, a2a, acp)
            resource_type: Type of resource requested
            success: Whether the request succeeded
            response_time_ms: Response time in milliseconds
        """
        with self._lock:
            self._total_requests += 1

            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

            # Update protocol counts
            self._protocol_counts[protocol.lower()] += 1

            # Update resource type counts
            self._resource_type_counts[resource_type.lower()] += 1

            # Record response time
            self._response_times.append(response_time_ms)
            if len(self._response_times) > self._max_response_times:
                self._response_times.pop(0)

        logger.debug(
            f"Recorded request: protocol={protocol}, resource_type={resource_type}, "
            f"success={success}, response_time_ms={response_time_ms:.2f}"
        )

    def record_token_generation(self, ttl_minutes: int) -> None:
        """
        Record a token generation event.

        Args:
            ttl_minutes: Token time-to-live in minutes
        """
        with self._lock:
            self._active_tokens += 1
            self._total_tokens_generated += 1
            self._token_ttl_sum += ttl_minutes

        logger.debug(f"Recorded token generation: ttl_minutes={ttl_minutes}")

    def record_token_expiration(self) -> None:
        """Record a token expiration event."""
        with self._lock:
            if self._active_tokens > 0:
                self._active_tokens -= 1

        logger.debug("Recorded token expiration")

    def get_snapshot(self) -> MetricSnapshot:
        """
        Get a snapshot of current metrics.

        Returns:
            MetricSnapshot with current metrics
        """
        with self._lock:
            # Calculate average token TTL
            avg_ttl = (
                self._token_ttl_sum / self._total_tokens_generated
                if self._total_tokens_generated > 0
                else 0.0
            )

            # Calculate average response time
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times
                else 0.0
            )

            snapshot = MetricSnapshot(
                timestamp=datetime.now(UTC),
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
                active_tokens=self._active_tokens,
                total_tokens_generated=self._total_tokens_generated,
                avg_token_ttl_minutes=avg_ttl,
                avg_response_time_ms=avg_response_time,
                protocol_breakdown=dict(self._protocol_counts),
                resource_type_breakdown=dict(self._resource_type_counts),
            )

        return snapshot

    def get_metrics_dict(self) -> dict[str, Any]:
        """
        Get metrics as a dictionary for JSON serialization.

        Returns:
            Dictionary of metrics
        """
        snapshot = self.get_snapshot()
        uptime = datetime.now(UTC) - self._startup_time

        # Calculate success rate
        success_rate = (
            (snapshot.successful_requests / snapshot.total_requests * 100)
            if snapshot.total_requests > 0
            else 0.0
        )

        return {
            "timestamp": snapshot.timestamp.isoformat() + "Z",
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime).split(".")[0],  # Remove microseconds
            "requests": {
                "total": snapshot.total_requests,
                "successful": snapshot.successful_requests,
                "failed": snapshot.failed_requests,
                "success_rate_percent": round(success_rate, 2),
            },
            "tokens": {
                "active": snapshot.active_tokens,
                "total_generated": snapshot.total_tokens_generated,
                "avg_ttl_minutes": round(snapshot.avg_token_ttl_minutes, 2),
            },
            "performance": {
                "avg_response_time_ms": round(snapshot.avg_response_time_ms, 2),
            },
            "protocols": snapshot.protocol_breakdown,
            "resource_types": snapshot.resource_type_breakdown,
        }

    def get_health_status(self) -> dict[str, Any]:
        """
        Get health status based on metrics.

        Returns:
            Dictionary with health status
        """
        snapshot = self.get_snapshot()

        # Determine health status
        status = "healthy"
        issues = []

        # Check success rate (warn if below 95%)
        if snapshot.total_requests > 10:
            success_rate = snapshot.successful_requests / snapshot.total_requests
            if success_rate < 0.95:
                status = "degraded"
                issues.append(
                    f"Low success rate: {success_rate * 100:.1f}% (expected >95%)"
                )

        # Check average response time (warn if above 1000ms)
        if snapshot.avg_response_time_ms > 1000:
            if status == "healthy":
                status = "degraded"
            issues.append(
                f"High response time: {snapshot.avg_response_time_ms:.1f}ms (expected <1000ms)"
            )

        return {
            "status": status,
            "timestamp": snapshot.timestamp.isoformat() + "Z",
            "issues": issues if issues else None,
            "metrics": {
                "total_requests": snapshot.total_requests,
                "success_rate": (
                    f"{snapshot.successful_requests / snapshot.total_requests * 100:.1f}%"
                    if snapshot.total_requests > 0
                    else "N/A"
                ),
                "active_tokens": snapshot.active_tokens,
                "avg_response_time_ms": round(snapshot.avg_response_time_ms, 2),
            },
        }

    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._active_tokens = 0
            self._total_tokens_generated = 0
            self._token_ttl_sum = 0.0
            self._response_times.clear()
            self._protocol_counts.clear()
            self._resource_type_counts.clear()
            self._startup_time = datetime.now(UTC)

        logger.info("Metrics reset")


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Returns:
        MetricsCollector singleton
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_request_metrics(
    protocol: str,
    resource_type: str,
    success: bool,
    response_time_ms: float,
) -> None:
    """
    Convenience function to record request metrics.

    Args:
        protocol: Protocol used
        resource_type: Type of resource
        success: Whether request succeeded
        response_time_ms: Response time in milliseconds
    """
    collector = get_metrics_collector()
    collector.record_request(protocol, resource_type, success, response_time_ms)


def record_token_metrics(ttl_minutes: int) -> None:
    """
    Convenience function to record token generation.

    Args:
        ttl_minutes: Token TTL in minutes
    """
    collector = get_metrics_collector()
    collector.record_token_generation(ttl_minutes)


def get_current_metrics() -> dict[str, Any]:
    """
    Convenience function to get current metrics.

    Returns:
        Dictionary of current metrics
    """
    collector = get_metrics_collector()
    return collector.get_metrics_dict()


def get_health_metrics() -> dict[str, Any]:
    """
    Convenience function to get health status.

    Returns:
        Dictionary with health status
    """
    collector = get_metrics_collector()
    return collector.get_health_status()


# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations and recording metrics."""

    def __init__(self, protocol: str, resource_type: str):
        """
        Initialize the timer.

        Args:
            protocol: Protocol being used
            resource_type: Resource type being accessed
        """
        self.protocol = protocol
        self.resource_type = resource_type
        self.start_time = None
        self.success = False

    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metrics."""
        if self.start_time is not None:
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            record_request_metrics(
                self.protocol, self.resource_type, self.success, elapsed_ms
            )

    def mark_success(self):
        """Mark the operation as successful."""
        self.success = True

