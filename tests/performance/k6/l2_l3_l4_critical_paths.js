import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const L2_URL = (__ENV.L2_URL || 'http://localhost:8002').replace(/\/$/, '');
const L3_URL = (__ENV.L3_URL || 'http://localhost:8003').replace(/\/$/, '');
const L4_URL = (__ENV.L4_URL || 'http://localhost:8004').replace(/\/$/, '');

function requireEnv(name) {
  const value = __ENV[name];
  if (!value) {
    throw new Error(`${name} is required for authenticated performance tests`);
  }
  return value;
}

const PERF_TENANT_ID = requireEnv('PERF_TENANT_ID');
const PERF_AUTH_BEARER = requireEnv('PERF_AUTH_BEARER');
const PERF_S2S_BEARER = requireEnv('PERF_S2S_BEARER');

const userAuthHeaders = {
  Authorization: `Bearer ${PERF_AUTH_BEARER}`,
  'X-Tenant-ID': PERF_TENANT_ID,
};

const s2sAuthHeaders = {
  Authorization: `Bearer ${PERF_S2S_BEARER}`,
  'X-Tenant-ID': PERF_TENANT_ID,
};

const l2Duration = new Trend('l2_extract_ingest_duration_ms');
const l3Duration = new Trend('l3_hybrid_search_duration_ms');
const l4Duration = new Trend('l4_workflows_active_duration_ms');

const l2Errors = new Rate('l2_extract_ingest_error_rate');
const l3Errors = new Rate('l3_hybrid_search_error_rate');
const l4Errors = new Rate('l4_workflows_active_error_rate');

export const options = {
  scenarios: {
    l2_extract_ingest: {
      executor: 'constant-arrival-rate',
      exec: 'runL2ExtractAndIngest',
      rate: Number(__ENV.L2_RPS || 1),
      timeUnit: '1s',
      duration: __ENV.PERF_DURATION || '2m',
      preAllocatedVUs: Number(__ENV.L2_PREALLOCATED_VUS || 5),
      maxVUs: Number(__ENV.L2_MAX_VUS || 20),
      startTime: '0s',
    },
    l3_hybrid_search: {
      executor: 'constant-arrival-rate',
      exec: 'runL3HybridSearch',
      rate: Number(__ENV.L3_RPS || 3),
      timeUnit: '1s',
      duration: __ENV.PERF_DURATION || '2m',
      preAllocatedVUs: Number(__ENV.L3_PREALLOCATED_VUS || 8),
      maxVUs: Number(__ENV.L3_MAX_VUS || 30),
      startTime: '10s',
    },
    l4_workflows_active: {
      executor: 'constant-arrival-rate',
      exec: 'runL4WorkflowsActive',
      rate: Number(__ENV.L4_RPS || 3),
      timeUnit: '1s',
      duration: __ENV.PERF_DURATION || '2m',
      preAllocatedVUs: Number(__ENV.L4_PREALLOCATED_VUS || 8),
      maxVUs: Number(__ENV.L4_MAX_VUS || 30),
      startTime: '20s',
    },
  },
  thresholds: {
    l2_extract_ingest_error_rate: ['rate<0.02'],
    l3_hybrid_search_error_rate: ['rate<0.01'],
    l4_workflows_active_error_rate: ['rate<0.01'],
    l2_extract_ingest_duration_ms: ['p(95)<5000'],
    l3_hybrid_search_duration_ms: ['p(95)<1200'],
    l4_workflows_active_duration_ms: ['p(95)<1000'],
  },
};

function defaultHeaders(authHeaders) {
  return {
    'Content-Type': 'application/json',
    ...authHeaders,
  };
}

export function runL2ExtractAndIngest() {
  const payload = JSON.stringify({
    content_id: `perf-${__VU}-${__ITER}`,
    source_url: 'https://example.com/perf-test',
    markdown_content: '# Performance Test\n\nThis payload validates extraction throughput.',
    extraction_config: {
      chunk_size: 400,
      chunk_overlap: 40,
      confidence_threshold: 0.6,
    },
  });

  const response = http.post(`${L2_URL}/v1/extract-and-ingest`, payload, {
    headers: defaultHeaders(s2sAuthHeaders),
    timeout: '90s',
  });

  const ok = check(response, {
    'L2 extract-and-ingest accepted': (r) => r.status >= 200 && r.status < 300,
    'L2 extract-and-ingest has job_id': (r) => {
      try {
        const body = JSON.parse(r.body || '{}');
        return !!body.job_id;
      } catch (_error) {
        return false;
      }
    },
  });

  l2Duration.add(response.timings.duration);
  l2Errors.add(!ok);
}

export function runL3HybridSearch() {
  const payload = JSON.stringify({ query: 'value optimization', limit: 10 });

  const response = http.post(`${L3_URL}/v1/search/hybrid`, payload, {
    headers: defaultHeaders(userAuthHeaders),
    timeout: '30s',
  });

  const ok = check(response, {
    'L3 hybrid search status is 2xx': (r) => r.status >= 200 && r.status < 300,
    'L3 hybrid search has results envelope': (r) => {
      try {
        const body = JSON.parse(r.body || '{}');
        return 'results' in body || 'entities' in body;
      } catch (_error) {
        return false;
      }
    },
  });

  l3Duration.add(response.timings.duration);
  l3Errors.add(!ok);
}

export function runL4WorkflowsActive() {
  const response = http.get(`${L4_URL}/workflows/active`, {
    headers: defaultHeaders(userAuthHeaders),
    timeout: '30s',
  });

  const ok = check(response, {
    'L4 active workflows status is 2xx': (r) => r.status >= 200 && r.status < 300,
  });

  l4Duration.add(response.timings.duration);
  l4Errors.add(!ok);
}
