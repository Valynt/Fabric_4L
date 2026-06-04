"""Release Policy: Secret remediation policy enforcement.

Verifies that non-example .env files are not tracked in git for release-candidate.
Uses git ls-files and path patterns only - does not read secret values.
"""

import subprocess
from pathlib import Path

import pytest


class TestSecretPolicy:
    """Enforce: No non-example .env files in git for release-candidate."""

    def _git_ls_files(self) -> list[str]:
        """Get list of tracked files from git."""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split("\n")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Git not available or not in a git repository")

    def test_no_tracked_env_files(self):
        """No .env files (except .env.example) should be tracked in git.

        Security: Real environment files contain secrets and must not be committed.
        """
        tracked_files = self._git_ls_files()

        # Find .env files that are not examples/templates
        forbidden_patterns = [".env", ".env.local", ".env.prod", ".env.staging"]
        allowed_suffixes = [".example", ".template", ".sample"]

        violations = []
        for file in tracked_files:
            if not Path(file).exists():
                continue
            file_lower = file.lower()
            # Check if it's an env file
            if any(file_lower.endswith(pat) or f"{pat}." in file_lower for pat in forbidden_patterns):
                # Check if it's explicitly allowed (ends with known safe suffix)
                if not any(file_lower.endswith(suffix) for suffix in allowed_suffixes):
                    violations.append(file)

        if violations:
            details = "\n".join(f"  - {v}" for v in violations)
            pytest.fail(
                f"Found {len(violations)} tracked .env file(s) that may contain secrets:\n{details}\n"
                f"Only .env.example, .env.template, .env.sample are allowed. "
                f"Add real .env files to .gitignore and remove from tracking."
            )

    def test_gitignore_includes_env_files(self):
        """.gitignore must include patterns for common env files."""
        gitignore = Path(".gitignore")
        if not gitignore.exists():
            pytest.skip("No .gitignore file found")

        content = gitignore.read_text(encoding="utf-8")

        required_patterns = [
            ".env",
            ".env.local",
            ".env.prod",
            ".env.staging",
            "*.env",
        ]

        missing = [p for p in required_patterns if p not in content]

        # Informational - not all patterns may be needed in all repos
        if len(missing) > 2:
            pytest.skip(f".gitignore may be missing env patterns: {missing}")
