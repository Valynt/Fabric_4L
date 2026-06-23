# Cloud Provider Outage Runbook

Use this runbook when AWS, GCP, Azure, DNS, CDN, managed database, managed Kubernetes, identity, or regional cloud services have a confirmed or suspected outage affecting Value Fabric. Classify severity from customer impact; regional production outage is usually **SEV1**.

## Triggers

- Cloud provider status page reports regional or service-level degradation.
- Multiple unrelated services in the same region fail simultaneously.
- Kubernetes nodes, managed databases, queues, object storage, load balancers, or identity services become unavailable.
- Synthetic checks fail from multiple locations while application deploy state is unchanged.
- Network, DNS, TLS, or CDN errors spike across tenants.

## Immediate response

1. **Classify severity** using [severity-classification.md](severity-classification.md); declare SEV1 for complete production region outage.
2. **Assign roles:** Incident Commander, Infrastructure Lead, Application Lead, Communications Lead, and cloud-provider liaison.
3. **Confirm blast radius:** identify affected region, account/subscription/project, services, tenants, and layers.
4. **Stop risky automation:** pause deploys, migrations, large batch jobs, and scaling actions that depend on unstable provider APIs.
5. **Check provider status and support cases:** capture screenshots or status links in the evidence log.
6. **Prepare failover decision:** compare impact to RTO/RPO in [backup-disaster-recovery.md](backup-disaster-recovery.md) and region-loss procedures in [dr-gameday-region-loss.md](dr-gameday-region-loss.md).

## Diagnosis

```bash
# Check cluster and node health.
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp | tail -200

# Check ingress and service endpoints.
kubectl get ingress,svc,endpoints -A

# Review failing probes and affected namespaces.
kubectl get pods -A --field-selector=status.phase!=Running

# Compare with provider status pages and support notices outside the cluster.
```

## Decision matrix

| Condition | Action |
|---|---|
| Single managed service degraded with workaround | Keep primary region, mitigate locally, communicate SEV2/SEV3 impact. |
| Complete regional control-plane outage but data plane healthy | Freeze deploys and node changes; monitor; prepare failover but avoid unnecessary restart. |
| Complete regional data-plane outage | Execute regional failover if RTO/RPO risk exceeds failover risk. |
| Identity provider or DNS outage | Use approved break-glass path, cached credentials, or DNS failover if available. |
| Object storage or backup service outage | Pause destructive data operations; verify backup replication before recovery actions. |

## Regional failover checklist

1. Confirm failover authority with Incident Commander and Infrastructure Lead.
2. Verify latest replicated database, object storage, queue, and configuration state in target region.
3. Estimate RPO and customer-visible data gap.
4. Disable writers in the impaired region if reachable.
5. Promote target-region data stores according to service runbooks.
6. Update DNS/load balancer/CDN routing with low TTL.
7. Scale target-region services and run smoke tests for API, web, L1-L6, auth, and tenant isolation.
8. Announce status page update and support guidance.
9. Keep impaired region isolated until reconciliation plan is approved.

## Recovery back to primary

- Do not fail back automatically.
- Wait for provider recovery confirmation and stable monitoring.
- Reconcile data differences and queue backlogs.
- Run read-only validation before enabling writes.
- Schedule failback during an approved window unless current region risk requires immediate action.

## Communication

- Use [communication-template.md](communication-template.md).
- Include affected product areas and customer symptoms, not internal cloud-provider speculation.
- If provider status page is public, link it only when it helps customers understand third-party dependency impact.
- Maintain update cadence from [severity-classification.md](severity-classification.md).

## Closure criteria

- Services are stable in the active region.
- RPO/RTO impact is measured and documented.
- Queues, workflows, and tenant-scoped data are reconciled.
- Provider support case and timeline are attached to the incident record.
- Follow-up actions cover resilience, alerting, and game-day updates.
