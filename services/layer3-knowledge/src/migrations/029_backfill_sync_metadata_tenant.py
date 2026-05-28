from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Backfill tenant_id on SyncMetadata nodes using trusted source ownership mapping.

Trusted ownership precedence:
1. :Source {id = source_id, tenant_id}
2. :Source {source_id = source_id, tenant_id}
3. Existing :SyncMetadata.tenant_id fallback to DEFAULT_TENANT
"""


import argparse
import asyncio
import logging
import os
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)


class SyncMetadataTenantBackfill:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        if self._driver is None:
            if not self.password:
                raise RuntimeError("Neo4j password required. Set NEO4J_PASSWORD.")
            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def run(self, default_tenant_id: str = "system", dry_run: bool = False) -> dict[str, Any]:
        driver = await self._get_driver()
        async with driver.session() as session:
            count_result = await session.run(
                """
                MATCH (s:SyncMetadata)
                WHERE s.tenant_id IS NULL
                RETURN count(s) AS missing
                """
            )
            missing = (await count_result.single())["missing"]

            if dry_run:
                return {"status": "dry_run", "missing": missing, "updated": 0}

            update_result = await session.run(
                """
                MATCH (m:SyncMetadata)
                WHERE m.tenant_id IS NULL
                OPTIONAL MATCH (src_by_id:Source {id: m.source_id})
                OPTIONAL MATCH (src_by_source_id:Source {source_id: m.source_id})
                WITH m, coalesce(src_by_id.tenant_id, src_by_source_id.tenant_id, $default_tenant_id) AS resolved_tenant
                SET m.tenant_id = resolved_tenant
                RETURN count(m) AS updated
                """,
                {"default_tenant_id": default_tenant_id},
            )
            updated = (await update_result.single())["updated"]

            return {
                "status": "completed",
                "missing": missing,
                "updated": updated,
                "default_tenant_id": default_tenant_id,
            }


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Backfill SyncMetadata.tenant_id")
    parser.add_argument("--default-tenant-id", default=os.getenv("DEFAULT_TENANT", "system"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    migration = SyncMetadataTenantBackfill()
    try:
        result = await migration.run(default_tenant_id=args.default_tenant_id, dry_run=args.dry_run)
        logger.info("SyncMetadata tenant backfill result: %s", result)
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(_main())
