import { describe, expect, it } from "vitest";
import {
  getSettingsCapabilityForPath,
  governanceAdminControlMetrics,
} from "./schemas";

describe("settings schema helpers", () => {
  it("maps canonical settings paths to their capability group", () => {
    expect(getSettingsCapabilityForPath("/personal/profile")).toBe("personal");
    expect(getSettingsCapabilityForPath("/settings/workspace")).toBe("billing");
    expect(getSettingsCapabilityForPath("/settings/api-keys")).toBe("team");
    expect(getSettingsCapabilityForPath("/settings/value-packs")).toBe("integrations");
    expect(getSettingsCapabilityForPath("/settings/governance/admin")).toBe("governance");
  });

  it("keeps admin control metrics in the shared schema", () => {
    expect(governanceAdminControlMetrics.map((metric) => metric.key)).toEqual([
      "tenantStatus",
      "mfaRequirement",
      "sessionTimeout",
      "auditTrail",
    ]);
  });
});
