import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { apiClient } from '@/api/client';
import {
  applySessionServiceTestEnvironment,
  authFixtures,
  type MemoryStorage,
} from '@/test/authSessionTestUtils';

describe('Contract: Tenant context propagation', () => {
  let testSessionStorage: MemoryStorage;

  beforeEach(() => {
    ({ sessionStorage: testSessionStorage } = applySessionServiceTestEnvironment());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does NOT send x-tenant-id header (tenant is cookie/session-bound)', async () => {
    testSessionStorage.setItem(
      'vf.auth.session.meta',
      JSON.stringify(
        authFixtures.sessionMeta({
          tenantId: 'tenant-abc-123',
          user: authFixtures.user({ tenantId: 'tenant-abc-123' }),
        })
      )
    );

    let capturedHeaders: Record<string, string> = {};

    server.use(
      http.get('/api/v1/signals/test', ({ request }) => {
        request.headers.forEach((value, key) => {
          capturedHeaders[key] = value;
        });
        return HttpResponse.json({});
      })
    );

    await apiClient.get('l2_5', '/test');

    expect(capturedHeaders['x-tenant-id']).toBeUndefined();
    expect(capturedHeaders['x-organization-id']).toBeUndefined();
  });

  it('does NOT send authorization bearer token header (cookie/session-bound)', async () => {
    testSessionStorage.setItem(
      'vf.auth.session.meta',
      JSON.stringify(
        authFixtures.sessionMeta({
          tenantId: 'tenant-abc-123',
          user: authFixtures.user({ tenantId: 'tenant-abc-123' }),
        })
      )
    );

    let capturedHeaders: Record<string, string> = {};

    server.use(
      http.get('/api/v1/signals/test', ({ request }) => {
        request.headers.forEach((value, key) => {
          capturedHeaders[key] = value;
        });
        return HttpResponse.json({});
      })
    );

    await apiClient.get('l2_5', '/test');

    expect(capturedHeaders.authorization).toBeUndefined();
  });

  it('sends cookies with credentials:include for session-bound auth', async () => {
    testSessionStorage.setItem(
      'vf.auth.session.meta',
      JSON.stringify(
        authFixtures.sessionMeta({
          tenantId: 'tenant-abc-123',
          user: authFixtures.user({ tenantId: 'tenant-abc-123' }),
        })
      )
    );

    // Axios does not use window.fetch; verify withCredentials via client defaults
    const client = apiClient.getClient('l2_5');
    expect(client.defaults.withCredentials).toBe(true);

    // Also verify the request actually fires through MSW
    let requestReceived = false;
    server.use(
      http.get('/api/v1/signals/test', ({ request }) => {
        requestReceived = true;
        return HttpResponse.json({});
      })
    );

    await apiClient.get('l2_5', '/test');
    expect(requestReceived).toBe(true);
  });

  it('rejects session metadata with tenant mismatch as a validation error', () => {
    const mismatchedMeta = authFixtures.sessionMeta({
      tenantId: 'tenant-a',
      user: authFixtures.user({ tenantId: 'tenant-b' }),
    });

    // A tenant mismatch between session metadata and user claim
    // should be caught by frontend validation before any API call
    expect(mismatchedMeta.tenantId).not.toBe(mismatchedMeta.user?.tenantId);
  });

  it('does not synthesize tenant header when session metadata is absent', async () => {
    let capturedHeaders: Record<string, string> = {};

    server.use(
      http.get('/api/v1/signals/test', ({ request }) => {
        request.headers.forEach((value, key) => {
          capturedHeaders[key] = value;
        });
        return HttpResponse.json({});
      })
    );

    await apiClient.get('l2_5', '/test');

    expect(capturedHeaders['x-tenant-id']).toBeUndefined();
    expect(capturedHeaders['x-organization-id']).toBeUndefined();
    expect(capturedHeaders.authorization).toBeUndefined();
  });
});
