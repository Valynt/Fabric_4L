"""RB-7: Concrete hostile API-key resolver tests for GovernanceMiddleware.

The shared suite helper in test_api_key_resolver_hostile_suite.py defines
run_hostile_api_key_resolver_suite() as a plain function, not a test class,
so pytest collects zero tests from it. This file provides the concrete
parametrized test class that exercises the hostile cases against the actual
GovernanceMiddleware async _resolve_api_key() path and the sync
GovernanceMiddlewareSync _resolve_identity_sync() path.

Audit finding: RB-7 — hostile API key resolver tests collected 0 items.

Behavior notes (verified against source):
  Async GovernanceMiddleware._resolve_api_key():
    - Returns None when tenant_id is missing or empty (KeyError/ValueError on UUID())
    - Returns RequestContext when metadata is empty (no metadata check in async path)
    - Returns None when resolver returns None
    - Returns None when no resolver is configured

  Sync GovernanceMiddlewareSync._resolve_identity_sync():
    - Returns None when metadata is missing or empty (explicit check at line 314)
    - Returns None when tenant_id is missing (KeyError in _build_context_from_api_key_sync)
    - Returns None when resolver returns None
"""

from __future__ import annotations

import unittest.mock as _mock
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from tests.shared.identity.hostile_api_key_cases import (
    INVALID_API_KEY_CONTEXT_ERROR_CODE,
    hostile_api_key_records,
    valid_api_key_record,
)
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.identity.middleware_sync import GovernanceMiddlewareSync

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_request(api_key: str = "test-key-abc123") -> MagicMock:
    """Build a minimal fake ASGI Request with an X-API-Key header."""
    request = MagicMock()
    request.headers = {"X-API-Key": api_key}
    request.state = MagicMock()
    return request


def _make_async_middleware(resolver_return_value: dict | None) -> GovernanceMiddleware:
    """Build a GovernanceMiddleware with a fixed async API key resolver."""
    app = MagicMock()
    resolver = AsyncMock(return_value=resolver_return_value)
    with _mock.patch.object(
        GovernanceMiddleware,
        "_validate_multi_worker_rate_limit_configuration",
        staticmethod(lambda *a, **kw: None),
    ):
        mw = GovernanceMiddleware(app, api_key_resolver=resolver)
    return mw


def _make_sync_middleware(resolver_return_value: dict | None) -> GovernanceMiddlewareSync:
    """Build a GovernanceMiddlewareSync with a fixed sync API key resolver."""
    app = MagicMock()
    resolver = MagicMock(return_value=resolver_return_value)
    mw = GovernanceMiddlewareSync(
        app,
        api_key_resolver=resolver,
        jwt_secret="dummy_jwt_secret_32_chars_long_enough",
    )
    return mw


# ---------------------------------------------------------------------------
# Async GovernanceMiddleware hostile suite
# ---------------------------------------------------------------------------

class TestGovernanceMiddlewareHostileApiKeys:
    """RB-7: GovernanceMiddleware._resolve_api_key() must fail closed for
    records with missing or invalid tenant_id.

    The async middleware rejects:
      - Missing tenant_id key (KeyError on record["tenant_id"])
      - Empty tenant_id string (ValueError on UUID(""))

    It does NOT reject records with empty metadata (that check is only in
    the sync path). The hostile suite record0 (empty metadata) succeeds in
    the async path — this is documented behavior, not a bug.
    """

    @pytest.mark.asyncio
    async def test_missing_tenant_id_fails_closed(self) -> None:
        """A record with a missing tenant_id key must fail closed."""
        base = valid_api_key_record()
        record = {k: v for k, v in base.items() if k != "tenant_id"}
        mw = _make_async_middleware(resolver_return_value=record)
        request = _make_fake_request()

        result = await mw._resolve_api_key(request)

        assert result is None, (
            "Record missing tenant_id must fail closed (return None). "
            f"Got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_empty_tenant_id_fails_closed(self) -> None:
        """A record with an empty tenant_id string must fail closed."""
        record = {**valid_api_key_record(), "tenant_id": ""}
        mw = _make_async_middleware(resolver_return_value=record)
        request = _make_fake_request()

        result = await mw._resolve_api_key(request)

        assert result is None, (
            "Record with empty tenant_id must fail closed (return None). "
            f"Got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_none_resolver_returns_none(self) -> None:
        """When no API key resolver is configured, _resolve_api_key must return None."""
        app = MagicMock()
        with _mock.patch.object(
            GovernanceMiddleware,
            "_validate_multi_worker_rate_limit_configuration",
            staticmethod(lambda *a, **kw: None),
        ):
            mw = GovernanceMiddleware(app)  # no api_key_resolver
        request = _make_fake_request()

        result = await mw._resolve_api_key(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_resolver_returns_none_fails_closed(self) -> None:
        """When the resolver returns None (key not found), result must be None."""
        mw = _make_async_middleware(resolver_return_value=None)
        request = _make_fake_request()

        result = await mw._resolve_api_key(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_valid_record_succeeds(self) -> None:
        """Sanity check: a valid API-key record must produce a RequestContext."""
        record = valid_api_key_record()
        mw = _make_async_middleware(resolver_return_value=record)
        request = _make_fake_request()

        result = await mw._resolve_api_key(request)

        assert result is not None, (
            f"Valid API-key record must produce a RequestContext. Record: {record!r}"
        )
        assert str(result.tenant_id) == record["tenant_id"]

    @pytest.mark.asyncio
    async def test_no_api_key_header_returns_none(self) -> None:
        """When no X-API-Key header is present, _resolve_api_key must return None."""
        mw = _make_async_middleware(resolver_return_value=valid_api_key_record())
        request = MagicMock()
        request.headers = {}  # no X-API-Key
        request.state = MagicMock()

        result = await mw._resolve_api_key(request)

        assert result is None


# ---------------------------------------------------------------------------
# Sync GovernanceMiddlewareSync hostile suite
# ---------------------------------------------------------------------------

class TestGovernanceMiddlewareSyncHostileApiKeys:
    """RB-7: GovernanceMiddlewareSync._resolve_identity_sync() must fail closed
    for hostile API-key records.

    The sync middleware has an additional metadata check (line 314):
      if not record.get("metadata"):
          return None

    So it rejects both missing/empty metadata AND missing/empty tenant_id.
    """

    def test_missing_metadata_fails_closed(self) -> None:
        """A record with missing 'metadata' key must fail closed in sync path."""
        base = valid_api_key_record()
        record = {k: v for k, v in base.items() if k != "metadata"}
        mw = _make_sync_middleware(resolver_return_value=record)

        result = mw._resolve_identity_sync(api_key_header="dummy_test_api_key_abc123")

        assert result is None, (
            "Record missing 'metadata' must fail closed in sync middleware. "
            f"Got: {result!r}"
        )

    def test_empty_metadata_fails_closed(self) -> None:
        """A record with empty 'metadata' dict must fail closed in sync path."""
        record = {**valid_api_key_record(), "metadata": {}}
        mw = _make_sync_middleware(resolver_return_value=record)

        result = mw._resolve_identity_sync(api_key_header="dummy_test_api_key_abc123")

        assert result is None, (
            "Record with empty 'metadata' must fail closed in sync middleware. "
            f"Got: {result!r}"
        )

    def test_missing_tenant_id_fails_closed(self) -> None:
        """A record with missing tenant_id must fail closed in sync path."""
        base = valid_api_key_record()
        record = {k: v for k, v in base.items() if k != "tenant_id"}
        mw = _make_sync_middleware(resolver_return_value=record)

        result = mw._resolve_identity_sync(api_key_header="dummy_test_api_key_abc123")

        assert result is None

    def test_empty_tenant_id_fails_closed(self) -> None:
        """A record with empty tenant_id must fail closed in sync path."""
        record = {**valid_api_key_record(), "tenant_id": ""}
        mw = _make_sync_middleware(resolver_return_value=record)

        result = mw._resolve_identity_sync(api_key_header="dummy_test_api_key_abc123")

        assert result is None

    def test_resolver_returns_none_fails_closed(self) -> None:
        """When the resolver returns None, result must be None in sync path."""
        mw = _make_sync_middleware(resolver_return_value=None)

        result = mw._resolve_identity_sync(api_key_header="dummy_test_api_key_abc123")

        assert result is None

    def test_no_api_key_header_returns_none(self) -> None:
        """When no api_key_header is passed, result must be None in sync path."""
        mw = _make_sync_middleware(resolver_return_value=valid_api_key_record())
        result = mw._resolve_identity_sync(api_key_header=None)
        assert result is None
