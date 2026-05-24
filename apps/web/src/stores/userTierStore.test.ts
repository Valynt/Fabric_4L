import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from "@testing-library/react";
import { useUserTierStore, getRouteTier, validateTier, isDenied, normalizeRoleToTier, type UserTier } from "./userTierStore";

describe("useUserTierStore", () => {
  beforeEach(() => {
    // Clear localStorage to reset persisted state
    localStorage.clear();

    // Reset store to initial state - use setTier to properly reset permissions
    const { result } = renderHook(() => useUserTierStore());
    act(() => {
      result.current.setTier("standard");
      result.current.disableAdvancedMode();
      // Note: setUserRole with empty string triggers tier reset, so we skip it
      // The store will reset role to null when tier is set to standard
    });
  });

  describe("initial state", () => {
    it("should start with standard tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      expect(result.current.currentTier).toBe("standard");
    });

    it("should have advanced mode disabled initially", () => {
      const { result } = renderHook(() => useUserTierStore());

      expect(result.current.isAdvancedModeEnabled).toBe(false);
    });

    it("should have no user role initially", () => {
      const { result } = renderHook(() => useUserTierStore());

      expect(result.current.userRole).toBeNull();
    });

    it("should have standard permissions initially", () => {
      const { result } = renderHook(() => useUserTierStore());

      expect(result.current.permissions.canAccessAdmin).toBe(false);
      expect(result.current.permissions.canAccessAdvanced).toBe(false);
      expect(result.current.permissions.canEditFormulas).toBe(false);
    });
  });

  describe("setTier", () => {
    it("should set tier to advanced", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("advanced"));

      expect(result.current.currentTier).toBe("advanced");
      expect(result.current.permissions.canAccessAdvanced).toBe(true);
      expect(result.current.permissions.canEditFormulas).toBe(true);
    });

    it("should set tier to admin", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("admin"));

      expect(result.current.currentTier).toBe("admin");
      expect(result.current.permissions.canAccessAdmin).toBe(true);
      expect(result.current.permissions.canManageUsers).toBe(true);
    });

    it("should set tier back to standard", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("advanced"));
      act(() => result.current.setTier("standard"));

      expect(result.current.currentTier).toBe("standard");
      expect(result.current.permissions.canAccessAdvanced).toBe(false);
    });

    it.each([
      { tier: "standard" as UserTier, expectAdvanced: false, expectManageUsers: false },
      { tier: "advanced" as UserTier, expectAdvanced: true, expectManageUsers: false },
      { tier: "admin" as UserTier, expectAdvanced: true, expectManageUsers: true },
    ])("setting tier to $tier sets correct permissions", ({ tier, expectAdvanced, expectManageUsers }) => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier(tier));

      expect(result.current.permissions.canAccessAdvanced).toBe(expectAdvanced);
      expect(result.current.permissions.canManageUsers).toBe(expectManageUsers);
    });

    it("sets elevated permissions when tier is upgraded to admin", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("admin"));

      expect(result.current.permissions.canManageUsers).toBe(true);
      expect(result.current.permissions.canAccessAdvanced).toBe(true);
    });

    it("removes elevated permissions when tier is downgraded from admin to standard", () => {
      const { result } = renderHook(() => useUserTierStore());

      // Start as admin with full permissions
      act(() => result.current.setTier("admin"));

      // Downgrade to standard
      act(() => result.current.setTier("standard"));

      expect(result.current.permissions.canManageUsers).toBe(false);
      expect(result.current.permissions.canAccessAdvanced).toBe(false);
    });
  });

  describe("setUserRole", () => {
    it("should set user role", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("admin"));

      expect(result.current.userRole).toBe("admin");
    });

    it("should auto-set tier to admin for admin role", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("admin"));

      expect(result.current.currentTier).toBe("admin");
    });

    it("should auto-set tier to advanced for editor role", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("editor"));

      expect(result.current.currentTier).toBe("advanced");
    });

    it("should auto-set tier to advanced for analyst role", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("analyst"));

      expect(result.current.currentTier).toBe("advanced");
    });

    it("should default to standard for unknown role", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("unknown"));

      expect(result.current.currentTier).toBe("standard");
    });

    it("should handle role case insensitively", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("ADMIN"));

      expect(result.current.currentTier).toBe("admin");
    });

    // Backend-canonical role mapping tests
    it("should map super_admin to admin tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("super_admin"));

      expect(result.current.currentTier).toBe("admin");
      expect(result.current.permissions.canAccessAdmin).toBe(true);
    });

    it("should map tenant_admin to admin tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("tenant_admin"));

      expect(result.current.currentTier).toBe("admin");
      expect(result.current.permissions.canManageUsers).toBe(true);
    });

    it("should map content_admin to admin tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("content_admin"));

      expect(result.current.currentTier).toBe("admin");
    });

    it("should map read_only to standard tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("read_only"));

      expect(result.current.currentTier).toBe("standard");
      expect(result.current.permissions.canAccessAdmin).toBe(false);
      expect(result.current.permissions.canAccessAdvanced).toBe(false);
    });

    it("should map system role to standard tier (fail-safe)", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setUserRole("system"));

      expect(result.current.currentTier).toBe("standard");
    });
  });

  describe("advanced mode toggle", () => {
    it("should toggle advanced mode", () => {
      const { result } = renderHook(() => useUserTierStore());

      expect(result.current.isAdvancedModeEnabled).toBe(false);

      act(() => result.current.toggleAdvancedMode());

      expect(result.current.isAdvancedModeEnabled).toBe(true);

      act(() => result.current.toggleAdvancedMode());

      expect(result.current.isAdvancedModeEnabled).toBe(false);
    });

    it("should enable advanced mode", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.enableAdvancedMode());

      expect(result.current.isAdvancedModeEnabled).toBe(true);
    });

    it("should disable advanced mode", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.enableAdvancedMode());
      act(() => result.current.disableAdvancedMode());

      expect(result.current.isAdvancedModeEnabled).toBe(false);
    });
  });

  describe("canAccessRoute", () => {
    it("should allow admin to access all route tiers", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("admin"));

      expect(result.current.canAccessRoute("standard")).toBe(true);
      expect(result.current.canAccessRoute("advanced")).toBe(true);
      expect(result.current.canAccessRoute("admin")).toBe(true);
    });

    it("should allow advanced user to access standard and advanced routes", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("advanced"));

      expect(result.current.canAccessRoute("standard")).toBe(true);
      expect(result.current.canAccessRoute("advanced")).toBe(true);
      expect(result.current.canAccessRoute("admin")).toBe(false);
    });

    it("should allow standard user to access only standard routes", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("standard"));

      expect(result.current.canAccessRoute("standard")).toBe(true);
      expect(result.current.canAccessRoute("advanced")).toBe(false);
      expect(result.current.canAccessRoute("admin")).toBe(false);
    });

    it("should allow standard user with advanced mode to access advanced routes", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("standard"));
      act(() => result.current.enableAdvancedMode());

      expect(result.current.canAccessRoute("standard")).toBe(true);
      expect(result.current.canAccessRoute("advanced")).toBe(true);
      expect(result.current.canAccessRoute("admin")).toBe(false);
    });

    // SECURITY: Fail-closed tests
    it("should deny access for 'unknown' tier routes (fail-closed)", () => {
      const { result } = renderHook(() => useUserTierStore());

      // All user tiers should be denied access to 'unknown' tier routes
      // 'unknown' is not a valid tier value and should always be rejected
      act(() => result.current.setTier("standard"));
      expect(result.current.canAccessRoute("unknown")).toBe(false);

      act(() => result.current.setTier("advanced"));
      expect(result.current.canAccessRoute("unknown")).toBe(false);

      // Admin is also denied - 'unknown' is invalid tier parameter, not a permission check
      act(() => result.current.setTier("admin"));
      expect(result.current.canAccessRoute("unknown")).toBe(false);
    });

    it("should deny access for invalid/malformed tier parameters", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));

      // Invalid tier values should be denied
      expect(result.current.canAccessRoute("")).toBe(false);
      expect(result.current.canAccessRoute("invalid")).toBe(false);
      expect(result.current.canAccessRoute("hacker")).toBe(false);
      expect(result.current.canAccessRoute("STANDARD")).toBe(true); // Case insensitive OK
    });

    it("should deny access for null/undefined tier parameters", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));

      expect(result.current.canAccessRoute(null as unknown as string)).toBe(false);
      expect(result.current.canAccessRoute(undefined as unknown as string)).toBe(false);
    });
  });

  describe("canAccessRouteWithReason (SECURITY: Observable reject reasons)", () => {
    it("should provide reason for denied access to unknown tier", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));

      const decision = result.current.canAccessRouteWithReason("unknown");
      expect(decision.allowed).toBe(false);
      expect(isDenied(decision) && decision.reason).toBe("INVALID_TIER_PARAMETER");
    });

    it("should provide reason for denied access to invalid tier", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));

      const decision = result.current.canAccessRouteWithReason("malicious");
      expect(decision.allowed).toBe(false);
      expect(isDenied(decision) && decision.reason).toBe("INVALID_TIER_PARAMETER");
    });

    it("should provide reason when advanced route requires advanced mode", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));
      act(() => result.current.disableAdvancedMode());

      const decision = result.current.canAccessRouteWithReason("advanced");
      expect(decision.allowed).toBe(false);
      expect(isDenied(decision) && decision.reason).toBe("ADVANCED_ROUTE_REQUIRES_ADVANCED_MODE");
    });

    it("should provide reason when admin route requires admin tier", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));

      const decision = result.current.canAccessRouteWithReason("admin");
      expect(decision.allowed).toBe(false);
      expect(isDenied(decision) && decision.reason).toBe("ADMIN_ROUTE_REQUIRES_ADMIN_TIER");
    });

    it("should allow with no reason for successful access", () => {
      const { result } = renderHook(() => useUserTierStore());
      act(() => result.current.setTier("standard"));

      const decision = result.current.canAccessRouteWithReason("standard");
      expect(decision.allowed).toBe(true);
      // No 'reason' property on allowed decisions
      expect("reason" in decision).toBe(false);
    });
  });

  describe("canAccessFeature", () => {
    it("should check feature permissions for standard tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("standard"));

      expect(result.current.canAccessFeature("canAccessAdvanced")).toBe(false);
      expect(result.current.canAccessFeature("canAccessAdmin")).toBe(false);
    });

    it("should check feature permissions for advanced tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("advanced"));

      expect(result.current.canAccessFeature("canAccessAdvanced")).toBe(true);
      expect(result.current.canAccessFeature("canEditFormulas")).toBe(true);
      expect(result.current.canAccessFeature("canAccessAdmin")).toBe(false);
    });

    it("should check feature permissions for admin tier", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("admin"));

      expect(result.current.canAccessFeature("canAccessAdmin")).toBe(true);
      expect(result.current.canAccessFeature("canManageUsers")).toBe(true);
      expect(result.current.canAccessFeature("canManagePacks")).toBe(true);
    });
  });

  describe("computed properties via behavior", () => {
    // Note: Zustand getters (effectiveTier, isPrivileged) don't trigger React re-renders
    // when their dependencies change. We test the actual behavior through canAccessRoute
    // which internally uses the same effectiveTier logic.

    it("effectiveTier works - standard user can access advanced routes with advanced mode enabled", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("standard"));
      act(() => result.current.disableAdvancedMode());

      // Without advanced mode, standard user cannot access advanced routes
      expect(result.current.canAccessRoute("advanced")).toBe(false);

      act(() => result.current.enableAdvancedMode());

      // With advanced mode, effectiveTier becomes 'advanced', allowing access
      expect(result.current.canAccessRoute("advanced")).toBe(true);
    });

    it("isPrivileged works - tier-based privileges are enforced", () => {
      const { result } = renderHook(() => useUserTierStore());

      // Standard user is not privileged
      act(() => result.current.setTier("standard"));
      act(() => result.current.disableAdvancedMode());
      expect(result.current.canAccessFeature("canAccessAdvanced")).toBe(false);

      // Advanced user is privileged (can access advanced features)
      act(() => result.current.setTier("advanced"));
      expect(result.current.canAccessFeature("canAccessAdvanced")).toBe(true);

      // Admin user is fully privileged
      act(() => result.current.setTier("admin"));
      expect(result.current.canAccessFeature("canAccessAdmin")).toBe(true);
      expect(result.current.canAccessFeature("canManageUsers")).toBe(true);
    });

    it("standard user with advanced mode gains privileged access", () => {
      const { result } = renderHook(() => useUserTierStore());

      act(() => result.current.setTier("standard"));
      act(() => result.current.disableAdvancedMode());

      // Standard user without advanced mode - no advanced access
      expect(result.current.canAccessRoute("advanced")).toBe(false);
      expect(result.current.canAccessFeature("canEditFormulas")).toBe(false);

      // Enable advanced mode
      act(() => result.current.enableAdvancedMode());

      // Now has advanced access via effectiveTier logic
      expect(result.current.canAccessRoute("advanced")).toBe(true);
    });
  });
});

describe("isDenied type guard", () => {
  it("should return true for denied decisions", () => {
    const denied = { allowed: false as const, reason: "TEST_REASON" };
    expect(isDenied(denied)).toBe(true);
    // Type narrowing allows access to reason
    if (isDenied(denied)) {
      expect(denied.reason).toBe("TEST_REASON");
    }
  });

  it("should return false for allowed decisions", () => {
    const allowed = { allowed: true as const };
    expect(isDenied(allowed)).toBe(false);
  });

  it("should narrow types correctly in store context", () => {
    const { result } = renderHook(() => useUserTierStore());
    act(() => result.current.setTier("standard"));

    const decision = result.current.canAccessRouteWithReason("admin");
    expect(isDenied(decision)).toBe(true);
    expect(isDenied(decision) && decision.reason).toBe("ADMIN_ROUTE_REQUIRES_ADMIN_TIER");
  });
});

describe("validateTier helper", () => {
  it("should validate and normalize valid tiers", () => {
    expect(validateTier("standard")).toBe("standard");
    expect(validateTier("advanced")).toBe("advanced");
    expect(validateTier("admin")).toBe("admin");
  });

  it("should handle case-insensitive tier values", () => {
    expect(validateTier("STANDARD")).toBe("standard");
    expect(validateTier("Advanced")).toBe("advanced");
    expect(validateTier("ADMIN")).toBe("admin");
  });

  it("should trim whitespace from tier values", () => {
    expect(validateTier("  standard  ")).toBe("standard");
    expect(validateTier("advanced ")).toBe("advanced");
  });

  it("should return null for invalid tier values", () => {
    expect(validateTier("unknown")).toBeNull();
    expect(validateTier("hacker")).toBeNull();
    expect(validateTier("")).toBeNull();
  });

  it("should return null for non-string values", () => {
    expect(validateTier(null as unknown as string)).toBeNull();
    expect(validateTier(undefined as unknown as string)).toBeNull();
    expect(validateTier(123 as unknown as string)).toBeNull();
  });
});

describe("getRouteTier helper", () => {
  it("should return tier for exact route matches", () => {
    expect(getRouteTier("/home")).toBe("standard");
    expect(getRouteTier("/discover/extraction")).toBe("advanced");
    expect(getRouteTier("/admin")).toBe("admin");
  });

  it("should return tier for nested routes", () => {
    expect(getRouteTier("/home/dashboard")).toBe("standard");
    expect(getRouteTier("/discover/knowledge/graph/nodes")).toBe("advanced");
    expect(getRouteTier("/admin/content/formulas/versions")).toBe("admin");
  });

  // SECURITY: Fail-closed behavior - unknown routes return 'unknown' tier
  it("should return 'unknown' tier for unregistered routes (fail-closed)", () => {
    expect(getRouteTier("/unknown-route")).toBe("unknown");
    expect(getRouteTier("/new-feature")).toBe("unknown");
    expect(getRouteTier("/malicious/path")).toBe("unknown");
  });

  it("should handle root route", () => {
    expect(getRouteTier("/")).toBe("standard");
  });

  it("should return tier for canonical tenant-scoped routes", () => {
    expect(getRouteTier("/t/acme/accounts")).toBe("standard");
    expect(getRouteTier("/t/acme/accounts/acc-123/intelligence/signals")).toBe("standard");
    expect(getRouteTier("/t/acme/accounts/acc-123/studio/action-plan")).toBe("advanced");
    expect(getRouteTier("/t/acme/accounts/acc-123/deliverables/business-cases")).toBe("standard");
    expect(getRouteTier("/t/acme/context")).toBe("standard");
    expect(getRouteTier("/t/acme/governance/audit")).toBe("standard");
  });
});

describe("normalizeRoleToTier", () => {
  // Backend-canonical role tests
  it("should map super_admin to admin tier", () => {
    expect(normalizeRoleToTier("super_admin")).toBe("admin");
  });

  it("should map tenant_admin to admin tier", () => {
    expect(normalizeRoleToTier("tenant_admin")).toBe("admin");
  });

  it("should map content_admin to admin tier", () => {
    expect(normalizeRoleToTier("content_admin")).toBe("admin");
  });

  it("should map analyst to advanced tier", () => {
    expect(normalizeRoleToTier("analyst")).toBe("advanced");
  });

  it("should map read_only to standard tier", () => {
    expect(normalizeRoleToTier("read_only")).toBe("standard");
  });

  it("should map system to standard tier (fail-safe)", () => {
    expect(normalizeRoleToTier("system")).toBe("standard");
  });

  // Frontend tier passthrough tests
  it("should pass through admin tier", () => {
    expect(normalizeRoleToTier("admin")).toBe("admin");
  });

  it("should pass through advanced tier", () => {
    expect(normalizeRoleToTier("advanced")).toBe("advanced");
  });

  it("should pass through standard tier", () => {
    expect(normalizeRoleToTier("standard")).toBe("standard");
  });

  // Legacy role tests
  it("should map editor to advanced tier", () => {
    expect(normalizeRoleToTier("editor")).toBe("advanced");
  });

  it("should map viewer to standard tier", () => {
    expect(normalizeRoleToTier("viewer")).toBe("standard");
  });

  it("should map user to standard tier", () => {
    expect(normalizeRoleToTier("user")).toBe("standard");
  });

  // Case insensitivity tests
  it("should handle uppercase backend roles", () => {
    expect(normalizeRoleToTier("SUPER_ADMIN")).toBe("admin");
    expect(normalizeRoleToTier("TENANT_ADMIN")).toBe("admin");
    expect(normalizeRoleToTier("ANALYST")).toBe("advanced");
  });

  it("should handle mixed case roles", () => {
    expect(normalizeRoleToTier("Super_Admin")).toBe("admin");
    expect(normalizeRoleToTier("Content_Admin")).toBe("admin");
  });

  // SECURITY: Unknown role fail-safe tests
  it("should fail-safe to standard for unknown roles", () => {
    expect(normalizeRoleToTier("unknown")).toBe("standard");
    expect(normalizeRoleToTier("hacker")).toBe("standard");
    expect(normalizeRoleToTier("administrator")).toBe("standard");
  });

  it("should fail-safe to standard for empty/whitespace roles", () => {
    expect(normalizeRoleToTier("")).toBe("standard");
    expect(normalizeRoleToTier("   ")).toBe("standard");
  });

  it("should trim whitespace from roles", () => {
    expect(normalizeRoleToTier("  admin  ")).toBe("admin");
    expect(normalizeRoleToTier(" analyst ")).toBe("advanced");
  });
});
