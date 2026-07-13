"""Analyzer sub-package for the AuditOrchestrator agent."""

from __future__ import annotations

from .base import BaseAnalyzer
from .code_analyzer import CodeAnalyzer
from .doc_analyzer import DocAnalyzer
from .finding_catalog import FindingCatalog
from .git_analyzer import GitAnalyzer


def run_all_analyzers(
    repo_path: str,
    config,
) -> tuple[list, dict]:
    """Run all analyzers and return combined findings and metrics.

    Args:
        repo_path: Filesystem path to the repository root.
        config: Audit configuration (``AuditConfig`` instance).

    Returns:
        Tuple of ``(findings, metrics)`` where ``findings`` is a combined list
        and ``metrics`` aggregates per-analyzer metrics under ``by_analyzer``.
    """
    analyzers: list[BaseAnalyzer] = [
        GitAnalyzer(config),
        CodeAnalyzer(config),
        DocAnalyzer(config),
    ]

    all_findings: list = []
    metrics: dict = {"by_analyzer": {}}

    for analyzer in analyzers:
        findings, analyzer_metrics = analyzer.analyze(repo_path)
        all_findings.extend(findings)
        metrics["by_analyzer"][analyzer.name] = analyzer_metrics

    metrics["total_findings"] = len(all_findings)
    return all_findings, metrics


__all__ = [
    "BaseAnalyzer",
    "GitAnalyzer",
    "CodeAnalyzer",
    "DocAnalyzer",
    "FindingCatalog",
    "run_all_analyzers",
]
