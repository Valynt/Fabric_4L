import { beforeEach, describe, expect, it } from "vitest";
import { normalizeRoleToTier, useUserTierStore } from "./userTierStore";

describe("role-to-tier display compatibility", () => {
  beforeEach(() =>
    useUserTierStore.setState({ currentTier: "standard", userRole: null })
  );

  it("retains known display mappings", () => {
    expect(normalizeRoleToTier("tenant_admin")).toBe("admin");
    expect(normalizeRoleToTier("analyst")).toBe("advanced");
    expect(normalizeRoleToTier("viewer")).toBe("standard");
  });

  it.each(["unknown_role", "", "   ", undefined, null, 42])(
    "leaves malformed or unknown role unresolved: %p",
    role => {
      expect(normalizeRoleToTier(role)).toBe("unknown");
    }
  );

  it("actively clears a previously privileged compatibility tier", () => {
    useUserTierStore.setState({ currentTier: "admin" });
    useUserTierStore.getState().setUserRole("custom:unmapped");
    expect(useUserTierStore.getState().currentTier).toBe("unknown");
  });

  it("cannot independently grant routes, features, or permissions", () => {
    useUserTierStore.getState().setUserRole("tenant_admin");
    const state = useUserTierStore.getState();
    expect(state.canAccessRoute("standard")).toBe(false);
    expect(state.canAccessFeature("canManageUsers")).toBe(false);
    expect(Object.values(state.permissions).some(Boolean)).toBe(false);
  });
});
