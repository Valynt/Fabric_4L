import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  buildWebVitalsPayload,
  installWebVitals,
  sendWebVitalsMetric,
  shouldEnableWebVitals,
  type WebVitalsPayload,
} from "./web-vitals";

const originalLocation = window.location;

function setEnv(values: Record<string, string | boolean | undefined>) {
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined) {
      delete import.meta.env[key];
    } else {
      import.meta.env[key] = value;
    }
  }
}

function samplePayload(overrides: Partial<WebVitalsPayload> = {}): WebVitalsPayload {
  return {
    type: "web_vital",
    name: "LCP",
    value: 1234,
    rating: "good",
    delta: 12,
    id: "vital-1",
    navigationType: "navigate",
    timestamp: "2026-06-05T12:00:00.000Z",
    path: "/t/acme/accounts",
    appVersion: "test-version",
    environment: "production",
    ...overrides,
  };
}

describe("web vitals telemetry", () => {
  beforeEach(() => {
    setEnv({
      VITE_API_BASE: "/api/v1",
      VITE_APP_VERSION: "test-version",
      VITE_ENABLE_WEB_VITALS: undefined,
      VITE_ENVIRONMENT: "test",
      MODE: "test",
    });

    Object.defineProperty(window, "location", {
      configurable: true,
      value: new URL("https://app.fabric.test/t/acme/accounts?token=secret&tenantId=tenant-1"),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setEnv({
      VITE_API_BASE: undefined,
      VITE_APP_VERSION: undefined,
      VITE_ENABLE_WEB_VITALS: undefined,
      VITE_ENVIRONMENT: undefined,
      MODE: "test",
    });
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
    delete navigator.sendBeacon;
  });

  it("stays disabled in test and development unless explicitly enabled", () => {
    setEnv({ VITE_ENVIRONMENT: "development", VITE_ENABLE_WEB_VITALS: undefined });

    expect(shouldEnableWebVitals()).toBe(false);

    setEnv({ VITE_ENABLE_WEB_VITALS: "true" });

    expect(shouldEnableWebVitals()).toBe(true);
  });

  it("enables collection for production and staging", () => {
    setEnv({ VITE_ENVIRONMENT: "production" });
    expect(shouldEnableWebVitals()).toBe(true);

    setEnv({ VITE_ENVIRONMENT: "staging" });
    expect(shouldEnableWebVitals()).toBe(true);
  });

  it("registers core web vitals only when enabled", () => {
    const registrar = vi.fn();
    installWebVitals({ registrars: [registrar] });
    expect(registrar).not.toHaveBeenCalled();

    setEnv({ VITE_ENABLE_WEB_VITALS: "true" });
    installWebVitals({ registrars: [registrar] });

    expect(registrar).toHaveBeenCalledTimes(1);
    expect(registrar).toHaveBeenCalledWith(expect.any(Function));
  });

  it("builds a redacted metric payload with path-only location context", () => {
    const payload = buildWebVitalsPayload(
      {
        name: "INP",
        value: 90,
        rating: "good",
        delta: 30,
        id: "metric-id",
        navigationType: "reload",
        entries: [],
      },
      () => new Date("2026-06-05T12:00:00.000Z")
    );

    expect(payload).toEqual({
      type: "web_vital",
      name: "INP",
      value: 90,
      rating: "good",
      delta: 30,
      id: "metric-id",
      navigationType: "reload",
      timestamp: "2026-06-05T12:00:00.000Z",
      path: "/t/acme/accounts",
      appVersion: "test-version",
      environment: "test",
    });
    expect(JSON.stringify(payload)).not.toContain("token=secret");
    expect(JSON.stringify(payload)).not.toContain("tenant-1");
  });

  it("prefers sendBeacon for metric delivery", async () => {
    const sendBeacon = vi.fn(() => true);
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: sendBeacon,
    });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response());

    sendWebVitalsMetric(samplePayload());

    expect(sendBeacon).toHaveBeenCalledWith("/api/v1/telemetry/web-vitals", expect.any(Blob));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("uses non-blocking fetch fallback when sendBeacon is unavailable", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response());

    sendWebVitalsMetric(samplePayload());

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/telemetry/web-vitals",
      expect.objectContaining({
        method: "POST",
        keepalive: true,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  it("swallows metric export failures without breaking startup", () => {
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: () => {
        throw new Error("beacon unavailable");
      },
    });
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    expect(() => sendWebVitalsMetric(samplePayload())).not.toThrow();
    expect(warnSpy).toHaveBeenCalledWith(
      "[Fabric]",
      expect.stringContaining("[Fabric][web-vitals] Web vitals metric export failed"),
      expect.objectContaining({ feature: "web-vitals" })
    );
  });
});
