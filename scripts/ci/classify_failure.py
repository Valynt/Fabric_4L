#!/usr/bin/env python3
"""Classify CI failures into the governance triage taxonomy."""

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

GOVERNANCE_CATEGORY_KEYS = frozenset(
    {
        "infra/setup",
        "dependency/cache",
        "flaky test",
        "real regression",
        "contract drift",
        "lint/type debt",
        "environment/secret issue",
    }
)


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
    secondary_key: str = ""
    secondary_name: str = ""

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

    secondary_category_key: str = ""
    secondary_category_name: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


TAXONOMY: tuple[FailureCategory, ...] = (
    FailureCategory(
        key="environment/secret issue",
        name="Environment / Secret Issue",
        patterns=(
            r"missing secret|secret not found|secrets?\.[A-Z0-9_]+|API key not set",
            r"credentials? not configured|invalid credentials?|expired token|token expired",
            r"OIDC|id-token: write|OpenID Connect|federated credential",
            r"Infisical|Vault|KMS|AWS_ROLE_ARN|GITHUB_TOKEN",
            r"environment protection|production safety validator|dev auth bypass",
            r"ALLOW_.*BYPASS|DEV_AUTH_BYPASS|AUTH_BYPASS_ENABLED",
        ),
        auto_fixable=False,
        fix_strategy="repair_ci_secret_or_environment_wiring",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
        secondary_key="ENVIRONMENT_DEPENDENCY",
        secondary_name="Environment Dependency",
    ),
    FailureCategory(
        key="contract drift",
        name="Contract Drift",
        patterns=(
            r"OpenAPI|openapi",
            r"contract\s+drift|contract\s+compliance|contract[_\s-]?static",
            r"schema\s+mismatch|JSON Schema|jsonschema",
            r"response\s+shape|generated types?.*(?:stale|drift|differ)",
            r"required.*missing|additionalProperties|unexpected property",
            r"Zod\s+validation|DTOs?\s+(?:stale|drift)",
            r"api-types|check:api-types|source-of-truth contract",
        ),
        auto_fixable=True,
        fix_strategy="align_contract_boundary",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
        secondary_key="CONTRACT_BOUNDARY_DRIFT",
        secondary_name="Contract Boundary Drift",
    ),
    FailureCategory(
        key="lint/type debt",
        name="Lint / Type Debt",
        patterns=(
            r"\bruff\b|Ruff|black would reformat|prettier|formatting violation",
            r"\bmypy\b|pyright|TypeScript error|tsc\b|typecheck",
            r"\bESLint\b|eslint|lint failed|lint violation",
            r"forbidden import|import topology|legacy debt baseline|debt threshold",
            r"\bF\d{3}\b|\bE\d{3}\b|\bW\d{3}\b",
            r"error TS\d+|\[mypy|no-explicit-any|react-hooks/",
        ),
        auto_fixable=True,
        fix_strategy="fix_static_analysis_or_update_approved_debt_baseline",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
        secondary_key="STATIC_ANALYSIS_DEBT",
        secondary_name="Static Analysis Debt",
    ),
    FailureCategory(
        key="dependency/cache",
        name="Dependency / Cache",
        patterns=(
            r"pnpm\s+(?:install|fetch)|ERR_PNPM|frozen-lockfile|pnpm-lock\.yaml",
            r"pip\s+(?:install|wheel)|No matching distribution|Could not find a version",
            r"wheel unavailable|failed building wheel|Package .* not found",
            r"cache (?:restore|save|hit|miss|corrupt|not found|failed)",
            r"actions/cache|cache key|dependency artifact|node_modules|\.pnpm-store",
            r"corepack|package manager|lockfile|poetry|pipx|virtualenv",
        ),
        auto_fixable=True,
        fix_strategy="repair_dependency_resolution_or_cache_artifact",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
        secondary_key="DEPENDENCY_CACHE_FAILURE",
        secondary_name="Dependency Cache Failure",
    ),
    FailureCategory(
        key="infra/setup",
        name="Infra / Setup",
        patterns=(
            r"actions/(?:checkout|setup-node|setup-python|setup-java|upload-artifact|download-artifact)",
            r"setup[-\s]?(?:node|python|action)|checkout failed|unable to resolve action",
            r"runner image|hosted runner|self-hosted runner|GitHub Actions runner",
            r"Docker daemon|Cannot connect to the Docker daemon|service container",
            r"container .* (?:unhealthy|health check|never became healthy)",
            r"apt-get|brew install|OS package|tool bootstrap|workflow command failed",
            r"No space left on device|ENOSPC|network is unreachable|temporary failure in name resolution",
        ),
        auto_fixable=False,
        fix_strategy="repair_runner_or_ci_orchestration",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
        secondary_key="FIXTURE_SETUP_PORTABILITY",
        secondary_name="Fixture Setup Portability",
    ),
    FailureCategory(
        key="flaky test",
        name="Flaky Test",
        patterns=(
            r"Playwright.*(?:Timeout|timed out|deadline exceeded)",
            r"TimeoutError|test timeout|suite timeout|Promise not resolved",
            r"passed on rerun|rerun passed|retry #?\d+ passed|flaky",
            r"same commit.*pass(?:ed)? on rerun|without code changes",
            r"intermittent|nondeterministic|race condition|randomized test data",
        ),
        auto_fixable=False,
        fix_strategy="stabilize_or_quarantine_with_owner_and_exit_criteria",
        severity="warning",
        blocks_ga=False,
        blocks_paid_ga=False,
        secondary_key="TIMEOUT",
        secondary_name="Timeout / Test Isolation Leak",
    ),
    FailureCategory(
        key="real regression",
        name="Real Regression",
        patterns=(
            r"tenant[_\s-]?id|tenant\s+isolation|cross[-\s]?tenant",
            r"\bRLS\b|row[-\s]?level|JWT|decode_jwt|token validation",
            r"auth(?:entication|orization)?\s+(?:fail|bypass|denied)",
            r"audit\s+(?:event|emission)|security gate|OWASP",
            r"AssertionError|expected .* but (?:got|received)",
            r"toHaveBeenCalled|toEqual|toStrictEqual|toMatchObject",
            r"smoke test.*(?:failed|broken)|unit test.*(?:failed|regression)",
            r"No calls recorded|received different number of calls",
        ),
        auto_fixable=False,
        fix_strategy="human_review_required",
        severity="blocker",
        blocks_ga=True,
        blocks_paid_ga=True,
        secondary_key="REAL_SECURITY_REGRESSION",
        secondary_name="Real Security Regression / Test Expectation Drift",
    ),
)

UNKNOWN = FailureCategory(
    key="real regression",
    name="Real Regression",
    patterns=(r".",),
    auto_fixable=False,
    fix_strategy="human_review_required",
    severity="blocker",
    blocks_ga=True,
    blocks_paid_ga=True,
    secondary_key="UNKNOWN",
    secondary_name="Unknown / Needs Human Triage",
)


class FailureClassifier:
    def classify(self, output: str) -> ClassificationResult:
        text = output.strip()
        if not text:
            return self._result(UNKNOWN, 0, [], "")

        scored = []
        for priority, category in enumerate(TAXONOMY):
            score, snippets = category.score(text)
            scored.append((score, -priority, category, snippets))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        score, _, category, snippets = scored[0]
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

        if category.key not in GOVERNANCE_CATEGORY_KEYS:
            raise ValueError(
                f"Primary category is not in governance taxonomy: {category.key}"
            )

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
            secondary_category_key=category.secondary_key,
            secondary_category_name=category.secondary_name,
        )

    @staticmethod
    def markdown(results: list[ClassificationResult]) -> str:
        lines = [
            "| Category | Secondary | Severity | Auto-fixable | Blocks GA | Strategy | Signature | Summary |",
            "|---|---|---|---:|---:|---|---|---|",
        ]
        for result in results:
            secondary = result.secondary_category_key or "-"
            lines.append(
                f"| {result.category_key} | {secondary} | {result.severity} | "
                f"{str(result.auto_fixable).lower()} | "
                f"{str(result.blocks_ga).lower()} | {result.fix_strategy} | "
                f"{result.normalized_signature_hash[:12]} | "
                f"{result.signature_summary.replace('|', '/')[:120]} |"
            )
        return "\n".join(lines)

    @staticmethod
    def human(results: list[ClassificationResult]) -> str:
        return "\n".join(
            f"{result.category_key}: secondary={result.secondary_category_key or '-'} "
            f"severity={result.severity} auto_fix={result.auto_fixable} "
            f"blocks_ga={result.blocks_ga} strategy={result.fix_strategy} "
            f"signature={result.normalized_signature_hash[:12]} "
            f"summary={result.signature_summary}"
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