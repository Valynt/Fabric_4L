#!/usr/bin/env python3
"""Bulk conflict resolver. Handles nested ours/theirs markers."""
from __future__ import annotations

import sys
from pathlib import Path


def resolve_text(content: str, keep: str) -> str:
    """Strip merge-conflict markers, keeping the chosen side.

    Handles nested markers by counting depth.
    keep: 'head' (top half of outermost conflict) or 'branch' (bottom half).
    """
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    # stack of bool: True means we're currently in the "top" half of that conflict
    # We only keep lines whose entire stack of conflict contexts allows it.
    stack: list[bool] = []  # element = is_top_half flag at that depth

    def keeping() -> bool:
        if not stack:
            return True
        # The outermost decision is stack[0]; we keep the chosen side at depth 0.
        # For deeper nesting we keep the top half by default (since 315e84c1
        # files use nested <ours>/<theirs> inside HEAD vs 315e84c1 outer).
        # If outer says we keep head and we're in head, recurse for nested.
        # Simpler rule: keep line iff at every level the half we're in is kept.
        for depth, in_top in enumerate(stack):
            if depth == 0:
                want_top = (keep == "head")
            else:
                # For nested levels, also prefer the chosen side semantics.
                # Most nested patterns we have are HEAD-inner-ours vs theirs.
                want_top = True
            if in_top != want_top:
                return False
        return True

    for raw in lines:
        stripped = raw.lstrip()
        if stripped.startswith("<<<<<<< "):
            stack.append(True)
            continue
        if stripped.rstrip("\r\n") == "=======":
            if stack:
                stack[-1] = False
            continue
        if stripped.startswith(">>>>>>> "):
            if stack:
                stack.pop()
            continue
        if keeping():
            out.append(raw)
    return "".join(out)


def resolve_file(filepath: Path, keep: str) -> bool:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    if "<<<<<<<" not in text:
        return False
    new = resolve_text(text, keep)
    if "<<<<<<<" in new or ">>>>>>>" in new:
        print(f"  WARNING: leftover markers in {filepath}")
    filepath.write_text(new, encoding="utf-8")
    return True


# Per-file resolution map. Side: 'head' or 'branch' (315e84c1).
# Decisions are documented in reports/conflict-inventory-2026-05-19.md
DECISIONS: dict[str, str] = {
    # Layer 3 chain
    "services/layer3-knowledge/src/db/query_execution.py": "head",
    "services/layer3-knowledge/src/agents/provenance_tracking.py": "head",
    "services/layer3-knowledge/src/agents/roi_calculation.py": "head",
    "services/layer3-knowledge/src/agents/value_tree_projection.py": "head",
    "services/layer3-knowledge/src/agents/whitespace_analysis.py": "head",
    "services/layer3-knowledge/src/analytics/centrality.py": "head",
    "services/layer3-knowledge/src/analytics/communities.py": "head",
    "services/layer3-knowledge/src/analytics/similarity.py": "head",
    "services/layer3-knowledge/src/api/dependencies_tenant.py": "head",
    "services/layer3-knowledge/src/api/routes/calculators.py": "head",
    "services/layer3-knowledge/src/api/routes/entities.py": "head",
    "services/layer3-knowledge/src/api/routes/signals.py": "head",
    "services/layer3-knowledge/src/api/routes/value_packs.py": "head",
    "services/layer3-knowledge/tests/test_query_execution_boundary.py": "head",
    "services/layer3-knowledge/README.md": "head",
    # Layer 5 transitive
    "services/layer5-ground-truth/src/layer5_ground_truth/integration/layer3_client.py": "head",
    "services/layer5-ground-truth/src/layer5_ground_truth/services/freshness_monitor.py": "head",
    "services/layer5-ground-truth/tests/test_layer3_failure_modes.py": "head",
    # Layer 4 test (align with tenant_cypher choice)
    "services/layer4-agents/tests/test_context_gatherer.py": "branch",
    # Build / scripts
    "Makefile": "head",
    "scripts/check_layer3_cypher_scope.py": "head",
    "scripts/ci/check_conflict_markers.sh": "head",
    "scripts/ci/check_layer3_source_mirror.py": "head",
    "scripts/resolve_conflicts.py": "head",
    # Frontend manual
    "apps/web/src/api/workflows.ts": "branch",  # align with workflows.py L4 choice (315e84c1 schema)
    "apps/web/scripts/quality/assert-compatibility-shims-registered.mjs": "head",
    "apps/web/scripts/quality/assert-frontend-hygiene.mjs": "head",
    # Docs / audit reports
    "docs/governance/compatibility-debt-registry.md": "head",
    "docs/security/multi-tenancy.md": "head",
    "fabric_audit/v1.0.0_release_gate_report_2026-05-12.md": "head",
    "reports/RELEASE_READINESS_AUDIT_2026-05-12.md": "head",
    "reports/TEST_COVERAGE_RUBRIC_AUDIT_2026-05-12.md": "head",
    "signoff-evidence/phase-04-contracts/contract-static-tests.txt": "head",
}


def main() -> int:
    repo = Path(__file__).parent.parent
    changed = 0
    missing = 0
    for relpath, side in DECISIONS.items():
        p = repo / relpath
        if not p.exists():
            print(f"  MISSING: {relpath}")
            missing += 1
            continue
        if resolve_file(p, side):
            changed += 1
            print(f"  resolved ({side}): {relpath}")
        else:
            print(f"  no markers: {relpath}")
    print(f"\nResolved: {changed}, missing: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
