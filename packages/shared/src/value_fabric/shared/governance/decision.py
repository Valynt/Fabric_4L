from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionEffect(str, Enum):
    """Outcome of a policy decision."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    INDETERMINATE = "INDETERMINATE"


class Obligation(str, Enum):
    """Typed obligations attached to a policy decision."""

    MASK = "MASK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    AUDIT = "AUDIT"
    RATE = "RATE"
    ABOM_DENIED = "ABOM_DENIED"
    INVARIANT_BLOCKED = "INVARIANT_BLOCKED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    LOG = "LOG"


def _normalize_obligations(obligations: list[Any] | tuple[Any, ...] | None) -> list[str]:
    normalized: list[str] = []
    for item in obligations or []:
        if isinstance(item, Obligation):
            normalized.append(item.value)
        elif item is not None:
            normalized.append(str(item))
    return normalized


@dataclass(frozen=True)
class Decision:
    """Canonical, transport-neutral policy outcome."""

    effect: DecisionEffect
    reason_code: str
    reason: str
    obligations: list[str] = field(default_factory=list)
    policy_ids: list[str] = field(default_factory=list)
    policy_bundle_hash: str | None = None
    decision_id: str | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    action: str | None = None
    resource: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "obligations", _normalize_obligations(self.obligations))
        object.__setattr__(self, "policy_ids", [str(item) for item in self.policy_ids])

    @property
    def allowed(self) -> bool:
        return self.effect == DecisionEffect.ALLOW

    @property
    def denied(self) -> bool:
        return self.effect == DecisionEffect.DENY

    @property
    def indeterminate(self) -> bool:
        return self.effect == DecisionEffect.INDETERMINATE


__all__ = [
    "Decision",
    "DecisionEffect",
    "Obligation",
]
