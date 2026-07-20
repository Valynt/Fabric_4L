/**
 * DriverTreePage Regression Tests
 *
 * Locks down the fix for the original bug where DriverTreePage rendered:
 *   "Account · Unknown · N/A"
 * with empty content when no account context was present.
 *
 * Verifies the standardized pattern:
 *   missing accountId → AccountRequiredGuard
 *   loading           → CenteredLoader
 *   valid account     → shell with correct header
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { createWrapperWithRouterPath } from "@/test-utils";
import DriverTreePage from "./DriverTreePage";

const mockUseAccount = vi.fn();

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: (accountId: string | null) => mockUseAccount(accountId),
  resolveBackendAccountId: (accountId: string | null | undefined) => accountId ?? null,
}));

vi.mock("@/features/intelligence-workspace/components/EvidenceTabContent", () => ({
  EvidenceTabContent: () => <div data-testid="evidence-content">Evidence</div>,
}));

vi.mock("@/pages/evidence/AlternativesTab", () => ({
  default: () => <div data-testid="alternatives-content">Alternatives</div>,
}));

vi.mock("@/pages/evidence/SolutionCostTab", () => ({
  default: () => <div data-testid="solution-cost-content">Solution Cost</div>,
}));

describe("DriverTreePage trees tab behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get("/api/v1/agents/hypotheses/account/:accountId", () =>
        HttpResponse.json({
          hypotheses: [
            {
              id: "hyp-1",
              account_id: "acc-123",
              product_id: "prod-1",
              signal_id: "sig-1",
              hypothesis_text: "Reduce churn via onboarding improvements",
              value_path_category: "revenue_uplift",
              confidence: 0.8,
              status: "draft",
              evidence_ids: [],
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
          ],
          total: 1,
        })
      )
    );
  });

  it("renders suggested driver trees and reveals Model Impact after selecting one", async () => {
    mockUseAccount.mockReturnValue({
      data: { id: "acc-123", name: "Acme Corp" },
      isLoading: false,
    });

    const wrapper = createWrapperWithRouterPath("/t/acme/accounts/acc-123/studio/driver-tree");
    render(<DriverTreePage accountId="acc-123" />, { wrapper });

    const suggestion = await screen.findByText("Reduce churn via onboarding improvements");
    expect(suggestion).toBeInTheDocument();
    expect(screen.queryByText(/Model Impact/)).not.toBeInTheDocument();

    await userEvent.click(suggestion);

    expect(screen.getByText(/Model Impact/)).toBeInTheDocument();
  });
});

describe("DriverTreePage account/loading guards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get("/api/v1/agents/cases", () =>
        HttpResponse.json({ items: [{ case_id: "case-123" }] })
      ),
      http.get("/api/v1/agents/cases/:caseId/workspace/drivers", () =>
        HttpResponse.json({ drivers: [] })
      ),
      http.get("/api/v1/agents/cases/:caseId/workspace/evidence-links", () =>
        HttpResponse.json({ evidence_links: [] })
      ),
      http.get("/api/v1/agents/v1/hypotheses/account/:accountId", () =>
        HttpResponse.json({ hypotheses: [], total: 0 })
      )
    );
  });

  it("renders AccountRequiredGuard when accountId is missing", () => {
    mockUseAccount.mockReturnValue({ data: undefined, isLoading: false });

    const wrapper = createWrapperWithRouterPath("/t/acme/accounts/acc-123/studio/driver-tree");
    render(<DriverTreePage accountId="" />, { wrapper });

    expect(screen.getByText("No account selected")).toBeInTheDocument();
    expect(
      screen.getByText("Select an account from the sidebar to view this page.")
    ).toBeInTheDocument();
  });

  it("renders CenteredLoader while account is loading", () => {
    mockUseAccount.mockReturnValue({ data: undefined, isLoading: true });

    const wrapper = createWrapperWithRouterPath("/t/acme/accounts/acc-123/studio/driver-tree");
    render(<DriverTreePage accountId="acc-123" />, { wrapper });

    expect(screen.getByText("Loading driver tree…")).toBeInTheDocument();
  });

  it('renders "Account not found" when accountId is present but account does not exist', () => {
    mockUseAccount.mockReturnValue({ data: undefined, isLoading: false });

    const wrapper = createWrapperWithRouterPath("/t/acme/accounts/acc-404/studio/driver-tree");
    render(<DriverTreePage accountId="acc-404" />, { wrapper });

    expect(screen.getByText("Account not found.")).toBeInTheDocument();
  });

  it("renders page content without its own account header", async () => {
    mockUseAccount.mockReturnValue({
      data: {
        id: "acc-123",
        name: "Acme Corp",
        industry: "Technology",
        annual_revenue: 1_500_000,
      },
      isLoading: false,
    });

    const wrapper = createWrapperWithRouterPath("/t/acme/accounts/acc-123/studio/driver-tree?sub=evidence");
    render(<DriverTreePage accountId="acc-123" />, { wrapper });
    await userEvent.click(screen.getByRole("button", { name: "Evidence" }));

    // Page content is present
    expect(screen.getByTestId("evidence-content")).toBeInTheDocument();

    // DriverTreePage no longer renders its own account header
    expect(screen.queryByText("Acme Corp")).not.toBeInTheDocument();
    expect(screen.queryByText("Technology")).not.toBeInTheDocument();
    expect(screen.queryByText("$1,500,000")).not.toBeInTheDocument();
  });
});
