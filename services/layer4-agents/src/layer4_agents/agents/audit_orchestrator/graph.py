"""LangGraph state machine for the AuditOrchestrator agent.

Implements the audit pipeline as a compiled state graph with nodes for
repository cloning, parallel analysis, scoring, sprint planning, report
generation, persistence, and knowledge-graph updates.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, NotRequired, TypedDict, cast
from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .analyzers.code_analyzer import CodeAnalyzer
from .analyzers.doc_analyzer import DocAnalyzer
from .analyzers.git_analyzer import GitAnalyzer
from .models import (
    AuditArea,
    AuditConfig,
    AuditRun,
    Finding,
    FindingStatus,
    Scorecard,
    Sprint,
    SprintStatus,
    validate_repo_url,
)
from .persistence import PersistenceManager, update_knowledge_graph
from .reporter import generate_full_report
from .scoring import build_scorecard, severity_deduction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def _merge_findings(left: list[Finding], right: list[Finding]) -> list[Finding]:
    """Reducer that concatenates findings from parallel analyzer branches."""
    return left + right


class AuditState(TypedDict):
    """LangGraph state for the audit workflow."""

    # Input
    config: AuditConfig
    trigger_type: str
    previous_run_id: str | None

    # Execution tracking
    run_id: str
    status: str
    current_step: str
    started_at: datetime
    completed_at: datetime | None

    # Analysis results
    repo_path: str | None
    git_metrics: dict[str, Any] | None
    code_metrics: dict[str, Any] | None
    doc_metrics: dict[str, Any] | None
    findings: Annotated[list[Finding], _merge_findings]

    # Derived
    scorecard: Scorecard | None
    sprints: list[Sprint]
    report_path: str | None
    report_markdown: str | None

    # Incremental audit metadata
    commit_sha: NotRequired[str | None]
    files_changed_since_last: NotRequired[list[str]]
    areas_reanalyzed: NotRequired[list[str]]

    # Error handling
    error: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _effort_to_days(effort: str) -> float:
    """Map effort label to an approximate number of person-days."""
    mapping = {"XS": 0.5, "S": 1.0, "M": 3.0, "L": 5.0, "XL": 8.0}
    return mapping.get(effort.upper(), 1.0)


def _resolve_repo_path(config: AuditConfig) -> tuple[Path, str | None]:
    """Resolve a local repo path or clone a remote URL.

    Security Confinement Rules:
    - If `config.trusted_source` is True:
      - The `repo_url` is treated as a local filesystem path.
      - Canonicalize with `Path(repo_url).resolve()`.
      - Check against `config.allowed_repo_root` (or cwd if not specified).
      - Ensure `candidate.is_relative_to(allowed_root)` to prevent path traversal or symlink escapes.
      - Fail closed if the directory does not exist or escapes the allowed root.
    - If `config.trusted_source` is False (default for API / Webhook):
      - Local filesystem resolution is strictly forbidden.
      - Validate `repo_url` using `validate_repo_url(repo_url)`.
      - Clone remote git repository into `config.cache_dir`.
      - If clone fails, FAIL CLOSED by raising `RuntimeError` (do NOT fall back to cwd).

    Returns the resolved path and the current commit SHA (when available).
    """
    repo_url = config.repo_url

    if config.trusted_source:
        candidate = Path(repo_url).resolve()
        allowed_root = (
            Path(config.allowed_repo_root).resolve()
            if config.allowed_repo_root
            else Path.cwd().resolve()
        )
        if not candidate.is_relative_to(allowed_root):
            raise PermissionError(
                f"Local repository path '{repo_url}' (resolved: '{candidate}') escapes allowed repository root '{allowed_root}'."
            )
        if not candidate.exists() or not candidate.is_dir():
            raise FileNotFoundError(
                f"Local repository path '{candidate}' does not exist or is not a directory."
            )
        return candidate, _git_head(candidate)

    # config.trusted_source is False: must be a validated remote Git repository URL
    validate_repo_url(repo_url)

    # Treat repo_url as a git remote and clone into the cache directory.
    cache = Path(config.cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    safe_name = config.repo_name.replace("/", "__").replace("\\", "__")
    clone_target = cache / safe_name

    if clone_target.exists():
        shutil.rmtree(clone_target)

    depth_arg = ["--depth", str(config.clone_depth)] if config.clone_depth > 0 else []
    cmd = ["git", "clone", *depth_arg, "--branch", config.branch, repo_url, str(clone_target)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        logger.error("Git clone failed for '%s': %s", repo_url, exc)
        raise RuntimeError(f"Failed to clone repository from '{repo_url}': {exc}") from exc

    return clone_target, _git_head(clone_target)


def _git_head(repo_path: Path) -> str | None:
    """Return the current commit SHA for a git repository, if available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def _metrics_by_area(
    git_metrics: dict[str, Any] | None,
    code_metrics: dict[str, Any] | None,
    doc_metrics: dict[str, Any] | None,
) -> dict[AuditArea, dict[str, Any]]:
    """Distribute analyzer metrics to the audit areas they influence."""
    mapped: dict[AuditArea, dict[str, Any]] = {}

    if git_metrics:
        mapped[AuditArea.ARCHITECTURE] = dict(git_metrics)

    if code_metrics:
        for area in (
            AuditArea.CODE_QUALITY,
            AuditArea.CORRECTNESS,
            AuditArea.TESTING,
            AuditArea.SECURITY,
            AuditArea.CICD,
            AuditArea.RELIABILITY,
        ):
            mapped.setdefault(area, {}).update(code_metrics)

    if doc_metrics:
        for area in (
            AuditArea.DOCUMENTATION,
            AuditArea.AGENT_READINESS,
            AuditArea.DEV_EXPERIENCE,
        ):
            mapped.setdefault(area, {}).update(doc_metrics)

    return mapped


def _total_from_metrics(
    git_metrics: dict[str, Any] | None,
) -> tuple[int, int, int, int]:
    """Extract repository totals from git/structural metrics."""
    gm = git_metrics or {}
    return (
        int(gm.get("total_files", 0) or 0),
        int(gm.get("total_directories", 0) or 0),
        int(gm.get("total_commits", 0) or 0),
        int(gm.get("total_contributors", 0) or 0),
    )


def _plan_sprints_from_findings(
    findings: Sequence[Finding],
    config: AuditConfig,
) -> list[Sprint]:
    """Build a remediation sprint plan from open findings and team capacity."""
    if not config.sprints_enabled:
        return []

    open_findings = [
        f for f in findings if f.status in (FindingStatus.OPEN, FindingStatus.IN_PROGRESS)
    ]

    # Sort by severity then by effort so high-impact items are addressed first.
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_findings = sorted(
        open_findings,
        key=lambda f: (severity_order.get(f.severity.value, 99), _effort_to_days(f.effort)),
    )

    # Capacity in person-days per sprint.
    days_per_sprint = config.sprint_length_weeks * 5
    capacity = days_per_sprint * config.team_size * config.team_capacity_percent

    sprints: list[Sprint] = []
    remaining = list(sorted_findings)
    sprint_id = 1

    themes = [
        "Stabilize correctness and security",
        "Harden quality gates",
        "Improve architecture and reliability",
        "Close documentation and agent-readiness gaps",
        "Refine developer experience",
        "Pay down residual risk",
        "Consolidate improvements",
        "Verify and lock in gains",
    ]

    while remaining and sprint_id <= 8:
        used = 0.0
        targeted: list[str] = []
        objectives: list[str] = []
        deliverables: list[str] = []
        projected_impact = 0

        while remaining and used + _effort_to_days(remaining[0].effort) <= capacity:
            finding = remaining.pop(0)
            targeted.append(finding.id)
            used += _effort_to_days(finding.effort)
            objectives.append(f"Address {finding.id}: {finding.observed_fact}")
            deliverables.append(f"PR resolving {finding.id}")
            projected_impact += abs(severity_deduction(finding.severity))

        if not targeted:
            # Force at least one item per sprint so progress is visible.
            finding = remaining.pop(0)
            targeted.append(finding.id)
            objectives.append(f"Address {finding.id}: {finding.observed_fact}")
            deliverables.append(f"PR resolving {finding.id}")
            projected_impact += abs(severity_deduction(finding.severity))

        sprints.append(
            Sprint(
                id=sprint_id,
                theme=themes[(sprint_id - 1) % len(themes)],
                objectives=objectives,
                deliverables=deliverables,
                findings_targeted=targeted,
                status=SprintStatus.PLANNED,
                score_impact_projected=min(100, projected_impact),
            )
        )
        sprint_id += 1

    return sprints


def _write_report(
    run_id: str,
    report_markdown: str,
    output_dir: str,
) -> Path:
    """Write the Markdown report to disk and return its path."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"report_{run_id}.md"
    path.write_text(report_markdown, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def node_clone_repo(state: AuditState) -> dict[str, Any]:
    """Clone or update the repository and record the commit SHA."""
    try:
        repo_path, commit_sha = _resolve_repo_path(state["config"])
        return {
            "repo_path": str(repo_path),
            "commit_sha": commit_sha,
            "current_step": "clone",
            "status": "running",
        }
    except Exception as exc:  # pragma: no cover
        logger.exception("Repository clone/setup failed")
        return {"error": f"clone failed: {exc}", "current_step": "clone"}


async def node_analyze_git(state: AuditState) -> dict[str, Any]:
    """Run the git/structural analyzer."""
    config = state["config"]
    repo_path = state.get("repo_path")
    if repo_path is None:
        return {"error": "no repo_path available for git analysis"}

    try:
        analyzer = GitAnalyzer(config)
        findings, metrics = await asyncio.to_thread(analyzer.analyze, repo_path)
        return {
            "git_metrics": metrics,
            "findings": findings,
            "current_step": "analyze_git",
        }
    except Exception as exc:
        logger.exception("Git analyzer failed")
        return {"error": f"git analyzer failed: {exc}", "current_step": "analyze_git"}


async def node_analyze_code(state: AuditState) -> dict[str, Any]:
    """Run the static code analyzer."""
    config = state["config"]
    repo_path = state.get("repo_path")
    if repo_path is None:
        return {"error": "no repo_path available for code analysis"}

    try:
        analyzer = CodeAnalyzer(config)
        findings, metrics = await asyncio.to_thread(analyzer.analyze, repo_path)
        return {
            "code_metrics": metrics,
            "findings": findings,
            "current_step": "analyze_code",
        }
    except Exception as exc:
        logger.exception("Code analyzer failed")
        return {"error": f"code analyzer failed: {exc}", "current_step": "analyze_code"}


async def node_analyze_docs(state: AuditState) -> dict[str, Any]:
    """Run the documentation and agent-readiness analyzer."""
    config = state["config"]
    repo_path = state.get("repo_path")
    if repo_path is None:
        return {"error": "no repo_path available for doc analysis"}

    try:
        analyzer = DocAnalyzer(config)
        findings, metrics = await asyncio.to_thread(analyzer.analyze, repo_path)
        return {
            "doc_metrics": metrics,
            "findings": findings,
            "current_step": "analyze_docs",
        }
    except Exception as exc:
        logger.exception("Doc analyzer failed")
        return {"error": f"doc analyzer failed: {exc}", "current_step": "analyze_docs"}


def node_score(state: AuditState) -> dict[str, Any]:
    """Calculate area scores and the overall scorecard."""
    try:
        config = state["config"]
        findings = state.get("findings", [])
        git_metrics = state.get("git_metrics")
        code_metrics = state.get("code_metrics")
        doc_metrics = state.get("doc_metrics")

        total_files, total_dirs, total_commits, total_contributors = _total_from_metrics(
            git_metrics
        )
        metrics_by_area = _metrics_by_area(git_metrics, code_metrics, doc_metrics)

        scorecard = build_scorecard(
            repo_name=config.repo_name,
            findings=list(findings),
            metrics_by_area=metrics_by_area,
            area_weights=config.area_weights,
            branch=config.branch,
            commit_sha=state.get("commit_sha") or _git_head(Path(state["repo_path"] or ".")),
            total_files=total_files,
            total_directories=total_dirs,
            total_commits=total_commits,
            total_contributors=total_contributors,
        )

        return {
            "scorecard": scorecard,
            "current_step": "score",
            "status": "running",
        }
    except Exception as exc:
        logger.exception("Scoring failed")
        return {"error": f"scoring failed: {exc}", "current_step": "score"}


def node_plan_sprints(state: AuditState) -> dict[str, Any]:
    """Generate a remediation sprint plan based on findings and team capacity."""
    config = state["config"]
    findings = state.get("findings", [])
    try:
        sprints = _plan_sprints_from_findings(findings, config)
        return {
            "sprints": sprints,
            "current_step": "plan_sprints",
        }
    except Exception as exc:
        logger.exception("Sprint planning failed")
        return {"error": f"sprint planning failed: {exc}", "current_step": "plan_sprints"}


def node_generate_report(state: AuditState) -> dict[str, Any]:
    """Generate the Markdown report and write it to the configured output directory."""
    scorecard = state.get("scorecard")
    if scorecard is None:
        return {"error": "no scorecard available for report generation"}

    try:
        sprints = state.get("sprints", [])
        report_markdown = generate_full_report(scorecard, sprints)
        report_path = _write_report(
            state["run_id"],
            report_markdown,
            state["config"].output_dir,
        )
        return {
            "report_markdown": report_markdown,
            "report_path": str(report_path),
            "current_step": "generate_report",
            "status": "completed",
            "completed_at": datetime.now(UTC),
        }
    except Exception as exc:
        logger.exception("Report generation failed")
        return {"error": f"report generation failed: {exc}", "current_step": "generate_report"}


async def node_persist(state: AuditState) -> dict[str, Any]:
    """Persist the audit run, scorecard, findings, and sprints."""
    config = state["config"]
    scorecard = state.get("scorecard")
    tenant_id = config.tenant_id

    try:
        manager = PersistenceManager(
            postgres_dsn=config.postgres_dsn,
            fallback_dir=config.cache_dir,
        )

        audit_run = AuditRun(
            id=state["run_id"],
            status=state.get("status", "completed"),
            trigger_type=state["trigger_type"],
            started_at=state["started_at"],
            completed_at=state.get("completed_at"),
            repo_path=state.get("repo_path") or ".",
            scorecard=scorecard,
            error_message=state.get("error"),
            previous_run_id=state.get("previous_run_id"),
            files_changed_since_last=state.get("files_changed_since_last", []),
            areas_reanalyzed=state.get("areas_reanalyzed", []),
            tenant_id=tenant_id,
        )

        await manager.save_run(audit_run, tenant_id=tenant_id)
        if scorecard is not None:
            await manager.save_scorecard(audit_run.id, scorecard, tenant_id=tenant_id)
        if state.get("findings"):
            await manager.save_findings(
                audit_run.id,
                state["findings"],
                repo_name=config.repo_name,
                tenant_id=tenant_id,
            )
        if state.get("sprints"):
            await manager.save_sprints(
                audit_run.id,
                state["sprints"],
                repo_name=config.repo_name,
                tenant_id=tenant_id,
            )

        return {"current_step": "persist"}
    except Exception as exc:
        logger.exception("Persistence failed")
        return {"error": f"persistence failed: {exc}", "current_step": "persist"}


async def node_update_kg(state: AuditState) -> dict[str, Any]:
    """Update the Neo4j knowledge graph with audit results when configured."""
    config = state["config"]
    scorecard = state.get("scorecard")
    if scorecard is None or config.neo4j_uri is None:
        return {"current_step": "update_kg"}

    try:
        await update_knowledge_graph(
            run_id=state["run_id"],
            repo_name=config.repo_name,
            scorecard=scorecard,
            findings=state.get("findings", []),
            sprints=state.get("sprints", []),
            neo4j_uri=config.neo4j_uri,
            neo4j_user=config.neo4j_user,
            neo4j_password=config.neo4j_password,
        )
        return {"current_step": "update_kg"}
    except Exception as exc:
        logger.exception("Knowledge-graph update failed")
        return {"error": f"knowledge-graph update failed: {exc}", "current_step": "update_kg"}


async def node_handle_error(state: AuditState) -> dict[str, Any]:
    """Error handler that preserves partial results and persists a failed run."""
    error_message = state.get("error") or "unknown error"
    config = state["config"]
    tenant_id = config.tenant_id
    completed_at = datetime.now(UTC)

    try:
        manager = PersistenceManager(
            postgres_dsn=config.postgres_dsn,
            fallback_dir=config.cache_dir,
        )
        audit_run = AuditRun(
            id=state["run_id"],
            status="failed",
            trigger_type=state["trigger_type"],
            started_at=state["started_at"],
            completed_at=completed_at,
            repo_path=state.get("repo_path") or ".",
            error_message=error_message,
            previous_run_id=state.get("previous_run_id"),
            files_changed_since_last=state.get("files_changed_since_last", []),
            areas_reanalyzed=state.get("areas_reanalyzed", []),
            tenant_id=tenant_id,
        )
        await manager.save_run(audit_run, tenant_id=tenant_id)
    except Exception:
        logger.exception("Failed to persist failed audit run from error handler")

    return {
        "status": "failed",
        "completed_at": completed_at,
        "error_message": error_message,
        "current_step": "handle_error",
    }


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------


def should_full_or_incremental(state: AuditState) -> str:
    """Decide whether to run a full analysis or skip to scoring.

    For now incremental audits still re-analyze the repository so that findings
    are always current; the branch exists for future short-circuit logic.
    """
    if state.get("error"):
        return "error"
    return "analyze"


def check_for_errors(state: AuditState) -> str:
    """Route to the error handler when an error is set."""
    if state.get("error"):
        return "error"
    return "continue"


def should_plan_sprints(state: AuditState) -> str:
    """Skip sprint planning when it is disabled in configuration."""
    if state.get("error"):
        return "error"
    if state["config"].sprints_enabled:
        return "plan"
    return "skip"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def create_audit_graph() -> CompiledStateGraph:
    """Build and compile the AuditOrchestrator LangGraph state machine."""
    builder = StateGraph(AuditState)

    builder.add_node("clone", node_clone_repo)
    builder.add_node("analyze_git", node_analyze_git)
    builder.add_node("analyze_code", node_analyze_code)
    builder.add_node("analyze_docs", node_analyze_docs)
    builder.add_node("score", node_score)
    builder.add_node("plan_sprints", node_plan_sprints)
    builder.add_node("generate_report", node_generate_report)
    builder.add_node("persist", node_persist)
    builder.add_node("update_kg", node_update_kg)
    builder.add_node("handle_error", node_handle_error)

    builder.set_entry_point("clone")
    builder.add_conditional_edges(
        "clone",
        should_full_or_incremental,
        {"analyze": "analyze_git", "score": "score", "error": "handle_error"},
    )
    builder.add_conditional_edges(
        "analyze_git",
        check_for_errors,
        {"continue": "analyze_code", "error": "handle_error"},
    )
    builder.add_conditional_edges(
        "analyze_code",
        check_for_errors,
        {"continue": "analyze_docs", "error": "handle_error"},
    )
    builder.add_conditional_edges(
        "analyze_docs",
        check_for_errors,
        {"continue": "score", "error": "handle_error"},
    )
    builder.add_conditional_edges(
        "score",
        should_plan_sprints,
        {"plan": "plan_sprints", "skip": "generate_report", "error": "handle_error"},
    )
    builder.add_edge("plan_sprints", "generate_report")
    builder.add_conditional_edges(
        "generate_report",
        check_for_errors,
        {"continue": "persist", "error": "handle_error"},
    )
    builder.add_conditional_edges(
        "persist",
        check_for_errors,
        {"continue": "update_kg", "error": "handle_error"},
    )
    builder.add_conditional_edges(
        "update_kg",
        check_for_errors,
        {"continue": END, "error": "handle_error"},
    )
    builder.add_edge("handle_error", END)

    return builder.compile()


def _initial_state(
    config: AuditConfig,
    trigger_type: str,
    previous_run_id: str | None,
    run_id: str | None = None,
) -> AuditState:
    """Create the initial state for an audit run."""
    return AuditState(
        config=config,
        trigger_type=trigger_type,
        previous_run_id=previous_run_id,
        run_id=run_id or str(uuid4()),
        status="pending",
        current_step="start",
        started_at=datetime.now(UTC),
        completed_at=None,
        repo_path=None,
        git_metrics=None,
        code_metrics=None,
        doc_metrics=None,
        findings=[],
        scorecard=None,
        sprints=[],
        report_path=None,
        report_markdown=None,
        error=None,
    )


async def run_audit_async(
    config: AuditConfig,
    trigger_type: str = "manual",
    previous_run_id: str | None = None,
    run_id: str | None = None,
    tenant_id: str | None = None,
) -> AuditState:
    """Asynchronous entrypoint that executes the full audit graph."""
    if tenant_id is not None:
        config.tenant_id = tenant_id
    graph = create_audit_graph()
    initial_state = _initial_state(config, trigger_type, previous_run_id, run_id)
    final_state = cast(AuditState, await graph.ainvoke(initial_state))
    if final_state.get("error"):
        raise RuntimeError(f"Audit run failed: {final_state['error']}")
    return final_state


def run_audit(
    config: AuditConfig,
    trigger_type: str = "manual",
    previous_run_id: str | None = None,
    run_id: str | None = None,
    tenant_id: str | None = None,
) -> AuditState:
    """Synchronous entrypoint that executes the full audit graph."""
    return asyncio.run(run_audit_async(config, trigger_type, previous_run_id, run_id, tenant_id))


__all__ = [
    "AuditState",
    "create_audit_graph",
    "run_audit",
    "run_audit_async",
    "node_clone_repo",
    "node_analyze_git",
    "node_analyze_code",
    "node_analyze_docs",
    "node_score",
    "node_plan_sprints",
    "node_generate_report",
    "node_persist",
    "node_update_kg",
    "node_handle_error",
    "should_full_or_incremental",
    "check_for_errors",
    "should_plan_sprints",
]
