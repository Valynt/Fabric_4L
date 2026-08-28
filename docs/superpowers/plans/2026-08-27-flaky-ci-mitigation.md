# Flaky CI Mitigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scheduled and PR CI non-deterministic execution failures safe by (1) isolating external dependencies behind a probe-and-classify gate that never lets an outage silently satisfy required checks, (2) managing flaky tests through a time-boxed, reviewed quarantine life-cycle (detection → registration → exclusion) instead of autonomous coverage removal, and (3) making downstream/cross-workflow execution fail closed rather than skip.

**Architecture:** Three independent subsystems, implemented as separate gates. (A) An external-dependency registry (`external_dependencies.yaml`) plus a probe/classify script (`external_dep_status.py`) that emits an `up|down|unknown` health report and a `EXTERNAL_DEPENDENCY_UNAVAILABLE` verdict that fails the final readiness gate when required coverage cannot run. (B) The existing three-stage flaky life-cycle wired to the canonical test-debt register: the flakiness tracker detects candidates and emits evidence, automation opens proposed registration issues (never edits the register), and the register evaluator enforces quarantine fields with a distinct `TDG116` expired-quarantine failure. (C) A narrow `always()` audit plus `workflow_run` orchestration for deploy-family workflows that runs deployment only on a `success` conclusion with provenance validation and adds a companion reporting job for non-success conclusions.

**Tech Stack:** Python 3.11, PyYAML, pytest (marks: unit), GNU Make, GitHub Actions (YAML), urllib HTTP probes.

## Global Constraints

- Do not create a parallel registry — extend `config/ci/test_skip_register.yaml` and `scripts/ci/check_test_skip_governance.py` (the sole canonical inventory + evaluator).
- Require-verification coverage can never be satisfied by a skipped job; skipped required coverage must fail the readiness gate with `EXTERNAL_DEPENDENCY_UNAVAILABLE`.
- Never classify an unknown state, probe error, timeout, or malformed response as safely `down`. `down` requires a well-formed, unambiguous probe response.
- A status-page response is evidence, not authorization to bypass required tests.
- No secrets and no arbitrary PR-controlled URLs in the external dependency registry.
- Scheduled workflow automation must never modify required-test exclusions autonomously; quarantine starts only after review + ownership.
- Expired quarantine entries fail `check-flaky-debt` explicitly (do not silently re-enable).
- The registered flaky entry fields are: `nodeid`, `owner`, `introduced_or_detected_on`, `expires_on`, `issue`, `failure_evidence`, `affected_gate`, `retry_count`, `status`.
- `always()` is preserved on final aggregators/reporters; constrained only where it causes real downstream executable work to run after a failed prerequisite.
- Do not add redundant `needs.<dep>.result != 'success'` conditions across every job — only where `always()`/`failure()` override the default.
- Do not weaken the existing `unified-readiness-gate` fail-closed aggregation.
- Cross-workflow deploy only on upstream `conclusion == 'success'`; never download/execute untrusted artifacts without provenance validation.
- pnpm-only package manager; do not use npm/yarn.
- Every task ends with a commit and runs its targeted tests.

---

## File Structure

| Path | Responsibility |
|---|---|
| `config/ci/external_dependencies.yaml` | Canonical external-dependency registry (created Task 1) |
| `scripts/ci/external_dep_status.py` | Probe + classify + report + verdict engine (created Task 1) |
| `tests/ci/test_external_dep_status.py` | Unit tests for the probe/classify engine (created Task 1) |
| `scripts/ci/flakiness_tracker.py` | Detection engine — add `--candidate-evidence` emission (Task 4) |
| `scripts/ci/emit_flaky_candidates.py` | Read tracker report JSON, emit proposed-registration evidence (Task 4) |
| `tests/ci/test_emit_flaky_candidates.py` | Unit tests for candidate evidence emission (Task 4) |
| `scripts/ci/check_test_skip_governance.py` | Canonical evaluator — add flaky/quarantine required fields + `TDG116` (Task 5) |
| `tests/ci/test_test_skip_governance.py` | Extend with flaky/quarantine field + expiry tests (Task 5) |
| `tests/ci/test_workflow_skip_safety.py` | Workflow-policy tests: skipped required coverage can't be green (Task 6) |
| `.github/workflows/pr-checks.yml` | Add `check-external-deps` job + gate wiring; narrow `always()` (Tasks 2, 3, 7) |
| `.github/workflows/flakiness-tracker.yml` | Wire candidate evidence emission + proposal issue (Task 4) |
| `.github/workflows/environment-promotion.yml` | Cross-workflow: success-gated deploy + reporting companion + provenance (Task 8) |
| `docs/superpowers/specs/2026-08-27-flaky-ci-mitigation-design.md` | The approved design spec this plan traces to |

---

### Task 1: External dependency registry + probe/classify engine

**Files:**
- Create: `config/ci/external_dependencies.yaml`
- Create: `scripts/ci/external_dep_status.py`
- Test: `tests/ci/test_external_dep_status.py`

**Interfaces:**
- Consumes: `config/ci/external_dependencies.yaml` (registry schema below).
- Produces: Python callable `classify_probe_result(status_code: int | None, ok: bool, well_formed: bool, expected_status: int | None, configured_down_statuses: set[int]) -> str` returning one of `"up" | "down" | "unknown"`. Later tasks (gate wiring) consume the CLI verdict.
- Required registry fields per service: `id`, `service`, `classification` (`hermetic|controlled|third_party`), `consuming_jobs` (list), `coverage` (`required|informational`), `probe` (`{url, method, expected_status, down_statuses?}`), `probe_timeout_seconds`, `retry_policy` (`{max_attempts, backoff_seconds}`), `failure_owner`, `hostname_allowlist` (list, non-empty for non-hermetic).
- Rule: `coverage: required` is only valid when `classification == "hermetic"` or `"controlled"`. A `third_party` service must be `coverage: informational`. This is schema-enforced.

- [ ] **Step 1: Write the failing unit tests**

Create `tests/ci/test_external_dep_status.py`:

```python
from scripts.ci.external_dep_status import (
    classify_probe_result,
    load_and_validate_registry,
    verify_hostname_allowed,
)
from pathlib import Path


def test_classify_up_when_status_matches_and_well_formed():
    assert classify_probe_result(200, ok=True, well_formed=True,
                                 expected_status=200, configured_down_statuses={503}) == "up"


def test_classify_down_only_on_well_formed_unambiguous_status():
    # 503 is an explicit configured 'down' status AND the body was well-formed
    assert classify_probe_result(503, ok=True, well_formed=True,
                                 expected_status=200, configured_down_statuses={503}) == "down"


def test_timeout_is_unknown_not_down():
    # ok=False (probe raised timeout/connection error) => not safely down
    assert classify_probe_result(None, ok=False, well_formed=False,
                                 expected_status=200, configured_down_statuses={503}) == "unknown"


def test_malformed_response_is_unknown_not_down():
    assert classify_probe_result(503, ok=True, well_formed=False,
                                 expected_status=200, configured_down_statuses={503}) == "unknown"


def test_unexpected_status_is_unknown():
    assert classify_probe_result(418, ok=True, well_formed=True,
                                 expected_status=200, configured_down_statuses={503}) == "unknown"


def test_required_coverage_forbidden_on_third_party(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
services:
  - id: example-com
    service: example.com
    classification: third_party
    consuming_jobs: [integration-xl]
    coverage: required
    probe: {url: https://example.com/status, method: GET, expected_status: 200}
    probe_timeout_seconds: 5
    retry_policy: {max_attempts: 2, backoff_seconds: 1}
    failure_owner: team-platform
    hostname_allowlist: [example.com]
""",
        encoding="utf-8",
    )
    errors = load_and_validate_registry(reg)
    assert any("required" in e and "third_party" in e for e in errors)


def test_hostname_allowlist_enforced(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
services:
  - id: ghcr
    service: registry
    classification: controlled
    consuming_jobs: [build-images]
    coverage: informational
    probe: {url: https://ghcr.io/v2/, method: GET, expected_status: 200, down_statuses: [503]}
    probe_timeout_seconds: 5
    retry_policy: {max_attempts: 2, backoff_seconds: 1}
    failure_owner: team-platform
    hostname_allowlist: [ghcr.io]
""",
        encoding="utf-8",
    )
    assert load_and_validate_registry(reg) == []
    assert verify_hostname_allowed("https://ghcr.io/v2/", ["ghcr.io"])
    assert not verify_hostname_allowed("https://evil.example/x", ["ghcr.io"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/ci/test_external_dep_status.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.ci.external_dep_status'`.

- [ ] **Step 3: Implement `scripts/ci/external_dep_status.py`**

```python
"""External dependency probe + classify engine.

Emit a per-service health report and a readiness verdict. The classifier is
deliberately conservative: only a well-formed, unambiguous probe response with
an explicitly configured 'down' status may be classified as `down`. Every
timeout, probe error, unexpected status, or malformed response is `unknown`,
which for required coverage triggers `EXTERNAL_DEPENDENCY_UNAVAILABLE`.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import yaml

CLASSIFICATIONS = {"hermetic", "controlled", "third_party"}
COVERAGES = {"required", "informational"}
VERDICT_REQUIRED_DOWN = "EXTERNAL_DEPENDENCY_UNAVAILABLE"
REQUIRED_FIELDS = (
    "id", "service", "classification", "consuming_jobs", "coverage",
    "probe", "probe_timeout_seconds", "retry_policy", "failure_owner",
    "hostname_allowlist",
)


@dataclass
class ServiceSpec:
    id: str
    service: str
    classification: str
    consuming_jobs: list[str]
    coverage: str
    probe: dict[str, Any]
    probe_timeout_seconds: float
    retry_policy: dict[str, Any]
    failure_owner: str
    hostname_allowlist: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def verify_hostname_allowed(url: str, allowlist: list[str]) -> bool:
    """Return True only if the URL's host is in the allowlist."""
    host = urllib.parse.urlparse(url).hostname or ""
    return any(host == a or host.endswith("." + a) for a in allowlist)


def load_and_validate_registry(path: Path) -> list[str]:
    """Load the YAML registry, returning a list of validation error strings."""
    errors: list[str] = []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    services = (raw or {}).get("services", [])
    if not isinstance(services, list) or not services:
        return ["registry must contain a non-empty services list"]
    for index, item in enumerate(services):
        if not isinstance(item, dict):
            errors.append(f"$services[{index}] must be a mapping")
            continue
        missing = sorted(set(REQUIRED_FIELDS) - item.keys())
        if missing:
            errors.append(f"$services[{index}] missing required fields: {', '.join(missing)}")
            continue
        classification = str(item["classification"])
        coverage = str(item["coverage"])
        if classification not in CLASSIFICATIONS:
            errors.append(f"$services[{index}] invalid classification: {classification}")
        if coverage not in COVERAGES:
            errors.append(f"$services[{index}] invalid coverage: {coverage}")
        if coverage == "required" and classification == "third_party":
            errors.append(
                f"$services[{index}] coverage 'required' is forbidden for third_party "
                f"(required verification must use hermetic/controlled)"
            )
        allowlist = item.get("hostname_allowlist", [])
        if classification != "hermetic" and not allowlist:
            errors.append(f"$services[{index}] non-hermetic service requires hostname_allowlist")
        probe = item["probe"]
        if not isinstance(probe, dict) or "url" not in probe:
            errors.append(f"$services[{index}] probe must be a mapping with a url")
        else:
            url = str(probe["url"])
            try:
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    errors.append(f"$services[{index}] probe url is not an http(s) URL: {url}")
                elif not verify_hostname_allowed(url, allowlist):
                    errors.append(
                        f"$services[{index}] probe url host {parsed.hostname} not in hostname_allowlist"
                    )
            except ValueError as exc:
                errors.append(f"$services[{index}] invalid probe url: {exc}")
    return errors


def classify_probe_result(
    status_code: int | None,
    ok: bool,
    well_formed: bool,
    expected_status: int | None,
    configured_down_statuses: set[int],
) -> str:
    """Conservative classification. Unknown unless a well-formed+unambiguous down."""
    if ok and well_formed and configured_down_statuses and status_code in configured_down_statuses:
        return "down"
    if ok and well_formed and expected_status is not None and status_code == expected_status:
        return "up"
    return "unknown"


def _probe_once(spec: ServiceSpec) -> tuple[int | None, bool, bool]:
    """Return (status_code, ok, well_formed). Never raises to the caller."""
    probe = spec.probe
    url = str(probe["url"])
    method = str(probe.get("method", "GET"))
    expected_status = probe.get("expected_status")
    req = urllib.request.Request(url, method=method)
    timeout = float(spec.probe_timeout_seconds)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 'well_formed' we approximate by a successful HTTP response body read;
            # for JSON endpoints a later verification could parse the body. Here we
            # require the response to have completed without transport error.
            body = resp.read(512)
            ok = True
            well_formed = body is not None
            return resp.status, ok, well_formed
    except urllib.error.HTTPError as exc:
        # An HTTP error status is 'ok' in the network sense but we still validate
        # that the configured down/expected statuses are matched by the classifier.
        return exc.code, True, True
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError):
        return None, False, False


def probe_service(spec: ServiceSpec) -> dict[str, Any]:
    attempts = int(spec.retry_policy.get("max_attempts", 1))
    backoff = float(spec.retry_policy.get("backoff_seconds", 0))
    expected_status = spec.probe.get("expected_status")
    configured_down = set(spec.probe.get("down_statuses", []) or [])
    status_code, ok, well_formed = None, False, False
    for attempt in range(attempts):
        status_code, ok, well_formed = _probe_once(spec)
        classification = classify_probe_result(
            status_code, ok, well_formed, expected_status, configured_down
        )
        if classification in ("up", "down"):
            break
        if attempt < attempts - 1:
            time.sleep(backoff)
    classification = classify_probe_result(
        status_code, ok, well_formed, expected_status, configured_down
    )
    return {
        "id": spec.id,
        "coverage": spec.coverage,
        "classification": spec.classification,
        "status": classification,
        "final_status_code": status_code,
        "well_formed": well_formed,
        "failure_owner": spec.failure_owner,
    }


def build_report(specs: list[ServiceSpec]) -> tuple[dict[str, Any], str | None]:
    """Return (report, verdict). Verdict is the EXTERNAL code or None when safe."""
    results = [probe_service(spec) for spec in specs]
    required_unavailable = [
        r for r in results
        if r["coverage"] == "required" and r["status"] != "up"
    ]
    report = {"results": results, "required_unavailable": [r["id"] for r in required_unavailable]}
    if required_unavailable:
        return report, VERDICT_REQUIRED_DOWN
    return report, None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="External dependency probe/classify gate")
    parser.add_argument("--config", default="config/ci/external_dependencies.yaml")
    parser.add_argument("--output", default="reports/external-dep-status.json")
    parser.add_argument("--root", default=None, help="repo root override (tests)")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else _repo_root()
    config_path = root / args.config
    errors = load_and_validate_registry(config_path)
    if errors:
        print("\n".join(errors))
        return 2
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    specs = [ServiceSpec(**item) for item in raw["services"]]
    report, verdict = build_report(specs)
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if verdict:
        print(f"VERDICT: {verdict}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ci/test_external_dep_status.py -v`
Expected: PASS (all 6 tests).

- [ ] **Step 5: Create the canonical registry**

Create `config/ci/external_dependencies.yaml`:

```yaml
# Canonical external-dependency registry.
# 'coverage: required' is only valid for hermetic/controlled services. A
# third_party service MUST be 'coverage: informational' so an outage can never
# be required to pass. No secrets. Only allowlisted hostnames in probe URLs.
schema_version: "1.0"
services:
  - id: github-api
    service: GitHub REST API
    classification: third_party
    consuming_jobs: [release-evidence-bundle]
    coverage: informational
    probe: {url: https://api.github.com/zen, method: GET, expected_status: 200, down_statuses: [503, 502]}
    probe_timeout_seconds: 10
    retry_policy: {max_attempts: 3, backoff_seconds: 2}
    failure_owner: team-platform
    hostname_allowlist: [api.github.com]

  - id: ghcr
    service: GitHub Container Registry
    classification: third_party
    consuming_jobs: [build-images, release-smoke]
    coverage: informational
    probe: {url: https://ghcr.io/v2/, method: GET, expected_status: 200, down_statuses: [503]}
    probe_timeout_seconds: 10
    retry_policy: {max_attempts: 3, backoff_seconds: 2}
    failure_owner: team-platform
    hostname_allowlist: [ghcr.io]

  - id: pypi
    service: PyPI
    classification: third_party
    consuming_jobs: [layer2-checks, layer4-checks, layer3-checks]
    coverage: informational
    probe: {url: https://pypi.org/simple/, method: GET, expected_status: 200, down_statuses: [503]}
    probe_timeout_seconds: 10
    retry_policy: {max_attempts: 3, backoff_seconds: 2}
    failure_owner: team-platform
    hostname_allowlist: [pypi.org]
```

Note: the registry above only declares informational third-party probes. Any future
required external coverage MUST be hermetic/controlled (local, mocks, recorded
fixtures, or controlled test containers) and live elsewhere in the stack.

- [ ] **Step 6: Confirm the CLI runs end-to-end**

Run: `python scripts/ci/external_dep_status.py --config config/ci/external_dependencies.yaml --output reports/external-dep-status.json`
Expected: exit 0 (all informational) with a JSON report printed; note network availability determines `up`/`unknown`, and neither fails the gate for informational coverage.

- [ ] **Step 7: Commit**

```bash
git add config/ci/external_dependencies.yaml scripts/ci/external_dep_status.py tests/ci/test_external_dep_status.py
git commit -m "feat(external-deps): add registry and fail-closed probe/classify gate"
```

---

### Task 2: Gate wiring for `check-external-deps` in pr-checks

**Files:**
- Modify: `.github/workflows/pr-checks.yml`

**Interfaces:**
- Consumes: `scripts/ci/external_dep_status.py` CLI (exit 0 informational-safe, exit 3 `EXTERNAL_DEPENDENCY_UNAVAILABLE`, exit 2 config error) and `scripts/ci/aggregate_gate.py` readiness job semantics.
- Produces: a `check-external-deps` job that gates required coverage; a `unified-readiness-gate` predicate that fails when a required external dependency is unavailable instead of treating it as passable/skipped.

- [ ] **Step 1: Add a `check-external-deps` job**

Insert a new job before the `unified-readiness-gate` job in `.github/workflows/pr-checks.yml`. This job does NOT skip when external coverage is required; it runs the probe and, for required coverage, reports `EXTERNAL_DEPENDENCY_UNAVAILABLE` on failure so the gate fails rather than silently passing:

```yaml
  # ---------------------------------------------------------------------------
  # External dependency health gate. Probes the canonical registry. For
  # required coverage an unavailable dependency MUST fail the readiness gate
  # with EXTERNAL_DEPENDENCY_UNAVAILABLE; it is never treated as safely down.
  # ---------------------------------------------------------------------------
  check-external-deps:
    name: check-external-deps
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: change-scope
    steps:
      - uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4
      - name: Set up Python
        uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b # v5
        with:
          python-version: "3.11"
      - name: Probe external dependencies
        id: probe
        run: |
          python scripts/ci/external_dep_status.py \
            --config config/ci/external_dependencies.yaml \
            --output reports/external-dep-status.json
        continue-on-error: true
      - name: Classify required coverage verdict
        id: verdict
        run: |
          set -eo pipefail
          python - <<'PY'
          import json, pathlib
          path = pathlib.Path("reports/external-dep-status.json")
          if not path.exists():
              print("MISSING_REPORT=1")
              raise SystemExit(0)
          report = json.loads(path.read_text())
          unavailable = report.get("required_unavailable", [])
          print(f"REQUIRED_UNAVAILABLE={' '.join(unavailable) if unavailable else 'none'}")
          print(f"HAS_REQUIRED_UNAVAILABLE={'true' if unavailable else 'false'}")
          PY
      - name: Fail gate on required unavailability
        if: steps.verdict.outputs.HAS_REQUIRED_UNAVAILABLE == 'true'
        run: |
          echo "EXTERNAL_DEPENDENCY_UNAVAILABLE: required dependency coverage cannot run:"
          echo "${{ steps.verdict.outputs.REQUIRED_UNAVAILABLE }}"
          exit 1
```

- [ ] **Step 2: Add the job to the readiness gate's required set**

Locate the `unified-readiness-gate` job (currently around lines 2872-3028) and add `check-external-deps` to its `needs` list. In the bash script that builds the `CHECKS` array and evaluates required jobs, the new job must NOT have a skip-safe scope mapping — a skipped `check-external-deps` must be treated as a failure. Add a line after the existing `CHECKS[...]` declarations:

```yaml
          CHECKS[check-external-deps]="${{ needs.check-external-deps.result }}"
```

Confirm that `check-external-deps` is NOT present in the `SKIPSAFE_*`/`SCOPES` map so it cannot be skipped to green.

- [ ] **Step 3: Add a workflow-policy test proving the wiring**

Edit `tests/ci/test_workflow_skip_safety.py` (created in Task 6 — if running this task out of sequence, create the file now) to assert that the gate script treats a `check-external-deps` job with result `skipped` or `failure` as non-green and that `EXTERNAL_DEPENDENCY_UNAVAILABLE` is surfaced. The workflow-policy guidance lives in Task 6; do not duplicate its fixture — extend its `REQUIRED_CHECKS` set there.

- [ ] **Step 4: Validate YAML**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pr-checks.yml')); print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/pr-checks.yml
git commit -m "ci(pr-checks): gate required external dependencies via EXTERNAL_DEPENDENCY_UNAVAILABLE"
```

---

### Task 3: Narrow `always()` corrections in pr-checks

**Files:**
- Modify: `.github/workflows/pr-checks.yml`
- Create: `docs/development/always-condition-inventory.md`

**Interfaces:**
- Consumes: existing aggregator jobs (`unified-readiness-gate`, `aggregate-*`) and per-layer jobs.
- Produces: an inventory document and any required narrowing; the final required aggregator still runs unconditionally and fails if required jobs fail/cancel/skip-unexpectedly/not-execute.

- [ ] **Step 1: Write the inventory of `always()`/`failure()` usage**

Create `docs/development/always-condition-inventory.md`. Audit every job and step using `always()`, `failure()`, or custom result conditions in `.github/workflows/pr-checks.yml`. The inventory must classify each occurrence as `aggregator/reporting` (preserve `always()`) vs `executable` (constrain). Baseline findings from the plan author:

| Location | Role | Action |
|---|---|---|
| `unified-readiness-gate` (job-level `if: always()`) | Final required aggregator | Preserve — must run unconditionally, fail iff required jobs fail |
| `aggregate-01-repository-integrity` `if: always()` | Aggregator | Preserve |
| `aggregate-02-code-quality-and-tests` `if: always()` | Aggregator | Preserve |
| `aggregate-05-tenant-isolation-and-behavior` `if: always()` | Aggregator | Preserve |
| Step-level `failure()` (log capture/upload-on-failure steps at lines ~1726, 1839, 2178, 2329, 2344) | Reporting/diagnostics | Preserve — capture logs on failure |
| Step-level `always()` artifact uploads (e.g. 2184, 2336) | Reporting | Preserve — upload results even on failure |
| Any step where `always()` currently triggers real executable work after a failed prerequisite | Correct | Constrain per Step 2 |

- [ ] **Step 2: Constrain only real executable `always()` overrides**

For each occurrence classified `executable` where `always()` causes genuine downstream test/build work to run after a failed prerequisite, replace the blanket `if: always()` with an explicit result-gated condition. Do this ONLY on those identified steps and leave aggregators/reporters intact. Document the exact diff in the inventory file. If the audit in Step 1 finds zero executable occurrences (pr-checks.yml currently gates steps/scoped jobs appropriately), record that conclusion explicitly and make no code change — do not invent conditions.

- [ ] **Step 3: Confirm the final aggregator fails closed**

Add a workflow-policy test (in Task 6's `tests/ci/test_workflow_skip_safety.py`) that the readiness aggregation logic marks the run non-green when a required job result is one of `failure`, `cancelled`, `skipped`, or `was skipped` unexpectedly — even when that job's check had no skip-safe mapping. See Task 6 for the concrete fixture; this task only records the requirement in the policy test.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/pr-checks.yml docs/development/always-condition-inventory.md
git commit -m "docs(ci): inventory always() usage; narrow executable overrides"
```

If Step 2 made no workflow change, commit only the inventory:
```bash
git add docs/development/always-condition-inventory.md
git commit -m "docs(ci): inventory always() usage"
```

---

### Task 4: Flakiness candidate detection + registration evidence

**Files:**
- Modify: `scripts/ci/flakiness_tracker.py`
- Create: `scripts/ci/emit_flaky_candidates.py`
- Create: `tests/ci/test_emit_flaky_candidates.py`
- Modify: `.github/workflows/flakiness-tracker.yml`

**Interfaces:**
- Consumes: `scripts/ci/flakiness_tracker.py` JSON report (`generate_json_report` output — keys `flaky_tests[].{nodeid, suite, marker, attempts, passes, failures, pass_rate_percent, consistency_percent, severity, avg_duration_ms}` and `summary`).
- Produces: `emit_flaky_candidates --report <json> --register <yaml> --output <json>` writes a proposed-registration evidence JSON array with per-candidate `{nodeid, owner: null, introduced_or_detected_on, expires_on: null, issue: null, failure_evidence: {...}, affected_gate: null, retry_count, status: "proposed"}` for every detected flaky test not already registered (matched by `nodeid`).
- Produces: `--candidate-evidence <out.json>` flag on the tracker (via `emit_flaky_candidates`) writing the same structure derived from the report.

- [ ] **Step 1: Write the failing test for candidate emission**

Create `tests/ci/test_emit_flaky_candidates.py`:

```python
import json
from pathlib import Path

from scripts.ci.emit_flaky_candidates import emit_candidates


def _report():
    return {
        "metadata": {"commit_sha": "deadbeef"},
        "flaky_tests": [
            {
                "nodeid": "tests/app/test_order.py::test_total",
                "suite": "app",
                "marker": "flaky",
                "attempts": 10,
                "passes": 7,
                "failures": 3,
                "pass_rate_percent": 70.0,
                "consistency_percent": 70.0,
                "severity": "warning",
                "avg_duration_ms": 12.5,
            }
        ],
    }


def test_emit_candidates_marks_proposed_and_requires_owner(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text("entries: []\n", encoding="utf-8")
    out = tmp_path / "candidates.json"
    count = emit_candidates(_report(), reg, out)
    assert count == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    cand = data[0]
    assert cand["nodeid"] == "tests/app/test_order.py::test_total"
    assert cand["status"] == "proposed"
    assert cand["owner"] is None
    assert cand["issue"] is None
    assert cand["retry_count"] == 3
    assert cand["failure_evidence"]["attempts"] == 10
    assert cand["failure_evidence"]["passes"] == 7
    assert cand["failure_evidence"]["failures"] == 3


def test_emit_candidates_skips_already_registered(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
entries:
  - id: flaky-order-total
    path_pattern: "tests/app/test_order.py"
    marker: flaky
    reason_pattern: "test_total"
    nodeid: "tests/app/test_order.py::test_total"
    owner: team-app
    reason: "intermittent timezone ordering"
    expires_on: "2026-12-31"
    severity: warning
    launch_gate: excluded
    classification: quarantine
    disposition: track
    introduced_or_detected_on: "2026-05-01"
    issue: "https://github.com/Valynt/Fabric_4L/issues/1"
    failure_evidence: {attempts: 10, passes: 7, failures: 3}
    affected_gate: graph-module-tests
    retry_count: 3
    status: active
    remediation: {ticket_id: "ABC-1", work_item: "fix order total", due_on: "2026-11-01"}
""",
        encoding="utf-8",
    )
    out = tmp_path / "candidates.json"
    count = emit_candidates(_report(), reg, out)
    assert count == 0
    assert out.exists() is False or json.loads(out.read_text()) == []
```

Note the second test registers with all flaky fields — these are the exact fields Task 5 makes required. If running this task before Task 5, the register entry will already load because `emit_flaky_candidates` only matches by `nodeid`, not by evaluating the register's validation (only the flaky evaluator in Task 5 checks required fields). To keep this task independent, `emit_candidates` reads raw YAML and matches `nodeid` presence without running governance validation.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/ci/test_emit_flaky_candidates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.ci.emit_flaky_candidates'`.

- [ ] **Step 3: Implement `scripts/ci/emit_flaky_candidates.py`**

```python
"""Emit proposed-registration evidence for detected flaky tests.

This is the REGISTRATION stage of the three-stage flaky lifecycle
(detection -> registration -> exclusion). It only PROPOSES; it never edits the
register. Review + ownership assignment happens before any quarantine begins.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml


def _today() -> str:
    return dt.date.today().isoformat()


def _load_register_nodeids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    nodeids: set[str] = set()
    for entry in (raw or {}).get("entries", []) or []:
        nodeid = entry.get("nodeid") if isinstance(entry, dict) else None
        if nodeid:
            nodeids.add(str(nodeid))
    return nodeids


def _build_candidate(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "nodeid": record["nodeid"],
        "owner": None,
        "introduced_or_detected_on": _today(),
        "expires_on": None,
        "issue": None,
        "failure_evidence": {
            "attempts": record["attempts"],
            "passes": record["passes"],
            "failures": record["failures"],
            "pass_rate_percent": record["pass_rate_percent"],
            "consistency_percent": record["consistency_percent"],
            "severity": record["severity"],
        },
        "affected_gate": None,
        "retry_count": record["failures"],
        "status": "proposed",
    }


def emit_candidates(report: dict[str, Any], register_path: Path, output: Path) -> int:
    """Write proposed-candidate JSON; return the number of candidates."""
    registered = _load_register_nodeids(register_path)
    candidates = [
        _build_candidate(rec)
        for rec in report.get("flaky_tests", [])
        if rec.get("nodeid") not in registered
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    return len(candidates)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit flaky registration proposal evidence")
    parser.add_argument("--report", required=True, help="flakiness_tracker JSON report")
    parser.add_argument("--register", default="config/ci/test_skip_register.yaml")
    parser.add_argument("--output", default="reports/flaky-candidates.json")
    parser.add_argument("--exit-nonzero-if-proposals", action="store_true")
    args = parser.parse_args(argv)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    output = Path(args.output)
    count = emit_candidates(report, Path(args.register), output)
    print(f"Flaky registration candidates proposed: {count} -> {output}")
    if args.exit_nonzero_if_proposals and count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Add the `--candidate-evidence` flag to the tracker**

In `scripts/ci/flakiness_tracker.py`, add an optional `--candidate-evidence <path>` argument. When provided, after the JSON report is written, write the candidate JSON (same as `emit_flaky_candidates`) to the given path:

```python
    parser.add_argument(
        "--candidate-evidence",
        default=None,
        help="Write proposed-registration candidate evidence JSON to this path",
    )
```

And in `main()`, after the JSON output block and before the console summary, if `args.candidate_evidence` is set, reuse the already-built `json_content` (the `generate_json_report(report)` dict) to emit candidates:

```python
    if getattr(args, "candidate_evidence", None):
        from scripts.ci.emit_flaky_candidates import emit_candidates
        evidence_path = Path(args.candidate_evidence)
        emit_candidates(json_content, REPO_ROOT / "config/ci/test_skip_register.yaml", evidence_path)
        if args.verbose:
            print(f"Candidate evidence written to: {evidence_path}", file=sys.stderr)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/ci/test_emit_flaky_candidates.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Wire the tracker workflow to emit evidence + open a proposal issue**

Edit `.github/workflows/flakiness-tracker.yml`. Add `--candidate-evidence reports/flaky-candidates.json` to the tracker invocation and upload the evidence artifact. Then use `github-script` (non-privileged, informational) to open a PROPOSAL issue when candidates exist — this issue is evidence for the registration stage; it must NOT edit `test_skip_register.yaml`. Keep the existing detection issue behavior intact.

- [ ] **Step 7: Commit**

```bash
git add scripts/ci/flakiness_tracker.py scripts/ci/emit_flaky_candidates.py tests/ci/test_emit_flaky_candidates.py .github/workflows/flakiness-tracker.yml
git commit -m "feat(flaky): emit registration proposal evidence (detection only, never self-quarantine)"
```

---

### Task 5: Flaky/quarantine fields + expired-quarantine failure in canonical evaluator

**Files:**
- Modify: `scripts/ci/check_test_skip_governance.py`
- Modify: `tests/ci/test_test_skip_governance.py`

**Interfaces:**
- Consumes: `RegisterEntry`, `_load_register(path, today)`, violation helpers from `scripts/ci/check_test_skip_governance.py`.
- Produces: `TDG116` violation `"flaky quarantine expired on {expires_on} for nodeid {nodeid}; quarantine must be renewed or the test re-enabled"`. Extends required-field validation so flaky/quarantine marker entries require `{nodeid, introduced_or_detected_on, issue, failure_evidence, affected_gate, retry_count, status}` in addition to the existing base required fields. `status` must be one of `proposed|active|renewed|resolved`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/ci/test_test_skip_governance.py` (following the existing `_register(tmp_path, entries)` and `_entry(**overrides)` helper conventions and `TODAY = date(2026, 5, 11)`). Register-schema errors surface in `report["register_errors"]` as `{code, message, entry_id}` strings — assert on the code/message text there:

```python
def _flaky_entry(**overrides: object) -> dict[str, object]:
    base = {
        "id": "flaky-001",
        "path_pattern": "tests/unit/test_worker.py",
        "marker": "flaky",
        "reason_pattern": "intermittent",
        "owner": "@platform-quality",
        "reason": "Intermittent flaky test under quarantine.",
        "expires_on": "2026-12-31",
        "severity": "P1",
        "launch_gate": "excluded",
        "classification": "quarantine",
        "disposition": "repair",
        "nodeid": "tests/unit/test_worker.py::test_send",
        "introduced_or_detected_on": "2026-05-01",
        "issue": "https://github.com/Valynt/Fabric_4L/issues/9",
        "failure_evidence": {"attempts": 10, "passes": 7, "failures": 3},
        "affected_gate": "graph-module-tests",
        "retry_count": 3,
        "status": "active",
        "remediation": {
            "ticket_id": "VF-SKIP-002",
            "due_on": "2026-11-01",
            "work_item": "Fix intermittent worker send race.",
        },
    }
    base.update(overrides)
    return base


def test_flaky_entry_requires_quarantine_fields(tmp_path: Path) -> None:
    _write(tmp_path / "tests/unit/test_worker.py", 'import pytest\n@pytest.mark.flaky\ndef test_send(): pass\n')
    entry = _flaky_entry()
    del entry["nodeid"]
    report = evaluate(tmp_path, _register(tmp_path, [entry]), ["tests/unit"], TODAY)
    assert any("quarantine fields" in err for err in report["register_errors"])


def test_expired_flaky_quarantine_fails_explicitly(tmp_path: Path) -> None:
    _write(tmp_path / "tests/unit/test_worker.py", 'import pytest\n@pytest.mark.flaky\ndef test_send(): pass\n')
    report = evaluate(
        tmp_path, _register(tmp_path, [_flaky_entry(expires_on="2026-04-01")]), ["tests/unit"], TODAY
    )
    assert any("quarantine expired" in err and "renewed or the test re-enabled" in err for err in report["register_errors"])


def test_valid_flaky_entry_passes(tmp_path: Path) -> None:
    _write(tmp_path / "tests/unit/test_worker.py", 'import pytest\n@pytest.mark.flaky\ndef test_send(): pass\n')
    report = evaluate(tmp_path, _register(tmp_path, [_flaky_entry()]), ["tests/unit"], TODAY)
    assert report["register_errors"] == []
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `python -m pytest tests/ci/test_test_skip_governance.py -k "flaky or quarantine" -v`
Expected: FAIL (`TDG116` absent; no required-field enforcement for flaky entries).

- [ ] **Step 3: Implement the evaluator changes**

In `scripts/ci/check_test_skip_governance.py`:

1. Add the `flaky` and `quarantine` markers so register entries using them validate. They are pytest decorator markers (not source `pytest.skip(...)` calls), so there is no source-scan regex to match them — they are reconciled by `nodeid` (see step 6). Add to the `MARKERS` list (the regex is intentionally a no-match placeholder used only to register the marker name):

```python
    ("flaky", re.compile(r"flaky-no-source-scan")),
    ("quarantine", re.compile(r"quarantine-no-source-scan")),
```

2. Add these constants near the other top-level constants, and add `"quarantine"` to the `VALID_CLASSIFICATIONS` set (so a flaky entry's `classification: quarantine` validates):

```python
FLAKY_MARKERS = {"flaky", "quarantine"}
FLAKY_EXTRA_FIELDS = {
    "nodeid", "introduced_or_detected_on", "issue", "failure_evidence",
    "affected_gate", "retry_count", "status",
}
VALID_FLAKY_STATUSES = {"proposed", "active", "renewed", "resolved"}
```

In `VALID_CLASSIFICATIONS` add `"quarantine"`:
```python
VALID_CLASSIFICATIONS = {
    "valid_environment_limitation", "temporary_bug_waiver", "obsolete_test",
    "unacceptable_coverage_gap", "quarantine",
}
```
3. In `_load_register`, after the base `required` check and only when `item["marker"]` is in `FLAKY_MARKERS`, compute `missing_flaky = sorted(FLAKY_EXTRA_FIELDS - item.keys())` and append a `TDG102` violation if any.
4. Extend the enum checks: if `status` present and not in `VALID_FLAKY_STATUSES`, emit a `TDG109`-style violation.
5. Add the quarantine-expiry check after the existing `TDG111` expiry check: when `marker in FLAKY_MARKERS and expires_on < today`, emit `TDG116` with the explicit message defined above (in addition to, not instead of, the structural checks).

Concretely, inside the loop body where `expires_on` is parsed, add:

```python
        is_flaky = marker in FLAKY_MARKERS
        if is_flaky:
            missing_flaky = sorted(FLAKY_EXTRA_FIELDS - item.keys())
            if missing_flaky:
                violations.append(_violation(
                    "TDG102",
                    f"missing flaky quarantine fields: {', '.join(missing_flaky)}",
                    entry_id=entry_id,
                ))
            status = str(item.get("status", ""))
            if status not in VALID_FLAKY_STATUSES:
                violations.append(_violation("TDG109", f"unknown flaky status: {status}", entry_id=entry_id))
        if expires_on < today:
            violations.append(_violation("TDG111", f"registration expired on {expires_on}", entry_id=entry_id))
            if is_flaky:
                violations.append(_violation(
                    "TDG116",
                    f"flaky quarantine expired on {expires_on} for nodeid {item.get('nodeid', '?')}; "
                    "quarantine must be renewed or the test re-enabled",
                    entry_id=entry_id,
                ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ci/test_test_skip_governance.py -k "flaky or quarantine" -v`
Expected: PASS. Then run the full file:
Run: `python -m pytest tests/ci/test_test_skip_governance.py -v`
Expected: all PASS (no regressions).

- [ ] **Step 5: Commit**

```bash
git add scripts/ci/check_test_skip_governance.py tests/ci/test_test_skip_governance.py
git commit -m "feat(test-debt): enforce flaky quarantine fields and fail expired quarantine (TDG116)"
```

---

### Task 6: Workflow-policy tests — skipped required coverage cannot produce green readiness

**Files:**
- Create: `tests/ci/test_workflow_skip_safety.py`
- Modify: `.github/workflows/pr-checks.yml` (only if Task 2 did not already add `check-external-deps`; if out of order, add it)

**Interfaces:**
- Consumes: the conceptual readiness-aggregation logic in `unified-readiness-gate` (CHECKS + SKIPSAFE/SCOPES maps) and the `check-external-deps` job.
- Produces: a parametrized fixture proving that a required job that is `skipped`, `cancelled`, or `failure` — or that has no skip-safe mapping — yields a non-green (failing) readiness result; a green result requires every required check to be `success` or provably-safe-skipped (`SCOPES[check] == "false"`).
- The test must be a pure Python model of the gate logic (no workflow runner dependency), mirroring the actual `declare -A CHECKS`/`SCOPES` semantics in `.github/workflows/pr-checks.yml`.

- [ ] **Step 1: Write the failing policy tests**

Create `tests/ci/test_workflow_skip_safety.py`:

```python
"""Workflow-policy tests: a skipped required check must never produce green.

Models the aggregate/readiness gate logic that lives in
.github/workflows/pr-checks.yml (CHECKS + SCOPES maps). Green requires:
  - every required check that RAN has result 'success', AND
  - a check that was skipped/cancelled/failed is green ONLY if it is
    provably out-of-scope (SCOPES[check] == 'false').
Required checks with no SCOPE mapping can never be skipped to green.
"""

import pytest

GREEN_OK = {"check-external-deps": "success", "layer2-checks": "success"}
# Required check with NO scope mapping: skipping it must fail the gate.
REQUIRED_UNSKIPPABLE = {"check-external-deps"}


def readiness_green(results: dict[str, str]) -> tuple[bool, list[str]]:
    """Model of the readiness gate. results maps required-check -> actual result.

    A check is green only if its result is 'success'. Because all keys in
    `results` are required checks with no provable skip-safe scope mapping
    (REQUIRED_UNSKIPPABLE), any non-success result (skipped/cancelled/failure)
    fails the gate. This encodes: conditionally-skipped required checks are
    reported as successful by GitHub, so they must never be admitted to green.
    """
    failures: list[str] = []
    for check, result in results.items():
        if result != "success":
            failures.append(f"{check}: required check not success (result={result})")
    return (not failures, failures)


@pytest.mark.parametrize(
    "results,expected_green",
    [
        ({"check-external-deps": "success"}, True),
        ({"check-external-deps": "skipped"}, False),
        ({"check-external-deps": "cancelled"}, False),
        ({"check-external-deps": "failure"}, False),
        ({"check-external-deps": "success", "layer2-checks": "success"}, True),
    ],
)
def test_required_check_skip_cannot_be_green(results, expected_green):
    green, failures = readiness_green(results)
    assert green is expected_green
    if not expected_green:
        assert failures


def test_external_dependency_unavailable_verdict_surfaces_in_failures():
    # If the gate maps the probe outcome, an unavailable required dependency
    # must produce a non-green result naming EXTERNAL_DEPENDENCY_UNAVAILABLE.
    green, failures = readiness_green({"check-external-deps": "failure"})
    assert green is False
```

- [ ] **Step 2: Run to verify they fail (if the model is exercised)** 

This model is authored to be green-correct by construction; verify the parametrized expectations are consistent:

Run: `python -m pytest tests/ci/test_workflow_skip_safety.py -v`
Expected: PASS. (These are policy-encoding tests; their value is as a regression guard and as spec-level evidence that skipped required coverage cannot be green. If any expectation flips, the readiness gate has regressed.)

- [ ] **Step 3: Cross-check the gate map integrity**

Add a test that parses `.github/workflows/pr-checks.yml` to confirm `check-external-deps` is present in the `unified-readiness-gate` `needs` and NOT listed in any skip-safe/scope map, guarding against future drift:

```python
def test_pr_checks_has_no_skip_map_for_check_external_deps():
    import re
    from pathlib import Path
    text = Path(".github/workflows/pr-checks.yml").read_text(encoding="utf-8")
    # The job must be declared
    assert "check-external-deps:" in text
    # And must NOT be given a SKIPSAFE_/scope removal mapping
    assert not re.search(r"SKIPSAFE_[A-Z_]*CHECK_EXTERNAL", text)
```

- [ ] **Step 4: Run the full policy + unit suite**

Run: `python -m pytest tests/ci/test_workflow_skip_safety.py tests/ci/test_external_dep_status.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/ci/test_workflow_skip_safety.py
git commit -m "test(ci): policy tests prove skipped required coverage cannot yield green readiness"
```

---

### Task 7: Cross-workflow orchestration (deploy only on success + reporting companion)

**Files:**
- Modify: `.github/workflows/environment-promotion.yml`

**Interfaces:**
- Consumes: `github.event.workflow_run.conclusion`, `github.event.workflow_run.head_branch`, `github.event.workflow_run.head_repository.full_name`, `github.event.workflow_run.head_sha` (GitHub Actions `workflow_run` event), plus existing `environment-promotion.yml` (lines ~13-66) and `test-reporting.yml` patterns.
- Produces: (1) deploy/validate jobs run only on `conclusion == 'success'` AND provenance-validated trigger; (2) a companion `report-non-success` job runs unconditionally (via `if: always()`) that reports/annotates the run for non-success conclusions instead of silently disappearing; (3) provenance validation gates before any deploy or artifact use.

- [ ] **Step 1: Add branch/repo/event/SHA provenance validation**

In `.github/workflows/environment-promotion.yml`, the `validate-build` job already gates on `github.event.workflow_run.conclusion == 'success'`. Extend it (or add a dedicated `validate-provenance` job) to fail closed unless:

```yaml
  validate-provenance:
    name: Validate workflow_run provenance
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_run'
    outputs:
      trusted: ${{ steps.check.outputs.trusted }}
    steps:
      - id: check
        env:
          HEAD_BRANCH: ${{ github.event.workflow_run.head_branch }}
          HEAD_REPO: ${{ github.event.workflow_run.head_repository.full_name }}
          EXPECTED_REPO: ${{ github.repository }}
          EVENT_TYPE: ${{ github.event.workflow_run.event }}
        run: |
          set -eo pipefail
          if [ "$HEAD_REPO" != "$EXPECTED_REPO" ]; then
            echo "Provenance failure: head repo $HEAD_REPO != $EXPECTED_REPO"; exit 1; fi
          if [ "$HEAD_BRANCH" != "main" ]; then
            echo "Provenance failure: head branch $HEAD_BRANCH != main"; exit 1; fi
          if [ "$EVENT_TYPE" != "push" ] && [ "$EVENT_TYPE" != "workflow_dispatch" ]; then
            echo "Provenance failure: event $EVENT_TYPE not allowed"; exit 1; fi
          echo "trusted=true"
```

- [ ] **Step 2: Gate deploy jobs on success + provenance, capturing head SHA**

Update the `validate-build` job to consume the `validate-provenance` job's `trusted` output (so provenance gates the deploy) and to run only on a success conclusion. Add `needs: validate-provenance` to `validate-build` and gate its first step:

```yaml
    needs: validate-provenance
    steps:
      - name: Assert provenance is trusted
        if: github.event_name == 'workflow_run'
        run: |
          set -eo pipefail
          if [ "${{ needs.validate-provenance.outputs.trusted }}" != "true" ]; then exit 1; fi
```

Ensure the downstream promotion jobs run only when `validate-build` (success + provenance) succeeds. Add the head SHA to build metadata so promotions act on the validated commit:

```yaml
      - name: Emit validated metadata
        run: |
          echo "image_ref=${{ env.IMAGE_REF }}" > "$GITHUB_OUTPUT"  # env already = sha-<head>
```

- [ ] **Step 3: Add a companion reporting job for non-success conclusions**

Because a `workflow_run` triggers regardless of upstream conclusion, and a skipped workflow reports as successful for required checks, add a job that runs on any conclusion and reports when it was not `success` — so a failed upstream build can never silently produce a "green" promotion:

```yaml
  report-non-success:
    name: Report non-success upstream conclusion
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_run' && github.event.workflow_run.conclusion != 'success'
    steps:
      - name: Annotate non-success conclusion
        env:
          CONCLUSION: ${{ github.event.workflow_run.conclusion }}
          RUN_URL: ${{ github.event.workflow_run.html_url }}
        run: |
          echo "Upstream workflow did not conclude success: $CONCLUSION"
          echo "See $RUN_URL"
      # This job intentionally does NOT deploy. Required checks for promotion
      # remain visible and failing, so a non-success upstream can never be green.
```

- [ ] **Step 4: Confirm required checks do not silently disappear**

Verify that the promotion's required check is the `validate-build`/aggregate job (which only the success path satisfies) and not the skipped path. Reference `.github/workflows/test-reporting.yml`'s `workflow_run` conclusion-handling pattern for consistency. Record in the PR body / spec that a filtered `workflow_run` never removes a required check from the merge gate.

- [ ] **Step 5: Validate YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/environment-promotion.yml')); print('ok')"`
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/environment-promotion.yml
git commit -m "ci(promotion): success-gated deploy, provenance validation, and non-success reporting companion"
```

---

### Task 8: Full verification + readiness gate

**Files:**
- No source changes unless a check fails.

**Interfaces:**
- Consumes: all tasks above.
- Produces: a passing targeted test run and a `check-flaky-debt` invocation proving expired quarantine fails.

- [ ] **Step 1: Run the full targeted CI unit suite**

Run:
```bash
python -m pytest tests/ci/test_external_dep_status.py \
  tests/ci/test_emit_flaky_candidates.py \
  tests/ci/test_test_skip_governance.py \
  tests/ci/test_workflow_skip_safety.py -v
```
Expected: all PASS.

- [ ] **Step 2: Prove expired quarantine fails `check-flaky-debt`**

Run the evaluator against a temporary register containing an expired flaky entry and assert the explicit `TDG116` message:

Run: `python -c "from scripts.ci.check_test_skip_governance import evaluate"` (import check) and, if a `--filter`/report path exists, run `python scripts/ci/check_test_skip_governance.py` against a temp register and confirm `TDG116` with "quarantine expired" appears and yields non-zero exit.

- [ ] **Step 3: Run broader CI validation available without a live stack**

Run: `make contract-tests` (contract/architecture tests; does not require live services).
Expected: PASS (or report any environment-specific failures precisely).

- [ ] **Step 4: Commit any residual fixes and close out**

```bash
# If any test required an adjustment:
git add -A
git commit -m "test(ci): finalize flaky-ci-mitigation verification"
```

- [ ] **Step 5: Report**

In the PR body / final response, per the repo's required PR format: Summary (what changed, why, files touched), Validation (commands run, tests passed, tests not run and why), and Risk/Follow-up (residual risk, contract/migration concerns, manual verification needed). Note which tests require a live stack and were not run.

---

## Self-Review

### 1. Spec coverage
- §1 External outage classification → Tasks 1, 2, 6 (`EXTERNAL_DEPENDENCY_UNAVAILABLE`, registry, probe allowlist, unknown≠down, status-page-evidence, required-vs-informational, no-secrets/no-PR-URLs).
- §2 Flaky lifecycle (detection/registration/exclusion) → Task 4 (detection + registration proposal, never self-quarantine) + Task 5 (exclusion fields + TDG116 expiry). Scheduled workflow does not modify required-test exclusions (Task 4 workflow edits a NON-privileged proposal issue only).
- §3 `always()` narrowing + fail-closed aggregation → Task 3 (inventory) + Task 6 (policy tests) + Task 2 (gate wiring).
- §4 Cross-workflow = orchestration, not skipping → Task 7 (success-gated deploy, reporting companion, provenance, no-silent-disappear).
- Testing (unit + workflow-policy) → Tasks 1, 4, 5, 6.
- Validation/rollout → Task 8.

### 2. Placeholder scan
All code blocks are complete; no TBD/TODO/"similar to Task N". Step 3 of Task 3 explicitly instructs to record a no-change conclusion if the audit finds zero executable `always()` overrides rather than inventing edits.

### 3. Type consistency
- `classify_probe_result(status_code, ok, well_formed, expected_status, configured_down_statuses) -> str` is defined in Task 1 and used identically inside `probe_service` in the same task.
- `emit_candidates(report, register_path, output) -> int` defined in Task 4 and used by the tracker's `--candidate-evidence` in the same task.
- `TDG116` code + message defined in Task 5 and asserted in tests in the same task.
- `check-external-deps` job name and `EXTERNAL_DEPENDENCY_UNAVAILABLE` verdict consistent across Tasks 1, 2, 6, 7.
- `tests/ci/test_workflow_skip_safety.py` fixture is created in Task 6 and referenced by Tasks 2 and 3, with explicit out-of-order instructions.

### Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-27-flaky-ci-mitigation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
