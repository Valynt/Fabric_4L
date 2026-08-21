# Operational Runbook Scripts

These scripts were previously located in `scripts/smoke/`, `tests/penetration/`, and
`tests/chaos/`. They are **not automated gate tests**. They are standalone scripts that
require live infrastructure (running services, ZAP proxy, Nikto, etc.) and are intended
for manual operational use during incident response, load testing, or penetration
testing engagements.

They were moved here during the gate system consolidation (Sprint 3) to prevent them
from being mistaken for CI-runnable gate tests.

## Scripts

| Script | Purpose | Requirements |
|--------|---------|-------------|
| `production_smoke.py` | Hit HTTP health endpoints on a running deployment | Running services |
| `clustersecretstore_check.py` | Validate ClusterSecretStore configuration | Kubernetes cluster |
| `vault_smoke.py` | Validate HashiCorp Vault connectivity | Running Vault instance |

## Runbooks

| Runbook | Purpose |
|--------|---------|
| `abuse-emergency-controls.md` | Emergency controls for abuse spikes, blocklists, replay response, and temporary stricter limits |
| `alerting-source-of-truth.md` | Canonical Alertmanager/alert-rule edit paths per environment and CI governance |
| `governance-gates-troubleshooting.md` | Ownership and troubleshooting for PR/merge governance automation (operational debt, PR size, branch protection, contract-drift, mypy ratchet) |
