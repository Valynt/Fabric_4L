import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import AccountPickerModal from "./AccountPickerModal";
import type { Account, AccountListResponse } from "@/hooks/useAccounts";
import { useWorkflowSessionStore } from "@/stores/workflowSessionStore";
import { useWorkflowStore } from "@/workflow/store/workflowStore";

const mockNavigate = vi.fn();
const mockSetSelectedAccountId = vi.fn();

// Polyfill scrollIntoView for cmdk in jsdom
Element.prototype.scrollIntoView = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual as object,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/hooks", async () => {
  const actual = await vi.importActual("@/hooks");
  return {
    ...actual as object,
    useAccounts: vi.fn(),
  };
});

vi.mock("@/stores/accountContextStore", () => ({
  useAccountContextStore: (selector: (state: { setSelectedAccountId: typeof mockSetSelectedAccountId }) => unknown) =>
    selector({ setSelectedAccountId: mockSetSelectedAccountId }),
}));

import { useAccounts } from "@/hooks";

const mockUseAccounts = useAccounts as unknown as ReturnType<typeof vi.fn>;

const sampleAccount: Account = {
  id: "acc-001",
  name: "Acme Corp",
  domain: "acme.com",
  provider: "salesforce",
  provider_record_id: "001",
  sync_status: "synced",
  industry: "Technology",
  segment: "Enterprise",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const sampleResponse: AccountListResponse = {
  items: [sampleAccount],
  total: 1,
  page: 1,
  page_size: 50,
  has_more: false,
};

function renderModal(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("AccountPickerModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWorkflowSessionStore.getState().clearContext();
    useWorkflowStore.getState().reset();
  });

  it("renders loading skeleton when accounts are loading", () => {
    mockUseAccounts.mockReturnValue({ data: null, isLoading: true, error: null });
    renderModal(<AccountPickerModal workspace="intelligence" tab="signals" />);

    expect(screen.getByText("Select an Account")).toBeInTheDocument();
    expect(screen.getAllByRole("generic").some(el => el.className.includes("animate-pulse"))).toBe(true);
  });

  it("renders accounts and navigates on selection", async () => {
    const user = userEvent.setup();
    mockUseAccounts.mockReturnValue({ data: sampleResponse, isLoading: false, error: null });
    renderModal(<AccountPickerModal workspace="intelligence" tab="signals" />);

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText(/acme.com/)).toBeInTheDocument();

    const item = screen.getByText("Acme Corp").closest("[cmdk-item]");
    if (item) await user.click(item);

    expect(mockSetSelectedAccountId).toHaveBeenCalledWith("acc-001");
    expect(mockNavigate).toHaveBeenCalledWith("/intelligence/acc-001/signals", undefined);
  });

  it("shows error state when accounts fail to load", () => {
    mockUseAccounts.mockReturnValue({
      data: null,
      isLoading: false,
      error: { message: "Network error" },
    });
    renderModal(<AccountPickerModal workspace="studio" />);

    expect(screen.getByText("Failed to load accounts.")).toBeInTheDocument();
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("navigates to /accounts when Manage Accounts is clicked", async () => {
    const user = userEvent.setup();
    mockUseAccounts.mockReturnValue({ data: sampleResponse, isLoading: false, error: null });
    renderModal(<AccountPickerModal workspace="intelligence" />);

    await user.click(screen.getByRole("button", { name: "Manage Accounts" }));
    // useNavigation appends workflow-context query params (e.g. wfStep=0) to the
    // path before calling navigate, so we match on the /accounts prefix only.
    expect(mockNavigate).toHaveBeenCalledWith(
      expect.stringContaining("/accounts"),
      expect.anything(),
    );
  });
});
