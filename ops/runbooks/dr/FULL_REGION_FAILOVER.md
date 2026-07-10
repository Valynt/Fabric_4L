# Runbook: Full Region Failover

| Field | Value |
|---|---|
| **Runbook ID** | DR-REGION-001 |
| **Service** | Full Fabric_4L Stack (all 6 layers + data stores) |
| **Severity** | P0 - Emergency |
| **RTO** | 15 minutes |
| **RPO** | 5 minutes (async replication) |
| **Owner** | SRE On-Call → DR Coordinator |
| **Last Reviewed** | 2025-01-15 |
| **Version** | v1.2.0 |

---

## 1. Detection

### Alert Triggers

| Alert | Query/Condition | Severity |
|---|---|---|
| `RegionHealthCheckFailed` | Multi-region health check failure for 2m | P0 |
| `CrossRegionLatencySpike` | `probe_latency{region!="primary"} > 5000` for 3m | P1 |
| `DatabaseReplicationLagCrossRegion` | `pg_replication_lag_seconds{cross_region="true"} > 300` | P1 |
| `LoadBalancerErrorRate` | `lb_5xx_rate > 0.1` for 2m | P0 |
| `KubernetesNodeNotReady` | `> 50% nodes NotReady` in primary region | P0 |
| `CloudProviderOutage` | External cloud status page reports outage | P0 |

### Health Check Endpoints
| Region | Health URL |
|---|---|
| Primary (us-east-1) | `https://health.fabric4l.io/primary/health` |
| Standby (us-west-2) | `https://health.fabric4l.io/standby/health` |
| Global LB | `https://health.fabric4l.io/global/health` |

### Dashboard Links
- [Grafana - Multi-Region Overview](https://grafana.fabric4l.io/d/multi-region)
- [Grafana - Cross-Region Replication](https://grafana.fabric4l.io/d/cross-region-repl)
- [Status Page Admin](https://admin.statuspage.io/fabric4l)

### Verification Command
```bash
# Check both regions
curl -sf https://health.fabric4l.io/primary/health && echo "PRIMARY: OK" || echo "PRIMARY: FAIL"
curl -sf https://health.fabric4l.io/standby/health && echo "STANDBY: OK" || echo "STANDBY: FAIL"

# Check if it's a DNS or actual service issue
# From bastion in primary region:
kubectl -n fabric4l get nodes -o wide
# If nodes are NotReady, it's a region-wide issue
```

---

## 2. Impact Assessment

### Scenarios

| Scenario | Primary | Standby | Action |
|---|---|---|---|
| A: Primary region down | FAIL | OK | Activate standby |
| B: Both regions affected | FAIL | FAIL | Degraded mode, notify customers |
| C: Network partition | OK (locally) | OK (locally) | Split-brain risk, evaluate |
| D: Partial primary failure | DEGRADED | OK | May not need full failover |

### Immediate Impact (Scenario A)
- **All services in primary** are unreachable
- **Data replication** may have lag (RPO: 5 min max)
- **In-flight requests** are lost (no multi-region load balancing)
- **DNS** still points to primary region

### Escalation Matrix
| Time | Action |
|---|---|
| T+0 | P0 alert fires, DR Coordinator paged immediately |
| T+2 min | DR Coordinator convenes war room (Zoom + Slack) |
| T+5 min | Decision: failover or wait for recovery |
| T+10 min | If failover decision made, execution begins |
| T+15 min | Standby should be serving traffic |
| T+30 min | Post-failover review begins |

---

## 3. Prerequisites

- [ ] DR Coordinator identified and reachable
- [ ] Access to DNS provider (Route53 / Cloudflare)
- [ ] Access to standby region Kubernetes cluster
- [ ] Standby region verified healthy (pre-check)
- [ ] Database replication lag < 5 minutes (verified)
- [ ] Communication templates ready
- [ ] Customer notification list prepared

---

## 4. Step-by-Step Procedure

### Phase 1: Decision & Authorization (2 minutes)

**Step 1.1: DR Coordinator confirms scenario**
```bash
# Run verification script
./scripts/verify-region-failure.sh
# Output should clearly indicate primary region failure
```

**Step 1.2: Verify standby region health**
```bash
# Switch kubectl context to standby
kubectl config use-context fabric4l-standby

# Verify all nodes ready
kubectl get nodes
# Expected: All Ready

# Verify all pods running
kubectl -n fabric4l get pods
# Expected: All Running or Completed
```

**Step 1.3: Check replication lag**
```bash
# From standby, check how far behind it is
kubectl -n fabric4l exec postgres-standby-0 -- psql -U postgres -c \
  "SELECT pg_last_xact_replay_timestamp(), now(), \
   EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;"
# lag_seconds should be < 300 (5 minutes)

# If lag > 5 minutes, acknowledge potential data loss in communications
```

**Step 1.4: Make go/no-go decision**
| Factor | Go | No-Go |
|---|---|---|
| Standby healthy | Yes | No |
| Replication lag < 5 min | Yes | Evaluate |
| Cloud provider confirms outage | Yes | — |
| Estimated primary recovery < 15 min | Evaluate | Yes |
| Customer-facing P0 impact | Yes | — |

### Phase 2: Activate Standby Region (5 minutes)

**Step 2.1: Promote standby database to primary**
```bash
# On standby cluster
kubectl config use-context fabric4l-standby

# Promote PostgreSQL standby to primary
kubectl -n fabric4l exec postgres-standby-0 -- pg_ctl promote -D /var/lib/postgresql/data
# Or use Patroni:
kubectl -n fabric4l exec postgres-standby-0 -- patronictl failover --candidate postgres-standby-0 --force

# Verify writes work
kubectl -n fabric4l exec postgres-standby-0 -- psql -U postgres -c \
  "CREATE TABLE dr_test (id serial); INSERT INTO dr_test DEFAULT VALUES; SELECT * FROM dr_test;"
```

**Step 2.2: Activate standby Neo4j as independent cluster**
```bash
# Neo4j standby is read-only follower
# Promote to writable
kubectl -n fabric4l exec neo4j-standby-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.setDatabaseMode('neo4j', 'primary')"

# Verify
kubectl -n fabric4l exec neo4j-standby-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CREATE (t:Test {name: 'dr-failover', ts: datetime()}) RETURN t"
```

**Step 2.3: Scale up standby application deployments**
```bash
# Scale from 0 or reduced capacity to full capacity
kubectl -n fabric4l scale deployment/l1-ingestion --replicas=3
kubectl -n fabric4l scale deployment/l2-extraction --replicas=3
kubectl -n fabric4l scale deployment/l3-knowledge --replicas=3
kubectl -n fabric4l scale deployment/l4-agent --replicas=3
kubectl -n fabric4l scale deployment/l5-ground-truth --replicas=2
kubectl -n fabric4l scale deployment/l6-benchmark --replicas=1

# Wait for rollout
kubectl -n fabric4l rollout status deployment/l1-ingestion --timeout=120s
kubectl -n fabric4l rollout status deployment/l2-extraction --timeout=120s
kubectl -n fabric4l rollout status deployment/l3-knowledge --timeout=120s
kubectl -n fabric4l rollout status deployment/l4-agent --timeout=120s
```

**Step 2.4: Enable external traffic ingress**
```bash
# Ensure load balancer is provisioned
kubectl -n fabric4l get svc fabric4l-lb
# EXTERNAL-IP should be assigned

# Verify TLS certificates
kubectl -n fabric4l get certificates
# All should show Ready=True
```

### Phase 3: DNS Cutover (5 minutes)

**Step 3.1: Update DNS to point to standby**
```bash
# Using Route53 CLI
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.fabric4l.io",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$LB_HOSTED_ZONE_ID",
          "DNSName": "$STANDBY_LB_DNS",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# If using Cloudflare
# Update via Cloudflare API or dashboard
# Target: standby load balancer IP/hostname
```

**Step 3.2: Lower TTL on critical records**
```bash
# Temporarily reduce TTL for faster propagation
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.fabric4l.io",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [{"Value": "$STANDBY_LB_IP"}]
      }
    }]
  }'
```

**Step 3.3: Monitor DNS propagation**
```bash
# Check from multiple locations
for resolver in 8.8.8.8 1.1.1.1 9.9.9.9; do
  echo "=== $resolver ==="
  dig @$resolver api.fabric4l.io +short
done
# All should resolve to standby LB IP

# Global propagation check
dig api.fabric4l.io +short
# Should return standby LB IP, not primary
```

**Step 3.4: Update status page**
```bash
# Mark incident on status page
curl -X POST https://api.statuspage.io/v2/pages/$PAGE_ID/incidents \
  -H "Authorization: OAuth $STATUSPAGE_API_KEY" \
  -d '{
    "incident": {
      "name": "Primary Region Failover",
      "status": "investigating",
      "impact_override": "major",
      "components": {
        "component_id": "operational"
      }
    }
  }'
```

### Phase 4: Verify Traffic (3 minutes)

**Step 4.1: Health check all layers in standby**
```bash
# Verify all services respond
for endpoint in \
  https://api.fabric4l.io/l1/health \
  https://api.fabric4l.io/l2/health \
  https://api.fabric4l.io/l3/health \
  https://api.fabric4l.io/l4/health \
  https://api.fabric4l.io/l5/health \
  https://api.fabric4l.io/l6/health; do
  echo "=== $endpoint ==="
  curl -sf $endpoint | jq '.status' || echo "FAIL"
done
```

**Step 4.2: End-to-end ingestion test**
```bash
# Test full pipeline
curl -X POST https://api.fabric4l.io/v1/ingest \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "dr-verification",
    "content": "Full region failover test at '$(date -Iseconds)'",
    "source": "dr-runbook"
  }'
# Expected: 201 Created
```

**Step 4.3: Verify no 5xx errors**
```bash
# Check load balancer logs
kubectl -n fabric4l logs -l app=fabric4l-lb --tail=100 | grep -c '"status": 5'
# Should be 0

# Check application error rates
for deploy in l1-ingestion l2-extraction l3-knowledge l4-agent; do
  echo "=== $deploy ==="
  kubectl -n fabric4l logs deploy/$deploy --tail=50 | grep -c "ERROR" || echo "0 errors"
done
```

### Phase 5: Degraded Mode Checklist

Some features may be unavailable in standby region:

| Feature | Status | Notes |
|---|---|---|
| Document ingestion | ✅ Full | |
| Entity extraction | ✅ Full | |
| Knowledge graph queries | ⚠️ Degraded | pgvector fallback may be active |
| Agent orchestration | ✅ Full | |
| Ground truth evaluation | ❌ Unavailable | L5 not replicated in real-time |
| Benchmarks | ❌ Unavailable | L6 results from primary lost |
| Cross-tenant analytics | ⚠️ Degraded | Last 5 min of data may be missing |
| Real-time collaboration | ⚠️ Degraded | WebSocket state not replicated |

**Activate degraded mode if needed:**
```bash
# Notify frontend to show degraded mode banner
curl -X POST https://api.fabric4l.io/v1/admin/degraded-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "enabled": true,
    "reason": "Primary region failover - standby active",
    "affected_features": ["ground_truth", "benchmarks", "realtime_collab"]
  }'
```

---

## 5. Failback Procedure (When Primary Recovers)

### Phase A: Prepare Primary for Rejoin

```bash
# 1. Ensure primary is fully recovered
kubectl config use-context fabric4l-primary
kubectl get nodes
# All should be Ready

# 2. Reconfigure primary as standby
# PostgreSQL: rebase as streaming replica
kubectl -n fabric4l exec postgres-primary-0 -- pg_basebackup \
  -h postgres-standby-0.postgres-standby.fabric4l.svc.cluster.local \
  -D /var/lib/postgresql/data -Fp -Xs -P -v

# 3. Verify replication is flowing
kubectl -n fabric4l exec postgres-primary-0 -- psql -U postgres -c \
  "SELECT pg_is_in_recovery();"  # Should return: t
```

### Phase B: Scheduled Cutback (Maintenance Window)

```bash
# 1. Announce maintenance window
# 2. Repeat Phase 2-4 in reverse (standby → primary)
# 3. Update DNS back to primary
# 4. Scale down standby to reduced capacity
```

---

## 6. Communication Template

### War Room Slack (#incidents-war-room)
```
:red_circle: **P0: FULL REGION FAILOVER IN PROGRESS** — DR-REGION-001
- Detection: Primary region health check failure (multi-service)
- DR Coordinator: @sre-oncall
- War Room: https://zoom.us/j/xxxxxxxxx
- Decision: Activating standby region
- ETA for recovery: 15 minutes
- Data loss risk: Up to 5 minutes of async replication
- Status page: https://status.fabric4l.io/incidents/INC-XXXX
- Updates every 5 minutes in this thread
```

### Customer Communication
```
We are currently experiencing a service disruption in our primary data center.
Our team has activated our disaster recovery procedures and traffic is being
redirected to our standby region.

- **Impact**: Some features may be temporarily unavailable
- **Data integrity**: Your data is safe (replicated to standby region)
- **ETA**: Full service restoration within 15 minutes
- **Updates**: https://status.fabric4l.io/incidents/INC-XXXX
```

---

## 7. Post-Incident Review Template

### Timeline
| Time (UTC) | Event |
|---|---|
| | Primary region failure detected |
| | DR Coordinator paged |
| | Failover decision made |
| | Standby database promoted |
| | DNS cutover completed |
| | Traffic verified on standby |
| | Incident closed |

### Metrics
- **Actual RTO**: ___ minutes (target: 15)
- **Actual RPO**: ___ minutes (target: 5)
- **DNS propagation time**: ___ minutes
- **5xx rate during cutover**: ___%
- **Customer complaints**: ___

### Root Cause
- [ ] Cloud provider outage
- [ ] Network partition
- [ ] Data center failure
- [ ] Cascading failure (internal)
- [ ] Human error (primary region)
- [ ] Other: ___________

### Action Items
| ID | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| | | | | |

### Multi-Region Improvements
- Should RTO target be reduced? ___
- Was replication lag acceptable? ___
- Were there unexpected single-region dependencies? ___
- Should we add multi-region load balancing? ___
