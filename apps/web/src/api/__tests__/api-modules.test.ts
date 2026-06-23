import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { getEntitlementDecision } from "@/api/billing";
import {
  search,
  generateSearchResultUrl,
  isSafeSearchResultUrl,
  getSearchResultTypeLabel,
  getSearchResultTypeIcon,
} from "@/api/search";
import {
  getValueTree,
  getValueTreePaths,
  createValueTree,
  importValueTree,
} from "@/api/valueTrees";
import { workflowApi, analysisApi } from "@/api/workflows";

describe("billing API", () => {
  it("getEntitlementDecision calls l7 billing endpoint", async () => {
    server.use(
      http.get("/api/v1/billing/billing/entitlements/plan-123/decision", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("feature")).toBe("signals");
        return HttpResponse.json({
          tenant_id: "t1",
          plan_id: "plan-123",
          feature: "signals",
          allowed: true,
          policy: "pro",
        });
      })
    );

    const result = await getEntitlementDecision("plan-123", "signals");
    expect(result.allowed).toBe(true);
    expect(result.policy).toBe("pro");
  });
});

describe("search API", () => {
  it("search builds query params and calls l3", async () => {
    server.use(
      http.get("/api/v1/graph/v1/search", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("q")).toBe("acme");
        expect(url.searchParams.get("scope")).toBe("global");
        expect(url.searchParams.get("limit")).toBe("10");
        return HttpResponse.json({ results: [], total: 0 });
      })
    );

    const result = await search({ q: "acme", scope: "global", limit: 10 });
    expect(result.total).toBe(0);
  });

  it("search omits undefined optional params", async () => {
    server.use(
      http.get("/api/v1/graph/v1/search", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.has("scope")).toBe(false);
        expect(url.searchParams.has("account_id")).toBe(false);
        expect(url.searchParams.has("types")).toBe(false);
        expect(url.searchParams.has("cursor")).toBe(false);
        return HttpResponse.json({ results: [], total: 0 });
      })
    );

    await search({ q: "test" });
  });

  it("generateSearchResultUrl returns existing url when tenant-scoped", () => {
    const result = { id: "1", type: "account" as const, title: "Acme", url: "/t/slug/accounts/1" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/accounts/1");
  });

  it("generateSearchResultUrl prepends tenant scope when missing", () => {
    const result = { id: "1", type: "account" as const, title: "Acme", url: "/accounts/1" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/accounts/1");
  });

  it("generateSearchResultUrl handles account with account_id", () => {
    const result = { id: "1", type: "account" as const, title: "Acme", account_id: "acc-2" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/accounts/acc-2");
  });

  it("generateSearchResultUrl handles signal type", () => {
    const result = { id: "1", type: "signal" as const, title: "S" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/intelligence/signals/1");
  });

  it("generateSearchResultUrl handles evidence type", () => {
    const result = { id: "1", type: "evidence" as const, title: "E" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/governance/evidence/1");
  });

  it("generateSearchResultUrl handles value_case type", () => {
    const result = { id: "1", type: "value_case" as const, title: "V" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/deliverables/cases/1");
  });

  it("generateSearchResultUrl handles formula type", () => {
    const result = { id: "1", type: "formula" as const, title: "F" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/calculator/formulas/1");
  });

  it("generateSearchResultUrl handles benchmark type", () => {
    const result = { id: "1", type: "benchmark" as const, title: "B" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/benchmarks/1");
  });

  it("generateSearchResultUrl handles value_pack type", () => {
    const result = { id: "1", type: "value_pack" as const, title: "P" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/value-packs/1");
  });

  it("generateSearchResultUrl handles graph_entity type", () => {
    const result = { id: "1", type: "graph_entity" as const, title: "G" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/graph/entities/1");
  });

  it("generateSearchResultUrl handles agent_thread type", () => {
    const result = { id: "1", type: "agent_thread" as const, title: "A" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/agents/threads/1");
  });

  it("generateSearchResultUrl handles workflow_run type", () => {
    const result = { id: "1", type: "workflow_run" as const, title: "W" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/workflows/runs/1");
  });

  it("generateSearchResultUrl handles deliverable type", () => {
    const result = { id: "1", type: "deliverable" as const, title: "D" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/deliverables/1");
  });

  it("generateSearchResultUrl falls back to search for unknown type", () => {
    const result = { id: "1", type: "unknown_type" as any, title: "U" };
    expect(generateSearchResultUrl(result, "slug")).toBe("/t/slug/search?q=U");
  });

  it("isSafeSearchResultUrl validates tenant prefix", () => {
    expect(isSafeSearchResultUrl("/t/slug/accounts/1", "slug")).toBe(true);
    expect(isSafeSearchResultUrl("/other/accounts/1", "slug")).toBe(false);
  });

  it("getSearchResultTypeLabel returns correct labels", () => {
    expect(getSearchResultTypeLabel("account")).toBe("Account");
    expect(getSearchResultTypeLabel("signal")).toBe("Signal");
    expect(getSearchResultTypeLabel("unknown_type" as any)).toBe("unknown_type");
  });

  it("getSearchResultTypeIcon returns correct icons", () => {
    expect(getSearchResultTypeIcon("account")).toBe("Building2");
    expect(getSearchResultTypeIcon("signal")).toBe("Activity");
    expect(getSearchResultTypeIcon("unknown_type" as any)).toBe("Search");
  });
});

describe("valueTrees API", () => {
  it("getValueTree calls l3 with encoded params", async () => {
    server.use(
      http.get("/api/v1/graph/value-trees/entity-123", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("direction")).toBe("upward");
        expect(url.searchParams.get("max_depth")).toBe("4");
        return HttpResponse.json({
          root_entity_id: "entity-123",
          direction: "upward",
          nodes: [],
          edges: [],
          paths: [],
          stats: { total_nodes: 0, total_edges: 0, by_layer: {}, max_depth: 1 },
        });
      })
    );

    const result = await getValueTree("entity-123");
    expect(result.root_entity_id).toBe("entity-123");
  });

  it("getValueTree clamps maxDepth", async () => {
    server.use(
      http.get("/api/v1/graph/value-trees/entity-123", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("max_depth")).toBe("4");
        return HttpResponse.json({
          root_entity_id: "entity-123",
          direction: "upward",
          nodes: [],
          edges: [],
          paths: [],
          stats: { total_nodes: 0, total_edges: 0, by_layer: {}, max_depth: 1 },
        });
      })
    );

    await getValueTree("entity-123", "upward", 99);
  });

  it("getValueTreePaths calls paths endpoint", async () => {
    server.use(
      http.get("/api/v1/graph/value-trees/entity-123/paths", () => {
        return HttpResponse.json([]);
      })
    );

    const result = await getValueTreePaths("entity-123");
    expect(result).toEqual([]);
  });

  it("createValueTree posts to l3", async () => {
    server.use(
      http.post("/api/v1/graph/value-trees", async ({ request }) => {
        const body = await request.json();
        expect(body).toMatchObject({ entity_id: "e1" });
        return HttpResponse.json({
          root_entity_id: "e1",
          direction: "upward",
          nodes: [],
          edges: [],
          paths: [],
          stats: { total_nodes: 0, total_edges: 0, by_layer: {}, max_depth: 1 },
        });
      })
    );

    const result = await createValueTree({ entity_id: "e1" });
    expect(result.root_entity_id).toBe("e1");
  });

  it("importValueTree posts to import endpoint", async () => {
    server.use(
      http.post("/api/v1/graph/value-trees/import", async ({ request }) => {
        const body = await request.json();
        expect(body.entity_id).toBe("e1");
        return HttpResponse.json({
          root_entity_id: "e1",
          direction: "upward",
          nodes: [],
          edges: [],
          paths: [],
          stats: { total_nodes: 0, total_edges: 0, by_layer: {}, max_depth: 1 },
        });
      })
    );

    const tree = {
      root_entity_id: "e1",
      direction: "upward" as const,
      nodes: [],
      edges: [],
      paths: [],
      stats: { total_nodes: 0, total_edges: 0, by_layer: {}, max_depth: 1 },
    };
    const result = await importValueTree({ entity_id: "e1", tree });
    expect(result.root_entity_id).toBe("e1");
  });
});

describe("workflows API", () => {
  it("workflowApi.create posts to l4", async () => {
    server.use(
      http.post("/api/v1/agents/workflows", async ({ request }) => {
        const body = await request.json();
        expect(body.workflow_type).toBe("roi_calculator");
        return HttpResponse.json({
          workflow_instance_id: "wf-1",
          status: "queued",
          estimated_duration_seconds: 60,
        });
      })
    );

    const result = await workflowApi.create({ workflow_type: "roi_calculator" });
    expect(result.workflow_instance_id).toBe("wf-1");
  });

  it("workflowApi.getStatus fetches from l4", async () => {
    server.use(
      http.get("/api/v1/agents/workflows/wf-1", () => {
        return HttpResponse.json({
          workflow_instance_id: "wf-1",
          workflow_type: "roi_calculator",
          status: "running",
          current_state: "extracting",
          current_node: null,
          progress_percentage: 50,
          started_at: new Date().toISOString(),
          completed_at: null,
          error_count: 0,
          has_output: false,
          results: null,
          tenant_id: "t1",
          user_id: "u1",
          priority: 1,
          scheduler_status: "scheduled",
          progress: null,
        });
      })
    );

    const result = await workflowApi.getStatus("wf-1");
    expect(result.status).toBe("running");
  });

  it("workflowApi.getResult fetches result", async () => {
    server.use(
      http.get("/api/v1/agents/workflows/wf-1/result", () => {
        return HttpResponse.json({
          workflow_id: "wf-1",
          status: "completed",
          output: { summary: "Done" },
          errors: [],
          completed_at: new Date().toISOString(),
        });
      })
    );

    const result = await workflowApi.getResult("wf-1");
    expect(result.status).toBe("completed");
  });

  it("workflowApi.listActive fetches active workflows", async () => {
    server.use(
      http.get("/api/v1/agents/workflows/active", () => {
        return HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0, has_more: false });
      })
    );

    const result = await workflowApi.listActive();
    expect(result.total).toBe(0);
  });

  it("workflowApi.listTypes fetches workflow types", async () => {
    server.use(
      http.get("/api/v1/agents/workflows/types", () => {
        return HttpResponse.json({ workflows: [] });
      })
    );

    const result = await workflowApi.listTypes();
    expect(result.workflows).toEqual([]);
  });

  it("workflowApi.cancel deletes workflow", async () => {
    server.use(
      http.delete("/api/v1/agents/workflows/wf-1", () => {
        return HttpResponse.json({ workflow_id: "wf-1", status: "cancelled" });
      })
    );

    const result = await workflowApi.cancel("wf-1");
    expect(result.status).toBe("cancelled");
  });

  it("workflowApi.resume posts resume data", async () => {
    server.use(
      http.post("/api/v1/agents/workflows/wf-1/resume", async ({ request }) => {
        const body = await request.json();
        expect(body.user_id).toBe("u1");
        return HttpResponse.json({
          workflow_instance_id: "wf-1",
          status: "resumed",
          resumed_from_node: null,
          message: "Resumed",
          estimated_completion_seconds: 30,
        });
      })
    );

    const result = await workflowApi.resume("wf-1", { user_id: "u1" });
    expect(result.status).toBe("resumed");
  });

  it("workflowApi.pause posts pause data", async () => {
    server.use(
      http.post("/api/v1/agents/workflows/wf-1/pause", async ({ request }) => {
        const body = await request.json();
        expect(body.user_id).toBe("u1");
        return HttpResponse.json({ ok: true });
      })
    );

    const result = await workflowApi.pause("wf-1", { user_id: "u1" });
    expect(result.ok).toBe(true);
  });

  it("analysisApi.roi posts to analysis endpoint", async () => {
    server.use(
      http.post("/api/v1/agents/analysis/roi", async ({ request }) => {
        const body = await request.json();
        expect(body.prospect_id).toBe("p1");
        return HttpResponse.json({
          prospect_id: "p1",
          aggregated_roi: {},
          detailed_results: [],
          benchmark_comparison: null,
        });
      })
    );

    const result = await analysisApi.roi({ prospect_id: "p1", value_driver_ids: ["vd1"] });
    expect(result.prospect_id).toBe("p1");
  });

  it("analysisApi.whitespace posts to analysis endpoint", async () => {
    server.use(
      http.post("/api/v1/agents/analysis/whitespace", async ({ request }) => {
        const body = await request.json();
        expect(body.prospect_id).toBe("p1");
        return HttpResponse.json({
          prospect_id: "p1",
          extracted_needs: [],
          gap_analysis: [],
          opportunity_score: 0.5,
          recommendations: [],
        });
      })
    );

    const result = await analysisApi.whitespace({ prospect_id: "p1", prospect_needs: "needs" });
    expect(result.prospect_id).toBe("p1");
  });
});
