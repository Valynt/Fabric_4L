from __future__ import annotations

"""
Tool Contract Registry — manages tool contracts with deterministic versioning.

Invariants:
  - Duplicate tool_id registration is rejected.
  - High-risk tools must have approval_policy_id.
  - Customer-facing tools must have validation hooks.
  - Tool lookups are tenant-scoped where appropriate.
"""


from .models import ToolContract, ToolRiskLevel, ToolSideEffectClass


class ToolRegistrationError(ValueError):
    """Raised when tool registration violates a constraint."""

    pass


class ToolNotFoundError(KeyError):
    """Raised when a requested tool is not in the registry."""

    pass


class ToolContractRegistry:
    """
    In-memory registry for ToolContract definitions.

    Production upgrade path: persist to SQL/Redis with tenant scoping.
    """

    def __init__(self) -> None:
        # Tenant-scoped index: tenant_id -> {tool_id -> ToolContract}
        self._tools: dict[str, dict[str, ToolContract]] = {}

    def register_tool(self, tool: ToolContract, tenant_id: str) -> ToolContract:
        """
        Register a tool contract scoped to a tenant.

        Raises:
            ToolRegistrationError: on duplicate tool_id for tenant or policy violation.
        """
        tenant_tools = self._tools.setdefault(tenant_id, {})
        if tool.tool_id in tenant_tools:
            existing = tenant_tools[tool.tool_id]
            raise ToolRegistrationError(
                f"Tool '{tool.tool_id}' already registered for tenant '{tenant_id}' "
                f"(version={existing.version}, id={existing.id}). "
                f"Use versioned tool_id to register a new version."
            )

        # Enforce: high-risk tools need approval policy
        if tool.risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
            if not tool.approval_policy_id:
                raise ToolRegistrationError(
                    f"High-risk tool '{tool.tool_id}' must have approval_policy_id"
                )

        # Enforce: customer_facing_output tools need approval policy
        if tool.side_effect_class == ToolSideEffectClass.CUSTOMER_FACING_OUTPUT:
            if not tool.approval_policy_id:
                raise ToolRegistrationError(
                    f"Customer-facing tool '{tool.tool_id}' must have approval_policy_id"
                )

        tenant_tools[tool.tool_id] = tool
        return tool

    def get_tool(self, tool_id: str, tenant_id: str | None = None) -> ToolContract:
        """
        Retrieve a tool contract by ID.

        If tenant_id is provided, enforces tenant scoping.
        """
        if tenant_id is not None:
            tenant_tools = self._tools.get(tenant_id, {})
            tool = tenant_tools.get(tool_id)
            if tool is None:
                raise ToolNotFoundError(
                    f"Tool '{tool_id}' not found for tenant '{tenant_id}'"
                )
            return tool

        # Without tenant scoping, search across all tenants
        for tenant_tools in self._tools.values():
            if tool_id in tenant_tools:
                return tenant_tools[tool_id]
        raise ToolNotFoundError(f"Tool '{tool_id}' not found")

    def list_tools(
        self,
        tenant_id: str | None = None,
        layer: str | None = None,
        risk_level: ToolRiskLevel | None = None,
    ) -> list[ToolContract]:
        """List tools, optionally filtered."""
        if tenant_id is not None:
            tools = list(self._tools.get(tenant_id, {}).values())
        else:
            tools = [
                tool
                for tenant_tools in self._tools.values()
                for tool in tenant_tools.values()
            ]

        if layer is not None:
            tools = [t for t in tools if t.layer.value == layer]

        if risk_level is not None:
            tools = [t for t in tools if t.risk_level == risk_level]

        return tools

    def validate_tool_invocation_policy(
        self,
        tool_id: str,
        tenant_id: str,
        has_approval: bool = False,
        account_context_present: bool = False,
    ) -> ToolContract:
        """
        Validate that a tool invocation is permitted.

        Returns the ToolContract if valid.

        Raises:
            ToolNotFoundError: if tool doesn't exist or tenant mismatch.
            ApprovalRequiredError: if approval required but not present.
        """
        from harness.policies import (
            evaluate_tool_invocation_policy,
        )

        tool = self.get_tool(tool_id, tenant_id=tenant_id)

        evaluate_tool_invocation_policy(
            tool=tool,
            has_approval=has_approval,
            tenant_context_present=True,
            account_context_present=account_context_present,
        )

        return tool

    def unregister_tool(self, tool_id: str, tenant_id: str) -> None:
        """Remove a tool from the registry for a specific tenant."""
        tenant_tools = self._tools.get(tenant_id, {})
        if tool_id not in tenant_tools:
            raise ToolNotFoundError(
                f"Tool '{tool_id}' not found for tenant '{tenant_id}'"
            )

        del tenant_tools[tool_id]
