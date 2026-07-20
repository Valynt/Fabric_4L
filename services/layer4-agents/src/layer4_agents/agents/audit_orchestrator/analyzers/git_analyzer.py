"""Git repository analyzer for the AuditOrchestrator agent."""

from __future__ import annotations

import subprocess
from collections import Counter
from os import walk
from pathlib import Path
from typing import Any

from ..models import AuditArea, Finding
from .base import BaseAnalyzer
from .finding_catalog import FindingCatalog


class GitAnalyzer(BaseAnalyzer):
    """Analyzer that inspects git history and repository structure."""

    name: str = "git"
    areas: list[AuditArea] = [AuditArea.ARCHITECTURE]

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
        """Return True if ``repo_path`` is inside a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def _git_cmd(self, path: Path, args: list[str]) -> str:
        """Run a git command safely and return stdout, or an empty string on failure."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return ""

    def _collect_git_metrics(self, path: Path, git_available: bool) -> dict[str, Any]:
        """Collect metrics from git history."""
        if not git_available:
            return {
                "total_commits": 0,
                "total_contributors": 0,
                "branch_count": 0,
                "tag_count": 0,
                "recent_commit_days": None,
            }

        commits_output = self._git_cmd(path, ["rev-list", "HEAD", "--count"])
        contributors_output = self._git_cmd(path, ["log", "--format=%ae", "HEAD"])
        branches_output = self._git_cmd(path, ["branch", "-a"])
        tags_output = self._git_cmd(path, ["tag", "-l"])
        last_commit_ts = self._git_cmd(path, ["log", "-1", "--format=%ct"])

        contributors = set(
            line.strip() for line in contributors_output.splitlines() if line.strip()
        )
        branches = [b for b in branches_output.splitlines() if b.strip()]
        tags = [t for t in tags_output.splitlines() if t.strip()]

        recent_days = None
        if last_commit_ts.isdigit():
            from datetime import UTC, datetime

            recent_days = (
                datetime.now(UTC) - datetime.fromtimestamp(int(last_commit_ts), tz=UTC)
            ).days

        return {
            "total_commits": int(commits_output) if commits_output.isdigit() else 0,
            "total_contributors": len(contributors),
            "branch_count": len(branches),
            "tag_count": len(tags),
            "recent_commit_days": recent_days,
        }

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
