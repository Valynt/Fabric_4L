"""Regression test: Ensure no git merge conflict markers in source files.

This test scans the repository for conflict markers (<<<<<<<, =======, >>>>>>>)
to prevent unresolved merge conflicts from being committed.
"""

import pytest
from pathlib import Path


def get_repo_root() -> Path:
    """Get the repository root directory."""
    # tests/arch/test_no_merge_markers.py -> tests/arch -> tests -> repo_root
    return Path(__file__).parent.parent.parent


def get_source_files(repo_root: Path) -> list[Path]:
    """Get all source files that should be checked."""
    import os
    source_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml", ".md", ".rego"}
    exclude_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "dist", "build", ".windsurf", ".mypy_cache", ".ruff_cache", ".vite", "artifacts", "audit-output", ".jr", "reports"}
    
    files = []
    for root, dirs, filenames in os.walk(repo_root):
        # Prune excluded directories in-place so os.walk doesn't traverse them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for filename in filenames:
            if any(filename.endswith(ext) for ext in source_extensions):
                files.append(Path(root) / filename)
    return files


@pytest.mark.parametrize("marker", ["<<<<<<<", ">>>>>>>"])
def test_no_merge_conflict_markers(marker: str):
    """Verify no merge conflict markers exist in source files."""
    repo_root = get_repo_root()
    violations = []
    
    for file_path in get_source_files(repo_root):
        try:
            content = file_path.read_text(encoding="utf-8")
            if marker in content:
                # Check if it's actually a conflict marker (at line start)
                for line_num, line in enumerate(content.splitlines(), 1):
                    if line.startswith(marker):
                        violations.append(f"{file_path}:{line_num}")
        except (UnicodeDecodeError, OSError):
            # Skip binary files or unreadable files
            continue
    
    if violations:
        pytest.fail(
            f"Found {len(violations)} files with merge conflict marker '{marker}':\n" +
            "\n".join(f"  - {v}" for v in violations[:10]) +
            ("\n  ... and more" if len(violations) > 10 else "")
        )
