# Compliance Evidence Controls Mapping

## Purpose

This mapping connects generated evidence to internal Value Fabric policy sources and early audit readiness controls. It complements `docs/compliance/control-matrix.md` and `docs/compliance/evidence-inventory-matrix.md`.

| Control ID | Control Area | Internal Policy Source | Evidence Artifact | Owner | Cadence |
| --- | --- | --- | --- | --- | --- |
| C-AC-01 | Access control and tenant authentication | `docs/reference/compliance.md`, `docs/core-concepts/security-model.md` | `security-summary.json`, `access-review-record.md` | Security Engineering | Per PR + quarterly |
| C-TI-01 | Tenant isolation and least privilege | `docs/tenant-isolation.md`, `docs/reference/tenant-context-enforcement-pattern.md` | `test-summary.json`, tenant-boundary test outputs | Platform Engineering | Per PR |
| C-AU-01 | Immutable audit trail and change history | `docs/governance.md`, `docs/operations/RELEASE_RUNBOOK.md` | `release-metadata.json`, `change-management-record.md` | Security Engineering + SRE | Per release |
| C-SEC-03 | Secrets, dependency, and vendor risk governance | `docs/SUPPLY_CHAIN.md`, `docs/trust/vendor-risk-policy.md` | `security-summary.json`, `sbom-summary.json`, `vendor-review-record.md` | Security Engineering | Per PR + quarterly |
| C-RET-01 | Retention, backup, and recovery readiness | `docs/reliability/dr-policy.md`, `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md` | `backup-verification-summary.json` | SRE | Monthly + per drill |
| P1-FLAGS | Operational change and release control | `docs/governance/production-readiness-p1-operational-controls.md` | `release-metadata.json`, `change-management-record.md` | Platform Engineering | Per release |
| P2-SOC2 | SOC 2 and ISO readiness evidence package | `docs/compliance/evidence-inventory-matrix.md`, `docs/trust/control-matrix.v1.yaml` | `bundle-manifest.json`, all evidence summaries | Compliance Engineering | Quarterly |

## Evidence Requirements

Every generated evidence bundle must include:

- UTC timestamp and Git SHA.
- Generated summary for tests, security scans, SBOM, backup verification, and release metadata.
- Explicit evidence gaps for required sources that are unavailable.
- SHA-256 hashes for generated evidence files.
- A publication marker indicating the bundle must not be edited in place.
