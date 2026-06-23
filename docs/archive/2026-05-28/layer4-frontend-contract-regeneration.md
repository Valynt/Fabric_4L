# Layer 4 Frontend Contract Regeneration and CI Drift Gate

## Purpose

Layer 4 API contract drift can break frontend payload parsing even when backend and frontend both pass isolated tests. This workflow keeps generated frontend contract artifacts aligned to the canonical Layer 4 OpenAPI source of truth.

- Canonical backend contract: `contracts/openapi/layer4-agents.json`
- Generated frontend artifacts checked by CI:
  - `apps/web/src/api/generated/`
  - `apps/web/src/types/`
- Compatibility contract test: `tests/contract/test_l4_frontend_contract.py`

## CI gate

GitHub Actions workflow: `.github/workflows/l4-frontend-contract-sync.yml`.

The workflow performs three checks:

1. Regenerates frontend client/types from Layer 4 OpenAPI using:

   ```bash
   pnpm --dir apps/web run generate:types
   ```

2. Fails if regeneration changes committed generated artifacts under `apps/web/src/api/generated` or `apps/web/src/types`.

3. Runs targeted contract tests:

   ```bash
   pytest tests/contract/test_l4_frontend_contract.py
   ```

## Local regeneration workflow

From repository root:

```bash
corepack enable
corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile
pnpm --dir apps/web run generate:types
```

Then validate generated output is committed:

```bash
git diff -- apps/web/src/api/generated apps/web/src/types
```

Optional parity check with CI scope:

```bash
pytest tests/contract/test_l4_frontend_contract.py
```

## Failure remediation

### If drift check fails (generated files changed)

#### Backend owner actions

1. Confirm `contracts/openapi/layer4-agents.json` matches runtime route behavior.
2. If backend route/schema changed, regenerate/export canonical contracts as needed (for example via `python scripts/export_openapi.py`) and commit that contract update.
3. Communicate schema-impacting changes to frontend owners before merge.

#### Frontend owner actions

1. Regenerate artifacts with `pnpm --dir apps/web run generate:types`.
2. Commit updated files under `apps/web/src/api/generated` and `apps/web/src/types`.
3. Resolve TypeScript compile errors or mapper drift caused by schema updates.
4. Re-run `pytest tests/contract/test_l4_frontend_contract.py` to confirm payload compatibility.

### If `test_l4_frontend_contract.py` fails

#### Backend owner actions

- Verify response payload shapes, monitored route paths, and schema component names still match contract expectations.
- If payload shape intentionally changed, update OpenAPI contract and coordinate corresponding frontend mapper/type updates.

#### Frontend owner actions

- Update frontend contract consumers to align with regenerated types.
- Avoid hand-editing generated files; apply changes via source contracts and generator.

## Ownership and review expectations

- Backend reviewers must block merges where Layer 4 runtime behavior and `contracts/openapi/layer4-agents.json` diverge.
- Frontend reviewers must block merges where generated artifacts are stale or contract tests fail.
- Both owners should treat this as a contract-first drift prevention gate, not a formatting check.
