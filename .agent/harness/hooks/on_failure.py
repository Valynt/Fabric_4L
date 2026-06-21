"""Failures are learning. High pain score + rewrite flag after repeat offenses."""
import json, datetime, os
from ._provenance import build_source
from ._episodic_io import append_jsonl

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
EPISODIC = os.path.join(ROOT, "memory/episodic/AGENT_LEARNINGS.jsonl")
FAILURE_THRESHOLD = 3
WINDOW_DAYS = 14


def _count_recent_failures(skill_name):
    if not os.path.exists(EPISODIC):
        return 0
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=WINDOW_DAYS)
    return sum(
        1 for entry in _episodic_entries()
        if _is_recent_failure(entry, skill_name, cutoff)
    )


def _episodic_entries():
    for line in open(EPISODIC):
        entry = _parse_entry(line)
        if entry:
            yield entry


def _parse_entry(line):
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _entry_timestamp(entry):
    try:
        ts = datetime.datetime.fromisoformat(entry["timestamp"])
    except (KeyError, ValueError):
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=datetime.timezone.utc)
    return ts


def _is_recent_failure(entry, skill_name, cutoff):
    if entry.get("skill") != skill_name or entry.get("result") != "failure":
        return False
    ts = _entry_timestamp(entry)
    return bool(ts and ts > cutoff)


def on_failure(skill_name, action, error, context="", confidence=0.9,
               evidence_ids=None, importance=None, pain_score=None):
    # Format reflection without the noisy `type(error).__name__:` prefix
    # when the caller passes a pre-formatted string (the common case for
    # hook callers). Only include the type name for actual Exception objects
    # where it carries diagnostic value.
    if isinstance(error, Exception):
        _refl = (f"FAILURE in {skill_name}: {type(error).__name__}: "
                 f"{str(error)[:200]}")
    else:
        _refl = f"FAILURE in {skill_name}: {str(error)[:200]}"

    # Let callers override the generic (7/8) defaults so a failed deploy or
    # schema migration is recorded with its true importance and pain score;
    # the dream-cycle salience can't distinguish failure severity otherwise.
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "skill": skill_name,
        "action": action[:200],
        "result": "failure",
        "detail": str(error)[:500],
        "pain_score": pain_score if pain_score is not None else 8,
        "importance": importance if importance is not None else 7,
        "reflection": _refl,
        "context": context[:300],
        "confidence": confidence,
        "source": build_source(skill_name),
        "evidence_ids": list(evidence_ids) if evidence_ids else [],
    }
    # _count_recent_failures returns PRIOR failures only; add 1 for this one
    # so the rewrite flag fires on the Nth failure, not the (N+1)th.
    recent = _count_recent_failures(skill_name) + 1
    if recent >= FAILURE_THRESHOLD:
        entry["reflection"] += (
            f" | THIS SKILL HAS FAILED {recent} TIMES IN {WINDOW_DAYS}d. "
            f"Flag for rewrite."
        )
        entry["pain_score"] = 10
    return append_jsonl(EPISODIC, entry)
