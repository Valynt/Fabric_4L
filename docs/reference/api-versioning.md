# API Versioning Guide — Fabric 4L

> **Document ID:** REF-API-VERSION-001  
> **Version:** 1.2.0  
> **Status:** ACTIVE  
> **Owner:** API Platform Team  
> **Review Cycle:** Quarterly  

---

## Table of Contents

1. [Versioning Strategy](#1-versioning-strategy)
2. [URL Path Versioning](#2-url-path-versioning)
3. [Deprecation Policy](#3-deprecation-policy)
4. [Sunset Schedule Template](#4-sunset-schedule-template)
5. [Migration Guides](#5-migration-guides)
6. [Breaking vs Non-Breaking Classification](#6-breaking-vs-non-breaking-classification)
7. [Consumer Communication](#7-consumer-communication)
8. [Backward Compatibility Testing](#8-backward-compatibility-testing)
9. [Version Lifecycle Diagram](#9-version-lifecycle-diagram)
10. [Appendix](#10-appendix)

---

## 1. Versioning Strategy

### 1.1 Philosophy

Fabric 4L uses **URL path versioning** with **semantic versioning** principles. Every public API endpoint is versioned explicitly to ensure:

- **Predictability:** Consumers know exactly what behavior to expect
- **Stability:** Existing integrations continue working across minor releases
- **Transparency:** Changes are communicated clearly and in advance
- **Testability:** Versioned contracts can be validated independently

### 1.2 Version Format

```
MAJOR.MINOR.PATCH

Examples:
  1.0.0   — Initial stable release
  1.1.0   — New features added (backward compatible)
  1.1.1   — Bug fix (backward compatible)
  2.0.0   — Breaking changes (requires migration)
```

### 1.3 API Version Matrix

| API Version | Status | Release Date | Sunset Date | Consumers |
|-------------|--------|--------------|-------------|-----------|
| v1 | **Current** | 2024-03-15 | — | 100% |
| v2 | **Beta** | 2025-01-15 | — | 5% (opt-in) |
| v0 | **Sunset** | 2023-06-01 | 2024-06-01 | 0% (deprecated) |

### 1.4 Version Header (Optional)

In addition to URL path versioning, the API version is exposed in response headers:

```http
GET /v1/workflows/wf-123 HTTP/1.1
Host: api.fabric4l.io

HTTP/1.1 200 OK
Content-Type: application/json
X-API-Version: 1.2.0
X-API-Deprecated: false
X-API-Sunset-Date: —
```

---

## 2. URL Path Versioning

### 2.1 Path Structure

```
https://api.fabric4l.io/{version}/{resource}

Examples:
  https://api.fabric4l.io/v1/workflows
  https://api.fabric4l.io/v1/workflows/wf-123
  https://api.fabric4l.io/v2/workflows
  https://api.fabric4l.io/v1/jobs?status=running
```

### 2.2 FastAPI Implementation

```python
"""
Fabric 4L — API Version Router Setup
Implements URL path versioning for all 6 layers.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Fabric 4L API", version="1.2.0")

# ── Version Router Factory ──────────────────────────────────────────────────

def create_versioned_router(version: str) -> APIRouter:
    """Create a router with version prefix and common middleware."""
    router = APIRouter(prefix=f"/{version}")

    @router.middleware("http")
    async def version_headers(request: Request, call_next):
        """Add API version headers to all responses."""
        response = await call_next(request)
        response.headers["X-API-Version"] = version
        response.headers["X-API-Deprecation-Status"] = "stable"
        return response

    return router

# ── v1 Router (Current Stable) ──────────────────────────────────────────────

v1_router = create_versioned_router("v1")

@v1_router.get("/workflows")
async def list_workflows_v1(
    page: int = 1,
    per_page: int = 20,
):
    """List workflows — v1 API."""
    return {"items": [], "page": page, "per_page": per_page}

@v1_router.get("/workflows/{workflow_id}")
async def get_workflow_v1(workflow_id: str):
    """Get a workflow by ID — v1 API."""
    return {"id": workflow_id, "name": "example", "status": "active"}

@v1_router.post("/workflows")
async def create_workflow_v1(request: dict):
    """Create a workflow — v1 API."""
    return {"id": "wf-new", "name": request.get("name"), "status": "pending"}

# ── v2 Router (Next Version) ────────────────────────────────────────────────

v2_router = create_versioned_router("v2")

@v2_router.get("/workflows")
async def list_workflows_v2(
    page: int = 1,
    per_page: int = 20,
    include_metadata: bool = False,  # New in v2
):
    """List workflows — v2 API with metadata support."""
    return {
        "items": [],
        "page": page,
        "per_page": per_page,
        "metadata": {"total_count": 0, "query_time_ms": 12} if include_metadata else None,
    }

@v2_router.get("/workflows/{workflow_id}")
async def get_workflow_v2(workflow_id: str):
    """Get a workflow — v2 API with enriched response."""
    return {
        "id": workflow_id,
        "name": "example",
        "status": "active",
        "version": 2,
        "audit_log": [],  # New in v2
    }

# ── Mount Routers ───────────────────────────────────────────────────────────

app.include_router(v1_router, tags=["v1"])
app.include_router(v2_router, tags=["v2"])

# ── Version Discovery Endpoint ──────────────────────────────────────────────

@app.get("/versions", tags=["meta"])
async def list_api_versions():
    """Discover available API versions and their status."""
    return {
        "versions": [
            {
                "version": "v2",
                "status": "beta",
                "url": "https://api.fabric4l.io/v2",
                "documentation": "https://docs.fabric4l.io/api/v2",
                "release_date": "2025-01-15",
                "sunset_date": None,
            },
            {
                "version": "v1",
                "status": "stable",
                "url": "https://api.fabric4l.io/v1",
                "documentation": "https://docs.fabric4l.io/api/v1",
                "release_date": "2024-03-15",
                "sunset_date": None,
            },
            {
                "version": "v0",
                "status": "sunset",
                "url": None,
                "documentation": None,
                "release_date": "2023-06-01",
                "sunset_date": "2024-06-01",
            },
        ],
    }
```

### 2.3 Request Routing Flow

```
Consumer Request
      │
      ▼
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  L1 Gateway     │  ← Extracts version from URL path
│  /v1/* → v1 svc │
│  /v2/* → v2 svc │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│  v1   │ │  v2   │
│Router │ │Router │
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
┌─────────────────┐
│  L3 Core        │  ← Business logic (version-aware)
└─────────────────┘
```

---

## 3. Deprecation Policy

### 3.1 Deprecation Timeline

```
Day 0        Day 30       Day 90       Day 150      Day 180
  │            │            │            │            │
  ▼            ▼            ▼            ▼            ▼
Announcement  Docs        Email       Warning      Removal
  +           Updated     Reminder    Header       + Sunset
Changelog     + SDKs      Sent        Enabled      Redirect

[━━━━━━━━━━━━][━━━━━━━━━━━][━━━━━━━━━━━][━━━━━━━━━━━][━━━━]
   Phase 1       Phase 2      Phase 3      Phase 4    Phase 5
   Notice        Prepare      Remind       Warn       Remove
```

### 3.2 Phases

| Phase | Timing | Action | Consumer Impact |
|-------|--------|--------|-----------------|
| **1. Notice** | Day 0 | Changelog entry, docs update, SDK release with deprecation annotations | Informational |
| **2. Prepare** | Day 30 | Migration guide published, SDKs updated with `@deprecated` tags | Low — time to plan |
| **3. Remind** | Day 90 | Email to registered API consumers, Slack announcement | Medium — active migration needed |
| **4. Warn** | Day 150 | `Deprecation` header added to all responses; warning in SDK logs | High — imminent removal |
| **5. Remove** | Day 180 | Endpoint removed; `410 Gone` or redirect to new version | Breaking — must have migrated |

### 3.3 Deprecation Headers

```http
# Phase 4+ — Warning headers added to every response
HTTP/1.1 200 OK
Content-Type: application/json
Deprecation: Sun, 15 Jun 2025 00:00:00 GMT
Sunset: Sun, 15 Dec 2025 00:00:00 GMT
Link: </v2/workflows>; rel="successor-version"
Link: <https://docs.fabric4l.io/migration/v1-to-v2>; rel="deprecation"
```

### 3.4 Deprecation in OpenAPI

```yaml
# contracts/openapi/l3-core.openapi.json
{
  "openapi": "3.1.0",
  "paths": {
    "/v1/workflows/{id}/execute": {
      "post": {
        "operationId": "executeWorkflowV1",
        "summary": "Execute a workflow (DEPRECATED)",
        "deprecated": true,
        "description": "Use `POST /v2/workflows/{id}/runs` instead. This endpoint will be removed on 2025-06-15.",
        "responses": {
          "200": {
            "description": "Success",
            "headers": {
              "Deprecation": {
                "description": "Deprecation date",
                "schema": {"type": "string", "format": "date-time"}
              },
              "Sunset": {
                "description": "Sunset date after which the endpoint will be removed",
                "schema": {"type": "string", "format": "date-time"}
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 4. Sunset Schedule Template

### 4.1 Template

```markdown
## API Sunset Schedule: {VERSION}

| Field | Value |
|-------|-------|
| **Version** | {VERSION} |
| **Announcement Date** | {DATE} |
| **Deprecation Start** | {DATE+30d} |
| **Warning Phase** | {DATE+150d} |
| **Sunset Date** | {DATE+180d} |
| **Successors** | {NEW_VERSION_LINKS} |
| **Migration Guide** | {MIGRATION_GUIDE_LINK} |
| **Contact** | api@fabric4l.io |

### Affected Endpoints

| Endpoint | Method | Replacement | Migration Complexity |
|----------|--------|-------------|---------------------|
| `/v{n}/resource` | GET | `/v{n+1}/resource` | Low |
| `/v{n}/resource` | POST | `/v{n+1}/resource` | Medium |

### Consumer Checklist

- [ ] Review migration guide
- [ ] Update SDK to latest version
- [ ] Update API calls to new endpoints
- [ ] Test in staging environment
- [ ] Deploy to production
- [ ] Confirm no v{n} traffic in dashboards

### Communication Log

| Date | Action | Channel | Status |
|------|--------|---------|--------|
| {DATE} | Announcement | Changelog + Email | ✅ Sent |
| {DATE+30d} | Docs updated | Documentation site | ✅ Published |
| {DATE+90d} | Reminder | Email + Slack | ⏳ Scheduled |
| {DATE+150d} | Final warning | Email + Headers | ⏳ Scheduled |
| {DATE+180d} | Removal | Deployment | ⏳ Scheduled |
```

### 4.2 Active Sunset Schedules

| Version | Sunset Date | Status | Consumers Remaining |
|---------|-------------|--------|---------------------|
| v0 | 2024-06-01 (past) | ✅ Removed | 0% |
| v1 | — | 🟢 Active | 100% |
| v2 | — | 🔵 Beta | N/A |

---

## 5. Migration Guides

### 5.1 v1 → v2 Migration Guide

#### Request Format Changes

**Before (v1):**
```http
POST /v1/workflows HTTP/1.1
Content-Type: application/json

{
  "name": "etl-pipeline",
  "steps": [
    {"type": "extract", "source": "postgres"},
    {"type": "transform", "rules": ["normalize"]},
    {"type": "load", "destination": "warehouse"}
  ]
}
```

**After (v2):**
```http
POST /v2/workflows HTTP/1.1
Content-Type: application/json

{
  "name": "etl-pipeline",
  "version": "2",
  "steps": [
    {"type": "extract", "source": "postgres", "options": {"batch_size": 1000}},
    {"type": "transform", "rules": ["normalize"], "parallel": true},
    {"type": "load", "destination": "warehouse", "mode": "upsert"}
  ],
  "metadata": {
    "owner": "data-team",
    "priority": "high",
    "tags": ["production", "daily"]
  }
}
```

#### Response Format Changes

**Before (v1):**
```json
{
  "id": "wf-123",
  "name": "etl-pipeline",
  "status": "running",
  "created_at": "2025-01-15T10:00:00Z"
}
```

**After (v2):**
```json
{
  "id": "wf-123",
  "name": "etl-pipeline",
  "status": "running",
  "version": 2,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:05:00Z",
  "metadata": {
    "owner": "data-team",
    "priority": "high",
    "tags": ["production", "daily"]
  },
  "audit_log": [
    {"action": "created", "at": "2025-01-15T10:00:00Z", "by": "user@example.com"},
    {"action": "started", "at": "2025-01-15T10:05:00Z", "by": "system"}
  ]
}
```

#### SDK Migration (Python)

**Before (v1):**
```python
from fabric4l_l3_core import Configuration, ApiClient
from fabric4l_l3_core.api import workflows_api
from fabric4l_l3_core.model.workflow_create_request import WorkflowCreateRequest

config = Configuration(host="https://api.fabric4l.io/v1")
client = ApiClient(config)
api = workflows_api.WorkflowsApi(client)

request = WorkflowCreateRequest(name="etl-pipeline", steps=[...])
workflow = api.create_workflow(request)
```

**After (v2):**
```python
from fabric4l_l3_core_v2 import Configuration, ApiClient          # ← Updated import
from fabric4l_l3_core_v2.api import workflows_api
from fabric4l_l3_core_v2.model.workflow_create_request import WorkflowCreateRequest
from fabric4l_l3_core_v2.model.workflow_metadata import WorkflowMetadata  # ← New model

config = Configuration(host="https://api.fabric4l.io/v2")         # ← Updated URL
client = ApiClient(config)
api = workflows_api.WorkflowsApi(client)

request = WorkflowCreateRequest(
    name="etl-pipeline",
    steps=[...],
    metadata=WorkflowMetadata(                                    # ← New field
        owner="data-team",
        priority="high",
        tags=["production", "daily"],
    ),
)
workflow = api.create_workflow(request)
```

#### Endpoint Renames

| v1 Endpoint | v2 Endpoint | Change Type |
|-------------|-------------|-------------|
| `GET /v1/workflows` | `GET /v2/workflows` | URL version bump |
| `POST /v1/workflows/{id}/execute` | `POST /v2/workflows/{id}/runs` | Path changed |
| `GET /v1/jobs` | `GET /v2/compute/jobs` | Resource renamed |
| `DELETE /v1/workflows/{id}` | `POST /v2/workflows/{id}/archive` | Soft delete instead |

---

## 6. Breaking vs Non-Breaking Classification

### 6.1 Change Classification Matrix

| Change Type | Breaking? | Consumer Action Required? | Example |
|-------------|-----------|---------------------------|---------|
| **New endpoint** | No | None | `POST /v1/workflows/batch` added |
| **New optional field in request** | No | None | `metadata` field added to POST body |
| **New field in response** | No | None | `audit_log` added to response |
| **New query parameter** | No | None | `?include_metadata=true` added |
| **New response status code** | No | Handle if desired | `202 Accepted` added |
| **Field made optional** | No | None | `description` no longer required |
| **Field made required** | **YES** | **Update requests** | `version` now required in POST body |
| **Field removed from response** | **YES** | **Update parsing** | `legacy_id` removed |
| **Field type changed** | **YES** | **Update parsing** | `count: int` → `count: string` |
| **Endpoint removed** | **YES** | **Use replacement** | `DELETE /v1/workflows` removed |
| **Endpoint path changed** | **YES** | **Update URLs** | `/v1/jobs` → `/v1/compute/jobs` |
| **Auth method changed** | **YES** | **Update auth** | API key → OAuth2 required |
| **Response status code removed** | **YES** | **Update handling** | `201 Created` → only `200 OK` |
| **Pagination format changed** | **YES** | **Update pagination** | `page/per_page` → `cursor/limit` |
| **Rate limit reduced** | **YES** | **Reduce call volume** | 1000/min → 100/min |
| **Deprecation of endpoint** | No (yet) | Plan migration | Endpoint marked deprecated |

### 6.2 Automated Classification

The [API Changelog Generator](../../scripts/ci/generate_api_changelog.py) automatically classifies changes:

```python
# Pseudocode for classification logic
def classify_change(old_spec, new_spec, path, method):
    if endpoint_removed(old_spec, new_spec, path, method):
        return BREAKING

    if required_field_added(new_spec, path):
        return BREAKING

    if field_type_changed(old_spec, new_spec, path):
        return BREAKING

    if field_removed_from_response(old_spec, new_spec, path):
        return BREAKING

    if endpoint_added(new_spec, path, method):
        return NON_BREAKING_ADDITION

    if optional_field_added(new_spec, path):
        return NON_BREAKING_ADDITION

    if endpoint_deprecated(new_spec, path, method):
        return DEPRECATION

    return MODIFICATION
```

### 6.3 Breaking Change Gate

```yaml
# .github/workflows/breaking-change-gate.yml
name: Breaking Change Review

on:
  pull_request:
    paths:
      - "contracts/openapi/**"

jobs:
  check-breaking:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detect breaking changes
        run: |
          python scripts/ci/generate_api_changelog.py \
            --from origin/main \
            --to HEAD \
            --json

      - name: Require approval for breaking changes
        if: steps.changelog.outputs.has_breaking == 'true'
        run: |
          echo "::error::Breaking API changes detected!"
          echo "::error::This PR requires explicit approval from @api-platform-team"
          exit 1
```

---

## 7. Consumer Communication

### 7.1 Communication Channels

| Channel | Timing | Audience | Content |
|---------|--------|----------|---------|
| **Changelog** | Immediate | All | Technical details, migration steps |
| **Email** | Day 0, 90, 150 | Registered consumers | Summary + action items |
| **Slack #api-announcements** | Day 0, 90 | Internal teams | Brief announcement |
| **SDK Release Notes** | Day 30 | SDK users | Code migration examples |
| **Dashboard Banner** | Day 90–180 | Active users | In-app warning |
| **Response Headers** | Day 150–180 | All API consumers | Machine-readable deprecation |

### 7.2 Email Templates

#### Initial Announcement (Day 0)

```
Subject: [Fabric 4L API] Upcoming changes in v2.0 — Action required by {SUNSET_DATE}

Hi {COMPANY} Team,

We're writing to inform you of upcoming changes to the Fabric 4L API that
affect your integration.

SUMMARY
───────
• Current version: v1 (your current version)
• New version: v2 (available now for testing)
• Sunset date: {SUNSET_DATE} (6 months from now)

WHAT'S CHANGING
───────────────
• New features: Metadata support, audit logs, parallel transforms
• Breaking changes: 3 endpoint renames, 2 required field changes
• Migration effort: ~2-4 hours for most integrations

WHAT YOU NEED TO DO
───────────────────
1. Review the migration guide: https://docs.fabric4l.io/migration/v1-to-v2
2. Update to the latest SDK: pip install --upgrade fabric4l-l3-core
3. Test in staging: https://staging-api.fabric4l.io/v2
4. Deploy before {SUNSET_DATE}

NEED HELP?
──────────
• Documentation: https://docs.fabric4l.io/api/v2
• Support: api@fabric4l.io
• Slack: #api-support
• Office hours: Tuesdays 2pm UTC

Best regards,
The Fabric 4L API Team
```

#### Reminder Email (Day 90)

```
Subject: [REMINDER] Fabric 4L API v1 sunset — {DAYS_REMAINING} days remaining

Hi {COMPANY} Team,

This is a friendly reminder that Fabric 4L API v1 will be sunset on
{SUNSET_DATE} ({DAYS_REMAINING} days from now).

YOUR CURRENT USAGE
──────────────────
• API version: v1
• Daily requests: ~{REQUEST_COUNT}
• Last active: {LAST_REQUEST_DATE}
• Affected endpoints: {ENDPOINT_LIST}

If you have already migrated, please disregard this email.

Migration guide: https://docs.fabric4l.io/migration/v1-to-v2

The Fabric 4L API Team
```

#### Final Warning (Day 150)

```
Subject: [URGENT] Fabric 4L API v1 sunset in 30 days — Immediate action required

Hi {COMPANY} Team,

Fabric 4L API v1 will be permanently removed on {SUNSET_DATE} (30 days).

After this date, all v1 requests will return HTTP 410 Gone.

URGENT ACTION REQUIRED:
1. Migrate immediately: https://docs.fabric4l.io/migration/v1-to-v2
2. Contact support if you need an extension: api@fabric4l.io

We can provide:
• Pair programming sessions
• Dedicated Slack channel for your migration
• Extended sunset (up to 60 days, by request)

The Fabric 4L API Team
```

### 7.3 Changelog Entry Template

```markdown
## API Changelog — {DATE}

### 🔴 Breaking Changes
- `POST /v1/workflows` → `POST /v2/workflows`
  - `metadata` field is now required
  - Response no longer includes `legacy_id`
- `GET /v1/jobs` moved to `GET /v2/compute/jobs`

### ➕ Additions
- New endpoint: `GET /v2/workflows/{id}/audit-log`
- New field: `parallel` option in transform steps
- New field: `audit_log` in workflow responses

### ⚠️ Deprecations
- `POST /v1/workflows/{id}/execute` → Use `POST /v2/workflows/{id}/runs`
  - Sunset date: 2025-06-15

### Migration Guide
Full details: https://docs.fabric4l.io/migration/v1-to-v2
```

---

## 8. Backward Compatibility Testing

### 8.1 Testing Strategy

```
┌────────────────────────────────────────────────────────────────────┐
│                    Compatibility Test Matrix                        │
├──────────────────┬─────────────────┬───────────────────────────────┤
│ Test Type        │ Frequency       │ Scope                         │
├──────────────────┼─────────────────┼───────────────────────────────┤
│ Contract Tests   │ Every PR        │ OpenAPI spec validation       │
│ Consumer Tests   │ Every PR        │ SDK generation + import       │
│ Integration Tests│ Daily           │ End-to-end API calls          │
│ Canary Tests     │ Every release   │ Traffic replay + diff         │
│ Fuzz Tests       │ Weekly          │ Random input validation       │
└──────────────────┴─────────────────┴───────────────────────────────┘
```

### 8.2 Contract Tests

```python
"""
Fabric 4L — Backward Compatibility Contract Tests
Validates that API responses conform to the OpenAPI specification.
"""

import pytest
import requests
from schemathesis import from_path
import schemathesis

# Load OpenAPI spec
schema = from_path("contracts/openapi/l3-core.openapi.json")

# Auto-generate tests from OpenAPI spec
@schema.parametrize()
def test_api_contract(case):
    """Verify endpoint returns response matching OpenAPI schema."""
    case.call_and_validate()


# ── Specific backward compatibility tests ───────────────────────────────────

class TestBackwardCompatibility:
    """Verify backward compatibility across versions."""

    BASE_URL_V1 = "https://staging-api.fabric4l.io/v1"
    BASE_URL_V2 = "https://staging-api.fabric4l.io/v2"

    def test_v1_response_fields_still_present(self):
        """All v1 response fields must still exist in v2 responses."""
        resp_v1 = requests.get(f"{self.BASE_URL_V1}/workflows/wf-test")
        resp_v2 = requests.get(f"{self.BASE_URL_V2}/workflows/wf-test")

        v1_fields = set(resp_v1.json().keys())
        v2_fields = set(resp_v2.json().keys())

        # v2 must contain all v1 fields (v2 can add new ones)
        missing = v1_fields - v2_fields
        assert not missing, f"v2 missing fields that exist in v1: {missing}"

    def test_v1_request_still_works_with_v2(self):
        """A valid v1 request body must be accepted by v2."""
        v1_request = {
            "name": "test-workflow",
            "steps": [{"type": "extract", "source": "test"}],
        }

        resp = requests.post(
            f"{self.BASE_URL_V2}/workflows",
            json=v1_request,
            headers={"Content-Type": "application/json"},
        )
        # v2 should accept v1 requests (backward compatible)
        assert resp.status_code in (200, 201), f"v2 rejected v1 request: {resp.text}"

    def test_deprecated_endpoints_return_warning_headers(self):
        """Deprecated endpoints must include Deprecation and Sunset headers."""
        resp = requests.get(f"{self.BASE_URL_V1}/workflows/old-endpoint")

        assert "Deprecation" in resp.headers, "Missing Deprecation header"
        assert "Sunset" in resp.headers, "Missing Sunset header"

        sunset_date = resp.headers["Sunset"]
        # Sunset date must be in the future
        from datetime import datetime
        assert datetime.fromisoformat(sunset_date) > datetime.now()

    def test_removed_endpoints_return_410(self):
        """Removed endpoints must return HTTP 410 Gone."""
        resp = requests.get(f"{self.BASE_URL_V1}/removed-endpoint")
        assert resp.status_code == 410, f"Expected 410, got {resp.status_code}"

    @pytest.mark.parametrize("endpoint,method", [
        ("/v1/workflows", "GET"),
        ("/v1/workflows", "POST"),
        ("/v1/workflows/{id}", "GET"),
        ("/v1/workflows/{id}", "PUT"),
        ("/v1/workflows/{id}", "DELETE"),
    ])
    def test_v1_endpoints_still_functional(self, endpoint, method):
        """All v1 endpoints must remain functional until sunset."""
        url = f"{self.BASE_URL_V1}{endpoint.format(id='wf-test')}"
        resp = requests.request(method, url, json={} if method in ("POST", "PUT") else None)

        # Should not return 404 (endpoint exists) or 410 (not yet removed)
        assert resp.status_code not in (404, 410), (
            f"v1 endpoint {method} {endpoint} returned {resp.status_code} before sunset"
        )
```

### 8.3 Canary Testing

```python
"""
Fabric 4L — Canary Release Testing
Replays production traffic against new version and compares responses.
"""

import json
import hashlib
from datetime import datetime

class CanaryTester:
    """Compare responses between API versions using production traffic replay."""

    def __init__(self, v1_base_url: str, v2_base_url: str):
        self.v1_base = v1_base_url
        self.v2_base = v2_base_url
        self.differences: list[dict] = []

    def replay_and_compare(self, request_log: dict) -> dict:
        """Replay a request against both versions and compare."""
        import requests

        # Call v1
        v1_resp = requests.request(
            method=request_log["method"],
            url=f"{self.v1_base}{request_log['path']}",
            headers=request_log.get("headers"),
            json=request_log.get("body"),
            params=request_log.get("query"),
        )

        # Call v2
        v2_resp = requests.request(
            method=request_log["method"],
            url=f"{self.v2_base}{request_log['path']}",
            headers=request_log.get("headers"),
            json=request_log.get("body"),
            params=request_log.get("query"),
        )

        # Compare
        comparison = self._compare_responses(v1_resp, v2_resp)

        if comparison["has_diff"]:
            self.differences.append({
                "request": request_log,
                "comparison": comparison,
                "timestamp": datetime.utcnow().isoformat(),
            })

        return comparison

    def _compare_responses(self, v1_resp, v2_resp) -> dict:
        """Compare two responses and identify differences."""
        comparison = {
            "v1_status": v1_resp.status_code,
            "v2_status": v2_resp.status_code,
            "status_match": v1_resp.status_code == v2_resp.status_code,
            "has_diff": False,
            "differences": [],
        }

        # Compare status codes
        if not comparison["status_match"]:
            comparison["has_diff"] = True
            comparison["differences"].append({
                "field": "status_code",
                "v1": v1_resp.status_code,
                "v2": v2_resp.status_code,
            })

        # Compare response bodies (v2 can have extra fields)
        try:
            v1_body = v1_resp.json()
            v2_body = v2_resp.json()

            # Check v1 fields exist in v2
            if isinstance(v1_body, dict) and isinstance(v2_body, dict):
                for key in v1_body:
                    if key not in v2_body:
                        comparison["has_diff"] = True
                        comparison["differences"].append({
                            "field": f"response.{key}",
                            "v1": "present",
                            "v2": "missing",
                            "severity": "breaking",
                        })
                    elif v1_body[key] != v2_body[key]:
                        comparison["has_diff"] = True
                        comparison["differences"].append({
                            "field": f"response.{key}",
                            "v1": v1_body[key],
                            "v2": v2_body[key],
                            "severity": "warning",
                        })
        except (json.JSONDecodeError, ValueError):
            pass  # Non-JSON responses — skip body comparison

        return comparison

    def generate_report(self) -> dict:
        """Generate a summary report of all comparisons."""
        breaking = sum(
            1 for d in self.differences
            if any(diff.get("severity") == "breaking" for diff in d["comparison"]["differences"])
        )

        return {
            "total_requests": len(self.differences),
            "differences_found": len(self.differences),
            "breaking_differences": breaking,
            "details": self.differences,
            "recommendation": "DO NOT RELEASE" if breaking > 0 else "SAFE TO RELEASE",
        }
```

### 8.4 Compatibility Test CI Workflow

```yaml
# .github/workflows/api-compatibility.yml
name: API Compatibility Tests

on:
  pull_request:
    paths:
      - "contracts/openapi/**"
      - "services/**"
  schedule:
    - cron: "0 6 * * *"  # Daily at 6am UTC

jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install schemathesis requests
      - run: pytest tests/contract/ -v --tb=short

  backward-compat:
    runs-on: ubuntu-latest
    needs: contract-tests
    steps:
      - uses: actions/checkout@v4
      - name: Start services
        run: docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
      - name: Run backward compatibility tests
        run: |
          pip install requests pytest
          pytest tests/backward-compat/ -v
      - name: Generate report
        run: python tests/backward-compat/generate_report.py
      - uses: actions/upload-artifact@v4
        with:
          name: compatibility-report
          path: compatibility-report.json
```

---

## 9. Version Lifecycle Diagram

```
                    ┌──────────────┐
                    │   Planning   │
                    │  (RFC Phase) │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
         ┌─────────│  Development │◄────────┐
         │         │   (v2.0.0)   │         │
         │         └──────┬───────┘         │
         │                │                 │
         │                ▼                 │
         │         ┌──────────────┐         │
         │         │  Beta/RC     │         │
         │         │  (opt-in)    │         │
         │         └──────┬───────┘         │
         │                │                 │
         │                ▼                 │
         │         ┌──────────────┐         │
         │    ┌───▶│   Stable     │◄────┐   │
         │    │    │  (Current)   │     │   │
         │    │    └──────┬───────┘     │   │
         │    │           │              │   │
         │    │           ▼              │   │
         │    │    ┌──────────────┐      │   │
         │    └───│  Deprecated  │──────┘   │
         │         │  (6 months)  │          │
         │         └──────┬───────┘          │
         │                │                  │
         │                ▼                  │
         │         ┌──────────────┐          │
         └────────▶│   Sunset     │──────────┘
                   │  (410 Gone)  │
                   └──────────────┘
```

### State Definitions

| State | Description | Traffic | Response |
|-------|-------------|---------|----------|
| **Planning** | RFC/design phase | None | N/A |
| **Development** | Active development | Internal only | May be unstable |
| **Beta/RC** | Release candidate | Opt-in | Stable, minor issues |
| **Stable** | Current production | 100% | Fully supported |
| **Deprecated** | Maintenance mode | Declining | Functional + warnings |
| **Sunset** | Removed | Redirected | 410 Gone or redirect |

---

## 10. Appendix

### A.1 Version Negotiation (Content-Type)

For advanced use cases, version negotiation via `Accept` header is supported:

```http
GET /workflows/wf-123 HTTP/1.1
Accept: application/json;version=2

HTTP/1.1 200 OK
Content-Type: application/json;version=2
```

### A.2 Glossary

| Term | Definition |
|------|------------|
| **Breaking Change** | A change that requires consumers to modify their code |
| **Deprecation** | A formal announcement that an endpoint/field will be removed |
| **Sunset** | The date after which a deprecated feature is removed |
| **Successor Version** | The recommended replacement for a deprecated feature |
| **Canary Release** | Gradual rollout of a new version to a subset of traffic |
| **Backward Compatible** | A change that does not require consumer modifications |

### A.3 References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [IETF Deprecation HTTP Header](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-deprecation-header)
- [IETF Sunset HTTP Header](https://datatracker.ietf.org/doc/html/rfc8594)
- [OpenAPI 3.1 Specification](https://spec.openapis.org/oas/v3.1.0)

### A.4 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2024-03-15 | @api-team | Initial document |
| 1.1.0 | 2024-09-01 | @api-team | Added sunset schedule template |
| 1.2.0 | 2025-01-15 | @api-team | Added canary testing, email templates |

---

*This document is maintained by the Fabric 4L API Platform Team.*
*For questions: api@fabric4l.io | Slack: #api-platform*
