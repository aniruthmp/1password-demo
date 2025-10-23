"""
Shared pytest fixtures and configuration
"""

import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture(scope="session")
def test_env_vars(monkeypatch_session):
    """Set up test environment variables for the entire session."""
    monkeypatch_session.setenv("OP_CONNECT_HOST", "http://localhost:8080")
    monkeypatch_session.setenv("OP_CONNECT_TOKEN", "test-token-for-testing")
    monkeypatch_session.setenv("OP_VAULT_ID", "test-vault-123")
    monkeypatch_session.setenv("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long")
    monkeypatch_session.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch_session.setenv("TOKEN_TTL_MINUTES", "5")
    monkeypatch_session.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file path."""
    log_file = tmp_path / "test_audit.log"
    yield log_file
    # Cleanup
    if log_file.exists():
        log_file.unlink()


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch fixture."""
    from _pytest.monkeypatch import MonkeyPatch
    m = MonkeyPatch()
    yield m
    m.undo()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

