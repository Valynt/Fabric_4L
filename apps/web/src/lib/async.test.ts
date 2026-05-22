import { describe, it, expect, vi } from 'vitest';
import * as telemetry from './telemetry';
import { safeAsync } from './async';

describe('safeAsync', () => {
  it('reports rejected fire-and-forget promises to telemetry', async () => {
    const spy = vi.spyOn(telemetry, 'logError').mockImplementation(() => {});
    safeAsync(Promise.reject(new Error('boom')), 'unit.test');
    await Promise.resolve();
    expect(spy).toHaveBeenCalledWith('Unhandled async task failure', expect.objectContaining({ scope: 'unit.test', error: 'boom' }));
  });
});
