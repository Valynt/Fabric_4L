#!/usr/bin/env python3
"""Fail CI when Keycloak realm seed data contains static or insecure credentials."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_REALM_FILES = [Path("infra/keycloak/fabric-realm.json")]
BANNED_LITERALS = {
    "do-not-use-in-production",
    "fabric-frontend-secret-do-not-use-in-production",
    "fabric-api-secret-do-not-use-in-production",
}
BANNED_USER_CREDENTIALS = {
    ("admin", "admin"),
    ("analyst", "analyst"),
}


def load_realm(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: {path} is not valid JSON: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--realm-file", action="append", dest="realm_files")
    args = parser.parse_args()

    realm_files = [Path(p) for p in args.realm_files] if args.realm_files else DEFAULT_REALM_FILES

    errors: list[str] = []
    for realm_file in realm_files:
        realm = load_realm(realm_file)
        raw = realm_file.read_text(encoding="utf-8")

        for literal in sorted(BANNED_LITERALS):
            if literal in raw:
                errors.append(f"{realm_file}: banned literal present: {literal}")

        for client in realm.get("clients", []):
            client_id = client.get("clientId", "<unknown>")
            if "secret" in client:
                errors.append(f"{realm_file}: client '{client_id}' must not embed a committed secret")

        for user in realm.get("users", []):
            username = user.get("username", "<unknown>")
            for credential in user.get("credentials", []):
                if credential.get("type") != "password":
                    continue
                if credential.get("temporary") is False:
                    errors.append(
                        f"{realm_file}: user '{username}' has password credential with temporary=false"
                    )
                value = credential.get("value")
                if isinstance(value, str) and (username, value) in BANNED_USER_CREDENTIALS:
                    errors.append(
                        f"{realm_file}: user '{username}' uses banned default password literal '{value}'"
                    )

    if errors:
        print("ERROR: Keycloak realm seed security violations detected:", file=sys.stderr)
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        return 1

    print("OK: Keycloak realm seed security checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
