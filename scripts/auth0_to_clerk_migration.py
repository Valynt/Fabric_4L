#!/usr/bin/env python3
"""Auth0 to Clerk User Migration Script

This script provides a template for migrating user data from Auth0 to Clerk.
It exports user data from Auth0 and imports it into Clerk using Clerk's API.

Usage:
    python scripts/auth0_to_clerk_migration.py --export auth0_users.json
    python scripts/auth0_to_clerk_migration.py --import auth0_users.json --dry-run
    python scripts/auth0_to_clerk_migration.py --import auth0_users.json --execute

Environment Variables Required:
    AUTH0_DOMAIN: Auth0 tenant domain
    AUTH0_CLIENT_ID: Auth0 management API client ID
    AUTH0_CLIENT_SECRET: Auth0 management API client secret
    CLERK_SECRET_KEY: Clerk secret key

Dependencies:
    pip install requests
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

# Clerk Organization Role Mapping
# Maps Auth0 roles to Clerk organization roles
ROLE_MAPPING = {
    "admin": "org:admin",
    "tenant_admin": "org:admin",
    "analyst": "org:member",
    "user": "org:member",
    "read_only": "org:member",
}


def get_auth0_token(domain: str, client_id: str, client_secret: str) -> str:
    """Fetch Auth0 management API token."""
    url = f"https://{domain}/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": f"https://{domain}/api/v2/",
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def export_auth0_users(domain: str, token: str, output_file: str) -> None:
    """Export all users from Auth0 to a JSON file."""
    logger.info("Exporting users from Auth0 tenant: %s", domain)
    url = f"https://{domain}/api/v2/users"
    headers = {"Authorization": f"Bearer {token}"}
    
    users: List[Dict[str, Any]] = []
    page = 0
    per_page = 100
    
    while True:
        params = {"page": page, "per_page": per_page, "include_totals": True}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        batch = data.get("users", [])
        if not batch:
            break
            
        users.extend(batch)
        logger.info("Exported %d users (page %d)", len(users), page)
        
        if len(batch) < per_page:
            break
        page += 1
    
    # Enrich with roles
    for user in users:
        user_id = user["user_id"]
        roles_url = f"https://{domain}/api/v2/users/{user_id}/roles"
        try:
            roles_response = requests.get(roles_url, headers=headers, timeout=10)
            if roles_response.status_code == 200:
                user["roles"] = roles_response.json()
        except requests.RequestException as exc:
            logger.warning("Failed to fetch roles for user %s: %s", user_id, exc)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    
    logger.info("Exported %d users to %s", len(users), output_file)


def create_clerk_user(secret_key: str, user_data: Dict[str, Any], dry_run: bool = True) -> bool:
    """Create a user in Clerk."""
    if dry_run:
        logger.info("[DRY-RUN] Would create user: %s (%s)", 
                    user_data.get("email"), user_data.get("user_id"))
        return True
    
    url = "https://api.clerk.com/v1/users"
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    
    # Map Auth0 user to Clerk user format
    clerk_user = {
        "email_address": [user_data.get("email")],
        "first_name": user_data.get("given_name", ""),
        "last_name": user_data.get("family_name", ""),
        "password": None,  # Users will need to reset passwords
        "skip_password_checks": True,
    }
    
    # Add username if available
    if user_data.get("username"):
        clerk_user["username"] = user_data["username"]
    
    response = requests.post(url, headers=headers, json=clerk_user, timeout=30)
    
    if response.status_code == 201:
        logger.info("Created user in Clerk: %s", user_data.get("email"))
        return True
    elif response.status_code == 422 and "already exists" in response.text.lower():
        logger.warning("User already exists in Clerk: %s", user_data.get("email"))
        return True
    else:
        logger.error("Failed to create user %s: %s - %s", 
                     user_data.get("email"), response.status_code, response.text)
        return False


def create_clerk_organization(secret_key: str, org_name: str, org_slug: str) -> str | None:
    """Create an organization in Clerk."""
    url = "https://api.clerk.com/v1/organizations"
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "name": org_name,
        "slug": org_slug,
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if response.status_code == 201:
        org_id = response.json().get("id")
        logger.info("Created organization in Clerk: %s (%s)", org_name, org_id)
        return org_id
    elif response.status_code == 422:
        logger.warning("Organization may already exist: %s", org_name)
        return None
    else:
        logger.error("Failed to create organization %s: %s", org_name, response.text)
        return None


def add_user_to_clerk_org(secret_key: str, user_id: str, org_id: str, role: str) -> bool:
    """Add a user to a Clerk organization."""
    url = f"https://api.clerk.com/v1/organizations/{org_id}/memberships"
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "user_id": user_id,
        "role": role,
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if response.status_code == 201:
        logger.info("Added user %s to organization %s with role %s", user_id, org_id, role)
        return True
    else:
        logger.error("Failed to add user %s to org: %s", user_id, response.text)
        return False


def import_users_to_clerk(input_file: str, secret_key: str, dry_run: bool = True) -> None:
    """Import users from Auth0 export JSON to Clerk."""
    logger.info("Importing users from %s (dry_run=%s)", input_file, dry_run)
    
    with open(input_file, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    logger.info("Found %d users to import", len(users))
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        if not user.get("email"):
            logger.warning("Skipping user without email: %s", user.get("user_id"))
            continue
        
        # Create user in Clerk
        if create_clerk_user(secret_key, user, dry_run=dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info("Import complete: %d succeeded, %d failed", success_count, fail_count)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auth0 to Clerk User Migration")
    parser.add_argument("--export", metavar="FILE", help="Export Auth0 users to JSON file")
    parser.add_argument("--import", dest="import_file", metavar="FILE", 
                        help="Import users from JSON file to Clerk")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Show what would be done without making changes")
    parser.add_argument("--execute", action="store_true", help="Execute the migration")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    dry_run = not args.execute
    
    if args.export:
        domain = os.getenv("AUTH0_DOMAIN") or ""
        client_id = os.getenv("AUTH0_CLIENT_ID") or ""
        client_secret = os.getenv("AUTH0_CLIENT_SECRET") or ""
        
        if not all([domain, client_id, client_secret]):
            logger.error("Missing Auth0 credentials. Set AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET")
            return 1
        
        token = get_auth0_token(domain, client_id, client_secret)
        export_auth0_users(domain, token, args.export)
        return 0
    
    if args.import_file:
        secret_key = os.getenv("CLERK_SECRET_KEY")
        if not secret_key:
            logger.error("Missing CLERK_SECRET_KEY environment variable")
            return 1
        
        import_users_to_clerk(args.import_file, secret_key, dry_run=dry_run)
        return 0
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
