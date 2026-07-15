"""Release metadata tests.

These checks intentionally avoid skip valves. A release-policy gate must either pass with
evidence or fail closed so missing traceability cannot be mistaken for readiness.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

SEMVER_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+(-[A-Za-z0-9_.-]+)?$")
ISO_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class TestReleaseMetadata:
    """Enforce release metadata and traceability for release candidates."""

    def test_changelog_or_release_notes_exist(self) -> None:
        """A release candidate must ship with a changelog or release notes."""
        candidates = [
            Path("CHANGELOG.md"),
            Path("RELEASE_NOTES.md"),
            Path("docs/CHANGELOG.md"),
            Path("docs/releases"),
        ]
        found = [path for path in candidates if path.exists()]
        assert found, "Missing CHANGELOG.md, RELEASE_NOTES.md, docs/CHANGELOG.md, or docs/releases/"

        readable = [path for path in found if path.is_dir() or path.stat().st_size > 0]
        assert readable, "Release metadata path exists but is empty"

    def test_version_metadata_exists_and_is_semver(self) -> None:
        """Version metadata must be present and semver-compatible."""
        candidates = [Path("version.txt"), Path("VERSION"), Path("package.json"), Path("pyproject.toml")]
        assert any(path.exists() for path in candidates), "Missing version.txt, VERSION, package.json, or pyproject.toml"

        version: str | None = None
        if Path("version.txt").exists():
            version = Path("version.txt").read_text(encoding="utf-8").strip()
        elif Path("VERSION").exists():
            version = Path("VERSION").read_text(encoding="utf-8").strip()
        elif Path("package.json").exists():
            package = json.loads(Path("package.json").read_text(encoding="utf-8"))
            version = package.get("version")
        elif Path("pyproject.toml").exists():
            content = Path("pyproject.toml").read_text(encoding="utf-8")
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            version = match.group(1) if match else None

        assert version, "Release version metadata exists but does not define a version"
        assert SEMVER_PATTERN.match(version), f"Release version '{version}' is not semver-compatible"

    def test_package_version_is_canonical_release_version(self) -> None:
        """Root package.json version is the release version source used by release-safety evidence."""
        package = json.loads(Path("package.json").read_text(encoding="utf-8"))
        version = str(package.get("version") or "")
        assert version, "package.json must define release version metadata"
        assert SEMVER_PATTERN.match(version), f"package.json version '{version}' is not semver-compatible"

    def test_release_safety_artifact_contains_identity_metadata(self, tmp_path: Path) -> None:
        """The release dry-run artifact must contain immutable release identity metadata."""
        output = tmp_path / "release-safety.json"
        result = subprocess.run(
            [
                "python",
                "scripts/ci/generate_release_safety_artifact.py",
                "--environment",
                "release-candidate",
                "--profile",
                "release-candidate",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout

        payload = json.loads(output.read_text(encoding="utf-8"))
        for key in ("version", "commit_sha", "build_timestamp", "environment", "profile", "gate_decision"):
            value = str(payload.get(key) or "").strip()
            assert value, f"release-safety artifact is missing {key}"
            assert value.lower() not in {"unknown", "placeholder", "todo", "tbd"}, (
                f"release-safety artifact has placeholder {key}: {value!r}"
            )

        assert SEMVER_PATTERN.match(str(payload["version"]))
        assert re.fullmatch(r"[0-9a-f]{40}", str(payload["commit_sha"])), "commit_sha must be a full git SHA"
        assert ISO_UTC_PATTERN.match(str(payload["build_timestamp"]))
        parsed_timestamp = datetime.fromisoformat(str(payload["build_timestamp"]).replace("Z", "+00:00"))
        assert parsed_timestamp.tzinfo == UTC
        assert payload["environment"] == "release-candidate"
        assert payload["profile"] == "release-candidate"

    def test_contracts_are_generated_and_non_empty(self) -> None:
        """Committed OpenAPI contracts must exist when contract drift tooling is present."""
        makefile = Path("Makefile")
        assert makefile.exists(), "Makefile is required for contract generation targets"
        content = makefile.read_text(encoding="utf-8")
        assert "contract-drift" in content or "contracts:" in content, "Contract generation target is missing"

        expected_contracts = [
            Path("contracts/openapi/layer1-ingestion.json"),
            Path("contracts/openapi/layer2-extraction.json"),
            Path("contracts/openapi/layer3-knowledge.json"),
            Path("contracts/openapi/layer4-agents.json"),
            Path("contracts/openapi/layer5-ground-truth.json"),
        ]
        missing = [str(path) for path in expected_contracts if not path.is_file() or path.stat().st_size == 0]
        assert not missing, f"Missing or empty OpenAPI contracts: {missing}"

    def test_git_tag_or_version_follows_semver(self) -> None:
        """A release must be traceable through a semver tag or semver version file."""
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            latest_tag = result.stdout.strip()
            assert SEMVER_PATTERN.match(latest_tag), f"Latest tag '{latest_tag}' is not semver-compatible"
            return

        # Untagged development branches may still pass release-policy if the
        # committed version metadata is semver-compatible. The release publish
        # workflow should create the immutable tag before external deployment.
        package_json = Path("package.json")
        package_version = None
        if package_json.exists():
            package_version = json.loads(package_json.read_text(encoding="utf-8")).get("version")
        version_file = Path("version.txt")
        file_version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else None
        fallback_version = file_version or package_version
        assert fallback_version, "No git tag exists and no fallback release version is defined"
        assert SEMVER_PATTERN.match(fallback_version), f"Fallback release version '{fallback_version}' is not semver-compatible"

    def test_release_candidate_branch_naming(self) -> None:
        """Release branches must follow the documented convention; main is allowed."""
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Could not determine current branch: {result.stderr}"
        branch = result.stdout.strip()
        # GitHub Actions checks out a merge commit (detached HEAD) for pull_request
        # events. The source branch is available via GITHUB_HEAD_REF so the
        # release-policy validation still applies.
        if not branch:
            branch = os.environ.get("GITHUB_HEAD_REF", "").strip()
        assert branch, "Detached HEAD is not acceptable for release-policy validation"

        if branch.startswith("release/"):
            assert re.match(r"^release/(v?\d+\.\d+\.\d+|\d{4}-\d{2}-\d{2})$", branch), (
                f"Release branch '{branch}' does not follow release/vX.Y.Z or release/YYYY-MM-DD"
            )
        else:
            # AGENTS.md intentionally does not enforce a non-release branch naming pattern.
            # Keep this deterministic in local agent worktrees (for example, branch `work`)
            # while still validating the only branch namespace that carries release semantics.
            assert not branch.startswith("release"), (
                f"Release-policy validation branches must use the release/ namespace explicitly: {branch!r}"
            )
