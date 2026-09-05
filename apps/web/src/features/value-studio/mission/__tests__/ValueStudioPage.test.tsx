/**
 * Page-composition tests for the Value Studio Slice-1 page
 * (FE-VOS-STUDIO-001 §8.1 state matrix, §9 interactions, §14 analytics).
 *
 * Harness mirrors production: a fresh QueryClient (retry disabled), the real
 * route pattern in a MemoryRouter, and a <main> landmark wrapper like
 * GlobalLayout provides — so axe region rules evaluate the real composition.
 *
 * Analytics: the feature logger only emits when import.meta.env.DEV is true
 * (never under vitest), so @/lib/telemetry is mocked at the logger boundary
 * and events are asserted at createFeatureLogger().info.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { NAV_SCHEMA, type NavSchemaNode } from "@/navigation/navSchema";
import { getStatePath } from "@/navigation/navigationService";
import {
  StudioRightRailContext,
  type StudioRightRailApi,
} from "../../StudioRightRailContext";
import ValueStudioPage, { COMMAND_BACKEND_NOTICE } from "../ValueStudioPage";

expect.extend(toHaveNoViolations);

const { featureLoggerInfo } = vi.hoisted(() => ({ featureLoggerInfo: vi.fn() }));
vi.mock("@/lib/telemetry", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/telemetry")>();
  return {
    ...original,
    createFeatureLogger: () => ({
      error: vi.fn(),
      warn: vi.fn(),
      info: featureLoggerInfo,
      debug: vi.fn(),
      withContext: vi.fn(),
    }),
  };
});

const ROUTE = "/t/:tenantSlug/accounts/:accountId/studio/mission";
const BASE = "/t/acme/accounts/acct_acme_manufacturing/studio/mission";
const HEADING = "Acme Manufacturing — OPP-1842";

/**
 * Test double for the StudioShell right-rail seam: captures tab-injected
 * detail content into a plain container (mirroring the production RightRail,
 * which renders detail content inside plain divs) so tests can assert that
 * decision chrome is delivered through the shell's single right rail
 * (DEC-FE-001/008) rather than a page-local column. A div — not a nested
 * landmark — keeps the rendered tree axe-clean (DecisionRail is itself an
 * aside).
 */
function TestDetailRailShell({ children }: { children: ReactNode }) {
  const [detailContent, setDetailContent] = useState<ReactNode>(null);
  const railApi = useMemo<StudioRightRailApi>(() => ({ setDetailContent }), []);
  return (
    <StudioRightRailContext.Provider value={railApi}>
      {children}
      <div data-testid="shell-detail-rail">{detailContent}</div>
    </StudioRightRailContext.Provider>
  );
}

function renderPage(entry: string = BASE) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route
            path={ROUTE}
            element={
              <TestDetailRailShell>
                <main>
                  <ValueStudioPage />
                </main>
              </TestDetailRailShell>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function findNavNode(nodes: readonly NavSchemaNode[], id: string): NavSchemaNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = node.children ? findNavNode(node.children, id) : null;
    if (child) return child;
  }
  return null;
}

describe("route and navigation registration (DEC-FE-001)", () => {
  it("resolves the canonical mission route through the navigation service", () => {
    expect(
      getStatePath("studio-mission", {
        tenantSlug: "acme",
        accountId: "acct_acme_manufacturing",
      }),
    ).toBe(BASE);
  });

  it("registers the mission child in NAV_SCHEMA under Value Studio", () => {
    const studio = findNavNode(NAV_SCHEMA, "studio");
    expect(studio).not.toBeNull();
    const mission = findNavNode(NAV_SCHEMA, "studio-mission");
    expect(mission).toMatchObject({
      label: "Mission",
      path: "/t/:tenantSlug/accounts/:accountId/studio/mission",
      tier: "standard",
    });
    expect(studio?.children?.some((c) => c.id === "studio-mission")).toBe(true);
  });

  it("resolves the accounts list path used by the unauthorized state", () => {
    expect(getStatePath("accounts", { tenantSlug: "acme" })).toBe("/t/acme/accounts");
  });
});

describe("named state composition (§8.1)", () => {
  it("renders the blocked reference state by default", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: HEADING })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Value impact summary" })).toBeInTheDocument();
    expect(screen.getByTestId("decision-rail")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Mission: Prepare Acme for CFO validation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Mission activity events" })).toBeInTheDocument();
  });

  it("renders the loading skeleton for the loading state", async () => {
    renderPage(`${BASE}?fixture=loading`);
    expect(
      await screen.findByRole("status", { name: "Loading Value Studio" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: HEADING })).not.toBeInTheDocument();
  });

  it("renders the empty state with a route into the value model", async () => {
    renderPage(`${BASE}?fixture=empty`);
    expect(await screen.findByText("No active mission")).toBeInTheDocument();
    expect(screen.getByText(/Flo is monitoring the case/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Open value model" });
    expect(link).toHaveAttribute(
      "href",
      "/t/acme/accounts/acct_acme_manufacturing/studio/value-model",
    );
  });

  it("renders the partial state: banner plus unavailable activity section (§11.4)", async () => {
    renderPage(`${BASE}?fixture=partial`);
    expect(await screen.findByRole("heading", { name: HEADING })).toBeInTheDocument();
    expect(
      screen.getByText(/Some sections are temporarily unavailable/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Mission event stream unavailable \(correlation corr_fixture_partial_01\)/),
    ).toBeInTheDocument();
    expect(screen.getByTestId("decision-rail")).toBeInTheDocument();
  });

  it("renders the error state with correlation id and retry", async () => {
    renderPage(`${BASE}?fixture=error`);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The Value Studio projection could not be loaded.");
    expect(alert).toHaveTextContent("corr_fixture_error_01");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: HEADING })).not.toBeInTheDocument();
  });

  it("renders the offline state: banner, kept projection, paused actions", async () => {
    renderPage(`${BASE}?fixture=offline`);
    expect(await screen.findByRole("heading", { name: HEADING })).toBeInTheDocument();
    expect(screen.getByText(/You are offline/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reconnect" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept recommendation" })).toBeDisabled();
    // R2: mission mutations are disabled consistently while offline — the
    // authorized Pause control must not contradict the offline banner.
    expect(screen.getByRole("button", { name: /Pause mission/ })).toBeDisabled();
  });

  it("renders the stale state: out-of-date alert and paused submissions", async () => {
    renderPage(`${BASE}?fixture=stale`);
    expect(await screen.findByRole("heading", { name: HEADING })).toBeInTheDocument();
    const alerts = screen.getAllByRole("alert");
    expect(alerts.some((a) => a.textContent?.includes("This view is out of date."))).toBe(true);
    expect(
      screen.getByRole("button", { name: "Load latest projection" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept recommendation" })).toBeDisabled();
    // R2: mission mutations are disabled consistently while stale.
    expect(screen.getByRole("button", { name: /Pause mission/ })).toBeDisabled();
  });

  it("renders the unauthorized state with no protected body data (§8.1)", async () => {
    renderPage(`${BASE}?fixture=unauthorized`);
    expect(
      await screen.findByRole("heading", { name: "Access required" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/You do not have access to this value case/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to accounts" })).toHaveAttribute(
      "href",
      "/t/acme/accounts",
    );
    expect(screen.queryByRole("heading", { name: HEADING })).not.toBeInTheDocument();
    expect(screen.queryByText(/720,000/)).not.toBeInTheDocument();
  });

  it("renders resolved-decision-but-still-finance-blocked without mutation controls", async () => {
    renderPage(`${BASE}?fixture=resolved-decision-but-still-finance-blocked`);
    expect(await screen.findByText("Working target accepted")).toBeInTheDocument();
    expect(screen.getByText(/Resolved by R\. Chen/)).toBeInTheDocument();
    expect(screen.getByText("1 decision is waiting for you.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Accept recommendation" }),
    ).not.toBeInTheDocument();
  });

  it("renders the static-renderer fallback with the CFO lens active", async () => {
    renderPage(`${BASE}?fixture=static-renderer-fallback`);
    expect(await screen.findByRole("heading", { name: HEADING })).toBeInTheDocument();
    expect(screen.getByTestId("generative-ui-fallback")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CFO" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("deep link and lens selection", () => {
  it("opens and focuses the rail for ?decision=DISP-01", async () => {
    renderPage(`${BASE}?decision=DISP-01`);
    expect(await screen.findByTestId("decision-deep-link")).toHaveTextContent(
      "Focused decision DISP-01",
    );
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Review required — DISP-01" }),
      ).toHaveFocus(),
    );
  });

  it("honors ?lens=cfo on load (FE-LENS-004)", async () => {
    renderPage(`${BASE}?lens=cfo`);
    expect(await screen.findByRole("heading", { name: HEADING })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CFO" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Canonical" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("switches the lens when another lens is selected", async () => {
    const user = userEvent.setup();
    renderPage();
    const cfo = await screen.findByRole("button", { name: "CFO" });
    expect(cfo).toHaveAttribute("aria-pressed", "false");
    await user.click(cfo);
    expect(screen.getByRole("button", { name: "CFO" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("decision and intent interactions (§9.9, FE-INTENT-001)", () => {
  it("accept flow: preview, proceed, honest no-op notice, dismiss", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Accept recommendation" }));

    const dialog = await screen.findByRole("dialog", { name: "Review what this will do" });
    expect(dialog).toHaveTextContent(
      "set the working downtime target to 340 hours/year;",
    );
    expect(dialog).toHaveTextContent("clear unrelated blockers.");

    await user.click(screen.getByRole("button", { name: "Proceed" }));
    expect(await screen.findByText(COMMAND_BACKEND_NOTICE)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText(COMMAND_BACKEND_NOTICE)).not.toBeInTheDocument();
  });

  it("pause flow: pausing surfaces the no-op notice instead of simulating success", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Pause mission/ }));
    expect(await screen.findByText(COMMAND_BACKEND_NOTICE)).toBeInTheDocument();
  });

  it("defer flow: form, typed preview, proceed, notice", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Defer decision" }));
    await user.type(screen.getByLabelText("Defer to"), "R. Chen");
    await user.type(screen.getByLabelText("Due date"), "2026-09-01");
    await user.type(screen.getByLabelText("Reason"), "Waiting on the finance workbook.");
    await user.click(screen.getByRole("button", { name: "Continue to preview" }));

    const dialog = await screen.findByRole("dialog", { name: "Review what this will do" });
    expect(dialog).toHaveTextContent("defer DISP-01 to R. Chen until 2026-09-01;");
    expect(dialog).toHaveTextContent("change the working downtime target;");

    await user.click(screen.getByRole("button", { name: "Proceed" }));
    expect(await screen.findByText(COMMAND_BACKEND_NOTICE)).toBeInTheDocument();
  });

  it("edit flow: recommendation-identical draft needs no rationale", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Edit decision" }));

    const dialog = await screen.findByRole("dialog", { name: "Edit decision DISP-01" });
    expect(dialog).toHaveTextContent("Authoritative impact — read-only");
    await user.click(screen.getByRole("button", { name: "Continue to preview" }));

    const preview = await screen.findByRole("dialog", { name: "Review what this will do" });
    expect(preview).toHaveTextContent("set the working downtime target to 340 hours/year;");
    await user.click(screen.getByRole("button", { name: "Proceed" }));
    expect(await screen.findByText(COMMAND_BACKEND_NOTICE)).toBeInTheDocument();
  });

  it("closing the rail reveals the reopen card", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Close decision rail" }));
    expect(screen.queryByTestId("decision-rail")).not.toBeInTheDocument();
    const reopen = await screen.findByRole("button", { name: "Reopen review" });
    expect(screen.getByText(/DISP-01 — Resolve downtime target conflict/)).toBeInTheDocument();
    await user.click(reopen);
    expect(await screen.findByTestId("decision-rail")).toBeInTheDocument();
  });
});

describe("single-chrome decision rail (PR #1679 review, R1 / DEC-FE-008)", () => {
  it("delivers the decision surface through the shell detail rail, never a page-local column", async () => {
    renderPage();
    // Decision chrome arrives via the injected shell rail…
    const rail = await screen.findByTestId("shell-detail-rail");
    expect(await within(rail).findByTestId("decision-rail")).toBeInTheDocument();
    // …and the main workspace keeps full width: no decision surface and no
    // page-local rail grid inside the page body.
    const main = screen.getByRole("main");
    expect(within(main).queryByTestId("decision-rail")).not.toBeInTheDocument();
    expect(within(main).queryByText(/No open decisions for this mission/)).not.toBeInTheDocument();
    // No arbitrary-value grid-template split (the old 400px page-local rail
    // column); named column counts like the impact row's xl:grid-cols-4 stay.
    expect(document.querySelector('[class*="xl:grid-cols-["]')).toBeNull();
  });

  it("routes the closed-rail reopen card through the shell rail as well", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Close decision rail" }));
    const rail = await screen.findByTestId("shell-detail-rail");
    expect(
      await within(rail).findByRole("button", { name: "Reopen review" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("main")).queryByRole("button", { name: "Reopen review" }),
    ).not.toBeInTheDocument();
  });
});

describe("evidence, steering, and activity (§9.10, §9.12, §9.13)", () => {
  it("opens the evidence drawer with the full excerpt for unrestricted evidence", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(
      await screen.findByRole("button", {
        name: "Open evidence EV-1001: Downtime telemetry export FY-2026",
      }),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Downtime telemetry export FY-2026",
    });
    expect(dialog).toHaveTextContent(
      "Aggregated line-level downtime totals 400 hours per year across 14 packaging lines.",
    );
  });

  it("withholds the excerpt for restricted evidence (FE-EV-003)", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(
      await screen.findByRole("button", {
        name: "Open evidence EV-1003: Downtime cost basis workbook",
      }),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Downtime cost basis workbook",
    });
    expect(dialog).toHaveTextContent(
      "This source is restricted. Only governance metadata is shown; the excerpt is withheld pending access approval.",
    );
    // Governance metadata still renders (traceability/validation/approval).
    expect(dialog).toHaveTextContent("Partially traced");
  });

  it("opens the Steer Flo panel with a visibly disabled composer (Slice 1)", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Open Steer Flo panel" }));
    const dialog = await screen.findByRole("dialog", { name: "Steer Flo" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByLabelText(/Guidance for Flo/)).toBeDisabled();
  });

  it("expands an activity event to reveal its correlation id", async () => {
    const user = userEvent.setup();
    renderPage();
    const row = await screen.findByRole("button", {
      name: /Deterministic benefit calculation failed/,
    });
    expect(row).toHaveAttribute("aria-expanded", "false");
    await user.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findAllByText("corr_mission_204_04")).not.toHaveLength(0);
  });
});

describe("analytics emission (§14)", () => {
  it("emits value_studio_viewed once per projection view with ids and state only", async () => {
    renderPage(`${BASE}?fixture=blocked`);
    await screen.findByRole("heading", { name: HEADING });
    await waitFor(() =>
      expect(featureLoggerInfo).toHaveBeenCalledWith(
        "analytics-event",
        expect.objectContaining({ event: "value_studio_viewed", fixture: "blocked", state: "ready" }),
      ),
    );
  });

  it("emits lens_changed when the lens selection changes", async () => {
    const user = userEvent.setup();
    renderPage(`${BASE}?fixture=blocked`);
    await screen.findByRole("heading", { name: HEADING });
    featureLoggerInfo.mockClear();
    await user.click(screen.getByRole("button", { name: "CFO" }));
    await waitFor(() =>
      expect(featureLoggerInfo).toHaveBeenCalledWith(
        "analytics-event",
        expect.objectContaining({ event: "lens_changed", lens: "cfo" }),
      ),
    );
  });
});

describe("accessibility", () => {
  it("has no axe violations in the blocked reference state", async () => {
    const { container } = renderPage(`${BASE}?fixture=blocked`);
    await screen.findByRole("heading", { name: HEADING });
    expect(await axe(container)).toHaveNoViolations();
  });
});
