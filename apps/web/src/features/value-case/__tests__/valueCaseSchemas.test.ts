import { describe, it, expect } from "vitest";
import {
  valueCaseSectionSchema,
  valueCaseArtifactsInputSchema,
  apiBusinessCaseSchema,
  normalizeBoundaryError,
  ValueCaseBoundaryError,
} from "../api/valueCaseSchemas";

describe("valueCaseSchemas", () => {
  describe("valueCaseSectionSchema", () => {
    it("validates a valid section", () => {
      const valid = {
        id: "sec-1",
        type: "executive_summary",
        title: "Executive Summary",
        content: "Summary text",
        order: 1,
      };
      const result = valueCaseSectionSchema.safeParse(valid);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.title).toBe("Executive Summary");
      }
    });

    it("rejects section missing required fields", () => {
      const invalid = {
        id: "sec-1",
        type: "executive_summary",
      };
      const result = valueCaseSectionSchema.safeParse(invalid);
      expect(result.success).toBe(false);
    });
  });

  describe("valueCaseArtifactsInputSchema", () => {
    it("validates complete input DTO", () => {
      const valid = {
        account_id: "acc-1",
        account_name: "Acme Corp",
        stakeholders: ["CFO", "CTO"],
        accepted_evidence: ["High ROI"],
        scenario_assumptions: ["Growth 10%"],
        roi_metrics: {
          three_year_value: "$2.5M",
          roi: "250%",
          payback: "6 months",
        },
        risk_notes: ["Implementation risk"],
      };
      const result = valueCaseArtifactsInputSchema.safeParse(valid);
      expect(result.success).toBe(true);
    });

    it("defaults optional arrays to empty array", () => {
      const minimal = {
        account_id: "acc-1",
        account_name: "Acme Corp",
      };
      const result = valueCaseArtifactsInputSchema.safeParse(minimal);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.stakeholders).toEqual([]);
        expect(result.data.accepted_evidence).toEqual([]);
        expect(result.data.roi_metrics.three_year_value).toBe("");
      }
    });
  });

  describe("apiBusinessCaseSchema", () => {
    it("validates business case payload with defaults", () => {
      const payload = {
        id: "bc-1",
        account_id: "acc-1",
        title: "Acme Value Case",
        status: "draft",
        audit: {
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-02T00:00:00Z",
        },
      };
      const result = apiBusinessCaseSchema.safeParse(payload);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.id).toBe("bc-1");
        expect(result.data.status).toBe("draft");
        expect(result.data.assumptions).toEqual([]);
        expect(result.data.risks).toEqual([]);
      }
    });
  });

  describe("normalizeBoundaryError", () => {
    it("returns boundary error as is", () => {
      const boundaryError = new ValueCaseBoundaryError(
        "Validation failed",
        "validation_failed",
        400
      );
      const normalized = normalizeBoundaryError(boundaryError);
      expect(normalized).toBe(boundaryError);
    });

    it("normalizes Error object", () => {
      const err = new Error("Network timeout");
      const normalized = normalizeBoundaryError(err);
      expect(normalized.message).toBe("Network timeout");
      expect(normalized.code).toBe("transport_error");
    });

    it("normalizes string or unknown error", () => {
      const normalized = normalizeBoundaryError("Something went wrong");
      expect(normalized.message).toBe("Something went wrong");
      expect(normalized.code).toBe("unknown_error");
    });
  });
});
