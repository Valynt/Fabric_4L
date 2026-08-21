# Workspace (live task state)

## Current task

Infisical secret-path schema reconciliation — canonicalize all by-consumer
legacy paths to the by-layer taxonomy; add a CI regression guard; resolve
two follow-up drift items (CI wiring verification + undocumented paths).

## Status

Complete. Both commits landed on `bmsull560-reconcile-infisical-paths`:
- `cd9979475` canonicalize Infisical secret paths to by-layer taxonomy
- `9cbd48875` Resolve undocumented Infisical paths in .env.example

## What was done

Phase 1 (commit cd9979475):
- Stripped `secretPaths` from `.infisical.json`.
- Rewrote `scripts/push_secrets_to_infisical.py` to derive the variable->path
  map from `.env.example` annotations via `load_schema_from_example()`; deleted
  the redundant by-consumer `SECRET_SCHEMA`; default fallback `/shared`.
- Rewrote `scripts/security/setup_infisical_folders.py` `FOLDERS_TO_CREATE`
  to the 13 canonical by-layer paths.
- Rewrote `.devin/skills/infisical-windows-patterns.md` to by-layer; preserved
  the Windows Git Bash path-mangling fix (`MSYS_NO_PATHCONV=1`, `//` prefix,
  `fix_path_for_git_bash()`).
- Added `scripts/ci/check_infisical_path_schema.py` (marker-based path
  extraction) and wired it into the `structural-preflight` job in
  `.github/workflows/pr-checks.yml`.
- Added 16 tests (`tests/ci/test_check_infisical_path_schema.py` (9),
  `tests/ci/test_push_secrets_by_layer.py` (7)) — all green.

Phase 2 (commit 9cbd48875):
- Verified the CI guard wiring: the step is inside `structural-preflight`
  (line 179-180), which has no `if:`/`needs:` guard, so it runs
  unconditionally on every `pull_request`/`push` to `main` and `merge_group`.
  A planted `--path=/llm` in a temp tree makes the guard exit 1 -> job fails.
- Resolved the two undocumented `.env.example` paths `/api-gateway` and
  `/webhooks` -> `/shared/auth` (canonical sub-path already used for
  CLERK_ISSUER/AUTH_PROVIDER). Both groups are API-gateway auth-plane secrets
  consumed by services/api; production separation is at the Vault/k8s layer
  (value-fabric/auth, value-fabric/clerk), not Infisical.

## Findings (drift)

None outstanding. The schema is now single-source: `.env.example` is the
source of truth for variable->path mapping, the CI guard blocks regressions,
and `.env.example` contains only the 12 documented by-layer roots and their
`/shared/auth` sub-path.

## Active hypotheses / Next step

None. Task complete.
