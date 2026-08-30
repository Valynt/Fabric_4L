"""Regression tests for repository hygiene manifest loading."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from repo_hygiene import load_manifest


def test_load_manifest_uses_config_canonical_paths(tmp_path):
    manifest = tmp_path / "config" / "canonical-paths.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("metadata:\n  version: test\n", encoding="utf-8")

    assert load_manifest(tmp_path)["metadata"]["version"] == "test"


def test_load_manifest_does_not_require_root_manifest(tmp_path):
    with pytest.raises(FileNotFoundError) as exc_info:
        load_manifest(tmp_path)

    # The error message embeds the platform-specific path separator.
    assert ("config" + os.sep + "canonical-paths.yaml") in str(exc_info.value)
