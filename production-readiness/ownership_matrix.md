# Production Readiness Ownership Matrix

| Area | Primary owner | Backup owner | Accountable reviewer | Escalation path | Validation command |
|---|---|---|---|---|---|
| Security | Security Engineering | Platform Security | Security Lead | Incident commander for launch-blocking security regressions | `pnpm test:security` |
| Reliability | Platform Engineering | Layer Service Owners | Platform Lead | Release manager for failed golden path or smoke evidence | `pnpm test:queues` |
| Observability | SRE | Platform Engineering | SRE Lead | On-call lead for missing alert or dashboard evidence | `pnpm test:observability` |
| DR | SRE | Data Platform | SRE Lead | Incident commander for failed restore or rollback drill | `pnpm ops:backup:verify` |
| Release Safety | Release Engineering | Platform Engineering | Release Manager | Change advisory reviewer for production deploy approval | `pnpm release:dry-run` |
| Billing | Product Engineering | Finance Operations | Product Lead | Paid launch owner for billing evidence gaps | `python scripts/ci/generate_billing_evidence.py --help` |
| Tenancy | Platform Security | Backend Service Owners | Security Lead | Launch blocker escalation for any tenant isolation failure | `pnpm test:isolation` |
| Data Lifecycle | Data Platform | SRE | Data Lead | Data governance owner for retention, migration, backup, or deletion gaps | `pnpm db:migrate:check` |
| Compliance Evidence | Compliance Owner | Security Engineering | Compliance Lead | Executive launch reviewer for control evidence gaps | `python scripts/ci/validate_production_readiness_plan.py` |
