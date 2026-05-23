import { describe, it, expect, vi } from 'vitest';
import * as telemetry from './telemetry';
import { safeAsync } from './async';

describe('safeAsync', () => {
  it('reports rejected fire-and-forget promises to telemetry', async () => {
    const spy = vi.spyOn(telemetry, 'captureException').mockImplementation(() => {});
    safeAsync(Promise.reject(new Error('boom')), 'unit.test');
    await Promise.resolve();
    expect(spy).toHaveBeenCalledWith(expect.any(Error), expect.objectContaining({ scope: 'unit.test' }));
  });

  it('reports non-error promise rejections to telemetry logger', async () => {
    const spy = vi.spyOn(telemetry, 'logError').mockImplementation(() => {});
    safeAsync(Promise.reject('boom'), 'unit.test.non-error');
    await Promise.resolve();
    expect(spy).toHaveBeenCalledWith(
      'Unhandled async task failure',
      expect.objectContaining({ scope: 'unit.test.non-error', error: 'boom' })
    );
  });
});
