import { describe, it, expect } from "vitest";
import { SSO_PROVIDER_TENANT, isValidSSOProvider, getSSOTenantSlug } from "./auth";

describe("auth config", () => {
  it("SSO_PROVIDER_TENANT has expected keys", () => {
    expect(Object.keys(SSO_PROVIDER_TENANT)).toContain("apple");
    expect(Object.keys(SSO_PROVIDER_TENANT)).toContain("google");
    expect(Object.keys(SSO_PROVIDER_TENANT)).toContain("microsoft");
  });

  it("isValidSSOProvider returns true for known providers", () => {
    expect(isValidSSOProvider("apple")).toBe(true);
    expect(isValidSSOProvider("google")).toBe(true);
    expect(isValidSSOProvider("microsoft")).toBe(true);
  });

  it("isValidSSOProvider returns false for unknown provider", () => {
    expect(isValidSSOProvider("facebook")).toBe(false);
    expect(isValidSSOProvider("")).toBe(false);
  });

  it("getSSOTenantSlug returns slug for known providers", () => {
    expect(getSSOTenantSlug("apple")).toBe(SSO_PROVIDER_TENANT.apple);
    expect(getSSOTenantSlug("google")).toBe(SSO_PROVIDER_TENANT.google);
  });

  it("getSSOTenantSlug returns null for unknown provider", () => {
    expect(getSSOTenantSlug("unknown")).toBeNull();
  });
});
