# Contract Freshness Lanes

Fabric_4L uses two contract-freshness lanes so that PRs and release
candidates can pick the right level of validation without paying for a full
stack when it is not needed.

## Fast hermetic lane

Goal: validate the shapes and bindings that can be checked from committed
source alone.

- Does **not** require live services, databases, or the full layer stack.
- Exports only the API gateway OpenAPI spec (`contracts/openapi/fabric-4l-api.json`).
- Runs static contract shape checks:
  - `scripts/ci/contract_compliance_gate.py --mode fast`
  - `scripts/ci/check_l1_target_schema.py`
  - `scripts/ci/check_targets_stats_named_schema.py`
  - `scripts/ci/check_generated_jsonvalue_absent.py`
  - `scripts/ci/check_clerk_tenant_response_exported.py`
  - `scripts/ci/check_clerk_tenant_mapping_contract.py`

Run locally:

```bash
make contract-freshness-fast
```

Use in PR workflows and fast gate-engineering validation.

## Full release lane

Goal: guarantee that the committed OpenAPI source-of-truth files and
frontend generated DTOs are deterministic outputs of the current backend
sources.

- Requires the full layer stack (or a CI runner that can start it) so that
  every layer can export its OpenAPI spec.
- Regenerates frontend generated types (`pnpm run generate:api`).
- Fails if any tracked OpenAPI contract or generated type diff remains.

Run locally when the full stack is up:

```bash
make contract-freshness
```

Use in release-mode gate engineering and production-readiness gates.

## Release-mode gate behavior

The release-mode gate report uses the full lane. When the full stack is
unavailable, the relevant contract/export gates remain **INCONCLUSIVE** and
block release. Fast-mode reports are never release-eligible.

## CI wiring

- `.github/workflows/generated-api-freshness.yml` runs the fast lane on PRs.
- `.github/workflows/prod-readiness.yml` runs the full lane through the
  gate-engineering evidence producer.
