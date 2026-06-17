import { describe, it, expect } from "vitest";
import {
  globalToTenantPath,
  tenantToGlobalPath,
  isTenantSettingsPath,
} from "./pathBuilder";

const SETTINGS_ROUTE_PAIRS = [
  { global: "/settings/workspace", tenant: "/settings/workspace" },
  { global: "/settings/billing", tenant: "/settings/billing" },
  { global: "/settings/billing/subscription", tenant: "/settings/billing/subscription" },
  { global: "/settings/billing/usage", tenant: "/settings/billing/usage" },
  { global: "/settings/billing/payment-methods", tenant: "/settings/billing/payment-methods" },
  { global: "/settings/billing/invoices", tenant: "/settings/billing/invoices" },
  { global: "/settings/team", tenant: "/settings/users" },
  { global: "/settings/team/invitations", tenant: "/settings/invitations" },
  { global: "/settings/team/roles", tenant: "/settings/roles" },
  { global: "/settings/team/permissions", tenant: "/settings/permissions" },
  { global: "/settings/team/api-keys", tenant: "/settings/api-keys" },
  { global: "/settings/data/sources", tenant: "/settings/data-sources" },
  { global: "/settings/data/integrations", tenant: "/settings/integrations" },
  { global: "/settings/data/variables", tenant: "/settings/variables" },
  { global: "/settings/data/value-packs", tenant: "/settings/value-packs" },
  { global: "/settings/data/ingestion-rules", tenant: "/settings/ingestion-rules" },
  { global: "/settings/governance/policies", tenant: "/settings/governance/policies" },
  { global: "/settings/governance/compliance", tenant: "/settings/governance/compliance" },
  { global: "/settings/governance/health", tenant: "/settings/governance/health" },
  { global: "/settings/governance/audit-trail", tenant: "/settings/governance/audit" },
  { global: "/settings/governance/admin-controls", tenant: "/settings/governance/admin" },
];

const PERSONAL_GLOBAL_PATHS = [
  "/personal",
  "/personal/profile",
  "/personal/security",
  "/personal/preferences",
  "/personal/notifications",
  "/personal/sessions",
  "/personal/activity",
];

describe("pathBuilder", () => {
  describe("globalToTenantPath", () => {
    it("returns global paths unchanged when tenant slug is absent", () => {
      for (const { global: g } of SETTINGS_ROUTE_PAIRS) {
        expect(globalToTenantPath(g, null)).toBe(g);
      }
      for (const path of PERSONAL_GLOBAL_PATHS) {
        expect(globalToTenantPath(path, null)).toBe(path);
      }
    });

    it("maps every settings route to the correct tenant-scoped path", () => {
      for (const { global: g, tenant: t } of SETTINGS_ROUTE_PAIRS) {
        expect(globalToTenantPath(g, "acme")).toBe(`/t/acme${t}`);
      }
    });

    it("leaves personal paths unchanged even with a tenant slug", () => {
      for (const path of PERSONAL_GLOBAL_PATHS) {
        expect(globalToTenantPath(path, "acme")).toBe(path);
      }
    });

    it("returns already-tenant-scoped paths unchanged", () => {
      expect(globalToTenantPath("/t/acme/settings/api-keys", "acme")).toBe(
        "/t/acme/settings/api-keys"
      );
    });
  });

  describe("tenantToGlobalPath", () => {
    it("returns global paths unchanged", () => {
      for (const { global: g } of SETTINGS_ROUTE_PAIRS) {
        expect(tenantToGlobalPath(g)).toBe(g);
      }
      for (const path of PERSONAL_GLOBAL_PATHS) {
        expect(tenantToGlobalPath(path)).toBe(path);
      }
    });

    it("converts every tenant-scoped settings path back to its global template", () => {
      for (const { global: g, tenant: t } of SETTINGS_ROUTE_PAIRS) {
        expect(tenantToGlobalPath(`/t/acme${t}`)).toBe(g);
      }
    });
  });

  describe("isTenantSettingsPath", () => {
    it("detects tenant-scoped settings paths", () => {
      expect(isTenantSettingsPath("/t/acme/settings/api-keys")).toBe(true);
      expect(isTenantSettingsPath("/t/acme/settings/governance/audit")).toBe(true);
    });

    it("returns false for global and personal paths", () => {
      expect(isTenantSettingsPath("/settings/team")).toBe(false);
      expect(isTenantSettingsPath("/personal/profile")).toBe(false);
      expect(isTenantSettingsPath("/")).toBe(false);
    });
  });
});
