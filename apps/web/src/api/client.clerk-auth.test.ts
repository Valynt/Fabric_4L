import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/mocks/server";
import { apiClient } from "./client";
import {
  setClerkTokenGetter,
  _resetClerkSessionForTests,
} from "@/auth/clerkSession";

vi.mock("@/auth/clerkConfig", () => ({
  isClerkAuthEnabled: () => true,
}));

async function captureHeaders(path: string): Promise<Record<string, string>> {
  const capturedHeaders: Record<string, string> = {};
  server.use(
    http.get(path, ({ request }) => {
      request.headers.forEach((value, key) => {
        capturedHeaders[key] = value;
      });
      return HttpResponse.json({ ok: true });
    })
  );
  await apiClient.get("api", path.replace("/api/v1", ""));
  return capturedHeaders;
}

describe("ApiClient Clerk auth interceptor", () => {
  beforeEach(() => {
    _resetClerkSessionForTests();
  });

  afterEach(() => {
    _resetClerkSessionForTests();
    vi.restoreAllMocks();
  });

  it("attaches a sanitized Bearer token when Clerk returns a valid token", async () => {
    setClerkTokenGetter(async () => "valid-clerk-jwt");
    const headers = await captureHeaders("/api/v1/clerk-test");
    expect(headers.authorization).toBe("Bearer valid-clerk-jwt");
    expect(headers["x-request-id"]).toMatch(/^req_/);
  });

  it("does not attach Authorization when Clerk token is null", async () => {
    setClerkTokenGetter(async () => null);
    const headers = await captureHeaders("/api/v1/clerk-test-null");
    expect(headers.authorization).toBeUndefined();
    expect(headers["x-request-id"]).toMatch(/^req_/);
  });

  it("does not attach Authorization when Clerk token is undefined", async () => {
    setClerkTokenGetter(async () => undefined as unknown as string);
    const headers = await captureHeaders("/api/v1/clerk-test-undefined");
    expect(headers.authorization).toBeUndefined();
    expect(headers["x-request-id"]).toMatch(/^req_/);
  });

  it("does not attach Authorization when Clerk token is empty", async () => {
    setClerkTokenGetter(async () => "");
    const headers = await captureHeaders("/api/v1/clerk-test-empty");
    expect(headers.authorization).toBeUndefined();
    expect(headers["x-request-id"]).toMatch(/^req_/);
  });

  it("does not attach Authorization when Clerk token contains control characters", async () => {
    setClerkTokenGetter(async () => "bad\nheader\rvalue");
    const headers = await captureHeaders("/api/v1/clerk-test-control");
    expect(headers.authorization).toBeUndefined();
    expect(headers["x-request-id"]).toMatch(/^req_/);
  });
});
