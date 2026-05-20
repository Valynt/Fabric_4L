"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: API routes package.
"""

# pack_loader has no external dependencies and must always be importable.
# Other routes require neo4j, FastAPI, and agent dependencies — wrap in
# try/except so lightweight consumers (tests, CI) can import pack_loader
# without a full runtime environment.
from . import pack_loader  # Always available — no external deps

try:
    from . import (
        _utils,
        agents,
        analytics,
        benchmarks,
        calculators,
        compat_aliases,
        competitive_intel,
        documents,
        entities,
        evidence,
        formula_governance,
        formulas,
        graph_viz,
        ingestion,
        models,
        products,
        provenance_audit,
        query_search,
        roi_calculator,
        system,
        value_packs,
        value_trees,
        variables,
    )
    _ROUTES_AVAILABLE = True
except (ImportError, Exception):
    _ROUTES_AVAILABLE = False

__all__ = [
    "pack_loader",
    "_ROUTES_AVAILABLE",
    # V2 domain routers
    "agents",
    "analytics",
    "benchmarks",
    "calculators",
    "compat_aliases",
    "competitive_intel",
    "documents",
    "entities",
    "evidence",
    "formula_governance",
    "formulas",
    "graph_viz",
    "ingestion",
    "models",
    "products",
    "provenance_audit",
    "query_search",
    "roi_calculator",
    "system",
    "value_packs",
    "value_trees",
    "variables",
    "_utils",
]
