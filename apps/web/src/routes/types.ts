/**
 * Route Types — Access Policy and Analytics Metadata
 *
 * Centralized route metadata definitions for React Router `handle` fields.
 * Every route in the canonical tree must declare an `accessPolicy`.
 */

export type UserTier = "standard" | "advanced" | "admin";
export type StoreTier = UserTier | "unknown";

export type RouteAccessPolicy = {
  /** Whether the route requires an authenticated session. */
  requiresAuth: boolean;
  /** Whether the route is scoped to a tenant/workspace. */
  tenantScoped: boolean;
  /** Whether the route is scoped to a specific account. */
  accountScoped?: boolean;
  /** Minimum user tier required. */
  requiredTier?: Exclude<UserTier, "unknown">;
  /** Permission strings required (e.g., ['account:read', 'intelligence:read']). */
  requiredPermissions?: string[];
  /** Feature flag keys that must be enabled. */
  requiredFeatureFlags?: string[];
  /** Plan entitlement keys that must be active. */
  requiredEntitlements?: string[];
  /** Route to redirect to when access is denied. */
  fallbackRoute: string;
  /** Stable identifier used for analytics normalization. */
  analyticsRouteId: string;
};

export type AnalyticsMeta = {
  /** Human-readable page name for analytics (dot-notation). */
  pageName: string;
  /** Top-level product category. */
  category: string;
  /** Sub-category or feature area. */
  subcategory?: string;
  /** Feature flag or experiment key. */
  feature?: string;
  /** Whether this route requires an account context. */
  requiresAccount?: boolean;
  /** URL param names to redact in analytics payloads. */
  redactParams?: string[];
};
