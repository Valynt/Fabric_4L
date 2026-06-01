"""Reusable hostile API key resolver assertions.

Imported by layer-specific test suites to ensure all services enforce
the same baseline security posture against hostile API key payloads.
"""

from __future__ import annotations

from typing import Any

from value_fabric.shared.identity.middleware_sync import INVALID_API_KEY_CONTEXT_ERROR_CODE


def run_hostile_api_key_resolver_suite(
    resolver_fn: callable,
    record: dict[str, Any],
) -> None:
    """Run the standard hostile API key assertion suite against a resolver.

    Args:
        resolver_fn: Callable that takes a ``record`` dict and returns
            ``(context, error_code)`` where *context* is the resolved
            identity context (or ``None`` on rejection) and *error_code*
            is a string error constant (or ``None`` on success).
        record: A single hostile API key record from
            :func:`hostile_api_key_records`.

    Raises:
        AssertionError: If the resolver accepts the hostile key or
            leaks raw key material.
    """
    # The resolver must not raise — hostile inputs are expected.
    try:
        context, error_code = resolver_fn(record)
    except Exception as exc:
        # Crashing on hostile input is also a failure mode we track,
        # but for this suite we require graceful rejection, not an
        # unhandled exception.
        raise AssertionError(
            f"Resolver raised {type(exc).__name__} on hostile record: {exc}"
        ) from exc

    # Hostile keys must be rejected (context is None).
    assert context is None, (
        f"Hostile API key record was unexpectedly accepted. "
        f"record={_sanitize_record(record)}"
    )

    # When rejected, the expected error code must be present.
    assert error_code == INVALID_API_KEY_CONTEXT_ERROR_CODE, (
        f"Expected error code {INVALID_API_KEY_CONTEXT_ERROR_CODE!r}, "
        f"got {error_code!r}"
    )

    # Verify that raw key material is not present in the returned error
    # or context objects.  This is a defence-in-depth check against
    # information leakage.
    raw_key = str(record.get("key_id", ""))
    if raw_key:
        for obj_name, obj in [("context", context), ("error_code", error_code)]:
            if obj is not None:
                obj_str = str(obj)
                assert raw_key not in obj_str, (
                    f"Raw key material leaked in {obj_name}: {obj_str!r}"
                )


def _sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *record* safe for assertion messages."""
    safe = dict(record)
    if "key_id" in safe:
        key = str(safe["key_id"])
        if len(key) > 20:
            safe["key_id"] = key[:10] + "..." + key[-5:]
    return safe
