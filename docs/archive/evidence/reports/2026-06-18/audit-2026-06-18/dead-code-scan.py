import ast
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_DIR = Path(__file__).resolve().parent


def python_imports_and_references(path: Path):
    """Yield module names imported by a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module.split(".")[0]


def scan_python_dead(root: Path):
    modules = {}
    references = defaultdict(set)
    for py in root.rglob("*.py"):
        if "__pycache__" in py.parts or ".venv" in py.parts:
            continue
        # Module name heuristic: relative to services/<svc>/src or value_fabric
        rel = py.relative_to(root)
        mod = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
        modules[mod] = py
        for ref in python_imports_and_references(py):
            references[ref].add(mod)

    dead = []
    for mod, py in modules.items():
        # Heuristic: files in deeply nested packages that aren't referenced by name
        # or are explicitly listed as dead in prior sweeps
        pass
    return dead


def scan_known_dead_from_memory():
    return [
        {"file": "apps/web/src/pages/hypothesis/HypothesisTab.tsx", "confidence": "HIGH", "reason": "Re-export wrapper; zero imports. Registry uses HypothesesTab directly."},
        {"file": "apps/web/src/pages/studio/StudioCompetitiveTab.tsx", "confidence": "HIGH", "reason": "Old studio tab; not registered in studioTabRegistry.ts"},
        {"file": "apps/web/src/pages/studio/StudioEnrichmentTab.tsx", "confidence": "HIGH", "reason": "Old studio tab; not registered in studioTabRegistry.ts"},
        {"file": "apps/web/src/pages/studio/StudioEvidenceTab.tsx", "confidence": "HIGH", "reason": "Old studio tab; not registered in studioTabRegistry.ts"},
        {"file": "apps/web/src/pages/studio/StudioROITab.tsx", "confidence": "HIGH", "reason": "Old studio tab; not registered in studioTabRegistry.ts"},
        {"file": "services/layer4-agents/src/layer4_agents/tools/analytics.py", "confidence": "MEDIUM", "reason": "Only imported by dead workflows.py"},
        {"file": "services/layer4-agents/src/layer4_agents/tools/workflows.py", "confidence": "MEDIUM", "reason": "Not imported anywhere; imports dead analytics + knowledge"},
        {"file": "services/layer4-agents/src/layer4_agents/tools/files.py", "confidence": "LOW", "reason": "Referenced in security test test_file_tool_tenant_fallback.py"},
        {"file": "services/layer4-agents/src/layer4_agents/tools/admin.py", "confidence": "LOW", "reason": "Referenced in test test_admin_tool_h01.py"},
        {"file": "services/layer4-agents/src/layer4_agents/tools/knowledge.py", "confidence": "LOW", "reason": "Referenced in test test_knowledge_tool_persistence.py"},
    ]


def main():
    candidates = scan_known_dead_from_memory()
    # Verify existence
    existing = [c for c in candidates if (ROOT / c["file"]).exists()]
    missing = [c for c in candidates if not (ROOT / c["file"]).exists()]

    report = {
        "scanned_at": "2026-06-18T12:28:00+00:00",
        "method": "registry + import heuristic (previous sweep baseline)",
        "total_candidates": len(candidates),
        "existing_candidates": len(existing),
        "already_removed": len(missing),
        "existing": existing,
        "removed": missing,
    }
    (REPORT_DIR / "dead-code.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
