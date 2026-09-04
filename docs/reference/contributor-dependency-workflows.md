# Contributor Dependency Workflows Reference

This reference maps the approved dependency workflows across the monorepo and explains the lockfile guardrails enforced in pre-commit and CI.

## JavaScript / TypeScript workspaces (pnpm only)

Use **pnpm** for all workspace package management.
Use `apps/web/` as the only valid frontend source/config root.

### Canonical commands

```bash
corepack enable
corepack prepare pnpm@10.34.5 --activate
pnpm install --frozen-lockfile
pnpm --dir apps/web install --frozen-lockfile
```

### Prohibited commands

Do not run `npm install`, `npm ci`, or `yarn install` in this repository.

### Canonical lockfiles

- `pnpm-lock.yaml` (repo root)
- `apps/web/pnpm-lock.yaml`

### pnpm override rollback plan

When a root `package.json` `pnpm.overrides` entry is no longer needed:

1. Confirm the upstream dependency graph no longer resolves the vulnerable or incompatible version.
2. Remove only the resolved override entry from the root `package.json`.
3. Run `corepack pnpm install --lockfile-only`.
4. Review `pnpm-lock.yaml` and confirm the expected dependency graph changed, with no unrelated churn.
5. Run `corepack pnpm install --frozen-lockfile`, `pnpm run check:package-manager-policy`, and `pnpm audit:ci`.

If validation fails, restore the override and lockfile hunk, then capture the failing package and version evidence in the dependency review issue.

## Python services (uv + service-local tooling)

Each maintained Python service follows a service-local dependency boundary. Use `uv` with service-local `pyproject.toml` / `uv.lock` as the source of truth.

### Canonical lockfiles

- `services/layer1-ingestion/uv.lock`
- `services/layer2-extraction/uv.lock`
- `services/layer3-knowledge/uv.lock`
- `services/layer4-agents/uv.lock`
- `services/layer5-ground-truth/uv.lock`
- `services/layer6-benchmarks/uv.lock`

### Recommended workflow pattern

```bash
cd services/<layer-service>
uv sync
uv lock
```

Use service-specific tooling (for example, `pytest`, layer Make targets, or service scripts) after syncing dependencies.

## Guardrails: lockfile policy enforcement

Lockfile policies are enforced by `scripts/ci/check_package_manager_policy.mjs`.

The guard rejects:

1. Any changed `package-lock.json` or `yarn.lock` file.
2. Any changed `pnpm-lock.yaml` or `uv.lock` outside approved paths.

Approved lockfile churn paths are intentionally narrow to prevent accidental cross-workspace dependency drift.

## Where the guard runs

- **CI**: `pnpm run check:package-manager-policy`
- **pre-commit**: local hook `package-manager-and-lockfile-policy`

## Frontend root governance guard

CI rejects pull requests that add non-documentation files under `frontend/`.

- Canonical frontend root: `apps/web/`
- Legacy path (`frontend/`) is doc-only and migration metadata only
- Allowed under `frontend/`:
  - Markdown docs (including archive/doc-only content)

For migration context, see `docs/reference/frontend-root-policy.md`.

Guard entrypoint:

```bash
python scripts/ci/check_frontend_root_policy.py --base-ref origin/main
```
