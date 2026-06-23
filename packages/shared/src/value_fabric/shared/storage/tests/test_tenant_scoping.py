"""Tests for storage client key normalization with tenant scoping."""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from value_fabric.shared.storage.client import StorageClient


class TestStorageKeyNormalization:
    """Test storage key normalization with tenant scoping."""

    def test_normalize_key_with_tenant_id(self):
        """Key should be prefixed with tenant ID when tenant_id is provided."""
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        normalized = client._normalize_key("documents/file.pdf", tenant_id="tenant-123")
        
        # Assert
        assert normalized == "tenant-tenant-123/documents/file.pdf"

    def test_normalize_key_without_tenant_id(self):
        """Key should not be prefixed when tenant_id is not provided."""
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        normalized = client._normalize_key("documents/file.pdf", tenant_id=None)
        
        # Assert
        assert normalized == "documents/file.pdf"

    def test_normalize_key_strips_leading_slash(self):
        """Leading slashes should be stripped from key."""
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        normalized = client._normalize_key("/documents/file.pdf", tenant_id="tenant-123")
        
        # Assert
        assert normalized == "tenant-tenant-123/documents/file.pdf"

    def test_normalize_key_with_empty_tenant_id(self):
        """Empty tenant_id should be treated as no tenant scoping."""
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        normalized = client._normalize_key("documents/file.pdf", tenant_id="")
        
        # Assert
        assert normalized == "documents/file.pdf"

    def test_normalize_key_with_nested_path(self):
        """Nested paths should be preserved with tenant prefix."""
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        normalized = client._normalize_key("a/b/c/file.pdf", tenant_id="tenant-456")
        
        # Assert
        assert normalized == "tenant-tenant-456/a/b/c/file.pdf"


class TestStorageOperationsWithTenantScoping:
    """Test storage operations use normalized keys with tenant scoping."""

    @pytest.mark.asyncio
    @patch("value_fabric.shared.storage.client.boto3.client")
    async def test_put_object_uses_normalized_key(self, mock_boto3_client):
        """put_object should use tenant-scoped normalized key."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        result = await client.put_object(
            key="documents/file.pdf",
            data=b"test data",
            tenant_id="tenant-123",
        )
        
        # Assert
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Key"] == "tenant-tenant-123/documents/file.pdf"
        assert call_kwargs["Bucket"] == "test-bucket"

    @pytest.mark.asyncio
    @patch("value_fabric.shared.storage.client.boto3.client")
    async def test_get_object_uses_normalized_key(self, mock_boto3_client):
        """get_object should use tenant-scoped normalized key."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        mock_response = {"Body": MagicMock()}
        mock_response["Body"].read.return_value = b"test data"
        mock_s3_client.get_object.return_value = mock_response
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        result = await client.get_object(key="documents/file.pdf", tenant_id="tenant-123")
        
        # Assert
        mock_s3_client.get_object.assert_called_once()
        call_kwargs = mock_s3_client.get_object.call_args[1]
        assert call_kwargs["Key"] == "tenant-tenant-123/documents/file.pdf"
        assert call_kwargs["Bucket"] == "test-bucket"

    @pytest.mark.asyncio
    @patch("value_fabric.shared.storage.client.boto3.client")
    async def test_delete_object_uses_normalized_key(self, mock_boto3_client):
        """delete_object should use tenant-scoped normalized key."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        result = await client.delete_object(key="documents/file.pdf", tenant_id="tenant-123")
        
        # Assert
        mock_s3_client.delete_object.assert_called_once()
        call_kwargs = mock_s3_client.delete_object.call_args[1]
        assert call_kwargs["Key"] == "tenant-tenant-123/documents/file.pdf"
        assert call_kwargs["Bucket"] == "test-bucket"

    @pytest.mark.asyncio
    @patch("value_fabric.shared.storage.client.boto3.client")
    async def test_list_objects_uses_normalized_prefix(self, mock_boto3_client):
        """list_objects should use tenant-scoped normalized prefix."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "tenant-tenant-123/documents/file1.pdf"},
                {"Key": "tenant-tenant-123/documents/file2.pdf"},
            ]
        }
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        result = await client.list_objects(prefix="documents/", tenant_id="tenant-123")
        
        # Assert
        mock_s3_client.list_objects_v2.assert_called_once()
        call_kwargs = mock_s3_client.list_objects_v2.call_args[1]
        assert call_kwargs["Prefix"] == "tenant-tenant-123/documents/"
        assert call_kwargs["Bucket"] == "test-bucket"
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("value_fabric.shared.storage.client.boto3.client")
    async def test_generate_presigned_url_uses_normalized_key(self, mock_boto3_client):
        """generate_presigned_url should use tenant-scoped normalized key."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/presigned-url"
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        result = await client.generate_presigned_url(key="documents/file.pdf", tenant_id="tenant-123")
        
        # Assert
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["Params"]["Key"] == "tenant-tenant-123/documents/file.pdf"
        assert call_kwargs["Params"]["Bucket"] == "test-bucket"

    @pytest.mark.asyncio
    @patch("value_fabric.shared.storage.client.boto3.client")
    async def test_object_exists_uses_normalized_key(self, mock_boto3_client):
        """object_exists should use tenant-scoped normalized key."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        result = await client.object_exists(key="documents/file.pdf", tenant_id="tenant-123")
        
        # Assert
        mock_s3_client.head_object.assert_called_once()
        call_kwargs = mock_s3_client.head_object.call_args[1]
        assert call_kwargs["Key"] == "tenant-tenant-123/documents/file.pdf"
        assert call_kwargs["Bucket"] == "test-bucket"


class TestTenantIsolation:
    """Test tenant isolation through key normalization."""

    @patch("value_fabric.shared.storage.client.boto3.client")
    def test_different_tenants_cannot_access_same_key(self, mock_boto3_client):
        """Different tenants should have different normalized keys for the same logical key."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        key_tenant_a = client._normalize_key("documents/file.pdf", tenant_id="tenant-a")
        key_tenant_b = client._normalize_key("documents/file.pdf", tenant_id="tenant-b")
        
        # Assert
        assert key_tenant_a == "tenant-tenant-a/documents/file.pdf"
        assert key_tenant_b == "tenant-tenant-b/documents/file.pdf"
        assert key_tenant_a != key_tenant_b

    @patch("value_fabric.shared.storage.client.boto3.client")
    def test_tenant_prefix_format_is_consistent(self, mock_boto3_client):
        """Tenant prefix should always follow the format 'tenant-{tenant_id}/'."""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        client = StorageClient(
            endpoint_url="http://localhost:9000",
            access_key_id="test",
            secret_access_key="test",
            bucket="test-bucket",
        )
        
        # Act
        key1 = client._normalize_key("file.pdf", tenant_id="123")
        key2 = client._normalize_key("file.pdf", tenant_id="abc-456")
        key3 = client._normalize_key("file.pdf", tenant_id="tenant-xyz")
        
        # Assert
        assert key1.startswith("tenant-123/")
        assert key2.startswith("tenant-abc-456/")
        assert key3.startswith("tenant-tenant-xyz/")
