# Launch Runbook

This runbook coordinates the production launch window for Value Fabric. It is a launch control document, not a replacement for service-level rollback, incident, or monitoring runbooks.

## Compose File Use

| Compose file | When used | Operator | Evidence to retain |
|---|---|---|---|
| `docker-compose.monitoring.yml` | T-7d through T+7d for launch-environment monitoring, dashboard, and alert receiver validation. Start before production services so baseline telemetry exists before deploy. | SRE on-call | Compose transcript, Alertmanager receiver proof, dashboard screenshots, alert smoke output. |
| `docker-compose.blue-green.yml` | T-1d rehearsal and T-0 traffic shift when blue/green cutover is selected for the release candidate. Start it with explicit `BLUE_UPSTREAM`, `GREEN_UPSTREAM`, and `ACTIVE_COLOR`; keep the inactive color available until rollback risk is accepted as closed. | Release engineer with SRE on-call | Active color before and after cutover, health checks for both colors, traffic-switch transcript. |
| `docker-compose.prod.yml` | T-0 production deployment when the release owner approves launch. Use only after monitoring is live and rollback owner is present. | Release engineer | Rendered environment summary, service health output, release candidate SHA, operator sign-off. |

If any of these launch compose entrypoints is missing from the release branch, classify it as a P1 launch blocker unless the launch owner explicitly approves an equivalent documented deployment path.

## Rollback Triggers

Rollback authority comes from observable production signals. Use [Error Monitoring](ERROR_MONITORING.md), [Deployment rollback procedure](troubleshooting/runbooks/infrastructure/deployment-rollback.md), and monitoring configs under [monitoring](../monitoring/) as the source of truth for signal collection.

| Signal | Rollback trigger | Evidence source | First responder |
|---|---|---|---|
| Health endpoint | Any launched layer fails its health endpoint for more than 60 seconds, or the frontend cannot serve the primary route after cutover. | Service health checks, deployment logs, [deployment rollback procedure](troubleshooting/runbooks/infrastructure/deployment-rollback.md) | SRE on-call |
| Error rate | 5xx rate exceeds 5% for 2 minutes during T-0, or the `HighErrorRate` critical alert fires. | [production alert rules](../monitoring/alerting/rules-production.yml), Grafana operational dashboard | SRE on-call |
| Latency | p95 latency exceeds the approved SLO target by more than 50% for 5 minutes after cutover. | [SLO dashboard](../monitoring/grafana/dashboards/slo-detailed.json), Prometheus query output | Service owner |
| Memory and restarts | CrashLoopBackOff, repeated container restarts, or memory pressure appears on any launch-critical service. | [production alert rules](../monitoring/alerting/rules-production.yml), Kubernetes or compose service logs | SRE on-call |
| Data integrity | Any confirmed cross-tenant exposure, missing tenant scoping, corrupted persisted state, or irreversible migration issue. | Incident report, audit logs, service-owner validation | Launch owner |
| Observability loss | Monitoring, Alertmanager routing, or dashboard access fails during T-0 and cannot be restored within 10 minutes. | [Error Monitoring](ERROR_MONITORING.md), Alertmanager config, dashboard access proof | SRE on-call |

When a rollback trigger is met, stop promotion, announce the incident, preserve logs before restart, execute the approved rollback path, and confirm recovery for at least 5 minutes before closing the launch window.

## Communications Matrix

| Role | Launch responsibility | Rollback authority | Update cadence |
|---|---|---|---|
| Launch owner | Final go/no-go decision, launch-scope acceptance, stakeholder escalation. | Approves rollback for data integrity, security, or customer-impacting incidents. | T-7d readiness note, T-1d go/no-go, T-0 start and completion, T+1d summary, T+7d closeout. |
| Release engineer | Runs compose deployment commands, records release candidate SHA, captures terminal evidence. | Recommends rollback when deploy or cutover commands fail. | Every phase transition and every 15 minutes during T-0. |
| SRE on-call | Owns monitoring, health checks, alert routing, and rollback execution. | May initiate immediate rollback for availability or observability loss. | Every 15 minutes during T-0, immediate update on alert or trigger. |
| Service owner | Validates affected layer behavior, tenant safety, and contract health. | Approves service-specific rollback or forward-fix recommendation. | At phase handoff and on any service-specific alert. |
| Security/governance owner | Reviews secrets, auditability, tenant isolation, and incident classification. | Can block launch or require rollback for security exposure. | T-1d sign-off, T-0 go/no-go, immediate update on security signal. |
| Stakeholder comms owner | Sends customer/internal status updates using approved language. | Does not approve rollback; communicates decisions from launch owner. | T-0 start, material incident updates every 30 minutes, completion notice. |

## T-7d Readiness

Goal: confirm the release candidate can enter launch preparation without unresolved P0 blockers.

- Confirm the launch scope, release candidate branch, and target commit SHA.
- Confirm `docker-compose.monitoring.yml`, `docker-compose.blue-green.yml`, and `docker-compose.prod.yml` are present or formally waived with an equivalent deployment path.
- Run repository-owned launch gate checks listed in [final-testing launch checklist](launch/final-testing-launch-checklist.md).
- Review [launch blocker register](launch/launch-blocker-register.md) and assign every open P1/P2 item.
- Start monitoring rehearsal with `docker-compose.monitoring.yml` in the launch-like environment.
- Confirm alert receiver routing against [production Alertmanager config](../monitoring/alertmanager/alertmanager-production.yml).
- Create the launch evidence bundle folder and assign an evidence owner.

Exit criteria: no open P0 launch blockers, every open P1 has owner and mitigation, monitoring rehearsal evidence is attached, and launch owner accepts remaining risk.

## T-1d Go/No-Go

Goal: freeze launch inputs and prove rollback readiness before production traffic is touched.

- Re-run final repository launch checks and attach outputs to the evidence bundle.
- Rehearse blue/green cutover with `docker-compose.blue-green.yml` if that is the selected deployment mode, using explicit blue and green upstream URLs.
- Confirm `docker-compose.prod.yml` can render with secure environment injection and without committing secrets.
- Confirm rollback owner, backup owner, and stakeholder comms owner are available for the full T-0 window.
- Review rollback triggers and confirm thresholds in [Error Monitoring](ERROR_MONITORING.md).
- Snapshot dashboards, alert receiver status, and service health baselines.
- Confirm migration rollback or forward-fix notes for any persistence changes.
- Execute the critical-path L1→L6 E2E smoke against the live stack and attach the artifact to the evidence bundle:

  ```bash
  docker compose -f docker-compose.live.yml up -d
  docker compose -f docker-compose.live.yml exec layer4 \
      python /app/scripts/e2e/critical_path_smoke.py --network
  ```

  The script writes a timestamped JSON artifact to `signoff-evidence/e2e/`. Commit the artifact and reference it in `docs/readiness/launch-decision-artifact.md` §1a row "Live stack run". Exit code 0 is required; any failure blocks T-0.

Exit criteria: launch owner records go/no-go decision, rollback owner confirms readiness, stakeholder update cadence is scheduled, critical-path E2E artifact is committed, and all launch-critical evidence gaps are closed or explicitly accepted.

## T-0 Launch

Goal: deploy, shift traffic, and monitor until the release is stable or rolled back.

1. Announce launch start with release candidate SHA, operator, on-call owner, and rollback approver.
2. Start or verify monitoring with `docker-compose.monitoring.yml`.
3. Deploy production services with `docker-compose.prod.yml`.
4. If using blue/green, validate inactive color health, shift traffic with `docker-compose.blue-green.yml` by changing `ACTIVE_COLOR`, and retain the previous color for rollback.
5. Check health endpoints for frontend and all launch-critical layers.
6. Watch error rate, latency, memory, restart, and alert-routing signals for at least 30 minutes.
7. Trigger rollback immediately if any rollback signal crosses threshold and cannot be cleared within the defined window.
8. Announce launch completion only after health, error rate, latency, and memory signals remain stable.

Evidence required: command transcript, release candidate SHA, health checks, dashboard screenshots, alert status, incident notes if any, and launch owner sign-off.

## T+1d Stabilization

Goal: verify the release remains healthy through normal usage patterns.

- Review overnight alerts, error rates, latency, memory pressure, and restart counts.
- Compare launch dashboards against pre-launch baseline.
- Confirm no cross-tenant, contract, or workflow drift reports were opened.
- Review support tickets and customer-impact notes.
- Keep rollback path available unless launch owner accepts that rollback window is closed.
- Publish T+1d stakeholder summary with open risks and owners.

Exit criteria: no unresolved launch-critical alerts, no unowned support escalations, and launch owner accepts current stability posture.

## T+7d Closeout

Goal: close audit evidence, retain operational learning, and transition from launch mode to steady state.

- Complete the launch evidence bundle checklist.
- Attach incident records, rollback decisions, or explicit no-rollback confirmation.
- Review alert tuning and update [Error Monitoring](ERROR_MONITORING.md) if launch revealed monitoring gaps.
- Close or reclassify launch blockers in [launch blocker register](launch/launch-blocker-register.md).
- Record follow-up work in the appropriate backlog with owners and dates.
- Publish closeout summary to stakeholders.

Exit criteria: evidence bundle is complete, sign-offs are retained, unresolved items have owners, and launch owner closes launch mode.

## Launch Evidence Bundle Checklist

| Evidence item | Required contents | Owner |
|---|---|---|
| Release identity | Commit SHA, image digests or service versions, release branch, launch window timestamp. | Release engineer |
| Compose transcripts | Commands and outputs for `docker-compose.monitoring.yml`, `docker-compose.blue-green.yml`, and `docker-compose.prod.yml` or approved equivalent path. | Release engineer |
| Health evidence | Health endpoint outputs before deploy, after deploy, after traffic shift, and after stabilization. | SRE on-call |
| Monitoring evidence | Grafana dashboard snapshots, Prometheus/alert outputs, Alertmanager receiver proof, latency and error-rate snapshots. | SRE on-call |
| Checklist snapshots | Final-testing checklist, launch blocker register, environment-dependent evidence matrix if used. | Launch owner |
| Rollback record | Trigger status, rollback decision, approver, transcript if executed, and recovery confirmation. | Launch owner |
| Incident records | Incident channel export, timeline, customer impact, owner, and follow-up action list. | SRE on-call |
| Sign-offs | Launch owner, rollback approver, SRE on-call, service owner, security/governance owner. | Launch owner |

Retain the bundle with the release record. Do not store secrets, raw tokens, private keys, or unredacted customer data in evidence artifacts.
