/**
 * Phase 2 — lifecycle tests for <ClerkAuthBridge />.
 *
 * Invariants under test:
 *   L1. Mounting while signed in registers a working token getter that
 *       returns Clerk's current token.
 *   L2. The registered getter ALWAYS reflects the latest Clerk `getToken`
 *       closure even after re-renders that change its identity (the
 *       stable-ref design from the hardening pass).
 *   L3. Sign-out (isSignedIn flips false) clears the token getter.
 *   L4. Sign-out (organization → null) clears the active org id.
 *   L5. Org switch updates the active org id.
 *   L6. Unmount clears BOTH the token getter and the active org id.
 *   L7. React StrictMode's double-invoke does not leave the bridge in a
 *       permanently-null state.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import React, { StrictMode } from "react";
import { render, cleanup, act, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import {
  _resetClerkSessionForTests,
  getActiveClerkOrgId,
  getClerkSessionToken,
} from "@/auth/clerkSession";
import { setAuthProvider } from "@/test/utils/withAuthProvider";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { ACCOUNT_CONTEXT_STORAGE_KEY } from "@fabric/platform-contract/stores";

// ─────────────────────────────────────────────────────────────────────────
// Mock Clerk. The mock state object is mutable; tests flip values and
// re-render to simulate state transitions.
// ─────────────────────────────────────────────────────────────────────────
const mockClerkState = {
  authLoaded: true as boolean,
  isSignedIn: false as boolean,
  // Counter used to make `getToken` return distinguishable values per
  // call AND optionally simulate identity churn between renders.
  tokenSerial: 0,
  // When true, a fresh `getToken` closure is returned on every render.
  // This simulates Clerk's real-world behavior where the function identity
  // is not stable.
  churnGetToken: false,
  organization: null as { id: string } | null,
};

function makeGetToken() {
  const serial = mockClerkState.tokenSerial;
  return vi.fn(async () => `tok_${serial}`);
}

vi.mock("@clerk/react", () => ({
  useAuth: () => ({
    isLoaded: mockClerkState.authLoaded,
    isSignedIn: mockClerkState.isSignedIn,
    // Either a stable function (cached on first call per render-cycle) or
    // a brand-new closure each render, depending on churnGetToken.
    getToken: mockClerkState.churnGetToken ? makeGetToken() : stableGetToken(),
  }),
  useOrganization: () => ({
    isLoaded: true,
    organization: mockClerkState.organization,
  }),
  useUser: () => ({ user: mockClerkState.isSignedIn ? { id: "u_1" } : null }),
}));

// A stable getToken cached at module scope; re-created when tokenSerial flips.
let _stableGetToken: ReturnType<typeof makeGetToken> | null = null;
let _stableGetTokenSerial = -1;
function stableGetToken() {
  if (
    _stableGetToken === null ||
    _stableGetTokenSerial !== mockClerkState.tokenSerial
  ) {
    _stableGetToken = makeGetToken();
    _stableGetTokenSerial = mockClerkState.tokenSerial;
  }
  return _stableGetToken;
}

// Import after vi.mock.
import { ClerkAuthBridge } from "./ClerkAuthBridge";

const testQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 0,
    },
  },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={testQueryClient}>
      {children}
    </QueryClientProvider>
  );
}

function resetMockClerk() {
  mockClerkState.authLoaded = true;
  mockClerkState.isSignedIn = false;
  mockClerkState.tokenSerial = 0;
  mockClerkState.churnGetToken = false;
  mockClerkState.organization = null;
  _stableGetToken = null;
  _stableGetTokenSerial = -1;
}

describe("<ClerkAuthBridge />", () => {
  beforeEach(() => {
    resetMockClerk();
    _resetClerkSessionForTests();
    setAuthProvider("clerk");
    sessionStorage.clear();
    useAccountContextStore.getState().authorizationUnavailable();
  });

  afterEach(() => {
    cleanup();
    testQueryClient.clear();
    _resetClerkSessionForTests();
    setAuthProvider(undefined);
  });

  // ──────────────────────────────────────────────────────────────────
  // L1
  // ──────────────────────────────────────────────────────────────────
  it("registers a token getter when signed in", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.tokenSerial = 1;

    render(<ClerkAuthBridge />, { wrapper: Wrapper });

    await expect(getClerkSessionToken()).resolves.toBe("tok_1");
  });

  it("does NOT register a token getter when not signed in", async () => {
    mockClerkState.isSignedIn = false;

    render(<ClerkAuthBridge />, { wrapper: Wrapper });

    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  it("does NOT register a token getter while Clerk is still loading", async () => {
    mockClerkState.authLoaded = false;
    mockClerkState.isSignedIn = true;

    render(<ClerkAuthBridge />, { wrapper: Wrapper });

    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  // ──────────────────────────────────────────────────────────────────
  // L2 — race-free under getToken identity churn
  // ──────────────────────────────────────────────────────────────────
  it("survives getToken identity churn across re-renders (no null-getter race)", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.tokenSerial = 1;
    mockClerkState.churnGetToken = true;

    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });

    // First render — getter resolves to tok_1.
    await expect(getClerkSessionToken()).resolves.toBe("tok_1");

    // Bump the serial and force a re-render. With the stable-ref design,
    // the registered getter must reflect the latest closure without ever
    // briefly returning null.
    await act(async () => {
      mockClerkState.tokenSerial = 2;
      rerender(<ClerkAuthBridge />);
    });
    await expect(getClerkSessionToken()).resolves.toBe("tok_2");

    await act(async () => {
      mockClerkState.tokenSerial = 3;
      rerender(<ClerkAuthBridge />);
    });
    await expect(getClerkSessionToken()).resolves.toBe("tok_3");
  });

  // ──────────────────────────────────────────────────────────────────
  // L3 + L4 — sign-out
  // ──────────────────────────────────────────────────────────────────
  it("clears the token getter when isSignedIn flips false", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.tokenSerial = 1;

    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    await expect(getClerkSessionToken()).resolves.toBe("tok_1");

    await act(async () => {
      mockClerkState.isSignedIn = false;
      rerender(<ClerkAuthBridge />);
    });

    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  it("synchronously clears account context when the Clerk session changes", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_a" };
    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    useAccountContextStore.getState().authorizationVerified("tenant-a");
    useAccountContextStore.getState().setSelectedAccountId("acct-a");

    await act(async () => {
      mockClerkState.isSignedIn = false;
      rerender(<ClerkAuthBridge />);
    });

    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
    expect(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)).toBeNull();
  });

  it("clears the active org id when organization becomes null", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_initial" };

    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    expect(getActiveClerkOrgId()).toBe("org_initial");

    await act(async () => {
      mockClerkState.organization = null;
      rerender(<ClerkAuthBridge />);
    });

    expect(getActiveClerkOrgId()).toBeNull();
  });

  // ──────────────────────────────────────────────────────────────────
  // L5 — org switch
  // ──────────────────────────────────────────────────────────────────
  it("updates active org id when the user switches organizations", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_a" };

    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    expect(getActiveClerkOrgId()).toBe("org_a");

    await act(async () => {
      mockClerkState.organization = { id: "org_b" };
      rerender(<ClerkAuthBridge />);
    });

    expect(getActiveClerkOrgId()).toBe("org_b");
  });

  it("synchronously clears account context before a replacement organization resolves", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_a" };
    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    useAccountContextStore.getState().authorizationVerified("tenant-a");
    useAccountContextStore.getState().setSelectedAccountId("acct-a");

    await act(async () => {
      mockClerkState.organization = { id: "org_b" };
      rerender(<ClerkAuthBridge />);
    });

    expect(useAccountContextStore.getState()).toMatchObject({
      fabricTenantId: null,
      selectedAccountId: null,
      authorizationStatus: "unverified",
    });
    expect(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)).toBeNull();
  });

  it("invalidates React Query cache when the active organization switches", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_a" };
    testQueryClient.setQueryData(["tenant-scoped", "data"], {
      tenant: "org_a",
    });

    const { rerender } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    await act(async () => {
      mockClerkState.organization = { id: "org_b" };
      rerender(<ClerkAuthBridge />);
    });

    const staleQuery = testQueryClient
      .getQueryCache()
      .find({ queryKey: ["tenant-scoped", "data"] });
    expect(staleQuery?.state.isInvalidated).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────
  // L6 — unmount clears everything
  // ──────────────────────────────────────────────────────────────────
  it("unmount clears the token getter", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.tokenSerial = 1;

    const { unmount } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    await expect(getClerkSessionToken()).resolves.toBe("tok_1");

    unmount();
    await expect(getClerkSessionToken()).resolves.toBeNull();
  });

  it("unmount clears the active org id", () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_to_clear" };

    const { unmount } = render(<ClerkAuthBridge />, { wrapper: Wrapper });
    expect(getActiveClerkOrgId()).toBe("org_to_clear");

    unmount();
    expect(getActiveClerkOrgId()).toBeNull();
  });

  // ──────────────────────────────────────────────────────────────────
  // L7 — StrictMode double-invoke does not break the bridge
  // ──────────────────────────────────────────────────────────────────
  it("StrictMode double-mount leaves the bridge in a working (non-null) state", async () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.tokenSerial = 42;

    render(
      <StrictMode>
        <ClerkAuthBridge />
      </StrictMode>,
      { wrapper: Wrapper }
    );

    // Under StrictMode the effect's cleanup fires during the simulated
    // unmount, then the effect re-runs. The final state must be a live
    // getter, not null.
    await expect(getClerkSessionToken()).resolves.toBe("tok_42");
  });

  it("StrictMode double-mount with org set: org id is set, not lingering null from intermediate cleanup", () => {
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_strict" };

    render(
      <StrictMode>
        <ClerkAuthBridge />
      </StrictMode>,
      { wrapper: Wrapper }
    );

    expect(getActiveClerkOrgId()).toBe("org_strict");
  });

  it("renders children while Clerk loads and registers the token getter once signed-in auth is ready", async () => {
    mockClerkState.authLoaded = false;
    mockClerkState.isSignedIn = true;
    mockClerkState.tokenSerial = 7;

    const { rerender } = render(
      <ClerkAuthBridge>
        <div>protected app</div>
      </ClerkAuthBridge>,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("protected app")).toBeInTheDocument();
    await expect(getClerkSessionToken()).resolves.toBeNull();

    await act(async () => {
      mockClerkState.authLoaded = true;
      rerender(
        <ClerkAuthBridge>
          <div>protected app</div>
        </ClerkAuthBridge>
      );
    });

    await waitFor(() => {
      expect(screen.getByText("protected app")).toBeInTheDocument();
    });
    await expect(getClerkSessionToken()).resolves.toBe("tok_7");
  });
});
