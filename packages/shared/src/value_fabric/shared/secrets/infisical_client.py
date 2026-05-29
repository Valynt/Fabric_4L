"""Infisical API client for tenant secrets management.

Provides programmatic access to Infisical for creating tenant-scoped secret paths,
reading/writing secrets, and managing tenant configurations.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx
from value_fabric.shared.models.typed_dict import TypedDictModel


class TenantSecretManager_seed_default_tenant_secretsResult(TypedDictModel):
    data: Any | None = None
    error: Any
    success: bool

logger = logging.getLogger(__name__)

# Default API endpoint
DEFAULT_INFISICAL_API_URL = "https://app.infisical.com"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
RETRY_BACKOFF_FACTOR = 2.0


@dataclass
class InfisicalConfig:
    """Configuration for Infisical API client."""

    api_url: str
    token: str
    workspace_id: str

    @classmethod
    def from_env(cls) -> "InfisicalConfig":
        """Load configuration from environment variables."""
        return cls(
            api_url=os.getenv("INFISICAL_API_URL", DEFAULT_INFISICAL_API_URL),
            token=os.getenv("INFISICAL_TOKEN", ""),
            workspace_id=os.getenv("INFISICAL_WORKSPACE_ID", ""),
        )

    def is_configured(self) -> bool:
        """Check if all required configuration is present."""
        return bool(self.token and self.workspace_id)


@dataclass
class Secret:
    """Represents a secret in Infisical."""

    key: str
    value: str
    comment: str = ""
    tags: list[str] | None = None


class InfisicalClient:
    """Client for Infisical API operations.

    Handles authentication, API calls, and error handling for tenant secret management.
    """

    def __init__(self, config: InfisicalConfig | None = None) -> None:
        """Initialize client with configuration.

        Args:
            config: Infisical configuration. If None, loads from environment.
        """
        self.config = config or InfisicalConfig.from_env()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_url,
                headers={
                    "Authorization": f"Bearer {self.config.token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "InfisicalClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated request to Infisical API with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (without base URL)
            **kwargs: Additional arguments for httpx request

        Returns:
            JSON response as dictionary

        Raises:
            InfisicalAPIError: On API errors or after max retries
        """
        import asyncio

        client = await self._get_client()
        url = f"/api/v1{path}"
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    logger.error(
                        "Infisical API error: %s %s - %s",
                        method,
                        url,
                        e.response.text,
                    )
                    raise InfisicalAPIError(
                        f"API error {e.response.status_code}: {e.response.text}"
                    ) from e
                # Retry on 5xx errors
                last_exception = e
                logger.warning(
                    "Infisical API %s error (attempt %d/%d): %s",
                    e.response.status_code,
                    attempt + 1,
                    MAX_RETRIES,
                    url,
                )
            except httpx.RequestError as e:
                # Retry on network errors
                last_exception = e
                logger.warning(
                    "Infisical request error (attempt %d/%d): %s %s - %s",
                    attempt + 1,
                    MAX_RETRIES,
                    method,
                    url,
                    repr(e),
                )

            # Exponential backoff before retry
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR ** attempt)
                await asyncio.sleep(delay)

        # Max retries exceeded
        logger.error(
            "Infisical request failed after %d attempts: %s %s",
            MAX_RETRIES,
            method,
            url,
        )
        raise InfisicalAPIError(
            f"Request failed after {MAX_RETRIES} attempts: {last_exception}"
        ) from last_exception

    async def create_folder(
        self,
        environment: str,
        folder_path: str,
    ) -> dict[str, Any]:
        """Create a folder (secret path) in Infisical.

        Args:
            environment: Environment slug (dev, test, staging, prod)
            folder_path: Path to create (e.g., "/tenant/abc123")

        Returns:
            Created folder data
        """
        workspace_id = self.config.workspace_id
        path = f"/workspaces/{workspace_id}/folders"

        payload = {
            "workspaceId": workspace_id,
            "environment": environment,
            "folderPath": folder_path,
            "name": folder_path.strip("/").split("/")[-1],
        }

        logger.info("Creating Infisical folder: %s in %s", folder_path, environment)
        return await self._request("POST", path, json=payload)

    async def create_secrets(
        self,
        environment: str,
        secret_path: str,
        secrets: list[Secret],
    ) -> dict[str, Any]:
        """Create multiple secrets in Infisical.

        Args:
            environment: Environment slug
            secret_path: Path where secrets are stored
            secrets: List of secrets to create

        Returns:
            Created secrets data
        """
        workspace_id = self.config.workspace_id

        # Infisical bulk create endpoint
        path = f"/workspaces/{workspace_id}/secrets/batch"

        secrets_data = [
            {
                "secretKey": s.key,
                "secretValue": s.value,
                "secretComment": s.comment,
                "secretPath": secret_path,
                "environment": environment,
                "workspaceId": workspace_id,
                "type": "shared",  # or "personal"
                "tags": s.tags or [],
            }
            for s in secrets
        ]

        logger.info(
            "Creating %d secrets in %s:%s",
            len(secrets),
            environment,
            secret_path,
        )
        return await self._request("POST", path, json={"secrets": secrets_data})

    async def get_secrets(
        self,
        environment: str,
        secret_path: str = "/",
    ) -> list[Secret]:
        """Get secrets from a path.

        Args:
            environment: Environment slug
            secret_path: Path to read secrets from

        Returns:
            List of secrets
        """
        workspace_id = self.config.workspace_id
        path = f"/workspaces/{workspace_id}/secrets"

        params = {
            "environment": environment,
            "secretPath": secret_path,
            "workspaceId": workspace_id,
        }

        response = await self._request("GET", path, params=params)

        secrets = []
        for secret_data in response.get("secrets", []):
            secrets.append(
                Secret(
                    key=secret_data.get("secretKey", ""),
                    value=secret_data.get("secretValue", ""),
                    comment=secret_data.get("secretComment", ""),
                    tags=secret_data.get("tags", []),
                )
            )

        return secrets

    async def delete_secrets(
        self,
        environment: str,
        secret_path: str,
        secret_keys: list[str],
    ) -> dict[str, Any]:
        """Delete secrets from a path.

        Args:
            environment: Environment slug
            secret_path: Path where secrets are stored
            secret_keys: List of secret keys to delete

        Returns:
            Deletion response
        """
        workspace_id = self.config.workspace_id
        path = f"/workspaces/{workspace_id}/secrets/batch"

        secrets_data = [
            {
                "secretKey": key,
                "secretPath": secret_path,
                "environment": environment,
                "workspaceId": workspace_id,
                "type": "shared",
            }
            for key in secret_keys
        ]

        logger.info(
            "Deleting %d secrets from %s:%s",
            len(secret_keys),
            environment,
            secret_path,
        )
        return await self._request("DELETE", path, json={"secrets": secrets_data})

    async def delete_folder(
        self,
        environment: str,
        folder_path: str,
    ) -> dict[str, Any]:
        """Delete a folder and all its secrets.

        Args:
            environment: Environment slug
            folder_path: Path to delete

        Returns:
            Deletion response
        """
        workspace_id = self.config.workspace_id
        path = f"/workspaces/{workspace_id}/folders"

        params = {
            "workspaceId": workspace_id,
            "environment": environment,
            "folderPath": folder_path,
        }

        logger.info("Deleting Infisical folder: %s in %s", folder_path, environment)
        return await self._request("DELETE", path, params=params)


class InfisicalAPIError(Exception):
    """Error from Infisical API."""

    pass


class TenantSecretManager:
    """High-level manager for tenant-specific secrets in Infisical.

    Provides tenant-scoped operations that map tenant IDs to Infisical paths.
    """

    TENANT_PATH_PREFIX = "/tenants"

    def __init__(self, client: InfisicalClient | None = None) -> None:
        """Initialize with Infisical client.

        Args:
            client: Infisical client. If None, creates new client from env.
        """
        self.client = client or InfisicalClient()

    def _get_tenant_path(self, tenant_id: str) -> str:
        """Convert tenant ID to Infisical path.

        Args:
            tenant_id: UUID of tenant

        Returns:
            Path string like "/tenants/abc123"
        """
        return f"{self.TENANT_PATH_PREFIX}/{tenant_id}"

    async def create_tenant_secrets_path(
        self,
        tenant_id: str,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create secret paths for a tenant in all environments.

        Args:
            tenant_id: UUID of tenant
            environments: List of environments. Defaults to ["dev", "test", "staging", "prod"]

        Returns:
            Dict mapping environment to folder creation result
        """
        if environments is None:
            environments = ["dev", "test", "staging", "prod"]

        tenant_path = self._get_tenant_path(tenant_id)
        results = {}

        for env in environments:
            try:
                result = await self.client.create_folder(env, tenant_path)
                results[env] = {"success": True, "data": result}
                logger.info("Created Infisical path for tenant %s in %s", tenant_id, env)
            except InfisicalAPIError as e:
                results[env] = {"success": False, "error": repr(e)}
                logger.error("Failed to create path for tenant %s in %s: %s", tenant_id, env, e)

        return results

    async def seed_default_tenant_secrets(
        self,
        tenant_id: str,
        tenant_name: str,
        environment: str = "dev",
    ) -> dict[str, Any]:
        """Seed default secrets for a new tenant.

        Args:
            tenant_id: UUID of tenant
            tenant_name: Display name of tenant
            environment: Environment to seed

        Returns:
            Creation result
        """
        tenant_path = self._get_tenant_path(tenant_id)

        default_secrets = [
            Secret(
                key="TENANT_ID",
                value=tenant_id,
                comment="Tenant UUID",
            ),
            Secret(
                key="TENANT_NAME",
                value=tenant_name,
                comment="Tenant display name",
            ),
            Secret(
                key="DATABASE_URL",
                value="",  # To be filled by admin
                comment="Tenant database connection string",
            ),
            Secret(
                key="REDIS_URL",
                value="",  # To be filled by admin
                comment="Tenant Redis connection string",
            ),
            Secret(
                key="JWT_SECRET",
                value="",  # To be generated
                comment="JWT signing secret for tenant",
            ),
        ]

        try:
            result = await self.client.create_secrets(
                environment, tenant_path, default_secrets
            )
            logger.info("Seeded default secrets for tenant %s in %s", tenant_id, environment)
            return TenantSecretManager_seed_default_tenant_secretsResult.model_validate({"success": True, "data": result})
        except InfisicalAPIError as e:
            logger.error("Failed to seed secrets for tenant %s: %s", tenant_id, e)
            return TenantSecretManager_seed_default_tenant_secretsResult.model_validate({"success": False, "error": repr(e)})

    async def delete_tenant_secrets_path(
        self,
        tenant_id: str,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Delete all secret paths for a tenant.

        Args:
            tenant_id: UUID of tenant
            environments: List of environments. Defaults to all.

        Returns:
            Dict mapping environment to deletion result
        """
        if environments is None:
            environments = ["dev", "test", "staging", "prod"]

        tenant_path = self._get_tenant_path(tenant_id)
        results = {}

        for env in environments:
            try:
                result = await self.client.delete_folder(env, tenant_path)
                results[env] = {"success": True, "data": result}
                logger.info("Deleted Infisical path for tenant %s in %s", tenant_id, env)
            except InfisicalAPIError as e:
                results[env] = {"success": False, "error": repr(e)}
                logger.error("Failed to delete path for tenant %s in %s: %s", tenant_id, env, e)

        return results

    async def get_tenant_secrets(
        self,
        tenant_id: str,
        environment: str,
    ) -> list[Secret]:
        """Get all secrets for a tenant.

        Args:
            tenant_id: UUID of tenant
            environment: Environment slug

        Returns:
            List of secrets
        """
        tenant_path = self._get_tenant_path(tenant_id)
        return await self.client.get_secrets(environment, tenant_path)
