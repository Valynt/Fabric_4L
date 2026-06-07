#!/usr/bin/env python3
"""Behavior contract gate.

Statically validates the behavior contract registry (contracts/behavior-contract.yaml)
so that every production-critical capability proves BOTH its intended allowed path
and its intended denied path before release.

The gate is fully static: it does NOT run pytest, start services, or touch the
network. It is therefore safe to run in fast CI matrices and in `make verify`.

For each registered capability it asserts:
  - the capability maps to a canonical domain
  - it declares an `allowed` AND a `denied` test (allowed + denied paths)
  - each referenced test file exists
  - each referenced test is present in that file
      * backend (pytest): a `def <test>` / `async def <test>` definition
      * frontend (vitest/playwright): an `it(...)`/`test(...)` title substring
  - backend `marker` values are registered in pytest.ini

It also enforces a ratchet baseline (config/ci/behavior_contract_baseline.json):
the number of capabilities and the set of covered domains must not regress.

Operating principle:  No critical behavior exists unless it is tested.
Enforcement rule:      Intended behavior passes. Unintended behavior fails.
                       Untested behavior is not production-ready.

Exit codes:
  0  contract satisfied (or warn-only mode)
  1  one or more violations

Usage:
  python scripts/ci/check_behavior_contract.py --strict
  python scripts/ci/check_behavior_contract.py --write-report artifacts/behavior-contract.json
  python scripts/ci/check_behavior_contract.py --update-baseline   # author-only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - dependency guard
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_DOMAINS = {
    "auth",
    "tenant_isolation",
    "api_access",
    "configuration_validity",
    "environment_safety",
    "data_boundaries",
    "failure_behavior",
    "frontend_user_flows",
    "service_to_service",
    "production_readiness",
}

FRONTEND_TITLE_RE_TMPL = r"""(?:it|test|journeyTest)(?:\.each\([^)]*\))?\s*\(\s*['"`].*{needle}.*['"`]"""


@dataclass
class Violation:
    capability: str
    detail: str


@dataclass
class Result:
    capabilities: int = 0
    resolved_tests: int = 0
    domains_covered: set[str] = field(default_factory=set)
    violations: list[Violation] = field(default_factory=list)


def _load_registered_markers(pytest_ini: Path) -> set[str]:
    if not pytest_ini.exists():
        return set()
    markers: set[str] = set()
    in_markers = False
    for raw in pytest_ini.read_text(encoding="utf-8").splitlines():
        if raw.startswith("markers ="):
            in_markers = True
            continue
        if in_markers:
            # marker lines are indented "name: description"; section ends at a
            # non-indented, non-empty line (e.g. "filterwarnings =").
            if raw and not raw[0].isspace():
                break
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            name = stripped.split(":", 1)[0].strip()
            if name:
                markers.add(name)
    return markers


def _test_present(file_path: Path, test: str, kind: str) -> bool:
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return False
    if kind == "frontend":
        needle = re.escape(test)
        return re.search(FRONTEND_TITLE_RE_TMPL.format(needle=needle), content) is not None
    # backend pytest
    return re.search(rf"^\s*(?:async\s+)?def\s+{re.escape(test)}\s*\(", content, re.MULTILINE) is not None


def _check_side(
    cap_id: str,
    side: str,
    spec: object,
    kind: str,
    result: Result,
) -> None:
    if not isinstance(spec, dict):
        result.violations.append(Violation(cap_id, f"{side} path must be a mapping with file/test"))
        return
    file_rel = spec.get("file")
    test = spec.get("test")
    if not file_rel or not test:
        result.violations.append(Violation(cap_id, f"{side} path requires both 'file' and 'test'"))
        return
    file_path = REPO_ROOT / file_rel
    if not file_path.exists():
        result.violations.append(Violation(cap_id, f"{side} file does not exist: {file_rel}"))
        return
    if not _test_present(file_path, str(test), kind):
        result.violations.append(
            Violation(cap_id, f"{side} test '{test}' not found in {file_rel}")
        )
        return
    result.resolved_tests += 1


def validate(registry: dict, markers: set[str]) -> Result:
    result = Result()
    declared_domains = set(registry.get("domains") or [])
    unknown = declared_domains - CANONICAL_DOMAINS
    if unknown:
        result.violations.append(
            Violation("<registry>", f"unknown domains declared: {sorted(unknown)}")
        )

    capabilities = registry.get("capabilities") or []
    seen_ids: set[str] = set()
    for cap in capabilities:
        cap_id = cap.get("id", "<missing-id>")
        if cap_id in seen_ids:
            result.violations.append(Violation(cap_id, "duplicate capability id"))
        seen_ids.add(cap_id)
        result.capabilities += 1

        domain = cap.get("domain")
        if domain not in CANONICAL_DOMAINS:
            result.violations.append(Violation(cap_id, f"invalid/missing domain: {domain!r}"))
        else:
            result.domains_covered.add(domain)

        kind = cap.get("kind", "backend")
        if kind not in {"backend", "frontend"}:
            result.violations.append(Violation(cap_id, f"invalid kind: {kind!r}"))
            kind = "backend"

        if "allowed" not in cap:
            result.violations.append(Violation(cap_id, "missing required 'allowed' path"))
        else:
            _check_side(cap_id, "allowed", cap.get("allowed"), kind, result)

        if "denied" not in cap:
            result.violations.append(Violation(cap_id, "missing required 'denied' path"))
        else:
            _check_side(cap_id, "denied", cap.get("denied"), kind, result)

        if not cap.get("expected_failure_mode"):
            result.violations.append(Violation(cap_id, "missing 'expected_failure_mode'"))

        if kind == "backend":
            marker = cap.get("marker")
            if not marker:
                result.violations.append(Violation(cap_id, "backend capability requires a 'marker'"))
            elif markers and marker not in markers:
                result.violations.append(
                    Violation(cap_id, f"marker '{marker}' is not registered in pytest.ini")
                )

    return result


def _check_baseline(result: Result, baseline_path: Path) -> list[Violation]:
    if not baseline_path.exists():
        return []
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        return [Violation("<baseline>", f"could not parse baseline: {exc}")]
    violations: list[Violation] = []
    min_caps = int(baseline.get("min_capabilities", 0))
    if result.capabilities < min_caps:
        violations.append(
            Violation(
                "<baseline>",
                f"capability count regressed: {result.capabilities} < baseline {min_caps}",
            )
        )
    required_domains = set(baseline.get("required_domains") or [])
    missing = required_domains - result.domains_covered
    if missing:
        violations.append(
            Violation("<baseline>", f"domains regressed below baseline: {sorted(missing)}")
        )
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=Path, default=REPO_ROOT / "contracts/behavior-contract.yaml")
    ap.add_argument("--pytest-ini", type=Path, default=REPO_ROOT / "pytest.ini")
    ap.add_argument("--baseline", type=Path, default=REPO_ROOT / "config/ci/behavior_contract_baseline.json")
    ap.add_argument("--write-report", type=Path)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any violation (default behaviour in CI).",
    )
    ap.add_argument(
        "--warn-only",
        action="store_true",
        help="Always exit 0; print violations as warnings. Overrides --strict.",
    )
    ap.add_argument(
        "--update-baseline",
        action="store_true",
        help="Author-only: rewrite the baseline from the current registry, then exit.",
    )
    args = ap.parse_args()

    if yaml is None:
        print("ERROR: pyyaml is required to run the behavior contract gate", file=sys.stderr)
        return 1

    if not args.registry.exists():
        print(f"ERROR: registry not found: {args.registry}", file=sys.stderr)
        return 1

    registry = yaml.safe_load(args.registry.read_text(encoding="utf-8")) or {}
    markers = _load_registered_markers(args.pytest_ini)
    result = validate(registry, markers)
    result.violations.extend(_check_baseline(result, args.baseline))

    if args.update_baseline:
        payload = {
            "_comment": "Ratchet baseline for the behavior contract gate. "
            "Capability count and covered domains must not regress below these values. "
            "Regenerate with: python scripts/ci/check_behavior_contract.py --update-baseline",
            "min_capabilities": result.capabilities,
            "required_domains": sorted(result.domains_covered),
        }
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Baseline written to {args.baseline} (capabilities={result.capabilities})")
        return 0

    report = {
        "capabilities": result.capabilities,
        "resolved_tests": result.resolved_tests,
        "domains_covered": sorted(result.domains_covered),
        "domains_missing": sorted(CANONICAL_DOMAINS - result.domains_covered),
        "violations": [{"capability": v.capability, "detail": v.detail} for v in result.violations],
    }

    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("Behavior Contract Gate")
    print(f"  capabilities:    {result.capabilities}")
    print(f"  resolved tests:  {result.resolved_tests}")
    print(f"  domains covered: {len(result.domains_covered)}/{len(CANONICAL_DOMAINS)}")
    missing = CANONICAL_DOMAINS - result.domains_covered
    if missing:
        print(f"  domains missing: {sorted(missing)}")

    if result.violations:
        print(f"\n{len(result.violations)} violation(s):")
        for v in result.violations:
            print(f"  - [{v.capability}] {v.detail}")
    else:
        print("\nAll registered behavior contracts resolve to existing allowed + denied tests.")

    if args.warn_only:
        return 0
    return 1 if result.violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
