#!/usr/bin/env python3
"""Classify launch-readiness failures into a stable triage taxonomy."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from signature_normalization import (
    attach_recurrence_counts,
    normalize_ci_log_signature,
)  # noqa: E402

Severity = Literal["blocker", "warning", "info"]


@dataclass(frozen=True)
class FailureCategory:
    key: str
    name: str
    patterns: tuple[str, ...]
    auto_fixable: bool
    fix_strategy: str
    severity: Severity
    blocks_ga: bool
    blocks_paid_ga: bool

    def score(self, text: str) -> tuple[int, list[str]]:
        snippets: list[str] = []
        score = 0
        for pattern in self.patterns:
            match = re.search(
                pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
            )
            if match:
                score += 1
                snippets.append(match.group(0)[:160])
        return score, snippets


@dataclass(frozen=True)
class ClassificationResult:
    category_key: str
    category_name: str
    severity: Severity
    auto_fixable: bool
    fix_strategy: str
    confidence: int
    blocks_ga: bool
    blocks_paid_ga: bool
    matched_snippets: list[str]
    raw_summary: str
    primary_category: str
    normalized_signature_hash: str
    signature_summary: str
    normalized_signature: str
    recurrence_count: int = 1
    workflow: str = ""
    job: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


TAXONOMY: tuple[FailureCategory, ...] = (
    FailureCategory(
        key="REAL_SECURITY_REGRESSION",
        name="Real Security Regression",
        patterns=(
            r"tenant[_\s-]?id",
            r"tenant\s+isolation",
            r"cross[-\s]?tenant",
            r"\bRLS\b|row[-\s]?level",
            r"JWT|decode_jwt|token validation",
            r"auth(?:entication|orization)?\s+(?:fail|bypass|denied)",
            r"audit\s+(?:event|emission)",
        ),
        auto_fixable=False,
        fix_strategy="human_review_required",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
    ),
    FailureCategory(
        key="SOURCE_PATH_DRIFT",
        name="Source Path Drift",
        patterns=(
            r"ImportError",
            r"ModuleNotFoundError",
            r"No module named",
            r"cannot import name",
            r"Cannot find module",
            r"Module not found",
            r"is not exported from",
        ),
        auto_fixable=True,
        fix_strategy="update_import_paths",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
    ),
    FailureCategory(
        key="CONTRACT_BOUNDARY_DRIFT",
        name="Contract Boundary Drift",
        patterns=(
            r"OpenAPI",
            r"contract\s+drift",
            r"schema\s+mismatch",
            r"response\s+shape",
            r"required.*missing",
            r"additionalProperties",
            r"Zod\s+validation",
        ),
        auto_fixable=True,
        fix_strategy="align_contract_boundary",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
    ),
    FailureCategory(
        key="FIXTURE_SETUP_PORTABILITY",
        name="Fixture Setup Portability",
        patterns=(
            r"fixture .*not found|FixtureLookupError|FixtureError",
            r"UnicodeDecodeError|cp1252|charmap",
            r"ENOENT|No such file or directory",
            r"Windows path|WSL|bash not found",
            r"psycopg2|redis|Infisical",
        ),
        auto_fixable=True,
        fix_strategy="portability_fix",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
    ),
    FailureCategory(
        key="TEST_ISOLATION_LEAK",
        name="Test Isolation Leak",
        patterns=(
            r"vi\.useFakeTimers|fake timers?|fake clock",
            r"window\.location|global\.fetch|localStorage|sessionStorage",
            r"mock not restored|unrestored mock|handler not reset",
            r"not wrapped in act|React state update",
        ),
        auto_fixable=True,
        fix_strategy="cleanup_test_isolation",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
    ),
    FailureCategory(
        key="ENVIRONMENT_DEPENDENCY",
        name="Environment Dependency",
        patterns=(
            r"missing secret|secret not found|credentials not configured|API key not set",
            r"external service|provider credential|staging only|sandbox",
            r"live LLM|OIDC|SSO|billing|rollback|restore drill|telemetry dashboard",
        ),
        auto_fixable=False,
        fix_strategy="ci_only_or_env_setup",
        severity="info",
        blocks_ga=False,
        blocks_paid_ga=False,
    ),
    FailureCategory(
        key="TIMEOUT",
        name="Timeout",
        patterns=(
            r"Timeout|timed out|deadline exceeded",
            r"did not complete|took longer than|operation timed out",
            r"suite timeout|test timeout|Promise not resolved",
        ),
        auto_fixable=False,
        fix_strategy="bisect_and_profile",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
    ),
    FailureCategory(
        key="TEST_EXPECTATION_DRIFT",
        name="Test Expectation Drift",
        patterns=(
            r"AssertionError",
            r"expected .* but (?:got|received)",
            r"toHaveBeenCalled|toEqual|toStrictEqual|toMatchObject",
            r"received different number of calls|No calls recorded",
        ),
        auto_fixable=True,
        fix_strategy="align_test_with_runtime_contract",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
    ),
)

UNKNOWN = FailureCategory(
    key="UNKNOWN",
    name="Unknown / Needs Human Triage",
    patterns=(r".",),
    auto_fixable=False,
    fix_strategy="human_review_required",
    severity="blocker",
    blocks_ga=True,
    blocks_paid_ga=True,
)


class FailureClassifier:
    def classify(self, output: str) -> ClassificationResult:
        text = output.strip()
        if not text:
            category = UNKNOWN
            return self._result(category, 0, [], "")

        scored = []
        for category in TAXONOMY:
            score, snippets = category.score(text)
            scored.append((score, category, snippets))
        scored.sort(key=lambda item: item[0], reverse=True)
        score, category, snippets = scored[0]
        if score == 0:
            category = UNKNOWN
            snippets = []
        return self._result(category, score, snippets, text)

    def classify_suite(self, output: str) -> list[ClassificationResult]:
        text = output.strip()
        if not text:
            return []
        chunks = re.split(
            r"^={2,}\s+(?:FAILURES|ERRORS)\s+={2,}$|^FAILED\s+",
            text,
            flags=re.MULTILINE,
        )
        failures = [chunk.strip() for chunk in chunks if chunk.strip()]
        if len(failures) <= 1:
            return [self.classify(text)]
        return [self.classify(chunk) for chunk in failures]

    @staticmethod
    def _result(
        category: FailureCategory, score: int, snippets: list[str], text: str
    ) -> ClassificationResult:
        first_line = text.splitlines()[0] if text else ""
        signature = normalize_ci_log_signature(text)
        return ClassificationResult(
            category_key=category.key,
            category_name=category.name,
            severity=category.severity,
            auto_fixable=category.auto_fixable,
            fix_strategy=category.fix_strategy,
            confidence=score,
            blocks_ga=category.blocks_ga,
            blocks_paid_ga=category.blocks_paid_ga,
            matched_snippets=snippets,
            raw_summary=first_line[:500],
            primary_category=category.key,
            normalized_signature_hash=signature.normalized_signature_hash,
            signature_summary=signature.signature_summary,
            normalized_signature=signature.normalized_text,
        )

    @staticmethod
    def markdown(results: list[ClassificationResult]) -> str:
        lines = [
            "| Category | Severity | Auto-fixable | Blocks GA | Strategy | Signature | Summary |",
            "|---|---|---:|---:|---|---|---|",
        ]
        for result in results:
            lines.append(
                f"| {result.category_key} | {result.severity} | {str(result.auto_fixable).lower()} | "
                f"{str(result.blocks_ga).lower()} | {result.fix_strategy} | "
                f"{result.normalized_signature_hash[:12]} | {result.signature_summary.replace('|', '/')[:120]} |"
            )
        return "\n".join(lines)

    @staticmethod
    def human(results: list[ClassificationResult]) -> str:
        return "\n".join(
            f"{result.category_key}: severity={result.severity} auto_fix={result.auto_fixable} "
            f"blocks_ga={result.blocks_ga} strategy={result.fix_strategy} "
            f"signature={result.normalized_signature_hash[:12]} summary={result.signature_summary}"
            for result in results
        )


def read_input(args: argparse.Namespace) -> str:
    if args.suite:
        command = [
            sys.executable,
            "-m",
            "pytest",
            args.suite,
            *shlex.split(args.pytest_args),
        ]
        proc = subprocess.run(command, text=True, capture_output=True)
        return "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="", help="Read test output from a file.")
    parser.add_argument(
        "--suite", default="", help="Run a pytest suite and classify its output."
    )
    parser.add_argument(
        "--pytest-args", default="", help="Additional pytest arguments for --suite."
    )
    parser.add_argument(
        "--format", choices=("json", "markdown", "human"), default="human"
    )
    parser.add_argument(
        "--workflow",
        default="",
        help="Workflow name to include in recurrence grouping.",
    )
    parser.add_argument(
        "--job", default="", help="Job name to include in recurrence grouping."
    )
    parser.add_argument(
        "--include-fixes",
        action="store_true",
        help="Accepted for CLI compatibility; fixes are included as strategy fields.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw = read_input(args)
    results = FailureClassifier().classify_suite(raw)
    if not results:
        if args.format == "json":
            print("[]")
        else:
            print("No failures detected.")
        return 0

    if args.workflow or args.job:
        results = [
            replace(result, workflow=args.workflow, job=args.job) for result in results
        ]

    result_dicts = [result.to_dict() for result in results]
    attach_recurrence_counts(result_dicts)

    if args.format == "json":
        print(json.dumps(result_dicts, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(FailureClassifier.markdown(results))
    else:
        print(FailureClassifier.human(results))

    return 2 if any(result.severity == "blocker" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
