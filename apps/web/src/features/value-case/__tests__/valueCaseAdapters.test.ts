import { describe, it, expect } from "vitest";
import {
  apiCaseToArtifactVersion,
  domainDraftToApiInput,
  createVerifiedValueCaseScope,
} from "../domain/valueCaseAdapters";
import type { ApiBusinessCaseDto } from "../api/valueCaseSchemas";
import type { ValueCaseGenerationInputsDraft } from "../domain/valueCaseModels";
import type { AuthSnapshot } from "@/features/auth/authorizationContext";

describe("valueCaseAdapters", () => {
  describe("createVerifiedValueCaseScope", () => {
    it("creates scope when auth snapshot matches account route", () => {
      const authSnapshot = {
        state: "authenticated",
        tenantId: "tenant-1",
        accountScope: {
          scopeType: "account",
          accountId: "acc-1",
        },
      } as unknown as AuthSnapshot;

      const scope = createVerifiedValueCaseScope("acc-1", authSnapshot);
      expect(scope).not.toBeNull();
      expect(scope?.fabricTenantId).toBe("tenant-1");
      expect(scope?.accountId).toBe("acc-1");
    });

    it("returns null when auth snapshot is unauthenticated or loading", () => {
      const authSnapshot = {
        state: "loading",
        tenantId: null,
      } as unknown as AuthSnapshot;

      expect(createVerifiedValueCaseScope("acc-1", authSnapshot)).toBeNull();
    });

    it("returns null when accountId does not match route", () => {
      const authSnapshot = {
        state: "authenticated",
        tenantId: "tenant-1",
        accountScope: {
          scopeType: "account",
          accountId: "acc-2",
        },
      } as unknown as AuthSnapshot;

      expect(createVerifiedValueCaseScope("acc-1", authSnapshot)).toBeNull();
    });
  });

  describe("apiCaseToArtifactVersion", () => {
    it("maps raw API DTO into immutable domain entity", () => {
      const dto: ApiBusinessCaseDto = {
        id: "bc-1",
        account_id: "acc-1",
        title: "Value Case — Acme",
        status: "published",
        audit: {
          created_at: "2026-03-01T12:00:00.000Z",
          updated_at: "2026-03-02T12:00:00.000Z",
        },
        executive_summary: "High business impact.",
        value_case: {
          inputs: {
            account_id: "acc-1",
            account_name: "Acme",
            stakeholders: ["CFO"],
            accepted_evidence: ["Reduced OPEX"],
            scenario_assumptions: [],
            roi_metrics: {
              three_year_value: "$1.5M",
              roi: "150%",
              payback: "8 months",
            },
            risk_notes: ["Vendor lock-in"],
          },
          sections: [
            {
              id: "sec-1",
              type: "executive_summary",
              title: "Executive Summary",
              content: "High business impact.",
              order: 0,
            },
          ],
          stakeholder_framing: [
            {
              persona: "CFO",
              priorities: ["Cost containment"],
              pains: ["Manual reporting"],
              decision_role: "Economic Buyer",
            },
          ],
          assumption_ids: [],
          evidence_ids: [],
          claim_ids: [],
        },
        assumptions: [],
        risks: ["Vendor lock-in"],
      };

      const domain = apiCaseToArtifactVersion(dto, 2);

      expect(domain.id).toBe("bc-1");
      expect(domain.accountId).toBe("acc-1");
      expect(domain.version).toBe(2);
      expect(domain.status).toBe("published");
      expect(domain.businessCase.summary).toBe("High business impact.");
      expect(domain.businessCase.metrics.threeYearValue).toBe("$1.5M");
      expect(domain.stakeholderFraming[0]?.role).toBe("CFO");
      expect(domain.stakeholderFraming[0]?.valueMessage).toContain("Cost containment");
    });
  });

  describe("domainDraftToApiInput", () => {
    it("serializes domain draft to API DTO", () => {
      const scope = {
        fabricTenantId: "tenant-1",
        tenantSlug: "default",
        accountId: "acc-1",
      };
      const draft: ValueCaseGenerationInputsDraft = {
        stakeholders: ["CEO", "CFO"],
        acceptedEvidence: ["Faster delivery"],
        scenarioAssumptions: ["Base growth"],
        roiMetrics: {
          threeYearValue: "$3M",
          roi: "300%",
          payback: "4 months",
        },
        riskNotes: ["Change management"],
      };

      const dto = domainDraftToApiInput(draft, scope, "Acme Corp");

      expect(dto.account_id).toBe("acc-1");
      expect(dto.account_name).toBe("Acme Corp");
      expect(dto.stakeholders).toEqual(["CEO", "CFO"]);
      expect(dto.roi_metrics.three_year_value).toBe("$3M");
      expect(dto.risk_notes).toEqual(["Change management"]);
    });
  });
});
