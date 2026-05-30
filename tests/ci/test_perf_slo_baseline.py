from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "perf" / "slo-baseline.py"
K6_SCRIPT = REPO_ROOT / "scripts" / "perf" / "load-test-critical-paths.js"


def _load_module():
    spec = importlib.util.spec_from_file_location("slo_baseline", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _summary(p95: float, failed_rate: float = 0.0) -> dict:
    return {
        "metrics": {
            "http_req_duration": {"values": {"p(95)": p95}},
            "http_req_failed": {"values": {"rate": failed_rate}},
            "checks": {"values": {"rate": 1.0 - failed_rate}},
            "iterations": {"count": 25},
        }
    }


def test_load_test_critical_paths_defines_required_thresholds() -> None:
    source = K6_SCRIPT.read_text(encoding="utf-8")

    assert "http_req_duration: ['p(95)<200']" in source
    assert "http_req_failed: ['rate<0.01']" in source
    assert "`${BASE_URL}/health`" in source
    assert "`${BASE_URL}/api/v1/tenants`" in source
    assert "Bearer ${__ENV.TEST_TOKEN}" in source


def test_baseline_script_creates_dashboard_artifacts(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    output_dir = tmp_path / "artifacts" / "performance"
    summary_path.write_text(json.dumps(_summary(100.0)), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--summary",
            str(summary_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    latest = json.loads((output_dir / "slo-baseline-latest.json").read_text(encoding="utf-8"))
    assert latest["status"] == "baseline_created"
    assert latest["all_passed"] is True
    assert latest["metrics"]["http_req_duration_p95_ms"] == 100.0
    assert (output_dir / "baseline.json").exists()


def test_regression_detection_alerts_on_ten_percent_or_more_slowdown(tmp_path: Path) -> None:
    module = _load_module()
    baseline = module.PerformanceMetrics(http_req_duration_p95_ms=100.0, http_req_failed_rate=0.0)
    current = module.PerformanceMetrics(http_req_duration_p95_ms=111.0, http_req_failed_rate=0.0)

    regressions = module.detect_regressions(current, baseline, 0.10)

    assert len(regressions) == 1
    assert regressions[0]["metric"] == "http_req_duration_p95_ms"
    assert regressions[0]["delta_percent"] == 11.0


def test_cli_fails_and_writes_alert_when_current_run_regresses(tmp_path: Path) -> None:
    output_dir = tmp_path / "artifacts" / "performance"
    baseline_path = output_dir / "baseline.json"
    current_summary = tmp_path / "current.json"
    output_dir.mkdir(parents=True)

    baseline_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-05-30T00:00:00+00:00",
                "source": "test",
                "metrics": {
                    "http_req_duration_p95_ms": 100.0,
                    "http_req_failed_rate": 0.0,
                    "checks_rate": 1.0,
                    "iterations_count": 10,
                },
            }
        ),
        encoding="utf-8",
    )
    current_summary.write_text(json.dumps(_summary(125.0)), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--summary",
            str(current_summary),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    latest = json.loads((output_dir / "slo-baseline-latest.json").read_text(encoding="utf-8"))
    assert latest["status"] == "regression"
    assert latest["all_passed"] is False
    assert latest["alerts"]
    assert latest["alerts"][0]["metric"] == "http_req_duration_p95_ms"
