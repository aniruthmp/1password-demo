"""
1Password Connect API Client
Handles async communication with 1Password Connect server for credential retrieval.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from onepasswordconnectsdk.client import (
    Client,
    new_client_from_environment,
    new_client,
)
from onepasswordconnectsdk.models import Item, ItemVault


logger = logging.getLogger(__name__)


class OnePasswordClient:
    """
    Async wrapper for 1Password Connect SDK operations.
    
    Provides methods to:
    - Retrieve vaults
    - Fetch items by ID or title
    - List items in a vault
    - Perform health checks
    """
    
    def __init__(
        self,
        connect_host: Optional[str] = None,
        connect_token: Optional[str] = None,
        vault_id: Optional[str] = None,
    ):
        """
        Initialize 1Password Connect client.
        
        Args:
            connect_host: 1Password Connect server URL (defaults to OP_CONNECT_HOST env var)
            connect_token: Connect API token (defaults to OP_CONNECT_TOKEN env var)
            vault_id: Default vault ID (defaults to OP_VAULT_ID env var)
        """
        self.connect_host = connect_host or os.getenv("OP_CONNECT_HOST")
        self.connect_token = connect_token or os.getenv("OP_CONNECT_TOKEN")
        self.vault_id = vault_id or os.getenv("OP_VAULT_ID")
        
        if not self.connect_host or not self.connect_token:
            raise ValueError(
                "1Password Connect credentials not configured. "
                "Set OP_CONNECT_HOST and OP_CONNECT_TOKEN environment variables."
            )
        
        # Initialize the 1Password Connect client
        try:
            self.client: Client = new_client(self.connect_host, self.connect_token)
            logger.info(
                f"1Password Connect client initialized for host: {self.connect_host}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize 1Password Connect client: {e}")
            raise
    
    def get_vault(self, vault_id: Optional[str] = None) -> ItemVault:
        """
        Retrieve a vault by ID.
        
        Args:
            vault_id: Vault ID (uses default if not provided)
            
        Returns:
            ItemVault object
            
        Raises:
            ValueError: If vault_id is not provided and no default is set
            Exception: If vault retrieval fails
        """
        target_vault_id = vault_id or self.vault_id
        if not target_vault_id:
            raise ValueError("vault_id is required")
        
        try:
            vault = self.client.get_vault(target_vault_id)
            logger.debug(f"Retrieved vault: {vault.name} (ID: {vault.id})")
            return vault
        except Exception as e:
            logger.error(f"Failed to retrieve vault {target_vault_id}: {e}")
            raise
    
    def get_item(self, item_id: str, vault_id: Optional[str] = None) -> Item:
        """
        Fetch an item by its ID.
        
        Args:
            item_id: Item UUID
            vault_id: Vault ID (uses default if not provided)
            
        Returns:
            Item object with full details including fields
            
        Raises:
            Exception: If item retrieval fails
        """
        target_vault_id = vault_id or self.vault_id
        if not target_vault_id:
            raise ValueError("vault_id is required")
        
        try:
            item = self.client.get_item(item_id, target_vault_id)
            logger.info(f"Retrieved item: {item.title} (ID: {item.id})")
            return item
        except Exception as e:
            logger.error(
                f"Failed to retrieve item {item_id} from vault {target_vault_id}: {e}"
            )
            raise
    
    def get_item_by_title(
        self, title: str, vault_id: Optional[str] = None
    ) -> Optional[Item]:
        """
        Fetch an item by its title (name).
        
        Args:
            title: Item title to search for
            vault_id: Vault ID (uses default if not provided)
            
        Returns:
            Item object if found, None otherwise
            
        Raises:
            Exception: If search fails
        """
        target_vault_id = vault_id or self.vault_id
        if not target_vault_id:
            raise ValueError("vault_id is required")
        
        try:
            items = self.client.get_items(target_vault_id)
            for item in items:
                if item.title.lower() == title.lower():
                    # Get full item details (list only returns summaries)
                    full_item = self.get_item(item.id, target_vault_id)
                    logger.info(f"Found item by title: {title}")
                    return full_item
            
            logger.warning(f"Item not found with title: {title}")
            return None
        except Exception as e:
            logger.error(
                f"Failed to search for item '{title}' in vault {target_vault_id}: {e}"
            )
            raise
    
    def list_items(self, vault_id: Optional[str] = None) -> List[Item]:
        """
        List all items in a vault.
        
        Args:
            vault_id: Vault ID (uses default if not provided)
            
        Returns:
            List of Item objects (summary version)
            
        Raises:
            Exception: If listing fails
        """
        target_vault_id = vault_id or self.vault_id
        if not target_vault_id:
            raise ValueError("vault_id is required")
        
        try:
            items = self.client.get_items(target_vault_id)
            logger.info(f"Listed {len(items)} items in vault {target_vault_id}")
            return items
        except Exception as e:
            logger.error(f"Failed to list items in vault {target_vault_id}: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check connection health to 1Password Connect server.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Try to get vault as a health check
            vault = self.get_vault()
            return {
                "status": "healthy",
                "connected": True,
                "vault_accessible": True,
                "vault_name": vault.name,
                "message": "1Password Connect API is accessible",
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "vault_accessible": False,
                "error": str(e),
                "message": "Failed to connect to 1Password Connect API",
            }
    
    def extract_credential_fields(self, item: Item) -> Dict[str, str]:
        """
        Extract credential fields from an item into a simple dictionary.
        
        Args:
            item: 1Password Item object
            
        Returns:
            Dictionary of field labels to values
        """
        credentials = {}
        
        # Extract username if present
        if hasattr(item, "username") and item.username:
            credentials["username"] = item.username
        
        # Extract fields
        if hasattr(item, "fields") and item.fields:
            for field in item.fields:
                if hasattr(field, "label") and hasattr(field, "value"):
                    # Only include non-empty values
                    if field.value:
                        credentials[field.label] = field.value
        
        # Add item metadata
        credentials["_item_id"] = item.id
        credentials["_item_title"] = item.title
        credentials["_vault_id"] = item.vault.id if hasattr(item, "vault") else "unknown"
        
        return credentials


# Convenience function for creating client from environment
def create_client_from_env() -> OnePasswordClient:
    """
    Create a OnePasswordClient using environment variables.
    
    Returns:
        Configured OnePasswordClient instance
    """
    return OnePasswordClient()

