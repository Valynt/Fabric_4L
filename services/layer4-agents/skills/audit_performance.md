---
name: audit_performance
description: Performance engineering audit including load test validation, database query optimization, cache efficiency analysis, and frontend Core Web Vitals monitoring. Use when validating performance SLOs, preparing for production scale, or investigating performance regressions.
allowed_agents: ["sre", "performance-engineer", "platform-team", "pre-production-audit"]
---

# Audit Performance Skill

## Purpose

This skill provides comprehensive performance validation for the Value Fabric platform, including:
- SLO compliance verification and error budget analysis
- Load test execution and threshold validation
- Database query performance and N+1 detection
- Cache efficiency and optimization opportunities
- Frontend Core Web Vitals monitoring
- Performance regression detection from baselines

## When to Use

- Pre-production performance validation
- Quarterly SLO compliance reviews
- After performance-related incidents
- Before major scaling events or launches
- When investigating latency regressions
- Capacity planning validation

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| audit_scope | string | No | "all" | Areas: all, load_testing, database, cache, frontend, api_latency |
| layers | string[] | No | ["L1", "L2", "L3", "L4", "frontend"] | Layers to audit |
| run_load_tests | boolean | No | false | Execute k6 load tests as part of audit |
| load_test_duration | string | No | "2m" | Duration for load test execution |
| check_slo_compliance | boolean | No | true | Validate SLO compliance from metrics |
| slo_lookback_days | integer | No | 7 | Historical SLO data to analyze (1-30 days) |
| detect_regressions | boolean | No | true | Compare against baseline to detect regressions |
| baseline_comparison_window | string | No | "7d" | Time window for baseline comparison |
| severity_threshold | string | No | "medium" | Minimum severity: critical, high, medium, low |
| output_format | string | No | "markdown" | Output: markdown, json, sarif |
| fail_on_critical | boolean | No | true | Fail if critical findings detected |

## Audit Steps

### 1. SLO Compliance Analysis

Verify platform meets defined Service Level Objectives:

```promql
# Availability SLO: 99.9%
sum(rate(http_requests_total{status=~"2.."}[30d]))
/ sum(rate(http_requests_total[30d]))

# Latency SLO: p99 < 2s
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[7d])) by (le)
)

# Error budget consumption
1 - (
  sum(rate(http_requests_total{status=~"2.."}[30d]))
  / sum(rate(http_requests_total[30d]))
) - 0.001
```

**Layer-Specific SLOs:**

| Layer | Metric | Target | Query |
|-------|--------|--------|-------|
| L1 | Task Success Rate | 99.5% | `successful_tasks / total_tasks` |
| L1 | Task Latency p99 | < 5 min | `celery_task_duration_seconds` |
| L2 | Extraction Success | 98% | `successful_extractions / total` |
| L2 | Extraction Latency p99 | < 30s | `extraction_duration_seconds` |
| L3 | Query Latency p99 | < 500ms | `neo4j_query_duration_seconds` |
| L3 | Search Latency p99 | < 1s | `vector_search_duration_seconds` |
| L4 | Workflow Success | 95% | `completed_workflows / total` |
| L4 | Workflow Duration p99 | < 5 min | `workflow_duration_seconds` |

**Burn Rate Alerts:**
- 5x burn rate → Alert after 2 minutes (budget exhausted in 6 hours)
- 2x burn rate → Alert after 15 minutes (budget exhausted in 3 days)

### 2. Load Test Validation

Execute and analyze k6 load tests:

```bash
# Critical paths load test
k6 run --env L2_RPS=1 --env L3_RPS=3 --env L4_RPS=3 \
  --env PERF_DURATION=2m \
  tests/performance/k6/l2_l3_l4_critical_paths.js

# Multi-tenant stress test
k6 run tests/performance/k6/multi-tenant.js

# Stress test to find breaking point
k6 run tests/performance/k6/stress-test.js
```

**Load Test Scenarios:**

| Scenario | Target RPS | Duration | Key Metrics |
|----------|------------|----------|-------------|
| L2 Extract-Ingest | 1 rps | 2 min | p95 < 5s, error < 2% |
| L3 Hybrid Search | 3 rps | 2 min | p95 < 1.2s, error < 1% |
| L4 Active Workflows | 3 rps | 2 min | p95 < 1s, error < 1% |
| Multi-Tenant | 10 tenants | 5 min | No cross-tenant leakage |
| Stress | Ramp to 100 rps | 10 min | Identify breaking point |

### 3. Database Performance Audit

Identify query optimization opportunities:

```sql
-- Find slow queries (requires pg_stat_statements)
SELECT query,
       mean_exec_time,
       calls,
       total_exec_time,
       rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Detect N+1 query patterns (via application logs)
-- Look for repeated queries with single-row results
```

**Common Performance Issues:**

| Issue | Detection | Impact | Solution |
|-------|-----------|--------|----------|
| N+1 Queries | Repeated single-row SELECTs | High latency | Eager loading, batching |
| Missing Indexes | Seq scans on large tables | Slow queries | Add indexes |
| Connection Pool Exhaustion | Queue depth > 0 | Timeouts | Scale pool size |
| Lock Contention | Long-running transactions | Deadlocks | Shorter transactions |

**Connection Pool Sizing:**
```python
# Per-layer connection pool configuration
LAYER_POOL_SIZES = {
    "L1": {"min": 5, "max": 20},   # High throughput
    "L2": {"min": 2, "max": 10},   # LLM API bound
    "L3": {"min": 5, "max": 30},   # Complex graph queries
    "L4": {"min": 5, "max": 20},   # Agent orchestration
    "L5": {"min": 2, "max": 10},   # Evaluation tasks
}
```

### 4. Cache Efficiency Analysis

Evaluate Redis cache performance:

```promql
# Cache hit rate
redis_keyspace_hits / (redis_keyspace_hits + redis_keyspace_misses)

# Eviction rate
rate(redis_evicted_keys_total[5m])

# Memory usage
redis_memory_used_bytes / redis_memory_max_bytes
```

**Cache Metrics to Monitor:**

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Hit Rate | > 85% | < 70% |
| Memory Usage | < 80% | > 90% |
| Eviction Rate | 0/sec | > 10/sec |
| P99 Latency | < 5ms | > 10ms |

**Cache Optimization Opportunities:**
- Review TTL configurations
- Analyze cache key patterns
- Identify cache stampede risks
- Evaluate cache warming strategies

### 5. Frontend Performance

Monitor Core Web Vitals:

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | < 2.5s | < 4.0s | > 4.0s |
| INP (Interaction to Next Paint) | < 200ms | < 500ms | > 500ms |
| CLS (Cumulative Layout Shift) | < 0.1 | < 0.25 | > 0.25 |
| TTFB (Time to First Byte) | < 600ms | < 800ms | > 800ms |
| FCP (First Contentful Paint) | < 1.8s | < 3.0s | > 3.0s |

**Bundle Analysis:**
```bash
# Analyze frontend bundle size
npm run build
npx vite-bundle-visualizer

# Check for unused code
npx unimported
```

### 6. Regression Detection

Compare current performance against baseline:

```python
REGRESSION_THRESHOLDS = {
    "latency_p95": {"threshold_pct": 20, "severity": "high"},
    "latency_p99": {"threshold_pct": 15, "severity": "critical"},
    "error_rate": {"threshold_pct": 50, "severity": "critical"},
    "throughput": {"threshold_pct": -20, "severity": "high"},  # Decrease
}

# Alert if current value deviates > threshold from baseline
```

## Output Structure

### Summary

```markdown
## Performance Audit: Grade B (82/100)

**SLO Compliance:** 94% (5/6 SLOs met)
**Load Tests:** 3/3 passed
**Regressions:** 2 detected (1 high, 1 medium)

**Critical Finding:**
- L3 graph query p99 latency: 750ms (target: 500ms) - 50% over SLO

**High Priority Findings:**
- Redis cache hit rate: 72% (target: 85%)
- L2 extraction error rate: 3.2% (target: 2%)
```

### Detailed Findings

**SLO Non-Compliance:**
```json
{
  "slo_name": "L3 Query Latency p99",
  "target": 500,
  "current": 750,
  "compliant": false,
  "error_budget_remaining_pct": 12,
  "trend": "degrading",
  "severity": "high"
}
```

**Database Performance:**
```json
{
  "layer": "L3",
  "query_pattern": "MATCH (n)-[r]->(m) WHERE n.id IN $ids",
  "avg_execution_time_ms": 450,
  "calls_per_minute": 1200,
  "index_usage_pct": 65,
  "severity": "medium",
  "recommendation": "Add composite index on (n.id, r.type) for traversal queries"
}
```

**Performance Regressions:**
```json
{
  "metric": "L2 extraction p95 latency",
  "baseline_value": 22000,
  "current_value": 28500,
  "change_pct": 29.5,
  "severity": "high",
  "likely_cause": "Recent LLM model upgrade to gpt-4-turbo"
}
```

## Example Usage

```bash
# Full performance audit with live load tests
python -m layer4_agents.tools.audit_performance --run-load-tests --load-test-duration 5m

# SLO compliance check only
python -m layer4_agents.tools.audit_performance --audit-scope slo_compliance --slo-lookback-days 14

# Database performance focus
python -m layer4_agents.tools.audit_performance --audit-scope database --detect-regressions

# CI gate mode (fails on critical performance issues)
python -m layer4_agents.tools.audit_performance --fail-on-critical --output-format json

# Compare against extended baseline
python -m layer4_agents.tools.audit_performance --baseline-comparison-window 14d
```

## Integration with Pre-Production Audit

This skill is automatically invoked by the `pre-production-audit` workflow when:
- Load test results are available
- SLO alerts have fired in the past 7 days
- Database migration includes index changes
- Cache configuration is modified

## Safety Notes

- **Critical performance findings block production deployment**
- Load tests run against staging by default (not production)
- SLO violations trigger automatic capacity review
- Database changes require rollback plan

## Related Skills

- `assess_drift` - Detect configuration drift affecting performance
- `audit_infrastructure` - Validate infrastructure capacity
- `audit_compliance` - Performance-related compliance (SLO documentation)
