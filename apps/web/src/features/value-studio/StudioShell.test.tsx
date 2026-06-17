import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import StudioShell from "./StudioShell";

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: () => ({
    data: { name: "Acme Corp", industry: "Manufacturing", annual_revenue: 120000000 },
    isLoading: false,
  }),
}));

vi.mock("./components/StudioTabFrame", () => ({
  default: () => <div data-testid="tab-frame">Tab content</div>,
}));

vi.mock("./components/StudioRightRail", () => ({
  default: () => <div data-testid="right-rail">Right rail</div>,
}));

function renderShell(path = "/t/acme/accounts/acc-123/studio/value-model") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/t/:tenantSlug/accounts/:accountId/studio/:tabId"
          element={<StudioShell />}
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("StudioShell", () => {
  it("renders exactly one account header", () => {
    renderShell();
    const headers = screen.getAllByText("Acme Corp");
    expect(headers).toHaveLength(1);
  });

  it("renders exactly one canonical tablist", () => {
    renderShell();
    expect(screen.getAllByRole("tablist")).toHaveLength(1);
  });

  it("preserves tenant and account context in tab links", () => {
    renderShell();
    expect(screen.getByRole("tab", { name: "Action Plan" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/action-plan"
    );
  });

  it("renders the right rail consistently", () => {
    renderShell();
    expect(screen.getByTestId("right-rail")).toBeInTheDocument();
  });
});
