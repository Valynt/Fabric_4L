# Operations Runbook

> **Audit note (2026-07-18):** This runbook defines a SEV-0..SEV-3 severity model. `docs/operations/severity-escalation-policy.md` defines a different SEV-1..SEV-4 model with distinct response-time criteria. Reconcile these two models; `severity-escalation-policy.md` appears more recent and is referenced by `docs/operations/RUNBOOK.md`.

## Incident Response

### Severity Levels

| Level | Criteria | Response Time | Example |
|-------|----------|---------------|---------|
| **SEV-0** | Complete outage, data loss, security breach | 15 minutes | All services down, unauthorized data access |
| **SEV-1** | Major feature degradation, customer-visible | 1 hour | Graph queries failing, auth issues |
| **SEV-2** | Minor degradation, workarounds exist | 4 hours | Performance degradation, non-critical bugs |
| **SEV-3** | Cosmetic issues, documentation | 24 hours | UI glitches, typos |

### Incident Response Procedure

#### 1. Detection and Alerting

```bash
# Check current alerts
kubectl get alerts -n monitoring

# View recent events
kubectl get events -n value-fabric --sort-by='.lastTimestamp' | tail -20
```

#### 2. Initial Response

1. **Acknowledge**: Page on-call engineer via PagerDuty
2. **Assess**: Determine severity and scope
3. **Assemble**: Start in `#incident-response`, then create a dated war-room channel `#inc-sev-<level>-YYYYMMDD` if dedicated coordination is required
4. **Act**: Begin mitigation (preserve evidence for SEV-0/1)

#### 3. Communication

| Audience | Channel | Frequency |
|----------|---------|-----------|
| Response team | #incident-response (or `#inc-sev-<level>-YYYYMMDD` war room) | Real-time |
| Engineering leads | #engineering-leads | Every 30 min |
| Executives | Email | Every 2 hours |
| Customers | Status page | As needed |

#### 4. Resolution and Post-Incident

1. Resolve incident in PagerDuty
2. Schedule post-mortem within 48 hours (SEV-0/1) or 1 week (SEV-2/3)
3. Create action items with owners and due dates
4. Update runbook if needed

### Security Incident Response

#### Data Breach Procedure

1. **Contain**: Isolate affected systems
2. **Assess**: Determine scope of data access
3. **Notify**: Legal team within 1 hour
4. **Document**: Preserve all logs and evidence
5. **Eradicate**: Remove attacker access
6. **Recover**: Restore from known-good backups
7. **Review**: Post-incident with legal and compliance

**Legal Notification Requirements**:
- GDPR: 72 hours to supervisory authority
- GDPR: Without undue delay to affected individuals
- State laws: Varies by jurisdiction

## Rollback Procedures

### Database Rollback

#### PostgreSQL (Layer 5)

```bash
# Point-in-time recovery
# Identify target time (before problematic migration)
TARGET_TIME="2026-04-15 10:30:00 UTC"

# Initiate PITR from cloud provider console or CLI
# AWS RDS:
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier value-fabric-prod \
  --target-db-instance-identifier value-fabric-prod-rollback \
  --restore-time "$TARGET_TIME"

# After verification, update application connection strings
kubectl set env deployment/layer5-ground-truth \
  DATABASE_URL=<rollback-instance-url> -n value-fabric
```

#### Neo4j (Layer 3)

```bash
# Restore from backup snapshot
neo4j-admin database restore --from=/backups/neo4j-20250415.dump

# Restart Neo4j pods
kubectl rollout restart statefulset/neo4j -n value-fabric
```

### Application Rollback

#### Kubernetes Rollout

```bash
# Check current rollout status
kubectl rollout status deployment/layer4-agents -n value-fabric

# Rollback to previous revision
kubectl rollout undo deployment/layer4-agents -n value-fabric

# Rollback to specific revision
kubectl rollout undo deployment/layer4-agents --to-revision=3 -n value-fabric

# Verify rollback
kubectl get pods -n value-fabric -l app=layer4-agents
```

#### Helm Rollback

```bash
# List releases
helm list -n value-fabric

# Rollback to previous version
helm rollback value-fabric 2 -n value-fabric

# Verify
helm status value-fabric -n value-fabric
```

### GitOps Rollback (Argo CD)

```bash
# Sync to previous commit
argocd app sync value-fabric --revision a1b2c3d

# Or rollback via UI:
# 1. Open Argo CD dashboard
# 2. Select application
# 3. Click "History"
# 4. Select previous healthy revision
# 5. Click "Rollback"
```

## Monitoring and Alerting

### Key Metrics Dashboard

**Primary Dashboard**: `https://grafana.value-fabric.com/d/value-fabric`

| Metric | Warning | Critical | Query |
|--------|---------|----------|-------|
| API error rate | > 1% | > 5% | `rate(http_requests_total{status=~"5.."}[5m])` |
| P95 latency | > 500ms | > 1000ms | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |
| Database connections | > 80% | > 95% | `pg_stat_activity_count / pg_settings_max_connections` |
| Queue depth | > 100 | > 500 | `celery_queue_length` |
| Disk usage | > 80% | > 90% | `node_filesystem_avail_bytes / node_filesystem_size_bytes` |

### Log Queries

**Kibana/Elasticsearch**:

```bash
# Find all errors in last hour
level:ERROR AND @timestamp:[now-1h TO now]

# Find slow queries
message:"slow query" AND @timestamp:[now-1h TO now]

# Find auth failures
message:"authentication failed" AND @timestamp:[now-1h TO now]

# Find specific trace
trace_id:"abc-123-def"
```

### Common Issues

#### Issue: High Error Rate

**Symptoms**: PagerDuty alert for error rate > 5%

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n value-fabric --field-selector=status.phase!=Running

# Check recent logs
kubectl logs -n value-fabric -l app=layer4-agents --tail=100 | grep ERROR

# Check for resource exhaustion
kubectl top pods -n value-fabric
```

**Resolution**:
1. Check for upstream dependency failures (database, Redis, Neo4j)
2. Scale up if resource-constrained: `kubectl scale deployment/layer4-agents --replicas=5`
3. Restart if memory leak suspected: `kubectl rollout restart deployment/layer4-agents`

#### Issue: Database Connection Pool Exhaustion

**Symptoms**: Errors about connection timeouts, queue buildup

**Diagnosis**:
```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check idle connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle';"
```

**Resolution**:
1. Restart application to clear idle connections
2. Increase pool size in configuration
3. Add connection pool monitoring

#### Issue: Redis Memory Exhaustion

**Symptoms**: Eviction warnings, cache misses increasing

**Diagnosis**:
```bash
# Check memory usage
redis-cli INFO memory | grep used_memory

# Check eviction policy
redis-cli INFO stats | grep evicted_keys
```

**Resolution**:
1. Increase Redis memory allocation
2. Review cache TTL policies
3. Clear non-essential caches: `redis-cli FLUSHDB`

#### Issue: LLM API Rate Limiting

**Symptoms**: Layer 2 extraction failures, 429 errors

**Diagnosis**:
```bash
# Check rate limit headers in logs
kubectl logs -n value-fabric -l app=layer2-extraction | grep "429"
```

**Resolution**:
1. Implement exponential backoff in code
2. Add circuit breaker pattern
3. Request rate limit increase from provider

## Maintenance Procedures

### Certificate Rotation

```bash
# Check certificate expiration
cert-manager check renew -n value-fabric

# Force early renewal (if needed)
kubectl cert-manager renew -n value-fabric <certificate-name>

# Verify renewal
kubectl get certificate -n value-fabric
openssl s_client -connect api.value-fabric.com:443 -servername api.value-fabric.com 2>/dev/null | openssl x509 -noout -dates
```

### Database Maintenance

```bash
# VACUUM and ANALYZE
psql $DATABASE_URL -c "VACUUM ANALYZE;"

# Check for bloat
psql $DATABASE_URL -c "SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables;"

# Reindex if needed
psql $DATABASE_URL -c "REINDEX INDEX CONCURRENTLY idx_name;"
```

### Security Updates

```bash
# Check for available updates
kubectl get nodes -o wide
kubectl describe node <node-name> | grep "OS Image"

# Drain node for maintenance
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Update base images
# 1. Update Dockerfile base image tags
# 2. Rebuild and deploy
# 3. Verify in staging first
```

## Contact Information

| Role | Contact Alias | Primary On-Call Routing | Backup On-Call Routing | Escalation |
|------|---------------|-------------------------|------------------------|------------|
| On-Call Engineer | `@vf-eng-oncall` | PagerDuty service `pagerduty-critical` | Slack `#vf-alerts-critical` | Engineering Lead |
| Engineering Lead | `@vf-eng-leadership` (`eng-leadership@value-fabric.com`) | PagerDuty service `pagerduty-critical` (platform-engineering escalation path) | PagerDuty schedule `engineering-lead-secondary` + Slack `#engineering-leads` | VP Engineering |
| Security Lead | `@vf-security-lead` (`security-leadership@value-fabric.com`) | Alertmanager team route `team:security` → receiver `pagerduty-critical` | PagerDuty schedule `security-secondary` + Slack `#security` | CISO |
| SRE Lead | `@vf-sre-leadership` (`sre-leadership@value-fabric.com`) | Alertmanager severity route `severity:critical` → receiver `pagerduty-critical` | PagerDuty schedule `sre-secondary` + Slack `#vf-alerts-critical` | VP Engineering |
| Incident Commander | `@vf-incident-command` | Slack `#incident-response` | PagerDuty schedule `incident-commander-backup` | CEO (SEV-0 only) |

> Routing alignment: The primary and backup channels above are intentionally aligned with the active Alertmanager route trees in `monitoring/alertmanager/alertmanager.yml` and `monitoring/alertmanager/alertmanager-production.yml` (`pagerduty-critical`, `#vf-alerts-critical`) plus team/severity routing definitions in `monitoring/alertmanager/alertmanager-enhanced.yml` (`team:security`, `severity:critical`).

### Runbook Ownership and Review Cadence

- **Owner**: Site Reliability Engineering (`@vf-sre-leadership`)
- **Review cadence**: Quarterly (first business week of each quarter)
- **Scope**: Validate role aliases, PagerDuty schedules/services, Slack channels, and escalation targets.
- **Required update path**: If any alias or route changes, update this runbook in the same change set as Alertmanager/paging configuration.

## External Dependencies

| Service | Status Page | Support |
|---------|-------------|---------|
| AWS/GCP/Azure | [Status](https://status.cloud) | Case portal |
| Neo4j Aura | [Status](https://status.neo4j.io) | Support portal |
| OpenAI | [Status](https://status.openai.com) | Developer forum |
| Auth0/Okta | [Status](https://status.auth0.com) | Support portal |

---

**Last Updated**: 2026-05-12  
**Version**: 1.0.0  
**Owner**: Site Reliability Engineering  
**Next Review**: 2026-07-01 (quarterly cadence)


## Observability Contracts

- Trace correlation normalization contract: `docs/contracts/trace-correlation-observability-contract.md`.


## Tabletop Drill Evidence

- Latest cross-functional incident tabletop: `docs/operations/evidence/tabletop-drill-2026-05-12-servicedown.md`.
- Scope covered PagerDuty service/schedule paths (`pagerduty-critical`, `engineering-lead-secondary`, `sre-secondary`) and Slack escalation channels (`#vf-alerts-critical`, `#incident-response`).
