# Audit Evidence Snapshots

This directory stores machine-readable periodic evidence snapshots for compliance controls.

## Artifact format

- `snapshots/latest.json`: most recent generated snapshot.
- `snapshots/audit-snapshot-<timestamp>.json`: immutable timestamped snapshot.

Each snapshot includes:

- control/config checks
- policy state flags (GDPR + HIPAA conditional mode)
- command outputs and return codes for traceability

## Generation

Run locally:

```bash
python3 scripts/compliance/generate_audit_snapshot.py
```

CI automation is defined in `.github/workflows/audit-snapshot.yml` and runs on a weekly schedule plus manual dispatch.

> **Audit note (2026-07-18):** `.github/workflows/audit-snapshot.yml` does not currently exist. The snapshots are therefore manually generated; regenerate with `python3 scripts/compliance/generate_audit_snapshot.py` when needed.
