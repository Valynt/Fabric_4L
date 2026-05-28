from __future__ import annotations

"""Deterministic replay normalization helpers for Layer 4 workflow tests."""


from collections.abc import Mapping, Sequence
from copy import deepcopy
import re
from typing import Any

NON_DETERMINISTIC_KEY_PATTERNS = {
    "timestamp",
    "created_at",
    "updated_at",
    "started_at",
    "completed_at",
    "resumed_at",
    "trace_id",
    "span_id",
    "request_id",
    "run_id",
    "checkpoint_id",
    "event_id",
    "idempotency_key",
}

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
ISO_8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _is_nondeterministic_key(key: str) -> bool:
    key_lower = key.lower()
    return key_lower in NON_DETERMINISTIC_KEY_PATTERNS or key_lower.endswith("_timestamp")


def _normalize_primitive(value: Any) -> Any:
    if isinstance(value, str):
        if UUID_V4_PATTERN.match(value):
            return "<normalized:uuid-v4>"
        if ISO_8601_PATTERN.match(value):
            return "<normalized:timestamp>"
    return value


def normalize_checkpoint_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a workflow checkpoint snapshot for replay comparison."""

    def _normalize(value: Any, key: str | None = None) -> Any:
        if isinstance(value, Mapping):
            out: dict[str, Any] = {}
            for child_key in sorted(value.keys()):
                child_value = value[child_key]
                if _is_nondeterministic_key(child_key):
                    out[child_key] = f"<normalized:{child_key.lower()}>"
                else:
                    out[child_key] = _normalize(child_value, key=child_key)
            return out

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [_normalize(item, key=key) for item in value]

        return _normalize_primitive(value)

    snapshot_copy = deepcopy(dict(snapshot))
    return _normalize(snapshot_copy)


def assert_semantically_equivalent_replay(
    *,
    baseline_snapshot: Mapping[str, Any],
    replayed_snapshot: Mapping[str, Any],
) -> None:
    """Assert semantic equivalence between baseline and replay snapshots."""
    normalized_baseline = normalize_checkpoint_snapshot(baseline_snapshot)
    normalized_replay = normalize_checkpoint_snapshot(replayed_snapshot)
    assert normalized_baseline == normalized_replay
