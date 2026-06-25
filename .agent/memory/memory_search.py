#!/usr/bin/env python3
"""
Memory Search [BETA] — SQLite FTS5 full-text search over .agent/memory/ files.

Indexes all .md and .jsonl files under .agent/memory/ and provides ranked
keyword search. When SQLite FTS5 is not available, falls back to ripgrep
(`rg`) if installed, then to grep. Fallback paths are always restricted
to .md / .jsonl so implementation files never pollute results.

BETA + opt-in: disabled by default. Enable via onboarding
(agentic-stack <harness> --reconfigure) or by setting
    {"memory_search_fts": {"enabled": true}}
in .agent/memory/.features.json.

Usage:
  python3 memory_search.py <query>       Search memories by keyword
  python3 memory_search.py --rebuild     Force rebuild the index
  python3 memory_search.py --status      Show index status

The index is stored at .agent/memory/.index/memory.db and auto-rebuilds
when any memory file changes, is renamed, or is deleted.
"""
import json
import os
import re
import shutil
import sys
import sqlite3
import subprocess
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent
INDEX_DIR = MEMORY_DIR / ".index"
INDEX_PATH = INDEX_DIR / "memory.db"
FEATURES_PATH = MEMORY_DIR / ".features.json"

# Files we consider "memory documents" for both indexing and search.
MEMORY_SUFFIXES = (".md", ".jsonl")
SKIP_DIRS = {
    ".git",
    ".hypothesis",
    ".index",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def feature_enabled() -> bool:
    """True iff `memory_search_fts` is opted in via .features.json.

    Default OFF: beta features are explicit opt-in. Missing config file,
    missing key, or `enabled: false` all resolve to disabled.
    """
    try:
        data = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    entry = data.get("memory_search_fts") or {}
    return bool(entry.get("enabled"))


def _memory_files():
    """Yield memory document paths, skipping generated/cache directories."""
    for root, dirs, files in os.walk(MEMORY_DIR):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            f = Path(root) / name
            if f.suffix in MEMORY_SUFFIXES and f.is_file():
                yield f


def check_fts5() -> bool:
    """Check if SQLite FTS5 extension is available."""
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE _t USING fts5(c)")
        conn.close()
        return True
    except sqlite3.Error:
        return False


def needs_rebuild() -> bool:
    """True if the index is stale.

    Stale means any of:
      - index file does not exist
      - a current memory file is newer than the index
      - a file that WAS indexed no longer exists (delete / rename)

    Without the third check, deleted files keep showing up in search
    results until some unrelated edit bumps the index.
    """
    if not INDEX_PATH.exists():
        return True
    index_mtime = INDEX_PATH.stat().st_mtime

    current_rel = set()
    for f in _memory_files():
        if f.stat().st_mtime > index_mtime:
            return True
        current_rel.add(str(f.relative_to(MEMORY_DIR)))

    try:
        with sqlite3.connect(INDEX_PATH) as conn:
            indexed_rel = {row[0] for row in conn.execute("SELECT filename FROM memories")}
    except sqlite3.Error:
        return True  # corrupt schema / unreadable — rebuild from scratch

    # Any previously-indexed file no longer present? Rebuild to flush it.
    if indexed_rel - current_rel:
        return True
    return False


def _read_jsonl(path: Path) -> str:
    """Read a .jsonl file and return a searchable text representation."""
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
            parts = [
                entry.get("action", ""),
                entry.get("reflection", ""),
                entry.get("detail", ""),
                entry.get("skill", ""),
            ]
            lines.append(" ".join(p for p in parts if p))
        except json.JSONDecodeError:
            continue
    return "\n".join(lines)


def _reset_index(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS memories")
    conn.execute("""
        CREATE VIRTUAL TABLE memories
        USING fts5(filename, content, tokenize='porter unicode61')
    """)


def _content_for_memory_file(path: Path) -> str | None:
    if path.suffix == ".md":
        return path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return _read_jsonl(path)
    return None


def _insert_memory_file(conn, path: Path) -> bool:
    try:
        content = _content_for_memory_file(path)
        if content is None:
            return False
        rel_path = path.relative_to(MEMORY_DIR)
        conn.execute("INSERT INTO memories VALUES (?, ?)", (str(rel_path), content))
        return True
    except (OSError, UnicodeError, sqlite3.Error) as exc:
        print(f"Skipping memory file {path}: {exc}", file=sys.stderr)
        return False


def build_index() -> int:
    """Build or rebuild the FTS5 index from all memory files."""
    INDEX_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(INDEX_PATH) as conn:
        _reset_index(conn)
        return sum(1 for path in _memory_files() if _insert_memory_file(conn, path))


def search_fts5(query: str):
    """Search the FTS5 index. Returns (filename, snippet) pairs."""
    if needs_rebuild():
        build_index()
    conn = sqlite3.connect(INDEX_PATH)
    try:
        rows = conn.execute(
            """SELECT filename,
                      snippet(memories, 1, '>>>', '<<<', '...', 30)
               FROM memories
               WHERE memories MATCH ?
               ORDER BY rank""",
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        # Query syntax error — fall back to LIKE
        rows = conn.execute(
            "SELECT filename, substr(content, 1, 300) FROM memories WHERE content LIKE ?",
            (f"%{query}%",),
        ).fetchall()

    # SQLite's unicode61 tokenizer is good for mixed Latin/CJK text, but it
    # does not segment every short CJK substring the way users expect. Keep the
    # fast FTS path first, then recover exact CJK substring matches.
    if not rows and CJK_RE.search(query):
        rows = conn.execute(
            "SELECT filename, substr(content, 1, 300) FROM memories WHERE content LIKE ?",
            (f"%{query}%",),
        ).fetchall()
    conn.close()
    return rows


def _fallback_command(query, targets):
    """Return (cmd, tool_name) for the best available fallback searcher.

    Prefers ripgrep (faster, UTF-8 clean, sensible defaults). Falls back
    to grep for POSIX environments. Returns (None, None) if neither is
    on PATH — callers should degrade gracefully.
    """
    if shutil.which("rg"):
        # -l: files-with-matches, -i: case-insensitive, -- ends flags
        return (
            [
                "rg",
                "-li",
                "--glob",
                "!.pytest_cache/**",
                "--glob",
                "!__pycache__/**",
                "--glob",
                "!node_modules/**",
                "--",
                query,
                *targets,
            ],
            "ripgrep",
        )
    if shutil.which("grep"):
        return (["grep", "-ril", query, *targets], "grep")
    return (None, None)


def fallback_tool():
    """Name of the external tool that would be used for fallback search.

    'ripgrep' if rg is on PATH, else 'grep' if grep is, else 'unavailable'.
    Surfaced in --status so users know what mode a query would run in.
    """
    _, tool = _fallback_command("", [])
    return tool or "unavailable"


def search_fallback(query: str):
    """Full-text search without FTS5, restricted to memory document files.

    Passing explicit target paths (not the whole directory) keeps
    keyword retrieval scoped to .md / .jsonl — implementation files
    like archive.py or auto_dream.py never pollute the results.
    """
    targets = [str(f) for f in _memory_files()]
    if not targets:
        return []
    cmd, _ = _fallback_command(query, targets)
    if not cmd:
        return []
    result = subprocess.run(cmd, capture_output=True, text=True)
    files = [f for f in result.stdout.strip().split("\n") if f]
    return [
        (Path(f).relative_to(MEMORY_DIR), f"(match in {Path(f).name})")
        for f in files
    ]


# Backwards-compat alias — anything calling search_grep keeps working.
search_grep = search_fallback


def cmd_rebuild():
    if not check_fts5():
        print("FTS5 not available — cannot build index.")
        return
    count = build_index()
    print(f"Index rebuilt: {count} files indexed.")


def cmd_status():
    enabled = feature_enabled()
    tag = "ENABLED" if enabled else "DISABLED (beta, opt-in)"
    print(f"Feature: memory_search_fts [BETA] — {tag}")
    if not enabled:
        print("Enable via: agentic-stack <harness> --reconfigure")
        print("Or edit .agent/memory/.features.json directly.")
        return
    if not check_fts5():
        tool = fallback_tool()
        print(f"Mode: FALLBACK ({tool})")
        print("Reason: SQLite FTS5 not available in this Python build.")
        if tool == "unavailable":
            print("Also: neither rg nor grep on PATH — install ripgrep for best results.")
        return
    if not INDEX_PATH.exists():
        print("Mode: FTS5 (index not built yet — auto-builds on first search)")
        return
    conn = sqlite3.connect(INDEX_PATH)
    count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()
    size_kb = INDEX_PATH.stat().st_size // 1024
    print(f"Mode: FTS5")
    print(f"Index: {count} files indexed ({size_kb} KB)")
    print(f"Location: {INDEX_PATH}")
    print(f"Fallback available: {fallback_tool()}")


def _refuse_disabled():
    print(
        "memory_search [BETA] is disabled — opt-in only.\n"
        "Enable via onboarding:  agentic-stack <harness> --reconfigure\n"
        "Or set enabled=true for memory_search_fts in "
        ".agent/memory/.features.json",
        file=sys.stderr,
    )
    sys.exit(2)


def _print_usage():
    print("Usage [BETA, opt-in]:")
    print("  memory_search.py <query>     Search memories by keyword")
    print("  memory_search.py --rebuild   Force rebuild index")
    print("  memory_search.py --status    Show index status")


def _search_mode_and_results(query: str):
    use_fts5 = check_fts5()
    if use_fts5:
        return "FTS5", search_fts5(query)
    return fallback_tool(), search_fallback(query)


def _print_results(query: str, mode: str, results) -> None:
    if not results:
        print(f"No results for: '{query}'  [mode: {mode}]")
        return
    print(f"Results for: '{query}'  [mode: {mode}]\n")
    for filename, snippet in results:
        print(f"  {filename}")
        print(f"  {snippet}\n")


def _run_command(args):
    if not args or args[0] in ("-h", "--help"):
        _print_usage()
        return 0
    if args[0] == "--status":
        cmd_status()
        return 0
    if not feature_enabled():
        _refuse_disabled()
    if args[0] == "--rebuild":
        cmd_rebuild()
        return 0
    query = " ".join(args)
    mode, results = _search_mode_and_results(query)
    _print_results(query, mode, results)
    return 0


def main():
    sys.exit(_run_command(sys.argv[1:]))


if __name__ == "__main__":
    main()
