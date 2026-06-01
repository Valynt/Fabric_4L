from __future__ import annotations

"""Value Pack skill family for Layer 4 Agents.

Skills for pack discovery, loading, execution, and customization.
"""


from dataclasses import dataclass
from typing import Any

from ..interfaces.value_pack_service import (
    IValuePackService,
    PackExecutionRequest,
    PackStatus,
)


@dataclass
class PackListInput:
    """Input for pack_list skill."""

    industry: str | None = None
    status: str | None = "published"  # published, draft, deprecated


@dataclass
class PackListOutput:
    """Output from pack_list skill."""

    packs: list[dict[str, Any]]
    total_count: int


@dataclass
class PackLoadInput:
    """Input for pack_load skill."""

    pack_id: str
    workspace_id: str


@dataclass
class PackLoadOutput:
    """Output from pack_load skill."""

    success: bool
    pack: dict[str, Any] | None
    error: str | None = None


@dataclass
class PackExecuteInput:
    """Input for pack_execute skill."""

    pack_id: str
    workspace_id: str
    tenant_id: str
    variables: dict[str, Any]
    user_id: str | None = None


@dataclass
class PackExecuteOutput:
    """Output from pack_execute skill."""

    execution_id: str
    status: str
    outputs: dict[str, Any]
    errors: list[str]


@dataclass
class PackCustomizeInput:
    """Input for pack_customize skill."""

    pack_id: str
    workspace_id: str
    modifications: dict[str, Any]
    fork_name: str | None = None


@dataclass
class PackCustomizeOutput:
    """Output from pack_customize skill."""

    success: bool
    new_pack_id: str | None
    error: str | None = None


class PackSkills:
    """Value Pack skill family.

    Exposes pack operations as callable skills for agent workflows.
    """

    def __init__(self, pack_service: IValuePackService):
        self._service = pack_service

    async def pack_list(self, input_data: PackListInput) -> PackListOutput:
        """List available Value Packs.

        Args:
            input_data: Filter criteria (industry, status)

        Returns:
            List of pack summaries
        """
        status = PackStatus(input_data.status) if input_data.status else None

        packs = await self._service.list_packs(
            industry=input_data.industry,
            status=status,
        )

        pack_summaries = [
            {
                "pack_id": p.pack_id,
                "name": p.name,
                "industry": p.industry,
                "segment": p.segment,
                "status": p.status.value,
                "version": p.version,
                "metric_count": len(p.value_drivers),
                "formula_count": len(p.formulas),
            }
            for p in packs
        ]

        return PackListOutput(
            packs=pack_summaries,
            total_count=len(packs),
        )

    async def pack_load(self, input_data: PackLoadInput) -> PackLoadOutput:
        """Load pack into workspace for customization/execution.

        Args:
            input_data: pack_id and workspace_id

        Returns:
            Loaded pack details
        """
        try:
            pack = await self._service.load_pack_into_workspace(
                pack_id=input_data.pack_id,
                workspace_id=input_data.workspace_id,
            )

            return PackLoadOutput(
                success=True,
                pack={
                    "pack_id": pack.pack_id,
                    "name": pack.name,
                    "description": pack.description,
                    "industry": pack.industry,
                    "status": pack.status.value,
                    "is_loaded": pack.is_loaded,
                    "workspace_id": pack.workspace_id,
                },
            )
        except Exception:
            return PackLoadOutput(
                success=False,
                pack=None,
                error="PACK_LOAD_ERROR",
            )

    async def pack_execute(self, input_data: PackExecuteInput) -> PackExecuteOutput:
        """Execute pack workflow with provided variables.

        Args:
            input_data: pack_id, workspace_id, variables, optional user_id

        Returns:
            Execution results
        """
        request = PackExecutionRequest(
            pack_id=input_data.pack_id,
            workspace_id=input_data.workspace_id,
            variables=input_data.variables,
            user_id=input_data.user_id,
        )

        result = await self._service.execute_pack(request, tenant_id=input_data.tenant_id)

        return PackExecuteOutput(
            execution_id=result.execution_id,
            status=result.status,
            outputs=result.outputs,
            errors=result.errors,
        )

    async def pack_customize(self, input_data: PackCustomizeInput) -> PackCustomizeOutput:
        """Fork and customize pack for account-specific needs.

        Args:
            input_data: pack_id, workspace_id, modifications, optional fork_name

        Returns:
            New customized pack reference
        """
        try:
            pack = await self._service.customize_pack(
                pack_id=input_data.pack_id,
                workspace_id=input_data.workspace_id,
                modifications=input_data.modifications,
            )

            return PackCustomizeOutput(
                success=True,
                new_pack_id=pack.pack_id,
            )
        except Exception:
            return PackCustomizeOutput(
                success=False,
                new_pack_id=None,
                error="PACK_CUSTOMIZE_ERROR",
            )
