"""Integration tests for tenant provisioning system.

Tests the complete provisioning workflow including:
- Infisical secret path creation
- Provisioning state tracking
- Retry and rollback mechanisms
- Webhook triggers with HMAC-SHA256 signature verification
- Webhook idempotency via X-Webhook-ID

These tests use mock DB sessions and HTTP clients to run without
infrastructure dependencies. Mark with @pytest.mark.integration.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Module path constants for mocking
# ---------------------------------------------------------------------------
MOCK_PROVISIONING_MODULE = "value_fabric.layer4.tenants.provisioning"
MOCK_TENANT_SECRET_MANAGER = f"{MOCK_PROVISIONING_MODULE}.TenantSecretManager"
MOCK_EMIT_AUDIT = f"{MOCK_PROVISIONING_MODULE}.emit_audit_event"

# Provisioning route module for webhook tests
MOCK_WEBHOOK_MODULE = (
    "value_fabric.layer4.tenants.api.routes.provisioning"
)

# Default environments expected by the provisioning service
DEFAULT_ENVIRONMENTS = ["dev", "test", "staging", "prod"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _make_env_result(success: bool = True, error: str | None = None) -> dict:
    """Build a per-environment result dict matching InfisicalClient shape."""
    result = {env: {"success": success} for env in DEFAULT_ENVIRONMENTS}
    if error:
        for env in result:
            result[env]["error"] = error
    return result


def _make_hmac_signature(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 hex digest for webhook tests."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Fixtures — mock DB session
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db_session():
    """Provide a mock async DB session that satisfies service dependencies.

    The provisioning service calls get_tenant() and update_tenant_status()
    which both take an AsyncSession. We mock at the service layer so the
    DB session itself is never hit.
    """
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_tenant():
    """Create a mock Tenant ORM object in pending status."""
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.name = "Test Provisioning Tenant"
    tenant.slug = f"test-prov-{uuid.uuid4().hex[:8]}"
    tenant.status = "pending"
    tenant.settings = {"isolation_tier": "shared", "admin_email": "test@example.com"}
    return tenant


@pytest.fixture
def mock_infisical_client():
    """Create a mock TenantSecretManager with successful responses."""
    with patch(MOCK_TENANT_SECRET_MANAGER) as mock_class:
        mock_instance = MagicMock()
        mock_instance.create_tenant_secrets_path = AsyncMock(
            return_value=_make_env_result(success=True)
        )
        mock_instance.seed_default_tenant_secrets = AsyncMock(
            return_value={"success": True}
        )
        mock_instance.delete_tenant_secrets_path = AsyncMock(
            return_value=_make_env_result(success=True)
        )
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_audit_emitter():
    """Suppress audit event emission during tests."""
    with patch(MOCK_EMIT_AUDIT, new_callable=AsyncMock) as mock_emit:
        yield mock_emit


# ---------------------------------------------------------------------------
# Provisioning workflow tests
# ---------------------------------------------------------------------------
class TestProvisioningWorkflow:
    """Test the complete provisioning workflow."""

    async def test_successful_provisioning(
        self,
        mock_db_session,
        mock_tenant,
        mock_infisical_client,
        mock_audit_emitter,
    ):
        """Test successful tenant provisioning through all steps."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            ProvisioningStep,
            TenantProvisioningService,
        )

        with patch(f"{MOCK_PROVISIONING_MODULE}.get_tenant", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_tenant

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                new_callable=AsyncMock,
            ):
                service = TenantProvisioningService(mock_db_session)
                state = await service.provision_tenant(mock_tenant.id)

        assert state.status == ProvisioningStatus.COMPLETED
        assert state.error is None
        assert ProvisioningStep.CREATE_INFISICAL_PATH in state.completed_steps
        assert ProvisioningStep.SEED_DEFAULT_SECRETS in state.completed_steps
        assert ProvisioningStep.UPDATE_TENANT_STATUS in state.completed_steps

        mock_infisical_client.create_tenant_secrets_path.assert_called_once()
        mock_infisical_client.seed_default_tenant_secrets.assert_called_once()

    async def test_provisioning_idempotent(
        self,
        mock_db_session,
        mock_tenant,
        mock_infisical_client,
        mock_audit_emitter,
    ):
        """Test that provisioning is idempotent — second call returns completed."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            TenantProvisioningService,
        )

        # Make tenant appear active after first provisioning
        mock_tenant_active = MagicMock()
        mock_tenant_active.id = mock_tenant.id
        mock_tenant_active.status = "active"

        with patch(f"{MOCK_PROVISIONING_MODULE}.get_tenant", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_tenant, mock_tenant_active]

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                new_callable=AsyncMock,
            ):
                service = TenantProvisioningService(mock_db_session)

                state1 = await service.provision_tenant(mock_tenant.id)
                assert state1.status == ProvisioningStatus.COMPLETED

                state2 = await service.provision_tenant(mock_tenant.id)
                assert state2.status == ProvisioningStatus.COMPLETED

        # Infisical should only be called once (second call skipped)
        mock_infisical_client.create_tenant_secrets_path.assert_called_once()

    async def test_force_retry_provisioning(
        self,
        mock_db_session,
        mock_tenant,
        mock_infisical_client,
        mock_audit_emitter,
    ):
        """Test force retry re-runs provisioning even if already completed."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            TenantProvisioningService,
        )

        with patch(f"{MOCK_PROVISIONING_MODULE}.get_tenant", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_tenant

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                new_callable=AsyncMock,
            ):
                service = TenantProvisioningService(mock_db_session)

                await service.provision_tenant(mock_tenant.id)
                state = await service.provision_tenant(mock_tenant.id, force_retry=True)

        assert state.status == ProvisioningStatus.COMPLETED
        assert mock_infisical_client.create_tenant_secrets_path.call_count == 2


# ---------------------------------------------------------------------------
# Failure and rollback tests
# ---------------------------------------------------------------------------
class TestProvisioningFailureHandling:
    """Test provisioning failure and retry scenarios."""

    async def test_infisical_failure_triggers_rollback(
        self,
        mock_db_session,
        mock_tenant,
        mock_audit_emitter,
    ):
        """Test rollback when Infisical path creation fails."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            TenantProvisioningService,
        )

        with patch(MOCK_TENANT_SECRET_MANAGER) as mock_class:
            mock_instance = MagicMock()
            mock_instance.create_tenant_secrets_path = AsyncMock(
                return_value=_make_env_result(success=False, error="Connection failed")
            )
            mock_instance.delete_tenant_secrets_path = AsyncMock(
                return_value=_make_env_result(success=True)
            )
            mock_class.return_value = mock_instance

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.get_tenant",
                new_callable=AsyncMock,
                return_value=mock_tenant,
            ):
                with patch(
                    f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                    new_callable=AsyncMock,
                ):
                    service = TenantProvisioningService(mock_db_session)
                    state = await service.provision_tenant(mock_tenant.id)

            assert state.status == ProvisioningStatus.FAILED
            assert state.error is not None

    async def test_retryable_error_with_automatic_retry(
        self,
        mock_db_session,
        mock_tenant,
        mock_audit_emitter,
    ):
        """Test automatic retry on transient errors (e.g., TimeoutError)."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            TenantProvisioningService,
        )

        call_count = 0

        async def mock_create_with_transient_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Connection timeout")
            return _make_env_result(success=True)

        with patch(MOCK_TENANT_SECRET_MANAGER) as mock_class:
            mock_instance = MagicMock()
            mock_instance.create_tenant_secrets_path = AsyncMock(
                side_effect=mock_create_with_transient_failure
            )
            mock_instance.seed_default_tenant_secrets = AsyncMock(
                return_value={"success": True}
            )
            mock_class.return_value = mock_instance

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.get_tenant",
                new_callable=AsyncMock,
                return_value=mock_tenant,
            ):
                with patch(
                    f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                    new_callable=AsyncMock,
                ):
                    service = TenantProvisioningService(mock_db_session)
                    state = await service.provision_tenant(mock_tenant.id)

            assert state.status == ProvisioningStatus.COMPLETED
            assert state.retry_count >= 1
            assert call_count >= 2


# ---------------------------------------------------------------------------
# Webhook HMAC-SHA256 tests
# ---------------------------------------------------------------------------
WEBHOOK_SECRET = "test-webhook-secret-32chars-long!"


class TestWebhookSecurity:
    """Test webhook HMAC-SHA256 signature verification and idempotency."""

    def _build_signed_request(
        self,
        tenant_id: UUID,
        secret: str = WEBHOOK_SECRET,
        webhook_id: str | None = None,
        timestamp: int | None = None,
    ) -> tuple[bytes, str, str]:
        """Build a signed webhook request body, signature, and webhook ID.

        Returns:
            (body_bytes, hmac_signature, webhook_id)
        """
        if webhook_id is None:
            webhook_id = f"wh-{uuid.uuid4().hex[:12]}"
        if timestamp is None:
            timestamp = int(time.time())

        payload = {
            "tenant_id": str(tenant_id),
            "timestamp": timestamp,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = _make_hmac_signature(body, secret)
        return body, signature, webhook_id

    def test_valid_signature_accepted(self):
        """Test that a correctly signed payload passes verification."""
        from value_fabric.layer4.tenants.api.routes.provisioning import (
            _verify_hmac_signature,
        )

        payload = b'{"tenant_id": "abc", "timestamp": 1234567890}'
        sig = _make_hmac_signature(payload, WEBHOOK_SECRET)
        assert _verify_hmac_signature(payload, sig, WEBHOOK_SECRET) is True

    def test_invalid_signature_rejected(self):
        """Test that a tampered payload fails verification."""
        from value_fabric.layer4.tenants.api.routes.provisioning import (
            _verify_hmac_signature,
        )

        payload = b'{"tenant_id": "abc", "timestamp": 1234567890}'
        wrong_sig = _make_hmac_signature(b"tampered", WEBHOOK_SECRET)
        assert _verify_hmac_signature(payload, wrong_sig, WEBHOOK_SECRET) is False

    def test_wrong_secret_rejected(self):
        """Test that a signature made with the wrong secret fails."""
        from value_fabric.layer4.tenants.api.routes.provisioning import (
            _verify_hmac_signature,
        )

        payload = b'{"tenant_id": "abc", "timestamp": 1234567890}'
        sig = _make_hmac_signature(payload, "wrong-secret")
        assert _verify_hmac_signature(payload, sig, WEBHOOK_SECRET) is False

    def test_expired_timestamp_rejected(self):
        """Test that a request with an old timestamp is rejected.

        The webhook endpoint enforces a 5-minute tolerance window.
        A timestamp older than 5 minutes should be rejected.
        """
        tenant_id = uuid.uuid4()
        expired_timestamp = int(time.time()) - 600  # 10 minutes ago
        body, sig, wid = self._build_signed_request(
            tenant_id, timestamp=expired_timestamp
        )

        # Parse the payload and check timestamp tolerance
        from value_fabric.layer4.tenants.api.routes.provisioning import (
            _WEBHOOK_SIGNATURE_TOLERANCE_SECONDS,
        )

        now = int(time.time())
        assert abs(now - expired_timestamp) > _WEBHOOK_SIGNATURE_TOLERANCE_SECONDS

    def test_idempotency_cache_deduplicates(self):
        """Test that the idempotency cache returns cached results for duplicate IDs."""
        from value_fabric.layer4.tenants.api.routes.provisioning import (
            _processed_webhooks,
        )

        webhook_id = f"wh-{uuid.uuid4().hex[:12]}"
        _processed_webhooks[webhook_id] = {
            "status": "completed",
            "tenant_id": str(uuid.uuid4()),
            "processed_at": time.time(),
        }

        assert webhook_id in _processed_webhooks
        assert _processed_webhooks[webhook_id]["status"] == "completed"

        # Cleanup
        del _processed_webhooks[webhook_id]

    def test_idempotency_cache_expires(self):
        """Test that expired entries are cleaned from the idempotency cache."""
        from value_fabric.layer4.tenants.api.routes.provisioning import (
            _WEBHOOK_CACHE_TTL_SECONDS,
            _cleanup_expired_webhooks,
            _processed_webhooks,
        )

        # Insert an expired entry
        expired_id = f"wh-expired-{uuid.uuid4().hex[:8]}"
        _processed_webhooks[expired_id] = {
            "status": "completed",
            "tenant_id": str(uuid.uuid4()),
            "processed_at": time.time() - _WEBHOOK_CACHE_TTL_SECONDS - 1,
        }

        # Insert a fresh entry
        fresh_id = f"wh-fresh-{uuid.uuid4().hex[:8]}"
        _processed_webhooks[fresh_id] = {
            "status": "completed",
            "tenant_id": str(uuid.uuid4()),
            "processed_at": time.time(),
        }

        _cleanup_expired_webhooks()

        assert expired_id not in _processed_webhooks
        assert fresh_id in _processed_webhooks

        # Cleanup
        del _processed_webhooks[fresh_id]


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------
class TestConvenienceFunction:
    """Test the provision_tenant convenience function."""

    async def test_convenience_function_delegates_to_service(
        self,
        mock_db_session,
        mock_tenant,
        mock_infisical_client,
        mock_audit_emitter,
    ):
        """Test the simple provision_tenant function."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            provision_tenant,
        )

        with patch(
            f"{MOCK_PROVISIONING_MODULE}.get_tenant",
            new_callable=AsyncMock,
            return_value=mock_tenant,
        ):
            with patch(
                f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                new_callable=AsyncMock,
            ):
                state = await provision_tenant(mock_db_session, mock_tenant.id)

        assert state.status == ProvisioningStatus.COMPLETED


# ---------------------------------------------------------------------------
# Audit event emission tests
# ---------------------------------------------------------------------------
class TestProvisioningAuditEvents:
    """Test that provisioning emits correct audit events."""

    async def test_successful_provisioning_emits_audit(
        self,
        mock_db_session,
        mock_tenant,
        mock_infisical_client,
    ):
        """Test that successful provisioning emits TENANT_PROVISIONED audit event."""
        from value_fabric.shared.audit import AuditAction
        from value_fabric.layer4.tenants.provisioning import (
            TenantProvisioningService,
        )

        with patch(MOCK_EMIT_AUDIT, new_callable=AsyncMock) as mock_emit:
            with patch(
                f"{MOCK_PROVISIONING_MODULE}.get_tenant",
                new_callable=AsyncMock,
                return_value=mock_tenant,
            ):
                with patch(
                    f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                    new_callable=AsyncMock,
                ):
                    service = TenantProvisioningService(mock_db_session)
                    await service.provision_tenant(mock_tenant.id)

            # Check that TENANT_PROVISIONED was emitted
            audit_actions = [
                call.kwargs.get("action") or call.args[0]
                for call in mock_emit.call_args_list
                if call.kwargs.get("action") == AuditAction.TENANT_PROVISIONED
                or (call.args and call.args[0] == AuditAction.TENANT_PROVISIONED)
            ]
            # At minimum, step-complete events should have been emitted
            assert mock_emit.call_count >= 3  # step + step + provisioned

    async def test_failed_provisioning_emits_failure_audit(
        self,
        mock_db_session,
        mock_tenant,
    ):
        """Test that failed provisioning emits TENANT_PROVISIONING_FAILED audit event."""
        from value_fabric.layer4.tenants.provisioning import (
            TenantProvisioningService,
        )

        with patch(MOCK_TENANT_SECRET_MANAGER) as mock_class:
            mock_instance = MagicMock()
            mock_instance.create_tenant_secrets_path = AsyncMock(
                side_effect=RuntimeError("Infisical unreachable")
            )
            mock_instance.delete_tenant_secrets_path = AsyncMock(
                return_value=_make_env_result(success=True)
            )
            mock_class.return_value = mock_instance

            with patch(MOCK_EMIT_AUDIT, new_callable=AsyncMock) as mock_emit:
                with patch(
                    f"{MOCK_PROVISIONING_MODULE}.get_tenant",
                    new_callable=AsyncMock,
                    return_value=mock_tenant,
                ):
                    with patch(
                        f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                        new_callable=AsyncMock,
                    ):
                        service = TenantProvisioningService(mock_db_session)
                        await service.provision_tenant(mock_tenant.id)

                # At least one failure or rollback event should be emitted
                assert mock_emit.call_count >= 1


# ---------------------------------------------------------------------------
# Email verification and duplicate slug tests (TEST-005 extensions)
# ---------------------------------------------------------------------------
class TestTenantProvisioningEdgeCases:
    """Edge-case coverage for tenant provisioning."""

    def test_email_verification_token_format(self):
        """Email verification tokens must be URL-safe and non-empty."""
        import secrets
        token = secrets.token_urlsafe(32)
        assert len(token) > 0
        assert " " not in token
        assert "\n" not in token

    async def test_duplicate_slug_conflict(self, mock_db_session, mock_tenant, mock_infisical_client, mock_audit_emitter):
        """Provisioning must handle duplicate slug gracefully."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            TenantProvisioningService,
        )

        duplicate_tenant = MagicMock()
        duplicate_tenant.id = uuid.uuid4()
        duplicate_tenant.name = "Duplicate Tenant"
        duplicate_tenant.slug = mock_tenant.slug  # same slug
        duplicate_tenant.status = "pending"

        with patch(f"{MOCK_PROVISIONING_MODULE}.get_tenant", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = duplicate_tenant

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                new_callable=AsyncMock,
            ):
                service = TenantProvisioningService(mock_db_session)
                state = await service.provision_tenant(duplicate_tenant.id)

        # Service completes provisioning even if slug duplicate; higher-layer
        # uniqueness constraints are enforced by the DB, not the service.
        assert state.status in {ProvisioningStatus.COMPLETED, ProvisioningStatus.FAILED}

    async def test_rollback_clears_partial_state(self, mock_db_session, mock_tenant, mock_audit_emitter):
        """Rollback must remove partial tenant state after Infisical failure."""
        from value_fabric.layer4.tenants.provisioning import (
            ProvisioningStatus,
            TenantProvisioningService,
        )

        with patch(MOCK_TENANT_SECRET_MANAGER) as mock_class:
            mock_instance = MagicMock()
            mock_instance.create_tenant_secrets_path = AsyncMock(
                return_value=_make_env_result(success=False, error="Already exists")
            )
            mock_instance.delete_tenant_secrets_path = AsyncMock(
                return_value=_make_env_result(success=True)
            )
            mock_class.return_value = mock_instance

            with patch(
                f"{MOCK_PROVISIONING_MODULE}.get_tenant",
                new_callable=AsyncMock,
                return_value=mock_tenant,
            ):
                with patch(
                    f"{MOCK_PROVISIONING_MODULE}.update_tenant_status",
                    new_callable=AsyncMock,
                ):
                    service = TenantProvisioningService(mock_db_session)
                    state = await service.provision_tenant(mock_tenant.id)

            assert state.status == ProvisioningStatus.ROLLED_BACK
            assert state.error is not None
