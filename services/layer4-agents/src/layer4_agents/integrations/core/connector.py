from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from .types import CanonicalRecord, CRMModel, CRMOperationResult, SyncCursor


@runtime_checkable
class CRMConnector(Protocol):
    """Provider-specific boundary for reading CRM data.

    Implementations encapsulate authentication, client transport, and provider
    response mapping. Callers (tools, SyncEngine) interact with the canonical
    shapes returned by this protocol and never with provider APIs directly.
    """

    async def test_connection(self, *, timeout: float | None = None) -> dict[str, Any]:
        """Validate that stored credentials can reach the provider.

        Returns a dict with keys: success (bool), message (str), details (dict),
        and optionally error_code (str). This is the boundary used by the
        integration configuration UI.
        """
        ...

    async def get_account(
        self,
        remote_id: str,
        *,
        include: set[CRMModel] | None = None,
        timeout: float | None = None,
    ) -> CanonicalRecord | None:
        """Fetch a single account/prospect by its provider remote ID."""
        ...

    async def list_opportunities(
        self,
        account_remote_id: str,
        *,
        cursor: SyncCursor | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Fetch opportunities associated with an account."""
        ...

    async def list_interactions(
        self,
        account_remote_id: str,
        *,
        since_date: str | None = None,
        cursor: SyncCursor | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Fetch engagements/interactions associated with an account."""
        ...

    async def list_accounts(
        self,
        *,
        cursor: SyncCursor | None = None,
        modified_since: datetime | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """List accounts for full/incremental sync.

        This is optional for PR 3; tools may continue to fetch by explicit IDs
        until the SyncEngine is introduced in PR 5.
        """
        ...


@runtime_checkable
class CRMWriteConnector(Protocol):
    """Narrow provider boundary for agent writes to CRM.

    Only update operations are exposed initially; create/delete can be added
    once the canonical record shape and idempotency keys are stable.
    """

    async def update_opportunity(
        self,
        remote_id: str,
        fields: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> CRMOperationResult:
        """Update a provider opportunity/deal by remote ID."""
        ...
