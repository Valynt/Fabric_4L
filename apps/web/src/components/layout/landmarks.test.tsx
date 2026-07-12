import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LeftNavigation } from "./LeftNavigation";
import { AgentSidePanel } from "./AgentSidePanel";
import { AuthProvider } from "@/contexts/AuthContext";

vi.mock("@/auth/clerkConfig", () => ({
  isClerkAuthEnabled: () => false,
  getClerkUrls: () => ({
    signInUrl: "/sign-in",
    signUpUrl: "/sign-up",
    afterSignInUrl: "/home",
    afterSignUpUrl: "/onboarding",
    selectOrgUrl: "/workspaces",
  }),
}));

function Wrapper({ children, path = "/" }: { children: React.ReactNode; path?: string }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe("layout landmarks", () => {
  it("renders a single primary navigation landmark for desktop sidebar", () => {
    render(
      <Wrapper>
        <LeftNavigation collapsed={false} onToggle={() => {}} />
      </Wrapper>
    );

    const sidebar = screen.getByRole("complementary", { name: /primary sidebar/i });
    const nav = within(sidebar).getByRole("navigation", { name: /primary navigation/i });

    expect(nav).toBeInTheDocument();
  });

  it("resolves tenant-scoped sidebar links from the provided tenant slug", () => {
    render(
      <Wrapper path="/home">
        <LeftNavigation collapsed={false} onToggle={() => {}} currentTenantSlug="acme" />
      </Wrapper>
    );

    expect(screen.getByRole("link", { name: /accounts/i })).toHaveAttribute(
      "href",
      "/t/acme/accounts"
    );
    expect(screen.getByRole("link", { name: /governance/i })).toHaveAttribute(
      "href",
      "/t/acme/governance"
    );
  });

  it("renders agent panel as a complementary landmark", () => {
    render(<AgentSidePanel onClose={() => {}} onMinimize={() => {}} />);

    expect(
      screen.getByRole("complementary", { name: /agent assistant panel/i })
    ).toBeInTheDocument();
  });
});
