"""Documentation and agent readiness analyzer for the AuditOrchestrator agent."""

from __future__ import annotations

from os import walk
from pathlib import Path
from typing import Any

from ..models import AuditArea, Finding
from .base import BaseAnalyzer
from .finding_catalog import FindingCatalog


class DocAnalyzer(BaseAnalyzer):
    """Analyzer for documentation completeness and agent readiness."""

    name: str = "doc"
    areas: list[AuditArea] = [
        AuditArea.DOCUMENTATION,
        AuditArea.AGENT_READINESS,
        AuditArea.DEV_EXPERIENCE,
    ]

    def analyze(self, repo_path: str) -> tuple[list[Finding], dict[str, Any]]:
        """Run documentation and agent-readiness analysis.

        Args:
            repo_path: Filesystem path to the repository root.

        Returns:
            Tuple of findings and metrics.
        """
        path = Path(repo_path).resolve()

        findings, metrics = FindingCatalog.check_all(
            str(path),
            self.config,
            areas=self.areas,
        )

        doc_metrics = self._collect_doc_metrics(path)
        metrics.update(doc_metrics)

        return findings, metrics

    def _collect_doc_metrics(self, path: Path) -> dict[str, Any]:
        """Collect lightweight documentation and agent-config metrics."""
        docs_dir = path / "docs"
        adr_dir = docs_dir / "explanations" / "adr"
        agent_skills_dir = path / ".agent" / "skills"
        agent_tools_dir = path / ".agent" / "tools"

        excluded = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
        }
        md_files: list[Path] = []
        if docs_dir.exists():
            for dirpath, dirnames, filenames in walk(str(docs_dir), topdown=True):
                dirnames[:] = [d for d in dirnames if d not in excluded]
                current = Path(dirpath)
                for filename in filenames:
                    if filename.endswith(".md"):
                        md_files.append(current / filename)

        adr_files = list(adr_dir.glob("*.md")) if adr_dir.exists() else []
        skill_dirs = (
            [d for d in agent_skills_dir.iterdir() if d.is_dir()]
            if agent_skills_dir.exists()
            else []
        )
        tool_files = list(agent_tools_dir.rglob("*.json")) if agent_tools_dir.exists() else []

        root_docs = [
            "README.md",
            "AGENTS.md",
            "DESIGN.md",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "ROADMAP.md",
        ]
        root_doc_count = sum(1 for name in root_docs if (path / name).exists())

        return {
            "total_markdown_files": len(md_files),
            "root_governance_doc_count": root_doc_count,
            "adr_count": len(adr_files),
            "agent_skill_count": len(skill_dirs),
            "agent_tool_schema_count": len(tool_files),
        }
