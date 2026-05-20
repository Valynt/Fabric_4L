/**
 * L3 V2 Router Write/Mutation Load Test (PERF-L3-014)
 *
 * Purpose: Verify that the strict tenancy checks (Sprint 1) and V2 routing
 *          architecture (Sprint 2 & 3) have not introduced latency regressions
 *          for write/mutation operations under production-representative load.
 *
 * Acceptance criteria:
 *   - p95 latency for write/mutation operations < 250 ms
 *   - Error rate < 2%
 *
 * Endpoints exercised:
 *   POST /v1/ingest          — RDF ingest (V2 ingestion router)
 *   POST /v1/batch/entities  — Batch entity create/update/delete (V2 analytics router)
 *   POST /v1/entities/query  — Filtered entity query (V2 entities router)
 *   POST /v1/analytics/communities — Community detection (V2 analytics router)
 *
 * Usage:
 *   k6 run \
 *     --env L3_URL=http://localhost:8003 \
 *     --env TENANT_COUNT=50 \
 *     --env PERF_AUTH_BEARER=<jwt> \
 *     tests/performance/k6/l3_write_heavy.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomIntBetween, randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

const L3_URL = (__ENV.L3_URL || 'http://localhost:8003').replace(/\/$/, '');
const TENANT_COUNT = parseInt(__ENV.TENANT_COUNT || '50');

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const ingestP95         = new Trend('l3_ingest_duration_ms',          true);
const batchEntityP95    = new Trend('l3_batch_entity_duration_ms',     true);
const entityQueryP95    = new Trend('l3_entity_query_duration_ms',     true);
const communityP95      = new Trend('l3_community_detect_duration_ms', true);
const errorRate         = new Rate('l3_write_error_rate');
const requestCount      = new Counter('l3_write_requests_total');

// ---------------------------------------------------------------------------
// Thresholds (acceptance criteria)
// ---------------------------------------------------------------------------

export const options = {
  scenarios: {
    l3_write_heavy: {
      executor: 'constant-vus',
      exec: 'runWriteHeavy',
      vus: TENANT_COUNT,
      duration: __ENV.PERF_DURATION || '5m',
    },
  },
  thresholds: {
    // p95 < 250 ms for all write/mutation operations
    l3_ingest_duration_ms:          ['p(95)<250'],
    l3_batch_entity_duration_ms:    ['p(95)<250'],
    l3_entity_query_duration_ms:    ['p(95)<250'],
    l3_community_detect_duration_ms:['p(95)<250'],
    // Error rate < 2%
    l3_write_error_rate:            ['rate<0.02'],
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

function minimalRdf(tenantId, sourceId) {
  return `@prefix ex: <http://example.org/> .
ex:${sourceId} a ex:Capability ;
  ex:tenant "${tenantId}" ;
  ex:name "Perf Test Capability ${sourceId}" .`;
}

// ---------------------------------------------------------------------------
// Scenario
// ---------------------------------------------------------------------------

export function runWriteHeavy() {
  const tenantId = tenantForVU(__VU);
  const headers  = authHeaders(tenantId);
  const sourceId = `src-${tenantId}-${randomString(6)}`;

  // 1. RDF ingest (V2 ingestion router: POST /v1/ingest)
  {
    const payload = JSON.stringify({
      rdf_data: minimalRdf(tenantId, sourceId),
      source_id: sourceId,
      extraction_job_id: `job-${randomString(8)}`,
      content_hash: randomString(32),
      tenant_id: tenantId,
    });
    const res = http.post(
      `${L3_URL}/v1/ingest`,
      payload,
      { headers, tags: { endpoint: 'ingest' } }
    );
    ingestP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'ingest 200': (r) => r.status === 200,
      'ingest has status field': (r) => {
        try { return !!JSON.parse(r.body).status; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  }

  sleep(0.15);

  // 2. Batch entity create (V2 analytics router: POST /v1/batch/entities)
  {
    const payload = JSON.stringify({
      operations: [
        {
          operation: 'create',
          entity_type: 'Capability',
          properties: {
            name: `Perf Capability ${randomString(4)}`,
            tenant_id: tenantId,
            confidence_score: 0.85,
          },
        },
      ],
      atomic: false,
    });
    const res = http.post(
      `${L3_URL}/v1/batch/entities`,
      payload,
      { headers, tags: { endpoint: 'batch_entities' } }
    );
    batchEntityP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'batch_entities 200': (r) => r.status === 200,
      'batch_entities has results': (r) => {
        try { return Array.isArray(JSON.parse(r.body).results); } catch { return false; }
      },
    });
    errorRate.add(!ok);
  }

  sleep(0.15);

  // 3. Filtered entity query (V2 entities router: POST /v1/entities/query)
  {
    const payload = JSON.stringify({
      entity_types: ['Capability', 'UseCase'],
      min_confidence: 0.7,
      limit: 20,
      offset: 0,
    });
    const res = http.post(
      `${L3_URL}/v1/entities/query`,
      payload,
      { headers, tags: { endpoint: 'entity_query' } }
    );
    entityQueryP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'entity_query 200': (r) => r.status === 200,
    });
    errorRate.add(!ok);
  }

  sleep(0.15);

  // 4. Community detection (V2 analytics router: POST /v1/analytics/communities)
  // Lighter algorithm to stay within write latency budget
  {
    const payload = JSON.stringify({
      algorithm: 'louvain',
      entity_types: ['Capability'],
      min_community_size: 2,
    });
    const res = http.post(
      `${L3_URL}/v1/analytics/communities`,
      payload,
      { headers, tags: { endpoint: 'community_detect' } }
    );
    communityP95.add(res.timings.duration);
    requestCount.add(1);
    const ok = check(res, {
      'community_detect 200': (r) => r.status === 200,
    });
    errorRate.add(!ok);
  }

  // Jitter to avoid thundering-herd
  sleep(randomIntBetween(1, 4) * 0.1);
}
