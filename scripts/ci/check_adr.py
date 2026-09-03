#!/usr/bin/env python3
"""Validate ADR registry, indexes, numbering, and related-code links."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_adr_numbering import numbering_failures

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]
REGISTRY_PATH = Path("docs/decisions/adr-registry.yaml")

DECISIONS_FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
DECISIONS_HEADER_RE = re.compile(r"^#\s+ADR-(\d{4}):\s+.+$")
INDEX_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SKIP_NAMES = frozenset({"readme.md", "template.md"})
REQUIRED_CORPORA = ("architecture", "decisions")
URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

ARCHITECTURE_INDEX_HEADING = "## ADR Index"
DECISIONS_INDEX_HEADING = "## Index"


@dataclass(frozen=True)
class ContentRule:
    path: str
    pattern: str


@dataclass(frozen=True)
class RegistryEntry:
    id: str
    corpus: str
    path: str
    status: str
    related: list[str] = field(default_factory=list)
    must_contain: list[ContentRule] = field(default_factory=list)
    must_not_contain: list[ContentRule] = field(default_factory=list)


@dataclass(frozen=True)
class CorpusConfig:
    name: str
    dir: str
    index: str


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_status(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^[^\w]+", "", text)
    text = text.lower().strip()
    if text.startswith("superseded"):
        return "superseded"
    if text.startswith("deprecated"):
        return "deprecated"
    if text.startswith(("proposed", "draft")):
        return "proposed"
    if text.startswith("accepted"):
        return "accepted"
    return text.split()[0] if text else ""


def _rules(raw: Any, *, field_name: str, entry_id: str, failures: list[str]) -> list[ContentRule]:
    if not raw:
        return []
    if not isinstance(raw, list):
        failures.append(f"{entry_id}: {field_name} must be a list")
        return []
    rules: list[ContentRule] = []
    for item in raw:
        if not isinstance(item, dict) or "path" not in item or "pattern" not in item:
            failures.append(f"{entry_id}: {field_name} entries must have path and pattern")
            continue
        rules.append(ContentRule(path=str(item["path"]).strip(), pattern=str(item["pattern"])))
    return rules


def load_registry(repo_root: Path, failures: list[str]) -> tuple[dict[str, CorpusConfig], list[RegistryEntry]]:
    path = repo_root / REGISTRY_PATH
    if not path.exists():
        failures.append(f"missing ADR registry: {REGISTRY_PATH.as_posix()}")
        return {}, []
    if yaml is None:
        failures.append("PyYAML is required to load docs/decisions/adr-registry.yaml")
        return {}, []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        failures.append("ADR registry must be a mapping")
        return {}, []
    if payload.get("version") != 1:
        failures.append("ADR registry version must be 1")

    corpora_raw = payload.get("corpora") or {}
    if not isinstance(corpora_raw, dict):
        failures.append("ADR registry corpora must be a mapping")
        corpora_raw = {}
    corpora: dict[str, CorpusConfig] = {}
    for name, body in corpora_raw.items():
        if not isinstance(body, dict):
            failures.append(f"corpus {name} must be a mapping")
            continue
        corpora[name] = CorpusConfig(
            name=name,
            dir=str(body.get("dir", "")).strip().strip("/"),
            index=str(body.get("index", "")).strip().strip("/"),
        )
    if not corpora:
        failures.append("ADR registry defines no corpora")
    for name in REQUIRED_CORPORA:
        if name not in corpora:
            failures.append(f"ADR registry must define the {name} corpus")

    entries: list[RegistryEntry] = []
    raw_entries = payload.get("entries") or []
    if not isinstance(raw_entries, list):
        failures.append("ADR registry entries must be a list")
        return corpora, []
    required_fields = {"id", "corpus", "path", "status", "related"}
    for raw in raw_entries:
        if not isinstance(raw, dict):
            failures.append("registry entry must be a mapping")
            continue
        missing = sorted(required_fields - raw.keys())
        if missing:
            failures.append(
                "registry entry is missing required field(s): " + ", ".join(missing)
            )
        corpus = str(raw.get("corpus", "")).strip()
        entry_id = raw.get("id")
        if corpus == "decisions":
            # Keep zero-padded decision IDs as strings.  Silently accepting an
            # integer here would let YAML coercion hide an invalid registry.
            if not isinstance(entry_id, str):
                failures.append(
                    f"{entry_id}: decisions registry IDs must be quoted strings"
                )
                entry_id = str(entry_id).strip()
            else:
                entry_id = entry_id.strip()
            if not re.fullmatch(r"\d{4}", entry_id):
                failures.append(f"{entry_id}: decisions registry ID must be four digits")
        else:
            entry_id = str(entry_id).strip()
        related_raw = raw.get("related") or []
        related = [str(item).strip().replace("\\", "/") for item in related_raw] if isinstance(related_raw, list) else []
        if not isinstance(related_raw, list):
            failures.append(f"{entry_id}: related must be a list")
        entries.append(
            RegistryEntry(
                id=entry_id,
                corpus=corpus,
                path=str(raw.get("path", "")).strip().replace("\\", "/"),
                status=normalize_status(str(raw.get("status", ""))),
                related=related,
                must_contain=_rules(raw.get("must_contain"), field_name="must_contain", entry_id=entry_id, failures=failures),
                must_not_contain=_rules(
                    raw.get("must_not_contain"),
                    field_name="must_not_contain",
                    entry_id=entry_id,
                    failures=failures,
                ),
            )
        )
    return corpora, entries


def discover_corpus_files(repo_root: Path, corpus: CorpusConfig) -> list[Path]:
    directory = repo_root / corpus.dir
    if not directory.exists():
        return []
    files: list[Path] = []
    for path in sorted(directory.glob("*.md")):
        if path.name.lower() in SKIP_NAMES:
            continue
        if corpus.name == "architecture" and not path.name.upper().startswith("ADR-"):
            continue
        # Decision corpora intentionally reach this point with malformed names
        # so the numbering checker can report them instead of excluding them.
        files.append(path)
    return files


def _index_link_resolves(index_path: Path, href: str) -> bool:
    target = href.split("#", 1)[0].strip()
    if not target or URI_SCHEME_RE.match(target):
        return True
    return (index_path.parent / target).exists()


def parse_index_rows(index_path: Path, heading: str) -> list[tuple[str, str, str, str]]:
    if not index_path.exists():
        return []
    lines = index_path.read_text(encoding="utf-8").splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx + 1
            break
    if start is None:
        return []
    rows: list[tuple[str, str, str]] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"adr", "title"}:
            continue
        match = INDEX_LINK_RE.search(cells[0])
        if not match:
            continue
        href = match.group(2).strip()
        rows.append((match.group(1).strip(), href, Path(href).name, cells[2]))
    return rows


def decisions_numbering_failures(repo_root: Path, files: list[Path]) -> list[str]:
    failures: list[str] = []
    by_id: dict[int, list[Path]] = {}
    for path in files:
        rel = _rel(path, repo_root)
        name_match = DECISIONS_FILENAME_RE.match(path.name)
        if not name_match:
            failures.append(f"Invalid decisions ADR filename format: {rel}")
            continue
        file_id = name_match.group(1)
        header_id = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                match = DECISIONS_HEADER_RE.match(line.strip())
                header_id = match.group(1) if match else None
                break
        if header_id is None:
            failures.append(f"Missing/invalid decisions ADR header ('# ADR-####: ...'): {rel}")
            continue
        if file_id != header_id:
            failures.append(
                f"Filename/header ADR ID mismatch: {rel} (filename {file_id}, header ADR-{header_id})"
            )
        by_id.setdefault(int(file_id), []).append(path)

    for id_num, paths in sorted(by_id.items()):
        if len(paths) > 1:
            labeled = ", ".join(_rel(path, repo_root) for path in paths)
            failures.append(f"Duplicate decisions ADR ID {id_num:04d}: {labeled}")

    ids = sorted(by_id.keys())
    if ids:
        expected = list(range(1, len(ids) + 1))
        if ids != expected:
            failures.append(
                "decisions sequence policy violation. "
                f"Expected contiguous IDs {expected[0]:04d}..{expected[-1]:04d}, got: "
                + ", ".join(f"{n:04d}" for n in ids)
            )
    return failures


def _apply_content_rules(repo_root: Path, entry: RegistryEntry, failures: list[str]) -> None:
    for kind, rules in (("must_contain", entry.must_contain), ("must_not_contain", entry.must_not_contain)):
        for rule in rules:
            target = repo_root / rule.path
            if not target.exists():
                failures.append(f"{entry.id}: {kind} path does not exist: {rule.path}")
                continue
            if target.is_dir():
                failures.append(f"{entry.id}: {kind} path is a directory (file required): {rule.path}")
                continue
            text = target.read_text(encoding="utf-8")
            try:
                found = re.search(rule.pattern, text) is not None
            except re.error as exc:
                failures.append(f"{entry.id}: invalid {kind} pattern /{rule.pattern}/ ({exc})")
                continue
            if kind == "must_contain" and not found:
                failures.append(f"{entry.id}: must_contain missed /{rule.pattern}/ in {rule.path}")
            if kind == "must_not_contain" and found:
                failures.append(f"{entry.id}: must_not_contain hit /{rule.pattern}/ in {rule.path}")


def check_adr(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    failures: list[str] = []
    failures.extend(numbering_failures(root))

    corpora, entries = load_registry(root, failures)

    files_by_corpus: dict[str, list[Path]] = {}
    for name, corpus in corpora.items():
        files_by_corpus[name] = discover_corpus_files(root, corpus)
        if not files_by_corpus[name]:
            failures.append(f"corpus {name} has no ADR markdown files under {corpus.dir}")
        if name == "decisions":
            failures.extend(decisions_numbering_failures(root, files_by_corpus[name]))

    discovered: dict[str, Path] = {}
    for name, files in files_by_corpus.items():
        for path in files:
            discovered[_rel(path, root)] = path

    registry_by_path: dict[str, RegistryEntry] = {}
    seen_ids: set[str] = set()
    for entry in entries:
        if entry.id in seen_ids:
            failures.append(f"duplicate registry id: {entry.id}")
        seen_ids.add(entry.id)
        if entry.corpus not in corpora:
            failures.append(f"{entry.id}: unknown corpus {entry.corpus}")
            continue
        corpus = corpora[entry.corpus]
        expected_prefix = corpus.dir.rstrip("/") + "/"
        if not entry.path.startswith(expected_prefix):
            failures.append(f"{entry.id}: path {entry.path} is not under {corpus.dir}")
        if entry.path in registry_by_path:
            failures.append(f"duplicate registry path: {entry.path}")
        registry_by_path[entry.path] = entry

        filename = Path(entry.path).name
        if entry.corpus == "architecture":
            match = re.match(r"^ADR-(\d{3})-", filename)
            if not match or f"ADR-{match.group(1)}" != entry.id:
                failures.append(f"{entry.id}: filename {filename} does not match id")
        elif entry.corpus == "decisions":
            match = DECISIONS_FILENAME_RE.match(filename)
            if not match or match.group(1) != entry.id:
                failures.append(f"{entry.id}: filename {filename} does not match id")

        if entry.status == "accepted" and not entry.related:
            failures.append(f"{entry.id}: accepted ADR requires at least one related path")
        for related in entry.related:
            target = root / related
            if not target.exists():
                failures.append(f"{entry.id}: related path does not exist: {related}")

        _apply_content_rules(root, entry, failures)

        if entry.path not in discovered:
            failures.append(f"{entry.id}: registry path not found on disk: {entry.path}")

    for rel in sorted(discovered):
        if rel not in registry_by_path:
            failures.append(f"ADR file not in registry: {rel}")

    for name, corpus in corpora.items():
        heading = ARCHITECTURE_INDEX_HEADING if name == "architecture" else DECISIONS_INDEX_HEADING
        index_path = root / corpus.index
        if not index_path.exists():
            failures.append(f"{name} index missing: {corpus.index}")
            continue
        rows = parse_index_rows(index_path, heading)
        indexed_files = {filename for _, _, filename, _ in rows}
        corpus_files = {path.name for path in files_by_corpus.get(name, [])}
        for filename in sorted(corpus_files - indexed_files):
            failures.append(f"{name} index missing {filename}")
        for filename in sorted(indexed_files - corpus_files):
            failures.append(f"{name} index extra row {filename}")
        for link_text, href, filename, status_cell in rows:
            if not _index_link_resolves(index_path, href):
                failures.append(f"{name} index link does not resolve: {href}")
            entry = next((item for item in entries if Path(item.path).name == filename), None)
            if entry is None:
                continue
            if normalize_status(status_cell) != entry.status:
                failures.append(
                    f"{entry.id}: index status {status_cell!r} does not match registry {entry.status!r}"
                )
            if name == "architecture" and not link_text.startswith(entry.id):
                failures.append(f"{entry.id}: index link text {link_text!r} does not match id")
            if name == "decisions" and link_text.zfill(4) != entry.id:
                failures.append(f"{entry.id}: index link text {link_text!r} does not match id")

    return failures


def main() -> int:
    failures = check_adr(REPO_ROOT)
    if failures:
        print("ADR registry check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ADR registry check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
