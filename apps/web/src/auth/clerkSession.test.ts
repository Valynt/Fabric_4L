import { describe, expect, it, beforeEach } from "vitest";

import {
  _resetClerkSessionForTests,
  getActiveClerkOrgId,
  getClerkSessionToken,
  setActiveClerkOrgId,
  setClerkTokenGetter,
  type ClerkTokenGetterOptions,
} from "@/auth/clerkSession";

describe("clerkSession bridge", () => {
  beforeEach(() => {
    _resetClerkSessionForTests();
  });

  it("returns null when no token getter is registered", async () => {
    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  it("calls the registered token getter and returns its value", async () => {
    setClerkTokenGetter(async () => "tok_abc");
    await expect(getClerkSessionToken()).resolves.toBe("tok_abc");
  });

  it("forwards options (template, skipCache) to the token getter", async () => {
    let receivedTemplate: string | undefined;
    let receivedSkipCache: boolean | undefined;
    setClerkTokenGetter(async (opts?: ClerkTokenGetterOptions) => {
      receivedTemplate = opts?.template;
      receivedSkipCache = opts?.skipCache;
      return "tok_with_template";
    });

    await getClerkSessionToken({ template: "fabric4l", skipCache: true });

    expect(receivedTemplate).toBe("fabric4l");
    expect(receivedSkipCache).toBe(true);
  });

  it("returns null when the token getter throws (rotation race)", async () => {
    setClerkTokenGetter(async () => {
      throw new Error("token rotation in progress");
    });
    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  it("clears the token getter when set to null", async () => {
    setClerkTokenGetter(async () => "tok");
    await expect(getClerkSessionToken()).resolves.toBe("tok");
    setClerkTokenGetter(null);
    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  it("tracks the active organization id", () => {
    expect(getActiveClerkOrgId()).toBeNull();
    setActiveClerkOrgId("org_42");
    expect(getActiveClerkOrgId()).toBe("org_42");
    setActiveClerkOrgId(null);
    expect(getActiveClerkOrgId()).toBeNull();
  });
});
