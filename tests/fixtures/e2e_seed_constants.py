"""Canonical E2E/backend-integrated seed constants for tests only.

Do not import this module from production runtime paths.
"""

from __future__ import annotations

from uuid import UUID

SEED_PRIVILEGED_REASON = "playwright-backend-validation-seed"
SEED_DRAFT_CASE_ID = "case-draft-001"
SEED_APPROVED_CASE_ID = "case-e2e-approved-001"
SEED_APPROVED_CASE_ALIASES = ["case-meridian-e2e-001"]
SEED_TENANT_SLUG = "tenant-e2e-001"
SEED_TENANT_NAME = "E2E Validation Tenant"
SEED_SERVICE_ACCOUNT_ID = "svc-playwright-backend-validation"
SEED_AUTH_SOURCE = "backend-integrated-auth-context"
SEED_VALIDATION_USER_IDS = {
    "admin": UUID("00000000-0000-4000-e2e0-000000000201"),
    "reviewer": UUID("00000000-0000-4000-e2e0-000000000202"),
    "read_only": UUID("00000000-0000-4000-e2e0-000000000203"),
    "sales": UUID("00000000-0000-4000-e2e0-000000000204"),
}
