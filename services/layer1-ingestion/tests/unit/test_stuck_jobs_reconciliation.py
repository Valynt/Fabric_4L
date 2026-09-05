from pathlib import Path


def test_stuck_jobs_reconciliation_is_scheduled() -> None:
    source_root = Path(__file__).parents[2] / "src" / "layer1_ingestion"
    bootstrap = (source_root / "shared" / "tasks" / "tasks_bootstrap.py").read_text()
    reconciliation = (source_root / "shared" / "tasks" / "cleanup.py").read_text()

    assert '"reconcile-stuck-jobs-metrics"' in bootstrap
    assert '"layer1_ingestion.shared.tasks.reconcile_stuck_jobs_metrics"' in bootstrap
    assert "metrics.refresh_stuck_jobs(counts_by_stage)" in reconciliation
