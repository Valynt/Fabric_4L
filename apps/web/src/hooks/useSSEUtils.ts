/**
 * Shared utilities for Server-Sent Events (SSE) URL construction
 *
 * Provides consistent URL building for SSE connections across hooks,
 * ensuring environment variables are handled uniformly.
 *
 * Layer prefix defaults are sourced from the centralized apiConfig module
 * so that a single env-var change propagates to all SSE connections.
 */
import { API_BASE, L2_PREFIX, L3_PREFIX, L4_PREFIX } from '@/lib/apiConfig';

/**
 * Build SSE URL with consistent environment variable handling
 */
function buildSSEUrl(prefix: string, endpointPath: string): string {
  return `${API_BASE}${prefix}${endpointPath}`;
}

/**
 * Pre-configured builders for each service layer.
 * Prefix defaults are sourced from the centralized apiConfig module.
 */
export const SSEBuilders = {
  l2: (endpointPath: string) => buildSSEUrl(L2_PREFIX, endpointPath),
  l3: (endpointPath: string) => buildSSEUrl(L3_PREFIX, endpointPath),
  l4: (endpointPath: string) => buildSSEUrl(L4_PREFIX, endpointPath),
};

/**
 * Default SSE connection timeout
 */
export const SSE_TIMEOUT_MS = 30 * 1000;
