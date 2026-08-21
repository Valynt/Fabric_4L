#!/usr/bin/env python3
"""Push Value Fabric secrets into Infisical via the REST API.

Reads credentials and secret values from a local .env file, then upserts every
secret into Infisical using the v3 batch API.

The variable→Infisical-path mapping is derived from the canonical by-layer
schema encoded in ``.env.example`` (section headers such as ``# /shared`` and
explicit ``# Infisical path: /apps/web`` comments). This is the sole supported
path taxonomy — see ``docs/security/secrets-management.md``. Variables without
an annotation fall back to ``/shared``.

Usage:
    python scripts/push_secrets_to_infisical.py [OPTIONS]

Options:
    --env-file PATH          Path to .env file  [default: .env]
    --schema-file PATH       Path to .env.example-style schema  [default: .env.example]
    --environment NAME       Infisical environment slug  [default: Development]
    --dry-run                Print what would be pushed; make no API calls
    --include-empty          Also push secrets whose value is blank
    --path PATH              Override all secret paths with a single root path
    --skip-confirm           Skip the "are you sure?" prompt

Examples:
    # Dry run — see what will be pushed
    python scripts/push_secrets_to_infisical.py --dry-run

    # Push to Development (default)
    python scripts/push_secrets_to_infisical.py

    # Push to Production, skipping the confirmation prompt
    python scripts/push_secrets_to_infisical.py --environment Production --skip-confirm
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_SCHEMA_FILE = REPO_ROOT / ".env.example"
INFISICAL_HOST_DEFAULT = "https://app.infisical.com"

# Canonical fallback path for variables without an explicit `.env.example`
# annotation. Cross-service config lives under /shared, matching the by-layer
# taxonomy in docs/security/secrets-management.md.
DEFAULT_FALLBACK_PATH = "/shared"

# Placeholder values that should not be pushed
PLACEHOLDER_PATTERNS = [
    r"^sk-your-",
    r"^sk-ant-your-",
    r"<generate-with-",
    r"^changeme-in-production",
    r"^your-",
    r"^REPLACE_WITH_",
    r"^<CHANGE",
    r"^<GENERATE",
]

# Variables that are Infisical config themselves — never push these
SKIP_VARS = {
    "INFISICAL_CLIENT_ID",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_PROJECT_ID",
    "INFISICAL_ENVIRONMENT",
    "INFISICAL_HOST",
    "INFISICAL_SECRET_PATH",
    "INFISICAL_OVERWRITE",
}

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class Secret(NamedTuple):
    name: str
    value: str
    path: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict. Handles comments, blank lines, quotes."""
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        # Strip inline comments (after unquoted #)
        value = raw_value.split(" #")[0].strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        result[key] = value
    return result


def is_placeholder(value: str) -> bool:
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def load_schema_from_example(path: Path) -> dict[str, str]:
    """Parse .env.example-style path annotations into a variable→path map.

    Supports two annotation styles, both treated as section headers:
      - Section header:   # /shared  —  description
      - Explicit comment: # Infisical path: /apps/web
    """
    schema: dict[str, str] = {}
    if not path.exists():
        return schema

    current_path = DEFAULT_FALLBACK_PATH
    section_re = re.compile(r"^#\s*(/[/\w\-]+)\s*(?:$|[—–-])")
    explicit_re = re.compile(r"^#\s*Infisical path:\s*(/[/\w\-]+)")

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            if (m := explicit_re.match(line)) or (m := section_re.match(line)):
                current_path = m.group(1)
            continue

        if "=" not in line:
            continue

        key = line.split("=", 1)[0].strip()
        if key in SKIP_VARS:
            continue

        schema[key] = current_path

    return schema


def classify_secrets(
    env_vars: dict[str, str],
    schema: dict[str, str],
    include_empty: bool,
    path_override: str | None,
) -> tuple[list[Secret], list[str], list[str]]:
    """Return (to_push, skipped_placeholder, skipped_empty)."""
    to_push: list[Secret] = []
    skipped_placeholder: list[str] = []
    skipped_empty: list[str] = []

    for key, value in sorted(env_vars.items()):
        if key in SKIP_VARS:
            continue

        if not value:
            if include_empty:
                path = path_override or schema.get(key, DEFAULT_FALLBACK_PATH)
                to_push.append(Secret(key, value, path))
            else:
                skipped_empty.append(key)
            continue

        if is_placeholder(value):
            skipped_placeholder.append(key)
            continue

        path = path_override or schema.get(key, DEFAULT_FALLBACK_PATH)
        to_push.append(Secret(key, value, path))

    return to_push, skipped_placeholder, skipped_empty


# ---------------------------------------------------------------------------
# Infisical API
# ---------------------------------------------------------------------------


def ensure_folder(
    host: str, token: str, project_id: str, environment: str, path: str
) -> None:
    """Create an Infisical folder at `path` if it does not already exist."""
    if path in ("/", ""):
        return  # root always exists
    import json as json_mod
    import urllib.error
    import urllib.request

    # "/foo/bar" → parent="/foo", name="bar"   |   "/foo" → parent="/", name="foo"
    stripped = path.rstrip("/")
    slash = stripped.rfind("/")
    parent = stripped[:slash] or "/"
    name = stripped[slash + 1 :]

    # Ensure parent exists recursively first
    if parent != "/":
        ensure_folder(host, token, project_id, environment, parent)

    payload = json_mod.dumps(
        {
            "workspaceId": project_id,
            "environment": environment,
            "name": name,
            "path": parent,
        }
    ).encode()
    req = urllib.request.Request(
        f"{host}/api/v1/folders",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass  # created
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        # 400/409 = already exists — fine
        if exc.code in (400, 409) and (
            "already exist" in body.lower() or "exists" in body.lower()
        ):
            return
        raise RuntimeError(
            f"Failed to create folder '{path}': HTTP {exc.code}: {body}"
        ) from exc


def get_access_token(host: str, client_id: str, client_secret: str) -> str:
    try:
        import json as json_mod
        import urllib.error
        import urllib.request

        payload = json_mod.dumps(
            {"clientId": client_id, "clientSecret": client_secret}
        ).encode()
        req = urllib.request.Request(
            f"{host}/api/v1/auth/universal-auth/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json_mod.loads(resp.read())
            token = body.get("accessToken")
            if not token:
                raise RuntimeError(f"No accessToken in response: {body}")
            return token
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(
            f"\n  ERROR: Authentication failed — HTTP {exc.code}: {body}",
            file=sys.stderr,
        )
        print(
            "  Check INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET.", file=sys.stderr
        )
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - intentional catch-all around auth
        print(f"\n  ERROR: Authentication failed — {exc}", file=sys.stderr)
        print(
            "  Check INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET.", file=sys.stderr
        )
        sys.exit(1)


def upsert_secrets_batch(
    host: str,
    token: str,
    project_id: str,
    environment: str,
    path: str,
    secrets: list[Secret],
) -> dict:
    """Push a batch of secrets at the same path via POST (create-or-update)."""
    import json as json_mod
    import urllib.error
    import urllib.request

    payload = json_mod.dumps(
        {
            "workspaceId": project_id,
            "environment": environment,
            "secretPath": path,
            "secrets": [
                {"secretKey": s.name, "secretValue": s.value, "type": "shared"}
                for s in secrets
            ],
        }
    ).encode()

    req = urllib.request.Request(
        f"{host}/api/v3/secrets/batch/raw",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json_mod.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        # 400 on "already exists" — retry with PATCH (update)
        if exc.code == 400 and "already exists" in body.lower():
            return _patch_secrets_batch(
                host, token, project_id, environment, path, secrets
            )
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def _patch_secrets_batch(
    host: str,
    token: str,
    project_id: str,
    environment: str,
    path: str,
    secrets: list[Secret],
) -> dict:
    """Update existing secrets via PATCH."""
    import json as json_mod
    import urllib.request

    payload = json_mod.dumps(
        {
            "workspaceId": project_id,
            "environment": environment,
            "secretPath": path,
            "secrets": [
                {"secretKey": s.name, "secretValue": s.value, "type": "shared"}
                for s in secrets
            ],
        }
    ).encode()

    req = urllib.request.Request(
        f"{host}/api/v3/secrets/batch/raw",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="PATCH",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        import json as json_mod

        return json_mod.loads(resp.read())


def upsert_secret_individual(
    host: str,
    token: str,
    project_id: str,
    environment: str,
    secret: Secret,
) -> None:
    """Upsert a single secret (POST then PATCH on conflict)."""
    import json as json_mod
    import urllib.error
    import urllib.request

    base_payload = {
        "workspaceId": project_id,
        "environment": environment,
        "secretPath": secret.path,
        "secretValue": secret.value,
        "type": "shared",
    }

    for method in ("POST", "PATCH"):
        payload = json_mod.dumps(base_payload).encode()
        req = urllib.request.Request(
            f"{host}/api/v3/secrets/raw/{secret.name}",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=20):
                return  # success
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            if (
                method == "POST"
                and exc.code in (400, 409)
                and ("already exists" in body.lower() or "duplicate" in body.lower())
            ):
                continue  # try PATCH
            raise RuntimeError(
                f"HTTP {exc.code} [{method} {secret.name}]: {body}"
            ) from exc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push Value Fabric secrets into Infisical.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help=f"Path to .env file (default: {DEFAULT_ENV_FILE})",
    )
    parser.add_argument(
        "--schema-file",
        default=str(DEFAULT_SCHEMA_FILE),
        help=f"Path to .env.example-style schema file (default: {DEFAULT_SCHEMA_FILE})",
    )
    parser.add_argument(
        "--environment",
        default=None,
        help="Infisical environment slug (default: from .env INFISICAL_ENVIRONMENT)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan without making API calls"
    )
    parser.add_argument(
        "--include-empty", action="store_true", help="Also push keys with blank values"
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Override all secret paths with a single path (e.g. /)",
    )
    parser.add_argument(
        "--skip-confirm", action="store_true", help="Skip confirmation prompt"
    )
    args = parser.parse_args()

    env_file = Path(args.env_file)
    if not env_file.exists():
        print(f"ERROR: .env file not found: {env_file}", file=sys.stderr)
        sys.exit(1)

    # ── Read .env ──────────────────────────────────────────────────────────
    env_vars = parse_env_file(env_file)

    # ── Load canonical path schema from .env.example ─────────────────────────
    schema_file = Path(args.schema_file)
    schema = load_schema_from_example(schema_file)
    if not schema:
        print(
            f"WARNING: no schema loaded from {schema_file}; every variable will "
            f"fall back to {DEFAULT_FALLBACK_PATH}.",
            file=sys.stderr,
        )

    # ── Read Infisical credentials from .env (or real environment) ─────────
    client_id = os.getenv("INFISICAL_CLIENT_ID") or env_vars.get(
        "INFISICAL_CLIENT_ID", ""
    )
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET") or env_vars.get(
        "INFISICAL_CLIENT_SECRET", ""
    )
    project_id = os.getenv("INFISICAL_PROJECT_ID") or env_vars.get(
        "INFISICAL_PROJECT_ID", ""
    )
    environment = (
        args.environment
        or os.getenv("INFISICAL_ENVIRONMENT")
        or env_vars.get("INFISICAL_ENVIRONMENT", "Development")
    )
    host = (
        os.getenv("INFISICAL_HOST")
        or env_vars.get("INFISICAL_HOST", "")
        or INFISICAL_HOST_DEFAULT
    ).rstrip("/")

    if not (client_id and client_secret and project_id):
        print(
            "ERROR: INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET, and "
            "INFISICAL_PROJECT_ID must be set in .env or environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Classify secrets ───────────────────────────────────────────────────
    to_push, skipped_placeholder, skipped_empty = classify_secrets(
        env_vars, schema, args.include_empty, args.path
    )

    # ── Group by path ──────────────────────────────────────────────────────
    by_path: dict[str, list[Secret]] = {}
    for secret in to_push:
        by_path.setdefault(secret.path, []).append(secret)

    # ── Print plan ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Value Fabric → Infisical Secret Push")
    print(f"{'='*60}")
    print(f"  Host:        {host}")
    print(f"  Project ID:  {project_id}")
    print(f"  Environment: {environment}")
    print(f"  Source:      {env_file}")
    print(f"  Mode:        {'DRY RUN (no changes)' if args.dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    total = len(to_push)
    print(f"  Secrets to push:  {total}")
    print(f"  Skipped (placeholder values):  {len(skipped_placeholder)}")
    print(f"  Skipped (empty, use --include-empty to push):  {len(skipped_empty)}")
    print()

    for path, secrets in sorted(by_path.items()):
        print(f"  Path: {path}  ({len(secrets)} secrets)")
        for s in sorted(secrets, key=lambda x: x.name):
            masked = s.value[:6] + "…" if len(s.value) > 6 else "****"
            print(f"    {s.name:<45} {masked}")
        print()

    if skipped_placeholder:
        print("  Skipped (placeholder — replace with real values):")
        for k in sorted(skipped_placeholder):
            print(f"    {k}")
        print()

    if total == 0:
        print("  Nothing to push. Exiting.")
        return

    if args.dry_run:
        print("  DRY RUN complete — no changes made.")
        return

    # ── Confirm ────────────────────────────────────────────────────────────
    if not args.skip_confirm:
        answer = (
            input(f"  Push {total} secrets to '{environment}'? [y/N] ").strip().lower()
        )
        if answer != "y":
            print("  Aborted.")
            return

    # ── Authenticate ───────────────────────────────────────────────────────
    print("\n  Authenticating with Infisical…")
    token = get_access_token(host, client_id, client_secret)
    print("  ✓ Authenticated\n")

    # ── Push secrets path by path ──────────────────────────────────────────
    pushed = 0
    errors = 0

    for path, secrets in sorted(by_path.items()):
        print(f"  Ensuring folder {path} exists…", end="", flush=True)
        try:
            ensure_folder(host, token, project_id, environment, path)
            print(" ✓")
        except Exception as exc:  # noqa: BLE001
            print(f" ✗ ({exc}) — skipping path")
            errors += len(secrets)
            continue
        print(f"  Pushing {len(secrets)} secret(s) to {path}…", end="", flush=True)
        try:
            upsert_secrets_batch(host, token, project_id, environment, path, secrets)
            print(f"  ✓  ({len(secrets)} pushed)")
            pushed += len(secrets)
        except Exception as exc:  # noqa: BLE001
            print(f"\n  Batch failed ({exc}), retrying individually…")
            for secret in secrets:
                try:
                    upsert_secret_individual(
                        host, token, project_id, environment, secret
                    )
                    print(f"    ✓ {secret.name}")
                    pushed += 1
                except Exception as inner:  # noqa: BLE001
                    print(f"    ✗ {secret.name}: {inner}")
                    errors += 1

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Done.  Pushed: {pushed}   Errors: {errors}")
    print(f"{'='*60}\n")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
