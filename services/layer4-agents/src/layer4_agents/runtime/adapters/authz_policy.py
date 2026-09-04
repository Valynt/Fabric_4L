"""Policy-backed AuthzPort adapter for the Agent Runtime.

Gates runtime tool calls through ``value_fabric.shared.identity.policy_registry``,
the canonical cross-layer action registry. Tools with no registered tool action
(e.g. ``calculate_roi``) are ungated and allowed; tools with a registered action
fail closed unless the runtime context carries the required permission/scope
grant.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
    get_request_context,
)
from value_fabric.shared.identity.policy_registry import authorize_action, get_tool_action

from ..models import AuthzDecision, RuntimeContext
from ..ports import AuthzPort


class PolicyAuthzPort(AuthzPort):
    """AuthzPort backed by the shared identity policy registry (deny by default)."""

    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> AuthzDecision:
        """Authorize a tool call for the current runtime context."""
        if ctx is None or not ctx.tenant_id:
            return AuthzDecision(allowed=False, reason="missing_tenant")

        action = get_tool_action(tool_name)
        if action is None:
            # No action is registered for this tool → ungated by policy registry.
            return AuthzDecision(allowed=True)

        request_context = get_request_context()
        if request_context is None:
            request_context = self._build_service_context(tool_name, ctx)

        try:
            authorize_action(action, request_context, target_tenant_id=ctx.tenant_id)
        except asyncio.CancelledError:
            raise
        except HTTPException as exc:
            return AuthzDecision(allowed=False, reason=_reason_from_http_error(exc))
        except Exception:
            # Never crash tool authorization on an unexpected policy failure;
            # fail closed with a stable reason.
            return AuthzDecision(allowed=False, reason="authorization_error")
        return AuthzDecision(allowed=True)

    @staticmethod
    def _build_service_context(tool_name: str, ctx: RuntimeContext) -> RequestContext:
        """Synthesize a service-account RequestContext from runtime ctx metadata.

        Grants travel in ``ctx.metadata`` because RuntimeContext rejects extra
        top-level fields (``extra="forbid"``). Canonical grant keys:

        - ``service_account_scopes``: raw scope strings (e.g. ``["read:search"]``).
        - ``permissions``: raw permission strings.

        Synthesized contexts carry exactly those grants — never auto-granted
        scopes — so missing grants fail closed inside ``authorize_action``.
        """
        metadata: dict[str, Any] = ctx.metadata or {}
        scopes = _grant_strings(metadata, "service_account_scopes")
        permissions = _grant_strings(metadata, "permissions")
        return RequestContext(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id or "workflow-executor",
            roles=["service"],
            permissions=permissions,
            source=AUTH_SOURCE_SERVICE_ACCOUNT,
            auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
            request_id=str(ctx.trace_id or ctx.workflow_id or "tool"),
            trace_id=str(ctx.trace_id) if ctx.trace_id else None,
            service_account_id="layer4-tool-registry",
            service_account_scopes=scopes,
            raw={"tool_name": tool_name, "workflow_id": ctx.workflow_id, "run_id": ctx.run_id},
        )


def _grant_strings(metadata: dict[str, Any], key: str) -> list[str]:
    """Collect grant strings from context metadata, failing closed on type drift.

    Only list/tuple/set/frozenset containers are honored. A ``str`` value
    would iterate characters and a ``dict`` would iterate keys — either
    could fabricate unintended grant strings that may match real grants —
    so any other container type is ignored entirely and authorization
    proceeds without those grants.
    """
    value = metadata.get(key)
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    return [item for item in value if isinstance(item, str)]


def _reason_from_http_error(exc: HTTPException) -> str:
    """Extract a stable denial reason from a policy HTTPException."""
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code")
        if code:
            return str(code)
    return str(detail) if detail else str(getattr(exc, "status_code", "denied"))
