import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LeftNavigation } from "./LeftNavigation";
import { AgentSidePanel } from "./AgentSidePanel";

describe("layout landmarks", () => {
  it("renders a single primary navigation landmark for desktop sidebar", () => {
    render(
      <MemoryRouter>
        <LeftNavigation collapsed={false} onToggle={() => {}} />
      </MemoryRouter>
    );

    const sidebar = screen.getByRole("complementary", { name: /primary sidebar/i });
    const nav = within(sidebar).getByRole("navigation", { name: /primary navigation/i });

    expect(nav).toBeInTheDocument();
  });

  it("resolves tenant-scoped sidebar links from the provided tenant slug", () => {
    render(
      <MemoryRouter initialEntries={["/home"]}>
        <LeftNavigation collapsed={false} onToggle={() => {}} currentTenantSlug="acme" />
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

  it("renders agent panel as a complementary landmark", () => {
    render(<AgentSidePanel onClose={() => {}} onMinimize={() => {}} />);

    expect(
      screen.getByRole("complementary", { name: /agent assistant panel/i })
    ).toBeInTheDocument();
  });
});
