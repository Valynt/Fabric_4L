from __future__ import annotations

"""Ports for Ground Truth proxy route operations."""

from typing import Any, Protocol


class GroundTruthProxyPort(Protocol):
    """Tenant-scoped operations exposed by the Layer 4 Ground Truth proxy."""

    async def list_truths(
        self,
        *,
        tenant_id: str,
        status: str | None = None,
        claim_type: str | None = None,
        min_maturity: int | None = None,
        min_confidence: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List tenant-scoped TruthObjects."""

    async def get_truth(self, *, truth_id: str, tenant_id: str) -> dict[str, Any]:
        """Get a tenant-scoped TruthObject."""

    async def get_truth_audit(self, *, truth_id: str, tenant_id: str) -> dict[str, Any]:
        """Get tenant-scoped TruthObject audit events."""

    async def validate_truth(
        self,
        *,
        truth_id: str,
        action: str,
        actor: str,
        tenant_id: str,
        actor_type: str = "user",
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Apply a tenant-scoped validation transition."""

    async def get_freshness_summary(self, *, tenant_id: str) -> dict[str, Any]:
        """Get tenant-scoped freshness summary."""

    async def get_stale_truths(
        self,
        *,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get tenant-scoped stale TruthObjects."""

    async def get_maturity_ladder(self, *, tenant_id: str) -> dict[str, Any]:
        """Get tenant-scoped maturity ladder metadata."""
