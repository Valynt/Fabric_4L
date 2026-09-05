import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import StudioShell from "./StudioShell";

const { rightRailProps } = vi.hoisted(() => ({ rightRailProps: vi.fn() }));

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: () => ({
    data: { name: "Acme Corp", industry: "Manufacturing", annual_revenue: 120000000 },
    isLoading: false,
  }),
}));

vi.mock("./components/StudioTabFrame", async () => {
  const React = await import("react");
  const ctxModule = await import("./StudioRightRailContext");
  // Stable identity: the injected node must not change per render (same
  // contract the real tabs follow via useMemo).
  const injected = React.createElement(
    "div",
    { "data-testid": "injected-detail" },
    "Injected detail",
  );
  return {
    default: function MockTabFrame() {
      ctxModule.useStudioDetailRail(injected);
      return React.createElement("div", { "data-testid": "tab-frame" }, "Tab content");
    },
  };
});

vi.mock("@/components/workspace/RightRail", () => ({
  default: (props: { mode: string; detailContent?: ReactNode }) => {
    rightRailProps(props);
    return (
      <div data-testid="right-rail">
        {props.mode === "detail" ? props.detailContent : null}
      </div>
    );
  },
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

  it("surfaces tab-injected detail content in the shell-owned rail (R1)", async () => {
    renderShell();
    // The tab's injected detail content is rendered by the shell's single
    // right rail, which auto-switches to Details mode to surface it.
    expect(await screen.findByTestId("injected-detail")).toBeInTheDocument();
    expect(rightRailProps).toHaveBeenLastCalledWith(
      expect.objectContaining({ mode: "detail" }),
    );
  });
});
