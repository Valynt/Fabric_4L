import { describe, expect, it } from "vitest";
import { deliverableRoutes } from "./deliverableRoutes";

describe("deliverableRoutes", () => {
  const tenantSlug = "acme";
  const accountId = "acct-1";

  describe("businessCaseDetail", () => {
    it("builds the correct path for a given caseId", () => {
      expect(deliverableRoutes.businessCaseDetail(tenantSlug, accountId, "case-123")).toBe(
        "/t/acme/accounts/acct-1/deliverables/business-cases/case-123"
      );
    });

    it("handles caseIds with special characters by passing them through", () => {
      expect(deliverableRoutes.businessCaseDetail(tenantSlug, accountId, "abc-def-456")).toBe(
        "/t/acme/accounts/acct-1/deliverables/business-cases/abc-def-456"
      );
    });

    it("returns a string starting with /t/", () => {
      const path = deliverableRoutes.businessCaseDetail(tenantSlug, accountId, "x");
      expect(path).toMatch(/^\/t\//);
    });
  });

  describe("businessCaseList", () => {
    it("returns the deliverables list path", () => {
      expect(deliverableRoutes.businessCaseList(tenantSlug, accountId)).toBe(
        "/t/acme/accounts/acct-1/deliverables/business-cases"
      );
    });

    it("returns a consistent value on repeated calls", () => {
      expect(deliverableRoutes.businessCaseList(tenantSlug, accountId)).toBe(
        deliverableRoutes.businessCaseList(tenantSlug, accountId)
      );
    });
  });
});
