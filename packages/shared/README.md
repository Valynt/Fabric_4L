# Value Fabric Shared Library

Cross-service Python utilities used by all backend layers.

## Contents

- \`value_fabric/shared/identity/\` — Tenant context, JWT middleware, auth primitives
- \`value_fabric/shared/security/\` — Production safety validators, security headers
- \`value_fabric/shared/startup/\` — Startup validation hooks
- \`value_fabric/shared/resilience/\` — Circuit breakers, retry policies

## Usage

Imported as a path dependency by all services via \`PYTHONPATH\`.

## Adding code here

Keep this package focused on **horizontal concerns** (auth, observability,
resilience). Domain logic belongs in the service that owns it.
