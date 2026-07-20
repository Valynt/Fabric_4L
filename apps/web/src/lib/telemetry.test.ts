import { describe, it, expect, vi, afterEach } from 'vitest';
import { createFeatureLogger, sendToTelemetryBackend } from './telemetry';

describe('createFeatureLogger', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('enriches log context with feature defaults', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const logger = createFeatureLogger('auth-session', {
      route: '/login',
      tenantId: 'tenant-1',
    });

    logger.error('Session restore failed', { authPhase: 'restore' });

    expect(errorSpy).toHaveBeenCalledWith(
      '[Fabric]',
      expect.stringContaining('[Fabric][auth-session] Session restore failed'),
      expect.objectContaining({
        feature: 'auth-session',
        route: '/login',
        tenantId: 'tenant-1',
        authPhase: 'restore',
      })
    );
  });
});

describe('sendToTelemetryBackend delivery', () => {
  const originalSendBeacon = Object.getOwnPropertyDescriptor(navigator, 'sendBeacon');

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    if (originalSendBeacon) {
      Object.defineProperty(navigator, 'sendBeacon', originalSendBeacon);
    } else {
      Reflect.deleteProperty(navigator, 'sendBeacon');
    }
  });

  function setSendBeacon(value: unknown): void {
    Object.defineProperty(navigator, 'sendBeacon', {
      value,
      configurable: true,
      writable: true,
    });
  }

  it('delivers error reports via sendBeacon when available', () => {
    const sendBeacon = vi.fn<typeof navigator.sendBeacon>(() => true);
    setSendBeacon(sendBeacon);
    const fetchSpy = vi.fn<typeof fetch>(() => Promise.resolve(new Response(null)));
    vi.stubGlobal('fetch', fetchSpy);

    sendToTelemetryBackend('exception', {
      message: 'boom',
      name: 'Error',
      context: { traceId: 'trace-1' },
    });

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    const [url, body] = sendBeacon.mock.calls[0];
    expect(String(url)).toBe('/api/v1/telemetry/error');
    expect(body).toBeInstanceOf(Blob);
    if (body instanceof Blob) {
      expect(body.type).toBe('application/json');
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('falls back to keepalive fetch without blocking when sendBeacon is unavailable', () => {
    setSendBeacon(undefined);
    const fetchSpy = vi.fn<typeof fetch>(() => Promise.resolve(new Response(null)));
    vi.stubGlobal('fetch', fetchSpy);

    sendToTelemetryBackend('exception', {
      message: 'boom',
      name: 'Error',
      context: { traceId: 'trace-1' },
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toBe('/api/v1/telemetry/error');
    expect(init).toMatchObject({
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
    });
    const body = init?.body;
    expect(typeof body).toBe('string');
    const payload = JSON.parse(typeof body === 'string' ? body : '') as Record<string, unknown>;
    expect(payload.type).toBe('exception');
    expect(payload.message).toBe('boom');
    expect(payload.context).toEqual({ traceId: 'trace-1' });
  });

  it('swallows fetch rejections so error reporting never throws', async () => {
    setSendBeacon(undefined);
    const fetchSpy = vi.fn<typeof fetch>(() => Promise.reject(new Error('network down')));
    vi.stubGlobal('fetch', fetchSpy);

    expect(() => sendToTelemetryBackend('message', { message: 'boom' })).not.toThrow();
    // Allow the rejection handler to settle before the test ends.
    await Promise.resolve();
  });
});
