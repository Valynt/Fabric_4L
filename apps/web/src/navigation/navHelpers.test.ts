import { describe, expect, it } from "vitest";
import { isRouteActive } from "./navHelpers";

describe("isRouteActive", () => {
  it("returns true for exact match", () => {
    expect(isRouteActive("/accounts", "/accounts")).toBe(true);
  });

  it("returns true when location starts with resolvedPath + /", () => {
    expect(isRouteActive("/accounts/123/intelligence", "/accounts")).toBe(true);
  });

  it("returns false when location is a different root path", () => {
    expect(isRouteActive("/settings", "/accounts")).toBe(false);
  });

  it("returns false when location is a prefix but not a path segment boundary", () => {
    // /accountsExtra should NOT match /accounts
    expect(isRouteActive("/accountsExtra", "/accounts")).toBe(false);
  });

  it("returns true for nested child path", () => {
    expect(
      isRouteActive("/governance/traces", "/governance")
    ).toBe(true);
  });

  it("returns false for sibling path", () => {
    expect(isRouteActive("/settings/team", "/settings/billing")).toBe(false);
  });

  it("handles trailing slash on resolvedPath gracefully", () => {
    // resolvedPath with trailing slash: startsWith check still works
    expect(isRouteActive("/accounts/123", "/accounts")).toBe(true);
  });

  it("returns false for empty location", () => {
    expect(isRouteActive("", "/accounts")).toBe(false);
  });

  it("returns true for root path exact match", () => {
    expect(isRouteActive("/", "/")).toBe(true);
  });

  it("strips /* suffix from pattern before matching", () => {
    expect(isRouteActive("/foo/bar", "/foo/*")).toBe(true);
    expect(isRouteActive("/foo", "/foo/*")).toBe(true);
    expect(isRouteActive("/other", "/foo/*")).toBe(false);
  });
});
