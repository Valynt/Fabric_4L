"""Abstract base analyzer for the AuditOrchestrator agent.

Provides the shared interface and a helper for creating :class:`Finding`
instances with either stable catalog IDs or auto-incrementing IDs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import AuditArea, AuditConfig, Confidence, Finding, Severity


class BaseAnalyzer(ABC):
    """Abstract base class for all audit analyzers.

    Subclasses define their analyzer domain through :attr:`name` and
    :attr:`areas`, collect domain-specific metrics, and produce
    :class:`Finding` instances.
    """

    name: str = "base"
    areas: list[AuditArea] = []

    _id_counters: dict[str, int] = {}

    def __init__(self, config: AuditConfig) -> None:
        """Initialize the analyzer with runtime configuration.

        Args:
            config: Validated audit configuration.
        """
        self.config = config
        self.findings: list[Finding] = []
        self.metrics: dict[str, Any] = {}

    @abstractmethod
    def analyze(self, repo_path: str) -> tuple[list[Finding], dict[str, Any]]:
        """Run the analyzer against a repository.

        Args:
            repo_path: Filesystem path to the repository root.

        Returns:
            Tuple of discovered findings and collected metrics.
        """
        ...

    def create_finding(
        self,
        id_prefix: str,
        severity: Severity,
        confidence: Confidence,
        area: AuditArea,
        evidence: str,
        observed_fact: str,
        inference_risk: str,
        business_impact: str,
        recommended_fix: str,
        effort: str,
        risk_of_change: str,
        owner: str,
        target_sprint: int = 0,
        analyzer_type: str | None = None,
        check_command: str | None = None,
        check_output: str | None = None,
        finding_id: str | None = None,
    ) -> Finding:
        """Create a :class:`Finding` with an auto-incrementing or explicit ID.

        When ``finding_id`` is omitted the ID is generated from
        ``id_prefix`` using a running per-prefix counter
        (e.g. ``ARCH-001``, ``ARCH-002``).

        Args:
            id_prefix: Short uppercase prefix for auto-generated IDs.
            severity: Finding severity.
            confidence: Confidence in the finding.
            area: Audit area the finding belongs to.
            evidence: File path / line numbers where the issue was found.
            observed_fact: Description of what was observed.
            inference_risk: Why the finding matters.
            business_impact: Business impact if not fixed.
            recommended_fix: Recommended remediation.
            effort: Estimated effort (XS, S, M, L, XL).
            risk_of_change: Risk of applying the fix.
            owner: Responsible team or individual.
            target_sprint: Target sprint (0 = backlog).
            analyzer_type: Analyzer that produced the finding.
            check_command: Command used to detect the issue.
            check_output: Raw output leading to the finding.
            finding_id: Optional explicit finding ID.

        Returns:
            A validated ``Finding`` instance.
        """
        if finding_id is None:
            BaseAnalyzer._id_counters.setdefault(id_prefix, 0)
            BaseAnalyzer._id_counters[id_prefix] += 1
            finding_id = f"{id_prefix}-{BaseAnalyzer._id_counters[id_prefix]:03d}"

        return Finding(
            id=finding_id,
            severity=severity,
            confidence=confidence,
            area=area,
            evidence=evidence,
            observed_fact=observed_fact,
            inference_risk=inference_risk,
            business_impact=business_impact,
            recommended_fix=recommended_fix,
            effort=effort,
            risk_of_change=risk_of_change,
            owner=owner,
            target_sprint=target_sprint,
            analyzer_type=analyzer_type or self.name,
            check_command=check_command,
            check_output=check_output,
        )

    def reset(self) -> None:
        """Clear findings and metrics for a fresh run."""
        self.findings = []
        self.metrics = {}
