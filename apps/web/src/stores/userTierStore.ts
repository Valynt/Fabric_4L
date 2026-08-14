/**
 * User Tier Store — Role-based access control and progressive disclosure state
 *
 * Manages:
 * - User tier/role (standard, advanced, admin)
 * - Advanced mode toggle state
 * - Route protection permissions
 * - Tier-specific feature flags
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { createFeatureLogger } from "@/lib/telemetry";

const log = createFeatureLogger("userTierStore");

export type UserTier = "standard" | "advanced" | "admin" | "unknown";

/** Security result type distinguishing explicit deny from evaluation failure */
export type AccessDecision =
  { allowed: true } | { allowed: false; reason: string };

/**
 * Type guard to check if access decision is denied.
 * Useful for type-safe access to rejection reasons.
 */
export function isDenied(
  decision: AccessDecision
): decision is { allowed: false; reason: string } {
  return !decision.allowed;
}

export interface UserPermissions {
  canAccessAdvanced: boolean;
  canAccessAdmin: boolean;
  canEditFormulas: boolean;
  canManageBenchmarks: boolean;
  canManageVariables: boolean;
  canManagePacks: boolean;
  canManageUsers: boolean;
}

export interface UserTierState {
  // Current tier
  currentTier: UserTier;

  // Advanced mode toggle (for standard users to temporarily access advanced features)
  isAdvancedModeEnabled: boolean;

  // User role from backend
  userRole: string | null;

  // Feature flags based on tier
  permissions: UserPermissions;

  // Persist rehydration state (used by route guards to avoid deciding before storage is read)
  isRehydrated: boolean;

  // Actions
  setRehydrated: (isRehydrated: boolean) => void;
  setTier: (tier: UserTier) => void;
  setUserRole: (role: string) => void;
  toggleAdvancedMode: () => void;
  enableAdvancedMode: () => void;
  disableAdvancedMode: () => void;

  // Permission checks
  canAccessRoute: (routeTier: UserTier | string) => boolean;
  canAccessRouteWithReason: (routeTier: UserTier | string) => AccessDecision;
  canAccessFeature: (feature: keyof UserPermissions) => boolean;

  // Computed
  effectiveTier: UserTier;
  isPrivileged: boolean;
}

// Valid tier values for runtime validation
const VALID_TIERS: readonly string[] = ["standard", "advanced", "admin"];

/**
 * Validates and normalizes a tier parameter.
 * @returns Normalized tier string if valid, null if invalid
 */
export const validateTier = (tier: UserTier | string): UserTier | null => {
  if (typeof tier !== "string") return null;
  const normalized = tier.toLowerCase().trim();
  if (VALID_TIERS.includes(normalized)) {
    return normalized as UserTier;
  }
  return null;
};

// Default permissions by tier
const getDefaultPermissions = (tier: UserTier): UserPermissions => {
  const base: UserPermissions = {
    canAccessAdvanced: false,
    canAccessAdmin: false,
    canEditFormulas: false,
    canManageBenchmarks: false,
    canManageVariables: false,
    canManagePacks: false,
    canManageUsers: false,
  };

  switch (tier) {
    case "standard":
      return base;
    case "advanced":
      return {
        ...base,
        canAccessAdvanced: true,
        canEditFormulas: true,
      };
    case "admin":
      return {
        canAccessAdvanced: true,
        canAccessAdmin: true,
        canEditFormulas: true,
        canManageBenchmarks: true,
        canManageVariables: true,
        canManagePacks: true,
        canManageUsers: true,
      };
    default:
      // SECURITY: Unknown tier gets no permissions (fail-closed)
      return base;
  }
};

/**
 * Canonical backend role to UI tier normalization
 *
 * Backend roles (source of truth) → Frontend tiers (presentation abstraction)
 *
 * Mapping:
 * - super_admin, tenant_admin, content_admin → admin
 * - analyst, editor, advanced → advanced
 * - read_only, viewer, user, standard → standard
 *
 * SECURITY: This compatibility mapping is presentation-only. Unknown roles
 * remain unresolved and must never be used to infer authorization grants.
 *
 * @param role - Backend-canonical role or frontend tier
 * @returns Normalized UI tier for feature gating
 */
export const normalizeRoleToTier = (role: unknown): UserTier | undefined => {
  if (typeof role !== "string" || role.trim() === "") {
    return undefined;
  }
  const normalizedRole = role.toLowerCase().trim();

  const roleToTierMap: Record<string, UserTier> = {
    // Backend admin roles → admin tier
    super_admin: "admin",
    tenant_admin: "admin",
    content_admin: "admin",
    // Frontend admin → admin tier
    admin: "admin",
    // Backend advanced roles → advanced tier
    analyst: "advanced",
    // Frontend advanced → advanced tier
    editor: "advanced",
    advanced: "advanced",
    // Backend read-only → standard tier
    read_only: "standard",
    // Frontend standard → standard tier
    viewer: "standard",
    user: "standard",
    standard: "standard",
    // System role (service-to-service) → standard for UI purposes
    system: "standard",
  };

  const tier = roleToTierMap[normalizedRole];

  if (!tier) {
    log.warn(`Unknown role "${role}" - leaving display tier unresolved`);
    return undefined;
  }

  return tier;
};

// Routes and their required tiers — Refactored 4-Layer Navigation Taxonomy
// 1. Context Engine → 2. Value Studio → 3. Delivery Orchestrator → 4. Governance & Trust → Admin
const ROUTE_TIER_MAP: Record<string, UserTier> = {
  // Root
  "/": "standard",

  // ───────────────────────────────────────────────────────────────
  // Home — All tiers
  // ───────────────────────────────────────────────────────────────
  "/home": "standard",

  // ═══════════════════════════════════════════════════════════════
  // 1. CONTEXT ENGINE — Foundation Layer
  // "What does the system know and how does it reason?"
  // ═══════════════════════════════════════════════════════════════

  // Ontology & Schema
  "/context": "advanced",
  "/context/ontology": "advanced",
  "/context/ontology/entities": "advanced",
  "/context/ontology/graph": "advanced",

  // Integrations, Sources & Targets
  "/context/integrations": "admin",
  "/context/sources": "admin",
  "/context/targets": "admin",
  "/context/ingestion/jobs": "advanced",
  "/context/extraction": "advanced",

  // Knowledge & Logic
  "/context/packs": "standard",
  "/context/models": "standard",
  "/context/value-trees/explorer": "advanced",
  "/context/formulas": "advanced",
  "/context/agents": "advanced",

  // ═══════════════════════════════════════════════════════════════
  // 2. VALUE STUDIO — Core Workflow Layer
  // "How do I create and prove value for this specific deal?"
  // ═══════════════════════════════════════════════════════════════

  "/studio": "standard",

  // Deal Context
  "/studio/deals": "standard",
  "/studio/deals/:id": "standard",
  "/studio/deals/:id/whitespace": "advanced",

  // Value Construction (6-Stage Pipeline)
  "/studio/build": "advanced",
  "/studio/build/discovery": "advanced",
  "/studio/build/mapping": "advanced",
  "/studio/build/modeling": "advanced",
  "/studio/build/validation": "advanced",
  "/studio/build/narrative": "advanced",
  "/studio/build/tracking": "advanced",

  // Value Exploration
  "/studio/trees": "advanced",
  "/studio/trees/:id": "advanced",
  "/studio/scenarios": "advanced",

  // ═══════════════════════════════════════════════════════════════
  // 3. DELIVERY ORCHESTRATOR — Activation Layer
  // "How does value leave the system and create impact?"
  // ═══════════════════════════════════════════════════════════════

  "/deliver": "standard",

  // Executive Outputs
  "/deliver/cases": "standard",
  "/deliver/cases/:caseId": "standard",
  "/deliver/cases/:caseId/export": "standard",
  "/deliverables/cases": "standard",
  "/deliverables/cases/:caseId": "standard",
  "/deliverables/cases/:caseId/export": "standard",

  // Interactive Tools
  "/deliver/calculators": "advanced",
  "/deliver/calculators/:id": "advanced",

  // API & Integration
  "/deliver/api": "admin",
  "/deliver/embeds": "admin",

  // Stakeholder Views
  "/deliver/views/cfo": "standard",
  "/deliver/views/executive": "standard",
  "/deliver/views/technical": "standard",

  // ═══════════════════════════════════════════════════════════════
  // 4. GOVERNANCE & TRUST — Trust Layer
  // "Can I trust this, and can I prove it?"
  // ═══════════════════════════════════════════════════════════════

  "/trust": "standard",

  // Assumption Traceability
  "/trust/lineage/:entityId": "advanced",
  "/trust/evidence": "standard",
  "/trust/provenance": "advanced",

  // Agent Reasoning
  "/trust/reasoning/:workflowId": "advanced",
  "/trust/traces": "standard",

  // Audit & Compliance
  "/trust/audit/log": "admin",
  "/trust/audit/changes": "admin",
  "/trust/compliance": "advanced",

  // System Integrity
  "/trust/health": "admin",
  "/trust/integrity": "advanced",
  "/trust/benchmarks": "admin",

  // ═══════════════════════════════════════════════════════════════
  // ADMIN — System Configuration (Control Plane)
  // ═══════════════════════════════════════════════════════════════

  "/admin": "admin",

  // Content Governance
  "/admin/content": "admin",
  "/admin/content/formulas": "admin",
  "/admin/content/versions": "admin",
  "/admin/content/approvals": "admin",

  // Data Governance
  "/admin/data": "admin",
  "/admin/data/variables": "admin",
  "/admin/data/bindings": "admin",
  "/admin/data/quality": "admin",

  // Access Control
  "/admin/access": "admin",
  "/admin/access/roles": "admin",
  "/admin/access/teams": "admin",
  "/admin/access/keys": "admin",

  // System Settings
  "/admin/system": "admin",
  "/admin/system/settings": "admin",
  "/settings/system/billing": "admin",
  "/settings/system/billing/usage": "admin",
  "/settings/system/billing/invoices": "admin",
  "/settings/system/billing/payments": "admin",

  // ═══════════════════════════════════════════════════════════════
  // CANONICAL WORKSPACE ROUTES — /t/:tenantSlug/accounts/:accountId/...
  // ═══════════════════════════════════════════════════════════════

  "/t": "standard",
  "/t/:tenantSlug/accounts": "standard",
  "/t/:tenantSlug/accounts/:accountId/intelligence": "standard",
  "/t/:tenantSlug/accounts/:accountId/studio": "advanced",
  "/t/:tenantSlug/accounts/:accountId/deliverables": "standard",
  "/t/:tenantSlug/context": "standard",
  "/t/:tenantSlug/context/integrations": "admin",
  "/t/:tenantSlug/governance": "standard",
  "/t/:tenantSlug/governance/benchmarks": "admin",
  "/t/:tenantSlug/settings": "admin",

  // ═══════════════════════════════════════════════════════════════
  // LEGACY REDIRECTS (maintain for backward compatibility)
  // ═══════════════════════════════════════════════════════════════

  // ═══════════════════════════════════════════════════════════════
  // LEGACY REDIRECTS (maintain for backward compatibility)
  // ═══════════════════════════════════════════════════════════════
  "/library": "standard",
  "/library/packs": "standard",
  "/library/models": "standard",
  "/library/authoring": "admin",
  "/discover": "standard",
  "/discover/accounts": "standard",
  "/discover/jobs": "standard",
  "/discover/extraction": "advanced",
  "/discover/knowledge": "advanced",
  "/discover/integrations": "admin",
  "/discover/sources": "admin",
  "/model": "advanced",
  "/model/value-studio": "advanced",
  "/evidence": "standard",
  "/evidence/traces": "standard",
  "/evidence/lineage": "advanced",
  "/evidence/compliance": "advanced",
  "/admin/system/audit": "admin",
  "/admin/system/health": "admin",
  "/admin/content/benchmarks": "admin",
};

// Pre-sorted routes for efficient lookup (longest first for proper prefix matching)
const SORTED_ROUTES = Object.entries(ROUTE_TIER_MAP).sort(
  (a, b) => b[0].length - a[0].length
);

// Deterministic fail-closed default tier. The actual persisted tier is applied
// synchronously by the persist middleware, and permissions are recomputed in
// onRehydrateStorage. This avoids a server/client hydration mismatch caused by
// reading localStorage at module evaluation time.
const DEFAULT_INITIAL_TIER: UserTier = "standard";

type PersistedUserTierSnapshot = Partial<UserTierState> & {
  state?: Partial<UserTierState>;
};

export function getPersistedTierSnapshot(
  persistedState: unknown
): Partial<UserTierState> {
  const snapshot = persistedState as PersistedUserTierSnapshot | undefined;
  return snapshot?.state ?? snapshot ?? {};
}

export const useUserTierStore = create<UserTierState>()(
  persist(
    (set, get) => ({
      // Initial state (deterministic; persisted values are merged during rehydration)
      currentTier: DEFAULT_INITIAL_TIER,
      isAdvancedModeEnabled: false,
      userRole: null,
      permissions: getDefaultPermissions(DEFAULT_INITIAL_TIER),
      isRehydrated: false,

      // Actions
      setRehydrated: isRehydrated => {
        set({ isRehydrated });
      },

      setTier: tier => {
        set({
          currentTier: tier,
          permissions: getDefaultPermissions(tier),
        });
      },

      setUserRole: role => {
        set({ userRole: role });
        // Normalize backend-canonical role to UI tier
        const tier = normalizeRoleToTier(role);
        if (!tier) {
          set({
            currentTier: "unknown",
            permissions: getDefaultPermissions("unknown"),
          });
          return;
        }
        set({
          currentTier: tier,
          permissions: getDefaultPermissions(tier),
        });
      },

      toggleAdvancedMode: () => {
        const newValue = !get().isAdvancedModeEnabled;
        set({ isAdvancedModeEnabled: newValue });
      },

      enableAdvancedMode: () => {
        set({ isAdvancedModeEnabled: true });
      },

      disableAdvancedMode: () => {
        set({ isAdvancedModeEnabled: false });
      },

      // Permission checks with explicit validation - fails closed
      canAccessRouteWithReason: routeTier => {
        const validatedTier = validateTier(routeTier);
        if (validatedTier === null) {
          return { allowed: false, reason: "INVALID_TIER_PARAMETER" };
        }

        const { currentTier, isAdvancedModeEnabled } = get();

        // Validate current tier is valid
        if (!VALID_TIERS.includes(currentTier)) {
          return { allowed: false, reason: "INVALID_USER_TIER_STATE" };
        }

        // Admin can access everything
        if (currentTier === "admin") {
          return { allowed: true };
        }

        // Advanced users can access standard and advanced routes
        if (currentTier === "advanced") {
          if (validatedTier === "standard" || validatedTier === "advanced") {
            return { allowed: true };
          }
          return { allowed: false, reason: "ADMIN_ROUTE_REQUIRES_ADMIN_TIER" };
        }

        // Standard users can access standard routes
        // And advanced routes if advanced mode is enabled
        if (currentTier === "standard") {
          if (validatedTier === "standard") {
            return { allowed: true };
          }
          if (validatedTier === "advanced" && isAdvancedModeEnabled) {
            return { allowed: true };
          }
          if (validatedTier === "advanced" && !isAdvancedModeEnabled) {
            return {
              allowed: false,
              reason: "ADVANCED_ROUTE_REQUIRES_ADVANCED_MODE",
            };
          }
          return { allowed: false, reason: "ADMIN_ROUTE_REQUIRES_ADMIN_TIER" };
        }

        // Fail closed - should never reach here but explicit deny
        return { allowed: false, reason: "TIER_EVALUATION_FAILED" };
      },

      canAccessRoute: routeTier => {
        return get().canAccessRouteWithReason(routeTier).allowed;
      },

      canAccessFeature: feature => {
        return get().permissions[feature];
      },

      // Computed properties
      get effectiveTier() {
        const { currentTier, isAdvancedModeEnabled } = get();
        if (currentTier === "standard" && isAdvancedModeEnabled) {
          return "advanced";
        }
        return currentTier;
      },

      get isPrivileged() {
        const tier = get().effectiveTier;
        return tier === "advanced" || tier === "admin";
      },
    }),
    {
      name: "user-tier-storage",
      storage: createJSONStorage(() => localStorage),
      partialize: state => ({
        currentTier: state.currentTier,
        isAdvancedModeEnabled: state.isAdvancedModeEnabled,
        userRole: state.userRole,
      }),
      merge: (persistedState, currentState) => {
        const typedState = getPersistedTierSnapshot(persistedState);
        const storedTier =
          validateTier(typedState?.currentTier ?? "standard") ?? "standard";
        const mergedState: UserTierState = {
          currentTier: storedTier,
          isAdvancedModeEnabled:
            typedState?.isAdvancedModeEnabled ?? storedTier !== "standard",
          userRole: typedState?.userRole ?? null,
          permissions: getDefaultPermissions(storedTier),
          isRehydrated: true,
          setRehydrated: currentState.setRehydrated,
          setTier: currentState.setTier,
          setUserRole: currentState.setUserRole,
          toggleAdvancedMode: currentState.toggleAdvancedMode,
          enableAdvancedMode: currentState.enableAdvancedMode,
          disableAdvancedMode: currentState.disableAdvancedMode,
          canAccessRoute: currentState.canAccessRoute,
          canAccessRouteWithReason: currentState.canAccessRouteWithReason,
          canAccessFeature: currentState.canAccessFeature,
          get effectiveTier() {
            const { currentTier, isAdvancedModeEnabled } =
              useUserTierStore.getState();
            if (currentTier === "standard" && isAdvancedModeEnabled) {
              return "advanced";
            }
            return currentTier;
          },
          get isPrivileged() {
            const tier = useUserTierStore.getState().effectiveTier;
            return tier === "advanced" || tier === "admin";
          },
        };
        return mergedState;
      },
      onRehydrateStorage: initialState => (state, error) => {
        if (error) {
          log.warn(
            "Failed to rehydrate user tier store; using fail-closed defaults",
            {
              error: error instanceof Error ? error.message : String(error),
            }
          );
          initialState.setRehydrated(true);
          return;
        }
        if (!state?.isRehydrated) {
          state?.setRehydrated(true);
        }
      },
    }
  )
);

/**
 * Look up the required tier for a single (already-normalized) path.
 * Returns `undefined` when the path is not registered.
 */
export function matchRouteTier(path: string): UserTier | undefined {
  const exact = ROUTE_TIER_MAP[path];
  if (exact) return exact;

  // Check parent routes using pre-sorted array (longest match wins)
  for (const [route, tier] of SORTED_ROUTES) {
    if (path.startsWith(route + "/")) {
      return tier;
    }
  }

  return undefined;
}

// Helper function to check route access outside of components
// SECURITY: Returns 'unknown' for unrecognized paths (fail-closed default)
export function getRouteTier(path: string): UserTier {
  // Normalize canonical tenant-scoped paths for pattern matching
  // e.g. /t/acme/accounts/acc-123/intelligence → /t/:tenantSlug/accounts/:accountId/intelligence
  const normalizedPath = path
    .replace(
      /^\/t\/[^/]+\/accounts\/[^/]+/,
      "/t/:tenantSlug/accounts/:accountId"
    )
    .replace(/^\/t\/[^/]+/, "/t/:tenantSlug");

  return matchRouteTier(normalizedPath) ?? matchRouteTier(path) ?? "unknown";
}

export default useUserTierStore;
