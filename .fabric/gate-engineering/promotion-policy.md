# Environment Promotion Policy

## Promotion path

`dev → staging → production`

No artifact may be promoted to an environment unless it has passed the gate profile assigned to that environment and all evidence is bound to the exact artifact digest.

## Environment profiles

| Environment | Required profile | Approval |
|---|---|---|
| dev | `pr-fast` | None (auto) |
| staging | `mainline-full` | None (auto after build success) |
| production | `release-candidate` | GitHub Environment protection rule + release manager approval |

## Required checks before promotion

The `environment-promotion.yml` workflow validates:

1. Build workflow succeeded.
2. Image digest is immutable (`sha-<40>` or semver release tag).
3. Required checks (`Unified Readiness Gate`, `Security Gates`, `Smoke Gate`) are `success` for the commit.
4. Promotion artifact contract is valid between `build-deploy.yml` and `environment-promotion.yml`.

## Production blockers

Production promotion is blocked unless:

- `prod-readiness.yml` produced a matching release packet.
- `deploy.yml` input `prod_readiness_verified` is `true`.
- All `release-candidate` blocking gates are green.
- No exceptions are expired.
- Rollback path is verified.

## Mutable tags

`:latest`, `:main`, `:staging`, `:production`, and similar mutable references are forbidden in all production-like overlays and deployment workflows.

## Rollback tie

A promotion record must include the previous production artifact digest so that rollback can be executed without image lookup.

## Evidence retention

Promotion metadata is retained in `artifacts/release/` and `artifacts/build-metadata/` for one year.
