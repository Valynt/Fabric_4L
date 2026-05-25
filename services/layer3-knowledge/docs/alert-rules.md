# Layer 3 Knowledge Graph Alert Rules

Phase 3 hardening: Alert rules for graph-specific SLO and security events.

## Security Alerts

### SEC-L3-001: Tenant Isolation Violation Spike
**Metric:** `tenant_isolation_violations_total`
**Condition:** Rate > 5 violations per 5 minutes
**Severity:** Critical
**Description:** Sudden spike in tenant isolation violations indicates potential cross-tenant attack or misconfiguration.
**Action:** Investigate source component, review recent changes, consider blocking offending IP ranges.

### SEC-L3-002: Direct Mutation Bypass Attempts
**Metric:** `tenant_isolation_violations_total` with `violation_type=direct_mutation_bypass`
**Condition:** Count > 0 in 1 minute
**Severity:** Critical
**Description:** Attempts to bypass AuditedGraphMutation gateway detected.
**Action:** Immediate investigation of source IP, review code for bypass attempts, consider emergency shutdown of affected endpoint.

### SEC-L3-003: Unauthorized Traversal Blocked
**Metric:** `unauthorized_traversals_total`
**Condition:** Rate > 10 traversals per 5 minutes
**Severity:** High
**Description:** High rate of unauthorized graph traversal attempts blocked.
**Action:** Review traversal patterns, identify potential hostile actors, update access controls.

## Performance Alerts

### PERF-L3-001: Slow Graph Queries
**Metric:** `graph_slow_queries_total`
**Condition:** Rate > 20 slow queries per minute (threshold_bucket > 5s)
**Severity:** Warning
**Description:** High rate of slow graph queries impacting performance.
**Action:** Review query patterns, add indexes, optimize Cypher queries.

### PERF-L3-002: High Graph Traversal Depth
**Metric:** `graph_traversal_depth`
**Condition:** P95 > 10
**Severity:** Warning
**Description:** Graph queries are traversing too deep, risking performance degradation.
**Action:** Review query patterns, add depth limits, optimize graph structure.

### PERF-L3-003: Large Result Sets
**Metric:** `graph_result_size`
**Condition:** P95 > 500 records
**Severity:** Warning
**Description:** Queries returning large result sets may indicate inefficient queries or missing pagination.
**Action:** Review query patterns, implement pagination, add result size limits.

## Mutation Alerts

### MUT-L3-001: High Mutation Rate
**Metric:** `graph_mutation_rate`
**Condition:** Rate > 100 mutations per second per operation_type
**Severity:** Warning
**Description:** Abnormally high mutation rate may indicate bulk operations or potential abuse.
**Action:** Review bulk operation logs, verify legitimate usage, consider rate limiting.

### MUT-L3-002: Mutation Failure Rate
**Metric:** `graph_mutations_total` with `status=failure`
**Condition:** Error rate > 5%
**Severity:** High
**Description:** High mutation failure rate indicates database issues or data integrity problems.
**Action:** Review database health, check constraint violations, investigate error logs.

## Entity Resolution Alerts

### RES-L3-001: Low Resolution Confidence
**Metric:** `entity_resolution_confidence`
**Condition:** P50 < 0.7 for strategy=hybrid
**Severity:** Warning
**Description:** Entity resolution confidence is low, indicating poor data quality or ambiguous matches.
**Action:** Review data quality, adjust matching thresholds, investigate ambiguous entities.

### RES-L3-002: High Manual Review Rate
**Metric:** `entity_resolution_total` with `confidence=ambiguous`
**Condition:** Rate > 20% of resolutions require manual review
**Severity:** Warning
**Description:** High rate of ambiguous resolutions requiring manual intervention.
**Action:** Review tie-breaking rules, improve data quality, adjust confidence thresholds.

### RES-L3-003: Slow Resolution Performance
**Metric:** `entity_resolution_duration`
**Condition:** P95 > 2 seconds
**Severity:** Warning
**Description:** Entity resolution is slow, impacting user experience.
**Action:** Review candidate search performance, add indexes, optimize scoring algorithms.

## SLO Alerts

### SLO-L3-001: Graph Query Latency SLO Breach
**Metric:** `database_operation_duration` for operation=graph_query
**Condition:** P95 > 1 second
**Severity:** High
**Description:** Graph query latency SLO breach (target: P95 < 1s).
**Action:** Review slow queries, optimize database, scale infrastructure.

### SLO-L3-002: Mutation Latency SLO Breach
**Metric:** `database_operation_duration` for operation=graph_mutation
**Condition:** P95 > 500ms
**Severity:** High
**Description:** Graph mutation latency SLO breach (target: P95 < 500ms).
**Action:** Review database performance, check for locks, optimize mutation operations.

## Health Alerts

### HLT-L3-001: High Error Rate
**Metric:** `errors_total`
**Condition:** Error rate > 1% of total requests
**Severity:** High
**Description:** High error rate indicates system instability.
**Action:** Review error logs, identify root cause, implement fixes.

### HLT-L3-002: Database Connection Issues
**Metric:** `active_connections` for connection_type=neo4j
**Condition:** Connection count > 80% of pool size
**Severity:** Warning
**Description:** Database connection pool nearing exhaustion.
**Action:** Review connection leaks, increase pool size, optimize connection usage.

## Alert Configuration Examples

### Prometheus Alert Rule Example

```yaml
groups:
  - name: layer3_security
    rules:
      - alert: TenantIsolationViolationSpike
        expr: rate(tenant_isolation_violations_total[5m]) > 5
        for: 2m
        labels:
          severity: critical
          component: layer3-knowledge
        annotations:
          summary: "Tenant isolation violation spike detected"
          description: "Rate of tenant isolation violations is {{ $value }} per 5 seconds"

      - alert: DirectMutationBypassAttempt
        expr: rate(tenant_isolation_violations_total{violation_type="direct_mutation_bypass"}[1m]) > 0
        for: 1m
        labels:
          severity: critical
          component: layer3-knowledge
        annotations:
          summary: "Direct mutation bypass attempt detected"
          description: "Attempts to bypass AuditedGraphMutation gateway detected"

  - name: layer3_performance
    rules:
      - alert: SlowGraphQueries
        expr: rate(graph_slow_queries_total{threshold_bucket=">5s"}[1m]) > 20
        for: 5m
        labels:
          severity: warning
          component: layer3-knowledge
        annotations:
          summary: "High rate of slow graph queries"
          description: "{{ $value }} slow queries per minute detected"

  - name: layer3_slo
    rules:
      - alert: GraphQueryLatencySLOBreach
        expr: histogram_quantile(0.95, database_operation_duration_seconds{operation="graph_query"}) > 1
        for: 5m
        labels:
          severity: high
          component: layer3-knowledge
        annotations:
          summary: "Graph query latency SLO breach"
          description: "P95 latency is {{ $value }}s (target: <1s)"
```

## Alert Routing

### Critical Alerts
- **PagerDuty:** Immediate notification to on-call engineer
- **Slack:** #layer3-critical channel
- **Email:** layer3-oncall@example.com

### High Severity Alerts
- **Slack:** #layer3-alerts channel
- **Email:** layer3-team@example.com

### Warning Alerts
- **Slack:** #layer3-ops channel
- **Daily digest:** Included in morning report

## Alert Suppression Rules

### Maintenance Windows
Alerts suppressed during scheduled maintenance windows (defined in configuration).

### Known Issues
Alerts suppressed for known issues tracked in incident management system.

### Testing Environments
Alerts suppressed for non-production environments unless explicitly enabled.

## Alert Tuning Guidelines

1. **Start conservative:** Set thresholds based on baseline metrics, adjust after observing false positives.
2. **Review weekly:** Review alert effectiveness weekly, adjust thresholds and conditions.
3. **Document changes:** Maintain changelog for alert rule modifications.
4. **Test alerts:** Periodically test alert delivery and routing.
5. **SLO-driven:** Align alert thresholds with SLO targets and customer impact.
