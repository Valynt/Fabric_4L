from __future__ import annotations

from scripts.ci import check_production_alert_metadata as checker


def test_production_alert_metadata_gate_passes_current_rules() -> None:
    assert checker.main() == 0


def test_production_alert_runbook_urls_do_not_use_internal_hosts() -> None:
    violations: list[str] = []
    for rule_file in checker.RULE_FILES:
        text = rule_file.read_text(encoding="utf-8")
        for banned_host in checker.BANNED_RUNBOOK_HOSTS:
            if banned_host in text:
                violations.append(f"{rule_file.relative_to(checker.REPO_ROOT)} contains {banned_host}")

    assert violations == []


def test_inconsistent_tenant_context_alert_is_active() -> None:
    rule_text = (checker.REPO_ROOT / "monitoring/alerting/layer-sli-rules-production.yml").read_text(
        encoding="utf-8"
    )

    assert "alert: InconsistentTenantContextAccess" in rule_text
    assert "tenant_context_inconsistent_access_total" in rule_text
    assert "tenant-isolation-context-access.md" in rule_text
