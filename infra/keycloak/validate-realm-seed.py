#!/usr/bin/env python3
"""Fail-fast validation for Keycloak dev realm import before Keycloak starts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLACEHOLDER_MARKERS = (
    "do-not-use-in-production",
    "changeme",
    "placeholder",
)


def fail(message: str) -> None:
    print(f"[keycloak-seed-check] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    realm_path = Path(os.environ.get("KC_REALM_IMPORT_LOCATION", "/opt/keycloak/data/import/fabric-realm.json"))
    if not realm_path.exists():
        fail(f"realm import file not found: {realm_path}")

    raw = realm_path.read_text(encoding="utf-8")
    for marker in PLACEHOLDER_MARKERS:
        if marker in raw:
            fail(f"placeholder marker '{marker}' found in realm import file {realm_path}")

    realm = json.loads(raw)

    for client in realm.get("clients", []):
        client_id = client.get("clientId", "<unknown>")
        if "secret" in client:
            fail(f"client '{client_id}' contains embedded secret in committed realm file")

    for user in realm.get("users", []):
        username = user.get("username", "<unknown>")
        for credential in user.get("credentials", []):
            if credential.get("type") != "password":
                continue
            if credential.get("temporary") is False:
                fail(f"user '{username}' has password credential with temporary=false")

    print(f"[keycloak-seed-check] OK: validated realm import file {realm_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
