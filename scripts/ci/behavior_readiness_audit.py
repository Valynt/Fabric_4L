#!/usr/bin/env python3
"""Behavior readiness audit gate.

Converts the behavior contract from a static, standalone validation into a
mandatory, EXECUTABLE, skip-controlled readiness audit that emits a
machine-readable GREEN / YELLOW / RED report.

The audit composes three evidence sources, all runnable without live services:

  1. Static behavior contract resolution
     -> scripts/ci/check_behavior_contract.py --strict
     Proves every production-critical capability maps to allowed + denied tests.

  2. Executed behavior tests (pytest, JUnit XML)
     -> the critical-behavior backend suites actually run and pass.
     Proves the contracts are not just resolvable on paper but pass in practice.

  3. Route auth dependency enforcement
     -> scripts/ci/check_route_auth_dependencies.py
     Proves write routes require auth + tenant context.

Skip discipline:
  Every skipped or xfailed test must be either
    * benign + not_applicable (matched by config benign_skip_patterns), OR
    * covered by an active, owned, time-boxed waiver.
  Anything else (route-not-found, import error, missing dependency, fixture
  unavailable, environment not configured, expired waiver) => RED.

Status:
  GREEN  = all gates pass; only benign not_applicable skips remain.
  YELLOW = all gates pass, but one or more active waivers remain.
  RED    = any failure, OR any unwaived/expired skip/xfail, OR the static
           contract is unresolved.

Operating principle:  No critical behavior exists unless it is tested.
                      "Ready" cannot be claimed from static resolution alone.

Exit codes:
  0  GREEN or YELLOW (executable gates pass; skips controlled)
  1  RED (a required gate failed or an unwaived/expired skip/xfail remains)
  2  usage / environment error

Usage:
  python scripts/ci/behavior_readiness_audit.py
  python scripts/ci/behavior_readiness_audit.py --report artifacts/readiness/behavior-readiness-audit.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - dependency guard
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REPORT = REPO_ROOT / "artifacts/readiness/behavior-readiness-audit.json"
DEFAULT_WAIVERS = REPO_ROOT / "config/ci/behavior_readiness_waivers.yaml"
BEHAVIOR_CONTRACT_REPORT = REPO_ROOT / "artifacts/behavior-contract.json"
JUNIT_OUT = REPO_ROOT / "artifacts/readiness/critical-behaviors.junit.xml"

# Critical-behavior backend suites that must EXECUTE and pass. These mirror the
# backend portion of `pnpm run test:critical-behaviors` so the audit is
# dependency-light (no Node/frontend required) and safe in fast CI matrices.
CRITICAL_BEHAVIOR_SUITES = [
    "tests/security/test_tenant_boundary_fails_closed.py",
    "tests/security/test_billing_tenant_boundary.py",
    "tests/security/test_hostile_tenant_endpoint_family_contracts.py",
    "services/layer2-extraction/tests/test_sse_streaming_behavior.py",
    "services/layer2-extraction/tests/test_cross_tenant_hostile_behavioral.py",
    "services/layer3-knowledge/tests/test_cross_tenant_hostile_behavioral.py",
]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def _load_waivers(path: Path) -> dict:
    if yaml is None:
        return {"benign_skip_patterns": [], "waivers": []}
    if not path.exists():
        return {"benign_skip_patterns": [], "waivers": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("benign_skip_patterns", [])
    data.setdefault("waivers", [])
    return data


def _gate_static_contract() -> dict:
    """Gate 1: static behavior contract resolution."""
    cmd = [
        sys.executable,
        "scripts/ci/check_behavior_contract.py",
        "--strict",
        "--write-report",
        str(BEHAVIOR_CONTRACT_REPORT),
    ]
    proc = _run(cmd)
    resolved = {}
    if BEHAVIOR_CONTRACT_REPORT.exists():
        try:
            resolved = json.loads(BEHAVIOR_CONTRACT_REPORT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            resolved = {}
    return {
        "gate": "static-behavior-contract",
        "command": " ".join(cmd),
        "result": "pass" if proc.returncode == 0 else "fail",
        "capabilities": resolved.get("capabilities"),
        "resolved_tests": resolved.get("resolved_tests"),
        "domains_covered": resolved.get("domains_covered", []),
        "violations": resolved.get("violations", []),
        "stdout_tail": proc.stdout.strip().splitlines()[-5:],
    }


def _gate_executed_behavior() -> dict:
    """Gate 2: executed behavior tests with JUnit capture."""
    JUNIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        "pytest.ini",
        "--no-mandatory-dep-check",
        "--tb=short",
        "-q",
        "-n",
        "0",
        f"--junitxml={JUNIT_OUT}",
        *CRITICAL_BEHAVIOR_SUITES,
    ]
    proc = _run(cmd)
    return {
        "gate": "executed-behavior-tests",
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-5:],
    }


def _gate_route_auth() -> dict:
    """Gate 3: route auth dependency enforcement."""
    cmd = [sys.executable, "scripts/ci/check_route_auth_dependencies.py"]
    proc = _run(cmd)
    return {
        "gate": "route-auth-dependencies",
        "command": " ".join(cmd),
        "result": "pass" if proc.returncode == 0 else "fail",
        "stdout_tail": proc.stdout.strip().splitlines()[-5:],
    }


def _parse_junit(path: Path) -> dict:
    """Parse JUnit XML into counts + per-skip/xfail details."""
    if not path.is_file() or path.stat().st_size == 0:
        return {
            "parsed": False,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "xfailed": 0,
            "skips": [],
        }

    tree = ET.parse(path)
    root = tree.getroot()

    failed = 0
    errors = 0
    skipped = 0
    xfailed = 0
    total = 0
    skips: list[dict] = []

    for testcase in root.iter("testcase"):
        total += 1
        node_id = f"{testcase.attrib.get('classname', '')}::{testcase.attrib.get('name', '')}"
        if testcase.find("failure") is not None:
            failed += 1
        elif testcase.find("error") is not None:
            errors += 1
        skip_el = testcase.find("skipped")
        if skip_el is not None:
            message = skip_el.attrib.get("message", "") or (skip_el.text or "")
            skip_type = skip_el.attrib.get("type", "")
            is_xfail = "xfail" in skip_type.lower() or "xfail" in message.lower()
            if is_xfail:
                xfailed += 1
            else:
                skipped += 1
            skips.append(
                {
                    "node_id": node_id.strip(":"),
                    "message": message.strip(),
                    "kind": "xfail" if is_xfail else "skip",
                }
            )

    passed = total - failed - errors - skipped - xfailed
    return {
        "parsed": True,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "xfailed": xfailed,
        "skips": skips,
    }


def _classify_skip(skip: dict, waivers: dict) -> dict:
    """Classify a single skip/xfail: benign | active-waiver | expired | unwaived."""
    message = skip.get("message", "")
    node_id = skip.get("node_id", "")

    for pattern in waivers.get("benign_skip_patterns", []):
        needle = pattern.get("message_pattern", "")
        if needle and needle in message:
            return {
                **skip,
                "classification": "benign",
                "category": pattern.get("category", "not_applicable"),
                "waiver_id": pattern.get("id"),
            }

    today = date.today()
    for waiver in waivers.get("waivers", []):
        needle = waiver.get("message_pattern", "")
        skip_id = waiver.get("skip_id", "")
        matches = (needle and needle in message) or (skip_id and skip_id in node_id)
        if not matches:
            continue
        expires_on = waiver.get("expires_on")
        expired = False
        if expires_on:
            try:
                expired = datetime.strptime(str(expires_on), "%Y-%m-%d").date() < today
            except ValueError:
                expired = True
        if expired:
            return {
                **skip,
                "classification": "expired-waiver",
                "waiver_id": waiver.get("id"),
                "expires_on": expires_on,
            }
        return {
            **skip,
            "classification": "active-waiver",
            "waiver_id": waiver.get("id"),
            "owner": waiver.get("owner"),
            "ticket": waiver.get("ticket"),
            "expires_on": expires_on,
        }

    return {**skip, "classification": "unwaived"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Behavior readiness audit gate")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--waivers", type=Path, default=DEFAULT_WAIVERS)
    args = parser.parse_args(argv)

    if yaml is None:
        print("ERROR: pyyaml is required for the behavior readiness audit", file=sys.stderr)
        return 2

    waivers = _load_waivers(args.waivers)

    print("=" * 78)
    print("Behavior Readiness Audit")
    print("=" * 78)

    # Gate 1: static contract
    static_gate = _gate_static_contract()
    print(f"\n[1/3] static-behavior-contract: {static_gate['result'].upper()} "
          f"(capabilities={static_gate.get('capabilities')}, "
          f"domains={len(static_gate.get('domains_covered', []))})")

    # Gate 2: executed behavior tests
    exec_gate = _gate_executed_behavior()
    junit = _parse_junit(JUNIT_OUT)
    print(f"[2/3] executed-behavior-tests: passed={junit['passed']} "
          f"failed={junit['failed']} errors={junit['errors']} "
          f"skipped={junit['skipped']} xfailed={junit['xfailed']}")

    # Gate 3: route auth
    auth_gate = _gate_route_auth()
    print(f"[3/3] route-auth-dependencies: {auth_gate['result'].upper()}")

    # Classify skips
    classified = [_classify_skip(s, waivers) for s in junit["skips"]]
    benign = [c for c in classified if c["classification"] == "benign"]
    active_waivers = [c for c in classified if c["classification"] == "active-waiver"]
    blocking_skips = [
        c for c in classified
        if c["classification"] in ("unwaived", "expired-waiver")
    ]

    # Determine status (fail-closed)
    failures = []
    if static_gate["result"] != "pass":
        failures.append("static-behavior-contract gate failed")
    if exec_gate["returncode"] != 0 or junit["failed"] or junit["errors"]:
        failures.append("executed-behavior-tests gate failed")
    if auth_gate["result"] != "pass":
        failures.append("route-auth-dependencies gate failed")
    if blocking_skips:
        failures.append(f"{len(blocking_skips)} unwaived/expired skip(s)/xfail(s)")

    if failures:
        final_status = "RED"
    elif active_waivers:
        final_status = "YELLOW"
    else:
        final_status = "GREEN"

    report = {
        "gate": "behavior-readiness-audit",
        "command": "python scripts/ci/behavior_readiness_audit.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "pass" if final_status in ("GREEN", "YELLOW") else "fail",
        "final_status": final_status,
        "passed_count": junit["passed"],
        "failed_count": junit["failed"] + junit["errors"],
        "skipped_count": junit["skipped"],
        "xfailed_count": junit["xfailed"],
        "waiver_references": [
            {
                "waiver_id": c.get("waiver_id"),
                "node_id": c.get("node_id"),
                "owner": c.get("owner"),
                "ticket": c.get("ticket"),
                "expires_on": c.get("expires_on"),
            }
            for c in active_waivers
        ],
        "benign_skips": [
            {"waiver_id": c.get("waiver_id"), "node_id": c.get("node_id"), "message": c.get("message")}
            for c in benign
        ],
        "blocking_skips": [
            {"classification": c["classification"], "node_id": c.get("node_id"), "message": c.get("message")}
            for c in blocking_skips
        ],
        "gates": {
            "static_behavior_contract": static_gate,
            "executed_behavior_tests": {**exec_gate, **junit},
            "route_auth_dependencies": auth_gate,
        },
        "failures": failures,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("\n" + "-" * 78)
    print(f"passed={junit['passed']} failed={report['failed_count']} "
          f"skipped={junit['skipped']} xfailed={junit['xfailed']} "
          f"benign_skips={len(benign)} active_waivers={len(active_waivers)} "
          f"blocking_skips={len(blocking_skips)}")
    if blocking_skips:
        print("\nBLOCKING skips/xfails (must be fixed or waived):")
        for c in blocking_skips:
            print(f"  - [{c['classification']}] {c.get('node_id')} :: {c.get('message')}")
    if active_waivers:
        print("\nActive waivers (YELLOW):")
        for c in active_waivers:
            print(f"  - {c.get('waiver_id')} {c.get('node_id')} (expires {c.get('expires_on')})")
    print("-" * 78)
    print(f"FINAL STATUS: {final_status}")
    print(f"Report: {args.report}")

    return 0 if final_status in ("GREEN", "YELLOW") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
