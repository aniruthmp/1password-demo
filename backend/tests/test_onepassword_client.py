"""
Unit tests for OnePasswordClient
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from onepasswordconnectsdk.models import Item, ItemVault, Field

from src.core.onepassword_client import OnePasswordClient, create_client_from_env


@pytest.fixture
def mock_op_client():
    """Mock 1Password Connect client."""
    with patch("src.core.onepassword_client.new_client") as mock:
        yield mock


@pytest.fixture
def sample_vault():
    """Sample vault object."""
    vault = Mock(spec=ItemVault)
    vault.id = "test-vault-123"
    vault.name = "Test Vault"
    return vault


@pytest.fixture
def sample_item():
    """Sample item object."""
    item = Mock(spec=Item)
    item.id = "item-123"
    item.title = "Test Database"
    item.username = "testuser"
    
    # Create mock fields
    field1 = Mock(spec=Field)
    field1.label = "password"
    field1.value = "testpass123"
    
    field2 = Mock(spec=Field)
    field2.label = "host"
    field2.value = "localhost"
    
    item.fields = [field1, field2]
    
    # Add vault reference
    item.vault = Mock(spec=ItemVault)
    item.vault.id = "test-vault-123"
    
    return item


class TestOnePasswordClientInit:
    """Tests for OnePasswordClient initialization."""
    
    def test_init_with_params(self, mock_op_client):
        """Test initialization with explicit parameters."""
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        assert client.connect_host == "http://localhost:8080"
        assert client.connect_token == "test-token"
        assert client.vault_id == "test-vault"
        mock_op_client.assert_called_once()
    
    def test_init_with_env_vars(self, mock_op_client, monkeypatch):
        """Test initialization with environment variables."""
        monkeypatch.setenv("OP_CONNECT_HOST", "http://env-host:8080")
        monkeypatch.setenv("OP_CONNECT_TOKEN", "env-token")
        monkeypatch.setenv("OP_VAULT_ID", "env-vault")
        
        client = OnePasswordClient()
        
        assert client.connect_host == "http://env-host:8080"
        assert client.connect_token == "env-token"
        assert client.vault_id == "env-vault"
    
    def test_init_missing_credentials(self, mock_op_client):
        """Test initialization fails without credentials."""
        with pytest.raises(ValueError, match="1Password Connect credentials not configured"):
            OnePasswordClient(connect_host="http://localhost:8080")
    
    def test_init_client_creation_error(self, mock_op_client):
        """Test initialization handles client creation errors."""
        mock_op_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            OnePasswordClient(
                connect_host="http://localhost:8080",
                connect_token="test-token"
            )


class TestOnePasswordClientVaultOperations:
    """Tests for vault operations."""
    
    def test_get_vault_success(self, mock_op_client, sample_vault):
        """Test successful vault retrieval."""
        client_instance = Mock()
        client_instance.get_vault.return_value = sample_vault
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault-123"
        )
        
        vault = client.get_vault()
        
        assert vault.id == "test-vault-123"
        assert vault.name == "Test Vault"
        client_instance.get_vault.assert_called_once_with("test-vault-123")
    
    def test_get_vault_with_custom_id(self, mock_op_client, sample_vault):
        """Test vault retrieval with custom vault ID."""
        client_instance = Mock()
        client_instance.get_vault.return_value = sample_vault
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token"
        )
        
        vault = client.get_vault("custom-vault-id")
        
        client_instance.get_vault.assert_called_once_with("custom-vault-id")
    
    def test_get_vault_missing_id(self, mock_op_client):
        """Test vault retrieval fails without vault ID."""
        mock_op_client.return_value = Mock()
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token"
        )
        
        with pytest.raises(ValueError, match="vault_id is required"):
            client.get_vault()
    
    def test_get_vault_api_error(self, mock_op_client):
        """Test vault retrieval handles API errors."""
        client_instance = Mock()
        client_instance.get_vault.side_effect = Exception("API Error")
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        with pytest.raises(Exception, match="API Error"):
            client.get_vault()


class TestOnePasswordClientItemOperations:
    """Tests for item operations."""
    
    def test_get_item_success(self, mock_op_client, sample_item):
        """Test successful item retrieval by ID."""
        client_instance = Mock()
        client_instance.get_item.return_value = sample_item
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        item = client.get_item("item-123")
        
        assert item.id == "item-123"
        assert item.title == "Test Database"
        client_instance.get_item.assert_called_once_with("item-123", "test-vault")
    
    def test_get_item_by_title_found(self, mock_op_client, sample_item):
        """Test successful item retrieval by title."""
        client_instance = Mock()
        client_instance.get_items.return_value = [sample_item]
        client_instance.get_item.return_value = sample_item
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        item = client.get_item_by_title("Test Database")
        
        assert item is not None
        assert item.title == "Test Database"
        client_instance.get_items.assert_called_once_with("test-vault")
    
    def test_get_item_by_title_not_found(self, mock_op_client):
        """Test item retrieval by title returns None when not found."""
        client_instance = Mock()
        client_instance.get_items.return_value = []
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        item = client.get_item_by_title("Nonexistent Item")
        
        assert item is None
    
    def test_get_item_by_title_case_insensitive(self, mock_op_client, sample_item):
        """Test item retrieval by title is case-insensitive."""
        client_instance = Mock()
        client_instance.get_items.return_value = [sample_item]
        client_instance.get_item.return_value = sample_item
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        item = client.get_item_by_title("test database")
        
        assert item is not None
        assert item.title == "Test Database"
    
    def test_list_items_success(self, mock_op_client, sample_item):
        """Test successful item listing."""
        client_instance = Mock()
        client_instance.get_items.return_value = [sample_item]
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        items = client.list_items()
        
        assert len(items) == 1
        assert items[0].title == "Test Database"
    
    def test_list_items_empty(self, mock_op_client):
        """Test listing items in empty vault."""
        client_instance = Mock()
        client_instance.get_items.return_value = []
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        items = client.list_items()
        
        assert len(items) == 0


class TestOnePasswordClientCredentialExtraction:
    """Tests for credential field extraction."""
    
    def test_extract_credential_fields(self, mock_op_client, sample_item):
        """Test extraction of credential fields from item."""
        mock_op_client.return_value = Mock()
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token"
        )
        
        credentials = client.extract_credential_fields(sample_item)
        
        assert credentials["username"] == "testuser"
        assert credentials["password"] == "testpass123"
        assert credentials["host"] == "localhost"
        assert credentials["_item_id"] == "item-123"
        assert credentials["_item_title"] == "Test Database"
        assert credentials["_vault_id"] == "test-vault-123"
    
    def test_extract_credential_fields_no_username(self, mock_op_client):
        """Test extraction when item has no username."""
        mock_op_client.return_value = Mock()
        
        item = Mock(spec=Item)
        item.id = "item-456"
        item.title = "API Key"
        item.username = None
        item.fields = []
        item.vault = Mock(spec=ItemVault)
        item.vault.id = "vault-456"
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token"
        )
        
        credentials = client.extract_credential_fields(item)
        
        assert "username" not in credentials
        assert credentials["_item_id"] == "item-456"


class TestOnePasswordClientHealthCheck:
    """Tests for health check functionality."""
    
    def test_health_check_success(self, mock_op_client, sample_vault):
        """Test successful health check."""
        client_instance = Mock()
        client_instance.get_vault.return_value = sample_vault
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        health = client.health_check()
        
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["vault_accessible"] is True
        assert health["vault_name"] == "Test Vault"
    
    def test_health_check_failure(self, mock_op_client):
        """Test health check when connection fails."""
        client_instance = Mock()
        client_instance.get_vault.side_effect = Exception("Connection timeout")
        mock_op_client.return_value = client_instance
        
        client = OnePasswordClient(
            connect_host="http://localhost:8080",
            connect_token="test-token",
            vault_id="test-vault"
        )
        
        health = client.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert health["vault_accessible"] is False
        assert "Connection timeout" in health["error"]


class TestOnePasswordClientConvenience:
    """Tests for convenience functions."""
    
    def test_create_client_from_env(self, mock_op_client, monkeypatch):
        """Test convenience function to create client from environment."""
        monkeypatch.setenv("OP_CONNECT_HOST", "http://localhost:8080")
        monkeypatch.setenv("OP_CONNECT_TOKEN", "env-token")
        monkeypatch.setenv("OP_VAULT_ID", "env-vault")
        
        client = create_client_from_env()
        
        assert isinstance(client, OnePasswordClient)
        assert client.connect_host == "http://localhost:8080"

