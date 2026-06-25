"""Regression tests for N+1 filesystem I/O in .agent/memory.

These tests verify that the hotspot functions batch filesystem work instead of
re-reading or re-locking files inside loops.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

import review_state
import render_lessons
import promote
import auto_dream

pytestmark = [pytest.mark.unit]


def _make_candidate(
    cid: str, claim: str = "sample claim", status: str = "staged"
) -> dict:
    return {
        "id": cid,
        "claim": claim,
        "status": status,
        "decisions": [],
        "rejection_count": 0,
        "evidence_ids": [],
    }


class TestMarkRejectedBatching:
    """mark_rejected should not re-read a candidate we already have in memory."""

    def test_mark_rejected_from_dict_moves_file_without_rereading(self, tmp_path: Path):
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        cid = "cand_001"
        cand = _make_candidate(cid)
        src = candidates_dir / f"{cid}.json"
        src.write_text(json.dumps(cand), encoding="utf-8")

        review_state._mark_rejected_from_dict(
            cand, str(candidates_dir), reviewer="test", reason="too short"
        )

        assert not src.exists()
        rejected = candidates_dir / "rejected" / f"{cid}.json"
        assert rejected.exists()
        assert rejected.read_text(encoding="utf-8") == json.dumps(cand, indent=2)
        assert cand["status"] == "rejected"
        assert cand["rejection_count"] == 1

    def test_mark_rejected_by_id_still_works(self, tmp_path: Path):
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        cid = "cand_002"
        src = candidates_dir / f"{cid}.json"
        src.write_text(json.dumps(_make_candidate(cid)), encoding="utf-8")

        review_state.mark_rejected(cid, "test", "by id", str(candidates_dir))

        assert not src.exists()
        assert (candidates_dir / "rejected" / f"{cid}.json").exists()


class TestAppendLessonsBatching:
    """Migrating many legacy claims should open lessons.jsonl once, not per claim."""

    def test_append_lessons_writes_multiple_rows_in_one_call(self, tmp_path: Path):
        semantic_dir = tmp_path / "semantic"
        semantic_dir.mkdir()
        lessons = [
            {"id": "l1", "claim": "claim one"},
            {"id": "l2", "claim": "claim two"},
        ]

        path = render_lessons.append_lessons(lessons, str(semantic_dir))

        assert path == str(semantic_dir / "lessons.jsonl")
        lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == "l1"
        assert json.loads(lines[1])["id"] == "l2"

    def test_migrate_claims_batches_appends(self, tmp_path: Path):
        semantic_dir = tmp_path / "semantic"
        semantic_dir.mkdir()
        claims = ["first legacy claim", "second legacy claim"]

        migrated = render_lessons._migrate_claims(
            claims,
            str(semantic_dir),
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        assert migrated == 2
        lines = (
            (semantic_dir / "lessons.jsonl")
            .read_text(encoding="utf-8")
            .strip()
            .splitlines()
        )
        assert len(lines) == 2


class TestCandidateIndexBatching:
    """write_candidates should scan lifecycle dirs once instead of per pattern."""

    def test_load_candidate_index_reads_all_locations(self, tmp_path: Path):
        candidates_dir = tmp_path / "candidates"
        (candidates_dir / "rejected").mkdir(parents=True)
        (candidates_dir / "graduated").mkdir(parents=True)

        staged = _make_candidate("staged_1")
        rejected = _make_candidate("rej_1", status="rejected")
        graduated = _make_candidate("grad_1", status="accepted")

        (candidates_dir / "staged_1.json").write_text(
            json.dumps(staged), encoding="utf-8"
        )
        (candidates_dir / "rejected" / "rej_1.json").write_text(
            json.dumps(rejected), encoding="utf-8"
        )
        (candidates_dir / "graduated" / "grad_1.json").write_text(
            json.dumps(graduated), encoding="utf-8"
        )

        index = promote._load_candidate_index(str(candidates_dir))

        assert index["staged_1"] == (staged, "staged")
        assert index["rej_1"] == (rejected, "rejected")
        assert index["grad_1"] == (graduated, "graduated")

    def test_write_candidates_reuses_index_and_moves_rejected_back(
        self, tmp_path: Path
    ):
        candidates_dir = tmp_path / "candidates"
        (candidates_dir / "rejected").mkdir(parents=True)
        cid = "recurring"
        prior = _make_candidate(cid, status="rejected")
        prior["rejection_count"] = 1
        prior["decisions"] = [{"ts": "old", "action": "rejected", "reviewer": "test"}]
        (candidates_dir / "rejected" / f"{cid}.json").write_text(
            json.dumps(prior), encoding="utf-8"
        )

        pattern = {
            "id": cid,
            "name": cid,
            "claim": "recurring claim",
            "conditions": [],
            "evidence_ids": ["new_evidence"],
            "cluster_size": 2,
            "canonical_salience": 8.0,
        }

        written = promote.write_candidates({cid: pattern}, str(candidates_dir))

        assert written == 1
        assert not (candidates_dir / "rejected" / f"{cid}.json").exists()
        staged_path = candidates_dir / f"{cid}.json"
        assert staged_path.exists()
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        assert staged["status"] == "staged"
        assert staged["rejection_count"] == 1


class TestHeuristicPrefilterBatching:
    """_heuristic_prefilter should not re-load a candidate it already loaded."""

    def test_prefilter_passes_loaded_candidate_to_rejected_helper(
        self, tmp_path: Path, monkeypatch
    ):
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        semantic_dir = tmp_path / "semantic"
        semantic_dir.mkdir()

        # A claim that is too short will fail the heuristic.
        cid = "short"
        cand = _make_candidate(cid, claim="x")
        (candidates_dir / f"{cid}.json").write_text(json.dumps(cand), encoding="utf-8")

        captured = []

        def fake_mark_rejected_from_dict(rej_cand, cdir, reviewer, reason, **extra):
            captured.append(rej_cand)
            review_state._mark_rejected_from_dict(
                rej_cand, cdir, reviewer, reason, **extra
            )

        monkeypatch.setattr(
            auto_dream, "_mark_rejected_from_dict", fake_mark_rejected_from_dict
        )

        # LESSONS.md must exist for heuristic_check to run its duplicate scan.
        (semantic_dir / "LESSONS.md").write_text("# Lessons\n", encoding="utf-8")

        rejected_count = auto_dream._heuristic_prefilter(
            str(candidates_dir), str(semantic_dir)
        )

        assert rejected_count == 1
        assert len(captured) == 1
        assert captured[0]["id"] == cid
