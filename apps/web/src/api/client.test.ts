import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/mocks/server";
import { apiClient, buildApiFetchInit } from "./client";
import {
  applySessionServiceTestEnvironment,
  authFixtures,
  type MemoryStorage,
} from "@/test/authSessionTestUtils";

describe("ApiClient", () => {
  let testSessionStorage: MemoryStorage;

  beforeEach(() => {
    ({ sessionStorage: testSessionStorage } = applySessionServiceTestEnvironment());
  });

  describe("layer routing", () => {
    it("should route l1 requests to ingestion layer", async () => {
      let capturedUrl = "";
      server.use(
        http.get("/api/v1/ingest/health", ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({ status: "ok" });
        })
      );

      await apiClient.get("l1", "/health");
      expect(capturedUrl).toContain("/api/v1/ingest/health");
    });

    it("should route l3 requests to knowledge graph layer", async () => {
      let capturedUrl = "";
      server.use(
        http.get("/api/v1/graph/entities", ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({ entities: [] });
        })
      );

      await apiClient.get("l3", "/entities");
      expect(capturedUrl).toContain("/api/v1/graph/entities");
    });

    it("should route l4 requests to agents layer", async () => {
      let capturedUrl = "";
      server.use(
        http.get("/api/v1/agents/workflows/active", ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json([]);
        })
      );

      await apiClient.get("l4", "/workflows/active");
      expect(capturedUrl).toContain("/api/v1/agents/workflows/active");
    });
  });

  describe("request configuration", () => {
    beforeEach(() => {
      testSessionStorage.clear();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it("should not include client-controlled auth or tenant headers with session metadata", async () => {
      testSessionStorage.setItem(
        "vf.auth.session.meta",
        JSON.stringify(
          authFixtures.sessionMeta({
            tenantId: "test-tenant-123",
            user: authFixtures.user({ tenantId: "test-tenant-123" }),
          })
        )
      );
      let capturedHeaders: Record<string, string> = {};

      server.use(
        http.get("/api/v1/graph/test", ({ request }) => {
          request.headers.forEach((value, key) => {
            capturedHeaders[key] = value;
          });
          return HttpResponse.json({});
        })
      );

      await apiClient.get("l3", "/test");
      expect(capturedHeaders["x-tenant-id"]).toBeUndefined();
      expect(capturedHeaders.authorization).toBeUndefined();
    });

    it("should not synthesize a default tenant header when session metadata is absent", async () => {
      let capturedHeaders: Record<string, string> = {};

      server.use(
        http.get("/api/v1/graph/test", ({ request }) => {
          request.headers.forEach((value, key) => {
            capturedHeaders[key] = value;
          });
          return HttpResponse.json({});
        })
      );

      await apiClient.get("l3", "/test");
      expect(capturedHeaders["x-tenant-id"]).toBeUndefined();
      expect(capturedHeaders.authorization).toBeUndefined();
    });

    it("builds fetch init with credentials, correlation, and CSRF for mutating requests", () => {
      document.cookie = "vf_csrf_token=test-csrf-token";

      const init = buildApiFetchInit({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ok: true }),
      });

      const headers = init.headers as Record<string, string>;
      expect(init.credentials).toBe("include");
      expect(headers["Content-Type"]).toBe("application/json");
      expect(headers["X-CSRF-Token"]).toBe("test-csrf-token");
      expect(headers["X-Request-ID"]).toMatch(/^req_/);
      expect(headers["X-Tenant-ID"]).toBeUndefined();
    });
  });

  describe("request deduplication", () => {
    it("shares identical in-flight GET requests", async () => {
      let requestCount = 0;
      server.use(
        http.get("/api/v1/graph/deduped", async () => {
          requestCount += 1;
          await new Promise((resolve) => setTimeout(resolve, 25));
          return HttpResponse.json({ ok: true });
        })
      );

      await Promise.all([
        apiClient.get("l3", "/deduped"),
        apiClient.get("l3", "/deduped"),
      ]);

      expect(requestCount).toBe(1);
    });

    it("does not deduplicate POST requests because they can be state-changing", async () => {
      let requestCount = 0;
      server.use(
        http.post("/api/v1/agents/workflows", async () => {
          requestCount += 1;
          await new Promise((resolve) => setTimeout(resolve, 25));
          return HttpResponse.json({ id: `workflow-${requestCount}` });
        })
      );

      await Promise.all([
        apiClient.post("l4", "/workflows", { name: "same" }),
        apiClient.post("l4", "/workflows", { name: "same" }),
      ]);

      expect(requestCount).toBe(2);
    });
  });

  describe("error handling", () => {
    it("redirects to /sign-in on 401", async () => {
      const locationMock = { ...window.location, replace: vi.fn(), href: "http://localhost:3000/home" };
      Object.defineProperty(window, "location", { value: locationMock, writable: true, configurable: true });

      server.use(
        http.get("/api/v1/graph/test", () => {
          return HttpResponse.json({ error: { message: "Authentication required", code: "AUTHENTICATION_ERROR", request_id: "trace-401" } }, { status: 401 });
        })
      );

      try {
        await apiClient.get("l3", "/test");
      } catch {
        /* expected */
      }

      expect(locationMock.replace).toHaveBeenCalledWith(expect.stringContaining('/sign-in'));
    });

    it("redirects to /forbidden on 403", async () => {
      const locationMock = { ...window.location, replace: vi.fn(), href: "http://localhost:3000/t/acme/accounts/a-1" };
      Object.defineProperty(window, "location", { value: locationMock, writable: true, configurable: true });

      server.use(
        http.get("/api/v1/graph/test", () => {
          return HttpResponse.json({ error: { message: "Access denied", code: "AUTHORIZATION_ERROR", request_id: "trace-403" } }, { status: 403 });
        })
      );

      try {
        await apiClient.get("l3", "/test");
      } catch {
        /* expected */
      }

      expect(locationMock.replace).toHaveBeenCalledWith("/forbidden");
    });

    it("should throw on network errors", async () => {
      server.use(
        http.get("/api/v1/graph/test", () => {
          return HttpResponse.error();
        })
      );

      // Wrap in try/catch to prevent unhandled rejection warning
      let error: Error | undefined;
      try {
        await apiClient.get("l3", "/test");
      } catch (e) {
        error = e as Error;
      }
      expect(error).toBeDefined();
    });

    it("should throw on HTTP error status", async () => {
      server.use(
        http.get("/api/v1/graph/test", () => {
          return HttpResponse.json({ error: "Server Error" }, { status: 500 });
        })
      );

      // Wrap in try/catch to prevent unhandled rejection warning
      let error: Error | undefined;
      try {
        await apiClient.get("l3", "/test");
      } catch (e) {
        error = e as Error;
      }
      expect(error).toBeDefined();
      expect(error?.message).toContain("Request failed with status code 500");
    });
  });

  describe("URL construction contract (FE-001 regression protection)", () => {
    it("never produces duplicate /v1/ segments", async () => {
      const testCases = ["l1", "l2", "l3", "l4", "l5", "l6"] as const;
      const capturedUrls: string[] = [];

      server.use(
        http.get("/api/v1/:layer/*", ({ request }) => {
          capturedUrls.push(request.url);
          return HttpResponse.json({});
        })
      );

      for (const layer of testCases) {
        try {
          await apiClient.get(layer, "/test");
        } catch {
          // Expected - handler returns empty, may throw
        }
      }

      for (const url of capturedUrls) {
        const pathname = new URL(url).pathname;
        expect(pathname).not.toMatch(/\/v1\/v1\//);
        expect(pathname).not.toMatch(/\/v1$/);
        expect(pathname).toMatch(/^\/api\/v1\/\w+/);
      }
    });

    it("correctly composes /api/v1 + /benchmarks -> /api/v1/benchmarks", async () => {
      let capturedUrl = "";

      server.use(
        http.get("/api/v1/benchmarks/datasets", ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({ data: [] });
        })
      );

      await apiClient.get("l6", "/datasets");
      expect(capturedUrl).toContain("/api/v1/benchmarks/datasets");
      expect(capturedUrl).not.toContain("/v1/v1/");
    });

    it("correctly composes all layer prefixes", async () => {
      const expectations: Record<string, string> = {
        l1: "/api/v1/ingest/health",
        l2: "/api/v1/extract/jobs",
        l3: "/api/v1/graph/entities",
        l4: "/api/v1/agents/workflows",
        l5: "/api/v1/truths/audit",
        l6: "/api/v1/benchmarks/datasets",
      };

      for (const [layer, expectedPath] of Object.entries(expectations)) {
        let capturedUrl = "";

        server.use(
          http.get(expectedPath, ({ request }) => {
            capturedUrl = request.url;
            return HttpResponse.json({});
          })
        );

        const endpoint = expectedPath.split("/").pop() || "/test";
        await apiClient.get(layer as "l1" | "l2" | "l3" | "l4" | "l5" | "l6", "/" + endpoint);
        expect(capturedUrl).toContain(expectedPath);
      }
    });
  });
});
