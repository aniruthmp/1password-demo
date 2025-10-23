"""
Centralized Logging Configuration
Provides structured JSON logging with per-protocol tagging.
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON string
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "protocol"):
            log_data["protocol"] = record.protocol
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id
        if hasattr(record, "resource"):
            log_data["resource"] = record.resource

        return json.dumps(log_data)


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: str = "logs/app.log",
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" or "text")
        log_file: Path to log file (optional, logs to console only if empty)
    """
    # Get config from environment
    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    log_format = os.getenv("LOG_FORMAT", log_format).lower()

    # Create logs directory if it doesn't exist
    if log_file:
        import pathlib

        pathlib.Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))

    # File handler (if configured)
    file_handler = None
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level))

    # Set formatter
    if log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if file_handler:
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    root_logger.info(f"Logging configured: level={log_level}, format={log_format}")


def get_logger_with_context(
    name: str,
    protocol: str = None,
    agent_id: str = None,
) -> logging.LoggerAdapter:
    """
    Get a logger with contextual information.

    Args:
        name: Logger name
        protocol: Protocol context (mcp, a2a, acp)
        agent_id: Agent identifier

    Returns:
        LoggerAdapter with extra context
    """
    logger = logging.getLogger(name)
    extra = {}

    if protocol:
        extra["protocol"] = protocol
    if agent_id:
        extra["agent_id"] = agent_id

    return logging.LoggerAdapter(logger, extra)
