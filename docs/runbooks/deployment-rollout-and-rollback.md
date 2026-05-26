# Deployment Rollout, Canary/Blue-Green Criteria, and Rollback

## Scope

This runbook applies to Kubernetes deployments under `k8s/base/`, `k8s/blue-green/`, and the CI/CD ephemeral deployment stage that:

1. Runs preflight checks.
2. Applies rendered manifests to an ephemeral Kubernetes cluster.
3. Executes post-deploy smoke checks for Layer 1–Layer 5 and the frontend.

---

## Blue-Green Operator Procedure (Required)

1. **Deploy green stack (no traffic yet)**
   - `kubectl apply -k k8s/blue-green/overlays/green`
   - Keep `Service/layer4-agents-active` selector on `track=blue`.
2. **Verify green health gates**
   - Run readiness/latency/error gate:
     - `python scripts/ci/blue_green_health_gate.py --health-url <green-health-url> --metrics-url <green-metrics-url> --max-error-rate 0.02 --max-p95-latency-ms 1200`
   - Gate must pass before traffic shift.
3. **Shift traffic (controlled switch)**
   - `kubectl apply -k k8s/blue-green/overlays/green` (service selector changes to `track=green`).
4. **Observe post-cutover window**
   - Observe for at least 15 minutes.
   - Rollback triggers:
     - readiness false for >60s
     - error rate >2% for 5 minutes
     - p95 latency >1200ms for 5 minutes
5. **Rollback criteria and command**
   - If any trigger breaches threshold and does not self-recover in 5 minutes:
     - `kubectl apply -k k8s/blue-green/overlays/blue`
   - Confirm health gate against blue before closing incident.

---

## Chaos Smoke Gate (Informational -> Required)

- Current non-blocking workflow: `.github/workflows/chaos-smoke.yml` job `chaos-smoke-informational`.
- Command: `scripts/ci/run_chaos_smoke.sh`.
- Includes minimal repeatable scenarios:
  - Redis outage behavior on Layer 1 job submission.
  - Database latency spike behavior on Layer 2 extraction.
  - Downstream Layer 3 timeout impact on Layer 4 approval policy path.
- Promotion plan:
  1. Track flakes for two consecutive weeks.
  2. Remove `continue-on-error: true`.
  3. Add `chaos-smoke-informational` as required in branch protection policy.

---

## Standard Rollback Procedure

If smoke checks fail or production SLOs regress:

1. **Freeze rollout**
   - Pause automation and stop additional promotions.
2. **Identify failing component**
   - Check deployment status and pod events.
   - Check readiness probe failures and error-rate dashboards.
3. **Rollback**
   - For a `Deployment`: `kubectl rollout undo deployment/<name> -n value-fabric`
   - For blue-green: switch traffic back to previous service selector (`track=blue` or `track=green`).
4. **Verify**
   - Wait for rollout completion.
   - Re-run smoke checks for L1–L5 and frontend.
5. **Escalate if persistent**
   - Follow service-specific runbook in this folder.
   - Open incident and include root cause plus corrective action.
