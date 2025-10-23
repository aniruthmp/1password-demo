"""
JWT Token Manager with AES-256 Encryption
Handles ephemeral token generation, encryption, and validation.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages JWT token generation, validation, and credential encryption.
    
    Features:
    - JWT token generation with configurable TTL
    - AES-256 encryption for sensitive credential data
    - Token expiration validation
    - Secure decryption and verification
    """
    
    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        default_ttl_minutes: int = 5,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize TokenManager.
        
        Args:
            jwt_secret: Secret key for JWT signing (defaults to JWT_SECRET_KEY env var)
            jwt_algorithm: JWT algorithm (default: HS256)
            default_ttl_minutes: Default token TTL in minutes (default: 5)
            encryption_key: Key for AES-256 encryption (defaults to JWT_SECRET_KEY)
        """
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET_KEY")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM") or jwt_algorithm
        self.default_ttl_minutes = int(
            os.getenv("TOKEN_TTL_MINUTES", str(default_ttl_minutes))
        )
        
        if not self.jwt_secret:
            raise ValueError(
                "JWT secret key not configured. Set JWT_SECRET_KEY environment variable."
            )
        
        if len(self.jwt_secret) < 32:
            logger.warning(
                "JWT secret key is shorter than recommended (32+ characters). "
                "Consider using a stronger secret."
            )
        
        # Initialize encryption key (use JWT secret if not provided)
        encryption_key = encryption_key or self.jwt_secret
        self.fernet = self._initialize_fernet(encryption_key)
        
        logger.info(
            f"TokenManager initialized with algorithm={self.jwt_algorithm}, "
            f"default_ttl={self.default_ttl_minutes}min"
        )
    
    def _initialize_fernet(self, key: str) -> Fernet:
        """
        Initialize Fernet cipher for AES-256 encryption.
        
        Args:
            key: Base key string
            
        Returns:
            Fernet cipher instance
        """
        # Derive a proper 32-byte key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"1password-broker-salt",  # Fixed salt for deterministic key
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(derived_key)
    
    def encrypt_payload(self, data: Dict[str, Any]) -> str:
        """
        Encrypt credential data using AES-256.
        
        Args:
            data: Dictionary of credential data
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            # Convert dict to JSON string
            json_data = json.dumps(data)
            
            # Encrypt using Fernet (AES-256 in CBC mode)
            encrypted_bytes = self.fernet.encrypt(json_data.encode())
            
            # Return as base64 string
            encrypted_str = encrypted_bytes.decode()
            
            logger.debug("Credential payload encrypted successfully")
            return encrypted_str
        except Exception as e:
            logger.error(f"Failed to encrypt payload: {e}")
            raise
    
    def decrypt_payload(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt AES-256 encrypted credential data.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted dictionary
            
        Raises:
            Exception: If decryption fails (invalid key, corrupted data, etc.)
        """
        try:
            # Decrypt using Fernet
            decrypted_bytes = self.fernet.decrypt(encrypted_data.encode())
            
            # Parse JSON
            json_data = decrypted_bytes.decode()
            data = json.loads(json_data)
            
            logger.debug("Credential payload decrypted successfully")
            return data
        except Exception as e:
            logger.error(f"Failed to decrypt payload: {e}")
            raise ValueError("Invalid or corrupted encrypted data")
    
    def generate_jwt(
        self,
        agent_id: str,
        credentials: Dict[str, Any],
        resource_type: str,
        resource_name: str,
        ttl_minutes: Optional[int] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a JWT token with encrypted credentials.
        
        Args:
            agent_id: Requesting agent identifier
            credentials: Credential data to encrypt and embed
            resource_type: Type of resource (database, api, ssh, generic)
            resource_name: Name/identifier of the resource
            ttl_minutes: Token TTL in minutes (uses default if not provided)
            additional_claims: Optional additional JWT claims
            
        Returns:
            JWT token string
        """
        ttl = ttl_minutes or self.default_ttl_minutes
        
        # Current time (timezone-aware UTC)
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=ttl)
        
        # Encrypt credentials
        encrypted_creds = self.encrypt_payload(credentials)
        
        # Build JWT payload
        payload = {
            "sub": agent_id,  # Subject: agent requesting credentials
            "credentials": encrypted_creds,  # Encrypted credential data
            "resource_type": resource_type,
            "resource_name": resource_name,
            "iat": now,  # Issued at
            "exp": exp,  # Expiration
            "iss": "1password-credential-broker",  # Issuer
            "ttl_minutes": ttl,
        }
        
        # Add any additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Generate JWT
        try:
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            logger.info(
                f"Generated JWT for agent={agent_id}, "
                f"resource={resource_type}/{resource_name}, ttl={ttl}min"
            )
            
            return token
        except Exception as e:
            logger.error(f"Failed to generate JWT: {e}")
            raise
    
    def verify_jwt(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload (with credentials still encrypted)
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
            
            logger.debug(f"JWT verified successfully for agent={payload.get('sub')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {e}")
            raise
    
    def verify_and_decrypt(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT and decrypt embedded credentials.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with decrypted credentials and metadata
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
            ValueError: If decryption fails
        """
        # Verify JWT
        payload = self.verify_jwt(token)
        
        # Decrypt credentials
        encrypted_creds = payload.get("credentials")
        if not encrypted_creds:
            raise ValueError("Token does not contain encrypted credentials")
        
        decrypted_creds = self.decrypt_payload(encrypted_creds)
        
        # Return full context
        return {
            "agent_id": payload.get("sub"),
            "credentials": decrypted_creds,
            "resource_type": payload.get("resource_type"),
            "resource_name": payload.get("resource_name"),
            "issued_at": payload.get("iat"),
            "expires_at": payload.get("exp"),
            "ttl_minutes": payload.get("ttl_minutes"),
        }
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without raising an exception.
        
        Args:
            token: JWT token string
            
        Returns:
            True if expired, False if valid
        """
        try:
            self.verify_jwt(token)
            return False
        except jwt.ExpiredSignatureError:
            return True
        except jwt.InvalidTokenError:
            # Invalid token is considered "expired" for safety
            return True
    
    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get the expiration datetime of a token.
        
        Args:
            token: JWT token string
            
        Returns:
            Expiration datetime or None if token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": False},  # Don't raise on expiration
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            return None
        except Exception as e:
            logger.error(f"Failed to get token expiration: {e}")
            return None
    
    def get_time_until_expiry(self, token: str) -> Optional[timedelta]:
        """
        Get time remaining until token expiry.
        
        Args:
            token: JWT token string
            
        Returns:
            Timedelta until expiry, or None if expired/invalid
        """
        exp = self.get_token_expiration(token)
        if not exp:
            return None
        
        now = datetime.now(timezone.utc)
        if exp <= now:
            return timedelta(0)  # Already expired
        
        return exp - now


# Convenience function for creating manager from environment
def create_token_manager_from_env() -> TokenManager:
    """
    Create a TokenManager using environment variables.
    
    Returns:
        Configured TokenManager instance
    """
    return TokenManager()

