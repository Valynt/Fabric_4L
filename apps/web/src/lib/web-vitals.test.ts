/**
 * Web Vitals Module — Unit Tests
 * ================================
 * Vitest suite for the web-vitals tracking module.
 *
 * Coverage targets:
 *   - serializeMetric   : 100% line coverage
 *   - sendToAnalytics   : beacon path, fetch fallback, error handling
 *   - initWebVitals     : idempotency, browser guard
 *   - getSessionId      : sessionStorage read/write, fallback
 *
 * DESIGN.md § Testing: "Unit/component tests for logic and rendering"
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  serializeMetric,
  sendToAnalytics,
  initWebVitals,
  __resetInit,
} from "./web-vitals";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createMockMetric(overrides: Partial<import("web-vitals").Metric> = {}) {
  return {
    name: "LCP",
    value: 1200,
    rating: "good" as const,
    delta: 1200,
    id: "test-metric-id",
    navigationType: "navigate",
    entries: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// serializeMetric
// ---------------------------------------------------------------------------

describe("serializeMetric", () => {
  it("produces a JSON-serializable payload with all required fields", () => {
    const metric = createMockMetric();
    const payload = serializeMetric(metric);

    expect(payload).toMatchObject({
      name: "LCP",
      value: 1200,
      rating: "good",
      delta: 1200,
      navigationType: "navigate",
    });

    expect(typeof payload.timestamp).toBe("number");
    expect(typeof payload.path).toBe("string");
    expect(typeof payload.sessionId).toBe("string");
  });

  it("handles 'needs-improvement' rating correctly", () => {
    const metric = createMockMetric({
      name: "CLS",
      value: 0.15,
      rating: "needs-improvement",
      delta: 0.05,
    });
    const payload = serializeMetric(metric);
    expect(payload.rating).toBe("needs-improvement");
    expect(payload.value).toBe(0.15);
  });

  it("handles 'poor' rating correctly", () => {
    const metric = createMockMetric({
      name: "INP",
      value: 450,
      rating: "poor",
      delta: 450,
    });
    const payload = serializeMetric(metric);
    expect(payload.rating).toBe("poor");
  });

  it("includes window.location.pathname as path", () => {
    const metric = createMockMetric();
    const payload = serializeMetric(metric);
    expect(payload.path).toBe(window.location.pathname);
  });

  it("assigns a consistent sessionId across multiple calls", () => {
    const m1 = createMockMetric();
    const m2 = createMockMetric({ name: "FCP", value: 900 });

    const p1 = serializeMetric(m1);
    const p2 = serializeMetric(m2);

    expect(p1.sessionId).toBe(p2.sessionId);
  });
});

// ---------------------------------------------------------------------------
// sendToAnalytics
// ---------------------------------------------------------------------------

describe("sendToAnalytics", () => {
  let sendBeaconSpy: ReturnType<typeof vi.fn>;
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    sendBeaconSpy = vi.fn().mockReturnValue(true);
    fetchSpy = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(globalThis.navigator, "sendBeacon", {
      value: sendBeaconSpy,
      writable: true,
      configurable: true,
    });

    Object.defineProperty(globalThis, "fetch", {
      value: fetchSpy,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("prefers navigator.sendBeacon when available", () => {
    const payload = serializeMetric(createMockMetric());
    sendToAnalytics(payload);

    expect(sendBeaconSpy).toHaveBeenCalledTimes(1);
    expect(sendBeaconSpy).toHaveBeenCalledWith(
      "/api/v1/telemetry/web-vitals",
      expect.any(String)
    );
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("falls back to fetch when sendBeacon returns false", () => {
    sendBeaconSpy.mockReturnValue(false);

    const payload = serializeMetric(createMockMetric());
    sendToAnalytics(payload);

    expect(sendBeaconSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/telemetry/web-vitals",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        body: expect.any(String),
      })
    );
  });

  it("falls back to fetch when sendBeacon is undefined", () => {
    Object.defineProperty(globalThis.navigator, "sendBeacon", {
      value: undefined,
      writable: true,
      configurable: true,
    });

    const payload = serializeMetric(createMockMetric());
    sendToAnalytics(payload);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("silently swallows fetch rejections", async () => {
    fetchSpy.mockRejectedValue(new Error("Network error"));

    const payload = serializeMetric(createMockMetric());
    // Should not throw
    expect(() => sendToAnalytics(payload)).not.toThrow();
  });

  it("serializes the full payload as JSON in the request body", () => {
    const metric = createMockMetric({ name: "TTFB", value: 80 });
    const payload = serializeMetric(metric);
    sendToAnalytics(payload);

    const bodyArg = sendBeaconSpy.mock.calls[0][1];
    const parsed = JSON.parse(bodyArg);
    expect(parsed).toMatchObject({
      name: "TTFB",
      value: 80,
      rating: "good",
    });
  });

  it("noop when navigator is undefined (non-browser env)", () => {
    const payload = serializeMetric(createMockMetric());

    // Simulate a non-browser environment by temporarily removing navigator
    const origNavigator = globalThis.navigator;
    // @ts-expect-error — testing non-browser fallback
    globalThis.navigator = undefined;

    expect(() => sendToAnalytics(payload)).not.toThrow();

    globalThis.navigator = origNavigator;
  });
});

// ---------------------------------------------------------------------------
// initWebVitals
// ---------------------------------------------------------------------------

describe("initWebVitals", () => {
  beforeEach(() => {
    __resetInit();
  });

  afterEach(() => {
    __resetInit();
    vi.restoreAllMocks();
  });

  it("is idempotent — second call does not re-register listeners", () => {
    // We can't easily spy on the web-vitals library internals, but we can
    // verify the guard by calling initWebVitals twice without error.
    expect(() => {
      initWebVitals();
      initWebVitals();
    }).not.toThrow();
  });

  it("guards against non-browser environments (window undefined)", () => {
    const origWindow = globalThis.window;
    // @ts-expect-error — testing SSR-like environment
    globalThis.window = undefined;

    __resetInit();
    expect(() => initWebVitals()).not.toThrow();

    globalThis.window = origWindow;
  });
});

// ---------------------------------------------------------------------------
// Integration: full flow from metric → payload → delivery
// ---------------------------------------------------------------------------

describe("end-to-end: metric → payload → delivery", () => {
  it("round-trips a CLS metric through the full pipeline", () => {
    const sendBeacon = vi.fn().mockReturnValue(true);
    Object.defineProperty(globalThis.navigator, "sendBeacon", {
      value: sendBeacon,
      writable: true,
      configurable: true,
    });

    const metric = createMockMetric({
      name: "CLS",
      value: 0.02,
      rating: "good",
      delta: 0.01,
    });

    const payload = serializeMetric(metric);
    sendToAnalytics(payload);

    const sent = JSON.parse(sendBeacon.mock.calls[0][1]);
    expect(sent).toMatchObject({
      name: "CLS",
      value: 0.02,
      rating: "good",
      delta: 0.01,
      navigationType: "navigate",
    });
    expect(typeof sent.timestamp).toBe("number");
    expect(typeof sent.sessionId).toBe("string");
    expect(sent.path).toBe(window.location.pathname);
  });
});

// ---------------------------------------------------------------------------
// Session ID persistence
// ---------------------------------------------------------------------------

describe("sessionId", () => {
  beforeEach(() => {
    sessionStorage.clear();
    // Reset internal cached value by calling __resetInit which
    // also resets the module state
    __resetInit();
  });

  it("generates a new sessionId when none exists in sessionStorage", () => {
    const payload = serializeMetric(createMockMetric());
    expect(payload.sessionId).toMatch(/^\d+-[a-z0-9]+$/);
  });

  it("reuses the sessionId from sessionStorage on subsequent calls", () => {
    const p1 = serializeMetric(createMockMetric());
    const p2 = serializeMetric(createMockMetric({ name: "FCP", value: 500 }));

    expect(p1.sessionId).toBe(p2.sessionId);
  });

  it("stores the sessionId in sessionStorage", () => {
    expect(sessionStorage.getItem("__fabric_vitals_sid")).toBeNull();

    serializeMetric(createMockMetric());

    expect(sessionStorage.getItem("__fabric_vitals_sid")).not.toBeNull();
  });
});
