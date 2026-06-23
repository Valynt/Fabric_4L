"""Budget tests for known expensive graph and formula operations."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.performance]

GRAPH_RAG_PATH = Path("services/layer3-knowledge/src/retrieval/graph_rag.py")
HYBRID_SEARCH_PATH = Path("services/layer3-knowledge/src/retrieval/hybrid_search.py")
FORMULA_PROFILE_PATH = Path("tests/performance/k6/formula-evaluation.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_graphrag_seed_entity_lookup_uses_batched_query_shape() -> None:
    source = _source(GRAPH_RAG_PATH)

    assert "UNWIND" in source, "seed entity enrichment must stay batched, not N+1"
    assert "entity_ids" in source, "batched lookup must pass bounded entity id lists"
    assert re.search(r"LIMIT\s+\$?limit", source, flags=re.IGNORECASE), "graph expansion queries must retain explicit limits"


def test_hybrid_search_keeps_top_k_and_parallel_source_limits() -> None:
    source = _source(HYBRID_SEARCH_PATH)
    tree = ast.parse(source)
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert {"_bm25_search", "_vector_search", "_graph_search"}.issubset(function_names)
    assert "asyncio.gather" in source, "hybrid search sources should remain concurrent"
    assert "top_k" in source, "search APIs must retain explicit result limits"


def test_formula_evaluation_profile_has_complexity_and_batch_limits() -> None:
    source = _source(FORMULA_PROFILE_PATH)

    assert "formula_eval_duration_ms: ['p(95)<2000']" in source
    assert "formula_eval_error_rate: ['rate<0.02']" in source
    assert "runComplexFormula" in source
    assert "runBatchEvaluation" in source
    assert "timeout: '20s'" in source, "batch formula evaluation must have a hard timeout"
