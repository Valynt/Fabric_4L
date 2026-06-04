# Operations

This directory contains concise operator workflows for production readiness.

## Incident Response

- [Incident response workflow](incident/README.md)
- [Severity matrix](incident/severity_matrix.md)
- [Escalation policy](incident/escalation_policy.md)
- [Customer communications template](incident/customer_comms_template.md)
- [Postmortem template](incident/postmortem_template.md)

Use `ops/incident/` as the first stop during production incidents. The broader
runbook inventory remains under `docs/runbooks/` and is linked from each
incident workflow where deeper service-specific procedures are needed.

## Validation

```bash
pnpm ops:runbooks:lint
pnpm ops:incident:check
```
