"""Tenant secrets provisioning service.

Provides a single entry-point for creating and managing Infisical secret paths
during tenant onboarding.  Wraps ``TenantSecretManager`` with higher-level
orchestration: path creation, default secret seeding, and audit logging.

Usage::

    from value_fabric.shared.secrets.tenant_secrets import TenantSecretsService

    service = TenantSecretsService()
    await service.provision(tenant_id="abc-123", tenant_name="Acme Corp")
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ENVIRONMENTS = ("dev", "staging", "prod")


@dataclass
class ProvisioningResult:
    """Outcome of a tenant secret provisioning run."""

    tenant_id: str
    success: bool
    paths_created: dict[str, Any] = field(default_factory=dict)
    secrets_seeded: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class TenantSecretsService:
    """Orchestrates Infisical secret lifecycle for tenant provisioning.

    Creates a ``/tenants/{tenant_id}`` path hierarchy in each requested
    environment and seeds sensible default secrets (``TENANT_ID``,
    ``TENANT_NAME``, ``JWT_SECRET``, ``DATABASE_URL``, ``REDIS_URL``).

    Args:
        environments: Infisical environments to provision.  Defaults to
            ``("dev", "staging", "prod")``.
        client: Optional pre-built ``TenantSecretManager`` instance (useful for
            testing with a mock).  When ``None``, a new instance is created from
            environment variables on first use.
    """

    def __init__(
        self,
        environments: tuple[str, ...] = _DEFAULT_ENVIRONMENTS,
        client: Any | None = None,
    ) -> None:
        self._environments = environments
        self._client = client

    def _get_manager(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from value_fabric.shared.secrets.infisical_client import (
                TenantSecretManager,
            )
            return TenantSecretManager()
        except ImportError:
            raise RuntimeError(
                "infisical_client is not available. "
                "Install the 'infisical-python' extra or provide a mock client."
            )

    async def provision(
        self,
        tenant_id: str,
        tenant_name: str,
        *,
        seed_environment: str = "prod",
    ) -> ProvisioningResult:
        """Create Infisical paths and seed default secrets for a new tenant.

        Args:
            tenant_id: UUID string identifying the tenant.
            tenant_name: Human-readable display name of the tenant.
            seed_environment: Which environment receives seeded placeholder
                secrets.  Defaults to ``"prod"`` so prod secrets are
                explicitly provisioned (placeholders only).

        Returns:
            :class:`ProvisioningResult` with per-environment outcomes.
        """
        result = ProvisioningResult(tenant_id=tenant_id, success=False)
        manager = self._get_manager()

        # 1. Create path hierarchy in every environment
        logger.info("Creating Infisical paths for tenant %s", tenant_id)
        try:
            paths = await manager.create_tenant_secrets_path(
                tenant_id, environments=list(self._environments)
            )
            result.paths_created = paths
        except Exception as exc:
            logger.error("Failed to create paths for tenant %s: %s", tenant_id, exc)
            result.errors.append(f"path_creation: {exc}")
            return result

        # 2. Seed placeholder secrets in the target environment
        logger.info(
            "Seeding default secrets for tenant %s in %s",
            tenant_id,
            seed_environment,
        )
        try:
            seeded = await manager.seed_default_tenant_secrets(
                tenant_id, tenant_name, environment=seed_environment
            )
            result.secrets_seeded = dict(seeded) if seeded else {}
        except Exception as exc:
            logger.error("Failed to seed secrets for tenant %s: %s", tenant_id, exc)
            result.errors.append(f"seed_secrets: {exc}")
            # Partial success — paths were created, secrets seeding failed
            result.success = bool(result.paths_created)
            return result

        result.success = True
        return result

    async def rotate_jwt_secret(
        self, tenant_id: str, environment: str = "prod"
    ) -> str:
        """Generate and store a fresh JWT signing secret for the tenant.

        The secret is generated after a successful write to Infisical so the
        caller only receives it when storage is confirmed.

        Args:
            tenant_id: UUID string identifying the tenant.
            environment: Infisical environment to update.

        Returns:
            The newly generated secret (caller should distribute securely).
        """
        manager = self._get_manager()

        try:
            from value_fabric.shared.secrets.infisical_client import Secret

            new_secret = secrets.token_hex(32)  # 256-bit secret
            await manager.client.create_secrets(
                environment,
                f"/tenants/{tenant_id}",
                [Secret(key="JWT_SECRET", value=new_secret, comment="JWT signing secret")],
            )
            logger.info(
                "Rotated JWT secret for tenant %s in %s", tenant_id, environment
            )
        except Exception as exc:
            logger.error(
                "Failed to rotate JWT secret for tenant %s: %s", tenant_id, exc
            )
            raise

        return new_secret

    async def delete_tenant_secrets(
        self, tenant_id: str
    ) -> dict[str, Any]:
        """Remove all Infisical secrets for a deleted tenant.

        Attempts concurrent deletion across environments.  Each environment's
        result is recorded independently so partial failures are surfaced
        accurately.

        Args:
            tenant_id: UUID string identifying the tenant.

        Returns:
            Dict mapping environment to deletion outcome.
        """
        import asyncio

        manager = self._get_manager()

        async def _delete_env(env: str) -> tuple[str, dict[str, Any]]:
            path = f"/tenants/{tenant_id}"
            deleted = 0
            failed: list[str] = []
            try:
                secret_list = await manager.client.list_secrets(env, path)
                delete_tasks = [
                    manager.client.delete_secret(env, path, secret.key)
                    for secret in secret_list
                ]
                results = await asyncio.gather(*delete_tasks, return_exceptions=True)
                for secret, result in zip(secret_list, results):
                    if isinstance(result, Exception):
                        failed.append(secret.key)
                        logger.warning(
                            "Failed to delete secret %s for tenant %s in %s: %s",
                            secret.key,
                            tenant_id,
                            env,
                            result,
                        )
                    else:
                        deleted += 1
                outcome: dict[str, Any] = {"deleted": deleted}
                if failed:
                    outcome["success"] = False
                    outcome["failed_keys"] = failed
                else:
                    outcome["success"] = True
                logger.info(
                    "Deleted %d/%d secrets for tenant %s in %s",
                    deleted,
                    len(secret_list),
                    tenant_id,
                    env,
                )
            except Exception as exc:
                outcome = {"success": False, "error": f"{type(exc).__name__}: secret_deletion_failed"}
                logger.error(
                    "Failed to list/delete secrets for tenant %s in %s: %s",
                    tenant_id,
                    env,
                    exc,
                )
            return env, outcome

        env_results = await asyncio.gather(*[_delete_env(env) for env in self._environments])
        return dict(env_results)
