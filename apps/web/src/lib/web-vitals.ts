import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from "web-vitals";
import { createFeatureLogger } from "./telemetry";

type WebVitalName = "CLS" | "FCP" | "INP" | "LCP" | "TTFB";

export interface WebVitalsPayload {
  type: "web_vital";
  name: WebVitalName;
  value: number;
  rating: Metric["rating"];
  delta: number;
  id: string;
  navigationType: Metric["navigationType"];
  timestamp: string;
  path: string;
  appVersion: string;
  environment: string;
}

type MetricRegistrar = (callback: (metric: Metric) => void) => void;

export interface WebVitalsOptions {
  registrars?: MetricRegistrar[];
  now?: () => Date;
}

const DEFAULT_API_BASE = "/api/v1";
const DEFAULT_APP_VERSION = "unknown";
const DEFAULT_ENVIRONMENT = "development";
const ENABLED_ENVIRONMENTS = new Set(["production", "staging"]);
const logger = createFeatureLogger("web-vitals");

function getEnvironment(): string {
  return import.meta.env.VITE_ENVIRONMENT || import.meta.env.MODE || DEFAULT_ENVIRONMENT;
}

export function shouldEnableWebVitals(): boolean {
  if (import.meta.env.VITE_ENABLE_WEB_VITALS === "true") {
    return true;
  }

  return ENABLED_ENVIRONMENTS.has(getEnvironment());
}

function getPath(): string {
  if (typeof window === "undefined") {
    return "/";
  }

  return window.location.pathname || "/";
}

export function buildWebVitalsPayload(metric: Metric, now: () => Date = () => new Date()): WebVitalsPayload {
  return {
    type: "web_vital",
    name: metric.name as WebVitalName,
    value: metric.value,
    rating: metric.rating,
    delta: metric.delta,
    id: metric.id,
    navigationType: metric.navigationType,
    timestamp: now().toISOString(),
    path: getPath(),
    appVersion: import.meta.env.VITE_APP_VERSION || DEFAULT_APP_VERSION,
    environment: getEnvironment(),
  };
}

export function sendWebVitalsMetric(payload: WebVitalsPayload): void {
  try {
    const apiBase = import.meta.env.VITE_API_BASE || DEFAULT_API_BASE;
    const endpoint = `${apiBase}/telemetry/web-vitals`;
    const data = JSON.stringify(payload);

    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      navigator.sendBeacon(endpoint, new Blob([data], { type: "application/json" }));
      return;
    }

    if (typeof fetch === "function") {
      void fetch(endpoint, {
        method: "POST",
        body: data,
        keepalive: true,
        headers: { "Content-Type": "application/json" },
      }).catch(() => undefined);
    }
  } catch (error) {
    logger.warn("Web vitals metric export failed", {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

export function installWebVitals(options: WebVitalsOptions = {}): void {
  if (!shouldEnableWebVitals()) {
    return;
  }

  const registrars = options.registrars ?? [onCLS, onFCP, onINP, onLCP, onTTFB];
  const now = options.now ?? (() => new Date());
  const report = (metric: Metric) => sendWebVitalsMetric(buildWebVitalsPayload(metric, now));

  for (const registerMetric of registrars) {
    registerMetric(report);
  }
}
