"""Golden-trace aggregation gate (V1-EVALS-001; refs #1259).

The ai-evals-pipeline ``run-golden-traces`` job executes exactly this file and
scores pass rate from the pytest report; the fail-closed workflow patch makes a
missing results file a gate failure (no evidence is not a pass, cf. #1254).
This suite is therefore the deterministic coverage behind that gate:

1. Discovery is fail-closed — zero fixtures is a failure, not a skip.
2. Every fixture conforms to the golden-trace schema contract.
3. Assertion vocabulary is well-formed (flag assertions boolean, comparators
   numeric), so a malformed assertion cannot read as coverage.
4. Trace payloads carry no secret patterns (data-policy redaction invariant).
5. Data-access skills must assert tenant scoping (tenant-boundary invariant).
6. Fixture content is pinned to the frozen baseline in
   ``evals/baselines/golden-traces-baseline.json`` — silent drift fails;
   regenerating the baseline is a deliberate, reviewable act.

Deterministic by design: no LLM calls, no network, no credentials
(``live_llm_workflows_mandatory`` is a pending human scope decision).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASELINE_PATH = (
    Path(__file__).parent.parent.parent / "evals" / "baselines" / "golden-traces-baseline.json"
)

TRACE_REQUIRED_KEYS = {"id", "description", "input", "assertions"}

# Secret patterns that must never appear in trace payloads (mirrors the
# platform log-sanitization policy in value_fabric.shared.error_handling).
SECRET_PATTERNS = ("bearer ", "access_token", "refresh_token", "api_key", "password")

# Assertion keys whose values are boolean flags.
BOOLEAN_FLAG_RE = re.compile(r"^(valid|steps_not_empty|.*_positive|.*_required|requires_.*|.*_not_empty)$")
# Assertion keys whose values are numeric bounds.
NUMERIC_BOUND_RE = re.compile(r"^(.*_lte|.*_gte|.*_gt|.*_lt|min_.*|max_.*|confidence_min|row_count|value)$")

# Skills whose traces read tenant-owned data; the tenant-boundary invariant
# requires an explicit tenant-scope assertion on every trace.
DATA_ACCESS_SKILLS = {"get_prospect_data", "query_graph", "semantic_search"}

ASSERTION_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _fixture_files() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*_traces.json"))


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


FIXTURE_FILES = _fixture_files()
FIXTURE_IDS = [p.name.removesuffix("_traces.json") for p in FIXTURE_FILES]


class TestGoldenTraceDiscovery:
    def test_fixtures_exist(self) -> None:
        """Fail closed: no golden-trace fixtures means no eval coverage."""
        assert FIXTURE_FILES, (
            f"No *_traces.json fixtures found in {FIXTURES_DIR} — "
            "a missing golden-trace suite must never read as a pass (#1254)"
        )

    def test_every_skill_has_traces(self) -> None:
        for path in FIXTURE_FILES:
            data = _load(path)
            assert data.get("traces"), f"{path.name}: fixture has zero traces"


class TestGoldenTraceSchema:
    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=FIXTURE_IDS)
    def test_fixture_envelope(self, path: Path) -> None:
        data = _load(path)
        assert data.get("version") == "1.0", f"{path.name}: unsupported version"
        skill = data.get("skill")
        assert skill == path.name.removesuffix("_traces.json"), (
            f"{path.name}: skill {skill!r} does not match filename"
        )
        assert isinstance(data["traces"], list)

    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=FIXTURE_IDS)
    def test_trace_shape_and_unique_ids(self, path: Path) -> None:
        data = _load(path)
        seen: set[str] = set()
        for trace in data["traces"]:
            tid = trace.get("id", "<missing>")
            missing = TRACE_REQUIRED_KEYS - set(trace)
            assert not missing, f"{path.name}:{tid} missing keys {sorted(missing)}"
            assert tid not in seen, f"{path.name}: duplicate trace id {tid}"
            seen.add(tid)
            assert isinstance(trace["input"], dict), f"{path.name}:{tid} input must be an object"
            assertions = trace["assertions"]
            assert isinstance(assertions, dict) and assertions, (
                f"{path.name}:{tid} must carry at least one assertion — "
                "an assertion-free trace is vacuous coverage"
            )


class TestGoldenTraceAssertionVocabulary:
    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=FIXTURE_IDS)
    def test_assertion_values_match_operator_types(self, path: Path) -> None:
        for trace in _load(path)["traces"]:
            for key, value in trace["assertions"].items():
                tid = f"{path.name}:{trace['id']}.{key}"
                assert ASSERTION_KEY_RE.match(key), f"{tid}: malformed assertion key"
                if BOOLEAN_FLAG_RE.match(key):
                    assert isinstance(value, bool), f"{tid}: flag assertion must be boolean"
                elif NUMERIC_BOUND_RE.match(key):
                    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
                        f"{tid}: bound assertion must be numeric"
                    )
                else:
                    # Remaining keys are exact-match expectations.
                    assert isinstance(value, (str, int, float, list)), (
                        f"{tid}: unsupported assertion value type {type(value).__name__}"
                    )


class TestGoldenTraceRedaction:
    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=FIXTURE_IDS)
    def test_traces_carry_no_secret_patterns(self, path: Path) -> None:
        blob = json.dumps(_load(path)).lower()
        for pattern in SECRET_PATTERNS:
            assert pattern not in blob, (
                f"{path.name}: trace payload contains {pattern!r} — "
                "traces must be redacted per data policy"
            )


class TestGoldenTraceTenantBoundary:
    def test_data_access_skills_have_fixtures(self) -> None:
        """Fail closed if no data-access skill is under tenant-scope governance."""
        covered = {
            p.name.removesuffix("_traces.json")
            for p in FIXTURE_FILES
            if p.name.removesuffix("_traces.json") in DATA_ACCESS_SKILLS
        }
        missing = DATA_ACCESS_SKILLS - covered
        assert not missing, f"data-access skills without fixtures: {sorted(missing)}"

    @pytest.mark.parametrize(
        "path",
        [p for p in FIXTURE_FILES if p.name.removesuffix("_traces.json") in DATA_ACCESS_SKILLS],
        ids=[n for n in FIXTURE_IDS if n in DATA_ACCESS_SKILLS],
    )
    def test_data_access_skills_assert_tenant_scope(self, path: Path) -> None:
        data = _load(path)
        for trace in data["traces"]:
            assert trace["assertions"].get("requires_tenant_scope") is True, (
                f"{path.name}:{trace['id']}: data-access trace lacks "
                "requires_tenant_scope: true — retrieval tenant isolation is a "
                "deterministic gate (V1-EVALS-001)"
            )


class TestGoldenTraceBaseline:
    def test_baseline_exists_and_matches(self) -> None:
        """Fixture drift must be deliberate: content is pinned to the baseline.

        To change golden traces, regenerate evals/baselines/golden-traces-baseline.json
        in the same PR so the diff shows both.
        """
        assert BASELINE_PATH.exists(), f"Missing baseline: {BASELINE_PATH}"
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        current = {
            p.name.removesuffix("_traces.json"): {
                "trace_count": len(_load(p)["traces"]),
                "sha256": _canonical_hash(_load(p)),
            }
            for p in FIXTURE_FILES
        }
        assert baseline.get("schema_version") == 1
        recorded = baseline.get("fixtures", {})
        assert set(recorded) == set(current), (
            f"fixture set drift: baseline={sorted(set(recorded) - set(current))} "
            f"current={sorted(set(current) - set(recorded))}"
        )
        for skill, meta in current.items():
            assert recorded[skill] == meta, (
                f"{skill}: fixture content drifted from baseline "
                f"(count {recorded[skill]['trace_count']} -> {meta['trace_count']}); "
                "regenerate the baseline in the same PR if this change is intended"
            )
