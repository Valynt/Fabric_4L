"""
Core Pydantic models for the AuditOrchestrator agent.

This module defines all data models used throughout the audit pipeline,
including enums, findings, scorecards, sprints, audit runs, configuration,
and API request/response models. These models serve as the contract between
all components of the audit system.

All models use Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from datetime import UTC, datetime
from enum import Enum
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Repository URL and Transport Validation
# ---------------------------------------------------------------------------

_APPROVED_SCHEMES: frozenset[str] = frozenset({"https", "http", "ssh", "git"})
_DISALLOWED_PREFIXES: tuple[str, ...] = (
    "file://",
    "file:",
    "ext::",
    "fd::",
    "ftp://",
    "ftps://",
    "gopher://",
    "dict://",
    "data:",
    "javascript:",
    "vbscript:",
    "ldap://",
    "ldaps://",
)

_DISALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",  # nosec B104 -- denylisted SSRF target, not a bind address
        "169.254.169.254",
        "::1",
        "[::1]",
        "localhost.localdomain",
        "metadata.google.internal",
        "instance-data",
    }
)
_SSH_SCP_PATTERN = re.compile(
    r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.\-]+:[a-zA-Z0-9._/\-]+(?:\.git)?$"
)

# Reject path traversal components or suspicious control/shell characters
_DANGEROUS_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f;`$&|<>\s\"']")


def _validate_hostname(hostname: str) -> None:
    """Validate that a hostname/IP is not private, loopback, link-local, or reserved."""
    clean_host = hostname.strip("[]").lower()
    if not clean_host:
        raise ValueError("Repository URL must include a valid hostname")

    if not re.match(r"^[a-zA-Z0-9.\-]+$", clean_host):
        raise ValueError(f"Invalid hostname in repository URL: {hostname}")

    if clean_host in _DISALLOWED_HOSTS:
        raise ValueError(f"Disallowed hostname or loopback/metadata host in repository URL: {hostname}")

    if clean_host.endswith((".localhost", ".local", ".internal", ".lan", ".arpa", ".localdomain")):
        raise ValueError(f"Disallowed private or internal domain in repository URL: {hostname}")

    # Check if the hostname is a literal IP address
    try:
        ip = ipaddress.ip_address(clean_host)
    except ValueError:
        # Not a literal IP address; proceed to DNS resolution
        ip = None

    if ip is not None:
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or not ip.is_global
        ):
            raise ValueError(f"Disallowed private, loopback, or non-global IP address in repository URL: {hostname}")
        return

    # Validate resolved IPs if DNS resolution succeeds
    try:
        addr_info = socket.getaddrinfo(clean_host, None)
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            try:
                resolved_ip = ipaddress.ip_address(ip_str)
            except ValueError:
                # Skip unparseable address format returned from getaddrinfo
                continue

            if (
                resolved_ip.is_loopback
                or resolved_ip.is_private
                or resolved_ip.is_link_local
                or resolved_ip.is_multicast
                or resolved_ip.is_reserved
                or resolved_ip.is_unspecified
                or not resolved_ip.is_global
            ):
                raise ValueError(f"Repository hostname '{hostname}' resolves to disallowed address {resolved_ip}")
    except (socket.gaierror, socket.herror, OSError):
        # Ignore DNS resolution failures during offline or transient environments
        pass


def validate_repo_url(url: str) -> str:
    r"""Validate that a repository URL uses an approved Git transport and target.

    Permits:
    - Standard URLs with approved schemes (https://, http://, ssh://, git://)
      and valid hostname and repository path.
    - Standard SCP-style SSH Git URLs (e.g. git@github.com:owner/repo.git).

    Rejects:
    - Arbitrary local paths (/, /etc, C:\, relative paths with ..).
    - file:// schemes and local file URIs.
    - Unsupported or dangerous Git custom transports (ext::, fd::, ftp://, etc.).
    - Path traversal sequences (..) and shell injection characters.

    Args:
        url: The repository URL to validate.

    Returns:
        The validated, stripped repository URL.

    Raises:
        ValueError: If the URL is invalid or uses an unapproved scheme/format.
    """
    if not isinstance(url, str):
        raise ValueError("Repository URL must be a string")

    stripped = url.strip()
    if not stripped:
        raise ValueError("Repository URL cannot be empty")

    if _DANGEROUS_CHARS_PATTERN.search(stripped):
        raise ValueError("Repository URL contains invalid control or shell characters")

    lower = stripped.lower()

    # Check disallowed protocol prefixes
    for prefix in _DISALLOWED_PREFIXES:
        if lower.startswith(prefix):
            raise ValueError(
                f"Disallowed repository URL scheme or protocol: {prefix.rstrip(':/')}"
            )

    # Check local path indicators
    if (
        stripped.startswith(("/", "\\", "."))
        or re.match(r"^[a-zA-Z]:", stripped)
        or re.match(r"^\\\\", stripped)
    ):
        raise ValueError(
            "Local filesystem paths are not permitted as repository URLs for API/webhook requests"
        )

    # Check path traversal
    normalized_for_traversal = stripped.replace("\\", "/")
    path_parts = normalized_for_traversal.split("/")
    if ".." in path_parts:
        raise ValueError("Repository URL cannot contain path traversal sequences ('..')")
    if "/../" in stripped or "\\..\\" in stripped or "/..\\" in stripped or "\\../" in stripped:
        raise ValueError("Repository URL cannot contain path traversal sequences ('..')")

    # Check SSH SCP pattern
    if "@" in stripped and ":" in stripped and not stripped.startswith(("http://", "https://", "ssh://", "git://")):
        if _SSH_SCP_PATTERN.match(stripped):
            user_host, path_part = stripped.split(":", 1)
            if "@" in user_host:
                _, host_part = user_host.split("@", 1)
            else:
                host_part = user_host
            if not host_part or not path_part or ".." in path_part:
                raise ValueError("Invalid SSH Git repository format")
            _validate_hostname(host_part)
            return stripped
        raise ValueError(
            "Invalid SSH Git URL format. Expected format: user@host:path/to/repo.git"
        )

    # Check standard URL
    try:
        parsed = urlparse(stripped)
    except Exception as exc:
        raise ValueError(f"Failed to parse repository URL: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if not scheme:
        raise ValueError(
            "Missing repository URL scheme (e.g., https://github.com/owner/repo.git)"
        )

    if scheme not in _APPROVED_SCHEMES:
        raise ValueError(
            f"Unsupported repository URL scheme '{scheme}'. Approved schemes are: {', '.join(sorted(_APPROVED_SCHEMES))}"
        )

    hostname = (parsed.hostname or "").lower()
    _validate_hostname(hostname)

    path = parsed.path
    if not path or path == "/" or not path.strip("/"):
        raise ValueError("Repository URL must include a repository path")

    path_segments = path.strip("/").split("/")
    if ".." in path_segments:
        raise ValueError("Repository URL path cannot contain traversal segments")

    return stripped

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Severity level of an audit finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(str, Enum):
    """Confidence level in a finding or score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuditArea(str, Enum):
    """Audit area categories with their descriptions and default weights."""

    ARCHITECTURE = "A: Architecture and Code Structure"           # 12%
    CODE_QUALITY = "B: Code Quality and Maintainability"           # 12%
    CORRECTNESS = "C: Correctness, Data Integrity, Contracts"      # 14%
    TESTING = "D: Testing and Verification"                        # 14%
    SECURITY = "E: Security and Supply Chain"                      # 16%
    CICD = "F: CI/CD and Quality Gates"                            # 10%
    RELIABILITY = "G: Reliability, Observability, Operations"       # 8%
    DOCUMENTATION = "H: Documentation, Decisions, Knowledge"        # 6%
    AGENT_READINESS = "I: AI-Agent Readiness, Rules, Skills"       # 5%
    DEV_EXPERIENCE = "J: Developer Experience and Velocity"        # 3%


class SprintStatus(str, Enum):
    """Status of a remediation sprint."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"


class FindingStatus(str, Enum):
    """Lifecycle status of an audit finding."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    WAIVED = "waived"


class ReportFormat(str, Enum):
    """Output format for audit reports."""

    MARKDOWN = "markdown"
    JSON = "json"


# ---------------------------------------------------------------------------
# Severity / Confidence numeric helpers
# ---------------------------------------------------------------------------

_SEVERITY_DEDUCTIONS: dict[Severity, int] = {
    Severity.CRITICAL: -8,
    Severity.HIGH: -5,
    Severity.MEDIUM: -3,
    Severity.LOW: -1,
}

_CONFIDENCE_MULTIPLIERS: dict[Confidence, float] = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.8,
    Confidence.LOW: 0.5,
}


def severity_deduction(severity: Severity) -> int:
    """Return the score deduction for a given severity level.

    Args:
        severity: The severity level of a finding.

    Returns:
        The numeric deduction (negative integer).
    """
    return _SEVERITY_DEDUCTIONS.get(severity, -1)


def confidence_multiplier(confidence: Confidence) -> float:
    """Return the confidence multiplier for scoring.

    Args:
        confidence: The confidence level of a finding or score.

    Returns:
        The multiplier as a float (0.5–1.0).
    """
    return _CONFIDENCE_MULTIPLIERS.get(confidence, 0.5)


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A single audit finding representing an issue discovered during analysis.

    Findings are the primary output of analyzers and are tracked across audit
    runs to support incremental auditing and remediation sprints.
    """

    id: str = Field(
        ...,
        description="Unique finding identifier, e.g., 'COR-001', 'ARCH-002'",
        examples=["COR-001", "ARCH-002"],
    )
    severity: Severity = Field(
        ...,
        description="Severity level of the finding",
    )
    confidence: Confidence = Field(
        ...,
        description="Confidence level in the finding's accuracy",
    )
    area: AuditArea = Field(
        ...,
        description="Audit area this finding belongs to",
    )
    evidence: str = Field(
        ...,
        description="File path and line numbers where the issue was found",
        examples=["src/app.py:42-56"],
    )
    observed_fact: str = Field(
        ...,
        description="Description of what was observed during analysis",
    )
    inference_risk: str = Field(
        ...,
        description="Explanation of why the finding matters and what it implies",
    )
    business_impact: str = Field(
        ...,
        description="Business impact if the issue is not addressed",
    )
    recommended_fix: str = Field(
        ...,
        description="Recommended remediation approach",
    )
    effort: str = Field(
        ...,
        description="Estimated effort to fix: XS, S, M, L, XL",
        pattern=r"^(XS|S|M|L|XL)$",
    )
    risk_of_change: str = Field(
        ...,
        description="Risk associated with implementing the fix: Low, Medium, High",
    )
    owner: str = Field(
        ...,
        description="Team or individual responsible for remediation",
    )
    target_sprint: int = Field(
        default=0,
        ge=0,
        le=8,
        description="Target sprint number (1-8, 0 = backlog)",
    )
    status: FindingStatus = Field(
        default=FindingStatus.OPEN,
        description="Current lifecycle status of the finding",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the finding was first created",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="Timestamp when the finding was resolved",
    )
    resolution_note: str | None = Field(
        default=None,
        description="Notes explaining how the finding was resolved",
    )

    # --- Incremental audit tracking ---
    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the finding was first observed across any run",
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the finding was most recently observed",
    )
    times_seen: int = Field(
        default=1,
        ge=1,
        description="Number of audit runs in which this finding has been observed",
    )

    # --- Source data for re-analysis ---
    analyzer_type: str = Field(
        ...,
        description="Type of analyzer that produced this finding: git, code, doc",
    )
    check_command: str | None = Field(
        default=None,
        description="Shell command used to detect this finding",
    )
    check_output: str | None = Field(
        default=None,
        description="Raw command output that led to this finding",
    )

    # --- Tenant isolation ---
    tenant_id: str | None = Field(
        default=None,
        description="Tenant that owns this finding",
    )

    def mark_seen(self) -> None:
        """Update last_seen_at and increment times_seen for a new observation."""
        self.last_seen_at = datetime.now(UTC)
        self.times_seen += 1

    def mark_resolved(self, note: str | None = None) -> None:
        """Mark the finding as resolved with an optional note.

        Args:
            note: Optional resolution note explaining how it was fixed.
        """
        self.status = FindingStatus.RESOLVED
        self.resolved_at = datetime.now(UTC)
        if note:
            self.resolution_note = note


class AreaScore(BaseModel):
    """Score for a single audit area within a scorecard.

    Represents the computed score, grade, and metadata for one of the ten
    audit areas defined in :class:`AuditArea`.
    """

    area: AuditArea = Field(
        ...,
        description="The audit area being scored",
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight of this area in overall score calculation, e.g., 0.12 for 12%",
    )
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Calculated score for this area (0-100)",
    )
    grade: str = Field(
        ...,
        description="Letter grade with +/-, e.g., 'A+', 'B-', 'C'",
    )
    confidence: Confidence = Field(
        ...,
        description="Confidence level in this area score",
    )
    trend_risk: str = Field(
        ...,
        description="Trend assessment: Stable, Improving, or Worsening",
    )
    diagnosis: str = Field(
        ...,
        description="One-line diagnosis summarizing the area's health",
    )
    findings_count: int = Field(
        default=0,
        ge=0,
        description="Number of findings in this area",
    )


class GitMetricCompleteness(BaseModel):
    """Completeness metadata for one git-derived metric.

    Lets consumers distinguish an exact figure from one derived from a
    timed-out, truncated, or failed git collection. Never contains raw git
    output or contributor email addresses.
    """

    source: str = Field(
        ...,
        description="Name of the git command/metric this entry describes",
    )
    status: str = Field(
        ...,
        description="Collection status: ok, error, timeout, truncated, or unavailable",
    )
    truncated: bool = Field(
        ...,
        description="True when output was cut short (timeout or a cap), so the derived count is an undercount",
    )
    complete: bool = Field(
        ...,
        description="True when the metric was collected exactly (status ok and not truncated)",
    )
    bytes_read: int = Field(
        ...,
        ge=0,
        description="Number of stdout bytes buffered for this command",
    )
    max_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Maximum stdout bytes permitted for this command, if capped",
    )
    max_lines: int | None = Field(
        default=None,
        ge=0,
        description="Maximum stdout lines permitted for this command, if capped",
    )


class GitWarning(BaseModel):
    """Structured warning raised when a git command was incomplete.

    Contains only the metric name, status, message, and byte counts - never
    raw git output or contributor email addresses.
    """

    code: str = Field(
        ...,
        description="Stable warning code, e.g., GIT_CMD_TIMEOUT",
    )
    metric: str = Field(
        ...,
        description=(
            "Git command key this warning applies to (e.g. 'commits', "
            "'contributors'); matches git_metric_completeness source entries."
        ),
    )
    status: str = Field(
        ...,
        description="Collection status that triggered the warning",
    )
    message: str = Field(
        ...,
        description="Human-readable warning message (safe; no raw git output)",
    )
    bytes_read: int = Field(
        ...,
        ge=0,
        description="Number of stdout bytes read for the affected command",
    )
    max_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Maximum bytes permitted for the affected command, if capped",
    )
    max_lines: int | None = Field(
        default=None,
        ge=0,
        description="Maximum lines permitted for the affected command, if capped",
    )


class Scorecard(BaseModel):
    """Full repository scorecard summarizing the health of a codebase.

    A scorecard aggregates area scores, overall metrics, and all findings
    from a single audit run. It serves as the primary output of the audit
    pipeline.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique scorecard identifier (UUID)",
    )
    repo_name: str = Field(
        ...,
        description="Repository name, e.g., 'bmsull560/Fabric_4L'",
    )
    branch: str = Field(
        default="main",
        description="Git branch that was audited",
    )
    commit_sha: str | None = Field(
        default=None,
        description="Git commit SHA at the time of audit",
    )
    version: str | None = Field(
        default=None,
        description="Semantic version of the codebase, if tagged",
    )
    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Weighted overall score (0-100)",
    )
    overall_grade: str = Field(
        ...,
        description="Overall letter grade, e.g., 'A+', 'B-', 'C'",
    )
    confidence: Confidence = Field(
        ...,
        description="Overall confidence in the scorecard",
    )
    trend: str = Field(
        ...,
        description="Overall trend: Improving, Stable, or Declining",
    )
    area_scores: list[AreaScore] = Field(
        ...,
        description="Scores for each of the ten audit areas",
    )
    total_files: int = Field(
        default=0,
        ge=0,
        description="Total number of files in the repository",
    )
    total_directories: int = Field(
        default=0,
        ge=0,
        description="Total number of directories in the repository",
    )
    total_commits: int = Field(
        default=0,
        ge=0,
        description="Total number of commits analyzed",
    )
    total_contributors: int = Field(
        default=0,
        ge=0,
        description="Total number of unique contributors",
    )
    git_metric_completeness: dict[str, GitMetricCompleteness] = Field(
        default_factory=dict,
        description=(
            "Per-metric git collection status (status, truncated, complete, "
            "bytes_read) so consumers can distinguish an exact figure from a "
            "timed-out, truncated or failed one. Empty when git is unavailable."
        ),
    )
    git_warnings: list[GitWarning] = Field(
        default_factory=list,
        description=(
            "Structured warnings (code, metric, status, message) raised when a "
            "git command timed out, was truncated, or failed. Contains no raw "
            "git output or email addresses."
        ),
    )
    audit_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the audit was completed",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="All findings from the audit",
    )
    executive_summary: str | None = Field(
        default=None,
        description="Executive summary of the audit results",
    )

    # --- Tenant isolation ---
    tenant_id: str | None = Field(
        default=None,
        description="Tenant that owns this scorecard",
    )

    @field_validator("area_scores")
    @classmethod
    def _validate_area_scores(cls, v: list[AreaScore]) -> list[AreaScore]:
        """Validate area scores.

        When ``area_scores`` is non-empty it must contain exactly one score
        for each of the ten :class:`AuditArea` members and the weights must
        sum to 1.0 within tolerance. An empty list is explicitly permitted.
        """
        if not v:
            return v
        seen = {a.area for a in v}
        expected = set(AuditArea)
        missing = expected - seen
        if missing:
            raise ValueError(f"Missing area scores for: {sorted(missing)}")
        total_weight = sum(a.weight for a in v)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Area weights must sum to 1.0, got {total_weight:.4f}")
        return v

    def get_area_score(self, area: AuditArea) -> AreaScore | None:
        """Get the score for a specific audit area.

        Args:
            area: The audit area to look up.

        Returns:
            The :class:`AreaScore` for the given area, or ``None`` if not found.
        """
        for a in self.area_scores:
            if a.area == area:
                return a
        return None

    def open_findings(self) -> list[Finding]:
        """Return all findings that are not resolved or waived.

        Returns:
            List of open or in-progress findings.
        """
        return [
            f for f in self.findings
            if f.status in (FindingStatus.OPEN, FindingStatus.IN_PROGRESS)
        ]

    def findings_by_severity(self, severity: Severity) -> list[Finding]:
        """Return findings filtered by severity level.

        Args:
            severity: The severity level to filter by.

        Returns:
            List of findings with the given severity.
        """
        return [f for f in self.findings if f.severity == severity]


class Sprint(BaseModel):
    """A remediation sprint from the audit roadmap.

    Sprints group findings into time-boxed remediation periods with
    defined themes, objectives, and deliverables.
    """

    id: int = Field(
        ...,
        ge=1,
        le=8,
        description="Sprint number (1-8)",
    )
    theme: str = Field(
        ...,
        description="High-level theme or focus area for the sprint",
    )
    objectives: list[str] = Field(
        ...,
        description="List of sprint objectives",
    )
    deliverables: list[str] = Field(
        ...,
        description="List of expected deliverables",
    )
    findings_targeted: list[str] = Field(
        ...,
        description="Finding IDs targeted for remediation in this sprint",
    )
    status: SprintStatus = Field(
        default=SprintStatus.PLANNED,
        description="Current status of the sprint",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when the sprint started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the sprint was completed",
    )
    actual_effort_days: float | None = Field(
        default=None,
        ge=0,
        description="Actual effort in days spent on the sprint",
    )
    score_impact_projected: int = Field(
        default=0,
        description="Projected score impact from completing this sprint",
    )
    score_impact_actual: int | None = Field(
        default=None,
        description="Actual score impact after sprint completion",
    )

    # --- Tenant isolation ---
    tenant_id: str | None = Field(
        default=None,
        description="Tenant that owns this sprint",
    )

    def start(self) -> None:
        """Mark the sprint as started."""
        self.status = SprintStatus.IN_PROGRESS
        self.started_at = datetime.now(UTC)

    def complete(self, actual_score_impact: int | None = None) -> None:
        """Mark the sprint as completed.

        Args:
            actual_score_impact: The actual score impact observed.
        """
        self.status = SprintStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        if actual_score_impact is not None:
            self.score_impact_actual = actual_score_impact


class AuditRun(BaseModel):
    """A single audit execution tracking the full lifecycle of an audit.

    Audit runs capture metadata about when and how an audit was triggered,
    its current status, and references to generated outputs like scorecards
    and reports. They also support incremental auditing by tracking the
    previous run and changed files.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique audit run identifier (UUID)",
    )
    status: str = Field(
        ...,
        description="Run status: pending, running, completed, or failed",
    )
    trigger_type: str = Field(
        ...,
        description="Trigger source: scheduled, manual, webhook, or post_merge",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the run started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the run completed",
    )
    repo_path: str = Field(
        ...,
        description="Filesystem path to the cloned repository",
    )
    scorecard: Scorecard | None = Field(
        default=None,
        description="Generated scorecard (available after scoring phase)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the run failed",
    )

    # --- Incremental tracking ---
    previous_run_id: str | None = Field(
        default=None,
        description="ID of the previous audit run for incremental tracking",
    )
    files_changed_since_last: list[str] = Field(
        default_factory=list,
        description="List of files changed since the previous run",
    )
    areas_reanalyzed: list[str] = Field(
        default_factory=list,
        description="Audit areas that were fully re-analyzed in this run",
    )

    # --- Tenant isolation ---
    tenant_id: str | None = Field(
        default=None,
        description="Tenant that owns this audit run",
    )

    def mark_completed(self, scorecard: Scorecard | None = None) -> None:
        """Mark the audit run as completed.

        Args:
            scorecard: The generated scorecard, if available.
        """
        self.status = "completed"
        self.completed_at = datetime.now(UTC)
        if scorecard:
            self.scorecard = scorecard

    def mark_failed(self, error_message: str) -> None:
        """Mark the audit run as failed with an error message.

        Args:
            error_message: Description of what caused the failure.
        """
        self.status = "failed"
        self.completed_at = datetime.now(UTC)
        self.error_message = error_message


# ---------------------------------------------------------------------------
# Default area weights (must sum to 1.0)
# ---------------------------------------------------------------------------

DEFAULT_AREA_WEIGHTS: dict[AuditArea, float] = {
    AuditArea.ARCHITECTURE: 0.12,
    AuditArea.CODE_QUALITY: 0.12,
    AuditArea.CORRECTNESS: 0.14,
    AuditArea.TESTING: 0.14,
    AuditArea.SECURITY: 0.16,
    AuditArea.CICD: 0.10,
    AuditArea.RELIABILITY: 0.08,
    AuditArea.DOCUMENTATION: 0.06,
    AuditArea.AGENT_READINESS: 0.05,
    AuditArea.DEV_EXPERIENCE: 0.03,
}

DEFAULT_GRADE_THRESHOLDS: dict[str, tuple[int, int]] = {
    "A+": (97, 100), "A": (93, 96), "A-": (90, 92),
    "B+": (87, 89), "B": (83, 86), "B-": (80, 82),
    "C+": (77, 79), "C": (73, 76), "C-": (70, 72),
    "D+": (67, 69), "D": (63, 66), "D-": (60, 62),
    "F": (0, 59),
}

DEFAULT_AREAS_ENABLED: list[AuditArea] = list(AuditArea)


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------

class AuditConfig(BaseModel):
    """Runtime configuration for the audit agent.

    Defines all tunable parameters for the audit pipeline, from repository
    settings and analysis scope to scoring weights and persistence options.

    Values can be overridden via environment variables (AUDIT__* prefix)
    or a YAML configuration file.
    """

    # --- Repository ---
    repo_url: str = Field(
        ...,
        description="URL of the git repository to audit",
    )
    repo_name: str = Field(
        ...,
        description="Human-readable repository name",
    )
    branch: str = Field(
        default="main",
        description="Git branch to audit",
    )
    clone_depth: int = Field(
        default=1,
        ge=0,
        description="Git clone depth (0 for full clone, ≥1 for shallow)",
    )
    trusted_source: bool = Field(
        default=False,
        description="Allow local filesystem paths as repository sources (CLI/internal execution only)",
    )
    allowed_repo_root: str | None = Field(
        default=None,
        description="Configured repository root for local path confinement",
    )

    # --- Analysis scope ---
    areas_enabled: list[AuditArea] = Field(
        default_factory=lambda: list(AuditArea),
        description="List of audit areas to enable",
    )
    severity_threshold: Severity = Field(
        default=Severity.LOW,
        description="Minimum severity level to report",
    )
    max_file_size_lines: int = Field(
        default=1500,
        ge=1,
        description="Flag files larger than this line count",
    )

    # --- Incremental audit ---
    incremental: bool = Field(
        default=True,
        description="Only re-analyze changed areas when True",
    )
    cache_dir: str = Field(
        default=".audit_cache",
        description="Directory for incremental audit cache",
    )

    # --- Scoring weights (must sum to 1.0) ---
    area_weights: dict[AuditArea, float] = Field(
        default_factory=lambda: DEFAULT_AREA_WEIGHTS.copy(),
        description="Weight for each audit area in overall score",
    )

    # --- Scoring rubric ---
    grade_thresholds: dict[str, tuple[int, int]] = Field(
        default_factory=lambda: DEFAULT_GRADE_THRESHOLDS.copy(),
        description="Score thresholds for letter grades",
    )

    # --- Sprint planning ---
    sprints_enabled: bool = Field(
        default=True,
        description="Enable sprint planning phase",
    )
    sprint_length_weeks: int = Field(
        default=2,
        ge=1,
        description="Length of each sprint in weeks",
    )
    team_size: int = Field(
        default=3,
        ge=1,
        description="Number of team members",
    )
    team_capacity_percent: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Percentage of team capacity allocated to remediation",
    )

    # --- Persistence ---
    postgres_dsn: str | None = Field(
        default=None,
        description="PostgreSQL connection DSN",
    )
    neo4j_uri: str | None = Field(
        default=None,
        description="Neo4j Bolt URI",
    )
    neo4j_user: str | None = Field(
        default=None,
        description="Neo4j username",
    )
    neo4j_password: str | None = Field(
        default=None,
        description="Neo4j password",
    )
    output_dir: str = Field(
        default="audit_reports",
        description="Directory for report output",
    )

    # --- Scheduling ---
    cron_schedule: str | None = Field(
        default="0 2 * * 0",
        description="Cron expression for scheduled runs (default: weekly Sunday 2AM)",
    )
    trigger_on_push: bool = Field(
        default=True,
        description="Trigger audit on git push events",
    )
    trigger_on_release: bool = Field(
        default=True,
        description="Trigger audit on release events",
    )

    # --- Tenant isolation ---
    tenant_id: str | None = Field(
        default=None,
        description="Tenant that owns this audit run",
    )

    @field_validator("area_weights")
    @classmethod
    def _validate_weights(cls, v: dict[AuditArea, float]) -> dict[AuditArea, float]:
        """Validate that area weights sum to 1.0 within tolerance."""
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Area weights must sum to 1.0, got {total:.4f}")
        return v

    @model_validator(mode="after")
    def _validate_repo_source(self) -> AuditConfig:
        """Validate repository URL format unless trusted local source mode is enabled."""
        if not self.trusted_source:
            validate_repo_url(self.repo_url)
        return self

    def get_area_weight(self, area: AuditArea) -> float:
        """Get the weight for a specific audit area.

        Args:
            area: The audit area to look up.

        Returns:
            The weight for the area, defaulting to 0.1 if not explicitly set.
        """
        return self.area_weights.get(area, 0.1)


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

class AuditTriggerRequest(BaseModel):
    """Request body for triggering a new audit run via the API.

    ``repo_url`` is required; remaining fields use configuration defaults when omitted.
    """

    repo_url: str = Field(
        description="Repository URL to audit (must be an approved Git URL scheme like https:// or ssh://).",
    )
    branch: str | None = Field(
        default=None,
        description="Branch to audit. Defaults to 'main'.",
    )
    incremental: bool | None = Field(
        default=None,
        description="Override incremental mode for this run.",
    )
    areas: list[AuditArea] | None = Field(
        default=None,
        description="List of areas to audit. Defaults to all enabled areas.",
    )
    trigger_type: str = Field(
        default="manual",
        description="Source of the trigger: manual, scheduled, webhook, post_merge",
    )

    @field_validator("repo_url")
    @classmethod
    def _validate_repo_url(cls, v: str) -> str:
        """Enforce strict repository URL format on API triggers."""
        if not v or not v.strip():
            raise ValueError("repo_url is required")
        return validate_repo_url(v.strip())


class AuditRunResponse(BaseModel):
    """Response returned immediately when an audit is triggered.

    Provides the run ID for polling and a message indicating the run
    has been accepted for processing.
    """

    run_id: str = Field(
        ...,
        description="Unique identifier for the accepted audit run",
    )
    status: str = Field(
        ...,
        description="Initial status: typically 'pending'",
    )
    message: str = Field(
        default="Audit run accepted and queued for processing.",
        description="Human-readable status message",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the run was accepted",
    )


class AuditRunDetail(BaseModel):
    """Detailed response for a single audit run including results.

    Returned by the GET /runs/{run_id} endpoint. Contains the full audit
    run record with its scorecard when available.
    """

    run_id: str = Field(..., description="Audit run identifier")
    status: str = Field(..., description="Current run status")
    trigger_type: str = Field(..., description="Trigger source")
    repo_name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Branch audited")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp"
    )
    overall_score: int | None = Field(
        default=None, ge=0, le=100, description="Overall score if completed"
    )
    overall_grade: str | None = Field(
        default=None, description="Overall grade if completed"
    )
    findings_count: int = Field(
        default=0, ge=0, description="Number of findings"
    )
    sprints_count: int = Field(
        default=0, ge=0, description="Number of planned sprints"
    )
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    areas_reanalyzed: list[str] = Field(
        default_factory=list, description="Areas re-analyzed (incremental)"
    )
    previous_run_id: str | None = Field(
        default=None, description="Previous run ID for incremental tracking"
    )


class AuditRunSummary(BaseModel):
    """Summary of an audit run for listing operations.

    A lightweight representation suitable for the GET /runs list endpoint.
    """

    run_id: str = Field(..., description="Audit run identifier")
    status: str = Field(..., description="Run status")
    trigger_type: str = Field(..., description="Trigger source")
    repo_name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Branch audited")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp"
    )
    overall_score: int | None = Field(
        default=None, ge=0, le=100, description="Overall score"
    )
    overall_grade: str | None = Field(
        default=None, description="Overall grade"
    )
    findings_count: int = Field(
        default=0, ge=0, description="Number of findings"
    )


class ScoreHistoryEntry(BaseModel):
    """A single score history entry.

    Represents a snapshot of a score at a specific point in time.
    """

    run_id: str = Field(..., description="Audit run identifier")
    score: int = Field(..., ge=0, le=100, description="Score at this point in time")
    grade: str = Field(..., description="Grade at this point in time")
    timestamp: datetime = Field(..., description="Timestamp of the score snapshot")
    findings_count: int = Field(
        default=0, ge=0, description="Number of findings at this time"
    )


class ScoreHistory(BaseModel):
    """Score history over time for trend analysis.

    Returned by the GET /scorecard/history endpoint. Supports filtering
    by audit area for area-specific trend charts.
    """

    repo_name: str = Field(..., description="Repository name")
    area: str | None = Field(
        default=None, description="Audit area filter (None for overall)"
    )
    entries: list[ScoreHistoryEntry] = Field(
        default_factory=list, description="Chronological score entries"
    )

    @property
    def latest_score(self) -> int | None:
        """Return the most recent score from the history.

        Returns:
            The latest score value, or ``None`` if no entries exist.
        """
        if not self.entries:
            return None
        return self.entries[-1].score

    @property
    def score_change(self) -> int | None:
        """Return the score change between first and latest entry.

        Returns:
            The absolute score change, or ``None`` if fewer than 2 entries.
        """
        if len(self.entries) < 2:
            return None
        return self.entries[-1].score - self.entries[0].score


class FindingUpdate(BaseModel):
    """Request body for updating a finding's status.

    Supports resolving, deferring, or re-opening findings with an
    optional explanatory note.
    """

    status: FindingStatus = Field(
        ...,
        description="New status for the finding",
    )
    resolution_note: str | None = Field(
        default=None,
        description="Optional note explaining the status change",
    )
    owner: str | None = Field(
        default=None,
        description="Optional reassignment of finding owner",
    )
    target_sprint: int | None = Field(
        default=None,
        ge=0,
        le=8,
        description="Optional sprint reassignment (0 = backlog)",
    )


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "Severity",
    "Confidence",
    "AuditArea",
    "SprintStatus",
    "FindingStatus",
    "ReportFormat",
    # Core models
    "Finding",
    "AreaScore",
    "Scorecard",
    "Sprint",
    "AuditRun",
    "AuditConfig",
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
    # Helpers
    "severity_deduction",
    "confidence_multiplier",
]
