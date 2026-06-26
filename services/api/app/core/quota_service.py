from __future__ import annotations

import os

from app.core.database import db


class QuotaService:
    """Gateway quota enforcement based on recorded usage events.

    Quotas are read from environment variables named ``QUOTA_<PRODUCT_CODE>``
    where ``<PRODUCT_CODE>`` is upper-cased. A value of ``-1`` means unlimited.
    If no env var is set, the default is unlimited.
    """

    def _limit(self, product_code: str) -> int:
        env_name = f"QUOTA_{product_code.upper()}"
        raw = os.environ.get(env_name, "")
        if raw:
            try:
                return int(raw)
            except ValueError:
                return -1
        return -1

    def used(self, tenant_id: str, product_code: str) -> int:
        events = db.usage_events.list(tenant_id=tenant_id, limit=10000)
        return sum(1 for e in events if e.product_code == product_code)

    def check(self, tenant_id: str, product_code: str, quantity: float = 1.0) -> dict:
        limit = self._limit(product_code)
        used = self.used(tenant_id, product_code)
        unlimited = limit < 0
        allowed = unlimited or (used + quantity <= limit)
        return {
            "product_code": product_code,
            "limit": limit,
            "used": used,
            "remaining": None if unlimited else max(0, limit - used),
            "allowed": allowed,
        }

    def quotas(self, tenant_id: str) -> dict[str, dict]:
        products = {
            "benchmarks",
            "value_drivers",
            "value_models",
            "assumptions",
            "evidence",
            "cfo_narratives",
            "realization",
        }
        return {product: self.check(tenant_id, product) for product in products}
