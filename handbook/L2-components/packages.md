# L2 Component — packages

## Purpose

Shared libraries (`packages/`). Common code consumed by services and the frontend. Commodity,
non-differentiating capability lives here behind stable interfaces; product-differentiating
behavior (hypothesis → driver → formula → case journey) lives in the services.

## Owned journey stages / behaviors

Cross-cutting — no single behavior owner; supports all BEH-01..BEH-09.

## Key verified paths

- `packages/shared/` — shared code: `src/`, `tests/`, `AGENTS.md`, `README.md`
- `packages/platform-contract/` — platform contract enforcement: `CONTRACT.md`, `schemas/`,
  `scripts/`, `src/`
- `packages/feature-flags/` — `src/`
- `packages/config/` — `src/`
- `packages/eslint-plugin-fabric-contracts/` — contract lint rules (contents not expanded)

## Dependencies

- Consumed by `apps/web` and `services/*`. Packages MUST NOT depend on services or apps
  (dependency direction: apps/services → packages).
- `packages/platform-contract/` ties into `contracts/` schemas.

## Primary gates

- **AG-01** repository-integrity — lockfile consistency, canonical configuration enforcement.
- **AG-02** code-quality-and-tests — package unit tests, type checking.
- **AG-07** supply-chain-integrity — dependency locking, SBOM inclusion for consumers.
