from __future__ import annotations

"""Neo4j repository for BenchmarkDataset persistence."""


import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.database import require_tenant_context

from ..models.benchmark_dataset import BenchmarkDataset, BenchmarkMetric, StatisticalProfile

logger = logging.getLogger(__name__)


class BenchmarkRepository:
    """CRUD operations for benchmark datasets in Neo4j."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    @staticmethod
    def _require_tenant_scope(tenant_id: str | None, *, operation: str) -> str:
        return require_tenant_context(tenant_id, operation=f"benchmark_repository.{operation}")

    async def save_dataset(self, dataset: BenchmarkDataset) -> None:
        """Persist a BenchmarkDataset and its metrics."""
        self._require_tenant_scope(dataset.tenant_id, operation="save_dataset")
        async with self._driver.session() as session:
            await session.execute_write(self._tx_save_dataset, dataset)

    @staticmethod
    async def _tx_save_dataset(tx, dataset: BenchmarkDataset) -> None:
        await tx.run(
            """
            MERGE (d:BenchmarkDataset {dataset_id: $dataset_id, tenant_id: $tenant_id})
            SET d.name = $name,
                d.description = $description,
                d.industry = $industry,
                d.segment = $segment,
                d.geography = $geography,
                d.version = $version,
                d.data_source = $data_source,
                d.is_public = $is_public,
                d.ownership_mode = $ownership_mode,
                d.created_at = $created_at,
                d.updated_at = $updated_at
            WITH d
            OPTIONAL MATCH (d)-[r:HAS_METRIC]->(m:BenchmarkMetric)
            DELETE r, m
            WITH d
            UNWIND $metrics AS metric
            CREATE (m:BenchmarkMetric {
                name: metric.name,
                unit: metric.unit,
                description: metric.description,
                lower_bound: metric.lower_bound,
                upper_bound: metric.upper_bound,
                is_higher_better: metric.is_higher_better,
                p10: metric.p10,
                p25: metric.p25,
                p50: metric.p50,
                p75: metric.p75,
                p90: metric.p90,
                mean: metric.mean,
                std_dev: metric.std_dev,
                sample_size: metric.sample_size
            })
            MERGE (d)-[:HAS_METRIC]->(m)
            """,
            dataset_id=dataset.dataset_id,
            tenant_id=dataset.tenant_id,
            name=dataset.name,
            description=dataset.description,
            industry=dataset.industry,
            segment=dataset.segment,
            geography=dataset.geography,
            version=dataset.version,
            data_source=dataset.data_source,
            is_public=dataset.is_public,
            ownership_mode=dataset.ownership_mode,
            created_at=dataset.created_at.isoformat() if dataset.created_at else None,
            updated_at=dataset.updated_at.isoformat() if dataset.updated_at else None,
            metrics=[_metric_to_dict(m) for m in dataset.metrics.values()],
        )

    async def get_dataset(self, dataset_id: str, tenant_id: str) -> BenchmarkDataset | None:
        """Retrieve a dataset by ID with all metrics."""
        tenant_id = self._require_tenant_scope(tenant_id, operation="get_dataset")
        async with self._driver.session() as session:
            result = await session.execute_read(self._tx_get_dataset, dataset_id, tenant_id)
            return result

    @staticmethod
    async def _tx_get_dataset(tx, dataset_id: str, tenant_id: str) -> BenchmarkDataset | None:
        records = await tx.run(
            """
            MATCH (d:BenchmarkDataset {dataset_id: $dataset_id})
            WHERE d.tenant_id = $tenant_id OR d.ownership_mode = 'global_system'
            OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:BenchmarkMetric)
            RETURN d, collect(m) AS metrics
            """,
            dataset_id=dataset_id,
            tenant_id=tenant_id,
        )
        record = await records.single()
        if not record:
            return None
        return _node_to_dataset(record["d"], record["metrics"])

    async def list_datasets(
        self, industry: str | None = None, segment: str | None = None, *, tenant_id: str
    ) -> list[BenchmarkDataset]:
        """List datasets with optional filters."""
        tenant_id = self._require_tenant_scope(tenant_id, operation="list_datasets")
        async with self._driver.session() as session:
            result = await session.execute_read(
                self._tx_list_datasets, industry, segment, tenant_id
            )
            return result

    @staticmethod
    async def _tx_list_datasets(
        tx, industry: str | None, segment: str | None, tenant_id: str
    ) -> list[BenchmarkDataset]:
        query = """
            MATCH (d:BenchmarkDataset)
            OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:BenchmarkMetric)
            RETURN d, collect(m) AS metrics
        """
        conditions = ["(d.tenant_id = $tenant_id OR d.ownership_mode = 'global_system')"]
        if industry:
            conditions.append("d.industry = $industry")
        if segment:
            conditions.append("d.segment = $segment")
        if conditions:
            query = query.replace(
                "MATCH (d:BenchmarkDataset)",
                "MATCH (d:BenchmarkDataset) WHERE " + " AND ".join(conditions),
            )

        records = await tx.run(query, industry=industry, segment=segment, tenant_id=tenant_id)
        datasets = []
        async for record in records:
            datasets.append(_node_to_dataset(record["d"], record["metrics"]))
        return datasets

    async def delete_dataset(self, dataset_id: str, tenant_id: str) -> None:
        """Delete a dataset and its metrics."""
        tenant_id = self._require_tenant_scope(tenant_id, operation="delete_dataset")
        async with self._driver.session() as session:
            await session.execute_write(self._tx_delete_dataset, dataset_id, tenant_id)

    @staticmethod
    async def _tx_delete_dataset(tx, dataset_id: str, tenant_id: str) -> None:
        await tx.run(
            """
            MATCH (d:BenchmarkDataset {dataset_id: $dataset_id, tenant_id: $tenant_id})
            OPTIONAL MATCH (d)-[:HAS_METRIC]->(m:BenchmarkMetric)
            DETACH DELETE d, m
            """,
            dataset_id=dataset_id,
            tenant_id=tenant_id,
        )


def _metric_to_dict(metric: BenchmarkMetric) -> dict[str, Any]:
    """Serialize a BenchmarkMetric for Cypher."""
    return {
        "name": metric.name,
        "unit": metric.unit,
        "description": metric.description,
        "lower_bound": str(metric.lower_bound) if metric.lower_bound is not None else None,
        "upper_bound": str(metric.upper_bound) if metric.upper_bound is not None else None,
        "is_higher_better": metric.is_higher_better,
        "p10": str(metric.profile.p10),
        "p25": str(metric.profile.p25),
        "p50": str(metric.profile.p50),
        "p75": str(metric.profile.p75),
        "p90": str(metric.profile.p90),
        "mean": str(metric.profile.mean),
        "std_dev": str(metric.profile.std_dev),
        "sample_size": metric.profile.sample_size,
    }


def _node_to_dataset(node: Any, metric_nodes: list[Any]) -> BenchmarkDataset:
    """Reconstruct a BenchmarkDataset from Neo4j nodes."""
    dataset = BenchmarkDataset(
        dataset_id=node["dataset_id"],
        name=node["name"],
        description=node["description"],
        industry=node["industry"],
        segment=node.get("segment"),
        geography=node.get("geography"),
        version=node.get("version", "1.0.0"),
        data_source=node.get("data_source"),
        is_public=node.get("is_public", False),
        tenant_id=node.get("tenant_id", "system"),
        ownership_mode=node.get("ownership_mode", "tenant"),
    )
    if node.get("created_at"):
        dataset.created_at = datetime.fromisoformat(node["created_at"])
    if node.get("updated_at"):
        dataset.updated_at = datetime.fromisoformat(node["updated_at"])

    for m in metric_nodes:
        if m is None:
            continue
        profile = StatisticalProfile(
            p10=Decimal(m["p10"]),
            p25=Decimal(m["p25"]),
            p50=Decimal(m["p50"]),
            p75=Decimal(m["p75"]),
            p90=Decimal(m["p90"]),
            mean=Decimal(m["mean"]),
            std_dev=Decimal(m["std_dev"]),
            sample_size=m["sample_size"],
        )
        metric = BenchmarkMetric(
            name=m["name"],
            unit=m["unit"],
            description=m["description"],
            profile=profile,
            lower_bound=Decimal(m["lower_bound"]) if m.get("lower_bound") else None,
            upper_bound=Decimal(m["upper_bound"]) if m.get("upper_bound") else None,
            is_higher_better=m.get("is_higher_better", True),
        )
        dataset.metrics[metric.name] = metric

    return dataset
