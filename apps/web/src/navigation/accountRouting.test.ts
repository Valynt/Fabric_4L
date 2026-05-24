import { describe, expect, it } from "vitest";
import {
  getWorkspaceTabOrDefault,
  resolveAccountScopedWorkspacePath,
  resolveWorkspaceRoutePath,
  isValidWorkspaceTab,
} from "./accountRouting";

describe("account routing utilities", () => {
  it("falls back to /t/default/accounts when no account is selected", () => {
    expect(
      resolveAccountScopedWorkspacePath({
        workspace: "intelligence",
        accountId: null,
        tab: "signals",
      })
    ).toBe("/t/default/accounts");
  });

  it("falls back to workspace default tab for invalid tabs", () => {
    expect(getWorkspaceTabOrDefault("intelligence", "not-a-tab")).toBe("signals");
    expect(getWorkspaceTabOrDefault("studio", "bad-tab")).toBe("action-plan");
  });

  it("keeps root workspace routes and deep links consistent", () => {
    const accountId = "acct-123";
    const tenantSlug = "acme";

    expect(resolveWorkspaceRoutePath("/intelligence", accountId, tenantSlug)).toBe(
      "/t/acme/accounts/acct-123/intelligence"
    );
    expect(resolveWorkspaceRoutePath("/intelligence/signals", accountId, tenantSlug)).toBe(
      "/t/acme/accounts/acct-123/intelligence/signals"
    );

    expect(resolveWorkspaceRoutePath("/studio", accountId, tenantSlug)).toBe(
      "/t/acme/accounts/acct-123/studio"
    );
    expect(resolveWorkspaceRoutePath("/studio/narrative", accountId, tenantSlug)).toBe(
      "/t/acme/accounts/acct-123/studio/narrative"
    );
  });
});

describe("workspace tab validation", () => {
  it("accepts valid intelligence tabs", () => {
    expect(isValidWorkspaceTab("intelligence", "signals")).toBe(true);
    expect(isValidWorkspaceTab("intelligence", "hypotheses")).toBe(true);
    expect(isValidWorkspaceTab("intelligence", "evidence")).toBe(true);
  });

  it("rejects invalid intelligence tabs", () => {
    expect(isValidWorkspaceTab("intelligence", "not-a-tab")).toBe(false);
    expect(isValidWorkspaceTab("intelligence", undefined)).toBe(false);
  });

  it("accepts valid studio tabs", () => {
    expect(isValidWorkspaceTab("studio", "action-plan")).toBe(true);
    expect(isValidWorkspaceTab("studio", "calculator")).toBe(true);
  });

  it("rejects invalid studio tabs", () => {
    expect(isValidWorkspaceTab("studio", "signals")).toBe(false);
  });
});

describe("resolveAccountScopedWorkspacePath — tab path construction", () => {
  it("builds intelligence tab path", () => {
    expect(
      resolveAccountScopedWorkspacePath({
        workspace: "intelligence",
        accountId: "acct-1",
        tab: "signals",
        tenantSlug: "acme",
      })
    ).toBe("/t/acme/accounts/acct-1/intelligence/signals");
  });

  it("uses default tab when tab is undefined", () => {
    expect(
      resolveAccountScopedWorkspacePath({
        workspace: "intelligence",
        accountId: "acct-1",
        tenantSlug: "acme",
      })
    ).toBe("/t/acme/accounts/acct-1/intelligence/signals");
  });

  it("uses default tab when tab is invalid", () => {
    expect(
      resolveAccountScopedWorkspacePath({
        workspace: "studio",
        accountId: "acct-1",
        tab: "not-a-tab",
        tenantSlug: "acme",
      })
    ).toBe("/t/acme/accounts/acct-1/studio/action-plan");
  });
});
