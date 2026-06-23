/**
 * Contract-level tests for Clerk auth failure semantics.
 *
 * These tests guard the behavior promised in the Clerk implementation contract:
 *   - Clerk is the canonical default auth provider.
 *   - 401 responses redirect to the sign-in page.
 *   - 403 responses redirect to the forbidden page.
 *   - Legacy auth is opt-in only via explicit configuration.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { getAuthProvider, isClerkAuthEnabled } from "./clerkConfig";
import { sessionService } from "@/services/sessionService";

describe("Clerk auth failure semantics", () => {
  let replaceSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    replaceSpy = vi.fn();
    Object.defineProperty(window, "location", {
      value: {
        pathname: "/home",
        replace: replaceSpy,
      },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("defaults to Clerk when AUTH_PROVIDER is not set", () => {
    expect(getAuthProvider()).toBe("clerk");
    expect(isClerkAuthEnabled()).toBe(true);
  });

  it("redirects to sign-in on 401", () => {
    sessionService.handleUnauthorized({ route: "/home", traceId: "trace-401" });
    expect(replaceSpy).toHaveBeenCalledWith("/sign-in");
  });

  it("redirects to /forbidden on 403", () => {
    sessionService.handleForbidden({ route: "/home", traceId: "trace-403" });
    expect(replaceSpy).toHaveBeenCalledWith("/forbidden");
  });

  it("does not redirect to /forbidden when already on /forbidden", () => {
    Object.defineProperty(window, "location", {
      value: {
        pathname: "/forbidden",
        replace: replaceSpy,
      },
      writable: true,
      configurable: true,
    });
    sessionService.handleForbidden({ route: "/forbidden", traceId: "trace-403" });
    expect(replaceSpy).not.toHaveBeenCalled();
  });
});
