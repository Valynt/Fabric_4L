/**
 * L3 V2 Router Read-Heavy Load Test (PERF-L3-014)
 *
 * Purpose: Verify that the V2 routing architecture and cypher_security.py
 *          allowlist middleware do not introduce latency regressions under
 *          high-concurrency multi-tenant read load.
 *
 * Acceptance criteria:
 *   - p95 latency for read operations < 150 ms
 *   - Error rate < 1%
 *
 * Usage:
 *   k6 run \
 *     --env L3_URL=http://localhost:8003 \
 *     --env TENANT_COUNT=50 \
 *     --env PERF_AUTH_BEARER=<jwt> \
 *     tests/performance/k6/l3_read_heavy.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

const L3_URL = (__ENV.L3_URL || 'http://localhost:8003').replace(/\/$/, '');
const TENANT_COUNT = parseInt(__ENV.TENANT_COUNT || '50');

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const entityListP95    = new Trend('l3_entity_list_duration_ms',    true);
const entityDetailP95  = new Trend('l3_entity_detail_duration_ms',  true);
const hybridSearchP95  = new Trend('l3_hybrid_search_duration_ms',  true);
const graphRagP95      = new Trend('l3_graphrag_duration_ms',       true);
const subgraphP95      = new Trend('l3_subgraph_duration_ms',       true);
const errorRate        = new Rate('l3_read_error_rate');
const requestCount     = new Counter('l3_read_requests_total');

// ---------------------------------------------------------------------------
// Thresholds (acceptance criteria)
// ---------------------------------------------------------------------------

export const options = {
  scenarios: {
    l3_read_heavy: {
      executor: 'constant-vus',
      exec: 'runReadHeavy',
      vus: TENANT_COUNT,
      duration: __ENV.PERF_DURATION || '5m',
    },
  },
  thresholds: {
    // p95 < 150 ms for all read operations
    l3_entity_list_duration_ms:   ['p(95)<150'],
    l3_entity_detail_duration_ms: ['p(95)<150'],
    l3_hybrid_search_duration_ms: ['p(95)<150'],
    l3_graphrag_duration_ms:      ['p(95)<150'],
    l3_subgraph_duration_ms:      ['p(95)<150'],
    // Error rate < 1%
    l3_read_error_rate:           ['rate<0.01'],
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tenantForVU(vuNumber) {
  const idx = (vuNumber - 1) % TENANT_COUNT;
  return `tenant-${String(idx).padStart(3, '0')}`;
}

function authHeaders(tenantId) {
  const h = { 'Content-Type': 'application/json' };
  if (__ENV.PERF_AUTH_BEARER) {
    h['Authorization'] = `Bearer ${__ENV.PERF_AUTH_BEARER}`;
  }
  h['X-Tenant-ID'] = tenantId;
  return h;
}

// Stable entity IDs per tenant so subgraph / detail calls are realistic
function entityIdForTenant(tenantId) {
  return `entity-${tenantId}-001`;
}

// ---------------------------------------------------------------------------
// Scenario
// ---------------------------------------------------------------------------

export function runReadHeavy() {
  const tenantId = tenantForVU(__VU);
  const headers  = authHeaders(tenantId);
  const entityId = entityIdForTenant(tenantId);

  // 1. Entity list (V2 router: GET /v1/entities)
  {
    const res = http.get(
      `${L3_URL}/v1/entities?limit=25&sort_by=confidence&sort_order=desc`,
      { headers, tags: { endpoint: 'entity_list' } }
    );
    entityListP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'entity_list 200': (r) => r.status === 200,
      'entity_list has entities key': (r) => {
        try { return Array.isArray(JSON.parse(r.body).entities); } catch { return false; }
      },
    });
    errorRate.add(!ok);
  }

  sleep(0.1);

  // 2. Entity detail (V2 router: GET /v1/entities/{id})
  {
    const res = http.get(
      `${L3_URL}/v1/entities/${entityId}`,
      { headers, tags: { endpoint: 'entity_detail' } }
    );
    entityDetailP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'entity_detail 200 or 404': (r) => r.status === 200 || r.status === 404,
    });
    errorRate.add(!ok);
  }

  sleep(0.1);

  // 3. Hybrid search (V2 router via compat_aliases: POST /v1/search)
  {
    const payload = JSON.stringify({
      query: 'revenue growth capability',
      search_type: 'hybrid',
      top_k: 10,
    });
    const res = http.post(
      `${L3_URL}/v1/search`,
      payload,
      { headers, tags: { endpoint: 'hybrid_search' } }
    );
    hybridSearchP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'hybrid_search 200': (r) => r.status === 200,
    });
    errorRate.add(!ok);
  }

  sleep(0.1);

  // 4. GraphRAG query (V2 router: POST /v1/query/graph)
  {
    const payload = JSON.stringify({
      query: 'What are the top value drivers for this tenant?',
      max_hops: 2,
      max_results: 5,
    });
    const res = http.post(
      `${L3_URL}/v1/query/graph`,
      payload,
      { headers, tags: { endpoint: 'graphrag' } }
    );
    graphRagP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'graphrag 200': (r) => r.status === 200,
    });
    errorRate.add(!ok);
  }

  sleep(0.1);

  // 5. Query subgraph (V2 router: GET /v1/graph/subgraph)
  {
    const res = http.get(
      `${L3_URL}/v1/graph/subgraph?query=capability&depth=2&limit=50`,
      { headers, tags: { endpoint: 'subgraph' } }
    );
    subgraphP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'subgraph 200 or 400': (r) => r.status === 200 || r.status === 400,
    });
    errorRate.add(!ok);
  }

  // Jitter to avoid thundering-herd
  sleep(randomIntBetween(1, 3) * 0.1);
}
