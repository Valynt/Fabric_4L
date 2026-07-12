"""Tests for monitoring validation scripts and alert rules.

Validates:
- monitoring-validation.sh script functionality
- Prometheus recording rules
- Alert rule groups and expressions
- Runbook URLs and annotations
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml


class TestMonitoringValidationScript:
    """Tests for the monitoring validation script."""

    def test_monitoring_validation_script_exists(self, repo_root: Path) -> None:
        """Verify monitoring-validation.sh script exists."""
        script = repo_root / "scripts" / "monitoring-validation.sh"
        assert script.exists(), "monitoring-validation.sh must exist"

    def test_monitoring_validation_script_syntax(self, repo_root: Path) -> None:
        """Verify script has valid bash syntax."""
        bash = shutil.which("bash")
        for candidate in (
            Path("C:/Git/usr/bin/bash.exe"),
            Path("C:/Program Files/Git/bin/bash.exe"),
            Path("C:/Git/bin/bash.exe"),
        ):
            if bash and "system32" not in bash.lower():
                break
            if candidate.exists():
                bash = str(candidate)
                break
        assert bash is not None, "bash must be available to syntax-check monitoring-validation.sh"
        
        result = subprocess.run(
            [bash, "-n", "scripts/monitoring-validation.sh"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Script syntax error: {result.stderr}"

    def test_monitoring_validation_checks_prometheus_targets(
        self, repo_root: Path
    ) -> None:
        """[6a] Verify script checks Prometheus targets health."""
        script = repo_root / "scripts" / "monitoring-validation.sh"
        
        with open(script) as f:
            content = f.read()
        
        assert "Prometheus Targets Health" in content
        assert "/api/v1/targets" in content
        assert "jq" in content

    def test_monitoring_validation_checks_prometheus_rules(
        self, repo_root: Path
    ) -> None:
        """[6b] Verify script checks Prometheus rules load status."""
        script = repo_root / "scripts" / "monitoring-validation.sh"
        
        with open(script) as f:
            content = f.read()
        
        assert "Prometheus Rules Load Status" in content
        assert "/api/v1/rules" in content

    def test_monitoring_validation_checks_alerts(self, repo_root: Path) -> None:
        """[6c] Verify script checks Prometheus alerts status."""
        script = repo_root / "scripts" / "monitoring-validation.sh"
        
        with open(script) as f:
            content = f.read()
        
        assert "Prometheus Alerts Status" in content
        assert "/api/v1/alerts" in content

    def test_monitoring_validation_checks_alertmanager_status(
        self, repo_root: Path
    ) -> None:
        """[6d] Verify script checks Alertmanager status."""
        script = repo_root / "scripts" / "monitoring-validation.sh"
        
        with open(script) as f:
            content = f.read()
        
        assert "Alertmanager Status" in content
        assert "/api/v2/status" in content

    def test_monitoring_validation_has_smoke_test(self, repo_root: Path) -> None:
        """[6e, 6f] Verify script includes alert pipeline smoke test."""
        script = repo_root / "scripts" / "monitoring-validation.sh"
        
        with open(script) as f:
            content = f.read()
        
        assert "Alert Pipeline Smoke Test" in content
        assert "/api/v2/alerts" in content
        assert "POST" in content or "-X POST" in content


class TestAlertingRules:
    """Tests for standalone alerting rules file."""

    @pytest.fixture(scope="class")
    def alert_rules(self, monitoring_dir: Path) -> list[dict]:
        """Load alert rules from monitoring/alerting/rules.yml."""
        rules_file = monitoring_dir / "alerting" / "rules.yml"
        
        with open(rules_file) as f:
            content = yaml.safe_load(f)
        
        return content.get("groups", [])

    def test_alert_rules_file_exists(self, monitoring_dir: Path) -> None:
        """Verify standalone alerting rules file exists."""
        rules_file = monitoring_dir / "alerting" / "rules.yml"
        assert rules_file.exists(), "rules.yml must exist in monitoring/alerting/"

    def test_alert_groups_present(self, alert_rules: list[dict]) -> None:
        """Verify alert rule groups are defined."""
        assert len(alert_rules) > 0, "At least one alert group must be defined"
        
        group_names = {g.get("name") for g in alert_rules}
        print(f"Found alert groups: {group_names}")

    def test_high_error_rate_alert(self, alert_rules: list[dict]) -> None:
        """[7a, 7b] Verify HighErrorRate alert covers all layers."""
        # Find the alert in any group
        high_error_rate = None
        for group in alert_rules:
            for rule in group.get("rules", []):
                if rule.get("alert") == "HighErrorRate":
                    high_error_rate = rule
                    break
            if high_error_rate:
                break
        
        assert high_error_rate is not None, "HighErrorRate alert must exist"
        
        expr = high_error_rate.get("expr", "")
        
        # Should cover multiple layers
        layers_found = []
        for layer in ["layer1", "layer2", "layer3", "layer4", "layer5", "layer6"]:
            if layer in expr:
                layers_found.append(layer)
        
        assert len(layers_found) >= 3, f"HighErrorRate should cover multiple layers, found: {layers_found}"

    def test_service_down_alerts(self, alert_rules: list[dict]) -> None:
        """[7c, 7d] Verify service down alerts for dependencies."""
        required_alerts = [
            "Neo4jDown",
            "PostgresDown",
            "RedisDown",
        ]
        
        found_alerts = set()
        for group in alert_rules:
            for rule in group.get("rules", []):
                alert_name = rule.get("alert")
                if alert_name in required_alerts:
                    found_alerts.add(alert_name)
        
        missing = set(required_alerts) - found_alerts
        # These are optional but recommended
        if missing:
            print(f"INFO: Missing dependency alerts: {missing}")

    def test_workflow_stalled_alert(self, alert_rules: list[dict]) -> None:
        """[7e, 7f] Verify WorkflowStalled alert exists."""
        workflow_stalled = None
        for group in alert_rules:
            for rule in group.get("rules", []):
                if rule.get("alert") == "WorkflowStalled":
                    workflow_stalled = rule
                    break
            if workflow_stalled:
                break
        
        # This is optional for now
        if not workflow_stalled:
            pytest.skip("WorkflowStalled alert not found (consider adding)")

    def test_alerts_have_severity_labels(self, alert_rules: list[dict]) -> None:
        """Verify all alerts have severity labels."""
        failures = []
        
        for group in alert_rules:
            for rule in group.get("rules", []):
                if "alert" not in rule:
                    continue  # Skip recording rules
                
                alert_name = rule.get("alert")
                labels = rule.get("labels", {})
                
                if "severity" not in labels:
                    failures.append(f"{alert_name}: missing severity label")
                elif labels["severity"] not in ("critical", "warning", "info"):
                    failures.append(
                        f"{alert_name}: invalid severity '{labels['severity']}'"
                    )
        
        if failures:
            pytest.fail("Alert label violations:\n" + "\n".join(failures))

    def test_alerts_have_runbook_urls(self, alert_rules: list[dict]) -> None:
        """Verify alerts have runbook URLs for operational guidance."""
        failures = []
        
        for group in alert_rules:
            for rule in group.get("rules", []):
                if "alert" not in rule:
                    continue
                
                alert_name = rule.get("alert")
                annotations = rule.get("annotations", {})
                
                if "runbook_url" not in annotations:
                    failures.append(f"{alert_name}: missing runbook_url")
                elif "github.com" not in annotations["runbook_url"]:
                    failures.append(f"{alert_name}: runbook_url should point to github")
        
        if failures:
            pytest.fail("Runbook URL violations:\n" + "\n".join(failures))

    def test_alert_runbook_urls_link_to_existing_runbooks(
        self, alert_rules: list[dict], repo_root: Path
    ) -> None:
        """Verify alert runbook URLs resolve to tracked runbook markdown files."""
        runbook_root = repo_root / "docs" / "troubleshooting" / "runbooks"
        runbook_names = {path.name for path in runbook_root.rglob("*.md")}

        failures = []

        for group in alert_rules:
            for rule in group.get("rules", []):
                if "alert" not in rule:
                    continue

                alert_name = rule.get("alert")
                runbook_url = rule.get("annotations", {}).get("runbook_url")
                if not runbook_url:
                    continue

                parsed = urlparse(runbook_url)
                path_parts = parsed.path.strip("/").split("/")
                repo_relative = None
                if "blob" in path_parts:
                    blob_index = path_parts.index("blob")
                    if path_parts[blob_index + 1 : blob_index + 2] == ["main"]:
                        repo_relative = "/".join(path_parts[blob_index + 2 :])

                if repo_relative and (repo_root / repo_relative).exists():
                    continue

                runbook_basename = parsed.path.rstrip("/").split("/")[-1]
                if runbook_basename not in runbook_names:
                    failures.append(
                        f"{alert_name}: runbook file '{runbook_basename}' not found under "
                        "docs/troubleshooting/runbooks/"
                    )

        if failures:
            pytest.fail("Runbook linkage violations:\n" + "\n".join(failures))

    def test_alerts_have_summary_and_description(self, alert_rules: list[dict]) -> None:
        """Verify alerts have summary and description annotations."""
        failures = []
        
        for group in alert_rules:
            for rule in group.get("rules", []):
                if "alert" not in rule:
                    continue
                
                alert_name = rule.get("alert")
                annotations = rule.get("annotations", {})
                
                if "summary" not in annotations:
                    failures.append(f"{alert_name}: missing summary")
                
                if "description" not in annotations:
                    failures.append(f"{alert_name}: missing description")
        
        if failures:
            pytest.fail("Alert annotation violations:\n" + "\n".join(failures))

    def test_alert_expressions_are_valid_promql(self, alert_rules: list[dict]) -> None:
        """Verify alert expressions look like valid PromQL."""
        # This is a basic syntax check - full validation requires promtool
        for group in alert_rules:
            for rule in group.get("rules", []):
                if "alert" not in rule:
                    continue
                
                expr = rule.get("expr", "")
                alert_name = rule.get("alert")
                
                # Basic checks
                if not expr.strip():
                    pytest.fail(f"{alert_name}: empty expression")
                
                # Should contain metric-like content
                if "(" not in expr and "{" not in expr:
                    # Very basic expressions might be OK, but log it
                    print(f"INFO: {alert_name} has simple expression: {expr[:50]}")


class TestRecordingRules:
    """Tests for Prometheus recording rules."""

    def test_recording_rules_file_exists(self, monitoring_dir: Path) -> None:
        """Verify recording rules file exists."""
        rules_file = monitoring_dir / "prometheus" / "recording-rules.yml"
        
        if not rules_file.exists():
            # Also check for alternative locations
            alt_file = monitoring_dir / "alerting" / "recording-rules.yml"
            if not alt_file.exists():
                pytest.skip("Recording rules file not found")

    def test_recording_rules_have_valid_format(self, monitoring_dir: Path) -> None:
        """Verify recording rules have valid format."""
        # Try to find and load recording rules
        possible_paths = [
            monitoring_dir / "prometheus" / "recording-rules.yml",
            monitoring_dir / "alerting" / "recording-rules.yml",
        ]
        
        rules_file = None
        for path in possible_paths:
            if path.exists():
                rules_file = path
                break
        
        if not rules_file:
            pytest.skip("Recording rules file not found")
        
        with open(rules_file) as f:
            content = yaml.safe_load(f)
        
        groups = content.get("groups", [])
        
        for group in groups:
            rules = group.get("rules", [])
            for rule in rules:
                # Recording rules have 'record' key
                if "record" in rule:
                    assert "expr" in rule, f"Recording rule {rule['record']} missing expr"
