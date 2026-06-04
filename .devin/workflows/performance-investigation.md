---
workflow_id: performance-investigation
name: Performance Investigation
version: 1.0.0
description: Systematic performance investigation workflow for identifying bottlenecks, analyzing metrics, and implementing optimizations
pattern: pipeline-dag
risk_level: medium
---

# Performance Investigation Workflow

Use this workflow for systematic performance investigation when slow response times, high latency, or resource utilization issues are detected in production or staging.

## When to Use

- Slow API response times detected
- High CPU/memory utilization
- Database query performance issues
- Frontend rendering slowness
- User-reported performance problems
- Before major releases to establish baselines

## Workflow Steps

### 1. Define Performance Issue
// turbo
- Quantify the problem with specific metrics
- Establish baseline vs current performance
- Identify affected services/layers
- Determine impact on users
- Set investigation scope

**Required Information:**
- What metric is degraded? (latency, throughput, error rate, resource usage)
- What is the baseline value?
- What is the current value?
- When did the degradation start?
- Which services/layers are affected?

### 2. Gather Metrics and Evidence

**Application Metrics:**
- Response times (p50, p95, p99)
- Request throughput
- Error rates
- Database query times
- Cache hit rates

**Infrastructure Metrics:**
- CPU utilization
- Memory usage
- Disk I/O
- Network I/O
- Container resource limits

**Frontend Metrics:**
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Time to Interactive (TTI)
- Bundle size
- JavaScript execution time

**Tools:**
- Prometheus/Grafana dashboards
- Application Performance Monitoring (APM)
- Browser DevTools Performance tab
- Database query logs
- Application logs

### 3. Identify Bottleneck Layer

Determine which layer is the bottleneck:

**Layer 1 (Ingestion):**
- Crawler throughput
- Queue depth
- Worker utilization

**Layer 2 (Extraction):**
- Extraction latency
- LLM API call times
- Batch processing throughput

**Layer 3 (Knowledge):**
- Neo4j query performance
- Vector search latency
- Graph traversal times

**Layer 4 (Agents):**
- LangGraph workflow execution time
- Agent tool call latency
- Checkpoint/resume overhead

**Layer 5 (Ground Truth):**
- Validation latency
- State machine execution time

**Layer 6 (Benchmarks):**
- Comparison query performance
- Statistical computation time

**Frontend:**
- API response times
- Component render times
- Bundle load times

### 4. Deep Dive Analysis

**Database Performance:**
- Identify slow queries (EXPLAIN ANALYZE)
- Check for missing indexes
- Analyze query patterns
- Review connection pool usage
- Check for N+1 query problems

**Application Code:**
- Profile CPU usage
- Identify hot paths
- Check for inefficient algorithms
- Review async/await patterns
- Analyze memory allocation

**Network/Infrastructure:**
- Check network latency between services
- Review load balancer distribution
- Analyze CDN cache hit rates
- Check for rate limiting

**Frontend:**
- Analyze bundle size
- Check for large JavaScript bundles
- Review component render cycles
- Identify unnecessary re-renders
- Check image optimization

### 5. Hypothesis Generation

Formulate specific hypotheses:

**Example Hypotheses:**
- "The slow query is due to missing index on tenant_id"
- "High CPU is caused by inefficient graph traversal algorithm"
- "Frontend slowness is due to large bundle size from unused dependencies"
- "Memory leak in L4 agent workflow causes gradual degradation"

### 6. Targeted Testing

Test each hypothesis:

**A/B Testing:**
- Deploy fix to staging
- Compare metrics before/after
- Validate improvement

**Load Testing:**
- Simulate production load
- Measure performance under stress
- Identify breaking points

**Profiling:**
- Run profiler on affected service
- Capture CPU/memory profiles
- Analyze flame graphs

### 7. Implement Optimizations

**Database Optimizations:**
- Add missing indexes
- Optimize queries
- Implement query caching
- Add connection pooling
- Denormalize if appropriate

**Code Optimizations:**
- Improve algorithm complexity
- Add caching (Redis, in-memory)
- Implement batching
- Optimize async patterns
- Reduce memory allocations

**Infrastructure Optimizations:**
- Scale horizontally (add instances)
- Scale vertically (increase resources)
- Optimize network topology
- Add CDN caching
- Implement rate limiting

**Frontend Optimizations:**
- Code splitting
- Lazy loading
- Tree shaking
- Image optimization
- Memoization (useMemo, useCallback)

### 8. Validation

After implementing fixes:
- Run load tests
- Compare to baseline metrics
- Monitor in staging for stability
- Check for regressions
- Document improvement

**Success Criteria:**
- Metric returns to within 10% of baseline
- No new performance issues introduced
- Resource utilization within acceptable limits
- User-reported issues resolved

### 9. Production Deployment

**Gradual Rollout:**
- Deploy to canary instances first
- Monitor metrics closely
- Gradually increase traffic
- Have rollback ready

**Monitoring:**
- Watch key metrics for 1 hour
- Set up alerts for regression
- Check logs for errors
- Verify user experience

### 10. Documentation

Document the investigation:
- Root cause analysis
- Metrics before/after
- Changes made
- Lessons learned
- Preventive measures

**Create Performance Runbook:**
- How to detect this issue in future
- Quick mitigation steps
- Permanent fix reference
- Monitoring setup

## Common Performance Patterns

### N+1 Query Problem
**Symptom:** Many database queries for a single request
**Fix:** Eager loading, batch queries, caching

### Missing Index
**Symptom:** Slow query on large table
**Fix:** Add appropriate index, analyze query plan

### Memory Leak
**Symptom:** Gradual memory increase over time
**Fix:** Identify leak source, fix reference cycles, add monitoring

### Inefficient Algorithm
**Symptom:** CPU spike on specific operation
**Fix:** Improve algorithm complexity, add caching

### Large Bundle Size
**Symptom:** Slow frontend load times
**Fix:** Code splitting, tree shaking, lazy loading

### Cache Stampede
**Symptom:** Cache miss causes load spike
**Fix:** Cache warming, lock-based caching, staggered expiration

## Tools and Resources

**Backend:**
- Prometheus: Metrics collection
- Grafana: Visualization
- Jaeger: Distributed tracing
- pprof: CPU/memory profiling
- EXPLAIN ANALYZE: Query analysis

**Frontend:**
- Lighthouse: Performance audit
- WebPageTest: Detailed performance analysis
- Chrome DevTools: Profiling
- webpack-bundle-analyzer: Bundle analysis

**Load Testing:**
- k6: Load testing
- Locust: Python load testing
- Apache Bench: Simple load testing

## Safety Rules

1. **Never optimize without measuring** - baseline first
2. **Test in staging before production** - validate fixes
3. **Have rollback plan** - fixes can make things worse
4. **Monitor after deployment** - watch for regressions
5. **Document findings** - future investigations benefit

## Example Commands

```
/investigate-performance service=layer3 metric=query-latency
/investigate-performance service=frontend metric=tti
/investigate-performance issue=high-cpu-usage
/investigate-performance baseline=2026-05-01
```

## Quick Reference

**Performance Targets:**
- API p95 latency: < 500ms
- Database queries: < 100ms
- Frontend TTI: < 3s
- CPU utilization: < 70%
- Memory utilization: < 80%

**Investigation Priority:**
- P0: User-visible degradation > 2x baseline
- P1: Resource utilization > 90%
- P2: Gradual degradation over time
- P3: Optimization opportunity
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "performance-investigation-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
