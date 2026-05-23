"""Runtime seed configuration for non-production lifecycle seeding.

Values are intentionally neutral defaults; tests can override via env vars.
"""

from __future__ import annotations

import os
from uuid import UUID

SEED_PRIVILEGED_REASON = os.environ.get(
    "VALIDATION_SEED_PRIVILEGED_REASON", "validation-seed"
)
SEED_DRAFT_CASE_ID = os.environ.get("VALIDATION_SEED_DRAFT_CASE_ID", "case-draft")
SEED_APPROVED_CASE_ID = os.environ.get(
    "VALIDATION_SEED_APPROVED_CASE_ID", "case-approved"
)
SEED_APPROVED_CASE_ALIASES = [
    a
    for a in os.environ.get(
        "VALIDATION_SEED_APPROVED_CASE_ALIASES", "case-approved-alias"
    ).split(",")
    if a
]
SEED_TENANT_SLUG = os.environ.get("VALIDATION_SEED_TENANT_SLUG", "tenant-validation")
SEED_TENANT_NAME = os.environ.get("VALIDATION_SEED_TENANT_NAME", "Validation Tenant")
SEED_SERVICE_ACCOUNT_ID = os.environ.get(
    "VALIDATION_SEED_SERVICE_ACCOUNT_ID", "svc-validation-seed"
)
SEED_AUTH_SOURCE = os.environ.get(
    "VALIDATION_SEED_AUTH_SOURCE", "backend-integrated-auth-context"
)
SEED_VALIDATION_USER_IDS = {
    "admin": UUID(
        os.environ.get("E2E_VALIDATION_ADMIN_ID", "00000000-0000-4000-8000-000000000201")
    ),
    "reviewer": UUID(
        os.environ.get(
            "E2E_VALIDATION_REVIEWER_ID", "00000000-0000-4000-8000-000000000202"
        )
    ),
    "read_only": UUID(
        os.environ.get("E2E_VALIDATION_READONLY_ID", "00000000-0000-4000-8000-000000000203")
    ),
    "sales": UUID(
        os.environ.get("E2E_VALIDATION_SALES_ID", "00000000-0000-4000-8000-000000000204")
    ),
}
