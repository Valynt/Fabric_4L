from __future__ import annotations

"""Pure Value Pack mapping and serialization helpers."""

from datetime import UTC, datetime
from typing import Any


def build_valuepack_response(
    value_pack: Any, *, completeness_score: float = 1.0
) -> Any:
    """Serialize a ValuePack domain model into its API response model."""
    from .value_packs import ValuePackResponse

    return ValuePackResponse(
        **value_pack.model_dump(), completeness_score=completeness_score
    )


def build_pack_detail_from_record(record: dict[str, Any]) -> Any:
    """Serialize a Neo4j pack detail record into the API response model."""
    from .value_packs import (
        DEFAULT_VERSION,
        BenchmarkSummary,
        FormulaSummary,
        PackDetail,
        ValueDriverSummary,
    )

    vp = record["vp"]
    drivers = [
        ValueDriverSummary(
            driver_id=d["id"],
            name=d.get("name", ""),
            category=d.get("category", ""),
            weight=1.0,
        )
        for d in record["drivers"]
        if d
    ]
    formulas = [
        FormulaSummary(
            formula_id=f["id"],
            name=f.get("name", ""),
            version=f.get("version", DEFAULT_VERSION),
            variables=f.get("variables", []),
        )
        for f in record["formulas"]
        if f
    ]
    benchmarks = [
        BenchmarkSummary(
            dataset_id=b["id"],
            metric=b.get("metric", ""),
            industry=b.get("industry", ""),
        )
        for b in record["benchmarks"]
        if b
    ]

    return PackDetail(
        pack_id=vp["id"],
        name=vp.get("name", ""),
        description=vp.get("description", ""),
        industry=vp.get("industry", ""),
        segment=vp.get("segment"),
        status=vp.get("status", "draft"),
        version=vp.get("version", DEFAULT_VERSION),
        drivers=drivers,
        formulas=formulas,
        benchmarks=benchmarks,
        created_at=vp.get("createdAt", datetime.now(UTC).isoformat()),
        updated_at=vp.get("updatedAt"),
        created_by=vp.get("createdBy"),
        workspace_id=vp.get("workspaceId"),
        is_loaded=vp.get("isLoaded", False),
        workflow_count=record["workflow_count"],
        scope=vp.get("scope", "global"),
        category=vp.get("category"),
    )
