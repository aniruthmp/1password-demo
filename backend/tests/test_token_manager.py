"""
Unit tests for TokenManager
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.core.token_manager import TokenManager, create_token_manager_from_env


@pytest.fixture
def token_manager():
    """Create TokenManager instance with test secret."""
    return TokenManager(
        jwt_secret="test_secret_key_at_least_32_characters_long_for_security",
        jwt_algorithm="HS256",
        default_ttl_minutes=5
    )


@pytest.fixture
def sample_credentials():
    """Sample credential data."""
    return {
        "username": "testuser",
        "password": "testpass123",
        "host": "localhost",
        "port": "5432"
    }


class TestTokenManagerInit:
    """Tests for TokenManager initialization."""
    
    def test_init_with_params(self):
        """Test initialization with explicit parameters."""
        manager = TokenManager(
            jwt_secret="my_secret_key_is_very_long_and_secure",
            jwt_algorithm="HS256",
            default_ttl_minutes=10
        )
        
        assert manager.jwt_secret == "my_secret_key_is_very_long_and_secure"
        assert manager.jwt_algorithm == "HS256"
        assert manager.default_ttl_minutes == 10
    
    def test_init_with_env_vars(self, monkeypatch):
        """Test initialization with environment variables."""
        monkeypatch.setenv("JWT_SECRET_KEY", "env_secret_key_at_least_32_chars_long")
        monkeypatch.setenv("JWT_ALGORITHM", "HS512")
        monkeypatch.setenv("TOKEN_TTL_MINUTES", "15")
        
        manager = TokenManager()
        
        assert manager.jwt_secret == "env_secret_key_at_least_32_chars_long"
        assert manager.jwt_algorithm == "HS512"
        assert manager.default_ttl_minutes == 15
    
    def test_init_missing_secret(self):
        """Test initialization fails without JWT secret."""
        with pytest.raises(ValueError, match="JWT secret key not configured"):
            TokenManager(jwt_secret=None)
    
    def test_init_short_secret_warning(self, caplog):
        """Test warning when JWT secret is too short."""
        manager = TokenManager(jwt_secret="short_key")
        
        assert "shorter than recommended" in caplog.text


class TestTokenManagerEncryption:
    """Tests for encryption and decryption."""
    
    def test_encrypt_payload(self, token_manager, sample_credentials):
        """Test credential encryption."""
        encrypted = token_manager.encrypt_payload(sample_credentials)
        
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        assert encrypted != str(sample_credentials)  # Should be encrypted
    
    def test_decrypt_payload(self, token_manager, sample_credentials):
        """Test credential decryption."""
        encrypted = token_manager.encrypt_payload(sample_credentials)
        decrypted = token_manager.decrypt_payload(encrypted)
        
        assert decrypted == sample_credentials
        assert decrypted["username"] == "testuser"
        assert decrypted["password"] == "testpass123"
    
    def test_encrypt_decrypt_roundtrip(self, token_manager):
        """Test encryption/decryption roundtrip with various data types."""
        test_data = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "nested": {"key": "value"},
            "list": [1, 2, 3]
        }
        
        encrypted = token_manager.encrypt_payload(test_data)
        decrypted = token_manager.decrypt_payload(encrypted)
        
        assert decrypted == test_data
    
    def test_decrypt_invalid_data(self, token_manager):
        """Test decryption fails with invalid data."""
        with pytest.raises(ValueError, match="Invalid or corrupted encrypted data"):
            token_manager.decrypt_payload("invalid_encrypted_data")
    
    def test_decrypt_wrong_key(self):
        """Test decryption fails with wrong key."""
        manager1 = TokenManager(jwt_secret="key1" + "0" * 32)
        manager2 = TokenManager(jwt_secret="key2" + "0" * 32)
        
        data = {"test": "data"}
        encrypted = manager1.encrypt_payload(data)
        
        with pytest.raises(ValueError):
            manager2.decrypt_payload(encrypted)


class TestTokenManagerJWTGeneration:
    """Tests for JWT token generation."""
    
    def test_generate_jwt(self, token_manager, sample_credentials):
        """Test JWT token generation."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="prod-db",
            ttl_minutes=5
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode without verification to check structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["sub"] == "test-agent"
        assert decoded["resource_type"] == "database"
        assert decoded["resource_name"] == "prod-db"
        assert decoded["ttl_minutes"] == 5
        assert "credentials" in decoded
        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["iss"] == "1password-credential-broker"
    
    def test_generate_jwt_default_ttl(self, token_manager, sample_credentials):
        """Test JWT generation uses default TTL when not specified."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="api",
            resource_name="api-key"
        )
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["ttl_minutes"] == 5  # Default
    
    def test_generate_jwt_custom_ttl(self, token_manager, sample_credentials):
        """Test JWT generation with custom TTL."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="ssh",
            resource_name="prod-server",
            ttl_minutes=15
        )
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["ttl_minutes"] == 15
    
    def test_generate_jwt_additional_claims(self, token_manager, sample_credentials):
        """Test JWT generation with additional custom claims."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="generic",
            resource_name="secret",
            additional_claims={"custom_field": "custom_value", "request_id": "12345"}
        )
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["custom_field"] == "custom_value"
        assert decoded["request_id"] == "12345"
    
    def test_generate_jwt_encrypted_credentials(self, token_manager, sample_credentials):
        """Test that credentials are encrypted in JWT."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db"
        )
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        encrypted_creds = decoded["credentials"]
        
        # Credentials should be encrypted string, not raw dict
        assert isinstance(encrypted_creds, str)
        assert "testuser" not in encrypted_creds
        assert "testpass123" not in encrypted_creds


class TestTokenManagerJWTValidation:
    """Tests for JWT token validation."""
    
    def test_verify_jwt_valid_token(self, token_manager, sample_credentials):
        """Test verification of valid JWT token."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db"
        )
        
        payload = token_manager.verify_jwt(token)
        
        assert payload["sub"] == "test-agent"
        assert payload["resource_type"] == "database"
        assert payload["resource_name"] == "test-db"
    
    def test_verify_jwt_expired_token(self, token_manager, sample_credentials):
        """Test verification fails for expired token."""
        # Generate token with -1 minute TTL (already expired)
        with patch('src.core.token_manager.datetime') as mock_datetime:
            # Set time to past
            past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            mock_datetime.now.return_value = past_time
            
            token = token_manager.generate_jwt(
                agent_id="test-agent",
                credentials=sample_credentials,
                resource_type="database",
                resource_name="test-db",
                ttl_minutes=1
            )
        
        # Now verify with current time (should be expired)
        with pytest.raises(jwt.ExpiredSignatureError):
            token_manager.verify_jwt(token)
    
    def test_verify_jwt_invalid_signature(self, token_manager, sample_credentials):
        """Test verification fails with invalid signature."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db"
        )
        
        # Tamper with token
        tampered_token = token[:-10] + "tampered00"
        
        with pytest.raises(jwt.InvalidTokenError):
            token_manager.verify_jwt(tampered_token)
    
    def test_verify_jwt_wrong_secret(self, sample_credentials):
        """Test verification fails with wrong secret."""
        manager1 = TokenManager(jwt_secret="secret1" + "0" * 32)
        manager2 = TokenManager(jwt_secret="secret2" + "0" * 32)
        
        token = manager1.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db"
        )
        
        with pytest.raises(jwt.InvalidTokenError):
            manager2.verify_jwt(token)
    
    def test_verify_and_decrypt(self, token_manager, sample_credentials):
        """Test verification and decryption of JWT token."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="prod-db",
            ttl_minutes=10
        )
        
        result = token_manager.verify_and_decrypt(token)
        
        assert result["agent_id"] == "test-agent"
        assert result["resource_type"] == "database"
        assert result["resource_name"] == "prod-db"
        assert result["ttl_minutes"] == 10
        assert result["credentials"] == sample_credentials
        assert "issued_at" in result
        assert "expires_at" in result
    
    def test_verify_and_decrypt_missing_credentials(self, token_manager):
        """Test verification fails when token has no credentials."""
        # Create token without credentials field
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test-agent",
            "resource_type": "database",
            "resource_name": "test-db",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        
        token = jwt.encode(payload, token_manager.jwt_secret, algorithm="HS256")
        
        with pytest.raises(ValueError, match="does not contain encrypted credentials"):
            token_manager.verify_and_decrypt(token)


class TestTokenManagerExpirationChecks:
    """Tests for token expiration checking."""
    
    def test_is_token_expired_valid_token(self, token_manager, sample_credentials):
        """Test checking valid (not expired) token."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db",
            ttl_minutes=10
        )
        
        is_expired = token_manager.is_token_expired(token)
        
        assert is_expired is False
    
    def test_is_token_expired_expired_token(self, token_manager, sample_credentials):
        """Test checking expired token."""
        # Generate expired token
        with patch('src.core.token_manager.datetime') as mock_datetime:
            past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            mock_datetime.now.return_value = past_time
            
            token = token_manager.generate_jwt(
                agent_id="test-agent",
                credentials=sample_credentials,
                resource_type="database",
                resource_name="test-db",
                ttl_minutes=1
            )
        
        is_expired = token_manager.is_token_expired(token)
        
        assert is_expired is True
    
    def test_is_token_expired_invalid_token(self, token_manager):
        """Test that invalid token is considered expired."""
        is_expired = token_manager.is_token_expired("invalid_token")
        
        assert is_expired is True
    
    def test_get_token_expiration(self, token_manager, sample_credentials):
        """Test getting token expiration datetime."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db",
            ttl_minutes=5
        )
        
        expiration = token_manager.get_token_expiration(token)
        
        assert expiration is not None
        assert isinstance(expiration, datetime)
        # Should expire approximately 5 minutes from now
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=5)
        assert abs((expiration - expected_exp).total_seconds()) < 5
    
    def test_get_token_expiration_invalid_token(self, token_manager):
        """Test getting expiration of invalid token returns None."""
        expiration = token_manager.get_token_expiration("invalid_token")
        
        assert expiration is None
    
    def test_get_time_until_expiry(self, token_manager, sample_credentials):
        """Test getting time remaining until expiry."""
        token = token_manager.generate_jwt(
            agent_id="test-agent",
            credentials=sample_credentials,
            resource_type="database",
            resource_name="test-db",
            ttl_minutes=5
        )
        
        time_remaining = token_manager.get_time_until_expiry(token)
        
        assert time_remaining is not None
        assert isinstance(time_remaining, timedelta)
        # Should be approximately 5 minutes
        assert 4.9 * 60 < time_remaining.total_seconds() < 5.1 * 60
    
    def test_get_time_until_expiry_expired_token(self, token_manager, sample_credentials):
        """Test getting time until expiry for expired token returns zero."""
        with patch('src.core.token_manager.datetime') as mock_datetime:
            past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            mock_datetime.now.return_value = past_time
            
            token = token_manager.generate_jwt(
                agent_id="test-agent",
                credentials=sample_credentials,
                resource_type="database",
                resource_name="test-db",
                ttl_minutes=1
            )
        
        time_remaining = token_manager.get_time_until_expiry(token)
        
        assert time_remaining == timedelta(0)
    
    def test_get_time_until_expiry_invalid_token(self, token_manager):
        """Test getting time until expiry for invalid token returns None."""
        time_remaining = token_manager.get_time_until_expiry("invalid_token")
        
        assert time_remaining is None


class TestTokenManagerConvenience:
    """Tests for convenience functions."""
    
    def test_create_token_manager_from_env(self, monkeypatch):
        """Test convenience function to create manager from environment."""
        monkeypatch.setenv("JWT_SECRET_KEY", "env_secret_key_long_enough_for_security")
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")
        monkeypatch.setenv("TOKEN_TTL_MINUTES", "10")
        
        manager = create_token_manager_from_env()
        
        assert isinstance(manager, TokenManager)
        assert manager.jwt_secret == "env_secret_key_long_enough_for_security"
        assert manager.default_ttl_minutes == 10

