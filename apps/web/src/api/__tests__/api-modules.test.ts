import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
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
