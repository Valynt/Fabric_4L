import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import StudioTabs from "./StudioTabs";

function renderTabs(path = "/t/acme/accounts/acc-123/studio/value-model") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/t/:tenantSlug/accounts/:accountId/studio/:tabId" element={<StudioTabs />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("StudioTabs", () => {
  it("renders exactly one canonical tablist", () => {
    renderTabs();
    expect(screen.getAllByRole("tablist")).toHaveLength(1);
  });

  it("marks the active tab selected", () => {
    renderTabs();
    expect(screen.getByRole("tab", { name: "Value Model" })).toHaveAttribute("aria-current", "page");
  });

  it("falls back to the default tab for an invalid tab id", () => {
    renderTabs("/t/acme/accounts/acc-123/studio/not-a-tab");
    expect(screen.getByRole("tab", { name: "Action Plan" })).toHaveAttribute("aria-current", "page");
  });

  it("builds tenant-scoped links that preserve account id", () => {
    renderTabs();
    expect(screen.getByRole("tab", { name: "Action Plan" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/action-plan"
    );
    expect(screen.getByRole("tab", { name: "Executive Value Case" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/value-case"
    );
  });

  it("does not link any Studio tab to /intelligence/*", () => {
    renderTabs();
    const tabs = screen.getAllByRole("tab");
    for (const tab of tabs) {
      const href = tab.getAttribute("href") ?? "";
      expect(href).not.toMatch(/\/intelligence\//);
    }
  });
});
