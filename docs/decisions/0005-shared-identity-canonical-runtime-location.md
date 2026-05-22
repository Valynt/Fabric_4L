# ADR-0005: Shared Identity Canonical Runtime Location

- Status: accepted
- Date: 2026-05-22
- Owners: Platform + Security Engineering

## Context

Shared identity imports have been used through multiple historical paths (`shared.identity.*`, service-local wrappers, and canonical `value_fabric.shared.identity.*`). That ambiguity increases drift risk and weakens CI policy enforcement.

## Decision

1. The **single canonical runtime package location** for shared identity is:
   - `packages/shared/src/value_fabric/shared/identity/`
2. The **single approved import namespace** is:
   - `from value_fabric.shared.identity import ...`
   - `from value_fabric.shared.identity.<module> import ...`
3. All layer-local and legacy root imports are disallowed for net-new code:
   - `shared.identity.*`
   - `value_fabric.layer*/identity*`
   - service-local `...identity...` modules unless explicitly listed in shim allowlists.

## Enforcement

- CI guardrail: `scripts/ci/check_shared_identity_canonical_imports.py`
- Temporary shim exceptions (if absolutely required):
  - `config/ci/shared_identity_import_shim_allowlist.txt`

## Public API boundary (canonical package)

Public API modules (approved for external imports):
- `value_fabric.shared.identity.context`
- `value_fabric.shared.identity.dependencies`
- `value_fabric.shared.identity.middleware`
- `value_fabric.shared.identity.permissions`
- `value_fabric.shared.identity.isolation`
- `value_fabric.shared.identity.jwt`
- `value_fabric.shared.identity.oidc`
- `value_fabric.shared.identity.models`
- `value_fabric.shared.identity.protocols`

Internal-only modules (do not import outside `value_fabric.shared.identity` package internals unless promoted):
- `value_fabric.shared.identity._internal.*`
- private module members prefixed with `_`
- helper implementation files not listed in the public API set above

## Consequences

- New code has one clear import path and a deterministic CI policy.
- Existing compatibility imports must be migrated or explicitly allowlisted with follow-up removal owners.
