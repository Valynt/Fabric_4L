# Layer 3 Cypher Runtime Security Inventory

This inventory classifies every runtime Cypher execution path in Layer 3 routes/services.

## Classification policy

- **Safe**: tenant constrained + parameterized + allowlisted dynamic fragments.
- **Unsafe**: missing one or more constraints.
- **Unknown**: requires manual review.

CI enforces this inventory via `scripts/check_layer3_cypher_scope.py` and fails on:

1. Any newly discovered runtime path missing from inventory (treated as `Unknown`).
2. Any path explicitly classified `unsafe` or `unknown`.
3. Any `safe` path missing:
   - inline marker (`strict-scoped-query-execution`) or approved safe execution wrapper, and
   - unit test evidence in inventory metadata.
4. Dynamic fragment mismatches (`target_label`, relationship types, sort clauses).

## Canonical inventory file

- `services/layer3-knowledge/security/layer3_cypher_runtime_inventory.json`

The JSON file is the machine-enforced source of truth used in tenancy/security PR gates.
