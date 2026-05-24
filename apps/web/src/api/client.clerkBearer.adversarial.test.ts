/**
 * Phase 2 — adversarial / hardening tests for the API client's Clerk Bearer
 * attachment. These tests are the source-of-truth for the security
 * invariants documented in the Phase 2 audit:
 *
 *   I1. Authorization: Bearer <token> attaches ONLY in Clerk mode AND ONLY
 *       when the token survives sanitization.
 *   I2. Legacy mode NEVER attaches Authorization, even if a Clerk token
 *       getter is somehow registered (defense-in-depth).
 *   I3. Token getter that returns null/undefined/"" → no header.
 *   I4. Token getter that returns whitespace-only → no header.
 *   I5. Token getter that returns a value containing CR/LF/control chars
 *       → no header and no injected adjacent header.
 *   I6. Token getter that throws or rejects → no header and request still
 *       completes (no unhandled rejection escapes the interceptor).
 *   I7. The browser NEVER sends X-Tenant-ID. Tenant authority is server-side.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";

import { server } from "../test/mocks/server";
import {
  _resetClerkSessionForTests,
  setClerkTokenGetter,
} from "@/auth/clerkSession";
import { setAuthProvider, withAuthProvider } from "@/test/utils/withAuthProvider";
import { apiClient } from "./client";

/**
 * Install an MSW handler that captures every header on the next /api/v1/ingest/health
 * GET and resolves the returned Promise with them. Each test gets its own
 * captured-headers snapshot so concurrency between tests cannot bleed.
 */
function captureNextIngestHealthHeaders(): Promise<Headers> {
  return new Promise<Headers>((resolve) => {
    server.use(
      http.get("/api/v1/ingest/health", ({ request }) => {
        resolve(request.headers);
        return HttpResponse.json({ status: "ok" });
      }),
    );
  });
}

describe("ApiClient — Clerk Bearer attachment (adversarial)", () => {
  let originalProvider: string | undefined;

  beforeEach(() => {
    originalProvider = (import.meta.env as Record<string, unknown>)
      .VITE_AUTH_PROVIDER as string | undefined;
    _resetClerkSessionForTests();
  });

  afterEach(() => {
    setAuthProvider(originalProvider);
    _resetClerkSessionForTests();
  });

  // ─────────────────────────────────────────────────────────────────────
  // I1. Happy path
  // ─────────────────────────────────────────────────────────────────────
  it("attaches Bearer <token> when AUTH_PROVIDER=clerk and token is safe", async () => {
    await withAuthProvider("clerk", async () => {
      setClerkTokenGetter(async () => "tok_phase2_abc");
      const headersPromise = captureNextIngestHealthHeaders();

      await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      expect(headers.get("authorization")).toBe("Bearer tok_phase2_abc");
    });
  });

  // ─────────────────────────────────────────────────────────────────────
  // I2. Legacy mode never sends Authorization
  // ─────────────────────────────────────────────────────────────────────
  it("does NOT attach Authorization under AUTH_PROVIDER=legacy even when a token getter is registered", async () => {
    await withAuthProvider("legacy", async () => {
      // Defense-in-depth: even if Clerk bridge code ran in legacy mode,
      // the interceptor must refuse to attach the header.
      setClerkTokenGetter(async () => "tok_must_be_ignored");
      const headersPromise = captureNextIngestHealthHeaders();

      await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      expect(headers.has("authorization")).toBe(false);
    });
  });

  it("does NOT attach Authorization when AUTH_PROVIDER is unset (defaults to legacy)", async () => {
    await withAuthProvider(undefined, async () => {
      setClerkTokenGetter(async () => "tok_unset_provider");
      const headersPromise = captureNextIngestHealthHeaders();

      await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      expect(headers.has("authorization")).toBe(false);
    });
  });

  it("does NOT attach Authorization for unknown provider values", async () => {
    // Only the exact (case-insensitive) string "clerk" enables Clerk mode.
    // Anything else (including truthy-looking strings) must fall back to legacy.
    for (const value of ["true", "1", "yes", "CLERK_MODE", "clerk-mode"]) {
      await withAuthProvider(value, async () => {
        setClerkTokenGetter(async () => "tok_should_be_ignored");
        const headersPromise = captureNextIngestHealthHeaders();

        await apiClient.get("l1", "/health");
        const headers = await headersPromise;

        expect(headers.has("authorization")).toBe(false);
      });
    }
  });

  // ─────────────────────────────────────────────────────────────────────
  // I3 / I4. Falsy / blank token values
  // ─────────────────────────────────────────────────────────────────────
  it.each([
    ["null", null],
    ["empty string", ""],
    ["single space", " "],
    ["tabs and newlines only", "\t\n "],
  ] as const)(
    "omits Authorization when token getter returns %s",
    async (_label, value) => {
      await withAuthProvider("clerk", async () => {
        setClerkTokenGetter(async () => value as string | null);
        const headersPromise = captureNextIngestHealthHeaders();

        await apiClient.get("l1", "/health");
        const headers = await headersPromise;

        expect(headers.has("authorization")).toBe(false);
      });
    },
  );

  // ─────────────────────────────────────────────────────────────────────
  // I5. Header-injection attempts
  // ─────────────────────────────────────────────────────────────────────
  it.each([
    ["CR + LF + injected header", "tok\r\nX-Admin: 1"],
    ["LF + injected header", "tok\nX-Admin: 1"],
    ["bare CR", "tok\rsuffix"],
    ["NUL byte", "tok\u0000evil"],
    ["DEL (0x7F)", "tok\u007Fevil"],
    ["unit separator (0x1F)", "tok\u001Fevil"],
  ] as const)(
    "rejects token containing %s; no Authorization and no injected adjacent header",
    async (_label, value) => {
      await withAuthProvider("clerk", async () => {
        setClerkTokenGetter(async () => value);
        const headersPromise = captureNextIngestHealthHeaders();

        await apiClient.get("l1", "/health");
        const headers = await headersPromise;

        expect(headers.has("authorization")).toBe(false);
        // Anything an attacker tries to inject must not have landed.
        expect(headers.get("x-admin")).toBeNull();
      });
    },
  );

  // ─────────────────────────────────────────────────────────────────────
  // I6. Failing token getter
  // ─────────────────────────────────────────────────────────────────────
  it("omits Authorization and completes the request when the token getter throws synchronously", async () => {
    await withAuthProvider("clerk", async () => {
      setClerkTokenGetter(() => {
        throw new Error("synchronous token failure");
      });
      const headersPromise = captureNextIngestHealthHeaders();

      const response = await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      expect(headers.has("authorization")).toBe(false);
      expect(response).toBeDefined();
    });
  });

  it("omits Authorization and completes the request when the token getter rejects", async () => {
    await withAuthProvider("clerk", async () => {
      setClerkTokenGetter(async () => {
        throw new Error("token rotation in progress");
      });
      const headersPromise = captureNextIngestHealthHeaders();

      const response = await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      expect(headers.has("authorization")).toBe(false);
      expect(response).toBeDefined();
    });
  });

  // ─────────────────────────────────────────────────────────────────────
  // I7. The browser never asserts tenancy
  // ─────────────────────────────────────────────────────────────────────
  it("never sends X-Tenant-ID (legacy mode)", async () => {
    await withAuthProvider("legacy", async () => {
      const headersPromise = captureNextIngestHealthHeaders();

      await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      expect(headers.has("x-tenant-id")).toBe(false);
      expect(headers.has("x-organization-id")).toBe(false);
    });
  });

  it("never sends X-Tenant-ID (Clerk mode, even with a signed-in session)", async () => {
    await withAuthProvider("clerk", async () => {
      setClerkTokenGetter(async () => "tok_signed_in");
      const headersPromise = captureNextIngestHealthHeaders();

      await apiClient.get("l1", "/health");
      const headers = await headersPromise;

      // Even though we have a live Clerk session, the browser must NOT
      // assert tenant identity. The gateway is the sole authority.
      expect(headers.has("x-tenant-id")).toBe(false);
      expect(headers.has("x-organization-id")).toBe(false);
    });
  });
});
