"""
Unit tests for CredentialManager
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import jwt

from src.core.credential_manager import (
    CredentialManager,
    ResourceType,
    create_credential_manager_from_env
)


@pytest.fixture
def mock_op_client():
    """Mock OnePasswordClient."""
    client = Mock()
    client.health_check.return_value = {
        "status": "healthy",
        "connected": True,
        "vault_accessible": True
    }
    return client


@pytest.fixture
def mock_token_manager():
    """Mock TokenManager."""
    manager = Mock()
    manager.jwt_algorithm = "HS256"
    manager.default_ttl_minutes = 5
    return manager


@pytest.fixture
def sample_credentials():
    """Sample credential data."""
    return {
        "username": "dbuser",
        "password": "dbpass123",
        "host": "localhost",
        "port": "5432",
        "_item_id": "item-123",
        "_item_title": "Production Database",
        "_vault_id": "vault-123"
    }


@pytest.fixture
def credential_manager(mock_op_client, mock_token_manager):
    """Create CredentialManager with mocked dependencies."""
    return CredentialManager(
        onepassword_client=mock_op_client,
        token_manager=mock_token_manager
    )


class TestCredentialManagerInit:
    """Tests for CredentialManager initialization."""
    
    def test_init_with_dependencies(self, mock_op_client, mock_token_manager):
        """Test initialization with provided dependencies."""
        manager = CredentialManager(
            onepassword_client=mock_op_client,
            token_manager=mock_token_manager
        )
        
        assert manager.op_client == mock_op_client
        assert manager.token_mgr == mock_token_manager
    
    @patch('src.core.credential_manager.OnePasswordClient')
    @patch('src.core.credential_manager.TokenManager')
    def test_init_creates_defaults(self, mock_token_cls, mock_op_cls):
        """Test initialization creates default clients if not provided."""
        manager = CredentialManager()
        
        mock_op_cls.assert_called_once()
        mock_token_cls.assert_called_once()


class TestResourceTypeEnum:
    """Tests for ResourceType enum."""
    
    def test_resource_type_values(self):
        """Test ResourceType enum has expected values."""
        assert ResourceType.DATABASE.value == "database"
        assert ResourceType.API.value == "api"
        assert ResourceType.SSH.value == "ssh"
        assert ResourceType.GENERIC.value == "generic"
    
    def test_resource_type_validation(self):
        """Test ResourceType can validate string values."""
        assert ResourceType("database") == ResourceType.DATABASE
        assert ResourceType("api") == ResourceType.API
        
        with pytest.raises(ValueError):
            ResourceType("invalid_type")


class TestFetchCredentials:
    """Tests for fetch_credentials method."""
    
    def test_fetch_credentials_success(self, credential_manager, mock_op_client, sample_credentials):
        """Test successful credential fetching."""
        mock_op_client.get_item_by_title.return_value = Mock()
        mock_op_client.extract_credential_fields.return_value = sample_credentials
        
        result = credential_manager.fetch_credentials(
            resource_type="database",
            resource_name="Production Database"
        )
        
        assert result == sample_credentials
        mock_op_client.get_item_by_title.assert_called_once_with("Production Database", None)
        mock_op_client.extract_credential_fields.assert_called_once()
    
    def test_fetch_credentials_with_vault_id(self, credential_manager, mock_op_client, sample_credentials):
        """Test credential fetching with specific vault ID."""
        mock_op_client.get_item_by_title.return_value = Mock()
        mock_op_client.extract_credential_fields.return_value = sample_credentials
        
        result = credential_manager.fetch_credentials(
            resource_type="database",
            resource_name="Test DB",
            vault_id="custom-vault-123"
        )
        
        mock_op_client.get_item_by_title.assert_called_once_with("Test DB", "custom-vault-123")
    
    def test_fetch_credentials_invalid_resource_type(self, credential_manager):
        """Test credential fetching fails with invalid resource type."""
        with pytest.raises(ValueError, match="Invalid resource_type: invalid"):
            credential_manager.fetch_credentials(
                resource_type="invalid",
                resource_name="Test Resource"
            )
    
    def test_fetch_credentials_not_found(self, credential_manager, mock_op_client):
        """Test credential fetching fails when resource not found."""
        mock_op_client.get_item_by_title.return_value = None
        
        with pytest.raises(ValueError, match="not found in 1Password vault"):
            credential_manager.fetch_credentials(
                resource_type="database",
                resource_name="Nonexistent DB"
            )
    
    def test_fetch_credentials_api_error(self, credential_manager, mock_op_client):
        """Test credential fetching handles API errors."""
        mock_op_client.get_item_by_title.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            credential_manager.fetch_credentials(
                resource_type="database",
                resource_name="Test DB"
            )


class TestIssueEphemeralToken:
    """Tests for issue_ephemeral_token method."""
    
    def test_issue_token_success(self, credential_manager, mock_token_manager, sample_credentials):
        """Test successful token issuance."""
        mock_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        mock_token_manager.generate_jwt.return_value = mock_token
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "ttl_minutes": 5,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp()
        }
        
        result = credential_manager.issue_ephemeral_token(
            credentials=sample_credentials,
            agent_id="test-agent",
            resource_type="database",
            resource_name="prod-db",
            ttl_minutes=5
        )
        
        assert result["token"] == mock_token
        assert result["expires_in"] == 300  # 5 minutes in seconds
        assert result["resource"] == "database/prod-db"
        assert result["ttl_minutes"] == 5
        assert "issued_at" in result
        assert "expires_at" in result
        
        mock_token_manager.generate_jwt.assert_called_once()
    
    def test_issue_token_default_ttl(self, credential_manager, mock_token_manager, sample_credentials):
        """Test token issuance with default TTL."""
        mock_token = "test.jwt.token"
        mock_token_manager.generate_jwt.return_value = mock_token
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "ttl_minutes": 5,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp()
        }
        
        result = credential_manager.issue_ephemeral_token(
            credentials=sample_credentials,
            agent_id="test-agent",
            resource_type="api",
            resource_name="api-key"
        )
        
        # Should use default TTL from token manager
        call_args = mock_token_manager.generate_jwt.call_args
        assert call_args.kwargs["ttl_minutes"] is None
    
    def test_issue_token_custom_ttl(self, credential_manager, mock_token_manager, sample_credentials):
        """Test token issuance with custom TTL."""
        mock_token = "test.jwt.token"
        mock_token_manager.generate_jwt.return_value = mock_token
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "ttl_minutes": 15,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=15)).timestamp()
        }
        
        result = credential_manager.issue_ephemeral_token(
            credentials=sample_credentials,
            agent_id="test-agent",
            resource_type="ssh",
            resource_name="prod-server",
            ttl_minutes=15
        )
        
        assert result["ttl_minutes"] == 15
        assert result["expires_in"] == 900  # 15 minutes


class TestFetchAndIssueToken:
    """Tests for fetch_and_issue_token convenience method."""
    
    def test_fetch_and_issue_success(self, credential_manager, mock_op_client, mock_token_manager, sample_credentials):
        """Test successful fetch and issue workflow."""
        # Setup mocks
        mock_op_client.get_item_by_title.return_value = Mock()
        mock_op_client.extract_credential_fields.return_value = sample_credentials
        mock_token_manager.generate_jwt.return_value = "test.jwt.token"
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "ttl_minutes": 10,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=10)).timestamp()
        }
        
        result = credential_manager.fetch_and_issue_token(
            resource_type="database",
            resource_name="prod-db",
            agent_id="test-agent",
            ttl_minutes=10
        )
        
        assert "token" in result
        assert result["resource"] == "database/prod-db"
        assert result["ttl_minutes"] == 10
        
        # Verify both fetch and issue were called
        mock_op_client.get_item_by_title.assert_called_once()
        mock_token_manager.generate_jwt.assert_called_once()
    
    def test_fetch_and_issue_with_vault_id(self, credential_manager, mock_op_client, mock_token_manager, sample_credentials):
        """Test fetch and issue with custom vault ID."""
        mock_op_client.get_item_by_title.return_value = Mock()
        mock_op_client.extract_credential_fields.return_value = sample_credentials
        mock_token_manager.generate_jwt.return_value = "test.jwt.token"
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "ttl_minutes": 5,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp()
        }
        
        result = credential_manager.fetch_and_issue_token(
            resource_type="api",
            resource_name="api-key",
            agent_id="test-agent",
            vault_id="custom-vault"
        )
        
        mock_op_client.get_item_by_title.assert_called_once_with("api-key", "custom-vault")


class TestValidateToken:
    """Tests for validate_token method."""
    
    def test_validate_token_success(self, credential_manager, mock_token_manager):
        """Test successful token validation."""
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "resource_type": "database",
            "resource_name": "prod-db",
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp()
        }
        mock_token_manager.get_time_until_expiry.return_value = timedelta(minutes=5)
        
        result = credential_manager.validate_token("test.jwt.token")
        
        assert result["valid"] is True
        assert result["agent_id"] == "test-agent"
        assert result["resource_type"] == "database"
        assert result["resource_name"] == "prod-db"
        assert result["time_remaining"] == 300  # 5 minutes in seconds
    
    def test_validate_token_expired(self, credential_manager, mock_token_manager):
        """Test validation of expired token."""
        mock_token_manager.verify_jwt.side_effect = jwt.ExpiredSignatureError()
        
        with pytest.raises(jwt.ExpiredSignatureError):
            credential_manager.validate_token("expired.jwt.token")
    
    def test_validate_token_invalid(self, credential_manager, mock_token_manager):
        """Test validation of invalid token."""
        mock_token_manager.verify_jwt.side_effect = jwt.InvalidTokenError()
        
        with pytest.raises(jwt.InvalidTokenError):
            credential_manager.validate_token("invalid.jwt.token")


class TestGetCredentialsFromToken:
    """Tests for get_credentials_from_token method."""
    
    def test_get_credentials_success(self, credential_manager, mock_token_manager, sample_credentials):
        """Test successful credential extraction from token."""
        mock_token_manager.verify_and_decrypt.return_value = {
            "agent_id": "test-agent",
            "credentials": sample_credentials,
            "resource_type": "database",
            "resource_name": "prod-db",
            "issued_at": datetime.utcnow().timestamp(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).timestamp(),
            "ttl_minutes": 5
        }
        
        result = credential_manager.get_credentials_from_token("test.jwt.token")
        
        assert result["agent_id"] == "test-agent"
        assert result["credentials"] == sample_credentials
        assert result["resource_type"] == "database"
        assert result["resource_name"] == "prod-db"
    
    def test_get_credentials_expired_token(self, credential_manager, mock_token_manager):
        """Test credential extraction from expired token fails."""
        mock_token_manager.verify_and_decrypt.side_effect = jwt.ExpiredSignatureError()
        
        with pytest.raises(jwt.ExpiredSignatureError):
            credential_manager.get_credentials_from_token("expired.jwt.token")
    
    def test_get_credentials_invalid_token(self, credential_manager, mock_token_manager):
        """Test credential extraction from invalid token fails."""
        mock_token_manager.verify_and_decrypt.side_effect = jwt.InvalidTokenError()
        
        with pytest.raises(jwt.InvalidTokenError):
            credential_manager.get_credentials_from_token("invalid.jwt.token")


class TestHealthCheck:
    """Tests for health_check method."""
    
    def test_health_check_all_healthy(self, credential_manager, mock_op_client):
        """Test health check when all components are healthy."""
        mock_op_client.health_check.return_value = {
            "status": "healthy",
            "connected": True,
            "vault_accessible": True
        }
        
        result = credential_manager.health_check()
        
        assert result["status"] == "healthy"
        assert result["components"]["onepassword"]["status"] == "healthy"
        assert result["components"]["token_manager"]["status"] == "healthy"
    
    def test_health_check_op_unhealthy(self, credential_manager, mock_op_client):
        """Test health check when 1Password is unhealthy."""
        mock_op_client.health_check.return_value = {
            "status": "unhealthy",
            "connected": False,
            "vault_accessible": False
        }
        
        result = credential_manager.health_check()
        
        assert result["status"] == "degraded"
        assert result["components"]["onepassword"]["status"] == "unhealthy"
    
    def test_health_check_includes_token_manager_info(self, credential_manager, mock_token_manager):
        """Test health check includes token manager information."""
        result = credential_manager.health_check()
        
        token_health = result["components"]["token_manager"]
        assert token_health["algorithm"] == "HS256"
        assert token_health["default_ttl"] == 5


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @patch('src.core.credential_manager.OnePasswordClient')
    @patch('src.core.credential_manager.TokenManager')
    def test_create_from_env(self, mock_token_cls, mock_op_cls):
        """Test convenience function to create manager from environment."""
        manager = create_credential_manager_from_env()
        
        assert isinstance(manager, CredentialManager)
        mock_op_cls.assert_called_once()
        mock_token_cls.assert_called_once()


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_fetch_credentials_all_resource_types(self, credential_manager, mock_op_client, sample_credentials):
        """Test fetching credentials for all supported resource types."""
        mock_op_client.get_item_by_title.return_value = Mock()
        mock_op_client.extract_credential_fields.return_value = sample_credentials
        
        for resource_type in ["database", "api", "ssh", "generic"]:
            result = credential_manager.fetch_credentials(
                resource_type=resource_type,
                resource_name="Test Resource"
            )
            assert result == sample_credentials
    
    def test_issue_token_empty_credentials(self, credential_manager, mock_token_manager):
        """Test issuing token with empty credentials."""
        mock_token_manager.generate_jwt.return_value = "test.token"
        mock_token_manager.verify_jwt.return_value = {
            "sub": "test-agent",
            "ttl_minutes": 5,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp()
        }
        
        result = credential_manager.issue_ephemeral_token(
            credentials={},
            agent_id="test-agent",
            resource_type="generic",
            resource_name="empty-creds"
        )
        
        assert "token" in result

