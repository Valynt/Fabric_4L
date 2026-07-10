# Fabric_4L Contract Test Expansion Spec v1.2.0

> **Status:** Draft | **Priority:** P1 | **Target:** v1.2.0 GA
>
> This document specifies the expansion of contract tests across five strategic
> areas to achieve 90% contract coverage by v1.3.0.

---

## Table of Contents

1. [Overview](#overview)
2. [Area 1: OpenAPI Endpoint Coverage](#area-1-openapi-endpoint-coverage)
3. [Area 2: JSON Schema Tool Manifests](#area-2-json-schema-tool-manifests)
4. [Area 3: Auth Boundary Per Route](#area-3-auth-boundary-per-route)
5. [Area 4: Dev-Bypass Safety in Production](#area-4-dev-bypass-safety-in-production)
6. [Area 5: Startup Guard Validation](#area-5-startup-guard-validation)
7. [Implementation Timeline](#implementation-timeline)
8. [Success Criteria](#success-criteria)

---

## Overview

### Current State

| Area | Current Coverage | Target (v1.2.0) | Target (v1.3.0) |
|------|-----------------|-------------------|-------------------|
| OpenAPI Endpoints | 40% | 70% | 90% |
| JSON Schema Manifests | 30% | 60% | 90% |
| Auth Boundary | 25% | 60% | 90% |
| Dev-Bypass Safety | 10% | 80% | 100% |
| Startup Guards | 20% | 70% | 100% |

### Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Contract Test Layer                       │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ schemathesis │ │  json    │ │  auth    │ │  startup  │ │
│  │  (OpenAPI)   │ │ schema   │ │ boundary │ │  guards   │ │
│  └──────┬───────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ │
│         │              │            │             │       │
│  ┌──────▼───────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ │
│  │  Property    │ │  Schema  │ │  Route   │ │  Config  │ │
│  │  -based      │ │  Valid.  │ │  Invtry. │ │  Valid.  │ │
│  └──────────────┘ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Area 1: OpenAPI Endpoint Coverage

### Objective
Use schemathesis to perform property-based contract testing on all OpenAPI-documented endpoints, automatically generating test cases that validate request/response contracts.

### Tools
- **schemathesis** — Property-based testing from OpenAPI spec
- **hypothesis** — Underlying property-based testing engine
- **pytest** — Test runner integration

### Test Code Examples

#### 1.1 Full OpenAPI Contract Test Suite

```python
# tests/contract/test_openapi_contracts.py
"""
OpenAPI contract tests using schemathesis.
Run: pytest tests/contract/test_openapi_contract.py -v
"""
import pytest
import schemathesis
from schemathesis.checks import (
    not_a_server_error,
    status_code_conformance,
    content_type_conformance,
    response_headers_conformance,
    response_schema_conformance,
)

from fabric_4l.app import create_app
from fabric_4l.config import TestConfig

# Load OpenAPI schema from the running app or spec file
schema = schemathesis.from_path(
    "openapi.json",
    base_url="http://localhost:5000",
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """Create test application instance."""
    app = create_app(config_class=TestConfig)
    return app


@pytest.fixture(scope="module")
def client(app):
    """Create test client."""
    return app.test_client()


# ── Global hooks ─────────────────────────────────────────────────────────────

@schemathesis.hook
def before_generate_path_parameters(context, strategy):
    """Customize path parameter generation for known constraints."""
    if context.endpoint == "/api/v1/tenants/{tenant_id}":
        # Ensure tenant_id matches UUID format
        return strategy.filter(
            lambda x: len(x.get("tenant_id", "")) == 36
        )
    return strategy


@schemathesis.hook
def after_call(context, case, response):
    """Log slow responses for performance tracking."""
    if response.elapsed.total_seconds() > 1.0:
        pytest.warn(f"Slow response: {case.operation.path} took "
                   f"{response.elapsed.total_seconds():.2f}s")


# ── Endpoint Contract Tests ──────────────────────────────────────────────────

@schema.parametrize()
def test_api_contract(case, client):
    """Property-based contract test for all OpenAPI endpoints."""
    response = case.call_and_validate(session=client)
    
    # Core contract checks
    not_a_server_error(response, case)
    status_code_conformance(response, case)
    content_type_conformance(response, case)
    response_schema_conformance(response, case)


@schema.parametrize(endpoint="/api/v1/auth/.*")
def test_auth_endpoints_contract(case, client):
    """Dedicated contract tests for auth endpoints with auth state."""
    response = case.call_and_validate(session=client)
    
    # Auth endpoints should never return 500
    assert response.status_code < 500, "Auth endpoints must not server-error"
    
    # Login endpoint should return tokens on success
    if case.operation.path == "/api/v1/auth/login" and response.status_code == 200:
        data = response.json()
        assert "access_token" in data, "Login must return access_token"
        assert "refresh_token" in data, "Login must return refresh_token"
        assert data["token_type"] == "bearer", "Token type must be bearer"


@schema.parametrize(endpoint="/api/v1/tenants/.*")
def test_tenant_isolation_contract(case, client, auth_headers):
    """Verify tenant endpoints enforce isolation."""
    # Test with valid auth
    response = case.call_and_validate(
        session=client,
        headers=auth_headers,
    )
    
    # Should never leak data across tenants
    if response.status_code == 200 and isinstance(response.json(), list):
        for item in response.json():
            assert "tenant_id" in item, "Tenant resources must include tenant_id"


@schema.parametrize(endpoint="/api/v1/admin/.*")
def test_admin_endpoint_authorization(case, client):
    """Admin endpoints must require admin privileges."""
    # Without auth — should fail
    response = case.call_wsgi(application=client.application)
    assert response.status_code in (401, 403), \
        "Admin endpoints must require authentication"


# ── Stateful Testing ─────────────────────────────────────────────────────────

schema_stateful = schemathesis.from_path(
    "openapi.json",
    base_url="http://localhost:5000",
)

TestAPIWorkflow = schema_stateful.as_state_machine().TestCase

class TestStatefulWorkflow(TestAPIWorkflow):
    """Stateful tests that verify multi-step API workflows."""
    
    def setup(self):
        """Set up test state before each workflow."""
        self.app = create_app(config_class=TestConfig)
        self.client = self.app.test_client()
    
    def step_create_tenant(self, case):
        """Create a tenant and store ID for subsequent steps."""
        response = case.call_and_validate(session=self.client)
        if response.status_code == 201:
            self.tenant_id = response.json()["id"]
    
    def step_use_tenant(self, case):
        """Use tenant ID in dependent operations."""
        if hasattr(self, "tenant_id"):
            case.path_parameters["tenant_id"] = self.tenant_id
        response = case.call_and_validate(session=self.client)
        # Tenant-scoped operations should succeed after creation
        assert response.status_code in (200, 201, 204, 404)
```

#### 1.2 Performance Budget per Endpoint

```python
# tests/contract/test_endpoint_performance.py
"""Contract-level performance validation for API endpoints."""
import pytest
import time
from dataclasses import dataclass


@dataclass
class EndpointBudget:
    path: str
    method: str
    max_p95_ms: float  # 95th percentile budget
    max_p99_ms: float  # 99th percentile budget


ENDPOINT_BUDGETS = [
    EndpointBudget("/api/v1/auth/login", "POST", 200, 500),
    EndpointBudget("/api/v1/auth/refresh", "POST", 100, 300),
    EndpointBudget("/api/v1/tenants", "GET", 150, 400),
    EndpointBudget("/api/v1/tenants", "POST", 250, 600),
    EndpointBudget("/api/v1/tenants/{id}", "GET", 100, 300),
    EndpointBudget("/api/v1/users", "GET", 200, 500),
    EndpointBudget("/api/v1/tools/execute", "POST", 500, 1000),
    EndpointBudget("/api/v1/health", "GET", 50, 150),
]


@pytest.mark.contract_static
@pytest.mark.slow
@pytest.mark.parametrize("budget", ENDPOINT_BUDGETS, ids=lambda b: f"{b.method}_{b.path}")
def test_endpoint_latency_budget(client, budget):
    """Verify each endpoint meets its latency budget."""
    latencies = []
    
    # Warm-up request
    client.open(budget.path, method=budget.method)
    
    # Collect 20 samples
    for _ in range(20):
        start = time.perf_counter()
        response = client.open(budget.path, method=budget.method)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
    
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    p99 = latencies[int(len(latencies) * 0.99) - 1]
    
    assert p95 <= budget.max_p95_ms, \
        f"{budget.method} {budget.path} P95={p95:.1f}ms exceeds budget {budget.max_p95_ms}ms"
    assert p99 <= budget.max_p99_ms, \
        f"{budget.method} {budget.path} P99={p99:.1f}ms exceeds budget {budget.max_p99_ms}ms"
```

---

## Area 2: JSON Schema Tool Manifests

### Objective
Validate all JSON Schema tool manifests to ensure tool definitions, input/output schemas, and metadata conform to the canonical schema.

### Tools
- **jsonschema** — JSON Schema validation in Python
- **hypothesis-jsonschema** — Property-based schema testing
- **pytest** — Test runner

### Test Code Examples

```python
# tests/contract/test_tool_manifests.py
"""
JSON Schema contract tests for tool manifests.
Validates that all tool definitions conform to the canonical schema.
"""
import json
import jsonschema
import pytest
from pathlib import Path
from hypothesis import given, settings, strategies as st
from hypothesis_jsonschema import from_schema


# ── Schema Definitions ───────────────────────────────────────────────────────

TOOL_MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "version", "description", "input_schema", "output_schema"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9_]*$",
            "minLength": 2,
            "maxLength": 64,
        },
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
        },
        "description": {
            "type": "string",
            "minLength": 10,
            "maxLength": 500,
        },
        "author": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[a-z][a-z0-9_-]*$"},
        },
        "input_schema": {
            "type": "object",
            "required": ["type", "properties"],
        },
        "output_schema": {
            "type": "object",
            "required": ["type"],
        },
        "config_schema": {
            "type": "object",
        },
        "permissions": {
            "type": "array",
            "items": {
                "enum": ["read", "write", "execute", "network", "filesystem"],
            },
        },
        "timeout_ms": {
            "type": "integer",
            "minimum": 100,
            "maximum": 300000,
        },
        "deprecated": {"type": "boolean"},
        "replaced_by": {"type": "string"},
    },
    "additionalProperties": False,
    "if": {"properties": {"deprecated": {"const": True}}},
    "then": {"required": ["replaced_by"]},
}


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tool_manifests_dir() -> Path:
    """Directory containing all tool manifest JSON files."""
    return Path(__file__).parents[2] / "tools" / "manifests"


@pytest.fixture(scope="session")
def all_manifests(tool_manifests_dir) -> list:
    """Load all tool manifests."""
    manifests = []
    for path in tool_manifests_dir.glob("*.json"):
        with open(path) as f:
            data = json.load(f)
        manifests.append((path.name, data))
    return manifests


# ── Schema Validation Tests ──────────────────────────────────────────────────

@pytest.mark.contract_static
class TestToolManifestSchema:
    """Validate all tool manifests against the canonical schema."""

    def test_all_manifests_conform_to_schema(self, all_manifests):
        """Every manifest must validate against TOOL_MANIFEST_SCHEMA."""
        errors = []
        for name, manifest in all_manifests:
            try:
                jsonschema.validate(instance=manifest, schema=TOOL_MANIFEST_SCHEMA)
            except jsonschema.ValidationError as e:
                errors.append(f"{name}: {e.message}")
        
        assert not errors, f"Schema validation failed for:\n" + "\n".join(errors)

    @pytest.mark.parametrize("manifest_name,manifest", [
        pytest.param(name, m, id=name)
        for name, m in []  # Populated dynamically via fixture
    ])
    def test_individual_manifest(self, manifest_name, manifest):
        """Each manifest validates independently (for granular failure)."""
        jsonschema.validate(instance=manifest, schema=TOOL_MANIFEST_SCHEMA)

    def test_manifest_name_matches_filename(self, all_manifests):
        """Tool name in manifest must match the filename (without .json)."""
        for filename, manifest in all_manifests:
            expected_name = filename.replace(".json", "")
            assert manifest["name"] == expected_name, \
                f"{filename}: name '{manifest['name']}' != filename '{expected_name}'"

    def test_unique_tool_names(self, all_manifests):
        """All tool names must be unique."""
        names = [m["name"] for _, m in all_manifests]
        assert len(names) == len(set(names)), \
            f"Duplicate tool names found: {[n for n in names if names.count(n) > 1]}"

    def test_semantic_versioning(self, all_manifests):
        """All versions must follow semantic versioning."""
        import re
        semver_pattern = re.compile(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?$")
        for filename, manifest in all_manifests:
            assert semver_pattern.match(manifest["version"]), \
                f"{filename}: invalid version '{manifest['version']}'"


# ── Input/Output Schema Contract Tests ───────────────────────────────────────

@pytest.mark.contract_static
class TestToolInputOutputContracts:
    """Validate tool input/output schemas are self-consistent."""

    def test_input_schemas_have_type(self, all_manifests):
        """Every input_schema must declare a top-level type."""
        for filename, manifest in all_manifests:
            assert "type" in manifest["input_schema"], \
                f"{filename}: input_schema missing 'type'"
            assert manifest["input_schema"]["type"] in ("object", "array", "string", "number"), \
                f"{filename}: invalid input_schema.type"

    def test_input_properties_have_types(self, all_manifests):
        """All properties in input_schema must have explicit types."""
        for filename, manifest in all_manifests:
            props = manifest["input_schema"].get("properties", {})
            for prop_name, prop_schema in props.items():
                assert "type" in prop_schema, \
                    f"{filename}: input property '{prop_name}' missing type"

    def test_required_properties_exist(self, all_manifests):
        """All required properties must exist in properties."""
        for filename, manifest in all_manifests:
            required = manifest["input_schema"].get("required", [])
            props = manifest["input_schema"].get("properties", {})
            for req in required:
                assert req in props, \
                    f"{filename}: required property '{req}' not in properties"


# ── Property-Based Schema Tests ──────────────────────────────────────────────

@pytest.mark.contract_static
class TestToolSchemaProperties:
    """Property-based tests for tool schema robustness."""

    @given(data=from_schema(TOOL_MANIFEST_SCHEMA))
    @settings(max_examples=100, deadline=None)
    def test_random_valid_manifests(self, data):
        """Randomly generated valid manifests should always validate."""
        jsonschema.validate(instance=data, schema=TOOL_MANIFEST_SCHEMA)

    @pytest.mark.parametrize("field", [
        "name", "version", "description", "input_schema", "output_schema",
    ])
    def test_required_field_absence(self, all_manifests, field):
        """Removing any required field should cause validation to fail."""
        for filename, manifest in all_manifests:
            test_manifest = {k: v for k, v in manifest.items() if k != field}
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(instance=test_manifest, schema=TOOL_MANIFEST_SCHEMA)


# ── Cross-Reference Validation ───────────────────────────────────────────────

@pytest.mark.contract_static
class TestToolCrossReferences:
    """Validate cross-references between tools and other system components."""

    def test_replaced_by_tool_exists(self, all_manifests):
        """If deprecated, replaced_by must reference an existing tool."""
        names = {m["name"] for _, m in all_manifests}
        for filename, manifest in all_manifests:
            if manifest.get("deprecated"):
                replaced_by = manifest.get("replaced_by", "")
                assert replaced_by in names, \
                    f"{filename}: replaced_by '{replaced_by}' not found"

    def test_permissions_are_valid(self, all_manifests):
        """All declared permissions must be from the allowed set."""
        valid_perms = {"read", "write", "execute", "network", "filesystem"}
        for filename, manifest in all_manifests:
            perms = set(manifest.get("permissions", []))
            invalid = perms - valid_perms
            assert not invalid, \
                f"{filename}: invalid permissions: {invalid}"
```

---

## Area 3: Auth Boundary Per Route

### Objective
Automatically inventory all routes and verify that each has the correct authentication boundary — public routes must not require auth, protected routes must enforce it.

### Tools
- **Flask/FastAPI route introspection** — Auto-discover routes
- **pytest** — Test runner
- **parameterized** — Dynamic test generation

### Test Code Examples

```python
# tests/contract/test_auth_boundary.py
"""
Auth boundary contract tests.
Automatically inventories all routes and verifies auth requirements.
"""
import pytest
import inspect
from typing import List, Dict, Set, Tuple
from http import HTTPStatus

from fabric_4l.app import create_app
from fabric_4l.config import TestConfig
from fabric_4l.auth.decorators import require_auth, require_admin
from fabric_4l.blueprints import all_blueprints


# ── Route Inventory ──────────────────────────────────────────────────────────

@dataclass
class RouteInfo:
    path: str
    methods: Set[str]
    endpoint: str
    view_function: callable
    has_auth_decorator: bool
    has_admin_decorator: bool
    is_public: bool  # From explicit @public decorator or whitelist


class RouteInventory:
    """Automatically discover and classify all application routes."""

    PUBLIC_ROUTE_PATTERNS = [
        "/health",
        "/ready",
        "/live",
        "/metrics",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/docs",
        "/api/v1/openapi.json",
        "/static/.*",
    ]

    def __init__(self, app):
        self.app = app
        self.routes = self._discover()

    def _discover(self) -> List[RouteInfo]:
        """Introspect Flask app to discover all routes."""
        routes = []
        for rule in self.app.url_map.iter_rules():
            # Skip static and OPTIONS
            methods = rule.methods - {"HEAD", "OPTIONS"}
            if not methods:
                continue

            endpoint = self.app.view_functions.get(rule.endpoint)
            if endpoint is None:
                continue

            # Check decorators
            source = inspect.getsource(endpoint) if hasattr(endpoint, '__code__') else ""
            has_auth = "require_auth" in source or hasattr(endpoint, "_auth_required")
            has_admin = "require_admin" in source or hasattr(endpoint, "_admin_required")
            is_public = self._is_public(str(rule.rule))

            routes.append(RouteInfo(
                path=str(rule.rule),
                methods=methods,
                endpoint=rule.endpoint,
                view_function=endpoint,
                has_auth_decorator=has_auth,
                has_admin_decorator=has_admin,
                is_public=is_public,
            ))
        return routes

    def _is_public(self, path: str) -> bool:
        import re
        for pattern in self.PUBLIC_ROUTE_PATTERNS:
            if re.match(pattern, path):
                return True
        return False

    @property
    def protected_routes(self) -> List[RouteInfo]:
        return [r for r in self.routes if not r.is_public]

    @property
    def public_routes(self) -> List[RouteInfo]:
        return [r for r in self.routes if r.is_public]


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def inventory():
    app = create_app(config_class=TestConfig)
    return RouteInventory(app)


@pytest.fixture(scope="module")
def unauthenticated_client():
    app = create_app(config_class=TestConfig)
    return app.test_client()


# ── Auth Boundary Tests ──────────────────────────────────────────────────────

@pytest.mark.contract_static
@pytest.mark.security
class TestAuthBoundary:
    """Verify auth boundary is correctly enforced for all routes."""

    def test_all_routes_inventoried(self, inventory):
        """Route inventory must discover > 0 routes."""
        assert len(inventory.routes) > 0, "No routes discovered"
        print(f"\nDiscovered {len(inventory.routes)} routes")
        print(f"  Public: {len(inventory.public_routes)}")
        print(f"  Protected: {len(inventory.protected_routes)}")

    def test_protected_routes_require_auth(self, inventory, unauthenticated_client):
        """All non-public routes must return 401 without auth."""
        failures = []
        for route in inventory.protected_routes:
            for method in route.methods:
                if method == "GET":  # Test one method per route
                    resp = unauthenticated_client.open(route.path, method=method)
                    if resp.status_code not in (401, 403, 302):
                        failures.append(
                            f"{method} {route.path}: got {resp.status_code}, expected 401/403"
                        )
        assert not failures, f"Auth boundary failures:\n" + "\n".join(failures[:20])

    def test_public_routes_allow_anonymous(self, inventory, unauthenticated_client):
        """Public routes must not require authentication."""
        failures = []
        for route in inventory.public_routes:
            for method in route.methods:
                if method in ("GET", "POST"):
                    resp = unauthenticated_client.open(route.path, method=method)
                    # Public routes should NOT return 401
                    if resp.status_code == 401:
                        failures.append(f"{method} {route.path}: public route returned 401")
        assert not failures, f"Public route auth failures:\n" + "\n".join(failures[:20])

    @pytest.mark.parametrize("route_info", [
        pytest.param(r, id=f"{list(r.methods)[0]}_{r.path}")
        for r in []  # Dynamically populated below
    ])
    def test_individual_route_auth(self, route_info, unauthenticated_client):
        """Each protected route independently requires auth."""
        if route_info.is_public:
            return  # Skip public routes
        method = "GET" if "GET" in route_info.methods else list(route_info.methods)[0]
        resp = unauthenticated_client.open(route_info.path, method=method)
        assert resp.status_code in (401, 403, 404), \
            f"{method} {route_info.path}: expected 401/403, got {resp.status_code}"


def pytest_generate_tests(metafunc):
    """Dynamically generate route-based tests."""
    if "route_info" in metafunc.fixturenames:
        app = create_app(config_class=TestConfig)
        inv = RouteInventory(app)
        metafunc.parametrize(
            "route_info",
            [pytest.param(r, id=f"{list(r.methods)[0]}_{r.path}".replace("/", "_"))
             for r in inv.routes[:50]],  # Limit to first 50 for speed
        )


# ── Admin Boundary Tests ─────────────────────────────────────────────────────

@pytest.mark.contract_static
@pytest.mark.security
class TestAdminBoundary:
    """Verify admin routes require admin privileges."""

    def test_admin_routes_require_admin_role(self, inventory, client):
        """Admin routes must reject non-admin authenticated users."""
        # Create a regular user token (mocked)
        regular_token = "mock_regular_user_token"
        
        admin_routes = [r for r in inventory.routes if r.has_admin_decorator]
        failures = []
        
        for route in admin_routes:
            for method in route.methods:
                if method == "GET":
                    resp = client.open(
                        route.path,
                        method=method,
                        headers={"Authorization": f"Bearer {regular_token}"},
                    )
                    if resp.status_code != 403:
                        failures.append(
                            f"{method} {route.path}: non-admin got {resp.status_code}, expected 403"
                        )
        
        assert not failures, f"Admin boundary failures:\n" + "\n".join(failures[:20])


# ── Tenant Boundary Tests ────────────────────────────────────────────────────

@pytest.mark.tenant_boundary
@pytest.mark.contract_static
class TestTenantBoundary:
    """Verify multi-tenant data isolation at the route level."""

    def test_tenant_routes_reject_cross_tenant_access(self, client, auth_headers):
        """Authenticated users cannot access other tenants' data."""
        # User from tenant_A tries to access tenant_B resource
        tenant_a_headers = {**auth_headers, "X-Tenant-ID": "tenant-a"}
        tenant_b_path = "/api/v1/tenants/tenant-b/users"
        
        resp = client.open(tenant_b_path, method="GET", headers=tenant_a_headers)
        assert resp.status_code in (403, 404), \
            f"Cross-tenant access should be forbidden, got {resp.status_code}"

    def test_tenant_header_required(self, client, auth_headers):
        """Tenant-scoped routes require X-Tenant-ID header."""
        headers_no_tenant = {k: v for k, v in auth_headers.items() if k != "X-Tenant-ID"}
        resp = client.open("/api/v1/users", method="GET", headers=headers_no_tenant)
        assert resp.status_code == 400, \
            f"Missing tenant header should return 400, got {resp.status_code}"
```

---

## Area 4: Dev-Bypass Safety in Production

### Objective
Ensure that development bypass mechanisms (mock auth, debug flags, test endpoints) are completely disabled in production builds and cannot be activated.

### Test Code Examples

```python
# tests/contract/test_prod_bypass_safety.py
"""
Production bypass safety contract tests.
Verifies that dev-only bypass mechanisms are disabled in production.
"""
import os
import pytest
from unittest.mock import patch

from fabric_4l.app import create_app
from fabric_4l.config import ProductionConfig, DevelopmentConfig


# ── Environment Detection Tests ──────────────────────────────────────────────

@pytest.mark.contract_static
@pytest.mark.security
class TestProductionEnvironmentFlags:
    """Verify production configuration disables all bypasses."""

    def test_production_has_debug_disabled(self):
        """ProductionConfig.DEBUG must be False."""
        config = ProductionConfig()
        assert config.DEBUG is False, "DEBUG must be False in production"

    def test_production_has_testing_disabled(self):
        """ProductionConfig.TESTING must be False."""
        config = ProductionConfig()
        assert config.TESTING is False, "TESTING must be False in production"

    def test_no_env_var_enables_debug_in_production(self):
        """No environment variable should enable DEBUG in production."""
        dangerous_vars = ["DEBUG", "FABRIC_DEBUG", "DEV_MODE", "BYPASS_AUTH"]
        for var in dangerous_vars:
            assert var not in os.environ or os.environ[var] != "1", \
                f"Dangerous env var {var}=1 detected"

    def test_secret_key_not_default(self):
        """Production SECRET_KEY must not be the default/dev value."""
        config = ProductionConfig()
        default_keys = ["dev-secret-key", "change-me", "default", "test-secret"]
        assert config.SECRET_KEY not in default_keys, \
            "Production SECRET_KEY appears to be a default value"
        assert len(config.SECRET_KEY) >= 32, \
            "Production SECRET_KEY must be at least 32 characters"


# ── Auth Bypass Endpoint Tests ───────────────────────────────────────────────

@pytest.mark.contract_static
@pytest.mark.security
class TestAuthBypassDisabled:
    """Verify auth bypass endpoints are disabled in production."""

    PRODUCTION_BYPASS_ENDPOINTS = [
        "/api/v1/auth/bypass",
        "/api/v1/auth/mock-login",
        "/api/v1/auth/dev-token",
        "/api/v1/debug/user-impersonate",
        "/api/v1/debug/override-tenant",
    ]

    def test_bypass_endpoints_return_404(self):
        """All known bypass endpoints must return 404 in production."""
        app = create_app(config_class=ProductionConfig)
        client = app.test_client()
        
        for endpoint in self.PRODUCTION_BYPASS_ENDPOINTS:
            for method in ["GET", "POST", "PUT", "DELETE"]:
                resp = client.open(endpoint, method=method)
                assert resp.status_code == 404, \
                    f"{method} {endpoint}: bypass endpoint accessible (got {resp.status_code})"

    def test_no_debug_routes_exist(self):
        """No debug/test routes should be registered in production."""
        app = create_app(config_class=ProductionConfig)
        
        debug_patterns = ["debug", "test", "mock", "bypass", "dev-", "stub"]
        for rule in app.url_map.iter_rules():
            path = str(rule.rule).lower()
            for pattern in debug_patterns:
                assert pattern not in path, \
                    f"Debug route found in production: {rule.rule}"

    def test_swagger_ui_disabled(self):
        """Swagger/OpenAPI UI must be disabled in production."""
        app = create_app(config_class=ProductionConfig)
        client = app.test_client()
        
        ui_paths = ["/docs", "/swagger-ui", "/api/docs", "/redoc"]
        for path in ui_paths:
            resp = client.get(path)
            assert resp.status_code in (404, 403), \
                f"API docs UI accessible in production at {path}"


# ── Configuration Safety Tests ───────────────────────────────────────────────

@pytest.mark.contract_static
@pytest.mark.security
class TestConfigurationSafety:
    """Verify production configuration safety invariants."""

    def test_sqlalchemy_echo_disabled(self):
        """SQL echo must be disabled in production."""
        config = ProductionConfig()
        assert not getattr(config, "SQLALCHEMY_ECHO", False), \
            "SQLALCHEMY_ECHO must be False in production"

    def test_propagate_exceptions_disabled(self):
        """Exception propagation must not expose internals."""
        app = create_app(config_class=ProductionConfig)
        assert not app.propagate_exceptions, \
            "Exception propagation should be disabled in production"

    def test_error_handlers_mask_details(self):
        """Error responses must not leak internal details."""
        app = create_app(config_class=ProductionConfig)
        client = app.test_client()
        
        # Trigger a 500 error
        resp = client.get("/api/v1/trigger-error")
        if resp.status_code == 500:
            data = resp.get_json() or {}
            assert "traceback" not in str(data).lower(), \
                "Error response contains traceback"
            assert "stack" not in str(data).lower(), \
                "Error response contains stack trace"
            assert "password" not in str(data).lower(), \
                "Error response may contain sensitive data"

    @pytest.mark.parametrize("header", [
        "X-Debug-Mode",
        "X-Bypass-Auth",
        "X-Dev-Override",
        "X-Mock-User",
    ])
    def test_debug_headers_ignored(self, header):
        """Debug headers must be ignored in production."""
        app = create_app(config_class=ProductionConfig)
        client = app.test_client()
        
        resp_normal = client.get("/api/v1/health")
        resp_debug = client.get("/api/v1/health", headers={header: "true"})
        
        assert resp_normal.status_code == resp_debug.status_code, \
            f"Debug header {header} changed response behavior"


# ── Build-Time Safety Tests ──────────────────────────────────────────────────

@pytest.mark.contract_static
class TestBuildTimeSafety:
    """Verify production build artifacts exclude dev code."""

    def test_no_test_files_in_production_build(self):
        """Test files must not be included in production container."""
        # In CI, verify the Docker image doesn't contain test code
        excluded_patterns = [
            "tests/",
            "conftest.py",
            "test_*.py",
            "*_test.py",
            "pytest.ini",
            ".pytest_cache",
        ]
        # This test runs in CI after Docker build
        if os.path.exists("/app"):  # Container path
            for root, dirs, files in os.walk("/app"):
                for pattern in excluded_patterns:
                    assert pattern not in dirs and pattern not in files, \
                        f"Test artifact '{pattern}' found in production build"

    def test_no_pdb_breakpoints_in_source(self):
        """Source code must not contain pdb breakpoints."""
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "pdb.set_trace\|breakpoint()", "fabric_4l/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0 or not result.stdout, \
            f"Debugger breakpoints found in source:\n{result.stdout}"

    def test_dev_dependencies_not_in_production(self):
        """Dev-only dependencies should not be installed in production."""
        dev_only_packages = ["pytest", "pytest-cov", "pytest-xdist",
                           "mutmut", "hypothesis", "ipython", "pdb++"]
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
        )
        installed = result.stdout.lower()
        
        for pkg in dev_only_packages:
            assert pkg not in installed, \
                f"Dev package '{pkg}' found in production environment"
```

---

## Area 5: Startup Guard Validation

### Objective
Validate that all startup guards (configuration validation, dependency checks, database migrations, feature flags) execute correctly and fail fast on invalid conditions.

### Test Code Examples

```python
# tests/contract/test_startup_guards.py
"""
Startup guard contract tests.
Validates that the application fails fast on invalid configuration.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from fabric_4l.app import create_app
from fabric_4l.config import ProductionConfig, TestConfig
from fabric_4l.startup import StartupGuard, StartupCheckResult


# ── Startup Guard Tests ──────────────────────────────────────────────────────

@pytest.mark.contract_static
class TestStartupGuards:
    """Verify startup guards catch configuration errors."""

    def test_missing_database_url_fails(self):
        """App must fail to start without DATABASE_URL."""
        env = os.environ.copy()
        env.pop("DATABASE_URL", None)
        
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="DATABASE_URL"):
                create_app(config_class=ProductionConfig)

    def test_invalid_database_url_fails(self):
        """App must fail with malformed DATABASE_URL."""
        with patch.dict(os.environ, {"DATABASE_URL": "not-a-valid-url"}):
            with pytest.raises(RuntimeError):
                create_app(config_class=ProductionConfig)

    def test_missing_redis_url_warns(self):
        """App should start without REDIS_URL but log warning."""
        env = {k: v for k, v in os.environ.items() if k != "REDIS_URL"}
        env["DATABASE_URL"] = "postgresql://test:test@localhost/test"
        
        with patch.dict(os.environ, env, clear=True):
            app = create_app(config_class=ProductionConfig)
            assert app is not None

    def test_invalid_secret_key_fails(self):
        """App must fail with weak SECRET_KEY."""
        with patch.object(ProductionConfig, "SECRET_KEY", "short"):
            with pytest.raises(RuntimeError, match="SECRET_KEY"):
                create_app(config_class=ProductionConfig)

    def test_missing_required_env_vars(self):
        """All required env vars must be present."""
        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "JWT_ISSUER",
            "TENANT_ENCRYPTION_KEY",
        ]
        
        for var in required_vars:
            env = {k: v for k, v in os.environ.items() if k != var}
            env["DATABASE_URL"] = "postgresql://test:test@localhost/test"
            env["SECRET_KEY"] = "a" * 64
            
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises((RuntimeError, KeyError)):
                    create_app(config_class=ProductionConfig)


# ── Dependency Check Tests ───────────────────────────────────────────────────

@pytest.mark.contract_static
class TestDependencyChecks:
    """Verify startup dependency validation."""

    def test_database_connection_check(self):
        """Startup must verify database connectivity."""
        guard = StartupGuard()
        
        result = guard.check_database()
        assert result.status in ("ok", "warning"), \
            f"Database check failed: {result.message}"

    def test_database_migration_check(self):
        """Startup must verify migrations are current."""
        guard = StartupGuard()
        
        result = guard.check_migrations()
        assert result.status in ("ok", "warning"), \
            f"Migration check failed: {result.message}"

    def test_redis_connection_check(self):
        """Startup must verify Redis connectivity if configured."""
        if "REDIS_URL" not in os.environ:
            pytest.skip("REDIS_URL not configured")
        
        guard = StartupGuard()
        result = guard.check_redis()
        assert result.status in ("ok", "warning"), \
            f"Redis check failed: {result.message}"

    def test_critical_feature_flags_defined(self):
        """All critical feature flags must have defined defaults."""
        from fabric_4l.feature_flags import CRITICAL_FLAGS
        
        guard = StartupGuard()
        result = guard.check_feature_flags()
        
        for flag in CRITICAL_FLAGS:
            assert flag in result.flags, \
                f"Critical feature flag '{flag}' not validated at startup"


# ── Health Check Endpoint Tests ──────────────────────────────────────────────

@pytest.mark.contract_static
class TestHealthCheckEndpoints:
    """Verify health/readiness probes reflect startup state."""

    def test_health_endpoint_returns_200(self, client):
        """/health must return 200 when app is healthy."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"

    def test_ready_endpoint_checks_dependencies(self, client):
        """/ready must check all critical dependencies."""
        resp = client.get("/api/v1/ready")
        assert resp.status_code in (200, 503)
        
        data = resp.get_json()
        assert "database" in data.get("checks", {})
        assert "migrations" in data.get("checks", {})

    def test_ready_returns_503_on_db_failure(self, client):
        """/ready must return 503 when database is unreachable."""
        with patch("fabric_4l.health.check_database") as mock_check:
            mock_check.return_value = StartupCheckResult(
                status="error",
                message="Connection refused",
            )
            resp = client.get("/api/v1/ready")
            assert resp.status_code == 503

    def test_health_response_format(self, client):
        """Health response must match contract schema."""
        resp = client.get("/api/v1/health")
        data = resp.get_json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        
        # No sensitive data
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()
        assert "token" not in str(data).lower()


# ── Configuration Schema Validation ──────────────────────────────────────────

@pytest.mark.contract_static
class TestConfigurationSchema:
    """Validate configuration schema at startup."""

    def test_all_config_values_have_types(self):
        """All config values must be strongly typed."""
        config = ProductionConfig()
        
        typed_configs = {
            "DEBUG": bool,
            "TESTING": bool,
            "SECRET_KEY": str,
            "DATABASE_URL": str,
            "JWT_EXPIRATION_SECONDS": int,
            "MAX_UPLOAD_SIZE": int,
            "ENABLE_RATE_LIMITING": bool,
        }
        
        for key, expected_type in typed_configs.items():
            value = getattr(config, key, None)
            assert value is not None, f"Config {key} is not set"
            assert isinstance(value, expected_type), \
                f"Config {key} expected {expected_type.__name__}, got {type(value).__name__}"

    def test_url_configs_are_valid(self):
        """All URL configs must be valid URLs."""
        from urllib.parse import urlparse
        
        config = ProductionConfig()
        url_keys = ["DATABASE_URL", "REDIS_URL"]
        
        for key in url_keys:
            value = getattr(config, key, None)
            if value:
                parsed = urlparse(value)
                assert parsed.scheme and parsed.netloc, \
                    f"Config {key} is not a valid URL: {value}"

    def test_numeric_configs_in_valid_range(self):
        """Numeric configs must be in valid ranges."""
        config = ProductionConfig()
        
        assert config.JWT_EXPIRATION_SECONDS > 0
        assert config.JWT_EXPIRATION_SECONDS <= 86400  # Max 24 hours
        assert config.MAX_UPLOAD_SIZE > 0
        assert config.MAX_UPLOAD_SIZE <= 100 * 1024 * 1024  # Max 100MB
        assert config.RATE_LIMIT_REQUESTS_PER_MINUTE > 0
        assert config.RATE_LIMIT_REQUESTS_PER_MINUTE <= 10000


# ── Graceful Degradation Tests ───────────────────────────────────────────────

@pytest.mark.contract_static
class TestGracefulDegradation:
    """Verify graceful degradation when optional services are unavailable."""

    def test_starts_without_redis(self):
        """App must start (with warnings) when Redis is unavailable."""
        env = {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "SECRET_KEY": "a" * 64,
            "REDIS_URL": "redis://invalid-host:6379/0",
        }
        
        with patch.dict(os.environ, env, clear=True):
            # Should not raise, but may log warnings
            app = create_app(config_class=ProductionConfig)
            assert app is not None

    def test_starts_without_celery_broker(self):
        """App must start without Celery broker (tasks queued locally)."""
        env = {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "SECRET_KEY": "a" * 64,
        }
        
        with patch.dict(os.environ, env, clear=True):
            app = create_app(config_class=ProductionConfig)
            assert app is not None
            # Tasks should fall back to synchronous execution
            assert app.config.get("TASK_ALWAYS_EAGER", False) is True

    def test_rate_limiting_disabled_without_redis(self):
        """Rate limiting should disable itself when Redis is unavailable."""
        with patch("fabric_4l.extensions.redis_client.ping", side_effect=ConnectionError):
            app = create_app(config_class=ProductionConfig)
            assert not app.config.get("RATE_LIMITING_ENABLED", False)
```

---

## Implementation Timeline

| Week | Area | Deliverable | Owner |
|------|------|-------------|-------|
| W1 | Area 1 | Schemathesis base config + top 10 endpoint tests | @backend-team |
| W1 | Area 2 | Tool manifest schema + validation tests | @backend-team |
| W2 | Area 1 | Expand to 50% endpoint coverage | @backend-team |
| W2 | Area 3 | Route inventory + auth boundary tests | @backend-team |
| W3 | Area 1 | Expand to 70% endpoint coverage | @backend-team |
| W3 | Area 3 | Admin boundary + tenant isolation tests | @backend-team |
| W4 | Area 4 | Dev-bypass safety tests (all bypass types) | @security-team |
| W4 | Area 5 | Startup guard framework + config tests | @backend-team |
| W5 | Area 4 | Build-time safety tests (Docker CI) | @devops-team |
| W5 | Area 5 | Dependency check + health probe tests | @backend-team |
| W6 | All | Integration testing + flaky test monitoring | @qa-team |
| W7 | All | Coverage analysis + gap remediation | @all |
| W8 | All | Final review + scorecard update | @qa-team |

---

## Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| OpenAPI endpoint contract coverage | ≥ 70% | schemathesis test count / total endpoints |
| Tool manifest schema coverage | ≥ 60% | manifests with passing tests / total manifests |
| Auth boundary route coverage | ≥ 60% | inventoried routes with auth tests / total routes |
| Dev-bypass safety coverage | ≥ 80% | bypass types with tests / total bypass types |
| Startup guard coverage | ≥ 70% | startup checks with tests / total checks |
| Contract test pass rate | 100% | No contract test failures in CI |
| Contract test execution time | < 10 min | CI pipeline wall clock time |

---

*Spec authored by QA Architecture. Reviewed by Backend Lead, Security Lead.*
*Last updated: 2024-06-15*
