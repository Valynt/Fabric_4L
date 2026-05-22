"""Shared hostile-case suite: migrated adapters must fail closed for malformed API-key records."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.shared.identity.hostile_api_key_cases import (
    INVALID_API_KEY_CONTEXT_ERROR_CODE,
    hostile_api_key_records,
)


@pytest.mark.parametrize("record", hostile_api_key_records())
def run_hostile_api_key_resolver_suite(
    adapter_resolver: Callable[[dict], tuple[object | None, str | None]],
    record: dict,
) -> None:
    context, error_code = adapter_resolver(record)
    assert context is None, "Hostile API-key record must fail closed"
    assert error_code == INVALID_API_KEY_CONTEXT_ERROR_CODE
