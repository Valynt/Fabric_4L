import { describe, expect, it } from "vitest";

import {
  parseFreshnessSummaryResponse,
  parseMaturityLadderResponse,
  parseStaleTruthsResponse,
  parseTruthObjectListResponse,
  parseValidationEventListResponse,
} from "./groundTruthGovernance";

const validTruth = {
  id: "truth-1",
  claim: "Customers reduce manual research by 30%",
  claim_type: "efficiency_gain",
  confidence: 0.87,
  status: "validated",
  maturity_level: 4,
  is_stale: false,
  source_count: 3,
  validated_by: "reviewer@example.com",
  freshness: "fresh",
  created_at: "2026-01-01T00:00:00Z",
};

describe("ground-truth governance runtime-boundary parsers", () => {
  it("parses a valid truth-object list response and preserves passthrough fields", () => {
    const result = parseTruthObjectListResponse({
      items: [{ ...validTruth, reviewer_queue: "principal" }],
      total: 1,
      limit: 25,
      offset: 0,
      has_more: false,
      backend_cursor: "cursor-1",
    });

    expect(result.items).toHaveLength(1);
    expect(result.items[0]?.reviewer_queue).toBe("principal");
    expect(result.backend_cursor).toBe("cursor-1");
  });

  it("rejects invalid truth status values", () => {
    expect(() =>
      parseTruthObjectListResponse({
        items: [{ ...validTruth, status: "pending_review" }],
        total: 1,
        limit: 25,
        offset: 0,
        has_more: false,
      })
    ).toThrowError();
  });

  it("rejects negative truth list pagination totals", () => {
    expect(() =>
      parseTruthObjectListResponse({
        items: [validTruth],
        total: -1,
        limit: 25,
        offset: 0,
        has_more: false,
      })
    ).toThrowError();
  });

  it("parses validation-event arrays", () => {
    const result = parseValidationEventListResponse([
      {
        id: "event-1",
        from_status: "proposed",
        to_status: "validated",
        from_maturity: 1,
        to_maturity: 4,
        actor: "analyst@example.com",
        actor_type: "user",
        confidence_at_transition: 0.8,
        source_count_at_transition: 3,
        notes: "Evidence validated",
        created_at: "2026-01-02T00:00:00Z",
      },
    ]);

    expect(result[0]?.to_status).toBe("validated");
    expect(result[0]?.to_maturity).toBe(4);
  });

  it("rejects malformed validation-event arrays", () => {
    expect(() =>
      parseValidationEventListResponse([
        {
          id: "event-1",
          to_status: "validated",
          to_maturity: "level-two",
          actor_type: "user",
          created_at: "2026-01-02T00:00:00Z",
        },
      ])
    ).toThrowError();
  });

  it("parses freshness summary envelopes", () => {
    const result = parseFreshnessSummaryResponse({
      tenant_id: "tenant-1",
      timestamp: "2026-01-02T00:00:00Z",
      summary: { stale: 2, fresh: 7, expiring_soon: 1, total: 10 },
      warning_threshold_days: 14,
    });

    expect(result.summary.stale).toBe(2);
    expect(result.summary.total).toBe(10);
    expect(result.warning_threshold_days).toBe(14);
  });

  it("rejects invalid freshness summary counts", () => {
    expect(() =>
      parseFreshnessSummaryResponse({
        tenant_id: "tenant-1",
        timestamp: "2026-01-02T00:00:00Z",
        summary: { stale: -1, fresh: 7, expiring_soon: 1, total: 10 },
        warning_threshold_days: 14,
      })
    ).toThrowError();
  });

  it("normalizes bare stale-truth arrays into paginated responses", () => {
    const result = parseStaleTruthsResponse([validTruth], {
      limit: 50,
      offset: 10,
    });

    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(1);
    expect(result.limit).toBe(50);
    expect(result.offset).toBe(10);
    expect(result.has_more).toBe(false);
  });

  it("parses stale-truth envelopes without overriding backend pagination", () => {
    const result = parseStaleTruthsResponse({
      items: [validTruth],
      total: 4,
      limit: 1,
      offset: 2,
      has_more: true,
    });

    expect(result.total).toBe(4);
    expect(result.limit).toBe(1);
    expect(result.offset).toBe(2);
    expect(result.has_more).toBe(true);
  });

  it("rejects malformed stale truth entries", () => {
    expect(() =>
      parseStaleTruthsResponse([
        {
          ...validTruth,
          claim_type: "unsupported_claim_type",
        },
      ])
    ).toThrowError();
  });

  it("parses maturity ladder responses", () => {
    const result = parseMaturityLadderResponse({
      levels: [
        {
          level: 1,
          name: "Extracted",
          description: "Claim extracted from source material",
          required_status: "extracted",
          advancement_trigger: "initial extraction",
        },
      ],
    });

    expect(result.levels[0]?.name).toBe("Extracted");
  });

  it("rejects malformed maturity ladder responses", () => {
    expect(() =>
      parseMaturityLadderResponse({
        levels: [
          {
            level: 1,
            name: "Extracted",
            description: "Claim extracted from source material",
            required_status: "extracted",
          },
        ],
      })
    ).toThrowError();
  });
});
