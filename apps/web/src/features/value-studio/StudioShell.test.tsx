import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

vi.mock("@/components/workspace/RightRail", () => ({
  default: () => <div data-testid="right-rail">Right rail</div>,
}));

vi.mock("@/agui", () => ({
  useAgentEvents: () => ({
    messages: [],
    sendMessage: vi.fn(),
    suggestedActions: [],
    steps: [],
    isStreaming: false,
    metadata: undefined,
  }),
}));

function renderShell(path = "/t/acme/accounts/acc-123/studio/value-model") {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/t/:tenantSlug/accounts/:accountId/studio/:tabId"
            element={<StudioShell />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
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
