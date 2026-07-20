# Fabric 4L Tenant Management Project Plan

This document adapts the generic Tenant Management Module requirements into a concrete, phased project plan specific to the Fabric 4L repository. It maps the requirements to the existing FastAPI, Postgres, Keycloak, and Infisical infrastructure, identifying what is already built and what must be developed.

## 1. Current State Assessment

The Fabric 4L backend already possesses a robust foundation for multi-tenancy, primarily focused on runtime enforcement and identity resolution.

### 1.1 Existing Infrastructure

The identity and context layers are well-developed. The `RequestContext` in `shared/identity/context.py` provides thread-safe tenant isolation via `ContextVar`. The `GovernanceMiddleware` resolves the tenant ID from JWT claims, API keys, or headers. The OIDC client (`shared/identity/oidc.py`) handles Keycloak token validation, JWKS caching, and role mapping. Six distinct roles (super_admin, tenant_admin, content_admin, analyst, read_only, system) are defined with granular permissions.

Database isolation currently relies on Row-Level Security (RLS). The `layer4-agents/src/database.py` module manages async sessions and executes `SET LOCAL app.tenant_id` to enforce RLS policies per transaction. Migrations exist for RLS policies across multiple layers.

Billing and feature flag foundations are present. Migrations in Layer 4 define tables for `billing_customers`, `billing_subscriptions`, and `feature_flags`. Infisical integration (`shared/secrets/infisical.py`) supports tenant-scoped secret paths.

### 1.2 Identified Gaps

Despite the strong foundation, several critical components required for a self-service control plane are missing.

The most significant gap is the lack of a central tenant registry and lifecycle management. There is no `tenants` table in the public schema, no self-service registration endpoint, and no automated provisioning pipeline.

Furthermore, the database isolation strategy needs to be upgraded. The current RLS approach must be replaced with a schema-per-tenant model using `fastapi-tenancy` to meet the strict isolation requirements of enterprise customers.

Finally, Keycloak and Infisical automation are absent. While token validation works, the programmatic creation of Keycloak realms and Infisical secret paths during tenant onboarding has not been implemented.

## 2. Phased Implementation Plan

The implementation is divided into three phases, prioritizing core isolation and automated provisioning before building the user-facing control plane.

### Phase 1: Core Isolation Upgrade (Schema-per-Tenant)

This phase upgrades the database isolation strategy from RLS to schema-per-tenant, ensuring strict data separation.

**Task 1.1: Integrate `fastapi-tenancy`**
Add the `fastapi-tenancy` library to manage schema isolation. Configure the `TenancyManager` to use the `schema` isolation strategy and resolve tenants via JWT claims.

**Task 1.2: Refactor Database Session Management**
Replace the custom `db_session` context manager in `layer4-agents/src/database.py` with `fastapi-tenancy`'s dependency injection. Ensure that `SET LOCAL search_path` is executed within the transaction scope to prevent connection pool leakage.

**Task 1.3: Update Alembic Migrations**
Configure Alembic to run migrations across all tenant schemas. Remove the existing RLS policies from the migration files, as schema isolation renders them redundant.

### Phase 2: Automated Provisioning Pipeline

This phase builds the backend orchestration required to onboard a new tenant without manual intervention.

**Task 2.1: Create the Tenant Registry**
Define the `tenants` table in the `public` schema to track tenant metadata, status (e.g., pending, active, suspended), and subscription tier.

**Task 2.2: Implement Keycloak Automation**
Develop a service using `python-keycloak` to programmatically create a new realm for each tenant. This service must configure the necessary clients, seed default roles, and create the initial tenant administrator account.

**Task 2.3: Implement Infisical Automation**
Extend the provisioning service to call the Infisical REST API. Create a dedicated secret path (e.g., `/tenants/{tenant_slug}`) and seed it with default configuration values.

**Task 2.4: Orchestrate the Provisioning Workflow**
Create a transactional `provision_tenant` function that executes the database, Keycloak, and Infisical provisioning steps sequentially. Implement rollback logic to handle failures gracefully.

### Phase 3: Self-Service Control Plane

This phase delivers the user-facing features defined in the requirements document, enabling autonomous tenant management.

**Task 3.1: Develop the Registration API**
Implement the `/api/v1/tenants/register` endpoint. This endpoint must validate subdomain uniqueness, initiate email verification, and trigger the automated provisioning pipeline upon successful verification.

**Task 3.2: Implement Subscription Tier Management**
Define the subscription tiers (Free, Basic, Pro, Enterprise) in a configuration file. Implement the upgrade and downgrade workflows, integrating with the existing Stripe billing tables to handle prorated charges.

**Task 3.3: Build the Tenant Admin Dashboard API**
Develop the endpoints required for the Tenant Admin Dashboard. This includes endpoints for managing users (`/api/v1/tenants/{tenant_id}/users`), configuring branding (`/api/v1/tenants/{tenant_id}/branding`), and retrieving usage metrics (`/api/v1/tenants/{tenant_id}/usage`).

## 3. Data Model Updates

The following updates to the data model are required to support the Tenant Management Module.

### 3.1 Public Schema (Global)

The `public` schema will house the central tenant registry and global configuration.

*   **`tenants`**: Stores tenant ID, subdomain, organization name, status, and tier ID.
*   **`tiers`**: Defines the available subscription tiers, resource limits, and pricing.
*   **`audit_log`**: An immutable, append-only table recording all administrative actions across all tenants.

### 3.2 Tenant Schemas (Isolated)

Each tenant schema will contain the tables specific to that organization's data and configuration.

*   **`users`**: Stores the users associated with the tenant and their assigned roles.
*   **`roles`**: Defines custom roles and permissions within the tenant boundary.
*   **`tenant_features`**: Stores tenant-specific feature flag overrides.
*   **`usage_metrics`**: Tracks token consumption, agent executions, and storage usage for billing purposes.
