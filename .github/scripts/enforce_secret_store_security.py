#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
import re

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCAN_PATHS = [ROOT / "k8s" / "external-secrets", ROOT / "k8s" / "envs" / "prod", ROOT / "k8s" / "envs" / "staging"]
BANNED_TOKENS = {"root", "changeme", "replace-me", "dev-token", "vault-dev-token"}
VAULT_DEV_ROOT_LITERAL_PATTERN = re.compile(r"VAULT_DEV_ROOT_TOKEN_ID\s*[:=]\s*[\"']?root[\"']?", re.IGNORECASE)


def iter_yaml_docs(path: Path):
    for file in path.rglob("*.y*ml"):
        with file.open("r", encoding="utf-8") as f:
            for idx, doc in enumerate(yaml.safe_load_all(f), start=1):
                if isinstance(doc, dict):
                    yield file, idx, doc


def check() -> list[str]:
    errors: list[str] = []
    for base in SCAN_PATHS:
        if not base.exists():
            continue
        for file, _, doc in iter_yaml_docs(base):
            original_text = file.read_text(encoding="utf-8")
            text = original_text.lower()
            if "vault_dev_" in text:
                errors.append(f"{file}: contains forbidden VAULT_DEV_* reference")
            if VAULT_DEV_ROOT_LITERAL_PATTERN.search(original_text):
                errors.append(f"{file}: contains forbidden VAULT_DEV_ROOT_TOKEN_ID=root literal")
            for token in BANNED_TOKENS:
                if token in text and "dev-only" not in str(file):
                    errors.append(f"{file}: contains dev token placeholder '{token}'")

            kind = doc.get("kind")
            if kind not in {"ClusterSecretStore", "SecretStore"}:
                continue
            vault = (((doc.get("spec") or {}).get("provider") or {}).get("vault") or {})
            server = str(vault.get("server", ""))
            if not server.startswith("https://"):
                errors.append(f"{file}: {kind} must use https:// vault server")
            ca = vault.get("caProvider")
            if not isinstance(ca, dict) or not ca.get("name") or not ca.get("key"):
                errors.append(f"{file}: {kind} must define caProvider name/key for CA pinning")
            auth = (vault.get("auth") or {}).get("kubernetes") or {}
            sa_ref = auth.get("serviceAccountRef") if isinstance(auth, dict) else None
            if not isinstance(sa_ref, dict) or not sa_ref.get("name"):
                errors.append(f"{file}: {kind} must define auth.kubernetes.serviceAccountRef.name")
            annotations = (doc.get("metadata") or {}).get("annotations") or {}
            if annotations.get("security.valuefabric.io/mtls-required") != "true":
                errors.append(f"{file}: {kind} must set metadata.annotations.security.valuefabric.io/mtls-required='true'")
    return errors


if __name__ == "__main__":
    failures = check()
    if failures:
        print("FAIL: secret store security policy violations detected")
        for f in failures:
            print(f" - {f}")
        sys.exit(1)
    print("PASS: secret store security policy checks passed")
