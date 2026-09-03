from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from scripts.ci.check_adr import check_adr
from scripts.ci.check_adr_numbering import numbering_failures

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")


def _mini_repo(tmp_path: Path, *, extra_registry: str = "", extra_files: dict[str, str] | None = None) -> Path:
    _write(
        tmp_path / "docs/explanations/adr/ADR-001-example.md",
        """
        # ADR-001: Example

        **Status:** Accepted
        """,
    )
    _write(
        tmp_path / "docs/explanations/adr/README.md",
        """
        # Architecture Decision Records (ADRs)

        ## ADR Index

        | ADR | Title | Status | Date |
        |-----|-------|--------|------|
        | [ADR-001](./ADR-001-example.md) | Example | ✅ Accepted | 2026-01-01 |

        ## ADR Template
        """,
    )
    _write(
        tmp_path / "docs/decisions/0001-example.md",
        """
        # ADR-0001: Example

        - **Status**: accepted
        """,
    )
    _write(
        tmp_path / "docs/decisions/README.md",
        """
        # Architecture Decision Records

        ## Index

        | ADR | Title | Status | Date |
        |-----|-------|--------|------|
        | [0001](./0001-example.md) | Example | accepted | 2026-01-01 |

        ## When to Write an ADR
        """,
    )
    related = tmp_path / "services" / "layer1-ingestion"
    related.mkdir(parents=True)
    (related / "README.md").write_text("ok\n", encoding="utf-8")
    code_file = tmp_path / "pkg" / "mod.py"
    code_file.parent.mkdir(parents=True)
    code_file.write_text("decode_jwt = True\ncanonical = True\n", encoding="utf-8")

    _write(
        tmp_path / "docs/decisions/adr-registry.yaml",
        f"""
        version: 1
        corpora:
                  architecture:
                    dir: docs/explanations/adr
                    index: docs/explanations/adr/README.md
                  decisions:
                    dir: docs/decisions
                    index: docs/decisions/README.md
        entries:
          - id: ADR-001
            corpus: architecture
            path: docs/explanations/adr/ADR-001-example.md
            status: accepted
            related:
              - services/layer1-ingestion
          - id: "0001"
            corpus: decisions
            path: docs/decisions/0001-example.md
            status: accepted
            related:
              - pkg/mod.py
            must_contain:
              - path: pkg/mod.py
                pattern: decode_jwt
            must_not_contain:
              - path: pkg/mod.py
                pattern: forbidden_token
        {extra_registry}
        """,
    )
    for rel, content in (extra_files or {}).items():
        _write(tmp_path / rel, content)
    return tmp_path


def test_valid_registry_passes(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    assert check_adr(repo) == []


def test_registry_without_corpora_fails_closed(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    _write(
        repo / "docs/decisions/adr-registry.yaml",
        """
        version: 1
        entries:
          - id: ADR-001
            corpus: architecture
            path: docs/explanations/adr/ADR-001-example.md
            status: accepted
            related:
              - services/layer1-ingestion
        """,
    )
    failures = check_adr(repo)
    assert any("defines no corpora" in item for item in failures)


def test_missing_related_path_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    (repo / "services" / "layer1-ingestion").rename(repo / "services" / "moved")
    failures = check_adr(repo)
    assert any("related path does not exist" in item for item in failures)


def test_unregistered_adr_file_fails(tmp_path: Path) -> None:
    repo = _mini_repo(
        tmp_path,
        extra_files={
            "docs/explanations/adr/ADR-002-extra.md": """
            # ADR-002: Extra

            **Status:** Accepted
            """,
        },
    )
    failures = check_adr(repo)
    assert any("not in registry" in item for item in failures)


def test_index_missing_row_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    readme = repo / "docs/explanations/adr/README.md"
    readme.write_text(
        dedent(
            """
            # Architecture Decision Records (ADRs)

            ## ADR Index

            | ADR | Title | Status | Date |
            |-----|-------|--------|------|

            ## ADR Template
            """
        ).lstrip("\n"),
        encoding="utf-8",
    )
    failures = check_adr(repo)
    assert any("index missing" in item for item in failures)


def test_must_contain_miss_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    (repo / "pkg" / "mod.py").write_text("canonical = True\n", encoding="utf-8")
    failures = check_adr(repo)
    assert any("must_contain" in item for item in failures)


def test_must_not_contain_hit_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    (repo / "pkg" / "mod.py").write_text("decode_jwt = True\nforbidden_token = 1\n", encoding="utf-8")
    failures = check_adr(repo)
    assert any("must_not_contain" in item for item in failures)


def test_architecture_numbering_gap_fails(tmp_path: Path) -> None:
    adr_dir = tmp_path / "docs" / "explanations" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-one.md").write_text("# ADR-001: One\n", encoding="utf-8")
    (adr_dir / "ADR-003-three.md").write_text("# ADR-003: Three\n", encoding="utf-8")
    failures = numbering_failures(tmp_path)
    assert any("sequence policy" in item for item in failures)


def test_decisions_numbering_gap_fails(tmp_path: Path) -> None:
    repo = _mini_repo(
        tmp_path,
        extra_files={
            "docs/decisions/0003-gap.md": """
            # ADR-0003: Gap

            - **Status**: accepted
            """,
        },
        extra_registry="""
          - id: "0003"
            corpus: decisions
            path: docs/decisions/0003-gap.md
            status: accepted
            related:
              - pkg/mod.py
        """,
    )
    readme = repo / "docs/decisions/README.md"
    readme.write_text(
        dedent(
            """
            # Architecture Decision Records

            ## Index

            | ADR | Title | Status | Date |
            |-----|-------|--------|------|
            | [0001](./0001-example.md) | Example | accepted | 2026-01-01 |
            | [0003](./0003-gap.md) | Gap | accepted | 2026-01-01 |

            ## When to Write an ADR
            """
        ).lstrip("\n"),
        encoding="utf-8",
    )
    failures = check_adr(repo)
    assert any("decisions sequence" in item for item in failures)


def test_repo_adr_registry_passes() -> None:
    assert check_adr(REPO_ROOT) == []


def test_registry_missing_required_corpus_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    _write(
        repo / "docs/decisions/adr-registry.yaml",
        """
        version: 1
        corpora:
                  architecture:
                    dir: docs/explanations/adr
                    index: docs/explanations/adr/README.md
        entries:
          - id: ADR-001
            corpus: architecture
            path: docs/explanations/adr/ADR-001-example.md
            status: accepted
            related:
              - services/layer1-ingestion
        """,
    )
    failures = check_adr(repo)
    assert any("must define the decisions corpus" in item for item in failures)


def test_configured_corpus_with_no_files_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    (repo / "docs/decisions/0001-example.md").unlink()
    failures = check_adr(repo)
    assert any("has no ADR markdown files" in item for item in failures)


def test_invalid_regex_pattern_fails_with_structured_error(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    registry = repo / "docs/decisions/adr-registry.yaml"
    registry.write_text(
        registry.read_text(encoding="utf-8").replace("pattern: decode_jwt", 'pattern: "["'),
        encoding="utf-8",
    )
    failures = check_adr(repo)
    assert any("invalid must_contain pattern" in item for item in failures)


def test_index_link_to_missing_path_fails(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    readme = repo / "docs/explanations/adr/README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "./ADR-001-example.md", "./missing/ADR-001-example.md"
        ),
        encoding="utf-8",
    )
    failures = check_adr(repo)
    assert any("index link does not resolve" in item for item in failures)
