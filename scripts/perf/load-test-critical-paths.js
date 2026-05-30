import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up
    { duration: '5m', target: 50 },   // Steady state
    { duration: '2m', target: 100 },  // Peak
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% under 200ms
    http_req_failed: ['rate<0.01'],   // <1% errors
  },
};

const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

function authHeaders() {
  const headers = {};
  if (__ENV.TEST_TOKEN) {
    headers.Authorization = `Bearer ${__ENV.TEST_TOKEN}`;
  }
  if (__ENV.TEST_TENANT_ID) {
    headers['X-Tenant-ID'] = __ENV.TEST_TENANT_ID;
  }
  return headers;
}

export default function () {
  // Test 1: Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, {
    'health status is 200': (r) => r.status === 200,
    'health response time < 50ms': (r) => r.timings.duration < 50,
  });

  // Test 2: Auth'd API call
  const res = http.get(`${BASE_URL}/api/v1/tenants`, {
    headers: authHeaders(),
  });
  check(res, {
    'tenants status is 200': (r) => r.status === 200,
    'tenants response time < 200ms': (r) => r.timings.duration < 200,
  });

  sleep(1);
}

export function handleSummary(data) {
  const outputPath = __ENV.K6_SUMMARY_PATH || 'artifacts/performance/k6-critical-paths-summary.json';
  return {
    stdout: textSummary(data),
    [outputPath]: JSON.stringify(data, null, 2),
  };
}

function textSummary(data) {
  const duration = data.metrics.http_req_duration?.values?.['p(95)'];
  const failed = data.metrics.http_req_failed?.values?.rate;
  return [
    'Critical path performance summary',
    `p95 http_req_duration: ${duration ?? 'n/a'} ms`,
    `http_req_failed rate: ${failed ?? 'n/a'}`,
    '',
  ].join('\n');
}
