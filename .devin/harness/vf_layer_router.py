"""Value Fabric layer router.

Maps file paths + task intent to affected layer(s) and emits boundary
warnings to prevent cross-layer drift.
"""
from typing import Dict, List, Tuple

__all__ = ["classify_paths", "detect_layers", "warn_on_cross_layer"]

# Canonical path prefixes per layer.
# MUST stay in sync with canonical-paths-policy.md.
LAYER_PREFIXES = {
    1: ["services/layer1-ingestion/", "value_fabric/layer1/"],
    2: ["services/layer2-extraction/", "value_fabric/layer2/"],
    3: ["services/layer3-knowledge/", "value_fabric/layer3/"],
    4: ["value_fabric/layer4/", "layer4_agents/", "services/layer4-agents/"],
    5: ["services/layer5-ground-truth/", "value_fabric/layer5/"],
    6: ["services/layer6-benchmarks/", "value_fabric/layer6/"],
    "frontend": ["apps/web/"],
    "contracts": ["contracts/", "packages/platform-contract/"],
    "shared": ["value_fabric/shared/", "packages/shared/"],
}

# Keywords for query-based layer detection
LAYER_KEYWORDS = {
    1: ["layer1", "ingestion", "crawl", "celery", "redis", "playwright", "queue", "job"],
    2: ["layer2", "extraction", "ontology", "rdf", "owl", "pydantic", "provenance", "batch"],
    3: ["layer3", "knowledge", "neo4j", "graphrag", "pgvector", "subgraph", "entity", "hybrid retrieval"],
    4: ["layer4", "agents", "langgraph", "workflow", "orchestration", "roi", "business case", "checkpoint"],
    5: ["layer5", "ground truth", "truthobject", "maturity", "validation", "evidence", "claim"],
    6: ["layer6", "benchmark", "peer comparison", "statistical validation", "dataset"],
}


def _normalize_path(p: str) -> str:
    """Normalize backslashes to forward slashes for cross-platform matching."""
    return p.replace("\\", "/")


def classify_paths(paths: List[str]) -> Dict[str, List[str]]:
    """Map each path to its primary layer(s)."""
    hits: Dict[str, List[str]] = {k: [] for k in LAYER_PREFIXES}
    for p in paths:
        normalized = _normalize_path(p)
        for layer, prefixes in LAYER_PREFIXES.items():
            if any(normalized.startswith(pre) for pre in prefixes):
                hits[layer].append(p)
    return {k: v for k, v in hits.items() if v}


def detect_layers(query: str, file_paths: List[str]) -> Tuple[List[int], bool]:
    """Infer affected layers from file paths + task description.

    Returns (sorted_layer_numbers, is_frontend).
    """
    layers: set = set()
    path_str = " ".join(_normalize_path(p) for p in file_paths).lower()
    query_lower = query.lower()

    # Path-based detection
    classified = classify_paths(file_paths)
    for layer, hits in classified.items():
        if isinstance(layer, int) and hits:
            layers.add(layer)

    # Query-based detection
    for layer, markers in LAYER_KEYWORDS.items():
        for m in markers:
            if m in query_lower:
                layers.add(layer)
                break

    is_frontend = any(
        _normalize_path(p).startswith("apps/web/") for p in file_paths
    ) or any(k in query_lower for k in ("frontend", "ui", "react"))

    return sorted(layers), is_frontend


def warn_on_cross_layer(file_paths: List[str], intent: str) -> List[str]:
    """Return warnings if a task appears to cross layer boundaries improperly.

    These are advisory, not blocking. The contract guard handles blocking checks.
    """
    layers, is_frontend = detect_layers(intent, file_paths)
    warnings = []

    if len(layers) > 2:
        warnings.append(
            f"CROSS_LAYER_WARNING: Task touches {len(layers)} layers ({layers}). "
            "Value Fabric rule: preserve layer responsibilities. "
            "Confirm this is an explicit cross-layer refactor, not accidental drift."
        )

    classified = classify_paths(file_paths)
    active_layers = [k for k, v in classified.items() if v]
    if "contracts" in classified and len(active_layers) == 1:
        warnings.append(
            "CONTRACT_WORKFLOW: Changing contracts without updating consumers "
            "(frontend types, backend routes, tests) is a contract drift risk. "
            "Run: make contract-tests"
        )

    if is_frontend and any(k in intent.lower() for k in ("api", "endpoint", "backend", "route", "schema")):
        warnings.append(
            "FRONTEND_API_DRIFT_RISK: Frontend task mentions backend APIs. "
            "Ensure OpenAPI contract, TanStack Query hooks, and Zod schemas are updated together."
        )

    if not layers and not is_frontend:
        warnings.append(
            "LAYER_UNKNOWN: Could not determine target layer from paths or query. "
            "Consider adding layer-specific keywords to the task description."
        )

    return warnings


def main():
    """CLI entry point: print layer classification and warnings."""
    import os
    import sys

    intent = os.environ.get("TASK", "")
    files_raw = os.environ.get("FILES", "")
    file_paths = [p.strip() for p in files_raw.split(",") if p.strip()]

    if not intent:
        print("Usage: TASK='<intent>' FILES='path1,path2' python vf_layer_router.py")
        sys.exit(1)

    layers, is_frontend = detect_layers(intent, file_paths)
    classified = classify_paths(file_paths)
    warnings = warn_on_cross_layer(file_paths, intent)

    print(f"Detected layers: {layers}")
    print(f"Is frontend: {is_frontend}")
    print("\nPath classification:")
    for layer, hits in classified.items():
        print(f"  {layer}: {len(hits)} file(s)")
        for h in hits:
            print(f"    - {h}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("\nNo warnings.")


if __name__ == "__main__":
    main()
