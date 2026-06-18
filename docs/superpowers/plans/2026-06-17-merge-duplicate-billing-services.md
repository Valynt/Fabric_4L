# Sub-plan A: Merge Duplicate Billing Services (#2)

**Goal:** Reduce the two billing codebases (`services/billing/` and `services/layer7-billing/`) to a single canonical service without losing endpoints, tests, or behavior.

**Canonical path decision rule**
Prefer `services/billing/` if it is the public/older path referenced by runbooks and ADR-023. Prefer `services/layer7-billing/` only if the platform is standardizing on `layerN-*` service names. The default recommendation is `services/billing/` because ADR-023 and existing callers reference it.

**Files to inspect / modify**
- `services/billing/pyproject.toml`
- `services/layer7-billing/pyproject.toml`
- `services/billing/src/billing/`
- `services/layer7-billing/src/layer7_billing/`
- `services/billing/tests/`
- `services/layer7-billing/tests/`
- `services/layer4-agents/src/layer4_agents/services/billing_service.py`
- `services/layer4-agents/tests/test_billing_service.py`
- Root `package.json`, `Makefile`, Docker Compose files, CI workflows referencing the deleted service.

**Approach**
1. Diff the two source trees and reconcile any divergent files into the canonical service.
2. Merge test suites; delete duplicate tests and preserve the union of coverage.
3. Update imports throughout the repo from the deleted namespace to the canonical namespace.
4. Delete the non-canonical service directory.
5. Update CI, compose, and Makefile references.

**Validation**
- `pytest services/<canonical>/tests` passes.
- `grep -R '<deleted-namespace>' --include='*.py' --include='*.yml' --include='*.yaml' --include='*.json' .` returns no references (except this plan).
- `make lint-layer*` for affected layers passes.
- `make verify-structure` passes.

**Rollback**
Keep the deleted service in git history. If a rollback is needed, restore the directory and revert import changes.

**Risks**
- Divergent business logic between the two services could be silently dropped.
- CI paths may reference the deleted directory and fail until updated.
