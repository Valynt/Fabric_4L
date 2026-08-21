/**
 * Phase 2 — pure-function tests for the auth provider switch and Clerk
 * config helpers. These tests pin the normalization policy so we cannot
 * silently widen what activates Clerk mode in a later refactor.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  AUTH_PROVIDER_CLERK,
  AUTH_PROVIDER_LEGACY,
  getAuthProvider,
  getClerkPublishableKey,
  getClerkUrls,
  isClerkAuthEnabled,
} from "./clerkConfig";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

type EnvBag = Record<string, unknown>;
const env = () => import.meta.env as unknown as EnvBag;

const VITE_KEYS_TO_SAVE = [
  "VITE_AUTH_PROVIDER",
  "VITE_CLERK_PUBLISHABLE_KEY",
  "VITE_CLERK_SIGN_IN_URL",
  "VITE_CLERK_SIGN_UP_URL",
  "VITE_CLERK_AFTER_SIGN_IN_URL",
  "VITE_CLERK_AFTER_SIGN_UP_URL",
  "VITE_CLERK_SELECT_ORG_URL",
];

describe("clerkConfig — provider normalization", () => {
  let saved: Record<string, unknown> = {};

  beforeEach(() => {
    saved = {};
    for (const k of VITE_KEYS_TO_SAVE) saved[k] = env()[k];
  });

  afterEach(() => {
    for (const k of VITE_KEYS_TO_SAVE) {
      if (saved[k] === undefined) delete env()[k];
      else env()[k] = saved[k];
    }
  });

  it("defaults to clerk when VITE_AUTH_PROVIDER is unset", () => {
    setAuthProvider(undefined);
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
    expect(isClerkAuthEnabled()).toBe(true);
  });

  it("treats empty string as clerk (default)", () => {
    setAuthProvider("");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
  });

  it("treats whitespace-only as clerk (default)", () => {
    setAuthProvider("   \t\n  ");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
  });

  it("treats explicit 'legacy' as legacy", () => {
    setAuthProvider("legacy");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_LEGACY);
    expect(isClerkAuthEnabled()).toBe(false);
  });

  it("treats explicit 'clerk' as clerk", () => {
    setAuthProvider("clerk");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
    expect(isClerkAuthEnabled()).toBe(true);
  });

  it("activates clerk on exact lowercase", () => {
    setAuthProvider("clerk");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
    expect(isClerkAuthEnabled()).toBe(true);
  });

  it("normalizes 'clerk' after trim + case-fold", () => {
    setAuthProvider("  CLERK  ");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
    setAuthProvider("Clerk");
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
  });

  it.each([
    "true",
    "1",
    "yes",
    "on",
    "enable",
    "CLERK_MODE",
    "clerk-mode",
    "clerks",
  ])("does NOT activate legacy for garbage-looking value %s", v => {
    setAuthProvider(v);
    expect(getAuthProvider()).toBe(AUTH_PROVIDER_CLERK);
    expect(isClerkAuthEnabled()).toBe(true);
  });
});

describe("clerkConfig — publishable key fail-fast", () => {
  let savedKey: unknown;
  beforeEach(() => {
    savedKey = env().VITE_CLERK_PUBLISHABLE_KEY;
  });
  afterEach(() => {
    if (savedKey === undefined) delete env().VITE_CLERK_PUBLISHABLE_KEY;
    else env().VITE_CLERK_PUBLISHABLE_KEY = savedKey;
  });

  it("throws when key is missing", () => {
    delete env().VITE_CLERK_PUBLISHABLE_KEY;
    expect(() => getClerkPublishableKey()).toThrow(
      /VITE_CLERK_PUBLISHABLE_KEY/
    );
  });

  it("throws when key is empty string", () => {
    env().VITE_CLERK_PUBLISHABLE_KEY = "";
    expect(() => getClerkPublishableKey()).toThrow(
      /VITE_CLERK_PUBLISHABLE_KEY/
    );
  });

  it("throws when key is whitespace-only", () => {
    env().VITE_CLERK_PUBLISHABLE_KEY = "   ";
    expect(() => getClerkPublishableKey()).toThrow(
      /VITE_CLERK_PUBLISHABLE_KEY/
    );
  });

  it("returns the trimmed key when present", () => {
    env().VITE_CLERK_PUBLISHABLE_KEY = "  pk_test_dummyabc123  ";
    expect(getClerkPublishableKey()).toBe("pk_test_dummyabc123");
  });

  it("does not throw merely because the key is missing in legacy mode", () => {
    // The fail-fast lives in getClerkPublishableKey(); legacy callers must
    // simply NOT invoke it. Verify legacy doesn't trigger it transitively.
    setAuthProvider("legacy");
    delete env().VITE_CLERK_PUBLISHABLE_KEY;
    expect(() => getAuthProvider()).not.toThrow();
    expect(() => isClerkAuthEnabled()).not.toThrow();
  });

  it("throws when key has invalid format (missing pk_test_/pk_live_ prefix)", () => {
    env().VITE_CLERK_PUBLISHABLE_KEY = "sk_test_abc123";
    expect(() => getClerkPublishableKey()).toThrow(/invalid format/);
  });

  it("throws when key is missing suffix after prefix", () => {
    env().VITE_CLERK_PUBLISHABLE_KEY = "pk_test_";
    expect(() => getClerkPublishableKey()).toThrow(/invalid format/);
  });

  it("accepts pk_live_ key format", () => {
    env().VITE_CLERK_PUBLISHABLE_KEY = "pk_live_dummyxyz789";
    expect(getClerkPublishableKey()).toBe("pk_live_dummyxyz789");
  });
});

describe("clerkConfig — getClerkUrls defaults + overrides", () => {
  let savedUrls: Record<string, unknown> = {};
  const URL_KEYS = [
    "VITE_CLERK_SIGN_IN_URL",
    "VITE_CLERK_SIGN_UP_URL",
    "VITE_CLERK_AFTER_SIGN_IN_URL",
    "VITE_CLERK_AFTER_SIGN_UP_URL",
    "VITE_CLERK_SELECT_ORG_URL",
  ];

  beforeEach(() => {
    savedUrls = {};
    for (const k of URL_KEYS) {
      savedUrls[k] = env()[k];
      delete env()[k];
    }
  });

  afterEach(() => {
    for (const k of URL_KEYS) {
      if (savedUrls[k] === undefined) delete env()[k];
      else env()[k] = savedUrls[k];
    }
  });

  it("returns deterministic defaults when no env vars are set", () => {
    const urls = getClerkUrls();
    expect(urls).toEqual({
      signInUrl: "/sign-in",
      signUpUrl: "/sign-up",
      afterSignInUrl: "/home",
      afterSignUpUrl: "/onboarding",
      selectOrgUrl: "/workspaces",
    });
  });

  it("honors each override independently", () => {
    env().VITE_CLERK_SIGN_IN_URL = "/auth/sign-in";
    env().VITE_CLERK_SIGN_UP_URL = "/auth/sign-up";
    env().VITE_CLERK_AFTER_SIGN_IN_URL = "/dashboard";
    env().VITE_CLERK_AFTER_SIGN_UP_URL = "/welcome";
    env().VITE_CLERK_SELECT_ORG_URL = "/orgs";

    expect(getClerkUrls()).toEqual({
      signInUrl: "/auth/sign-in",
      signUpUrl: "/auth/sign-up",
      afterSignInUrl: "/dashboard",
      afterSignUpUrl: "/welcome",
      selectOrgUrl: "/orgs",
    });
  });
});
