"""Adapter bridging the legacy tool registry behind the runtime ToolRegistryPort.

The Layer 4 Agent Runtime exposes a provider-agnostic ``ToolRegistryPort``. This
adapter implements that port over the existing, tenant-aware
``layer4_agents.tools.registry.ToolRegistry`` so runtime tool calls reuse the
established registry, execution envelope, and structured result semantics without
requiring a parallel registry implementation.
"""

from __future__ import annotations

from typing import Any

from value_fabric.shared.identity.context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
    clear_current_context,
    get_request_context,
    set_request_context,
)

from ...models.tool_schemas import ToolCategory
from ...models.tool_schemas import ToolSchema as LegacyToolSchema
from ...tools.registry import BaseTool, ToolNotFoundError, ToolRegistrationError, ToolRegistry
from ..errors import AgentRuntimeError
from ..models import RuntimeContext, ToolDef, ToolResult, ToolSchema
from ..ports import ToolRegistryPort


class LegacyToolRegistryAdapter(ToolRegistryPort):
    """ToolRegistryPort implemented over the legacy ``tools.registry.ToolRegistry``."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        """Wrap an existing registry or default to a fresh instance.

        Args:
            registry: Optional legacy registry to bridge. Defaults to a new
                ``ToolRegistry()`` (env vars are read at construction time, so a
                fresh registry per adapter keeps tests hermetic).
        """
        self._registry = registry if registry is not None else ToolRegistry()

    def register(self, tool: ToolDef) -> None:
        """Register a tool backed by a legacy ``BaseTool`` handler."""
        handler: Any = tool.handler
        if not isinstance(handler, BaseTool):
            handler_type = type(handler).__name__ if handler is not None else "None"
            raise AgentRuntimeError(
                f"Tool '{tool.name}' cannot be bridged: handler must be a BaseTool instance",
                code="INVALID_TOOL_HANDLER",
                details={"tool_name": tool.name, "handler_type": handler_type},
            )
        try:
            self._registry.register(handler)
        except ToolRegistrationError as exc:
            if "already registered" in str(exc):
                raise AgentRuntimeError(
                    f"Tool '{tool.name}' is already registered",
                    code="TOOL_ALREADY_REGISTERED",
                    details={"tool_name": tool.name},
                ) from exc
            raise AgentRuntimeError(
                f"Tool '{tool.name}' could not be registered: {exc}",
                code="TOOL_REGISTRATION_ERROR",
                details={"tool_name": tool.name},
            ) from exc

    def get_schema(self, name: str, tenant_id: str) -> ToolSchema | None:
        """Return the public runtime schema for a registered tool."""
        if not self._registry.has_tool(name):
            return None
        try:
            tool = self._registry.get(name)
        except ToolNotFoundError:
            return None
        return self._map_schema(tool.get_schema(), tenant_scoped=bool(tool.requires_tenant))

    def list_tools(self, tenant_id: str) -> list[ToolSchema]:
        """Return runtime schemas for every registered tool."""
        schemas: list[ToolSchema] = []
        for legacy_schema in self._registry.list_tools():
            tool: BaseTool | None = None
            try:
                tool = self._registry.get(legacy_schema.name)
            except ToolNotFoundError:
                pass
            schemas.append(
                self._map_schema(
                    legacy_schema,
                    tenant_scoped=bool(tool.requires_tenant) if tool is not None else True,
                )
            )
        return schemas

    async def execute(
        self, name: str, arguments: dict[str, Any], ctx: RuntimeContext
    ) -> ToolResult:
        """Execute a tool through the legacy registry.

        The legacy registry resolves the trusted tenant from the ambient
        ``RequestContext`` when present (context wins). When no ambient request
        context exists and the runtime context carries a tenant, we synthesize a
        service-account ``RequestContext`` so tenant-scoped tools execute with the
        runtime context's tenant rather than rejecting a raw string tenant_id.
        """
        input_dict = dict(arguments)
        synthesized = False
        try:
            if ctx is not None:
                self._inject_envelope(input_dict, ctx)
                if ctx.tenant_id and get_request_context() is None:
                    set_request_context(self._build_execution_context(name, ctx))
                    synthesized = True
            legacy_result = await self._registry.execute(name, input_dict)
        finally:
            if synthesized:
                clear_current_context()
        return ToolResult(
            status=legacy_result.status,
            data=legacy_result.data,
            error=legacy_result.error,
            metadata=legacy_result.metadata,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_envelope(input_dict: dict[str, Any], ctx: RuntimeContext) -> None:
        """Stamp correlation/tenant fields onto the raw input envelope."""
        if ctx.tenant_id:
            input_dict["tenant_id"] = ctx.tenant_id
        for key in ("trace_id", "workflow_id", "run_id", "user_id"):
            value = getattr(ctx, key, None)
            if value:
                input_dict[key] = value

    @staticmethod
    def _build_execution_context(tool_name: str, ctx: RuntimeContext) -> RequestContext:
        """Mirror the legacy registry's synthesized service-account context."""
        return RequestContext(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id or "workflow-executor",
            roles=["service"],
            source=AUTH_SOURCE_SERVICE_ACCOUNT,
            auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
            request_id=str(ctx.trace_id or ctx.workflow_id or "tool"),
            trace_id=str(ctx.trace_id) if ctx.trace_id else None,
            service_account_id="layer4-tool-registry",
            service_account_scopes=[f"tool:{tool_name}"],
            raw={
                "workflow_id": ctx.workflow_id,
                "run_id": ctx.run_id,
                "tool_name": tool_name,
            },
        )

    @staticmethod
    def _map_schema(legacy: LegacyToolSchema, *, tenant_scoped: bool) -> ToolSchema:
        """Map a legacy ``ToolSchema`` onto the canonical runtime schema."""
        parameters = dict(legacy.input_schema or {})
        category = (
            legacy.category.value
            if isinstance(legacy.category, ToolCategory)
            else str(legacy.category)
        )
        return ToolSchema(
            name=legacy.name,
            description=legacy.description,
            category=category,
            tenant_scoped=tenant_scoped,
            parameters=parameters,
            required=list(parameters.get("required") or []),
            version="1.0.0",
        )
