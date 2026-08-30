"""Authorization facade: stable, fail-closed single decision and enforcement layer.

Application/service code calls :func:`authorize` and never imports Rego policy
names or OPA response shapes directly. The ``AuthorizationClient``:

* enriches an ``AuthzRequest`` with server-side facts (attribute resolver / PIP),
* evaluates it (pure-Python engine by default; an OPA/HTTP PDP can be plugged in),
* applies revision-aware caching (protected commands are never cached),
* records the decision for audit/domain correlation,
* maps the outcome to a typed ``AuthzDecision`` or raises on failure.

On any evaluation failure (engine error, bundle unavailable, PDP outage) the
client FAILS CLOSED on protected writes by raising``PDUnavailableError``.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Iterable
from uuid import uuid4

from . import errors
from .actions import UNCACHEABLE_ACTIONS
from .engine import DecisionEngine, PolicyBundle, load_bundle
from .errors import AuthorizationDeniedError, PDUnavailableError, PolicyBundleUnavailableError
from .models import AuthzDecision, Obligation

logger = logging.getLogger(__name__)

# Default policy version override via env for testing/parity.
import os as _os

DEFAULT_POLICY_VERSION = _os.environ.get("FABRIC_AUTHZ_POLICY_VERSION", "fabric.authz.v1")
DEFAULT_BUNDLE_DIR = _os.environ.get(
    "FABRIC_AUTHZ_BUNDLE_DIR",
    "policies/authorization/bundle/data",
)


class AuthorizationClient:
    """Typed authorization facade.

    ``authorize(principal, action, resource, environment) -> AuthzDecision``.
    """

    def __init__(
        self,
        *,
        bundle: PolicyBundle | None = None,
        engine: DecisionEngine | None = None,
        data_dir: str = DEFAULT_BUNDLE_DIR,
        policy_version: str = DEFAULT_POLICY_VERSION,
        cache=None,
        attribute_resolver=None,
        decision_sink=None,
        fail_closed_on_protected: bool = True,
    ) -> None:
        if bundle is None:
            try:
                bundle = load_bundle(data_dir, policy_version=policy_version)
            except Exception as exc:  # pragma: no cover - defensive
                raise PolicyBundleUnavailableError(
                    f"failed to load policy bundle from {data_dir}: {exc}",
                ) from exc
        self._bundle = bundle
        self._engine = engine or DecisionEngine(bundle=bundle)
        self._data_dir = data_dir
        self._policy_version = policy_version
        self._cache = cache
        self._attribute_resolver = attribute_resolver
        self._decision_sink = decision_sink
        self._fail_closed_on_protected = fail_closed_on_protected

    @property
    def policy_version(self) -> str:
        return self._policy_version

    @property
    def bundle_digest(self) -> str:
        return self._bundle.bundle_digest

    # ------------------------------------------------------------------
    async def authorize(self, request: Any) -> AuthzDecision:
        """Evaluate a request and return a typed decision.

        Never raises for a *denied* decision (returns allowed=False). Raises
        ``AuthorizationDeniedError``/``PDUnavailableError`` only when the caller
        opted into exception-style handling via ``authorize_or_raise``.
        """
        return await self._evaluate(request, raise_on_deny=False)

    async def authorize_or_raise(self, request: Any) -> AuthzDecision:
        """Like ``authorize`` but raises ``AuthorizationDeniedError`` on deny and
        ``PDUnavailableError`` on availability failure (fail closed)."""
        return await self._evaluate(request, raise_on_deny=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _evaluate(self, request, *, raise_on_deny: bool) -> AuthzDecision:
        action = str(request.action)
        cacheable = action not in UNCACHEABLE_ACTIONS

        # 1. Server-side attribute enrichment (PIP). Never trust client facts.
        attrs, rel = None, None
        if self._attribute_resolver is not None:
            try:
                attrs, rel = await self._attribute_resolver.resolve(request)
            except Exception:
                # If enrichment fails on a protected command, fail closed.
                if self._fail_closed_on_protected and action in UNCACHEABLE_ACTIONS:
                    raise PDUnavailableError(
                        "attribute enrichment failed; failing closed",
                        action=action,
                    )
                logger.warning("attribute resolver failed; proceeding without enrichment", exc_info=True)
        if attrs is not None:
            request.environment.resource_attributes.update(attrs)
        if rel is not None:
            request.environment.relationships.update(rel)

        request.resource = dict(request.resource or {})
        if attrs is not None:
            # Surface key resource attributes for revision/inputs.
            for k, v in attrs.items():
                request.resource.setdefault(k, v)

        # 2. Cache lookup (only for cacheable actions).
        cache_key = self._cache_key(request) if cacheable and self._cache else None
        if cache_key is not None:
            cached = await self._cache.get(cache_key) if self._cache else None
            if cached is not None:
                return cached

        # 3. Evaluate the policy engine.
        interim = self._engine.evaluate(request)

        # 4. Revision freshness (ABAC): reject stale requested revision.
        requested_rev = getattr(request, "requested_resource_revision", None)
        current_rev = request.environment.resource_attributes.get("revision")
        if requested_rev and current_rev and str(current_rev) != str(requested_rev):
            # Even if granted on attributes, reframe as stale revision denial.
            if not request.environment.relationships.get("ignore_revision_check"):
                interim = _stale_revision_result()

        allowed = interim.allowed
        reason_codes = interim.reason_codes or []
        deny_code = interim.deny_code

        decision = AuthzDecision(
            allowed=allowed,
            decision_id=str(uuid4()),
            policy_version=self._policy_version,
            reason_codes=reason_codes,
            deny_code=deny_code,
            obligations=self._obligations_for(action) if allowed else [],
            bundle_digest=self._bundle.bundle_digest,
            input_fingerprint=getattr(request, "input_fingerprint", lambda: None)(),
            evaluated_at=datetime.now(UTC),
            resource_revision=request.environment.resource_attributes.get("revision"),
        )

        # 5. Persist/record the decision for audit correlation.
        if self._decision_sink is not None:
            try:
                await self._decision_sink.record(decision, request)
            except Exception:
                logger.warning("failed to record authorization decision", exc_info=True)

        # 6. Cache allowed cacheable decisions.
        if cache_key is not None and self._cache is not None:
            ttl = self._ttl_for(action)
            await self._cache.set(cache_key, decision, ttl_ms=ttl)

        if raise_on_deny and not allowed:
            raise AuthorizationDeniedError(
                " ".join(reason_codes) or "denied by policy",
                action=action,
                details={"decision_id": decision.decision_id, "deny_code": deny_code},
            )
        return decision

    def _obligations_for(self, action: str) -> list[Obligation]:
        obligations: list[Obligation] = [Obligation(kind="audit", detail={"action": action})]
        if action == "deliverable.publish_external":
            obligations.append(
                Obligation(kind="mask_external_scope", detail={"scope": "external_viewers"})
            )
        if action == "break_glass.approve":
            obligations.append(
                Obligation(kind="dual_control", detail={"required": True})
            )
        return obligations

    def _ttl_for(self, action: str) -> int:
        # Sensitive/protected verbs: short TTL or none (they are uncacheable anyway).
        if action == "claim.view":
            return 30_000
        return 5_000

    @staticmethod
    def _cache_key(request: Any) -> str:
        return request.input_fingerprint()


def _stale_revision_result() -> Any:
    from .engine import InterimResult

    return InterimResult(
        allowed=False,
        deny_code=errors.ReasonCode.RESOURCE_REVISION_CHANGED.value,
        reason_codes=[errors.ReasonCode.RESOURCE_REVISION_CHANGED.value],
    )


# ---------------------------------------------------------------------------
# Module-level singleton + convenience facade
# ---------------------------------------------------------------------------
_client: AuthorizationClient | None = None


def get_authorization_client() -> AuthorizationClient:
    """Return the process-wide authorization client (lazy init)."""
    global _client
    if _client is None:
        _client = AuthorizationClient()
    return _client


def configure_authorization_client(*, client: AuthorizationClient | None = None, **kwargs) -> None:
    """Override the singleton (used by tests and app startup)."""
    global _client
    _client = client or AuthorizationClient(**kwargs)


def reset_authorization_client() -> None:
    global _client
    _client = None


async def authorize(
    principal: Any,
    action: str,
    resource: dict[str, Any] | None = None,
    environment: Any | None = None,
    *,
    requested_resource_revision: str | None = None,
    client: AuthorizationClient | None = None,
) -> AuthzDecision:
    """Stable repository-owned interface:

        decision = await authorize(principal, action, resource, environment)
    """
    cli = client or get_authorization_client()
    from .models import AuthzEnvironment, AuthzRequest

    env = environment or AuthzEnvironment()
    req = AuthzRequest(
        action=action,
        principal=principal,
        resource=resource or {},
        environment=env,
        requested_resource_revision=requested_resource_revision,
    )
    return await cli.authorize(req)