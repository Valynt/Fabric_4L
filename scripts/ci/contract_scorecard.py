#!/usr/bin/env python3
"""Compute contract compliance scorecard and trendline.

Usage:
    python scripts/ci/contract_scorecard.py [--output contract-scorecard.json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CONTRACT_RULES = {
    "§2.1": {
        "name": "Tenant Context Propagation",
        "patterns": [
            (r"tenant_id\s*[:=]", "tenant_id parameter", "medium"),
            (r"request\.headers\[. tenant", "direct header access", "high"),
        ],
    },
    "§2.2": {
        "name": "DB Session Isolation",
        "patterns": [
            (r"execute\s*\(.*tenant", "raw SQL tenant filtering", "medium"),
            (r"create_engine\s*\(", "explicit DB connect", "medium"),
        ],
    },
    "§2.3": {
        "name": "Middleware/Auth Flow",
        "patterns": [
            (r"@app\.middleware", "inline middleware", "medium"),
        ],
    },
    "§2.4": {
        "name": "Tool Invocation Boundary",
        "patterns": [
            (r"def\s+\w+.*\(.*\).*:\s*\n.*raise\s+(ValueError|ToolError|Exception)", "tool throwing exception", "high"),
            (r"tools\s*=\s*\[", "inline tool definition", "low"),
        ],
    },
    "§2.5": {
        "name": "Agent Output Shape",
        "patterns": [
            (r"json\.loads\s*\(", "raw json.loads on LLM output", "high"),
        ],
    },
    "§2.6": {
        "name": "UI State Progression",
        "patterns": [
            (r"\bnavigate\s*\(", "imperative navigation", "low"),
            (r"router\.push\s*\(", "imperative router.push", "low"),
            (r"['\"]\s*\+\s*.*['\"]\s*\+\s*.*['\"]", "URL string concatenation", "low"),
        ],
    },
}


def _count_matches(pattern: str, paths: list[Path], file_types: list[str] | None = None) -> int:
    """Count grep matches across paths with file type filtering."""
    total = 0
    for p in paths:
        if not p.exists():
            continue
        try:
            rg_args = ["rg", "-c", "--multiline", pattern, str(p)]
            if file_types:
                for ft in file_types:
                    rg_args.extend(["-t", ft])
            result = subprocess.run(
                rg_args,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                total += sum(1 for line in result.stdout.splitlines() if line.strip())
        except FileNotFoundError:
            # Fallback to Python regex if ripgrep unavailable
            for ext in (file_types or ["*"]):
                for file_path in p.rglob(f"*.{ext}" if ext != "*" else "*"):
                    if file_path.is_file() and not any(
                        skip in str(file_path) for skip in ["node_modules", ".venv", "__pycache__", ".git"]
                    ):
                        text = file_path.read_text(encoding="utf-8", errors="ignore")
                        total += len(re.findall(pattern, text, re.MULTILINE))
    return total


def _scan_contract(contract_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Scan a single contract and return violation counts."""
    backend_paths = [Path("services")]
    frontend_paths = [Path("apps/web/src")]

    violations: list[dict[str, Any]] = []
    total_count = 0

    for pattern, label, severity in config["patterns"]:
        if label in ("imperative navigation", "imperative router.push", "URL string concatenation"):
            paths = frontend_paths
            file_types = ["ts", "tsx", "js", "jsx"]
        else:
            paths = backend_paths
            file_types = ["py"]

        count = _count_matches(pattern, paths, file_types=file_types)
        if count:
            total_count += count
            violations.append({
                "pattern_label": label,
                "severity": severity,
                "count": count,
            })

    return {
        "contract": contract_id,
        "name": config["name"],
        "total_violations": total_count,
        "violations": violations,
    }


def compute_scorecard() -> dict[str, Any]:
    """Compute full scorecard."""
    contract_results: list[dict[str, Any]] = []
    total_violations = 0

    for cid, config in CONTRACT_RULES.items():
        result = _scan_contract(cid, config)
        contract_results.append(result)
        total_violations += result["total_violations"]

    # Baseline targets from CONTRACT_AUDIT_REPORT.md
    baseline = {
        "§2.1": 200,
        "§2.2": 43,
        "§2.3": 42,
        "§2.4": 46,
        "§2.5": 8,
        "§2.6": 90,
    }

    overall_score = 0.0
    if baseline:
        weighted = 0.0
        for r in contract_results:
            b = baseline.get(r["contract"], 1)
            weighted += max(0, 1 - r["total_violations"] / b)
        overall_score = round((weighted / len(baseline)) * 100, 2)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_score": overall_score,
        "total_violations": total_violations,
        "target_score": 85,
        "contracts": contract_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Contract compliance scorecard")
    parser.add_argument("--output", type=str, default="contract-scorecard.json")
    parser.add_argument("--gha-comment", action="store_true", help="Emit GitHub Actions comment markdown")
    args = parser.parse_args()

    scorecard = compute_scorecard()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)

    if args.gha_comment:
        print("## 📊 Contract Compliance Scorecard")
        print(f"**Overall Score: {scorecard['overall_score']}%** (target: {scorecard['target_score']}%)")
        print()
        print("| Contract | Name | Violations |")
        print("|----------|------|-----------:|")
        for c in scorecard["contracts"]:
            status = "🟢" if c["total_violations"] == 0 else "🟡" if c["total_violations"] < 20 else "🔴"
            print(f"| {status} {c['contract']} | {c['name']} | {c['total_violations']} |")
        print()
        if scorecard["overall_score"] >= scorecard["target_score"]:
            print("PASS **Target attained**")
        else:
            gap = scorecard["target_score"] - scorecard["overall_score"]
            print(f"⚠️ **{gap:.1f} points below target**")

    return 0 if scorecard["overall_score"] >= scorecard["target_score"] else 1


if __name__ == "__main__":
    sys.exit(main())
