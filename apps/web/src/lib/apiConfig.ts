/**
 * API Configuration
 *
 * Centralized API endpoint configuration for SSE and direct API access.
 * These values mirror the configuration in api/client.ts.
 * Canonical routing/versioning matrix:
 * docs/reference/service-routing-and-api-version-matrix.md
 */

function isProductionApiConfig(): boolean {
  return import.meta.env.PROD || import.meta.env.VITE_APP_ENV === "production";
}

function getApiConfigValue(
  names: readonly string[],
  fallback: string,
  label: string
): string {
  for (const name of names) {
    const value = import.meta.env[name];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }

  if (isProductionApiConfig()) {
    throw new Error(
      `${label} is required in production frontend builds. Set one of: ${names.join(", ")}.`
    );
  }

  return fallback;
}

export const API_VERSION_PREFIX = getApiConfigValue(
  ["VITE_API_VERSION_PREFIX", "VITE_API_BASE"],
  "/api/v1",
  "Gateway API version prefix"
);
export const API_BASE = API_VERSION_PREFIX;

// Layer prefixes
export const L1_PREFIX = getApiConfigValue(
  ["VITE_LAYER1_ROUTE_PREFIX", "VITE_L1_PREFIX"],
  "/ingest",
  "Layer 1 route prefix"
);
export const L2_PREFIX = getApiConfigValue(
  ["VITE_LAYER2_ROUTE_PREFIX", "VITE_L2_PREFIX"],
  "/extract",
  "Layer 2 route prefix"
);
export const L3_PREFIX = getApiConfigValue(
  ["VITE_LAYER3_ROUTE_PREFIX", "VITE_L3_PREFIX"],
  "/graph",
  "Layer 3 route prefix"
);
export const L4_PREFIX = getApiConfigValue(
  ["VITE_LAYER4_ROUTE_PREFIX", "VITE_L4_PREFIX"],
  "/agents",
  "Layer 4 route prefix"
);
export const L5_PREFIX = getApiConfigValue(
  ["VITE_LAYER5_ROUTE_PREFIX", "VITE_L5_PREFIX"],
  "/truths",
  "Layer 5 route prefix"
);
export const L6_PREFIX = getApiConfigValue(
  ["VITE_LAYER6_ROUTE_PREFIX", "VITE_L6_PREFIX"],
  "/benchmarks",
  "Layer 6 route prefix"
);

// Special prefixes. The frontend Layer 4 client already routes through
// /api/v1/agents and the Vite gateway rewrites that to backend /v1.
// Do not add another /v1 here, or browser calls become /v1/v1/*.
export const L4_ANALYSIS_PREFIX = "";

// Re-export layer prefixes for consistency
export const LAYER_PREFIXES = {
  l1: L1_PREFIX,
  l2: L2_PREFIX,
  l3: L3_PREFIX,
  l4: L4_PREFIX,
  l5: L5_PREFIX,
  l6: L6_PREFIX,
} as const;
