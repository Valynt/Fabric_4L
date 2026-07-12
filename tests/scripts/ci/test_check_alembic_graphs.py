from pathlib import Path

from scripts.ci._check_alembic_graphs import _extract_revisions

from scripts.ci import _check_alembic_graphs


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_extract_revisions_simple_assignment(tmp_path: Path) -> None:
    _write(
        tmp_path / "001_simple.py",
        "revision = 'rev_1'\ndown_revision = 'rev_0'\nbranch_labels = None\ndepends_on = None\n",
    )

    revisions, revision_files = _extract_revisions(tmp_path)

    assert revisions["rev_1"]["down_revision"] == ("rev_0",)
    assert revisions["rev_1"]["branch_labels"] is None
    assert revisions["rev_1"]["depends_on"] is None
    assert revision_files == {"rev_1": ["001_simple.py"]}


def test_extract_revisions_annotated_assignment(tmp_path: Path) -> None:
    _write(
        tmp_path / "002_annotated.py",
        "revision: str = 'rev_2'\ndown_revision: str | None = None\nbranch_labels: tuple[str, ...] | None = ('alpha',)\ndepends_on: tuple[str, ...] | None = ('base_1', 'base_2')\n",
    )

    revisions, _ = _extract_revisions(tmp_path)

    assert revisions["rev_2"]["down_revision"] == ()
    assert revisions["rev_2"]["branch_labels"] == ("alpha",)
    assert revisions["rev_2"]["depends_on"] == ("base_1", "base_2")


def test_extract_revisions_multi_parent_down_revision(tmp_path: Path) -> None:
    _write(
        tmp_path / "003_merge.py",
        "revision = 'rev_merge'\ndown_revision = ('rev_left', 'rev_right')\n",
    )
    _write(
        tmp_path / "004_merge_list.py",
        "revision = 'rev_merge_list'\ndown_revision = ['rev_a', 'rev_b']\n",
    )

    revisions, _ = _extract_revisions(tmp_path)

    assert revisions["rev_merge"]["down_revision"] == ("rev_left", "rev_right")
    assert revisions["rev_merge_list"]["down_revision"] == ("rev_a", "rev_b")


def test_extract_revisions_tracks_duplicate_revision_ids(tmp_path: Path) -> None:
    _write(tmp_path / "005_dup_a.py", "revision = 'dup_rev'\ndown_revision = None\n")
    _write(tmp_path / "006_dup_b.py", "revision = 'dup_rev'\ndown_revision = 'prev'\n")

    _, revision_files = _extract_revisions(tmp_path)

    assert revision_files["dup_rev"] == ["005_dup_a.py", "006_dup_b.py"]


def test_main_accepts_multi_parent_merge_revision(monkeypatch, tmp_path: Path, capsys) -> None:
    service_dir = tmp_path / "service"
    versions_dir = service_dir / "migrations" / "versions"
    versions_dir.mkdir(parents=True)

    _write(versions_dir / "001_base.py", "revision = 'base'\ndown_revision = None\n")
    _write(versions_dir / "002_left.py", "revision = 'left'\ndown_revision = 'base'\n")
    _write(versions_dir / "003_right.py", "revision = 'right'\ndown_revision = 'base'\n")
    _write(
        versions_dir / "004_merge.py",
        "revision = 'merge'\ndown_revision = ('left', 'right')\nbranch_labels = ('merge_branch',)\n",
    )

    monkeypatch.setattr(_check_alembic_graphs, "SERVICES", {"svc": service_dir})

    assert _check_alembic_graphs.main() == 0
    output = capsys.readouterr().out
    assert "svc: 4 revisions, 1 head(s), 1 root(s)" in output
    assert "MULTI-HEAD" not in output


def test_main_reports_duplicate_revision_diagnostics(monkeypatch, tmp_path: Path, capsys) -> None:
    service_dir = tmp_path / "service"
    versions_dir = service_dir / "migrations" / "versions"
    versions_dir.mkdir(parents=True)

    _write(
        versions_dir / "005_dup_a.py",
        "revision = 'dup_rev'\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n",
    )
    _write(
        versions_dir / "006_dup_b.py",
        "revision: str = 'dup_rev'\ndown_revision: str | None = 'prev'\nbranch_labels = ('beta',)\n",
    )

    monkeypatch.setattr(_check_alembic_graphs, "SERVICES", {"svc": service_dir})

    assert _check_alembic_graphs.main() == 1
    output = capsys.readouterr().out
    assert "DUPLICATE revision ID 'dup_rev' in files: ['005_dup_a.py', '006_dup_b.py']" in output
    assert "005_dup_a.py: revision='dup_rev', down_revision=None, branch_labels=None, depends_on=None" in output
    assert "006_dup_b.py: revision='dup_rev', down_revision='prev', branch_labels=('beta',), depends_on=None" in output
