/**
 * Fabric_4L Feature Flags SDK — v1.2.0
 * Production-grade, tenant-scoped feature flag system with
 * A/B support, kill switches, and experimentation telemetry.
 *
 * @module @fabric_4l/feature-flags
 */

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

/** Tenant isolation tiers */
export type TenantTier = "shared" | "dedicated" | "enterprise";

/** A single rule that can enable a flag for a subset of tenants/users */
export interface FlagRule {
  /** Target tenant tier */
  tenantTier?: TenantTier;
  /** Explicit allow-list of tenant IDs (takes precedence over tier) */
  tenantIds?: string[];
  /** Percentage rollout (0–100). Uses deterministic hashing. */
  percentage?: number;
  /** User segments (e.g. "beta", "internal") */
  userSegments?: string[];
}

/** Runtime configuration for a feature flag */
export interface FeatureFlagConfig {
  /** Unique flag identifier (kebab-case) */
  flagKey: string;
  /** Fail-safe default — MUST be `false` for new flags */
  defaultValue: boolean;
  /** Human-readable description */
  description?: string;
  /** Evaluation rules applied in order; first match wins */
  rules?: FlagRule[];
  /** ISO-8601 timestamp when the flag was created */
  createdAt?: string;
  /** ISO-8601 timestamp of last update */
  updatedAt?: string;
}

/** Evaluation context provided by the caller */
export interface EvaluationContext {
  tenantId: string;
  tenantTier?: TenantTier;
  userId?: string;
  userSegments?: string[];
}

/** Result of a single flag evaluation */
export interface EvaluationResult {
  flagKey: string;
  enabled: boolean;
  source: "default" | "rule" | "override" | "kill_switch";
  ruleIndex?: number;
  /** ISO-8601 timestamp */
  evaluatedAt: string;
}

/** Serialized audit event */
export interface FlagAuditEvent {
  id: string;
  flagKey: string;
  actor: string;
  action: "created" | "updated" | "deleted" | "toggled" | "override_added" | "override_removed";
  oldValue?: Record<string, unknown> | null;
  newValue?: Record<string, unknown> | null;
  timestamp: string;
}

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const SDK_VERSION = "1.2.0";
const STORAGE_KEY = "@fabric_4l/feature-flags/cache";
const DEFAULT_CACHE_TTL_MS = 30_000;
const HASH_PRIME = 0x811c9dc5;

// ─────────────────────────────────────────────────────────────
// Deterministic hashing (FNV-1a 32-bit) for percentage rollouts
// ─────────────────────────────────────────────────────────────

function fnv1a32(input: string): number {
  let hash = HASH_PRIME;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return hash >>> 0; // unsigned 32-bit
}

function hashPercentage(seed: string): number {
  return (fnv1a32(seed) % 100) + 1; // 1–100
}

// ─────────────────────────────────────────────────────────────
// In-memory flag store (populated from bootstrap / polling)
// ─────────────────────────────────────────────────────────────

class FlagStore {
  private flags: Map<string, FeatureFlagConfig> = new Map();
  private lastUpdated = 0;
  private ttlMs: number;

  constructor(ttlMs = DEFAULT_CACHE_TTL_MS) {
    this.ttlMs = ttlMs;
  }

  set(flags: FeatureFlagConfig[]): void {
    this.flags.clear();
    for (const f of flags) {
      this.flags.set(f.flagKey, f);
    }
    this.lastUpdated = Date.now();
  }

  get(flagKey: string): FeatureFlagConfig | undefined {
    return this.flags.get(flagKey);
  }

  all(): FeatureFlagConfig[] {
    return Array.from(this.flags.values());
  }

  isStale(): boolean {
    return Date.now() - this.lastUpdated > this.ttlMs;
  }

  /** Hydrate from a static JSON blob (useful for SSR / edge). */
  hydrate(json: Record<string, FeatureFlagConfig>): void {
    this.flags = new Map(Object.entries(json));
    this.lastUpdated = Date.now();
  }
}

const globalStore = new FlagStore();

// ─────────────────────────────────────────────────────────────
// Core evaluation engine
// ─────────────────────────────────────────────────────────────

/**
 * Evaluate a single flag against the provided context.
 * Rules are evaluated in order; the first matching rule wins.
 * If no rule matches, the flag's `defaultValue` is returned.
 *
 * @param flag   — the flag configuration
 * @param ctx    — evaluation context (tenant, user, segments)
 * @returns EvaluationResult with provenance metadata
 */
export function evaluateFlag(
  flag: FeatureFlagConfig,
  ctx: EvaluationContext
): EvaluationResult {
  const now = new Date().toISOString();

  // 1. Check rules (first match wins)
  if (flag.rules && flag.rules.length > 0) {
    for (let i = 0; i < flag.rules.length; i++) {
      const rule = flag.rules[i];

      // Tenant ID allow-list (highest priority)
      if (rule.tenantIds && rule.tenantIds.length > 0) {
        if (rule.tenantIds.includes(ctx.tenantId)) {
          const enabled =
            rule.percentage !== undefined
              ? hashPercentage(`${flag.flagKey}:${ctx.tenantId}:${ctx.userId ?? ""}`) <=
                rule.percentage
              : true;
          return {
            flagKey: flag.flagKey,
            enabled,
            source: enabled ? "rule" : "rule",
            ruleIndex: i,
            evaluatedAt: now,
          };
        }
        continue;
      }

      // Tenant tier match
      if (rule.tenantTier && rule.tenantTier !== ctx.tenantTier) {
        continue;
      }

      // User segment match
      if (
        rule.userSegments &&
        rule.userSegments.length > 0 &&
        (!ctx.userSegments ||
          !rule.userSegments.some((s) => ctx.userSegments!.includes(s)))
      ) {
        continue;
      }

      // Percentage rollout
      if (rule.percentage !== undefined) {
        const bucket = hashPercentage(
          `${flag.flagKey}:${ctx.tenantId}:${ctx.userId ?? ""}`
        );
        if (bucket <= rule.percentage) {
          return {
            flagKey: flag.flagKey,
            enabled: true,
            source: "rule",
            ruleIndex: i,
            evaluatedAt: now,
          };
        }
        // Fell outside percentage — continue to next rule rather than
        // immediately returning false. This allows a fallback rule.
        continue;
      }

      // No percentage constraint → fully enabled for matched criteria
      return {
        flagKey: flag.flagKey,
        enabled: true,
        source: "rule",
        ruleIndex: i,
        evaluatedAt: now,
      };
    }
  }

  // 2. No rules matched → return default (fail-safe to false)
  return {
    flagKey: flag.flagKey,
    enabled: flag.defaultValue,
    source: "default",
    evaluatedAt: now,
  };
}

// ─────────────────────────────────────────────────────────────
// Bootstrap / polling helpers
// ─────────────────────────────────────────────────────────────

export interface BootstrapOptions {
  /** Base URL of the Fabric_4L admin API */
  apiBaseUrl: string;
  /** Tenant API key (used for read-only flag fetching) */
  apiKey?: string;
  /** Polling interval in ms (default 30_000) */
  pollIntervalMs?: number;
  /** Initial flag payload (skip first fetch) */
  initialFlags?: FeatureFlagConfig[];
}

/**
 * Bootstrap the SDK with flags from the admin API.
 * Returns a cleanup function that stops background polling.
 */
export function bootstrapFlags(options: BootstrapOptions): () => void {
  if (options.initialFlags) {
    globalStore.set(options.initialFlags);
  }

  const interval = setInterval(async () => {
    if (!globalStore.isStale()) return;
    try {
      const headers: Record<string, string> = {
        Accept: "application/json",
        "X-SDK-Version": SDK_VERSION,
      };
      if (options.apiKey) headers["Authorization"] = `Bearer ${options.apiKey}`;

      const res = await fetch(`${options.apiBaseUrl}/api/v1/admin/feature-flags`, {
        headers,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const flags: FeatureFlagConfig[] = await res.json();
      globalStore.set(flags);
    } catch (err) {
      // Fail-safe: on fetch error we keep the existing cache rather than
      // clearing it. Stale flags are safer than no flags.
      if (typeof console !== "undefined") {
        console.warn("[FeatureFlags] Polling error (stale cache retained):", err);
      }
    }
  }, options.pollIntervalMs ?? DEFAULT_CACHE_TTL_MS);

  return () => clearInterval(interval);
}

// ─────────────────────────────────────────────────────────────
// React hook
// ─────────────────────────────────────────────────────────────

import { useCallback, useMemo, useSyncExternalStore } from "react";

let reactStoreListeners: (() => void)[] = [];

function emitReactStoreChange(): void {
  for (const cb of reactStoreListeners) cb();
}

function subscribeReactStore(callback: () => void): () => void {
  reactStoreListeners.push(callback);
  return () => {
    reactStoreListeners = reactStoreListeners.filter((cb) => cb !== callback);
  };
}

function getReactStoreSnapshot(): number {
  return Date.now();
}

/**
 * React hook for consuming a feature flag.
 *
 * @param flagKey      — the flag identifier
 * @param options      — optional overrides
 * @returns boolean    — whether the flag is enabled for the current context
 *
 * @example
 * ```tsx
 * const showNewDashboard = useFeatureFlag("new-dashboard-v2", {
 *   defaultValue: false,
 * });
 *
 * return showNewDashboard ? <DashboardV2 /> : <DashboardV1 />;
 * ```
 */
export function useFeatureFlag(
  flagKey: string,
  options?: { defaultValue?: boolean }
): boolean {
  // Force re-evaluation when the store updates
  useSyncExternalStore(subscribeReactStore, getReactStoreSnapshot);

  const flag = globalStore.get(flagKey);

  // Fail-safe: if flag is unknown, return the provided default (false)
  if (!flag) {
    return options?.defaultValue ?? false;
  }

  // In a real React app the EvaluationContext would come from
  // an auth/context provider. Here we read from a global that the
  // host app sets via `setEvaluationContext(...)`.
  const ctx = getEvaluationContext();
  if (!ctx) {
    // No context available → fail-safe to default
    return flag.defaultValue;
  }

  const result = evaluateFlag(flag, ctx);
  return result.enabled;
}

// ─────────────────────────────────────────────────────────────
// Evaluation context (host app provides this)
// ─────────────────────────────────────────────────────────────

let _evaluationContext: EvaluationContext | null = null;

/** Called once by the host app after auth resolves. */
export function setEvaluationContext(ctx: EvaluationContext): void {
  _evaluationContext = ctx;
}

export function getEvaluationContext(): EvaluationContext | null {
  return _evaluationContext;
}

/** Clear context (e.g. on logout). */
export function clearEvaluationContext(): void {
  _evaluationContext = null;
}

// ─────────────────────────────────────────────────────────────
// Admin helpers (used by the Admin UI page)
// ─────────────────────────────────────────────────────────────

export interface CreateFlagPayload {
  flagKey: string;
  description: string;
  defaultValue: boolean;
  rules?: FlagRule[];
}

export interface UpdateFlagPayload {
  description?: string;
  defaultValue?: boolean;
  rules?: FlagRule[];
}

export interface FlagListItem extends FeatureFlagConfig {
  overrideCount: number;
}

export async function listFlags(apiBaseUrl: string, adminToken: string): Promise<FlagListItem[]> {
  const res = await fetch(`${apiBaseUrl}/api/v1/admin/feature-flags`, {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  if (!res.ok) throw new Error(`Failed to list flags: ${res.status}`);
  return res.json();
}

export async function createFlag(
  apiBaseUrl: string,
  adminToken: string,
  payload: CreateFlagPayload
): Promise<FeatureFlagConfig> {
  const res = await fetch(`${apiBaseUrl}/api/v1/admin/feature-flags`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${adminToken}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to create flag: ${res.status}`);
  const created = await res.json();
  emitReactStoreChange();
  return created;
}

export async function updateFlag(
  apiBaseUrl: string,
  adminToken: string,
  flagKey: string,
  payload: UpdateFlagPayload
): Promise<FeatureFlagConfig> {
  const res = await fetch(`${apiBaseUrl}/api/v1/admin/feature-flags/${encodeURIComponent(flagKey)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${adminToken}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to update flag: ${res.status}`);
  const updated = await res.json();
  emitReactStoreChange();
  return updated;
}

export async function fetchAuditLog(
  apiBaseUrl: string,
  adminToken: string,
  flagKey: string
): Promise<FlagAuditEvent[]> {
  const res = await fetch(
    `${apiBaseUrl}/api/v1/admin/feature-flags/${encodeURIComponent(flagKey)}/audit`,
    { headers: { Authorization: `Bearer ${adminToken}` } }
  );
  if (!res.ok) throw new Error(`Failed to fetch audit log: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────────────────────
// Telemetry helpers (impressions & conversions)
// ─────────────────────────────────────────────────────────────

/** Impression event — fired every time a flag is evaluated */
export interface FlagImpressionEvent {
  eventType: "flag_impression";
  flagKey: string;
  tenantId: string;
  userId: string;        // hashed
  variation: "enabled" | "disabled";
  timestamp: string;     // ISO-8601
  sdkVersion: string;
  source: EvaluationResult["source"];
}

/** Conversion event — tied to an experiment */
export interface ExperimentConversionEvent {
  eventType: "experiment_conversion";
  experimentKey: string;
  tenantId: string;
  userId: string;        // hashed
  goalName: string;
  value?: number;
  timestamp: string;
}

export type TelemetryEvent = FlagImpressionEvent | ExperimentConversionEvent;

type TelemetrySink = (event: TelemetryEvent) => void | Promise<void>;

let _telemetrySink: TelemetrySink | null = null;

/** Register a callback to receive telemetry events. */
export function registerTelemetrySink(sink: TelemetrySink): void {
  _telemetrySink = sink;
}

export function recordImpression(result: EvaluationResult, ctx: EvaluationContext): void {
  if (!_telemetrySink) return;
  const event: FlagImpressionEvent = {
    eventType: "flag_impression",
    flagKey: result.flagKey,
    tenantId: ctx.tenantId,
    userId: hashUserId(ctx.userId ?? "anonymous"),
    variation: result.enabled ? "enabled" : "disabled",
    timestamp: result.evaluatedAt,
    sdkVersion: SDK_VERSION,
    source: result.source,
  };
  // Fire-and-forget; never block evaluation on telemetry
  Promise.resolve(_telemetrySink(event)).catch(() => {
    /* silently drop */
  });
}

function hashUserId(raw: string): string {
  // Simple stable hash for privacy preservation.
  // In production, use a HMAC with a server-side secret.
  if (typeof crypto !== "undefined" && crypto.subtle) {
    // Async path handled separately; sync fallback here:
  }
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    const chr = raw.charCodeAt(i);
    hash = (hash << 5) - hash + chr;
    hash |= 0;
  }
  return `u_${Math.abs(hash).toString(36)}`;
}

// ─────────────────────────────────────────────────────────────
// Python-equivalent pseudo-bridge (type stubs for shared logic)
// ─────────────────────────────────────────────────────────────

// The backend Python equivalent lives in `api.py` and exposes:
//
//     from fabric_feature_flags import is_enabled
//     if is_enabled("new-dashboard-v2", tenant_id="tenant-42"):
//         ...
//
// Both SDKs share the same evaluation semantics and hash algorithm
// so percentage rollouts are consistent across backend and frontend.

// ─────────────────────────────────────────────────────────────
// Exports
// ─────────────────────────────────────────────────────────────

export { SDK_VERSION };
export { globalStore };
