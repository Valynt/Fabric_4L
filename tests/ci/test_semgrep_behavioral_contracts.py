"""Behavioral contract tests for Semgrep rules, SARIF parsing, and baseline gating.

Validates:
1. Stability of rule IDs and required metadata.
2. Behavioral detection on known-bad fixtures and non-detection on safe fixtures.
3. Proper allowlist provenance enforcement for dynamic Cypher annotations.
4. Correct SARIF parsing, multi-run aggregation, error filtering, and baseline matching.
5. Fail-closed behavior on unbaselined findings and malformed inputs.
6. Completeness of security paths in .github/paths-filters.yml.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

import pytest
import yaml

from scripts.ci.check_semgrep_sarif import (
    BaselineEntry,
    SarifErrorFinding,
    is_baselined,
    load_baseline,
    match_findings_against_baseline,
    normalize_path,
    normalize_rule_id,
    parse_sarif_errors,
)

ROOT = Path(__file__).resolve().parents[2]
SEMGREP_DIR = ROOT / ".semgrep"
PATHS_FILTERS = ROOT / ".github/paths-filters.yml"
SECURITY_WORKFLOW = ROOT / ".github/workflows/security-gates.yml"
BASELINE_PATH = ROOT / "config/ci/semgrep_baseline.json"


EXPECTED_CUSTOM_RULES = {
    "block-direct-graph-mutation",
    "cypher-dynamic-label-injection",
    "cypher-dynamic-rel-type-injection",
    "cypher-dynamic-where-clause",
    "cypher-dynamic-set-clause",
    "error-str-leakage-in-result-dict",
    "error-str-leakage-in-logger-extra",
    "error-str-leakage-in-celery-stage",
}


def _load_all_rules() -> dict[str, dict[str, object]]:
    rules: dict[str, dict[str, object]] = {}
    for yml_file in SEMGREP_DIR.glob("*.yml"):
        data = yaml.safe_load(yml_file.read_text(encoding="utf-8"))
        if not data or "rules" not in data:
            continue
        for r in data["rules"]:
            rules[r["id"]] = r
    return rules


def test_custom_rules_exist_and_have_valid_metadata() -> None:
    rules = _load_all_rules()
    for rule_id in EXPECTED_CUSTOM_RULES:
        assert rule_id in rules, f"Missing expected custom rule: {rule_id}"
        rule = rules[rule_id]
        assert "message" in rule and rule["message"].strip()
        assert "severity" in rule and rule["severity"] in ("ERROR", "WARNING", "INFO")
        assert "languages" in rule and "python" in rule["languages"]
        assert "metadata" in rule
        assert "category" in rule["metadata"]


def test_paths_filters_code_scope_covers_all_security_surfaces() -> None:
    data = yaml.safe_load(PATHS_FILTERS.read_text(encoding="utf-8"))
    assert "code" in data
    code_patterns = set(data["code"])

    expected_surfaces = [
        "services/**",
        "apps/**",
        "packages/**",
        "contracts/**",
        "tests/**",
        "packs/**",
        "infra/**",
        "k8s/**",
        "sdk/**",
        "docs-site/**",
        "examples/**",
        ".semgrep/**",
        ".semgrepignore",
    ]
    for surface in expected_surfaces:
        assert (
            surface in code_patterns
        ), f"Missing security surface {surface} in code: filter"


def test_security_workflow_runs_baseline_check() -> None:
    workflow_text = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    assert "check_semgrep_sarif.py" in workflow_text
    assert "config/ci/semgrep_baseline.json" in workflow_text


def _run_semgrep_on_code(code_snippet: str, rule_id: str) -> list[dict[str, object]]:
    rules_map = _load_all_rules()
    rule = rules_map[rule_id]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        rule_file = tmp_path / "rule.yml"
        rule_file.write_text(yaml.dump({"rules": [rule]}), encoding="utf-8")

        # Write code file in simulated services/layer3-knowledge directory so path filters pass
        target_dir = tmp_path / "services" / "layer3-knowledge" / "src"
        target_dir.mkdir(parents=True, exist_ok=True)
        code_file = target_dir / "target.py"
        code_file.write_text(code_snippet, encoding="utf-8")

        cmd = [
            "semgrep",
            "scan",
            "--config",
            str(rule_file),
            "--metrics",
            "off",
            "--json",
            str(code_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        try:
            res = json.loads(proc.stdout)
            return res.get("results", [])
        except json.JSONDecodeError:
            pytest.fail(
                f"Semgrep failed to produce JSON: {proc.stderr}\nStdout: {proc.stdout}"
            )


def test_block_direct_mutation_behavior() -> None:
    bad_code = '''
def mutate_node(tx, tenant_id, name):
    tx.run("""
        MERGE (n:Entity {tenant_id: $tenant_id, name: $name})
        SET n.updated_at = datetime()
    """, tenant_id=tenant_id, name=name)
'''
    results = _run_semgrep_on_code(bad_code, "block-direct-graph-mutation")
    assert len(results) >= 1, "Expected direct MERGE mutation to be flagged"

    safe_code = """
def mutate_node(mutation, tenant_id, name):
    # cypher-mutation-safe: audited gateway
    mutation.write_node("Entity", "id-123", {"name": name})
"""
    results_safe = _run_semgrep_on_code(safe_code, "block-direct-graph-mutation")
    assert len(results_safe) == 0, "Expected safe AuditedGraphMutation to remain clean"


def test_cypher_label_injection_behavior() -> None:
    bad_fstring = """
def get_nodes(session, target_label):
    query = f"MATCH (n:{target_label}) RETURN n"
    return session.run(query)
"""
    results = _run_semgrep_on_code(bad_fstring, "cypher-dynamic-label-injection")
    assert len(results) >= 1, "Expected dynamic label interpolation to be flagged"

    # Fake suppression without allowlist provenance must STILL fail
    bad_suppression = """
def get_nodes(session, target_label):
    query = f"MATCH (n:{target_label}) RETURN n"  # cypher-dynamic-safe: ignore
    return session.run(query)
"""
    results_bad_suppr = _run_semgrep_on_code(
        bad_suppression, "cypher-dynamic-label-injection"
    )
    assert (
        len(results_bad_suppr) >= 1
    ), "Expected fake suppression without allowlist provenance to be flagged"

    # Verified allowlist provenance is accepted
    safe_provenance = """
def get_nodes(session, target_label):
    query = f"MATCH (n:{target_label}) RETURN n"  # cypher-dynamic-safe: validated against _ALLOWED_TARGET_LABELS
    return session.run(query)
"""
    results_safe = _run_semgrep_on_code(
        safe_provenance, "cypher-dynamic-label-injection"
    )
    assert (
        len(results_safe) == 0
    ), "Expected valid allowlist provenance to suppress safely"


def test_cypher_rel_type_injection_behavior() -> None:
    bad_rel = """
def get_relationships(session, rel_type):
    query = f"MATCH (a)-[:{rel_type}]->(b) RETURN a, b"
    return session.run(query)
"""
    results = _run_semgrep_on_code(bad_rel, "cypher-dynamic-rel-type-injection")
    assert len(results) >= 1, "Expected dynamic rel_type to be flagged"

    safe_rel = """
def get_relationships(session, rel_type):
    query = f"MATCH (a)-[:{rel_type}]->(b) RETURN a, b"  # cypher-dynamic-safe: validated against _ALLOWED_REL_TYPES
    return session.run(query)
"""
    results_safe = _run_semgrep_on_code(safe_rel, "cypher-dynamic-rel-type-injection")
    assert (
        len(results_safe) == 0
    ), "Expected valid allowlist provenance to suppress safely"


def test_error_str_leakage_logging_not_flagged_as_result_dict() -> None:
    logger_code = """
def handle_request():
    try:
        do_something()
    except Exception as e:
        logger.info("request failed", extra={"error": str(e), "status": 500})
        return {"error": "An internal error occurred", "code": 500}
"""
    results = _run_semgrep_on_code(logger_code, "error-str-leakage-in-result-dict")
    assert (
        len(results) == 0
    ), "Logging extra dictionary must NOT trigger result-dict error rule"

    leakage_code = """
def handle_request():
    try:
        do_something()
    except Exception as e:
        return {"error": str(e), "success": False}
"""
    results_leak = _run_semgrep_on_code(
        leakage_code, "error-str-leakage-in-result-dict"
    )
    assert len(results_leak) >= 1, "Actual error string in return dict MUST be flagged"


def test_sarif_parser_and_baseline_matching() -> None:
    sample_sarif = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "semgrep",
                        "rules": [
                            {
                                "id": "semgrep.cypher-dynamic-label-injection",
                                "defaultConfiguration": {"level": "error"},
                            },
                            {
                                "id": "semgrep.cypher-dynamic-where-clause",
                                "defaultConfiguration": {"level": "warning"},
                            },
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": "semgrep.cypher-dynamic-label-injection",
                        "level": "error",
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": "services/layer3-knowledge/query.py"
                                    },
                                    "region": {"startLine": 42},
                                }
                            }
                        ],
                        "message": {"text": "Dynamic label injection"},
                    },
                    {
                        "ruleId": "semgrep.cypher-dynamic-where-clause",
                        "level": "warning",
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": "services/layer3-knowledge/filter.py"
                                    },
                                    "region": {"startLine": 10},
                                }
                            }
                        ],
                        "message": {"text": "Dynamic where clause warning"},
                    },
                ],
            }
        ],
    }

    findings = parse_sarif_errors(sample_sarif)
    assert len(findings) == 1
    assert findings[0].rule_id == "semgrep.cypher-dynamic-label-injection"
    assert findings[0].path == "services/layer3-knowledge/query.py"
    assert findings[0].line == 42

    exact_baseline = {
        (
            "semgrep.cypher-dynamic-label-injection",
            "services/layer3-knowledge/query.py",
            42,
        )
    }
    flexible_baseline = {
        ("semgrep.cypher-dynamic-label-injection", "services/layer3-knowledge/query.py")
    }

    assert is_baselined(findings[0], exact_baseline, flexible_baseline) is True

    new_finding = SarifErrorFinding(
        rule_id="semgrep.cypher-dynamic-label-injection",
        path="services/layer3-knowledge/new_file.py",
        line=10,
    )
    assert is_baselined(new_finding, exact_baseline, flexible_baseline) is False


def test_sarif_parser_handles_malformed_and_empty() -> None:
    empty_sarif = {"version": "2.1.0", "runs": []}
    assert parse_sarif_errors(empty_sarif) == []

    with pytest.raises(ValueError):
        parse_sarif_errors({"invalid": "format"})

    with pytest.raises(ValueError):
        parse_sarif_errors(cast(dict[str, object], []))


def test_checked_in_baseline_file_is_valid() -> None:
    assert BASELINE_PATH.exists(), f"Baseline file missing at {BASELINE_PATH}"
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert "allowed_errors" in data
    assert isinstance(data["allowed_errors"], list)


def test_exact_1_to_1_baseline_matching_and_bounded_relocation() -> None:
    # 1 baseline entry at line 50
    entries = [
        BaselineEntry(
            rule_id="block-direct-graph-mutation",
            path="services/api/app/core/database.py",
            line=50,
        )
    ]

    # Finding 1: exact match at line 50
    f1 = SarifErrorFinding(
        "block-direct-graph-mutation", "services/api/app/core/database.py", 50
    )
    baselined, new_errs = match_findings_against_baseline([f1], entries)
    assert len(baselined) == 1
    assert len(new_errs) == 0

    # Finding 2: shifted line (53, delta=3) is NOT baselined anymore: proximity
    # matching was removed so a removed legacy finding cannot mask a new nearby
    # finding. It must surface as a NEW error (SEC review feedback).
    f2 = SarifErrorFinding(
        "block-direct-graph-mutation", "services/api/app/core/database.py", 53
    )
    baselined, new_errs = match_findings_against_baseline(
        [f2], entries, max_line_delta=10
    )
    assert len(baselined) == 0
    assert len(new_errs) == 1
    assert new_errs[0] == f2

    # Finding 3: far unlisted line (line 150, delta=100 > 10) -> MUST FAIL (not baselined)
    f3 = SarifErrorFinding(
        "block-direct-graph-mutation", "services/api/app/core/database.py", 150
    )
    baselined, new_errs = match_findings_against_baseline(
        [f3], entries, max_line_delta=10
    )
    assert len(baselined) == 0
    assert len(new_errs) == 1

    # Finding 4: two findings in same file when only 1 baseline entry exists (1:1 consumption)
    # 1 should match, 2nd must be flagged as NEW error
    f_legit = SarifErrorFinding(
        "block-direct-graph-mutation", "services/api/app/core/database.py", 50
    )
    f_regression = SarifErrorFinding(
        "block-direct-graph-mutation", "services/api/app/core/database.py", 52
    )
    baselined, new_errs = match_findings_against_baseline(
        [f_legit, f_regression], entries, max_line_delta=10
    )
    assert len(baselined) == 1
    assert len(new_errs) == 1
    assert new_errs[0] == f_regression

    # Finding 5: a line=0 wildcard baseline entry matches any single finding 1:1
    wildcard_entries = [
        BaselineEntry(
            rule_id="block-direct-graph-mutation",
            path="services/api/app/core/database.py",
            line=0,
        )
    ]
    f_wild = SarifErrorFinding(
        "block-direct-graph-mutation", "services/api/app/core/database.py", 77
    )
    baselined, new_errs = match_findings_against_baseline(
        [f_wild], wildcard_entries, max_line_delta=10
    )
    assert len(baselined) == 1
    assert len(new_errs) == 0
    # Wildcard consumes only one finding; a second finding must be NEW.
    baselined, new_errs = match_findings_against_baseline(
        [f_wild, f2], wildcard_entries, max_line_delta=10
    )
    assert len(baselined) == 1
    assert len(new_errs) == 1
