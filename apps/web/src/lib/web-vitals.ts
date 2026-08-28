/**
 * Web Vitals Tracking Module
 * ===========================
 * Initializes Core Web Vitals (CWV) collection using the `web-vitals` library.
 *
 * Sends metrics to the telemetry endpoint as a beacon (or fetch fallback)
 * for every CWV event.  Data is sampled and batched server-side; this
 * module is intentionally thin and dependency-free beyond `web-vitals`.
 *
 * DESIGN.md references:
 *   - Observability: client-side telemetry must use typed schemas
 *   - Performance: CWV budgets are enforced in CI (performance-budget.json)
 *
 * @module lib/web-vitals
 */

import { onCLS, onINP, onFCP, onLCP, onTTFB, type Metric } from "web-vitals";

/** Telemetry ingestion endpoint — relative so it works behind any reverse proxy. */
const VITALS_ENDPOINT = "/api/v1/telemetry/web-vitals";

/** Fields we ship to the telemetry API.  Kept explicit so the schema is greppable. */
interface VitalsPayload {
  name: string;
  value: number;
  rating: "good" | "needs-improvement" | "poor";
  delta: number;
  navigationType: string;
  timestamp: number;
  /** URL path at capture time (not full href to avoid leaking PII). */
  path: string;
  /** Session-scoped anonymous ID for grouping events without cookies. */
  sessionId: string;
}

let _sessionId: string | null = null;

function getSessionId(): string {
  if (_sessionId) return _sessionId;

  // Use sessionStorage so the ID persists across page navigations
  // but is scoped to the browser tab session.
  try {
    const stored = sessionStorage.getItem("__fabric_vitals_sid");
    if (stored) {
      _sessionId = stored;
      return stored;
    }
  } catch {
    // sessionStorage may be unavailable in private mode or sandboxed iframes
  }

  const sid = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  _sessionId = sid;
  try {
    sessionStorage.setItem("__fabric_vitals_sid", sid);
  } catch {
    // Best-effort
  }
  return sid;
}

/**
 * Serialize a web-vitals Metric into our telemetry payload.
 *
 * @param metric — Raw metric from the web-vitals library
 * @returns JSON-serializable payload
 */
export function serializeMetric(metric: Metric): VitalsPayload {
  return {
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    delta: metric.delta,
    navigationType: metric.navigationType,
    timestamp: Date.now(),
    path: window.location.pathname,
    sessionId: getSessionId(),
  };
}

/**
 * Deliver a payload to the telemetry endpoint.
 *
 * Prefers `navigator.sendBeacon` for reliability during page unload;
 * falls back to `fetch(..., keepalive: true)`.
 *
 * @param payload — JSON-serializable vitals payload
 */
export function sendToAnalytics(payload: VitalsPayload): void {
  const body = JSON.stringify(payload);

  // In test environments or when navigator is unavailable, noop.
  if (typeof navigator === "undefined") return;

  if (navigator.sendBeacon) {
    const ok = navigator.sendBeacon(VITALS_ENDPOINT, body);
    if (ok) return;
    // sendBeacon returns false when the beacon queue is full;
    // fall through to fetch.
  }

  fetch(VITALS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch((err) => {
    // Silently drop telemetry failures so we never break user experience.
    // eslint-disable-next-line no-console
    if (import.meta.env.DEV) {
      console.warn("[web-vitals] Telemetry delivery failed:", err);
    }
  });
}

/**
 * Handler compatible with the `web-vitals` library callback signature.
 * Wraps the metric, serializes it, and ships it.
 */
function onMetric(metric: Metric): void {
  const payload = serializeMetric(metric);
  sendToAnalytics(payload);
}

/**
 * Initialize Core Web Vitals collection.
 *
 * Call this once at app boot (e.g. in `main.tsx` after React root creation).
 * Idempotent — safe to call multiple times; subsequent calls are no-ops.
 */
let _initialized = false;

export function initWebVitals(): void {
  if (_initialized) return;
  _initialized = true;

  // Only collect in browser environments
  if (typeof window === "undefined") return;

  // Register each CWV listener.  `web-vitals` handles its own feature
  // detection and browser compatibility.
  onCLS(onMetric);
  onINP(onMetric);
  onFCP(onMetric);
  onLCP(onMetric);
  onTTFB(onMetric);
}

/** Reset the initialization guard and session cache.  Exposed for testing only. */
export function __resetInit(): void {
  _initialized = false;
  _sessionId = null;
}
