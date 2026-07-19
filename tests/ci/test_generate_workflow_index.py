from __future__ import annotations

from pathlib import Path

from scripts.ci.generate_workflow_index import build_index


def test_generated_workflow_index_has_no_wall_clock_metadata(tmp_path: Path) -> None:
    workflow = tmp_path / "example.md"
    workflow.write_text(
        "---\n"
        "workflow_id: example\n"
        "name: Example\n"
        "description: Deterministic example workflow.\n"
        "category: testing\n"
        "---\n",
        encoding="utf-8",
    )

    generated = build_index(tmp_path)

    assert "Last Updated" not in generated
