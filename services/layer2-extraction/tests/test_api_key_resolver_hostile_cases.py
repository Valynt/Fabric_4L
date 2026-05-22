from __future__ import annotations

import pytest

from tests.shared.identity.hostile_api_key_cases import hostile_api_key_records
from tests.shared.identity.test_api_key_resolver_hostile_suite import run_hostile_api_key_resolver_suite
from value_fabric.shared.identity.middleware_sync import GovernanceMiddlewareSync, INVALID_API_KEY_CONTEXT_ERROR_CODE


def _adapter_resolver(record: dict):
    middleware = GovernanceMiddlewareSync(None, api_key_resolver=lambda _: record)
    context = middleware._resolve_identity_sync(api_key_header="vf_hostile")
    return context, INVALID_API_KEY_CONTEXT_ERROR_CODE if context is None else None


@pytest.mark.parametrize("record", hostile_api_key_records())
def test_layer2_middleware_sync_enforces_shared_hostile_cases(record: dict) -> None:
    run_hostile_api_key_resolver_suite(_adapter_resolver, record)
