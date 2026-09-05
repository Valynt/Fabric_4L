"""V1-TENANCY-011: DSAR export download tokens — expiry and forgery tests.

Covers, against ``services/api/app/services/dsar_service.py``:

* Download tokens expire server-side (replaying an expired token is denied).
* Tokens bind package id + requester user id + expiry via HMAC; a different
  requester (cross-user / cross-tenant) is denied.
* Forged tokens (tampered expiry, tampered requester, garbage signature)
  are denied.
* The expiry embedded in the token comes from the server-side package
  record, not from client input.

Self-contained: structlog / prometheus_client / app.* dependencies are
stubbed in sys.modules.
"""

from __future__ import annotations

import dataclasses
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_API_APP = _PROJECT_ROOT / "services" / "api"


@dataclasses.dataclass
class _DSARPackage:
    id: str
    dsar_request_id: str
    tenant_id: str
    requester_user_id: str
    export_payload: dict
    expires_at: str


def _install_stubs() -> None:
    structlog_mod = types.ModuleType("structlog")
    structlog_mod.get_logger = lambda *a, **k: MagicMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("structlog", structlog_mod)

    prom_mod = types.ModuleType("prometheus_client")
    prom_mod.Histogram = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
    sys.modules.setdefault("prometheus_client", prom_mod)

    app_mod = types.ModuleType("app")
    app_mod.__path__ = [str(_API_APP / "app")]  # type: ignore[attr-defined]
    sys.modules.setdefault("app", app_mod)

    core_mod = types.ModuleType("app.core")
    core_mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("app.core", core_mod)

    config_mod = types.ModuleType("app.core.config")
    config_mod.get_settings = lambda: types.SimpleNamespace(  # type: ignore[attr-defined]
        secret_key="test-signing-key"
    )
    sys.modules.setdefault("app.core.config", config_mod)

    db_mod = types.ModuleType("app.core.database")
    db_mod.db = MagicMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("app.core.database", db_mod)

    metrics_mod = types.ModuleType("app.core.metrics")
    metrics_mod.registry = MagicMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("app.core.metrics", metrics_mod)

    models_mod = types.ModuleType("app.models")
    models_mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("app.models", models_mod)
    schemas_mod = types.ModuleType("app.models.schemas")
    schemas_mod.DSARPackage = _DSARPackage  # type: ignore[attr-defined]
    schemas_mod.DSARRequestCreate = MagicMock()  # type: ignore[attr-defined]
    schemas_mod.DSARRequestRecord = MagicMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("app.models.schemas", schemas_mod)


_install_stubs()
sys.path.insert(0, str(_API_APP))

from app.services import dsar_service  # noqa: E402


def _package(*, expires_in_hours: float = 1.0) -> _DSARPackage:
    return _DSARPackage(
        id="pkg-1",
        dsar_request_id="dsar-1",
        tenant_id="tenant-a",
        requester_user_id="user-a",
        export_payload={"tenant_id": "tenant-a"},
        expires_at=(datetime.now(UTC) + timedelta(hours=expires_in_hours)).isoformat(),
    )


class TestDsarDownloadTokenExpiry:
    def test_valid_token_accepted_within_expiry(self) -> None:
        pkg = _package()
        token = dsar_service.issue_download_url(pkg).split("token=", 1)[1]
        dsar_service.validate_download_access(
            pkg, requester_user_id="user-a", token=token
        )

    def test_expired_token_replay_denied(self) -> None:
        """Hostile: replaying a token after expiry must fail."""
        pkg = _package(expires_in_hours=-1.0)  # already expired
        token = dsar_service.issue_download_url(pkg).split("token=", 1)[1]
        with pytest.raises(PermissionError):
            dsar_service.validate_download_access(
                pkg, requester_user_id="user-a", token=token
            )

    def test_cross_requester_token_denied(self) -> None:
        """Hostile: tenant B's user cannot use tenant A requester's token."""
        pkg = _package()
        token = dsar_service.issue_download_url(pkg).split("token=", 1)[1]
        with pytest.raises(PermissionError):
            dsar_service.validate_download_access(
                pkg, requester_user_id="user-b", token=token
            )

    def test_tampered_expiry_denied(self) -> None:
        """Hostile: editing the embedded expiry breaks the HMAC."""
        pkg = _package()
        token = dsar_service.issue_download_url(pkg).split("token=", 1)[1]
        parts = token.split("|")
        parts[2] = (datetime.now(UTC) + timedelta(days=365)).isoformat()
        forged = "|".join(parts)
        with pytest.raises(PermissionError):
            dsar_service.validate_download_access(
                pkg, requester_user_id="user-a", token=forged
            )

    def test_tampered_requester_denied(self) -> None:
        pkg = _package()
        token = dsar_service.issue_download_url(pkg).split("token=", 1)[1]
        parts = token.split("|")
        parts[1] = "user-b"
        forged = "|".join(parts)
        with pytest.raises(PermissionError):
            dsar_service.validate_download_access(
                pkg, requester_user_id="user-b", token=forged
            )

    def test_garbage_signature_denied(self) -> None:
        pkg = _package()
        token = dsar_service.issue_download_url(pkg).split("token=", 1)[1]
        parts = token.split("|")
        parts[4] = "0" * 64
        forged = "|".join(parts)
        with pytest.raises(PermissionError):
            dsar_service.validate_download_access(
                pkg, requester_user_id="user-a", token=forged
            )

    def test_malformed_token_denied(self) -> None:
        pkg = _package()
        with pytest.raises(PermissionError):
            dsar_service.validate_download_access(
                pkg, requester_user_id="user-a", token="not-a-token"
            )
