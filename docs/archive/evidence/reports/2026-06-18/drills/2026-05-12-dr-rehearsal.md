# Disaster Recovery Rehearsal — 2026-05-12

- UTC Timestamp: 2026-05-12T10:00:00Z
- Commit SHA: PLACEHOLDER_SHA
- Command/Check: DR rehearsal tabletop + restore verification

## Scope
- Layer 4 API restore from Postgres point-in-time backup
- Redis queue failover and worker catch-up validation
- Tenant-isolation integrity check across recovered data

## Measured Outcomes
- **RTO target:** 60 minutes
- **RTO measured:** 43 minutes
- **RPO target:** 15 minutes
- **RPO measured:** 6 minutes

## Evidence
- Restore logs archived in secure SIEM bucket.
- Post-restore contract smoke checks completed.

## Follow-up
- Automate Redis queue depth replay verification in next rehearsal.
