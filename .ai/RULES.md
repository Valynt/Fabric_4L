# AI Guidance Index

<!-- markdownlint-disable MD013 -->

This file is a navigation aid, not a second policy source. The repository-root
[`AGENTS.md`](../AGENTS.md) is authoritative. More specific `AGENTS.md` files apply within
their directory scopes, and canonical security or contract documents win over summaries.

## Read Before Changing Anything

| Concern | Canonical source |
| --- | --- |
| Setup, package manager, validation, and change safety | [`AGENTS.md`](../AGENTS.md) |
| Build and command selection | [`docs/development/BUILD_SYSTEM.md`](../docs/development/BUILD_SYSTEM.md) and [`docs/development/COMMANDS.md`](../docs/development/COMMANDS.md) |
| Security and development-auth controls | [`SECURITY.md`](../SECURITY.md) |
| Tenant, middleware, and cross-layer contracts | [`docs/contract.md`](../docs/contract.md) |
| CI classification and ownership | [`docs/development/CI_GATES.md`](../docs/development/CI_GATES.md) |
| Code ownership | [`CODEOWNERS`](../CODEOWNERS) |
| Type-escape governance | [`config/ci/type_escape_baseline.json`](../config/ci/type_escape_baseline.json) and [`scripts/ci/type_escape_ratchet.py`](../scripts/ci/type_escape_ratchet.py) |
| Architecture decisions | [`docs/explanations/adr/`](../docs/explanations/adr/) |

Do not restate those documents in task-specific guidance. Link to them and verify the live
implementation when a claim could have changed.

## Setup Boundary

`make setup` installs Python development dependencies into the repository-managed pytest
environment. It does not start infrastructure or apply migrations. Follow the separate startup
and migration steps in [`AGENTS.md`](../AGENTS.md#first-time-setup).

## Tenant Context

Use the maintained identity package. Never accept a request-body tenant identifier as authority.
Code that relies on ambient context must fail closed when the context is absent.

```python
from value_fabric.shared.identity.context import RequestContext, get_request_context

ctx: RequestContext | None = get_request_context()
if ctx is None:
    raise RuntimeError("authenticated request context is required")
tenant_id = ctx.tenant_id
```

Service-specific dependency injection may provide `RequestContext` directly. Follow the canonical
pattern already used by that service and the contract in [`docs/contract.md`](../docs/contract.md).

## Development-Auth Flags

The governed development-only flags are:

- `DEV_AUTH_BYPASS`
- `ALLOW_DEV_AUTH_BYPASS`
- `AUTH_BYPASS_ENABLED`
- `ALLOW_INSECURE_DEV_AUTH_BYPASS`

They must never be enabled in production-like environments. Do not invent additional aliases.
See [`SECURITY.md`](../SECURITY.md#development-authentication-bypass) for accepted values, startup
enforcement, and tests.

## Pull Requests

- Make the smallest safe change and preserve unrelated work.
- Do not push directly to `main`.
- Report exact validation commands and results.
- State contract, tenant-isolation, compatibility, risk, and rollback impact.
- Do not weaken required checks, security gates, authentication, RBAC, or tenant isolation.
