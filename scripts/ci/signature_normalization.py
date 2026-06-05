#!/usr/bin/env python3
"""Normalize volatile CI log text into stable failure signatures.

The backlog generator uses these signatures to group repeated failures without
being confused by run-specific values such as timestamps, workspace paths, UUIDs,
ports, temporary filenames, cache keys, line numbers, and commit SHAs.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Iterable, Mapping, MutableMapping, Sequence

MAX_SUMMARY_CHARS = 240


@dataclass(frozen=True)
class NormalizedSignature:
    """Stable representation of a CI failure log."""

    normalized_text: str
    normalized_signature_hash: str
    signature_summary: str
    token_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SignaturePattern:
    name: str
    pattern: re.Pattern[str]
    replacement: str


# Order matters: specific path/cache patterns should run before broad numbers or
# SHA-like hex patterns so the readable summary preserves useful context.
_PATTERNS: tuple[SignaturePattern, ...] = (
    SignaturePattern(
        "workspace_path",
        re.compile(
            r"(?i)(?:"
            r"/workspace/[^/\s:'\")\]]+"
            r"|/home/runner/work/[^/\s:'\")\]]+/[^/\s:'\")\]]+"
            r"|/__w/[^/\s:'\")\]]+/[^/\s:'\")\]]+"
            r"|/github/workspace"
            r"|/Users/runner/work/[^/\s:'\")\]]+/[^/\s:'\")\]]+"
            r")"
        ),
        "<workspace_path>",
    ),
    SignaturePattern(
        "temp_filename",
        re.compile(
            r"(?i)(?:[A-Z]:\\[^\s:'\")\]]*|/)(?:tmp|temp|var/folders)"
            r"(?:[\\/][^\s:'\")\]]+)+"
        ),
        "<temp_path>",
    ),
    SignaturePattern(
        "package_cache_key",
        re.compile(
            r"(?i)\b(?:pnpm|npm|yarn|pip|uv|poetry|cargo|gradle|maven|go|node)[-_ ]?"
            r"(?:cache|store)[-_ ]?(?:key|id)?[:= ]+[^\s,;]+"
        ),
        "<package_cache_key>",
    ),
    SignaturePattern(
        "package_cache_key",
        re.compile(r"(?i)\b(?:setup-node|actions/cache|cache)[-_ ]?key[:= ]+[^\s,;]+"),
        "<package_cache_key>",
    ),
    SignaturePattern(
        "timestamp",
        re.compile(
            r"\b\d{4}-\d{2}-\d{2}[T ][0-2]\d:[0-5]\d:[0-5]\d"
            r"(?:\.\d+)?(?:Z|[+-][0-2]\d:?[0-5]\d)?\b"
        ),
        "<timestamp>",
    ),
    SignaturePattern(
        "timestamp",
        re.compile(
            r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),? \d{1,2} \w{3} \d{4} [0-2]?\d:[0-5]\d:[0-5]\d GMT\b"
        ),
        "<timestamp>",
    ),
    SignaturePattern(
        "uuid",
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
        ),
        "<uuid>",
    ),
    SignaturePattern(
        "run_id",
        re.compile(
            r"(?i)\b(?:run|run_id|run-id|github_run_id|attempt|job_id|job-id)[:=# ]+\d{5,}\b"
        ),
        "<run_id>",
    ),
    SignaturePattern(
        "memory_address",
        re.compile(r"\b0x[0-9a-fA-F]{6,}\b"),
        "<memory_address>",
    ),
    SignaturePattern(
        "commit_sha",
        re.compile(r"(?i)\b(?:commit|sha|revision|ref)[:= ]+[0-9a-f]{7,40}\b"),
        "<commit_sha>",
    ),
    SignaturePattern(
        "commit_sha",
        re.compile(r"(?<![\w-])[0-9a-f]{40}(?![\w-])", re.IGNORECASE),
        "<commit_sha>",
    ),
    SignaturePattern(
        "port",
        re.compile(r"(?i)\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0|::1)(?::\d{2,5})\b"),
        "<host>:<port>",
    ),
    SignaturePattern(
        "port",
        re.compile(
            r"(?i)\b(?:port|PORT|EADDRINUSE|address already in use)[:= ]+\d{2,5}\b"
        ),
        "<port>",
    ),
    SignaturePattern(
        "line_column",
        re.compile(r"(?P<path><(?:workspace_path|temp_path)>):\d+(?::\d+)?"),
        r"\g<path>:<line>:<col>",
    ),
    SignaturePattern(
        "line_column",
        re.compile(
            r"(?P<file>[^\s:'\")\]]+\.(?:py|pyi|ts|tsx|js|jsx|mjs|cjs|rs|go|java|kt|rb|php|cs|cpp|c|h|hpp|yaml|yml|json|toml|md)):(?P<line>\d+)(?::(?P<col>\d+))?"
        ),
        r"\g<file>:<line>:<col>",
    ),
    SignaturePattern(
        "line_column",
        re.compile(r"(?i)\bline\s+\d+(?:,?\s*(?:column|col)\s+\d+)?\b"),
        "line <line>",
    ),
    SignaturePattern(
        "line_column",
        re.compile(r"(?i)\b(?:column|col)\s+\d+\b"),
        "col <col>",
    ),
    SignaturePattern(
        "temp_filename",
        re.compile(r"(?i)\b(?:tmp|temp|pytest-|tmpfile)[A-Za-z0-9_.-]{6,}\b"),
        "<temp_file>",
    ),
    SignaturePattern(
        "run_id",
        re.compile(r"(?i)\bgh[a-z_]*[_-]?run[_-]?[0-9]{5,}\b"),
        "<run_id>",
    ),
)

_LINE_NOISE = re.compile(
    r"^\s*(?:\[?debug\]?|\[?notice\]?|\[?info\]?|##\[group\]|##\[endgroup\])",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_ci_log_signature(log_text: str) -> NormalizedSignature:
    """Return normalized text, a SHA-256 hash, and a readable summary.

    The hash is computed from the fully normalized text. The summary is a compact
    first meaningful line/snippet from that same normalized text, making backlog
    items readable while keeping recurrence grouping deterministic.
    """

    normalized = log_text.replace("\r\n", "\n").replace("\r", "\n")
    counts: Counter[str] = Counter()

    for item in _PATTERNS:
        normalized, count = item.pattern.subn(item.replacement, normalized)
        if count:
            counts[item.name] += count

    normalized_lines = []
    for line in normalized.splitlines():
        line = _WHITESPACE.sub(" ", line).strip()
        if not line or _LINE_NOISE.match(line):
            continue
        normalized_lines.append(line)
    normalized = _BLANK_LINES.sub("\n\n", "\n".join(normalized_lines)).strip()

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return NormalizedSignature(
        normalized_text=normalized,
        normalized_signature_hash=digest,
        signature_summary=_build_summary(normalized),
        token_counts=dict(sorted(counts.items())),
    )


def _build_summary(normalized_text: str) -> str:
    for line in normalized_text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:MAX_SUMMARY_CHARS]
    return ""


def recurrence_key(record: Mapping[str, object]) -> tuple[str, str, str, str]:
    """Return the backlog recurrence key for a classified CI failure record."""

    workflow = str(record.get("workflow") or record.get("workflow_name") or "")
    job = str(record.get("job") or record.get("job_name") or "")
    signature_hash = str(
        record.get("normalized_signature_hash")
        or record.get("signature_hash")
        or record.get("hash")
        or ""
    )
    primary_category = str(
        record.get("primary_category")
        or record.get("category_key")
        or record.get("category")
        or "UNKNOWN"
    )
    return workflow, job, signature_hash, primary_category


def attach_recurrence_counts(
    records: Sequence[MutableMapping[str, object]],
) -> list[MutableMapping[str, object]]:
    """Annotate records with recurrence_count grouped by the backlog recurrence key."""

    counts = Counter(recurrence_key(record) for record in records)
    for record in records:
        record["recurrence_count"] = counts[recurrence_key(record)]
    return list(records)


def summarize_recurrences(
    records: Iterable[Mapping[str, object]],
) -> dict[tuple[str, str, str, str], int]:
    """Count failures by workflow + job + normalized signature hash + category."""

    return dict(Counter(recurrence_key(record) for record in records))
