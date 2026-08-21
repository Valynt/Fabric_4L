#!/usr/bin/env python3
"""Create Infisical folders for staging and production environments.

Creates the canonical by-layer folder structure used by the Fabric_4L runtime
(see docs/security/secrets-management.md) and copies dev secrets into each
target environment. Uses the Infisical REST API.

Requires environment variables:
  INFISICAL_CLIENT_ID
  INFISICAL_CLIENT_SECRET

Usage:
  python scripts/security/setup_infisical_folders.py
"""

import json
import os
import urllib.error
import urllib.request

INFISICAL_API_URL = "https://app.infisical.com/api"
PROJECT_ID = "d0dde515-abae-4f6a-a01c-75e7b713a9ff"

# Canonical by-layer secret path taxonomy. Must stay in sync with
# docs/security/secrets-management.md and the .env.example section headers.
# Each entry is (path, needs_parent_split): paths containing a "/" are
# nested folders that must be created parent-first via the Infisical API
# (which models folder name and parent path separately).
FOLDERS_TO_CREATE = [
    ("shared", False),
    ("shared/auth", True),
    ("infra", False),
    ("layer1-ingestion", False),
    ("layer2-extraction", False),
    ("layer2-5-signal-refinery", False),
    ("layer3-knowledge", False),
    ("layer4-agents", False),
    ("layer5-ground-truth", False),
    ("layer6-benchmarks", False),
    ("layer7-billing", False),
    ("apps", False),
    ("apps/web", True),
    ("monitoring", False),
    ("ci", False),
]
ENVIRONMENTS = ["staging", "prod"]


def get_access_token() -> str:
    """Authenticate via Universal Auth and get access token."""
    client_id = os.environ.get("INFISICAL_CLIENT_ID")
    client_secret = os.environ.get("INFISICAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Set INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET environment variables"
        )

    data = json.dumps(
        {
            "clientId": client_id,
            "clientSecret": client_secret,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{INFISICAL_API_URL}/v1/auth/universal-auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result["accessToken"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Auth failed ({e.code}): {body}")


def create_folder(
    token: str, environment: str, folder_name: str, path: str = "/"
) -> bool:
    """Create a folder in Infisical via API."""
    data = json.dumps(
        {
            "projectId": PROJECT_ID,
            "environment": environment,
            "name": folder_name,
            "path": path,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{INFISICAL_API_URL}/v2/folders",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            json.loads(resp.read())  # consume response; folder created
            display = f"/{folder_name}" if path == "/" else f"{path}/{folder_name}"
            print(f"  [OK] Created {display} in {environment}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 400 and "already exists" in body.lower():
            display = f"/{folder_name}" if path == "/" else f"{path}/{folder_name}"
            print(f"  [EXISTS] {display} already exists in {environment}")
            return True
        print(f"  [FAIL] /{folder_name} in {environment}: {e.code} - {body}")
        return False


def copy_secrets_from_dev(token: str, target_env: str, folder: str) -> None:
    """Copy secrets from dev to target environment for a given folder path."""
    # Get secrets from dev
    params = urllib.parse.urlencode(
        {
            "environment": "dev",
            "secretPath": f"/{folder}",
            "workspaceId": PROJECT_ID,
        }
    )
    req = urllib.request.Request(
        f"{INFISICAL_API_URL}/v3/secrets/raw?{params}",
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            secrets = result.get("secrets", [])
    except urllib.error.HTTPError as e:
        print(f"    Could not read dev/{folder}: {e.code}")
        return

    if not secrets:
        print(f"    No secrets in dev/{folder}")
        return

    # Set each secret in target env
    for secret in secrets:
        secret_key = secret.get("secretKey", "")
        secret_value = secret.get("secretValue", "")

        if not secret_key:
            continue

        data = json.dumps(
            {
                "workspaceId": PROJECT_ID,
                "environment": target_env,
                "secretPath": f"/{folder}",
                "secretName": secret_key,
                "secretValue": secret_value,
                "type": "shared",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{INFISICAL_API_URL}/v3/secrets/raw/{secret_key}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"    [OK] Set {secret_key} in {target_env}/{folder}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if "already exists" in body.lower():
                print(
                    f"    [EXISTS] {secret_key} already exists in {target_env}/{folder}"
                )
            else:
                print(f"    [FAIL] {secret_key}: {e.code} - {body[:100]}")


def main():
    print("=" * 60)
    print("Infisical Folder & Secret Setup for Fabric_4L")
    print("=" * 60)
    print(f"Project ID: {PROJECT_ID}")
    print(f"Environments to configure: {', '.join(ENVIRONMENTS)}")
    print(f"Folders to create: {', '.join(p for p, _ in FOLDERS_TO_CREATE)}")
    print()

    # Get access token
    print("Authenticating...")
    token = get_access_token()
    print("[OK] Authenticated successfully\n")

    # Create folders in each environment
    for env in ENVIRONMENTS:
        print(f"\n{'-' * 40}")
        print(f"Environment: {env}")
        print(f"{'-' * 40}")

        print("\nCreating folders:")
        for folder, _needs_parent in FOLDERS_TO_CREATE:
            parent, _, name = folder.rpartition("/")
            create_folder(token, env, name, path="/" + parent if parent else "/")

        print("\nCopying secrets from dev:")
        for folder, _needs_parent in FOLDERS_TO_CREATE:
            print(f"  [{folder}]")
            copy_secrets_from_dev(token, env, folder)

    print(f"\n{'=' * 60}")
    print("Setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    import urllib.parse

    main()
