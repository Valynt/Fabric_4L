"""Assemble context from memory + matched skills + protocols within a token budget.

Query-aware: episodes and lessons are scored against user_input so the agent
sees the memory that matters for *this* task, not just the most salient memory
in general. Always-on slots (PREFERENCES, WORKSPACE, permissions) are loaded
whole regardless of query — they're cheap and safety-critical.
"""
import json, os, re, sys
from salience import salience_score
from text import word_set, jaccard

ROOT = os.path.join(os.path.dirname(__file__), "..")
# skill_loader lives in tools/ — make it importable without requiring callers
# to configure PYTHONPATH themselves
sys.path.insert(0, os.path.join(ROOT, "tools"))
RELEVANCE_FLOOR = 0.3  # even zero-overlap episodes surface if very salient

# Keep in sync with memory/validate._extract_lesson_lines — both filters
# want TERMINAL-only lesson content.
_STATUS_RE = re.compile(r"status=(\w+)")


def _read(path, limit=None):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return ""
    content = open(full).read()
    return content[:limit] if limit else content


def _token_estimate(text):
    """Rough chars-to-tokens estimate for budgeting."""
    return len(text) // 4


def _relevance(entry_text, query_words):
    """Fraction of query words that appear in entry. 1.0 when no query."""
    if not query_words:
        return 1.0
    ew = word_set(entry_text)
    if not ew:
        return 0.0
    return len(query_words & ew) / len(query_words)


def _top_episodes(query, k=5):
    path = os.path.join(ROOT, "memory/episodic/AGENT_LEARNINGS.jsonl")
    if not os.path.exists(path):
        return ""
    entries = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    query_words = word_set(query)

    def _score(e):
        text = " ".join([
            e.get("action", ""),
            e.get("reflection", ""),
            e.get("detail", ""),
        ])
        rel = _relevance(text, query_words)
        return salience_score(e) * (RELEVANCE_FLOOR + (1.0 - RELEVANCE_FLOOR) * rel)

    entries.sort(key=_score, reverse=True)
    top = entries[:k]
    return "\n".join(
        f"- [{e.get('timestamp','')[:10]}] {e.get('action','')}: "
        f"{e.get('reflection', e.get('detail',''))}"
        for e in top
    )


def _lines_up_to_budget(lines, char_budget):
    out, used = [], 0
    for line in lines:
        block = f"- {line}\n"
        if used + len(block) > char_budget:
            break
        out.append(block)
        used += len(block)
    return "".join(out)


def _lesson_status_allowed(line):
    if "<!--" not in line:
        return True
    ann = line.split("<!--", 1)[1]
    match = _STATUS_RE.search(ann)
    return not match or match.group(1) == "accepted"


def _lesson_text_from_line(line):
    s = line.strip()
    if not s.startswith("- ") or len(s) <= 2:
        return ""
    if not _lesson_status_allowed(s):
        return ""
    text = s[2:].split("<!--")[0].strip()
    if text.startswith("[PROVISIONAL]"):
        return ""
    if text.startswith("~~") and text.endswith("~~"):
        return ""
    return text


def _accepted_lesson_lines(lessons_md):
    return [
        text for text in (
            _lesson_text_from_line(line)
            for line in (lessons_md or "").splitlines()
        )
        if text
    ]


def _rank_lessons(lines, query):
    query_words = word_set(query)
    if not query_words:
        return lines
    scored = [(len(query_words & word_set(line)), i, line)
              for i, line in enumerate(lines)]
    relevant = [item for item in scored if item[0] > 0]
    if not relevant:
        return lines
    return [line for _, _, line in sorted(relevant, key=lambda item: (-item[0], item[1]))]


def _top_lessons(query, lessons_md, char_budget=8000):
    """Rank accepted lesson bullets by query overlap; fall back to original order.

    Only terminal (status=accepted) lessons reach the host agent as retrievable
    guidance. Provisional, legacy, and superseded bullets exist in LESSONS.md
    for audit but must not be injected into the system prompt — they'd let the
    agent act on probationary or stale memory.
    """
    lines = _accepted_lesson_lines(lessons_md)
    if not lines:
        # No accepted lessons → return empty. Returning raw markdown would
        # leak the non-terminal content the filter is designed to block.
        return ""
    return _lines_up_to_budget(_rank_lessons(lines, query), char_budget)


def _append_part(parts, used, header, text):
    if not text:
        return used
    parts.append(f"{header}\n{text}")
    return used + _token_estimate(text)


def _append_always_on(parts, used):
    # always load: personal preferences + live workspace + AGENTS map + DECISIONS
    # AGENTS.md and DECISIONS.md were missing despite AGENTS.md specifying the
    # read order — the standalone path was not faithful to its own contract.
    for rel in (
        "AGENTS.md",
        "memory/personal/PREFERENCES.md",
        "memory/working/WORKSPACE.md",
        "memory/working/REVIEW_QUEUE.md",
        "memory/semantic/DECISIONS.md",
    ):
        used = _append_part(parts, used, f"# {rel}", _read(rel))
    return used


def _append_lessons(parts, used, user_input):
    lessons = _top_lessons(user_input, _read("memory/semantic/LESSONS.md"), char_budget=8000)
    return _append_part(parts, used, "# LESSONS (query-relevant)", lessons)


def _append_episodes(parts, used, user_input):
    episodes = _top_episodes(user_input, k=5)
    return _append_part(parts, used, "# RECENT EPISODES (salience x relevance)", episodes)


def _load_skills(user_input):
    # matched skills only (progressive_load is already input-matched).
    # Lazy import so a missing skill_loader doesn't kill context assembly.
    try:
        from skill_loader import progressive_load
        return progressive_load(user_input)
    except (ImportError, OSError, json.JSONDecodeError):
        return []


def _append_skills(parts, used, user_input, budget):
    for skill in _load_skills(user_input):
        block = f"## Skill: {skill['name']}\n{skill['content']}"
        tokens = _token_estimate(block)
        if used + tokens < budget:
            parts.append(block)
            used += tokens
    return used


def _append_permissions(parts, used):
    # permissions always last, small, safety-critical
    return _append_part(parts, used, "# PERMISSIONS", _read("protocols/permissions.md"))


def build_context(user_input: str, budget: int = 88000):
    """Returns (context_string, tokens_used). Lean and query-aware."""
    parts, used = [], 0
    used = _append_always_on(parts, used)
    used = _append_lessons(parts, used, user_input)
    used = _append_episodes(parts, used, user_input)
    used = _append_skills(parts, used, user_input, budget)
    used = _append_permissions(parts, used)
    return "\n\n---\n\n".join(parts), used
