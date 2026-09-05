"""V1-TENANCY-011: Hostile + allowed tests for tenant-scoped object storage.

Covers, against ``packages/shared/src/value_fabric/shared/storage/client.py``:

* Tenant B cannot reach Tenant A objects via direct storage path guessing
  (object keys are always re-prefixed with the *caller's* tenant scope).
* Object keys and tenant ids cannot contain path-traversal segments that
  escape the tenant prefix boundary (fail closed).
* Signed (presigned) URLs embed the tenant scope server-side.
* Signed URL expiry is bounded server-side and not client-controllable
  (no multi-year URLs, no zero/negative TTLs).

These tests are self-contained: boto3/botocore are stubbed in sys.modules so
no AWS/MinIO infrastructure or monorepo dependency installation is required.
"""

from __future__ import annotations

import asyncio
import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Self-contained boto3/botocore stubs (no real S3 endpoint needed).
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SHARED_SRC = _PROJECT_ROOT / "packages" / "shared" / "src"


class _StubClientError(Exception):
    """Minimal stand-in for botocore.exceptions.ClientError."""

    def __init__(self, code: str = "Unknown") -> None:
        super().__init__(code)
        self.response: dict[str, Any] = {"Error": {"Code": code}}


def _install_boto3_stubs() -> MagicMock:
    s3_client = MagicMock(name="s3_client")

    boto3_mod = types.ModuleType("boto3")
    boto3_mod.client = MagicMock(return_value=s3_client)  # type: ignore[attr-defined]

    botocore_mod = types.ModuleType("botocore")
    botocore_config_mod = types.ModuleType("botocore.config")

    class _Config:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    botocore_config_mod.Config = _Config  # type: ignore[attr-defined]
    botocore_exceptions_mod = types.ModuleType("botocore.exceptions")
    botocore_exceptions_mod.ClientError = _StubClientError  # type: ignore[attr-defined]

    sys.modules.setdefault("boto3", boto3_mod)
    sys.modules.setdefault("botocore", botocore_mod)
    sys.modules.setdefault("botocore.config", botocore_config_mod)
    sys.modules.setdefault("botocore.exceptions", botocore_exceptions_mod)
    return s3_client


_S3 = _install_boto3_stubs()
sys.path.insert(0, str(_SHARED_SRC))

from value_fabric.shared.storage.client import StorageClient  # noqa: E402


def _make_client() -> StorageClient:
    return StorageClient(
        endpoint_url="http://localhost:9000",
        access_key_id="test",
        secret_access_key="test",
        bucket="fabric4l-test",
    )


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Allowed behaviour: tenant scoping of prefixes and presigned URLs.
# ---------------------------------------------------------------------------

class TestTenantScopedPrefixes:
    def test_object_keys_are_prefixed_with_caller_tenant(self) -> None:
        client = _make_client()
        key_a = client._normalize_key("exports/report.pdf", tenant_id="tenant-a")
        key_b = client._normalize_key("exports/report.pdf", tenant_id="tenant-b")
        assert key_a != key_b
        assert key_a.startswith("tenant-tenant-a/")
        assert key_b.startswith("tenant-tenant-b/")

    def test_direct_storage_path_guess_is_reprefixed_not_raw(self) -> None:
        """Tenant B guessing Tenant A's full path must not hit the raw key."""
        client = _make_client()
        # Tenant B supplies the exact raw storage path of tenant A's object.
        guessed = client._normalize_key(
            "tenant-tenant-a/exports/report.pdf", tenant_id="tenant-b"
        )
        # The result must stay inside tenant B's own prefix.
        assert guessed.startswith("tenant-tenant-b/")
        assert guessed != "tenant-tenant-a/exports/report.pdf"

    def test_presigned_url_targets_tenant_prefixed_key(self) -> None:
        _S3.reset_mock()
        _S3.generate_presigned_url.return_value = "https://example.invalid/signed"
        client = _make_client()
        _run(client.generate_presigned_url(key="exports/x.pdf", tenant_id="tenant-a"))
        params = _S3.generate_presigned_url.call_args[1]["Params"]
        assert params["Key"].startswith("tenant-tenant-a/")


# ---------------------------------------------------------------------------
# Hostile: tenant id and key traversal must fail closed.
# ---------------------------------------------------------------------------

class TestTenantBoundaryTraversalDenied:
    @pytest.mark.parametrize(
        "bad_tenant",
        [
            "../tenant-a",
            "tenant-b/../tenant-a",
            "a/b",
            "..",
            "tenant a",  # whitespace
            "tenant\x00a",  # NUL byte
            "/tenant-a",
            "tenant-a/",
        ],
    )
    def test_malicious_tenant_id_is_rejected(self, bad_tenant: str) -> None:
        """Tenant ids containing separators/traversal must be refused."""
        client = _make_client()
        with pytest.raises((ValueError, Exception)) as excinfo:
            client._normalize_key("exports/report.pdf", tenant_id=bad_tenant)
        assert not isinstance(excinfo.value, AssertionError)

    @pytest.mark.parametrize(
        "bad_key",
        [
            "../tenant-tenant-a/exports/report.pdf",
            "exports/../../tenant-tenant-a/report.pdf",
            "..",
            "exports/..",
            "exports\\..\\tenant-a",  # windows-style separator
        ],
    )
    def test_malicious_object_key_is_rejected(self, bad_key: str) -> None:
        """Object keys containing traversal segments must be refused."""
        client = _make_client()
        with pytest.raises((ValueError, Exception)) as excinfo:
            client._normalize_key(bad_key, tenant_id="tenant-b")
        assert not isinstance(excinfo.value, AssertionError)


# ---------------------------------------------------------------------------
# Hostile: signed URL expiry must not be client-controllable.
# ---------------------------------------------------------------------------

class TestSignedUrlExpiryBounded:
    def test_expiry_cannot_exceed_server_side_maximum(self) -> None:
        """A 10-year expiry request must be rejected or clamped server-side."""
        _S3.reset_mock()
        _S3.generate_presigned_url.return_value = "https://example.invalid/signed"
        client = _make_client()
        ten_years = 10 * 365 * 24 * 3600
        try:
            _run(
                client.generate_presigned_url(
                    key="exports/x.pdf", tenant_id="tenant-a", expires_in=ten_years
                )
            )
        except ValueError:
            return  # fail-closed rejection is acceptable
        # If not rejected, the TTL handed to S3 must be clamped to <= 1 hour.
        expires = _S3.generate_presigned_url.call_args[1]["ExpiresIn"]
        assert expires <= 3600, (
            f"signed URL TTL {expires}s exceeds the server-side maximum; "
            "expiry is client-controllable"
        )

    @pytest.mark.parametrize("bad_ttl", [0, -1, -3600])
    def test_non_positive_expiry_rejected(self, bad_ttl: int) -> None:
        client = _make_client()
        with pytest.raises((ValueError, Exception)):
            _run(
                client.generate_presigned_url(
                    key="exports/x.pdf", tenant_id="tenant-a", expires_in=bad_ttl
                )
            )

    def test_expiry_is_bounded_for_presigned_url_params(self) -> None:
        """Whatever TTL reaches the S3 signer must be within server bounds."""
        _S3.reset_mock()
        _S3.generate_presigned_url.return_value = "https://example.invalid/signed"
        client = _make_client()
        _run(
            client.generate_presigned_url(
                key="exports/x.pdf", tenant_id="tenant-a", expires_in=600
            )
        )
        expires = _S3.generate_presigned_url.call_args[1]["ExpiresIn"]
        assert 0 < expires <= 3600


# ---------------------------------------------------------------------------
# Hostile: lifecycle deletion cannot cross the tenant prefix boundary.
# ---------------------------------------------------------------------------

class TestLifecycleDeletionTenantScoped:
    def test_delete_for_tenant_a_never_touches_tenant_b_prefix(self) -> None:
        _S3.reset_mock()
        client = _make_client()
        _run(client.delete_object(key="exports/report.pdf", tenant_id="tenant-a"))
        deleted_key = _S3.delete_object.call_args[1]["Key"]
        assert deleted_key.startswith("tenant-tenant-a/")
        assert not deleted_key.startswith("tenant-tenant-b/")

    def test_list_for_tenant_a_never_returns_tenant_b_objects(self) -> None:
        _S3.reset_mock()
        _S3.list_objects_v2.return_value = {"Contents": []}
        client = _make_client()
        _run(client.list_objects(prefix="", tenant_id="tenant-a"))
        listed_prefix = _S3.list_objects_v2.call_args[1]["Prefix"]
        assert re.match(r"^tenant-tenant-a/", listed_prefix)
