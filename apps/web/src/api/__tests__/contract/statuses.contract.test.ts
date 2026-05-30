import { describe, expect, it } from 'vitest';
import type { l3 } from '@/api/generated';
import {
  FORMULA_VERSION_STATUSES,
  L3_BENCHMARK_STATUSES,
  L3_ENTITY_STATUSES,
  L3_HEALTH_STATUSES,
  L3_INGEST_STATUSES,
  L3_SYNC_STATUSES,
} from '@/api/statuses';
import { ServiceStatusSchema } from '@/lib/schemas/healthMonitor';
import { ApiErrorSchema, assertSchema } from './_helpers';


describe('status contract alignment', () => {
  it('keeps Layer 3 status sets aligned with generated OpenAPI types', () => {
    const health: l3.components['schemas']['DependencyStatus']['status'][] = [...L3_HEALTH_STATUSES];
    const ingest: l3.components['schemas']['IngestResponse']['status'][] = [...L3_INGEST_STATUSES];
    const sync: NonNullable<l3.components['schemas']['SyncStatusResponse']['status']>[] = [...L3_SYNC_STATUSES];
    const entity: l3.components['schemas']['Entity']['status'][] = [...L3_ENTITY_STATUSES];
    const benchmark: l3.components['schemas']['BenchmarkPolicy']['status'][] = [...L3_BENCHMARK_STATUSES];

    expect(health).toEqual(['healthy', 'unhealthy', 'degraded']);
    expect(ingest).toEqual(['success', 'partial', 'failed']);
    expect(sync).toEqual(['synced', 'pending', 'failed', 'outdated']);
    expect(entity).toEqual(['validated', 'pending', 'draft', 'deprecated']);
    expect(benchmark).toEqual(['active', 'draft', 'deprecated']);
  });

  it('keeps frontend schemas and hook-specific statuses aligned', () => {
    expect(ServiceStatusSchema.safeParse('healthy').success).toBe(true);
    expect(ServiceStatusSchema.safeParse('degraded').success).toBe(true);
    expect(ServiceStatusSchema.safeParse('unhealthy').success).toBe(true);

    expect(FORMULA_VERSION_STATUSES).toEqual([
      'draft',
      'under_review',
      'approved',
      'active',
      'deprecated',
      'retired',
    ]);
  });
});


describe('Contract: statuses auth failures', () => {
  it('validates canonical status API auth error envelope', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { code: 'AUTHENTICATION_ERROR', message: 'Authentication required', request_id: 'trace-status-401' } },
      'Status auth error envelope'
    );
  });
});
