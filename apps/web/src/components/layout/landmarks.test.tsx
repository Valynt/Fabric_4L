import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { LeftNavigation } from "./LeftNavigation";
import { AgentSidePanel } from "./AgentSidePanel";
import { AuthProvider } from "@/contexts/AuthContext";
import { createTestQueryClient } from "@/test-utils";
import { withAuthProvider } from "@/test/utils/withAuthProvider";

describe("layout landmarks", () => {
  it("renders a single primary navigation landmark for desktop sidebar", async () => {
    await withAuthProvider("legacy", async () => {
      render(
        <MemoryRouter>
          <QueryClientProvider client={createTestQueryClient()}>
            <AuthProvider>
              <LeftNavigation collapsed={false} onToggle={() => {}} />
            </AuthProvider>
          </QueryClientProvider>
        </MemoryRouter>
      );

      const sidebar = screen.getByRole("complementary", { name: /primary sidebar/i });
      const nav = within(sidebar).getByRole("navigation", { name: /primary navigation/i });

      expect(nav).toBeInTheDocument();
    });
  });

  it("resolves tenant-scoped sidebar links from the provided tenant slug", async () => {
    await withAuthProvider("legacy", async () => {
      render(
        <MemoryRouter initialEntries={["/home"]}>
          <QueryClientProvider client={createTestQueryClient()}>
            <AuthProvider>
              <LeftNavigation collapsed={false} onToggle={() => {}} currentTenantSlug="acme" />
            </AuthProvider>
          </QueryClientProvider>
        </MemoryRouter>
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
  });

  it("renders agent panel as a complementary landmark", () => {
    render(<AgentSidePanel onClose={() => {}} onMinimize={() => {}} />);

    expect(
      screen.getByRole("complementary", { name: /agent assistant panel/i })
    ).toBeInTheDocument();
  });
});
