"""Command guard: the reusable enforcement point for protected domain commands.

A protected command (approval, validation, publication, exception activation,
canonicalization, realization locking, etc.) MUST NOT be a generic CRUD update.
The ``CommandGuard`` wraps the write path: it calls the authorization facade for
the specific verb, honors obligations, and FAILS CLOSED on any ambiguity.

Enforcement-point coverage is CI-gated (``check_protected_transition_guards.py``):
every protected command in the action catalog must reference a guard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .client import AuthorizationClient
from .decisions import (
    AuthzDecisionSink,
)
from .errors import AuthorizationDeniedError, PDUnavailableError
from .models import AuthzDecision, AuthzEnvironment, AuthzRequest
from .obligations import honor


@dataclass
class GuardResult:
    decision: AuthzDecision
    honored: bool = False

    def require(self) -> AuthzDecision:
        if not self.decision.allowed:
            raise AuthorizationDeniedError(
                " ".join(self.decision.reason_codes) or "denied",
                action=(self.decision.deny_code or ""),
            )
        if not self.honored:
            # Decision allowed but obligations not satisfied -> fail closed.
            raise PDUnavailableError(
                "authorization obligations not satisfied; failing closed",
            )
        return self.decision


class CommandGuard:
    """Guards a protected write with a typed authorize + obligations check.

    Async::
        decision = await guard.require(
            principal=..., action="claim.approve",
            resource=projection.as_resource(),
            environment=env,
            requested_resource_revision=proj.revision,
        )
    """

    def __init__(
        self,
        client: AuthorizationClient,
        *,
        decision_sink: AuthzDecisionSink | None = None,
        obligation_enabled: bool = True,
    ) -> None:
        self._client = client
        self._decision_sink = decision_sink
        self._obligation_enabled = obligation_enabled

    async def require(
        self,
        *,
        principal: Any,
        action: str,
        resource: dict[str, Any],
        requested_resource_revision: str | None = None,
        environment: AuthzEnvironment | None = None,
        request_context: Any = None,
    ) -> AuthzDecision:
        env = environment or AuthzEnvironment()
        req = AuthzRequest(
            action=action,
            principal=principal,
            resource=resource,
            environment=env,
            requested_resource_revision=requested_resource_revision,
        )
        decision = await self._client.authorize(req)
        if not decision.allowed:
            raise AuthorizationDeniedError(
                " ".join(decision.reason_codes) or "denied",
                action=action,
                details={"decision_id": decision.decision_id, "deny_code": decision.deny_code},
            )
        if self._obligation_enabled:
            ok = await honor(decision, request_context)
            if not ok:
                raise PDUnavailableError(
                    "authorization obligations not satisfied; failing closed",
                    action=action,
                )
        if self._decision_sink is not None:
            try:
                await self._decision_sink.record(decision, request_context)
            except Exception:
                raise PDUnavailableError(
                    "failed to record authorization decision; failing closed",
                    action=action,
                )
        return decision

    async def check(
        self,
        *,
        principal: Any,
        action: str,
        resource: dict[str, Any],
        requested_resource_revision: str | None = None,
        environment: AuthzEnvironment | None = None,
        request_context: Any = None,
    ) -> GuardResult:
        """Non-raising variant returning a GuardResult for read-style checks."""
        env = environment or AuthzEnvironment()
        req = AuthzRequest(
            action=action,
            principal=principal,
            resource=resource,
            environment=env,
            requested_resource_revision=requested_resource_revision,
        )
        decision = await self._client.authorize(req)
        honored = await honor(decision, request_context) if (self._obligation_enabled and decision.allowed) else (not decision.allowed)
        return GuardResult(decision=decision, honored=honored)