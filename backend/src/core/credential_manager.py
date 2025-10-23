"""
Unified Credential Manager
Orchestrates credential retrieval from 1Password and ephemeral token generation.
"""

import logging
from enum import Enum
from typing import Any

from .onepassword_client import OnePasswordClient
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Supported resource types for credential retrieval."""

    DATABASE = "database"
    API = "api"
    SSH = "ssh"
    GENERIC = "generic"


class CredentialManager:
    """
    Unified credential management orchestrator.

    Coordinates:
    - Credential retrieval from 1Password
    - Ephemeral JWT token generation
    - Token validation and decryption
    - Error handling and logging
    """

    def __init__(
        self,
        onepassword_client: OnePasswordClient | None = None,
        token_manager: TokenManager | None = None,
    ):
        """
        Initialize CredentialManager.

        Args:
            onepassword_client: 1Password client (creates from env if not provided)
            token_manager: Token manager (creates from env if not provided)
        """
        self.op_client = onepassword_client or OnePasswordClient()
        self.token_mgr = token_manager or TokenManager()

        logger.info("CredentialManager initialized successfully")

    def fetch_credentials(
        self,
        resource_type: str,
        resource_name: str,
        vault_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch credentials from 1Password for a given resource.

        Args:
            resource_type: Type of resource (database, api, ssh, generic)
            resource_name: Name/title of the resource in 1Password
            vault_id: Optional vault ID (uses default if not provided)

        Returns:
            Dictionary of credential fields

        Raises:
            ValueError: If resource_type is invalid or resource not found
            Exception: If retrieval fails
        """
        # Validate resource type
        try:
            ResourceType(resource_type)
        except ValueError as e:
            raise ValueError(
                f"Invalid resource_type: {resource_type}. "
                f"Must be one of: {[t.value for t in ResourceType]}"
            ) from e

        logger.info(
            f"Fetching credentials for resource_type={resource_type}, "
            f"resource_name={resource_name}"
        )

        try:
            # Retrieve item from 1Password by title
            item = self.op_client.get_item_by_title(resource_name, vault_id)

            if not item:
                raise ValueError(
                    f"Resource '{resource_name}' not found in 1Password vault"
                )

            # Extract credential fields
            credentials = self.op_client.extract_credential_fields(item)

            logger.info(
                f"Successfully fetched credentials for {resource_name} "
                f"(extracted {len(credentials)} fields)"
            )

            return credentials

        except Exception as e:
            logger.error(f"Failed to fetch credentials for {resource_name}: {e}")
            raise

    def issue_ephemeral_token(
        self,
        credentials: dict[str, Any],
        agent_id: str,
        resource_type: str,
        resource_name: str,
        ttl_minutes: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate an ephemeral JWT token with encrypted credentials.

        Args:
            credentials: Credential data to encrypt
            agent_id: Requesting agent identifier
            resource_type: Type of resource
            resource_name: Name of resource
            ttl_minutes: Token TTL in minutes (uses default if not provided)

        Returns:
            Dictionary with token and metadata:
            {
                "token": "eyJ...",
                "expires_in": 300,
                "resource": "database/prod-postgres",
                "issued_at": "2025-10-23T12:34:56Z",
                "expires_at": "2025-10-23T12:39:56Z"
            }
        """
        logger.info(
            f"Issuing ephemeral token for agent={agent_id}, "
            f"resource={resource_type}/{resource_name}, ttl={ttl_minutes or 'default'}"
        )

        try:
            # Generate JWT token
            token = self.token_mgr.generate_jwt(
                agent_id=agent_id,
                credentials=credentials,
                resource_type=resource_type,
                resource_name=resource_name,
                ttl_minutes=ttl_minutes,
            )

            # Get token metadata
            payload = self.token_mgr.verify_jwt(token)
            ttl = payload.get("ttl_minutes", self.token_mgr.default_ttl_minutes)

            result = {
                "token": token,
                "expires_in": ttl * 60,  # Convert to seconds
                "resource": f"{resource_type}/{resource_name}",
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "ttl_minutes": ttl,
            }

            logger.info(
                f"Successfully issued token for {agent_id} "
                f"(expires in {ttl} minutes)"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to issue ephemeral token: {e}")
            raise

    def fetch_and_issue_token(
        self,
        resource_type: str,
        resource_name: str,
        agent_id: str,
        ttl_minutes: int | None = None,
        vault_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Convenience method: Fetch credentials and issue token in one call.

        Args:
            resource_type: Type of resource (database, api, ssh, generic)
            resource_name: Name/title of the resource in 1Password
            agent_id: Requesting agent identifier
            ttl_minutes: Token TTL in minutes (uses default if not provided)
            vault_id: Optional vault ID (uses default if not provided)

        Returns:
            Dictionary with token and metadata (same as issue_ephemeral_token)

        Raises:
            ValueError: If resource not found or invalid parameters
            Exception: If any step fails
        """
        logger.info(
            f"Full credential flow: fetch + issue for agent={agent_id}, "
            f"resource={resource_type}/{resource_name}"
        )

        # Step 1: Fetch credentials
        credentials = self.fetch_credentials(resource_type, resource_name, vault_id)

        # Step 2: Issue token
        token_data = self.issue_ephemeral_token(
            credentials=credentials,
            agent_id=agent_id,
            resource_type=resource_type,
            resource_name=resource_name,
            ttl_minutes=ttl_minutes,
        )

        return token_data

    def validate_token(self, token: str) -> dict[str, Any]:
        """
        Validate a JWT token and return its metadata (without decrypting credentials).

        Args:
            token: JWT token string

        Returns:
            Dictionary with token metadata:
            {
                "valid": true,
                "agent_id": "...",
                "resource_type": "...",
                "resource_name": "...",
                "issued_at": ...,
                "expires_at": ...,
                "time_remaining": 120  # seconds
            }

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        logger.debug("Validating JWT token")

        try:
            # Verify token
            payload = self.token_mgr.verify_jwt(token)

            # Get time remaining
            time_remaining = self.token_mgr.get_time_until_expiry(token)
            time_remaining_seconds = (
                int(time_remaining.total_seconds()) if time_remaining else 0
            )

            result = {
                "valid": True,
                "agent_id": payload.get("sub"),
                "resource_type": payload.get("resource_type"),
                "resource_name": payload.get("resource_name"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "time_remaining": time_remaining_seconds,
            }

            logger.info(
                f"Token validated successfully for agent={result['agent_id']}, "
                f"time_remaining={time_remaining_seconds}s"
            )

            return result

        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise

    def get_credentials_from_token(self, token: str) -> dict[str, Any]:
        """
        Validate token and decrypt embedded credentials.

        Args:
            token: JWT token string

        Returns:
            Dictionary with decrypted credentials and metadata

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
            ValueError: If decryption fails
        """
        logger.info("Validating and decrypting token")

        try:
            result = self.token_mgr.verify_and_decrypt(token)

            logger.info(
                f"Successfully decrypted credentials for agent={result['agent_id']}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get credentials from token: {e}")
            raise

    def health_check(self) -> dict[str, Any]:
        """
        Comprehensive health check of all components.

        Returns:
            Dictionary with health status:
            {
                "status": "healthy",
                "components": {
                    "onepassword": {...},
                    "token_manager": {...}
                }
            }
        """
        logger.debug("Performing health check")

        # Check 1Password connection
        op_health = self.op_client.health_check()

        # Check token manager (simple verification)
        token_health = {
            "status": "healthy",
            "configured": True,
            "algorithm": self.token_mgr.jwt_algorithm,
            "default_ttl": self.token_mgr.default_ttl_minutes,
        }

        # Overall status
        overall_healthy = (
            op_health.get("status") == "healthy"
            and token_health.get("status") == "healthy"
        )

        result = {
            "status": "healthy" if overall_healthy else "degraded",
            "components": {
                "onepassword": op_health,
                "token_manager": token_health,
            },
        }

        logger.info(f"Health check complete: status={result['status']}")

        return result


# Convenience function for creating manager from environment
def create_credential_manager_from_env() -> CredentialManager:
    """
    Create a CredentialManager using environment variables.

    Returns:
        Configured CredentialManager instance
    """
    return CredentialManager()
