"""Git repository analyzer for the AuditOrchestrator agent."""

from __future__ import annotations

import logging
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from os import walk
from pathlib import Path
from typing import Any

from ..models import AuditArea, AuditConfig, Finding
from .base import BaseAnalyzer
from .finding_catalog import FindingCatalog

logger = logging.getLogger(__name__)

# Default caps for a single bounded ``git`` invocation. They are deliberately
# generous for repository metadata (commit count, tag/branch lists, shortlog),
# but exist so a runaway command can never buffer unbounded output into memory.
DEFAULT_GIT_TIMEOUT_SECONDS = 30.0
DEFAULT_GIT_MAX_OUTPUT_BYTES = 1_000_000
DEFAULT_GIT_MAX_OUTPUT_LINES = 50_000


@dataclass(frozen=True)
class GitCommandResult:
    """Result of a bounded ``git`` invocation plus completeness metadata.

    ``status`` is one of ``ok``, ``error``, ``timeout`` or ``truncated``.
    ``truncated`` is ``True`` whenever output was cut short (timeout or a cap),
    so callers know ``stdout`` is not the full command output and any metric
    derived from it is an undercount rather than an exact figure.
    """

    stdout: str = ""
    status: str = "ok"
    returncode: int | None = None
    truncated: bool = False
    bytes_read: int = 0
    max_bytes: int | None = None
    max_lines: int | None = None


class GitAnalyzer(BaseAnalyzer):
    """Analyzer that inspects git history and repository structure."""

    name: str = "git"
    areas: list[AuditArea] = [AuditArea.ARCHITECTURE]

    # Class-level hook so tests can substitute a fake process launcher without
    # touching the real ``subprocess`` module globally.
    _git_popen = subprocess.Popen

    def __init__(
        self,
        config: AuditConfig,
        *,
        timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS,
        max_output_bytes: int = DEFAULT_GIT_MAX_OUTPUT_BYTES,
        max_output_lines: int = DEFAULT_GIT_MAX_OUTPUT_LINES,
    ) -> None:
        """Initialize the git analyzer with bounded-output policy knobs.

        Args:
            config: Validated audit configuration.
            timeout_seconds: Per-command wall-clock timeout.
            max_output_bytes: Maximum stdout bytes buffered per command.
            max_output_lines: Maximum stdout lines buffered per command.
        """
        super().__init__(config)
        self._git_timeout_seconds = timeout_seconds
        self._git_max_output_bytes = max_output_bytes
        self._git_max_output_lines = max_output_lines

    def analyze(self, repo_path: str) -> tuple[list[Finding], dict[str, Any]]:
        """Run git and structural analysis.

        Args:
            repo_path: Filesystem path to the repository root.

        Returns:
            Tuple of findings and metrics.
        """
        path = Path(repo_path).resolve()
        git_available = self._git_available(path)

        findings, metrics = FindingCatalog.check_all(
            str(path),
            self.config,
            areas=self.areas,
        )

        git_metrics = self._collect_git_metrics(path, git_available)
        structural_metrics = self._collect_structural_metrics(path)

        metrics.update(git_metrics)
        metrics.update(structural_metrics)
        metrics["git_available"] = git_available

        return findings, metrics

    def _git_available(self, path: Path) -> bool:
        """Return True if ``repo_path`` is inside a git working tree.

        Implementation is deliberately filesystem-based rather than shelling
        out to ``git``. Earlier revisions invoked ``git rev-parse`` with a
        scrubbed environment, but this was still vulnerable to ambient state
        (ambient ``GIT_*`` vars, parent-process working directory, plugin
        fixtures) that caused unit tests running against a pristine
        ``tmp_path`` to report the host repo as available. Walking the
        filesystem directly answers the question "is there a ``.git``
        directory at or above this path?" without any subprocess involvement.
        """
        try:
            current = path.resolve()
        except (OSError, RuntimeError):
            return False
        # Walk upward looking for a ``.git`` directory. Stop at the filesystem
        # root. ``.git`` may be a directory (standard repo) or a file
        # (worktree / submodule gitdir pointer); both count as "inside a repo".
        while True:
            candidate = current / ".git"
            try:
                if candidate.exists():
                    return True
            except OSError:
                return False
            parent = current.parent
            if parent == current:
                return False
            current = parent

    def _git_cmd(self, path: Path, args: list[str]) -> GitCommandResult:
        """Run a git command with a bounded output policy.

        Output is streamed incrementally while enforcing per-command byte and
        line caps plus a wall-clock timeout. If the subprocess exceeds a cap or
        the timeout the process is terminated and the returned result is marked
        ``truncated`` (with a ``timeout``/``truncated`` status) so callers never
        mistake partial output for complete output.

        Args:
            path: Repository root the command runs in.
            args: Git sub-command arguments.

        Returns:
            A :class:`GitCommandResult` with captured stdout and completeness
            metadata. On hard failure (missing git, bad cwd) status is
            ``error`` and stdout is empty.
        """
        start = time.monotonic()
        lines: list[str] = []
        bytes_read = 0
        status = "ok"

        try:
            proc = self._git_popen(
                ["git", *args],
                cwd=str(path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
            )
        except (FileNotFoundError, OSError):
            return GitCommandResult(status="error")

        stdout = proc.stdout
        try:
            if stdout is not None:
                for line in stdout:
                    bytes_read += len(line.encode("utf-8", errors="replace"))
                    if time.monotonic() - start > self._git_timeout_seconds:
                        status = "timeout"
                        self._terminate(proc)
                        break
                    if (
                        bytes_read > self._git_max_output_bytes
                        or len(lines) >= self._git_max_output_lines
                    ):
                        status = "truncated"
                        self._terminate(proc)
                        break
                    lines.append(line)
        except OSError:
            if status == "ok":
                status = "error"
        finally:
            self._cleanup(proc)

        if status == "ok" and proc.returncode not in (0, None):
            status = "error"

        truncated = status in ("timeout", "truncated")

        return GitCommandResult(
            stdout="".join(lines),
            status=status,
            returncode=proc.returncode,
            truncated=truncated,
            bytes_read=bytes_read,
            max_bytes=self._git_max_output_bytes,
            max_lines=self._git_max_output_lines,
        )

    @staticmethod
    def _terminate(proc) -> None:
        """Best-effort terminate of the subprocess (used on cap/timeout)."""
        try:
            proc.terminate()
        except Exception:  # noqa: BLE001 - purely defensive shutdown
            pass

    @staticmethod
    def _cleanup(proc) -> None:
        """Reap the subprocess and release stream resources."""
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001 - purely defensive shutdown
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        if proc.stderr is not None:
            try:
                proc.stderr.close()
            except Exception:  # noqa: BLE001
                pass

    def _collect_git_metrics(self, path: Path, git_available: bool) -> dict[str, Any]:
        """Collect metrics from git history.

        Contributor counts are aggregated with ``git shortlog -s --all`` so the
        full commit-by-commit email history is never buffered in Python. The
        previously-used ``git log --format=%ae`` for every commit is avoided as
        it required loading the entire history into memory.

        Completeness metadata is returned alongside each count so callers can
        tell an exact figure from a truncated, timed-out or failed one.
        """
        if not git_available:
            return self._unavailable_metrics()

        commits = self._git_cmd(path, ["rev-list", "HEAD", "--count"])
        contributors = self._git_cmd(path, ["shortlog", "-s", "--all"])
        branches = self._git_cmd(path, ["branch", "-a"])
        tags = self._git_cmd(path, ["tag", "-l"])
        last_commit = self._git_cmd(path, ["log", "-1", "--format=%ct"])

        results = {
            "commits": commits,
            "contributors": contributors,
            "branches": branches,
            "tags": tags,
            "last_commit": last_commit,
        }

        warnings: list[dict[str, Any]] = []
        for name, result in results.items():
            if result.status not in ("timeout", "truncated", "error"):
                continue
            logger.warning(
                "Git metric '%s' incomplete (status=%s, bytes=%s); "
                "reported counts may be understated",
                name,
                result.status,
                result.bytes_read,
            )
            warnings.append(self._build_warning(name, result))

        metric_names = {
            "commits": "total_commits",
            "contributors": "total_contributors",
            "branches": "branch_count",
            "tags": "tag_count",
            "last_commit": "recent_commit_days",
        }

        # Total lines in shortlog == distinct contributors (git -s collapses
        # per-author aggregates). No email addresses are captured or parsed.
        contributor_count = sum(
            1 for line in contributors.stdout.splitlines() if line.strip()
        )

        metrics: dict[str, Any] = {
            "total_commits": _safe_int(commits.stdout),
            "total_contributors": contributor_count,
            "branch_count": len(_nonempty_lines(branches.stdout)),
            "tag_count": len(_nonempty_lines(tags.stdout)),
            "recent_commit_days": _commit_age_days(last_commit.stdout),
        }

        metrics["git_metric_completeness"] = {
            metric_names[name]: {
                "source": name,
                "status": result.status,
                "truncated": result.truncated,
                "complete": result.status == "ok" and not result.truncated,
                "bytes_read": result.bytes_read,
                "max_bytes": result.max_bytes,
                "max_lines": result.max_lines,
            }
            for name, result in results.items()
        }
        metrics["git_warnings"] = warnings

        return metrics

    @classmethod
    def _build_warning(cls, name: str, result: GitCommandResult) -> dict[str, Any]:
        """Build a structured audit warning without exposing raw git output."""
        code = {
            "timeout": "GIT_CMD_TIMEOUT",
            "truncated": "GIT_CMD_OUTPUT_TRUNCATED",
            "error": "GIT_CMD_FAILED",
        }[result.status]
        return {
            "code": code,
            "metric": name,
            "status": result.status,
            "message": (
                f"Git command for metric '{name}' {result.status}; "
                "reported value may be incomplete"
            ),
            "bytes_read": result.bytes_read,
            "max_bytes": result.max_bytes,
            "max_lines": result.max_lines,
        }

    def _unavailable_metrics(self) -> dict[str, Any]:
        """Return zeroed metrics with every completeness flag marked unavailable."""
        names = [
            "total_commits",
            "total_contributors",
            "branch_count",
            "tag_count",
            "recent_commit_days",
        ]
        metrics: dict[str, Any] = {
            "total_commits": 0,
            "total_contributors": 0,
            "branch_count": 0,
            "tag_count": 0,
            "recent_commit_days": None,
        }
        metrics["git_metric_completeness"] = {
            name: {
                "source": name,
                "status": "unavailable",
                "truncated": False,
                "complete": False,
                "bytes_read": 0,
                "max_bytes": None,
                "max_lines": None,
            }
            for name in names
        }
        metrics["git_warnings"] = []
        return metrics

    def _collect_structural_metrics(self, path: Path) -> dict[str, Any]:
        """Collect file/directory metrics without relying on git."""
        excluded = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".tmp",
        }
        files: list[Path] = []
        dirs: set[Path] = set()
        for dirpath, dirnames, filenames in walk(str(path), topdown=True):
            dirnames[:] = [d for d in dirnames if d not in excluded]
            current = Path(dirpath)
            for filename in filenames:
                files.append(current / filename)
            dirs.add(current)

        extensions = Counter(p.suffix.lstrip(".").lower() for p in files if p.suffix)
        return {
            "total_files": len(files),
            "total_directories": len(dirs),
            "file_extensions": dict(extensions.most_common(20)),
        }


def _safe_int(text: str) -> int:
    """Parse a numeric stdout field, returning 0 when it is not a clean integer."""
    stripped = text.strip()
    return int(stripped) if stripped.isdigit() else 0


def _nonempty_lines(text: str) -> list[str]:
    """Return non-empty, stripped lines of command output."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _commit_age_days(last_commit_ts: str) -> int | None:
    """Convert a git epoch timestamp into days since the last commit.

    Returns ``None`` for malformed, missing or out-of-range timestamps rather
    than raising, so a bad ``%ct`` value degrades gracefully.
    """
    stripped = last_commit_ts.strip()
    if not stripped.isdigit():
        return None
    try:
        return (datetime.now(UTC) - datetime.fromtimestamp(int(stripped), tz=UTC)).days
    except (OSError, OverflowError, ValueError):
        return None
