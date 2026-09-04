"""In-memory MemoryPort adapter for hermetic tests and ephemeral stores.

Stores thread state keyed by ``(tenant_id, thread_id)`` (latest write wins)
and an append-only pool of long-term records per tenant. All lookups are
tenant-scoped and fail closed: a thread saved under a different tenant is
invisible to ``get_thread_state``/``search_long_term``.

The ``MemoryPort`` contract has no long-term write operation, so the
in-memory adapter exposes ``add_long_term`` as a concrete extension seam used
to seed (and test) the searchable long-term pool; a durable adapter would back
these records from the runtime persistence layer instead.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from ..errors import TenantRequiredError
from ..ports import MemoryPort


class InMemoryMemoryAdapter(MemoryPort):
    """Tenant-scoped MemoryPort backed by in-process dicts and lists."""

    def __init__(self) -> None:
        self._thread_states: dict[tuple[str, str], dict[str, Any]] = {}
        self._long_term: list[tuple[str, dict[str, Any]]] = []

    # ------------------------------------------------------------------
    # MemoryPort
    # ------------------------------------------------------------------

    async def get_thread_state(self, thread_id: str, tenant_id: str) -> dict[str, Any] | None:
        """Load the latest thread state for a tenant, or ``None`` when absent."""
        if not tenant_id:
            raise TenantRequiredError(details={"thread_id": thread_id})
        state = self._thread_states.get((tenant_id, thread_id))
        return None if state is None else copy.deepcopy(state)

    async def save_thread_state(self, thread_id: str, tenant_id: str, state: dict[str, Any]) -> None:
        """Persist thread state for a tenant (latest write replaces prior state)."""
        if not tenant_id:
            raise TenantRequiredError(details={"thread_id": thread_id})
        self._thread_states[(tenant_id, thread_id)] = copy.deepcopy(state)

    async def search_long_term(self, query: str, tenant_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Search the tenant's long-term records, most recent first.

        Matches are case-insensitive substring hits against the JSON
        representation of each record. Results are deep copies capped at
        ``limit``; other tenants' records are never visible.
        """
        if not tenant_id:
            raise TenantRequiredError()
        if limit <= 0:
            return []
        needle = query.casefold()
        matches: list[dict[str, Any]] = []
        for record_tenant, record in reversed(self._long_term):
            if record_tenant != tenant_id:
                continue
            haystack = json.dumps(
                record, sort_keys=True, ensure_ascii=False, default=str
            ).casefold()
            if needle in haystack:
                matches.append(copy.deepcopy(record))
                if len(matches) >= limit:
                    break
        return matches

    # ------------------------------------------------------------------
    # Adapter extension (not part of MemoryPort)
    # ------------------------------------------------------------------

    async def add_long_term(self, tenant_id: str, record: dict[str, Any]) -> None:
        """Index a long-term memory record for a tenant (adapter extension).

        The ``MemoryPort`` contract only defines reads for long-term memory;
        durable implementations receive records from the runtime persistence
        layer. This seam lets the in-memory store be seeded hermetically.
        """
        if not tenant_id:
            raise TenantRequiredError()
        self._long_term.append((tenant_id, copy.deepcopy(record)))
