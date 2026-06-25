"""Cluster + extract + stage candidates. No graduation here — CLI tools do that.

Pipeline:
  1. cluster_and_extract(entries) — content clusters → structured patterns
  2. write_candidates(patterns, dir) — patterns → candidate JSON files

Every staged candidate carries lifecycle metadata (status, decisions,
rejection_count) from birth so repeated churn is visible rather than looking
fresh each time the pattern recurs.
"""

import os
import json
import datetime
import hashlib
import warnings
from cluster import content_cluster, extract_pattern
from validate import extract_lesson_lines, check_exact_duplicate


def cluster_and_extract(entries, threshold=0.3):
    """Cluster entries by content similarity, extract a pattern per cluster."""
    clusters = content_cluster(entries, threshold=threshold)
    return {p["name"]: p for p in (extract_pattern(c) for c in clusters)}


def _slug(pattern_or_key):
    """Slug for a pattern. Prefer pattern['id'] (claim-derived, stable across
    cluster membership changes); fall back to md5(key) for legacy callers."""
    if isinstance(pattern_or_key, dict) and pattern_or_key.get("id"):
        return pattern_or_key["id"]
    return hashlib.md5(str(pattern_or_key).encode()).hexdigest()[:12]


def _find_prior(slug, candidates_dir):
    """Look up any prior record for this slug across lifecycle subdirs.

    Returns (prev_dict, location) where location is one of
    'staged' | 'rejected' | 'graduated' | None. A slug can only live in
    one place at a time; the caller is responsible for cleaning up the
    old location when moving the candidate back to staged.
    """
    for location in _candidate_locations():
        record = _read_prior_candidate(
            _candidate_path(candidates_dir, location, slug), location
        )
        if record:
            return record, location
    return {}, None


def _candidate_locations():
    return ("staged", "rejected", "graduated")


def _candidate_path(candidates_dir, location, slug):
    if location == "staged":
        return os.path.join(candidates_dir, f"{slug}.json")
    return os.path.join(candidates_dir, location, f"{slug}.json")


def _read_prior_candidate(path, location):
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(
            f"Skipping unreadable {location} candidate {path}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


def _load_candidate_index(candidates_dir):
    """Scan staged/rejected/graduated once and return a slug -> (record, location) map.

    write_candidates previously called _find_prior for every pattern, which in
    turn stat/opened up to three files per pattern.  Building the index once
    removes that N+1 I/O.
    """
    index = {}
    for location in _candidate_locations():
        if location == "staged":
            search_dir = candidates_dir
        else:
            search_dir = os.path.join(candidates_dir, location)
        if not os.path.isdir(search_dir):
            continue
        with os.scandir(search_dir) as entries:
            for entry in entries:
                if not entry.name.endswith(".json") or not entry.is_file():
                    continue
                slug = entry.name[:-5]
                if slug in index:
                    # staged wins over rejected/graduated if a stale duplicate exists.
                    continue
                record = _read_prior_candidate(entry.path, location)
                if record is not None:
                    index[slug] = (record, location)
    return index


def _lessons_text_for_candidates(candidates_dir):
    lessons_path = os.path.join(
        os.path.dirname(candidates_dir), "semantic", "LESSONS.md"
    )
    if not os.path.exists(lessons_path):
        return ""
    try:
        with open(lessons_path) as f:
            return f.read()
    except OSError as exc:
        warnings.warn(
            f"Unable to read lessons file {lessons_path}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return ""


def _claim(pattern):
    return (pattern.get("claim") or "").strip()


def _already_terminal_claim(claim, lessons_text):
    return bool(lessons_text and check_exact_duplicate(claim, lessons_text))


def _terminal_graduated(prev, prev_loc):
    return prev_loc == "graduated" and prev.get("status") != "provisional"


def _last_decision(prev):
    decisions = prev.get("decisions") or []
    return decisions[-1] if decisions else {}


def _evidence_changed(last, pattern):
    prev_evidence = set(last.get("evidence_snapshot", []))
    new_evidence = set(pattern.get("evidence_ids", []))
    return bool(new_evidence - prev_evidence)


def _blocker_still_present(last, current_terminal_lessons):
    stamped_dups = last.get("duplicate_claims") or []
    if not stamped_dups:
        return True
    return any(dup in current_terminal_lessons for dup in stamped_dups)


def _can_restage(prev, prev_loc, pattern, current_terminal_lessons):
    if prev_loc not in ("rejected", "graduated"):
        return True
    last = _last_decision(prev)
    if _evidence_changed(last, pattern):
        return True
    return not _blocker_still_present(last, current_terminal_lessons)


def _should_stage(
    claim, lessons_text, prev, prev_loc, pattern, current_terminal_lessons
):
    if not claim or _already_terminal_claim(claim, lessons_text):
        return False
    if _terminal_graduated(prev, prev_loc):
        return False
    return _can_restage(prev, prev_loc, pattern, current_terminal_lessons)


def _candidate(slug, key, pattern, claim, prev, now):
    decisions = prev.get("decisions", [])
    decisions.append({"ts": now, "action": "staged", "reviewer": "auto_dream"})
    return {
        "id": slug,
        "key": key,
        "name": pattern.get("name", key),
        "claim": claim,
        "conditions": pattern.get("conditions", []),
        "evidence_ids": pattern.get("evidence_ids", []),
        "cluster_size": pattern.get("cluster_size", 1),
        "canonical_salience": pattern.get("canonical_salience", 0.0),
        "staged_at": prev.get("staged_at") or now,
        "status": "staged",
        "decisions": decisions,
        "rejection_count": prev.get("rejection_count", 0),
    }


def _write_candidate(candidates_dir, slug, candidate):
    staged_path = os.path.join(candidates_dir, f"{slug}.json")
    with open(staged_path, "w") as f:
        json.dump(candidate, f, indent=2)


def _cleanup_prior_location(candidates_dir, slug, prev_loc):
    if prev_loc not in ("rejected", "graduated"):
        return
    stale_path = os.path.join(candidates_dir, prev_loc, f"{slug}.json")
    try:
        os.remove(stale_path)
    except FileNotFoundError as exc:
        warnings.warn(
            f"Stale {prev_loc} candidate already absent {exc.filename}",
            RuntimeWarning,
            stacklevel=2,
        )
    except OSError as exc:
        warnings.warn(
            f"Unable to remove stale {prev_loc} candidate for {slug}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )


def write_candidates(patterns, candidates_dir):
    """Stage each pattern as a candidate JSON with lifecycle metadata.

    Checks all three lifecycle subdirs (staged / rejected / graduated) for an
    existing record with the same slug, and preserves its history.
      - staged already: append a new 'staged' decision, keep original staged_at.
      - rejected previously: move back to staged with rejection_count and
        decision log intact. The reviewer sees this as a recurring pattern,
        not a fresh one.
      - graduated previously: skip entirely. The lesson already lives in
        lessons.jsonl; re-staging would only create work the heuristic
        prefilter would then reject on exact-duplicate grounds.
    """
    if not patterns:
        return 0
    os.makedirs(candidates_dir, exist_ok=True)
    written = 0
    lessons_text = _lessons_text_for_candidates(candidates_dir)
    current_terminal_lessons = set(extract_lesson_lines(lessons_text))
    prior_index = _load_candidate_index(candidates_dir)

    for key, p in patterns.items():
        claim = _claim(p)
        slug = _slug(p)
        prev, prev_loc = prior_index.get(slug, ({}, None))
        if not _should_stage(
            claim, lessons_text, prev, prev_loc, p, current_terminal_lessons
        ):
            continue
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _write_candidate(
            candidates_dir, slug, _candidate(slug, key, p, claim, prev, now)
        )
        _cleanup_prior_location(candidates_dir, slug, prev_loc)
        written += 1
    return written
