from __future__ import annotations

"""Central compatibility policy for deprecated Layer 3 aliases."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError

DEFAULT_COMPAT_DEPRECATION_PHASE = "warning_only"
DEPRECATION_ACCEPTANCE_THRESHOLDS: dict[str, int] = {
    "max_legacy_route_hits_7d": 0,
    "max_legacy_field_hits_7d": 0,
}


@dataclass(frozen=True)
class CompatibilityPolicy:
    """Lifecycle policy for Layer 3 legacy aliases."""

    phase: str = DEFAULT_COMPAT_DEPRECATION_PHASE
    deprecation_acceptance_thresholds: Mapping[str, int] | None = None

    def normalized_phase(self) -> str:
        return (self.phase or DEFAULT_COMPAT_DEPRECATION_PHASE).strip().lower()

    def assert_route_alias_enabled(
        self, alias_name: str, *, environment: str = "dev"
    ) -> None:
        phase = self.normalized_phase()
        if phase == "disable_non_prod" and environment.strip().lower() != "prod":
            raise ServiceUnavailableError(
                message=f"Legacy alias '{alias_name}' disabled in non-production"
            )
        if phase == "removed":
            raise ServiceUnavailableError(
                message=f"Legacy alias '{alias_name}' has been removed"
            )

    def ready_for_removal(self, snapshot: Mapping[str, Mapping[str, int]]) -> bool:
        thresholds = (
            self.deprecation_acceptance_thresholds or DEPRECATION_ACCEPTANCE_THRESHOLDS
        )
        route_total = sum(snapshot.get("route_hits", {}).values())
        field_total = sum(snapshot.get("legacy_field_hits", {}).values())
        return (
            route_total <= thresholds["max_legacy_route_hits_7d"]
            and field_total <= thresholds["max_legacy_field_hits_7d"]
        )


def get_route_alias_policy(app_state: Any) -> CompatibilityPolicy:
    """Resolve route alias policy from app state, preserving legacy fallback behavior."""
    phase = getattr(
        app_state, "layer3_compat_deprecation_phase", DEFAULT_COMPAT_DEPRECATION_PHASE
    )
    return CompatibilityPolicy(phase=phase)


def assert_legacy_route_alias_enabled(app_state: Any, alias_name: str) -> None:
    """Raise a stable service error when a route alias is not allowed in this phase."""
    environment = getattr(app_state, "environment", "dev")
    get_route_alias_policy(app_state).assert_route_alias_enabled(
        alias_name, environment=environment
    )


def deprecation_ready_for_removal(
    snapshot: Mapping[str, Mapping[str, int]],
    *,
    thresholds: Mapping[str, int] | None = None,
) -> bool:
    """Return whether compatibility usage is below hard-removal thresholds."""
    policy = CompatibilityPolicy(deprecation_acceptance_thresholds=thresholds)
    return policy.ready_for_removal(snapshot)
