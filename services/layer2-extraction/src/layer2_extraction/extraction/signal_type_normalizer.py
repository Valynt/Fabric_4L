"""Normalization utilities for operational signal type labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from layer2_extraction.models.operational_signal_extraction import OperationalSignal, SignalType

_RAW_SIGNAL_TYPE_TO_CANONICAL: dict[str, SignalType] = {
    "pain": "pain",
    "opportunity": "opportunity",
    "risk": "risk",
    "trend": "trend",
    "issue": "pain",
    "problem": "pain",
    "challenge": "pain",
    "blocker": "pain",
    "threat": "risk",
    "concern": "risk",
    "warning": "risk",
    "upside": "opportunity",
    "expansion": "opportunity",
    "growth": "opportunity",
    "improvement": "opportunity",
    "pattern": "trend",
    "signal": "trend",
}


@dataclass(frozen=True)
class QuarantinedSignalType:
    raw_label: str
    reason: str
    payload: dict[str, Any]


def normalize_signal_type(raw_label: str) -> SignalType | None:
    normalized = raw_label.strip().lower()
    return _RAW_SIGNAL_TYPE_TO_CANONICAL.get(normalized)


def normalize_and_partition_signal_payloads(
    signal_payloads: list[dict[str, Any]],
) -> tuple[list[OperationalSignal], list[QuarantinedSignalType]]:
    canonical: list[OperationalSignal] = []
    quarantined: list[QuarantinedSignalType] = []

    for payload in signal_payloads:
        raw_label = str(payload.get("signal_type", ""))
        normalized_type = normalize_signal_type(raw_label)
        if normalized_type is None:
            quarantined.append(
                QuarantinedSignalType(
                    raw_label=raw_label,
                    reason="unknown_signal_type",
                    payload=payload,
                )
            )
            continue

        canonical_payload = dict(payload)
        canonical_payload["signal_type"] = normalized_type
        canonical.append(OperationalSignal.model_validate(canonical_payload))

    return canonical, quarantined
