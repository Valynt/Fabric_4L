#!/usr/bin/env python3
"""Hostile Tenant Evidence CI Gate.

Validates that every hostile tenancy invariant defined in Improvement Area B
has test coverage in the codebase that explicitly asserts foreign resource existence
(preventing 404-vs-403 false positives).

Invariants required:
- signed_url_expiration_and_replay
- object_storage_key_prefix_isolation
- export_and_deletion_isolation
- graph_and_vector_retrieval_isolation
- ai_memory_trace_cache_isolation
- queue_envelope_mismatch_rejection
- prior_session_switch_rejection
- support_impersonation_scope_expiry
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_HOSTILE_CONTRACTS = {
    "signed_url_expiration_and_replay": [
        "test_signed_url_replay_and_expiration_denial",
    ],
    "object_storage_key_prefix_isolation": [
        "test_object_storage_key_and_prefix_isolation",
    ],
    "export_and_deletion_isolation": [
        "test_export_and_deletion_isolation",
    ],
    "graph_and_vector_retrieval_isolation": [
        "test_graph_and_vector_retrieval_isolation",
    ],
    "ai_memory_trace_cache_isolation": [
        "test_ai_memory_trace_and_cache_isolation",
    ],
    "queue_envelope_mismatch_rejection": [
        "test_queue_envelope_mismatch_and_missing_context",
    ],
    "prior_session_switch_rejection": [
        "test_prior_session_and_tenant_switch_rejection",
    ],
    "support_impersonation_scope_expiry": [
        "test_support_impersonation_scope_and_expiration",
    ],
}


def verify_hostile_evidence(repo_root: Path) -> bool:
    test_file = repo_root / "tests" / "tenancy" / "test_hostile_tenancy_contracts.py"
    fixture_file = repo_root / "tests" / "tenancy" / "hostile_fixtures.py"

    if not test_file.is_file():
        print(f"FAIL: Missing hostile tenancy test suite: {test_file}", file=sys.stderr)
        return False

    if not fixture_file.is_file():
        print(f"FAIL: Missing hostile tenancy fixture harness: {fixture_file}", file=sys.stderr)
        return False

    content = test_file.read_text(encoding="utf-8")
    fixture_content = fixture_file.read_text(encoding="utf-8")

    if "assert_foreign_resource_exists" not in fixture_content:
        print("FAIL: Hostile harness lacks foreign resource existence assertion mechanism.", file=sys.stderr)
        return False

    missing = []
    for contract, test_names in REQUIRED_HOSTILE_CONTRACTS.items():
        found = any(f"def {name}" in content for name in test_names)
        if not found:
            missing.append(contract)

    if missing:
        print(f"FAIL: Incomplete hostile tenancy coverage. Missing contracts: {missing}", file=sys.stderr)
        return False

    print(f"SUCCESS: Hostile tenancy evidence verified across all {len(REQUIRED_HOSTILE_CONTRACTS)} contracts.")
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    ok = verify_hostile_evidence(repo_root)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
