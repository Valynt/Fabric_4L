# Architecture Decision Records

All significant technical decisions for Value Fabric are documented here using ADRs.

## Process

1. When a significant technical decision is needed, create a new ADR using TEMPLATE.md
2. Number sequentially (0001, 0002, ...)
3. Status starts as "proposed"
4. After implementation and validation, update to "accepted"
5. If superseded, update status to "superseded by ADR-XXXX" and update the superseder
6. Add the ADR to [`adr-registry.yaml`](./adr-registry.yaml) with related code paths — `make check-adr` fails any ADR file missing from the registry, including proposed ones
7. Run `make check-adr` before opening the PR

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](./0001-websocket-jwt-canonical-decoder.md) | WebSocket JWT Canonical Decoder | accepted | 2024-01-15 |
| [0002](./0002-knowledge-tool-runtime-tenant-context.md) | Knowledge Tool Runtime Tenant Context | accepted | 2024-01-15 |
| [0003](./0003-audit-emission-middleware-boundary.md) | Audit Emission Middleware Boundary | accepted | 2024-01-15 |
| [0004](./0004-layer4-database-facade-compatibility.md) | Layer 4 Database Facade Compatibility | accepted | 2024-01-15 |
| [0005](./0005-shared-identity-canonical-runtime-location.md) | Shared Identity Canonical Runtime Location | accepted | 2026-05-22 |

## When to Write an ADR

- Fixing contract mismatches between services
- Changing auth/tenant isolation behavior
- Adding compatibility shims or facade layers
- Modifying security-critical code paths
- Any change that required Plan Mode approval in the launch hardening process
