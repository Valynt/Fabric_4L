from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TenantBillingStore:
    plans: dict[str, dict[str, Any]] = field(default_factory=dict)
    entitlements: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    invoices: dict[str, dict[str, Any]] = field(default_factory=dict)
    payments: dict[str, dict[str, Any]] = field(default_factory=dict)
    usage_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    usage_aggregates: dict[str, float] = field(default_factory=lambda: defaultdict(float))


class BillingStore:
    def __init__(self) -> None:
        self._tenants: dict[str, TenantBillingStore] = defaultdict(TenantBillingStore)

    def tenant(self, tenant_id: str) -> TenantBillingStore:
        return self._tenants[tenant_id]

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


STORE = BillingStore()
