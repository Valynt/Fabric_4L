import { describe, it, expect } from "vitest";
import { settingsCategories, settingsNavigation } from "./schemas";
import { globalToTenantPath } from "./pathBuilder";

const TENANT_SLUG = "acme";

describe("settings tenant navigation regression", () => {
  it("maps every non-personal category tab to a tenant-scoped settings path", () => {
    for (const category of settingsCategories) {
      const tenantPath = globalToTenantPath(category.basePath, TENANT_SLUG);
      if (category.basePath.startsWith("/personal")) {
        expect(tenantPath).toBe(category.basePath);
      } else {
        expect(tenantPath).toMatch(new RegExp(`^/t/${TENANT_SLUG}/settings`));
      }
    }
  });

  it("maps every non-personal subnav link to a tenant-scoped settings path", () => {
    for (const section of settingsNavigation) {
      for (const child of section.children) {
        const tenantPath = globalToTenantPath(child.path, TENANT_SLUG);
        if (child.path.startsWith("/personal")) {
          expect(tenantPath).toBe(child.path);
        } else {
          expect(tenantPath).toMatch(new RegExp(`^/t/${TENANT_SLUG}/settings`));
        }
      }
    }
  });

  it("does not produce duplicate tenant-scoped paths across subnav sections", () => {
    const seen = new Set<string>();
    for (const section of settingsNavigation) {
      for (const child of section.children) {
        const tenantPath = globalToTenantPath(child.path, TENANT_SLUG);
        if (!child.path.startsWith("/personal")) {
          expect(seen.has(tenantPath)).toBe(false);
          seen.add(tenantPath);
        }
      }
    }
  });
});
