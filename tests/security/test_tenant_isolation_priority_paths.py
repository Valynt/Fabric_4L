from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PRIORITY_FILES = [
    "services/layer1-ingestion/src/api/routes/compatibility.py",
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    "services/layer3-knowledge/src/api/routes/knowledge.py",
    "services/layer3-knowledge/src/api/routes/query_search.py",
    "services/layer4-agents/src/layer4_agents/api/routes/intelligence.py",
    "services/layer4-agents/src/layer4_agents/api/routes/prospects.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/repositories/benchmark_repository.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/services/assumption_approval_service.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/observability/structured_logging.py",
]

FORBIDDEN_PATTERNS = [
    ".json().get(\"tenant_id\")",
    "payload.tenant_id",
    "request.tenant_id",
    "body.tenant_id",
]

REQUIRED_AUTH_PATTERNS = {
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py": ["governance_context", "Depends(get_tenant_id)"],
    "services/layer3-knowledge/src/api/routes/query_search.py": ["tenant_id", "ctx"],
    "services/layer4-agents/src/layer4_agents/api/routes/intelligence.py": ["Depends(get_verified_tenant_id)", "tenant_id: str"],
    "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py": ["_require_tenant_id", "ctx.tenant_id"],
    "services/layer5-ground-truth/src/layer5_ground_truth/services/assumption_approval_service.py": [
        "_require_assumption_tenant",
        "ApprovalRequest.tenant_id == tenant_id",
    ],
    "services/layer5-ground-truth/src/layer5_ground_truth/observability/structured_logging.py": [
        "governance_context",
    ],
}


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_priority_paths_do_not_source_tenant_from_request_payload() -> None:
    for rel_path in PRIORITY_FILES:
        content = _read(rel_path)
        for forbidden in FORBIDDEN_PATTERNS:
            assert forbidden not in content, f"{rel_path} contains forbidden tenant source: {forbidden}"


def test_priority_paths_reference_authenticated_context() -> None:
    for rel_path, patterns in REQUIRED_AUTH_PATTERNS.items():
        content = _read(rel_path)
        for pattern in patterns:
            assert pattern in content, f"{rel_path} missing expected auth-context pattern: {pattern}"
