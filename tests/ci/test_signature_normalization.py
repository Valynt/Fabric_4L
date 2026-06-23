from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "ci" / "signature_normalization.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "signature_normalization", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalizes_common_volatile_ci_tokens_to_same_hash() -> None:
    module = _load_module()
    first = """
    2026-06-03T12:34:56.789Z run_id=123456789 job_id=987654321
    FAILED /workspace/Fabric_4L/services/layer1/file.py:123:45 AssertionError at 0x7f8a9b0c1d2e
    request_id=123e4567-e89b-12d3-a456-426614174000 on localhost:54321 port 3001
    tmp file /tmp/pytest-of-runner/pytest-123/test_case0/output.tmp
    pnpm-cache-key=linux-pnpm-abcdef123456
    commit abcdef1234567890abcdef1234567890abcdef12
    """
    second = """
    2026-06-03T13:00:01.111Z run_id=222222222 job_id=333333333
    FAILED /workspace/Fabric_4L/services/layer1/file.py:777:3 AssertionError at 0x9abcdef01234
    request_id=123e4567-e89b-12d3-a456-426614174999 on localhost:65432 port 8080
    tmp file /tmp/pytest-of-runner/pytest-999/test_case1/output.tmp
    pnpm-cache-key=linux-pnpm-999999999999
    commit 1111111234567890abcdef1234567890abcdef99
    """

    normalized_first = module.normalize_ci_log_signature(first)
    normalized_second = module.normalize_ci_log_signature(second)

    assert (
        normalized_first.normalized_signature_hash
        == normalized_second.normalized_signature_hash
    )
    assert "<workspace_path>" in normalized_first.normalized_text
    assert (
        "<workspace_path>/services/layer1/file.py:<line>:<col>"
        in normalized_first.normalized_text
    )
    assert "<timestamp>" in normalized_first.normalized_text
    assert "<uuid>" in normalized_first.normalized_text
    assert "<run_id>" in normalized_first.normalized_text
    assert "<host>:<port>" in normalized_first.normalized_text
    assert "<temp_path>" in normalized_first.normalized_text
    assert "<package_cache_key>" in normalized_first.normalized_text
    assert "<commit_sha>" in normalized_first.normalized_text
    assert normalized_first.signature_summary.startswith("<timestamp> <run_id>")


def test_normalizes_pre_tokenized_source_locations_without_bad_group_references() -> None:
    module = _load_module()

    normalized = module.normalize_ci_log_signature(
        "FAILED <temp_path>:123:45 and <workspace_path>:987"
    )

    assert "<temp_path>:<line>:<col>" in normalized.normalized_text
    assert "<workspace_path>:<line>" in normalized.normalized_text
    assert "<workspace_path>:<line>:" not in normalized.normalized_text


def test_recurrence_counts_group_by_workflow_job_hash_and_primary_category() -> None:
    module = _load_module()
    records = [
        {
            "workflow": "pr-checks",
            "job": "lint",
            "normalized_signature_hash": "aaa",
            "primary_category": "SOURCE_PATH_DRIFT",
        },
        {
            "workflow": "pr-checks",
            "job": "lint",
            "normalized_signature_hash": "aaa",
            "primary_category": "SOURCE_PATH_DRIFT",
        },
        {
            "workflow": "pr-checks",
            "job": "test",
            "normalized_signature_hash": "aaa",
            "primary_category": "SOURCE_PATH_DRIFT",
        },
        {
            "workflow": "pr-checks",
            "job": "lint",
            "normalized_signature_hash": "aaa",
            "primary_category": "TIMEOUT",
        },
    ]

    annotated = module.attach_recurrence_counts(records)

    assert [record["recurrence_count"] for record in annotated] == [2, 2, 1, 1]
    assert (
        module.summarize_recurrences(records)[
            ("pr-checks", "lint", "aaa", "SOURCE_PATH_DRIFT")
        ]
        == 2
    )
