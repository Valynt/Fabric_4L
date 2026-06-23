import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import userEvent from "@testing-library/user-event";
import ValueNarrativeHome from "./ValueNarrativeHome";

const navigateTo = vi.fn();
const createSetup = vi.fn();
const useRecentIngestionJobs = vi.fn();
let isSubmitting = false;
let authState = {
  isAuthenticated: true,
  isLoading: false,
};

const discoveryNotes = `Acme Corp Discovery Notes
Met with Sarah (VP of Support / Champion) and John (Chief Financial Officer / Decision Maker).
They are struggling with manual support routing and ticket categorization. Complex tickets take hours to reach the right Tier 2 rep, causing SLA breaches.
Sarah said customer churn increased by roughly 5% this quarter because response cycles are dragging on.
John needs a validated ROI model before committing by End of Q3. They have budgeted roughly $120k ARR for support automation technologies if the ROI math proves itself.`;

vi.mock("@/hooks/useNavigation", () => ({
  useNavigation: () => ({ navigateTo }),
}));

vi.mock("@/hooks/useIngestion", () => ({
  useRecentIngestionJobs: (...args: unknown[]) => useRecentIngestionJobs(...args),
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuthContext: () => authState,
}));

vi.mock("@/hooks/useProspectSetupAccount", () => ({
  useProspectSetupAccountCreate: () => ({
    createSetup,
    isSubmitting,
  }),
}));

describe("ValueNarrativeHome intake workspace", () => {
  beforeEach(() => {
    navigateTo.mockReset();
    createSetup.mockReset();
    createSetup.mockResolvedValue({ accountId: "acc-home-created-001" });
    useRecentIngestionJobs.mockReset();
    useRecentIngestionJobs.mockReturnValue({ data: [], isLoading: false });
    isSubmitting = false;
    authState = {
      isAuthenticated: true,
      isLoading: false,
    };
  });

  it("loads recent ingestion activity only after authenticated auth state is ready", () => {
    render(<ValueNarrativeHome />);

    expect(useRecentIngestionJobs).toHaveBeenCalledWith(4, {
      suppressAuthRedirect: true,
      enabled: true,
    });
  });

  it("does not enable recent ingestion activity while auth is still resolving", () => {
    authState = {
      isAuthenticated: false,
      isLoading: true,
    };

    render(<ValueNarrativeHome />);

    expect(useRecentIngestionJobs).toHaveBeenCalledWith(4, {
      suppressAuthRedirect: true,
      enabled: false,
    });
  });

  it("renders all source input modes", () => {
    render(<ValueNarrativeHome />);

    expect(screen.getByRole("button", { name: /notes/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /web\/search/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /audio/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /crm link/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pdf file/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /meeting/i })).toBeInTheDocument();
  });

  it("deterministically extracts a structured preview from pasted discovery text", () => {
    render(<ValueNarrativeHome />);

    fireEvent.change(screen.getByLabelText(/copied discovery text/i), {
      target: { value: discoveryNotes },
    });

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getAllByText(/Sarah/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/VP of Support/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/manual support routing/i).length).toBeGreaterThan(1);
    expect(screen.getByText("Revenue protection")).toBeInTheDocument();
    expect(screen.getByText(/Fabric Found Summary/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Needs quantified inputs/i).length).toBeGreaterThan(0);
  });

  it("keeps readiness below high until baseline metrics are provided", async () => {
    const user = userEvent.setup();
    render(<ValueNarrativeHome />);

    fireEvent.change(screen.getByLabelText(/copied discovery text/i), {
      target: { value: discoveryNotes },
    });

    expect(screen.getByText(/Medium Evidence Strength/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/monthly support ticket volume/i), "12500");
    await user.type(screen.getByLabelText(/average tier 2 rep salary/i), "85000");

    expect(screen.getByText(/High Evidence Strength/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Baseline ready/i).length).toBeGreaterThan(0);
  });

  it("does not add source records when clicking unavailable connector buttons", async () => {
    const user = userEvent.setup();
    render(<ValueNarrativeHome />);

    await user.click(screen.getByRole("button", { name: /audio/i }));
    await user.click(screen.getByRole("button", { name: /crm link/i }));
    await user.click(screen.getByRole("button", { name: /pdf file/i }));
    await user.click(screen.getByRole("button", { name: /meeting/i }));

    const sourcesSection = screen.getByRole("heading", { name: /sources added/i });
    const sourcesPanel = within(sourcesSection.parentElement!.parentElement!);

    // Connector message is shown in the input area, but it is not a source record
    expect(
      screen.getByText(
        "Connector not configured yet. This source type will only appear in Sources added once the upload or import flow is connected."
      )
    ).toBeInTheDocument();

    // Sources added section remains empty
    expect(
      sourcesPanel.getByText("Add source context to start extraction and evidence scoring.")
    ).toBeInTheDocument();

    // No fake pending source records were added for unavailable connectors
    expect(sourcesPanel.queryByText("Audio")).not.toBeInTheDocument();
    expect(sourcesPanel.queryByText("CRM Link")).not.toBeInTheDocument();
    expect(sourcesPanel.queryByText("PDF File")).not.toBeInTheDocument();
    expect(sourcesPanel.queryByText("Meeting")).not.toBeInTheDocument();
    expect(sourcesPanel.queryByText("Pending")).not.toBeInTheDocument();

    // Source count stays at 0 / 10 in both the badge and progress label
    expect(screen.getByText("0 / 10 sources")).toBeInTheDocument();
    expect(screen.getByText("0 / 10")).toBeInTheDocument();
  });

  it("creates a real Notes source when the user enters note content", async () => {
    render(<ValueNarrativeHome />);

    fireEvent.change(screen.getByLabelText(/copied discovery text/i), {
      target: { value: "Acme discovery notes" },
    });
    fireEvent.blur(screen.getByLabelText(/copied discovery text/i));

    const sourcesSection = screen.getByRole("heading", { name: /sources added/i });
    const sourcesPanel = within(sourcesSection.parentElement!.parentElement!);

    expect(sourcesPanel.getByText("Notes")).toBeInTheDocument();
    expect(sourcesPanel.getByText("Extracted 3 words")).toBeInTheDocument();
    expect(sourcesPanel.getByText("Processed")).toBeInTheDocument();

    expect(screen.getByText("1 / 10 sources")).toBeInTheDocument();
    expect(screen.getByText("1 / 10")).toBeInTheDocument();
  });

  it("creates a real Web/Search source when the user submits a URL", async () => {
    const user = userEvent.setup();
    render(<ValueNarrativeHome />);

    await user.click(screen.getByRole("button", { name: /web\/search/i }));
    fireEvent.change(screen.getByLabelText(/url or research query/i), {
      target: { value: "https://acme.com/pricing" },
    });
    await user.click(screen.getByRole("button", { name: /add url or search/i }));

    const sourcesSection = screen.getByRole("heading", { name: /sources added/i });
    const sourcesPanel = within(sourcesSection.parentElement!.parentElement!);

    expect(sourcesPanel.getByText("Known URL")).toBeInTheDocument();
    expect(sourcesPanel.getByText("https://acme.com/pricing")).toBeInTheDocument();
    expect(sourcesPanel.getByText("Processed")).toBeInTheDocument();

    expect(screen.getByText("1 / 10 sources")).toBeInTheDocument();
    expect(screen.getByText("1 / 10")).toBeInTheDocument();
  });

  it("launches with the extracted account payload and routes to account intelligence", async () => {
    const user = userEvent.setup();
    render(<ValueNarrativeHome />);

    fireEvent.change(screen.getByLabelText(/copied discovery text/i), {
      target: { value: discoveryNotes },
    });
    await user.click(screen.getByRole("button", { name: /web\/search/i }));
    fireEvent.change(screen.getByLabelText(/url or research query/i), {
      target: { value: "https://acme.com/customer-support-platform" },
    });
    await user.click(screen.getByRole("button", { name: /add url or search/i }));
    await user.type(screen.getByLabelText(/monthly support ticket volume/i), "12500");
    await user.type(screen.getByLabelText(/average tier 2 rep salary/i), "85000");

    await user.click(screen.getAllByRole("button", { name: /launch case/i })[0]);

    await waitFor(() => {
      expect(createSetup).toHaveBeenCalledWith(expect.objectContaining({
        companyName: "Acme Corp",
        companyDomain: "acme.com",
        industry: "Software",
        outputType: "account_brief",
        desiredOutputs: ["account_brief", "value_hypotheses"],
      }));
    });
    expect(navigateTo).toHaveBeenCalledWith("intelligence-overview", {
      accountId: "acc-home-created-001",
    });
  });

  it("disables launch until an account is detected", () => {
    render(<ValueNarrativeHome />);

    screen.getAllByRole("button", { name: /launch case/i }).forEach(button => {
      expect(button).toBeDisabled();
    });
  });
});
