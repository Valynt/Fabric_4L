# Dependency Policy

## Package Managers

This monorepo is pnpm-only for JavaScript and TypeScript workspaces. Do not use npm or yarn install commands.

Python services use service-local dependency definitions and committed `uv.lock` files.

## Canonical Lockfiles

Required lockfiles:

- `pnpm-lock.yaml`
- `apps/web/pnpm-lock.yaml`
- `services/layer1-ingestion/uv.lock`
- `services/layer2-extraction/uv.lock`
- `services/layer3-knowledge/uv.lock`
- `services/layer4-agents/uv.lock`
- `services/layer5-ground-truth/uv.lock`
- `services/layer6-benchmarks/uv.lock`

CI and Docker builds must use frozen lockfile installs. Lockfile drift after install fails the gate.

## Dependency Updates

Dependency changes must:

- Update only approved lockfile paths.
- Preserve package-manager enforcement scripts.
- Pass dependency review, audit, license, and supply-chain tests.
- Include a security rationale for major upgrades, new runtime dependencies, or dependency replacements.

## License Policy

Production dependencies may not introduce the following licenses without written legal and security approval:

- `AGPL-3.0`
- `GPL-3.0`
- `LGPL-3.0`
- `SSPL-1.0`

Dual-licensed packages are allowed only when the permissive license option is explicitly documented.

Local command:

```bash
pnpm audit:ci
```

