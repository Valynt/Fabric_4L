import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  useUserTierStore,
  getRouteTier,
  matchRouteTier,
  isDenied,
  validateTier,
  normalizeRoleToTier,
  getPersistedTierSnapshot,
  type UserTier,
} from "./userTierStore";

const standardPermissions = {
  canAccessAdvanced: false,
  canAccessAdmin: false,
  canEditFormulas: false,
  canManageBenchmarks: false,
  canManageVariables: false,
  canManagePacks: false,
  canManageUsers: false,
};

const advancedPermissions = {
  ...standardPermissions,
  canAccessAdvanced: true,
  canEditFormulas: true,
};

const adminPermissions = {
  canAccessAdvanced: true,
  canAccessAdmin: true,
  canEditFormulas: true,
  canManageBenchmarks: true,
  canManageVariables: true,
  canManagePacks: true,
  canManageUsers: true,
};

function resetStore() {
  useUserTierStore.setState({
    currentTier: "standard" as UserTier,
    isAdvancedModeEnabled: false,
    userRole: null,
    permissions: { ...standardPermissions },
    isRehydrated: true,
  });
}

describe("isDenied", () => {
  it("returns true for denied decisions", () => {
    expect(isDenied({ allowed: false, reason: "test" })).toBe(true);
  });

  it("returns false for allowed decisions", () => {
    expect(isDenied({ allowed: true })).toBe(false);
  });
});

describe("validateTier", () => {
  it("accepts valid tiers", () => {
    expect(validateTier("standard")).toBe("standard");
    expect(validateTier("advanced")).toBe("advanced");
    expect(validateTier("admin")).toBe("admin");
  });

  it("normalizes case and trims whitespace", () => {
    expect(validateTier("Advanced")).toBe("advanced");
    expect(validateTier("  admin  ")).toBe("admin");
  });

  it("rejects invalid tier values", () => {
    expect(validateTier("hacker")).toBeNull();
    expect(validateTier("")).toBeNull();
    expect(validateTier(undefined as unknown as string)).toBeNull();
  });
});

describe("normalizeRoleToTier", () => {
  it("maps backend admin roles to admin tier", () => {
    expect(normalizeRoleToTier("super_admin")).toBe("admin");
    expect(normalizeRoleToTier("tenant_admin")).toBe("admin");
    expect(normalizeRoleToTier("content_admin")).toBe("admin");
    expect(normalizeRoleToTier("admin")).toBe("admin");
  });

  it("maps backend advanced roles to advanced tier", () => {
    expect(normalizeRoleToTier("analyst")).toBe("advanced");
    expect(normalizeRoleToTier("editor")).toBe("advanced");
    expect(normalizeRoleToTier("advanced")).toBe("advanced");
  });

  it("maps backend standard roles to standard tier", () => {
    expect(normalizeRoleToTier("read_only")).toBe("standard");
    expect(normalizeRoleToTier("viewer")).toBe("standard");
    expect(normalizeRoleToTier("user")).toBe("standard");
    expect(normalizeRoleToTier("standard")).toBe("standard");
    expect(normalizeRoleToTier("system")).toBe("standard");
  });

  it("maps unknown roles to the explicit unresolved tier", () => {
    expect(normalizeRoleToTier("unknown_role")).toBe("unknown");
  });
});

describe("useUserTierStore", () => {
  beforeEach(async () => {
    // Ensure the persist middleware has finished rehydrating before mutating state,
    // otherwise async rehydration can clobber test values after assertions run.
    await useUserTierStore.persist.rehydrate();
    resetStore();
  });

  describe("actions", () => {
    it("setTier updates current tier and permissions", () => {
      useUserTierStore.getState().setTier("advanced");
      const state = useUserTierStore.getState();
      expect(state.currentTier).toBe("advanced");
      expect(state.permissions).toEqual(advancedPermissions);
    });

    it("setTier fails closed for unknown tier", () => {
      useUserTierStore.getState().setTier("unknown" as UserTier);
      const state = useUserTierStore.getState();
      expect(state.currentTier).toBe("unknown");
      expect(state.permissions).toEqual(standardPermissions);
    });

    it("setUserRole normalizes role and updates tier and permissions", () => {
      useUserTierStore.getState().setUserRole("tenant_admin");
      const state = useUserTierStore.getState();
      expect(state.userRole).toBe("tenant_admin");
      expect(state.currentTier).toBe("admin");
      expect(state.permissions).toEqual(adminPermissions);
    });

    it("setUserRole explicitly denies unresolved roles", () => {
      const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
      useUserTierStore.getState().setUserRole("unknown_role");
      const state = useUserTierStore.getState();
      expect(state.currentTier).toBe("unknown");
      expect(state.permissions).toEqual(standardPermissions);
      expect(state.canAccessRoute("standard")).toBe(false);
      warnSpy.mockRestore();
    });

    it("toggleAdvancedMode toggles the flag", () => {
      const { toggleAdvancedMode } = useUserTierStore.getState();
      toggleAdvancedMode();
      expect(useUserTierStore.getState().isAdvancedModeEnabled).toBe(true);
      toggleAdvancedMode();
      expect(useUserTierStore.getState().isAdvancedModeEnabled).toBe(false);
    });

    it("enableAdvancedMode and disableAdvancedMode work", () => {
      useUserTierStore.getState().enableAdvancedMode();
      expect(useUserTierStore.getState().isAdvancedModeEnabled).toBe(true);
      useUserTierStore.getState().disableAdvancedMode();
      expect(useUserTierStore.getState().isAdvancedModeEnabled).toBe(false);
    });
  });

  describe("persistence", () => {
    it("extracts only a boolean presentation preference from legacy storage", () => {
      const snapshot = getPersistedTierSnapshot({
        state: {
          currentTier: "admin",
          userRole: "admin",
          permissions: adminPermissions,
          accountId: "other-tenant-account",
          securityContext: { isAdmin: true },
          isAdvancedModeEnabled: true,
        },
        version: 0,
      });

      expect(snapshot).toEqual({ isAdvancedModeEnabled: true });
    });

    it("ignores malformed persisted presentation preferences", () => {
      expect(
        getPersistedTierSnapshot({
          state: { isAdvancedModeEnabled: "true", currentTier: "admin" },
        })
      ).toEqual({});
    });

    it("rehydrates preferences without restoring legacy authorization state", async () => {
      localStorage.setItem(
        "user-tier-storage",
        JSON.stringify({
          state: {
            currentTier: "admin",
            userRole: "tenant_admin",
            permissions: adminPermissions,
            accountId: "other-tenant-account",
            securityContext: { isAdmin: true },
            isAdvancedModeEnabled: true,
          },
          version: 0,
        })
      );

      useUserTierStore.setState({
        currentTier: "unknown",
        userRole: null,
        permissions: { ...standardPermissions },
        isAdvancedModeEnabled: false,
        isRehydrated: false,
      });
      await useUserTierStore.persist.rehydrate();

      const state = useUserTierStore.getState();
      expect(state.currentTier).toBe("unknown");
      expect(state.userRole).toBeNull();
      expect(state.permissions).toEqual(standardPermissions);
      expect(state.isAdvancedModeEnabled).toBe(true);
      expect(state.canAccessRoute("standard")).toBe(false);
    });
  });

  describe("canAccessRoute", () => {
    it("admin can access all route tiers", () => {
      useUserTierStore.getState().setTier("admin");
      const state = useUserTierStore.getState();
      expect(state.canAccessRoute("standard")).toBe(true);
      expect(state.canAccessRoute("advanced")).toBe(true);
      expect(state.canAccessRoute("admin")).toBe(true);
    });

    it("advanced user can access standard and advanced routes", () => {
      useUserTierStore.getState().setTier("advanced");
      const state = useUserTierStore.getState();
      expect(state.canAccessRoute("standard")).toBe(true);
      expect(state.canAccessRoute("advanced")).toBe(true);
      expect(state.canAccessRoute("admin")).toBe(false);
    });

    it("standard user can only access standard routes", () => {
      const state = useUserTierStore.getState();
      expect(state.canAccessRoute("standard")).toBe(true);
      expect(state.canAccessRoute("advanced")).toBe(false);
      expect(state.canAccessRoute("admin")).toBe(false);
    });

    it("advanced mode never grants a standard user advanced route access", () => {
      useUserTierStore.getState().enableAdvancedMode();
      const state = useUserTierStore.getState();
      expect(state.canAccessRoute("standard")).toBe(true);
      expect(state.canAccessRoute("advanced")).toBe(false);
      expect(state.canAccessRoute("admin")).toBe(false);
    });

    it("fails closed for invalid route tier parameter", () => {
      expect(useUserTierStore.getState().canAccessRoute("invalid")).toBe(false);
    });
  });

  describe("canAccessRouteWithReason", () => {
    it("returns allowed for admin", () => {
      useUserTierStore.getState().setTier("admin");
      const decision = useUserTierStore
        .getState()
        .canAccessRouteWithReason("admin");
      expect(decision).toEqual({ allowed: true });
    });

    it("returns denied for invalid tier parameter", () => {
      const decision = useUserTierStore
        .getState()
        .canAccessRouteWithReason("invalid");
      expect(isDenied(decision)).toBe(true);
      if (isDenied(decision)) {
        expect(decision.reason).toBe("INVALID_TIER_PARAMETER");
      }
    });

    it("denies admin route for standard user", () => {
      const decision = useUserTierStore
        .getState()
        .canAccessRouteWithReason("admin");
      expect(isDenied(decision)).toBe(true);
      if (isDenied(decision)) {
        expect(decision.reason).toBe("ADMIN_ROUTE_REQUIRES_ADMIN_TIER");
      }
    });

    it("denies advanced route for standard user", () => {
      const decision = useUserTierStore
        .getState()
        .canAccessRouteWithReason("advanced");
      expect(isDenied(decision)).toBe(true);
      if (isDenied(decision)) {
        expect(decision.reason).toBe("ADVANCED_ROUTE_REQUIRES_ADVANCED_TIER");
      }
    });

    it("denies advanced route for standard user with advanced mode", () => {
      useUserTierStore.getState().enableAdvancedMode();
      const decision = useUserTierStore
        .getState()
        .canAccessRouteWithReason("advanced");
      expect(decision).toEqual({
        allowed: false,
        reason: "ADVANCED_ROUTE_REQUIRES_ADVANCED_TIER",
      });
    });

    it("advanced mode never changes role, tier, permissions, or privilege", () => {
      const before = useUserTierStore.getState();
      const authorization = {
        currentTier: before.currentTier,
        userRole: before.userRole,
        permissions: before.permissions,
        effectiveTier: before.effectiveTier,
        isPrivileged: before.isPrivileged,
      };

      before.enableAdvancedMode();
      const after = useUserTierStore.getState();

      expect({
        currentTier: after.currentTier,
        userRole: after.userRole,
        permissions: after.permissions,
        effectiveTier: after.effectiveTier,
        isPrivileged: after.isPrivileged,
      }).toEqual(authorization);
    });

    it("fails closed for invalid user tier state", () => {
      useUserTierStore.setState({ currentTier: "unknown" as UserTier });
      const decision = useUserTierStore
        .getState()
        .canAccessRouteWithReason("standard");
      expect(isDenied(decision)).toBe(true);
      if (isDenied(decision)) {
        expect(decision.reason).toBe("INVALID_USER_TIER_STATE");
      }
    });
  });

  describe("canAccessFeature", () => {
    it("reflects tier-based permissions", () => {
      useUserTierStore.getState().setTier("admin");
      expect(
        useUserTierStore.getState().canAccessFeature("canManageUsers")
      ).toBe(true);
      expect(
        useUserTierStore.getState().canAccessFeature("canEditFormulas")
      ).toBe(true);
      useUserTierStore.getState().setTier("advanced");
      expect(
        useUserTierStore.getState().canAccessFeature("canEditFormulas")
      ).toBe(true);
      expect(
        useUserTierStore.getState().canAccessFeature("canManageUsers")
      ).toBe(false);
      useUserTierStore.getState().setTier("standard");
      expect(
        useUserTierStore.getState().canAccessFeature("canAccessAdvanced")
      ).toBe(false);
    });
  });

  // NOTE: computed getters (effectiveTier, isPrivileged) are exercised by React
  // selectors in component tests; direct getState() access after setState does
  // not trigger recomputation in this unit-test environment, so they are left
  // for integration-level coverage rather than adding brittle mocks here.
});

describe("matchRouteTier", () => {
  it("returns the tier for an exact route", () => {
    expect(matchRouteTier("/home")).toBe("standard");
    expect(matchRouteTier("/admin")).toBe("admin");
  });

  it("returns the tier for the longest matching parent prefix", () => {
    expect(matchRouteTier("/admin/content/approvals/extra")).toBe("admin");
  });

  it("returns undefined for unrecognized routes", () => {
    expect(matchRouteTier("/not-a-route")).toBeUndefined();
  });
});

describe("getRouteTier", () => {
  it("matches exact routes", () => {
    expect(getRouteTier("/home")).toBe("standard");
    expect(getRouteTier("/admin")).toBe("admin");
  });

  it("normalizes tenant-scoped paths", () => {
    expect(getRouteTier("/t/acme/accounts/acc-123/intelligence")).toBe(
      "standard"
    );
    expect(getRouteTier("/t/acme/accounts/acc-123/studio")).toBe("advanced");
  });

  it("matches canonical tenant-scoped admin routes", () => {
    expect(getRouteTier("/t/demo/governance/benchmarks")).toBe("admin");
    expect(getRouteTier("/t/demo/context/integrations")).toBe("admin");
    expect(getRouteTier("/t/demo/settings")).toBe("admin");
  });

  it("falls back to parent prefix matching for unknown sub-routes", () => {
    expect(getRouteTier("/admin/content/approvals/extra")).toBe("admin");
  });

  it("returns unknown for completely unrecognized routes", () => {
    expect(getRouteTier("/not-a-route")).toBe("unknown");
  });
});
