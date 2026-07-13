"""Static code analyzer for the AuditOrchestrator agent."""

from __future__ import annotations

import re
from os import walk
from pathlib import Path
from typing import Any

from ..models import AuditArea, Finding
from .base import BaseAnalyzer
from .finding_catalog import FindingCatalog

# Module-level compiled patterns used by checks and exposed for validation.
COMPILED_PATTERNS: dict[str, re.Pattern[str]] = {
    "relative_import": re.compile(r"^\s*from\s+\."),
    "bare_except": re.compile(r"^\s*except\s*:\s*"),
    "todo_fixup": re.compile(r"TODO|FIXME|XXX|HACK", re.IGNORECASE),
    "cross_layer_import": re.compile(r"(?:from|import)\s+layer\d+"),
    "pydantic_v1": re.compile(r"from\s+pydantic\.v1|__root__|orm_mode|Config\s*="),
    "env_access": re.compile(r"os\.environ\[|os\.getenv\("),
    "mutating_endpoint": re.compile(r"@router\.(post|put|patch)\("),
    "http_call": re.compile(r"(?:requests|httpx)\.(get|post|put|patch|delete)\("),
    "secret_pattern": re.compile(
        r"(?i)(password|secret|token|api_key|apikey)\s*=\s*[\"'][^\"']{4,}[\"']",
    ),
}


class CodeAnalyzer(BaseAnalyzer):
    """Analyzer for static code quality, correctness, security, tests, CI/CD, and reliability."""

    name: str = "code"
    areas: list[AuditArea] = [
        AuditArea.CODE_QUALITY,
        AuditArea.CORRECTNESS,
        AuditArea.TESTING,
        AuditArea.SECURITY,
        AuditArea.CICD,
        AuditArea.RELIABILITY,
    ]

    def analyze(self, repo_path: str) -> tuple[list[Finding], dict[str, Any]]:
        """Run static code analysis.

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

        code_metrics = self._collect_code_metrics(path)
        metrics.update(code_metrics)

        return findings, metrics

    def _collect_code_metrics(self, path: Path) -> dict[str, Any]:
        """Collect lightweight source code metrics.

        Metrics are intentionally approximate and read-only.
        """
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

        py_files: list[Path] = []
        js_files: list[Path] = []
        test_files: list[Path] = []
        python_lines = 0
        js_lines = 0

        for dirpath, dirnames, filenames in walk(str(path), topdown=True):
            dirnames[:] = [d for d in dirnames if d not in excluded]
            current = Path(dirpath)
            for filename in filenames:
                file_path = current / filename
                if filename.endswith(".py"):
                    py_files.append(file_path)
                    try:
                        python_lines += len(
                            file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                        )
                    except OSError:
                        pass
                elif filename.endswith((".js", ".jsx", ".ts", ".tsx")):
                    js_files.append(file_path)
                    try:
                        js_lines += len(
                            file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                        )
                    except OSError:
                        pass

                if "test" in file_path.parts or filename.startswith("test_"):
                    test_files.append(file_path)

        return {
            "total_python_files": len(py_files),
            "total_frontend_files": len(js_files),
            "total_test_files": len(test_files),
            "python_lines_of_code": python_lines,
            "frontend_lines_of_code": js_lines,
        }
