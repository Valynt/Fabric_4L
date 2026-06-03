"""Layer-scoped episodic memory retrieval.

Thin wrapper over .agent/memory/episodic/ that filters by layer tag
before salience scoring. Episodes without layer tags are included
(universal fallback); episodes with non-matching layer tags are excluded.
"""
import datetime
import json
from pathlib import Path
from typing import List

from vf_text import word_set

__all__ = ["load_episodes"]

ROOT = Path(__file__).parent.parent.parent
EPISODIC_PATH = ROOT / ".agent" / "memory" / "episodic" / "AGENT_LEARNINGS.jsonl"


def _load_entries():
    if not EPISODIC_PATH.exists():
        return []
    entries = []
    with open(EPISODIC_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _entry_salience(entry: dict) -> float:
    """Basic salience: recency * pain * importance, mirroring .agent/harness/salience.py."""
    ts = entry.get("timestamp")
    if not ts:
        return 0.0
    try:
        parsed = datetime.datetime.fromisoformat(ts)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        age_days = max(0, (datetime.datetime.now(datetime.timezone.utc) - parsed).days)
    except ValueError:
        age_days = 999
    pain = entry.get("pain_score", 5)
    importance = entry.get("importance", 5)
    recency = max(0.0, min(10.0, 10.0 - age_days * 0.3))
    return recency * (pain / 10.0) * (importance / 10.0)


def load_episodes(query: str, layers: List[int], k: int = 5) -> str:
    """Return top-k episodes filtered by layer and ranked by salience x query relevance."""
    entries = _load_entries()
    if not entries:
        return ""

    query_words = word_set(query)
    layer_set = set(str(l) for l in layers) if layers else set()

    def _score(entry):
        text = " ".join([
            entry.get("action", ""),
            entry.get("reflection", ""),
            entry.get("detail", ""),
        ])
        entry_layers = set(str(l) for l in entry.get("layers", []))
        # Episodes without layer tags are included (universal fallback).
        # Episodes with layer tags are included only if at least one tag matches
        # the requested layers.
        if entry_layers and not entry_layers & layer_set:
            return -1.0  # exclude — tagged with layers, none match
        sal = _entry_salience(entry)
        if not query_words:
            return sal
        qw = word_set(text)
        overlap = len(query_words & qw) / len(query_words) if query_words else 1.0
        return sal * (0.3 + 0.7 * overlap)

    scored = [(e, _score(e)) for e in entries]
    scored = [(e, s) for e, s in scored if s >= 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:k]

    if not top:
        return ""

    return "\n".join(
        f"- [{e.get('timestamp', '')[:10]}] {e.get('action', '')}: "
        f"{e.get('reflection', e.get('detail', ''))}"
        for e, _ in top
    )
