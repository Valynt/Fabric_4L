"""
AuditOrchestrator — Autonomous repository health auditing agent.

Fabric_4L Layer 4 agent that runs repository audits on schedule or via
trigger, persists findings, tracks remediation progress across sprints,
and feeds results back into the governance system.

Data Models
-----------
- ``AuditConfig`` — Runtime configuration
- ``AuditRun`` — Single audit execution
- ``Finding`` — Audit finding with evidence and remediation guidance
- ``Scorecard`` — Full repository scorecard with area breakdowns
- ``AreaScore`` — Score for a single audit area
- ``Sprint`` — Remediation sprint in the audit plan

Enums
-----
- ``Severity`` — CRITICAL, HIGH, MEDIUM, LOW
- ``Confidence`` — HIGH, MEDIUM, LOW
- ``AuditArea`` — A-J audit areas with weights
- ``SprintStatus`` — PLANNED, IN_PROGRESS, COMPLETED, DEFERRED
- ``FindingStatus`` — OPEN, IN_PROGRESS, RESOLVED, DEFERRED, WAIVED
"""

from __future__ import annotations

from .config import (
    DEFAULT_YAML_PATH,
    ENV_PREFIX,
    ConfigManager,
)
from .graph import (
    AuditState,
    create_audit_graph,
    run_audit,
    run_audit_async,
)
from .models import (
    DEFAULT_AREA_WEIGHTS,
    DEFAULT_AREAS_ENABLED,
    DEFAULT_GRADE_THRESHOLDS,
    AreaScore,
    AuditArea,
    AuditConfig,
    AuditRun,
    AuditRunDetail,
    AuditRunResponse,
    AuditRunSummary,
    AuditTriggerRequest,
    Confidence,
    Finding,
    FindingStatus,
    FindingUpdate,
    ReportFormat,
    Scorecard,
    ScoreHistory,
    ScoreHistoryEntry,
    Severity,
    Sprint,
    SprintStatus,
    confidence_multiplier,
    severity_deduction,
)
from .scoring import (
    GRADE_THRESHOLDS,
    build_scorecard,
    calculate_area_score,
    calculate_overall_score,
    detect_trend,
    detect_trend_with_variance,
    grade_to_index,
    score_to_grade,
)

__all__ = [
    # Enums
    "Severity",
    "Confidence",
    "AuditArea",
    "SprintStatus",
    "FindingStatus",
    "ReportFormat",
    # Data models
    "AuditConfig",
    "AuditRun",
    "Finding",
    "Scorecard",
    "AreaScore",
    "Sprint",
    # API models
    "AuditTriggerRequest",
    "AuditRunResponse",
    "AuditRunDetail",
    "AuditRunSummary",
    "ScoreHistory",
    "ScoreHistoryEntry",
    "FindingUpdate",
    # Constants
    "DEFAULT_AREA_WEIGHTS",
    "DEFAULT_GRADE_THRESHOLDS",
    "DEFAULT_AREAS_ENABLED",
    # Config
    "ConfigManager",
    "ENV_PREFIX",
    "DEFAULT_YAML_PATH",
    # Graph
    "AuditState",
    "create_audit_graph",
    "run_audit",
    "run_audit_async",
    # Scoring
    "GRADE_THRESHOLDS",
    "score_to_grade",
    "grade_to_index",
    "calculate_overall_score",
    "calculate_area_score",
    "detect_trend",
    "detect_trend_with_variance",
    "build_scorecard",
    # Helpers
    "severity_deduction",
    "confidence_multiplier",
]
