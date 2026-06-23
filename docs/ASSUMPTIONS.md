# Assumptions — Enterprise Release Candidate

This document records consequential inferred decisions made while working autonomously toward the release candidate.

## 1. Scope of "release candidate"

- We are transforming the existing product, not replacing it. Greenfield rewrites are avoided unless explicitly required for security or correctness.
- The release candidate is the current `main` branch plus fixes for release-blocking issues, not a new major version.
- External dependencies (Clerk, OpenAI, Stripe, etc.) continue to be used as configured; we do not invent credentials or accounts.

## 2. Infrastructure and credentials

- Local development and validation use Docker Compose and the documented `.env.example` workflow.
- No production deployment, DNS changes, cloud resource modifications, or real customer communications are performed.
- Missing third-party credentials are addressed by local emulators, contract tests, or test doubles; activation steps are documented but not executed.

## 3. Code quality gates

- The canonical CI gates are `make lint`, `make typecheck`, `make contract-tests`, and `pnpm --dir apps/web run test` (plus the backend-integrated suites).
- `make verify` is the final gate. The Definition of Done is not met until all gates pass.
- The IDE's pyright warnings are noted but not treated as CI blockers unless they correspond to `make typecheck` errors.

## 4. Security and compliance

- We build technical readiness (hardening, tests, documentation) but do not claim legal certification (SOC 2, ISO 27001, HIPAA, PCI DSS, GDPR).
- Cryptography, authentication protocols, and payment processing are implemented through maintained libraries/providers; no custom protocols are built from scratch.

## 5. Documentation

- Internal engineering docs live in `/docs`.
- User-facing public docs live in `docs-site/` per the existing canonical decision.

## 6. Risk acceptance

- Some tests are skipped in the baseline. Skipped tests are treated as P1/P2 gaps unless they explicitly cover a security boundary.
- Dependency audit findings are triaged for exploitability; not every warning is release-blocking.

## 7. Changelog

- 2026-06-18: Initial assumptions captured.
