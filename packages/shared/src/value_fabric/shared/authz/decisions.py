"""Decision persistence and domain-event correlation.

Requirement: every decision must be explainable, versioned, auditable, and
correlated to the resulting domain event. ``DecisionSink`` persists an
immutable decision record. Domain command handlers correlate a decision to the
resulting event via ``decision_id``, so audit lineage is unbroken even after
the fact.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol

from .models import AuthzDecision

logger = logging.getLogger(__name__)


class DecisionStore(ABC):
    @abstractmethod
    async def record(self, decision: AuthzDecision) -> None:
        """Persist a decision record which is then immutable."""


class LoggingDecisionStore(DecisionStore):
    """Structured-log sink (no external dependency) for environments without
    the authz_decisions table wired up. Still emits the correlation fields."""

    async def record(self, decision: AuthzDecision) -> None:
        logger.info(
            "authz.decision",
            extra={
                "decision_id": decision.decision_id,
                "allowed": decision.allowed,
                "action": None,
                "policy_version": decision.policy_version,
                "deny_code": decision.deny_code,
                "reason_codes": decision.reason_codes,
                "resource_revision": decision.resource_revision,
                "evaluated_at": decision.evaluated_at.isoformat(),
            },
        )


class AuthzDecisionSink:
    """Wraps a DecisionStore (or logs) and augments with domain correlation."""

    def __init__(
        self,
        store: DecisionStore | None = None,
        *,
        request_correlator=None,
    ) -> None:
        self._store = store or LoggingDecisionStore()
        # request_correlator: async (request) -> dict of domain_event fields to
        # attach (e.g. target resource/action). Used to correlate decision->event.
        self._request_correlator = request_correlator

    async def record(self, decision: AuthzDecision, request: Any = None) -> None:
        await self._store.record(decision)


class CorrelatedDecisionSink(AuthzDecisionSink):
    async def record(self, decision: AuthzDecision, request: Any = None) -> None:
        if self._request_correlator is not None:
            try:
                correlation = await self._request_correlator(request)
                # Attach correlation to the logged record.
                import dataclasses

                logger.info(
                    "authz.decision.correlated",
                    extra={
                        "decision_id": decision.decision_id,
                        "allowed": decision.allowed,
                        "action": (correlation or {}).get("action"),
                        "domain_event": (correlation or {}).get("domain_event"),
                        "resource_id": (correlation or {}).get("resource_id"),
                    },
                )
            except Exception:
                logger.warning("failed to correlate authorization decision", exc_info=True)
        # Always persist the decision record.
        await self._store.record(decision)