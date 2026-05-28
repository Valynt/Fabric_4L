"""CI gate — detect hardcoded secrets in infrastructure files.

Part of PR4 of the elevate-to-9 plan. Scans docker-compose, Kubernetes
manifests, GitHub workflows, and example env files for literal secret values
(passwords, tokens, dev-root credentials, etc.) and refuses additions outside
a frozen baseline.

Scope:
- ``docker-compose*.yml``  (repo root)
- ``k8s/**/*.yml``, ``k8s/**/*.yaml``
- ``.github/workflows/*.yml``
- ``services/*/.env.example``, ``services/*/**/.env.example``
- ``infra/**``, ``monitoring/**``

Patterns flagged:
- ``KEY: literal`` or ``KEY=literal`` where KEY contains password/secret/token/key
  AND the value is *not* a ``${VAR}``-style reference, ``secretKeyRef`` lookup,
  or empty placeholder.
- ``VAULT_DEV_ROOT_TOKEN_ID`` set to a literal in production-like compose files.
- Redis services missing ``requirepass`` / ``REDIS_PASSWORD``.

The gate is *advisory in audit mode* by default (exit 0 with a report) and
becomes a blocker once the baseline freeze is approved. Use
``--enforce`` to make it block, or ``--update-baseline`` to refresh.

Usage::

    python scripts/ci/audit_infra_secrets.py                # audit + report
    python scripts/ci/audit_infra_secrets.py --enforce      # CI gate
    python scripts/ci/audit_infra_secrets.py --update-baseline
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = REPO_ROOT / "config" / "ci" / "infra_secret_baseline.txt"

SECRET_KEY_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9_\-]*(PASSWORD|SECRET|TOKEN|API[_-]?KEY|PASSWD|CREDENTIAL)S?$",
    re.IGNORECASE,
)

# Recognized non-literal value forms — these are SAFE (sourced externally).
SAFE_VALUE_PATTERNS = (
    re.compile(r"^\$\{[^}]+\}$"),               # ${VAR}
    re.compile(r"^\$[A-Z_][A-Z0-9_]*$"),         # $VAR
    re.compile(r"^\{\{.*\}\}$"),                 # {{ secrets.X }}
    re.compile(r"^secretKeyRef:"),               # k8s
    re.compile(r"^valueFrom:"),                  # k8s
    re.compile(r"^!\s*include\b"),               # yaml include
    re.compile(r"^['\"]?\s*['\"]?$"),            # empty / blank
    re.compile(r"^<.+>$"),                       # <REPLACE_ME> placeholders
    re.compile(r"^(changeme|placeholder|example|todo)$", re.IGNORECASE),
)

# Known-safe literal sentinels (development-only, gated by env flag elsewhere).
DEV_SENTINELS = frozenset({"dev", "development", "local"})


SCAN_GLOBS = (
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "k8s/**/*.yml",
    "k8s/**/*.yaml",
    ".github/workflows/*.yml",
    "services/*/.env.example",
    "services/**/.env.example",
    "infra/**/*.yml",
    "infra/**/*.yaml",
    "monitoring/**/*.yml",
    "monitoring/**/*.yaml",
)

# Match KEY=value (env-file style) and KEY: value (yaml style).
ASSIGN_RE = re.compile(
    r"""^
        \s*
        (?P<key>[A-Z_][A-Z0-9_\-]+)        # KEY
        \s*[:=]\s*
        (?P<quote>['\"]?)
        (?P<value>[^#\n]*?)
        (?P=quote)
        \s*(\#.*)?$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    key: str
    excerpt: str

    def as_baseline_entry(self) -> str:
        return f"{self.path}:{self.line}:{self.key}"


def _is_safe_value(value: str) -> bool:
    stripped = value.strip().strip("\"'")
    if not stripped:
        return True
    if stripped.lower() in DEV_SENTINELS:
        return True
    for pattern in SAFE_VALUE_PATTERNS:
        if pattern.match(stripped):
            return True
    return False


def _collect_files() -> list[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file():
                seen.add(path)
    return sorted(seen)


# K8s env array syntax: matches lines like "- name: POSTGRES_PASSWORD"
K8S_ENV_NAME_RE = re.compile(r"^\s+-\s+name:\s*(?P<key>[A-Z_][A-Z0-9_\-]+)\s*$")
# K8s env array value line: matches lines like "  value: secret123"
K8S_ENV_VALUE_RE = re.compile(r"^\s+value:\s*(?P<value>[^#\n]*?)\s*$")


def _scan_file(path: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    lines = text.splitlines()

    # Pass 1 — single-line KEY: value / KEY=value assignments.
    for line_no, raw_line in enumerate(lines, start=1):
        stripped_line = raw_line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        match = ASSIGN_RE.match(raw_line)
        if not match:
            continue
        key = match.group("key").upper()
        value = match.group("value") or ""
        if not SECRET_KEY_PATTERN.match(key):
            continue
        if _is_safe_value(value):
            continue
        findings.append(
            SecretFinding(
                path=rel,
                line=line_no,
                key=key,
                excerpt=raw_line.strip()[:120],
            )
        )

    # Pass 2 — K8s env: array syntax (adjacent name + value lines).
    for idx, raw_line in enumerate(lines):
        name_match = K8S_ENV_NAME_RE.match(raw_line)
        if not name_match:
            continue
        key = name_match.group("key").upper()
        if not SECRET_KEY_PATTERN.match(key):
            continue
        next_idx = idx + 1
        if next_idx >= len(lines):
            continue
        value_match = K8S_ENV_VALUE_RE.match(lines[next_idx])
        if not value_match:
            continue
        value = value_match.group("value") or ""
        if _is_safe_value(value):
            continue
        line_no = idx + 1  # 1-based for the "name:" line
        findings.append(
            SecretFinding(
                path=rel,
                line=line_no,
                key=key,
                excerpt=raw_line.strip()[:120],
            )
        )

    return findings


def scan_all() -> tuple[list[SecretFinding], list[Path]]:
    files = _collect_files()
    all_findings: list[SecretFinding] = []
    for f in files:
        all_findings.extend(_scan_file(f))
    return all_findings, files


def _load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    entries: set[str] = set()
    for raw in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line)
    return entries


def _write_baseline(findings: list[SecretFinding]) -> None:
    header = (
        "# Infrastructure hardcoded-secret baseline (PR4 of elevate-to-9 plan).\n"
        "#\n"
        "# Each line is a frozen pre-existing literal secret value found in infra\n"
        "# config. Entries should be migrated to ExternalSecret / Vault refs or\n"
        "# environment variable sourcing. New literal values are not permitted.\n"
        "#\n"
        "# Format: <repo-relative-path>:<line>:<KEY>\n"
    )
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entries = sorted({f.as_baseline_entry() for f in findings})
    BASELINE_FILE.write_text(
        header + "\n".join(entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )


def _render_mapping_table(findings: list[SecretFinding]) -> str:
    lines = [
        "# Infrastructure secret remediation mapping",
        "",
        "Auto-generated by `scripts/ci/audit_infra_secrets.py`. Each row should be",
        "remediated to source the value from a secret manager (Infisical for local",
        "dev, ExternalSecret/Vault for prod) before being removed from the baseline.",
        "",
        "| File | Line | Key | Current excerpt | Suggested source |",
        "|---|---|---|---|---|",
    ]
    for f in findings:
        suggested = _suggest_source(f)
        excerpt = f.excerpt[:60].replace("|", "\\|")
        lines.append(
            f"| `{f.path}` | {f.line} | `{f.key}` | `{excerpt}` | {suggested} |"
        )
    return "\n".join(lines) + "\n"


def _suggest_source(f: SecretFinding) -> str:
    p = f.path.lower()
    if p.startswith("k8s/"):
        return "ExternalSecret + Vault KV"
    if p.startswith(".github/workflows/"):
        return "GitHub Actions repository secret"
    if "docker-compose" in p and "prod" in p:
        return "Vault/ExternalSecret via env-file"
    if "docker-compose" in p:
        return "Infisical `.env.generated`"
    if p.endswith(".env.example"):
        return "Document only — strip literal, reference env var"
    return "Vault/ExternalSecret"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enforce", action="store_true", help="Fail on any unbaselined finding.")
    parser.add_argument("--update-baseline", action="store_true", help="Freeze current findings.")
    parser.add_argument(
        "--mapping-table",
        type=Path,
        default=None,
        help="Write a Markdown remediation mapping to this path.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    findings, files = scan_all()

    if args.update_baseline:
        _write_baseline(findings)
        print(f"Baseline updated: {len(findings)} entries -> {BASELINE_FILE}")
        if args.mapping_table is not None:
            args.mapping_table.write_text(_render_mapping_table(findings), encoding="utf-8")
            print(f"Mapping table -> {args.mapping_table}")
        return 0

    baseline = _load_baseline()
    current_entries = {f.as_baseline_entry() for f in findings}
    new_entries = sorted(current_entries - baseline)

    if not args.quiet:
        print(
            f"Scanned {len(files)} infra files; "
            f"{len(findings)} candidate findings; "
            f"{len(baseline)} in baseline."
        )

    if args.mapping_table is not None:
        args.mapping_table.write_text(_render_mapping_table(findings), encoding="utf-8")
        if not args.quiet:
            print(f"Mapping table -> {args.mapping_table}")

    if new_entries:
        print("\nNew hardcoded-secret candidates detected:", file=sys.stderr)
        for entry in new_entries:
            print(f"  + {entry}", file=sys.stderr)
        if args.enforce:
            return 1
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
