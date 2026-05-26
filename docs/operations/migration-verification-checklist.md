# Migration verification checklist

Run from repository root:

```bash
scripts/verification/migration_verification_checklist.sh
```

## Expected output

- Step `[1/4]` prints:
  - `PASS: no legacy \`value-fabric/\` filesystem references found in active code/config.`
- Step `[2/4]` prints a `REPO HYGIENE REPORT` with `Status     : PASS`.
- Step `[3/4]` prints no matches for actionable code/config in `services/`, `scripts/`, and `tests/`.
- Step `[4/4]` prints:
  - `PASS: compatibility namespace imports resolve`

If any step fails, treat as migration regression and block merge until fixed.

## Layer 3 audited graph-write migration checklist item

- Confirm all direct Cypher relationship write operations (`CREATE`, `MERGE`, `DELETE`) in:
  - `services/layer3-knowledge/src/api/routes`
  - `services/layer3-knowledge/src/services`
  - `services/layer3-knowledge/src/agents`
  are routed through `value_fabric.layer3.db.audited_mutation.AuditedGraphMutation`.
- Run `python scripts/ci/check_layer3_audited_relationship_writes.py --report-json artifacts/layer3-audited-mutation-violations.json` and verify `summary.violations == 0`.
