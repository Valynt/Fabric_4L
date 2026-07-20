import { describe, it, expect, vi } from "vitest";
import type React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import ProspectSetupPage from "@/pages/ProspectSetup";

const VALID_PROMPT = [
  "Company: Acme Corp",
  "Website: acme.example",
  "Buying context: Renewal risk",
  "Why this account now: Q4 planning",
].join("\n");

/**
 * Enters the multi-line prompt through the same onChange path as typing, but
 * as a single paste event. Per-keystroke typing re-parses the prompt on every
 * character (~110 renders in jsdom), which pushes these tests past the 5s
 * timeout under parallel CPU contention without exercising anything extra.
 */
async function enterPrompt(
  user: ReturnType<typeof userEvent.setup>,
  text: string
) {
  const prompt = screen.getByLabelText("New value case prompt");
  await user.click(prompt);
  await user.paste(text);
}

function renderProspectSetup(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe("ProspectSetup behavior primitives", () => {
  it("keeps launch action disabled without minimum prompt context", () => {
    renderProspectSetup(<ProspectSetupPage />);
    expect(
      screen.getByRole("button", { name: "Launch Intelligence" })
    ).toBeDisabled();
  });

  it("renders external loading state for launch action", () => {
    renderProspectSetup(<ProspectSetupPage isSubmitting />);
    expect(screen.getByRole("button", { name: "Launching..." })).toBeDisabled();
  });

  it("renders submission error when creation fails", async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn().mockRejectedValue(new Error("boom"));
    renderProspectSetup(<ProspectSetupPage onCreateSetup={onCreateSetup} />);

    await user.type(
      screen.getByLabelText("New value case prompt"),
      "Company: FailureCo"
    );
    await user.click(
      screen.getByRole("button", { name: "Launch Intelligence" })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to launch intelligence. Please review the input and try again."
    );
  });

  it("submits the current payload and navigates to the tenant-aware workspace", async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi
      .fn()
      .mockResolvedValue({ accountId: "account-123" });
    const onNavigateToWorkspace = vi.fn();
    renderProspectSetup(
      <ProspectSetupPage
        onCreateSetup={onCreateSetup}
        onNavigateToWorkspace={onNavigateToWorkspace}
      />
    );

    await enterPrompt(user, VALID_PROMPT);
    await user.click(
      screen.getByRole("button", { name: "Launch Intelligence" })
    );

    expect(onCreateSetup).toHaveBeenCalledTimes(1);
    expect(onCreateSetup).toHaveBeenCalledWith(
      expect.objectContaining({
        companyName: "Acme Corp",
        companyDomain: "acme.example",
        buyingContext: "Renewal risk",
        whyNow: "Q4 planning",
        outputType: "account_brief",
        mode: "Balanced",
        freeformPrompt: VALID_PROMPT,
      })
    );
    expect(onNavigateToWorkspace).toHaveBeenCalledWith(
      "/t/default/accounts/account-123/intelligence/signals",
      "account-123"
    );
  });

  it("submits with Ctrl+Enter through the same callback contract", async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi
      .fn()
      .mockResolvedValue({ accountId: "account-123" });
    renderProspectSetup(<ProspectSetupPage onCreateSetup={onCreateSetup} />);

    await enterPrompt(user, VALID_PROMPT);
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(onCreateSetup).toHaveBeenCalledTimes(1);
  });

  it("renders the normalized duplicate-account error", async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn().mockRejectedValue({
      statusCode: 409,
      responseData: {
        error: "duplicate account",
        duplicate_candidates: [{ name: "Acme Corp" }],
        suggested_action: "merge",
      },
    });
    renderProspectSetup(<ProspectSetupPage onCreateSetup={onCreateSetup} />);

    await enterPrompt(user, VALID_PROMPT);
    await user.click(
      screen.getByRole("button", { name: "Launch Intelligence" })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Duplicate account detected for Acme Corp. Review and merge before launching."
    );
  });

  it("shows required validation guidance before submission", () => {
    renderProspectSetup(<ProspectSetupPage />);
    expect(
      screen.getByText(
        "Add a company name, domain, or attachment to identify the account"
      )
    ).toBeVisible();
    expect(
      screen.getByText("Write at least a few sentences describing the context")
    ).toBeVisible();
  });
});
