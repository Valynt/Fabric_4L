"""Root conftest.py template for multi-tenant production gate tests.

Provides shared fixtures for tenant isolation testing. All gate tests
should use these fixtures instead of creating their own tenant contexts.

Customize:
  - PROJECT_ROOT: path to the project root
  - ROUTE_DIRS: list of directories containing route files
  - MIGRATIONS_DIR: path to Alembic migration versions
  - FRONTEND_SRC: path to frontend source directory
  - Tenant UUID values (use real UUIDs from your test environment)
"""
import os
import sys
import uuid

import pytest

# ---------------------------------------------------------------------------
# Path setup — adjust PROJECT_ROOT to your project
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Constants — customize for your project
# ---------------------------------------------------------------------------
TENANT_A_ID = str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
TENANT_B_ID = str(uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
ORPHAN_TENANT_ID = str(uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))

ROUTE_DIRS = [
    # Add your route directories here, e.g.:
    # os.path.join(PROJECT_ROOT, "src/api/routes"),
    # os.path.join(PROJECT_ROOT, "src/tenants/api/routes"),
]

MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "migrations/versions")

FRONTEND_SRC = os.path.join(PROJECT_ROOT, "frontend/client/src")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def tenant_a_id():
    """Stable tenant A UUID for cross-tenant isolation tests."""
    return TENANT_A_ID


@pytest.fixture
def tenant_b_id():
    """Stable tenant B UUID for cross-tenant isolation tests."""
    return TENANT_B_ID


@pytest.fixture
def orphan_tenant_id():
    """UUID that should never match any real tenant."""
    return ORPHAN_TENANT_ID


@pytest.fixture
def route_dirs():
    """All directories containing API route files."""
    return ROUTE_DIRS


@pytest.fixture
def migrations_dir():
    """Path to Alembic migration versions directory."""
    return MIGRATIONS_DIR


@pytest.fixture
def frontend_src():
    """Path to frontend source directory."""
    return FRONTEND_SRC
