#!/usr/bin/env python3
"""
Developer Authentication Seeding Script for Fabric 4L (`make auth-dev`).

Initializes a local development environment with pre-seeded Clerk mock users,
tenants (organizations), accounts, and valid Ed25519-signed internal AuthContext
envelopes.

Usage:
    python scripts/dev_auth_seed.py [--output .env.auth.local] [--print-tokens]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Add project paths to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))

try:
    from value_fabric.shared.identity.fabric_auth.context import AuthContext
    from value_fabric.shared.identity.fabric_auth.signer import SigningKey, sign_envelope
except ImportError as e:
    SigningKey = None
    sign_envelope = None
    AuthContext = None


SEED_DATA = {
    "tenants": [
        {
            "id": "org_dev_acme",
            "name": "Acme Industrial Corp",
            "slug": "acme-industrial",
            "tier": "enterprise",
            "accounts": [
                {"id": "acc_dev_acme_main", "name": "Global Operations"},
                {"id": "acc_dev_acme_eu", "name": "European Subsidiary"},
            ],
        },
        {
            "id": "org_dev_globex",
            "name": "Globex Systems",
            "slug": "globex-systems",
            "tier": "growth",
            "accounts": [
                {"id": "acc_dev_globex_core", "name": "Core Platform"},
            ],
        },
    ],
    "users": [
        {
            "id": "user_dev_alice_admin",
            "email": "alice@acme.example.com",
            "first_name": "Alice",
            "last_name": "Admin",
            "tenant_id": "org_dev_acme",
            "account_id": "acc_dev_acme_main",
            "role": "tenant_admin",
            "org_role": "org:admin",
            "scopes": ["*"],
        },
        {
            "id": "user_dev_bob_member",
            "email": "bob@acme.example.com",
            "first_name": "Bob",
            "last_name": "Analyst",
            "tenant_id": "org_dev_acme",
            "account_id": "acc_dev_acme_main",
            "role": "tenant_member",
            "org_role": "org:member",
            "scopes": ["read:all", "write:analyses"],
        },
        {
            "id": "user_dev_charlie_globex",
            "email": "charlie@globex.example.com",
            "first_name": "Charlie",
            "last_name": "Engineer",
            "tenant_id": "org_dev_globex",
            "account_id": "acc_dev_globex_core",
            "role": "tenant_admin",
            "org_role": "org:admin",
            "scopes": ["*"],
        },
    ],
}


def generate_dev_envelopes(signing_key_pem: str | None = None) -> dict[str, str]:
    """Generates signed Ed25519 X-Fabric-Auth-Context envelopes for each seed user."""
    envelopes = {}
    now = int(time.time())

    signing_key = None
    if SigningKey:
        try:
            if signing_key_pem:
                signing_key = SigningKey(kid="dev-key-1", private_pem=signing_key_pem)
            else:
                priv_key = ed25519.Ed25519PrivateKey.generate()
                private_pem = priv_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode("utf-8")
                signing_key = SigningKey(kid="dev-key-1", private_pem=private_pem)
        except Exception:
            pass

    for user in SEED_DATA["users"]:
        if sign_envelope and signing_key and AuthContext:
            try:
                auth_ctx = AuthContext(
                    clerk_user_id=user["id"],
                    clerk_org_id=user["tenant_id"],
                    user_id=user["id"],
                    tenant_id=user["tenant_id"],
                    roles=frozenset([user["role"]]),
                    permissions=frozenset(user["scopes"]),
                    request_id=f"req_dev_{user['id']}_{now}",
                    iat=now,
                    exp=now + 86400,
                    kid=signing_key.kid,
                )
                token = sign_envelope(auth_ctx, signing_key=signing_key)
                envelopes[user["id"]] = token
            except Exception as e:
                envelopes[user["id"]] = f"mock_envelope_for_{user['id']}"
        else:
            envelopes[user["id"]] = f"mock_envelope_for_{user['id']}"

    return envelopes


def main():
    parser = argparse.ArgumentParser(description="Seed Local Dev Auth Environment")
    parser.add_argument("--output", "-o", default=None, help="Output .env file path")
    parser.add_argument("--print-tokens", action="store_true", help="Print minted envelopes")
    parser.add_argument("--json", action="store_true", help="Output full JSON seed payload")
    args = parser.parse_args()

    envelopes = generate_dev_envelopes()

    seed_result = {
        "tenants": SEED_DATA["tenants"],
        "users": SEED_DATA["users"],
        "envelopes": envelopes,
    }

    if args.json:
        print(json.dumps(seed_result, indent=2))
        return

    print("=" * 70)
    print("Value Fabric -- Local Dev Auth Seeding (`make auth-dev`)")
    print("=" * 70)
    print(f"[OK] Seeded {len(SEED_DATA['tenants'])} Tenants:")
    for t in SEED_DATA["tenants"]:
        print(f"  - {t['name']} ({t['id']}) [Slug: {t['slug']}]")
        for acc in t["accounts"]:
            print(f"      +-- Account: {acc['name']} ({acc['id']})")

    print(f"\n[OK] Seeded {len(SEED_DATA['users'])} Users with Dev Envelopes:")
    for u in SEED_DATA["users"]:
        env_str = envelopes.get(u["id"], "")
        preview = env_str[:30] + "..." if len(env_str) > 30 else env_str
        print(f"  - {u['email']} ({u['id']}) -> Tenant: {u['tenant_id']}, Role: {u['role']}")
        if args.print_tokens:
            print(f"      Envelope Token: {env_str}")
        else:
            print(f"      Envelope (X-Fabric-Auth-Context): {preview}")

    if args.output:
        out_path = Path(args.output)
        lines = [
            "# Auto-generated by scripts/dev_auth_seed.py",
            f"DEV_SEED_PRIMARY_TENANT={SEED_DATA['tenants'][0]['id']}",
            f"DEV_SEED_PRIMARY_USER={SEED_DATA['users'][0]['id']}",
            f"DEV_SEED_ALICE_ENVELOPE={envelopes.get(SEED_DATA['users'][0]['id'], '')}",
            f"DEV_SEED_BOB_ENVELOPE={envelopes.get(SEED_DATA['users'][1]['id'], '')}",
        ]
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n[OK] Exported environment variables to {out_path}")

    print("\n[OK] Dev Auth environment ready. Gateway and downstream layers can be tested locally.")


if __name__ == "__main__":
    main()
