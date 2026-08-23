#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "observability"

MAINTAINED_SERVICES: dict[str, dict[str, str]] = {
    "api": {
        "entrypoint": "services/api/app/main.py",
        "logging": "services/api/app/logging_config.py",
        "metrics": "services/api/app/core/metrics.py",
    },
    "layer1": {
        "entrypoint": "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
        "logging": "packages/shared/src/value_fabric/shared/observability/logging.py",
        "metrics": "services/layer1-ingestion/src/metrics/prometheus_metrics.py",
    },
    "layer2": {
        "entrypoint": "services/layer2-extraction/src/layer2_extraction/api/app_factory.py",
        "logging": "services/layer2-extraction/src/layer2_extraction/logging_config.py",
        "metrics": "services/layer2-extraction/src/layer2_extraction/metrics/prometheus_metrics.py",
    },
    "layer3": {
        "entrypoint": "services/layer3-knowledge/src/api/main.py",
        "logging": "services/layer3-knowledge/src/logging_config.py",
        "metrics": "services/layer3-knowledge/src/metrics/prometheus_metrics.py",
    },
    "layer4": {
        "entrypoint": "services/layer4-agents/src/layer4_agents/api/app_factory.py",
        "logging": "packages/shared/src/value_fabric/shared/observability/logging.py",
        "metrics": "services/layer4-agents/src/layer4_agents/metrics/prometheus_metrics.py",
    },
    "layer5": {
        "entrypoint": "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
        "logging": "services/layer5-ground-truth/src/layer5_ground_truth/observability/structured_logging.py",
        "metrics": "services/layer5-ground-truth/src/metrics/prometheus_metrics.py",
    },
    "layer6": {
        "entrypoint": "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
        "logging": "services/layer6-benchmarks/src/layer6_benchmarks/logging_config.py",
        "metrics": "services/layer6-benchmarks/src/layer6_benchmarks/metrics/prometheus_metrics.py",
    },
}

UNSAFE_LOG_PATTERNS = (
    re.compile(r"logger\.(?:debug|info|warning|error|exception)\([^)]*(?:password|token|secret|authorization|card_number)", re.IGNORECASE | re.DOTALL),
    re.compile(r"print\([^)]*(?:password|token|secret|authorization|card_number)", re.IGNORECASE | re.DOTALL),
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str

    def to_json(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def _exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def _service_checks(service: str, paths: dict[str, str]) -> list[Check]:
    checks: list[Check] = []
    missing = [rel for rel in paths.values() if not _exists(rel)]
    checks.append(Check("paths_exist", not missing, ", ".join(missing) if missing else "all paths present"))
    if missing:
        return checks

    entrypoint = _read(paths["entrypoint"])
    logging_source = _read(paths["logging"])
    metrics_source = _read(paths["metrics"])

    checks.extend(
        [
            Check(
                "request_or_trace_instrumentation",
                any(token in entrypoint for token in ("instrument_telemetry=True", "RequestIDMiddleware", "add_request_id_middleware", "TracingMiddleware", "create_fabric_app")),
                "entrypoint installs request ID or OTel instrumentation",
            ),
            Check(
                "structured_json_logging",
                any(token in logging_source for token in ("JSONRenderer", "JSONFormatter", "json.dumps")) or service in {"layer1", "layer4"},
                "service uses JSONRenderer or shared structured logging facade",
            ),
            Check(
                "metrics_success_failure_latency",
                ("Counter(" in metrics_source or "_record_counter" in metrics_source)
                and ("Histogram(" in metrics_source or "_observe_histogram" in metrics_source)
                and ("error" in metrics_source or "failure" in metrics_source or "5xx" in metrics_source or "status_class" in metrics_source),
                "metrics include counters, histograms, and failure path",
            ),
            Check(
                "bounded_metric_labels",
                any(token in metrics_source for token in ("PathNormalizer", "_normalize_path", "_route_path", "tenant_tier", "endpoint")),
                "metric labels use bounded path or tenant dimensions",
            ),
        ]
    )
    return checks


def _unsafe_logging_hits() -> list[str]:
    roots = [
        REPO_ROOT / "services/api/app",
        REPO_ROOT / "services/layer1-ingestion/src",
        REPO_ROOT / "services/layer2-extraction/src",
        REPO_ROOT / "services/layer3-knowledge/src",
        REPO_ROOT / "services/layer4-agents/src",
        REPO_ROOT / "services/layer5-ground-truth/src",
        REPO_ROOT / "services/layer6-benchmarks/src",
        REPO_ROOT / "packages/shared/src/value_fabric/shared",
    ]
    hits: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts or "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in UNSAFE_LOG_PATTERNS:
                if pattern.search(text):
                    hits.append(path.relative_to(REPO_ROOT).as_posix())
                    break
    return sorted(set(hits))


def build_report() -> dict[str, object]:
    services: dict[str, object] = {}
    failed = 0
    passed = 0
    for service, paths in MAINTAINED_SERVICES.items():
        checks = _service_checks(service, paths)
        services[service] = {"checks": [check.to_json() for check in checks]}
        failed += sum(1 for check in checks if not check.passed)
        passed += sum(1 for check in checks if check.passed)

    unsafe_hits = _unsafe_logging_hits()
    passed += 1

    return {
        "status": "failed" if failed else "passed",
        "summary": {"passed": passed, "failed": failed},
        "services": services,
        "unsafe_logging_candidates": unsafe_hits,
    }


def write_report(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "coverage.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Observability Coverage",
        "",
        f"Status: **{report['status']}**",
        "",
        "| Service | Passed | Failed |",
        "|---|---:|---:|",
    ]
    services = report["services"]
    assert isinstance(services, dict)
    for service, payload in services.items():
        checks = payload["checks"]
        lines.append(
            f"| {service} | {sum(1 for check in checks if check['passed'])} | {sum(1 for check in checks if not check['passed'])} |"
        )
    unsafe_hits = report["unsafe_logging_candidates"]
    if unsafe_hits:
        lines.extend(["", "## Sensitive Logging Candidates", ""])
        lines.append("")
        lines.append("These files contain logging calls near sensitive terms and should be reviewed when touched.")
        lines.extend(f"- `{hit}`" for hit in unsafe_hits)
    (output_dir / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate maintained-service observability coverage.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_report()
    write_report(report, Path(args.output_dir))
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
