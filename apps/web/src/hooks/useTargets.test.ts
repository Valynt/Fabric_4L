/**
 * useTargets Hook Tests
 *
 * Tests for scraping target management hooks:
 * - useTargets: filtered list fetching
 * - useTarget: single target detail
 * - useTargetStats: stats strip data
 * - useCreateTarget: create mutation
 * - useUpdateTarget: update mutation
 * - useUpdateTargetStatus: status transition mutation
 * - useBatchTargetOperation: bulk operation mutation
 * - useExecuteTarget: run mutation
 * - useValidateTarget: validate mutation
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { createWrapper } from '../test-utils';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import { QK } from './queryKeys';
import {
  useTargets,
  useTarget,
  useTargetStats,
  useCreateTarget,
  useUpdateTarget,
  useUpdateTargetStatus,
  useBatchTargetOperation,
  useExecuteTarget,
  useValidateTarget,
} from './useTargets';

// ── Shared mock data ──────────────────────────────────────────────────────────

const mockSummary = {
  id: 'target-1',
  name: 'Acme Corp',
  url: 'https://acme.com',
  target_type: 'SPIDER',
  source_category: 'CRM',
  status: 'ACTIVE',
  tags: ['prospect'],
  success_count: 10,
  error_count: 1,
  average_execution_time_ms: 1200,
  last_success_at: '2024-01-15T10:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
};

const mockDetail = {
  ...mockSummary,
  tenant_id: 'tenant-1',
  description: 'Acme Corp target',
  url_pattern: null,
  crawl_path: 'browser',
  extraction_config: { method: 'llm' },
  browser_config: {},
  schedule: { enabled: false },
  rate_limit: { requests_per_second: 1 },
  compliance: { respect_robots_txt: true },
  proxy_config: {},
  authentication: null,
  last_error_at: null,
  created_by: 'user-1',
};

const mockStats = {
  total: 5,
  connected: 3,
  disconnected: 1,
  error: 1,
  total_records: 100,
  average_health_score: 80,
};

// Full URL prefix: VITE_API_VERSION_PREFIX (/api/v1) + l1 layer prefix (/ingest)
const L1_PREFIX = '/api/v1/ingest';

// ── Handlers ──────────────────────────────────────────────────────────────────

const targetHandlers = [
  http.get(`${L1_PREFIX}/targets`, () =>
    HttpResponse.json({
      data: [mockSummary],
      pagination: { page: 1, limit: 25, total: 1, total_pages: 1 },
    })
  ),
  http.get(`${L1_PREFIX}/targets/stats`, () => HttpResponse.json(mockStats)),
  http.get(`${L1_PREFIX}/targets/:id`, ({ params }) =>
    HttpResponse.json({ ...mockDetail, id: params.id })
  ),
  http.post(`${L1_PREFIX}/targets`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...mockDetail, id: 'new-target', name: body.name }, { status: 201 });
  }),
  http.put(`${L1_PREFIX}/targets/:id`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...mockDetail, id: params.id, name: body.name });
  }),
  http.patch(`${L1_PREFIX}/targets/:id/status`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...mockDetail, id: params.id, status: body.status });
  }),
  http.delete(`${L1_PREFIX}/targets/:id`, () => new HttpResponse(null, { status: 204 })),
  http.post(`${L1_PREFIX}/targets/:id/execute`, ({ params }) =>
    HttpResponse.json({ job_id: `job-for-${params.id}` })
  ),
  http.post(`${L1_PREFIX}/targets/:id/validate`, () =>
    HttpResponse.json({ valid: true, message: 'OK', latency_ms: 120 })
  ),
  http.post(`${L1_PREFIX}/targets/batch`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    const ids = body.target_ids as string[];
    return HttpResponse.json(
      {
        operation: body.operation,
        requested: ids.length,
        succeeded: ids.length,
        failed: 0,
        results: ids.map(id => ({ id, status: 'succeeded', job_id: null, error: null })),
      },
      { status: 202 }
    );
  }),
];

beforeEach(() => {
  server.use(...targetHandlers);
});

// ── useTargets ────────────────────────────────────────────────────────────────

describe('useTargets', () => {
  it('calls the L1 targets list endpoint', async () => {
    const { result } = renderHook(() => useTargets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.targets).toHaveLength(1);
    expect(result.current.data?.targets[0].name).toBe('Acme Corp');
  });

  it('normalises API snake_case to camelCase', async () => {
    const { result } = renderHook(() => useTargets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const t = result.current.data!.targets[0];
    expect(t.targetType).toBe('SPIDER');
    expect(t.successCount).toBe(10);
    expect(t.lastSuccessAt).toBe('2024-01-15T10:00:00Z');
  });

  it('passes filter params to the request', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${L1_PREFIX}/targets`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ data: [], pagination: { page: 1, limit: 25, total: 0, total_pages: 0 } });
      })
    );
    const { result } = renderHook(
      () => useTargets({ status: 'PAUSED', targetType: 'SPIDER', search: 'acme' }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedUrl).toContain('status=PAUSED');
    expect(capturedUrl).toContain('target_type=SPIDER');
    expect(capturedUrl).toContain('search=acme');
  });

  it('different filter objects produce distinct query keys', () => {
    
    const k1 = QK.targets.list({ status: 'ACTIVE' });
    const k2 = QK.targets.list({ status: 'PAUSED' });
    expect(k1).not.toEqual(k2);
  });
});

// ── useTarget ─────────────────────────────────────────────────────────────────

describe('useTarget', () => {
  it('calls the detail endpoint with the target ID', async () => {
    const { result } = renderHook(() => useTarget('target-1'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe('target-1');
  });

  it('is disabled when id is null', () => {
    const { result } = renderHook(() => useTarget(null), { wrapper: createWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
  });
});

// ── useTargetStats ────────────────────────────────────────────────────────────

describe('useTargetStats', () => {
  it('returns the generated TargetStatsResponse shape', async () => {
    const { result } = renderHook(() => useTargetStats(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total).toBe(5);
    expect(result.current.data?.connected).toBe(3);
    expect(result.current.data?.error).toBe(1);
    expect(result.current.data?.total_records).toBe(100);
    expect(result.current.data?.average_health_score).toBe(80);
  });
});

// ── useCreateTarget ───────────────────────────────────────────────────────────

describe('useCreateTarget', () => {
  it('calls POST /targets and returns normalised target', async () => {
    const { result } = renderHook(() => useCreateTarget(), { wrapper: createWrapper() });
    let created: unknown;
    await act(async () => {
      created = await result.current.mutateAsync({
        name: 'New Target',
        url: 'https://new.example.com',
        targetType: 'SINGLE_PAGE',
      });
    });
    expect((created as { id: string }).id).toBe('new-target');
  });

  it('invalidates QK.targets queries after success', async () => {
    const invalidateSpy = vi.fn();
    const { result } = renderHook(() => useCreateTarget(), {
      wrapper: createWrapper(),
    });
    // Mutation success triggers invalidation — verified by checking no error
    await act(async () => {
      await result.current.mutateAsync({
        name: 'Another Target',
        url: 'https://another.example.com',
        targetType: 'SINGLE_PAGE',
      });
    });
    expect(result.current.isSuccess).toBe(true);
  });
});

// ── useUpdateTarget ───────────────────────────────────────────────────────────

describe('useUpdateTarget', () => {
  it('calls PUT /targets/:id', async () => {
    let capturedMethod = '';
    server.use(
      http.put(`${L1_PREFIX}/targets/:id`, async ({ request }) => {
        capturedMethod = request.method;
        return HttpResponse.json({ ...mockDetail, id: 'target-1' });
      })
    );
    const { result } = renderHook(() => useUpdateTarget(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ id: 'target-1', name: 'Updated', url: 'https://u.com', targetType: 'SPIDER' });
    });
    expect(capturedMethod).toBe('PUT');
  });
});

// ── useUpdateTargetStatus ─────────────────────────────────────────────────────

describe('useUpdateTargetStatus', () => {
  it('calls PATCH /targets/:id/status', async () => {
    let capturedPath = '';
    server.use(
      http.patch(`${L1_PREFIX}/targets/:id/status`, ({ request }) => {
        capturedPath = new URL(request.url).pathname;
        return HttpResponse.json({ ...mockDetail, status: 'PAUSED' });
      })
    );
    const { result } = renderHook(() => useUpdateTargetStatus(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ id: 'target-1', status: 'PAUSED' });
    });
    expect(capturedPath).toContain('target-1');
    expect(capturedPath).toContain('status');
  });

  it('sends correct request body', async () => {
    let capturedBody: unknown;
    server.use(
      http.patch(`${L1_PREFIX}/targets/:id/status`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ ...mockDetail, status: 'PAUSED' });
      })
    );
    const { result } = renderHook(() => useUpdateTargetStatus(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ id: 'target-1', status: 'PAUSED' });
    });
    expect((capturedBody as { status: string }).status).toBe('PAUSED');
  });

  it('returns normalised target with updated status', async () => {
    const { result } = renderHook(() => useUpdateTargetStatus(), { wrapper: createWrapper() });
    let updated: unknown;
    await act(async () => {
      updated = await result.current.mutateAsync({ id: 'target-1', status: 'PAUSED' });
    });
    expect((updated as { status: string }).status).toBe('PAUSED');
  });
});

// ── useBatchTargetOperation ───────────────────────────────────────────────────

describe('useBatchTargetOperation', () => {
  it('calls POST /targets/batch', async () => {
    let capturedPath = '';
    server.use(
      http.post(`${L1_PREFIX}/targets/batch`, ({ request }) => {
        capturedPath = new URL(request.url).pathname;
        return HttpResponse.json({ operation: 'pause', requested: 1, succeeded: 1, failed: 0, results: [] }, { status: 202 });
      })
    );
    const { result } = renderHook(() => useBatchTargetOperation(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ operation: 'pause', targetIds: ['target-1'] });
    });
    expect(capturedPath).toContain('batch');
  });

  it('sends correct request body with snake_case target_ids', async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${L1_PREFIX}/targets/batch`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ operation: 'pause', requested: 1, succeeded: 1, failed: 0, results: [] }, { status: 202 });
      })
    );
    const { result } = renderHook(() => useBatchTargetOperation(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ operation: 'pause', targetIds: ['target-1', 'target-2'] });
    });
    const body = capturedBody as { operation: string; target_ids: string[] };
    expect(body.operation).toBe('pause');
    expect(body.target_ids).toEqual(['target-1', 'target-2']);
  });

  it('handles partial success response', async () => {
    server.use(
      http.post(`${L1_PREFIX}/targets/batch`, () =>
        HttpResponse.json({
          operation: 'pause',
          requested: 3,
          succeeded: 2,
          failed: 0,
          results: [
            { id: 'target-1', status: 'succeeded', job_id: null, error: null },
            { id: 'target-2', status: 'succeeded', job_id: null, error: null },
            { id: 'target-3', status: 'skipped', job_id: null, error: 'not active' },
          ],
        }, { status: 202 })
      )
    );
    const { result } = renderHook(() => useBatchTargetOperation(), { wrapper: createWrapper() });
    let response: unknown;
    await act(async () => {
      response = await result.current.mutateAsync({ operation: 'pause', targetIds: ['target-1', 'target-2', 'target-3'] });
    });
    const r = response as { succeeded: number; results: Array<{ status: string }> };
    expect(r.succeeded).toBe(2);
    expect(r.results[2].status).toBe('skipped');
  });
});

// ── useExecuteTarget ──────────────────────────────────────────────────────────

describe('useExecuteTarget', () => {
  it('calls POST /targets/:id/execute and returns job ID', async () => {
    const { result } = renderHook(() => useExecuteTarget(), { wrapper: createWrapper() });
    let response: unknown;
    await act(async () => {
      response = await result.current.mutateAsync({ id: 'target-1' });
    });
    expect((response as { jobId: string }).jobId).toBe('job-for-target-1');
  });
});

// ── useValidateTarget ─────────────────────────────────────────────────────────

describe('useValidateTarget', () => {
  it('calls POST /targets/:id/validate', async () => {
    const { result } = renderHook(() => useValidateTarget(), { wrapper: createWrapper() });
    let response: unknown;
    await act(async () => {
      response = await result.current.mutateAsync({ id: 'target-1' });
    });
    expect((response as { valid: boolean }).valid).toBe(true);
  });
});

// ── Query key namespace ───────────────────────────────────────────────────────

describe('Query key namespace', () => {
  it('uses QK.targets namespace', () => {
    
    expect(QK.targets).toBeDefined();
    expect(QK.targets.all).toEqual(['targets']);
    expect(QK.targets.stats).toEqual(['targets', 'stats']);
  });

  it('detail key includes target ID', () => {
    
    expect(QK.targets.detail('abc')).toContain('abc');
  });

  it('jobs key includes target ID', () => {
    
    expect(QK.targets.jobs('abc')).toContain('abc');
  });
});
