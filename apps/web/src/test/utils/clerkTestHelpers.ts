/**
 * Shared test utilities for Clerk authentication tests.
 *
 * Consolidates duplicate mock setup patterns across Clerk-related test files
 * to improve maintainability and ensure consistency.
 */
import { vi } from "vitest";
import { useAuth, useOrganization } from "@clerk/react";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

// Mock Clerk hooks
vi.mock("@clerk/react", () => ({
  useAuth: vi.fn(),
  useOrganization: vi.fn(),
}));

// Mock Clerk config
vi.mock("@/auth/clerkConfig", () => ({
  isClerkAuthEnabled: vi.fn(),
  getClerkUrls: vi.fn(() => ({
    signInUrl: "/sign-in",
    signUpUrl: "/sign-up",
    afterSignInUrl: "/home",
    afterSignUpUrl: "/onboarding",
    selectOrgUrl: "/workspaces",
  })),
}));

const mockUseAuth = vi.mocked(useAuth);
const mockUseOrganization = vi.mocked(useOrganization);
const mockClerkEnabled = vi.mocked(isClerkAuthEnabled);

/**
 * Set up Clerk mocks for a signed-in user with an active organization.
 *
 * @param orgId - The Clerk organization ID, or null to simulate no org selected
 */
export function setupClerkSignedIn(orgId: string | null): void {
  mockClerkEnabled.mockReturnValue(true);
  mockUseAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: true,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: true,
    organization: orgId ? { id: orgId, slug: "acme" } : null,
  } as unknown as ReturnType<typeof useOrganization>);
}

/**
 * Set up Clerk mocks for the loading state (auth still initializing).
 */
export function setupClerkLoading(): void {
  mockClerkEnabled.mockReturnValue(true);
  mockUseAuth.mockReturnValue({
    isLoaded: false,
    isSignedIn: undefined,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: false,
    organization: undefined,
  } as unknown as ReturnType<typeof useOrganization>);
}

/**
 * Set up Clerk mocks for legacy auth mode (Clerk disabled).
 */
export function setupLegacyAuth(): void {
  mockClerkEnabled.mockReturnValue(false);
  mockUseAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: false,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: true,
    organization: null,
  } as unknown as ReturnType<typeof useOrganization>);
}

/**
 * Reset all Clerk mocks to their default state.
 * Call this in beforeEach to ensure test isolation.
 */
export function resetClerkMocks(): void {
  vi.clearAllMocks();
  mockClerkEnabled.mockReturnValue(false);
  mockUseAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: false,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: true,
    organization: null,
  } as unknown as ReturnType<typeof useOrganization>);
}

/**
 * Get the mocked Clerk hooks for direct manipulation in tests.
 */
export function getClerkMocks() {
  return {
    useAuth: mockUseAuth,
    useOrganization: mockUseOrganization,
    isClerkAuthEnabled: mockClerkEnabled,
  };
}
