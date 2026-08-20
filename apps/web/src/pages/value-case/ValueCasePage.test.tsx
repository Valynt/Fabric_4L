import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen } from "@testing-library/react";
import { createWrapper } from "@/test-utils";
import ValueCasePage from "./ValueCasePage";

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: vi.fn(),
}));

vi.mock("@/features/value-case", () => ({
  ValueCaseWorkspace: vi.fn(({ accountId, accountName }: { accountId: string; accountName: string }) => (
    <div data-testid="value-case-workspace" data-account-id={accountId} data-account-name={accountName}>
      Value Case Workspace Mounted
    </div>
  )),
}));

import { useAccount } from "@/hooks/useAccounts";

describe("ValueCasePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAccount as Mock).mockReturnValue({
      data: { id: "acct-1", name: "Acme Corp" },
      isLoading: false,
    });
  });

  it("renders AccountRequiredGuard when accountId is missing", () => {
    const wrapper = createWrapper();
    render(<ValueCasePage accountId={null as unknown as string} />, { wrapper });

    expect(screen.queryByTestId("value-case-workspace")).not.toBeInTheDocument();
  });

  it("delegates to ValueCaseWorkspace when accountId is present", () => {
    const wrapper = createWrapper();
    render(<ValueCasePage accountId="acct-1" />, { wrapper });

    const workspace = screen.getByTestId("value-case-workspace");
    expect(workspace).toBeInTheDocument();
    expect(workspace).toHaveAttribute("data-account-id", "acct-1");
    expect(workspace).toHaveAttribute("data-account-name", "Acme Corp");
  });
});
