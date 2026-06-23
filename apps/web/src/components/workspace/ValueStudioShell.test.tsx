import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ValueStudioShell from "./ValueStudioShell";

const account = {
  accountName: "Acme Corp",
  industry: "Manufacturing",
  revenue: "$120M",
};

function renderShell(path = "/t/acme/accounts/acc-123/studio/value-model") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/t/:tenantSlug/accounts/:accountId/studio/:tabId"
          element={
            <ValueStudioShell account={account}>
              <div>Studio content</div>
            </ValueStudioShell>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("ValueStudioShell", () => {
  it("builds tenant-scoped studio tabs from the canonical registry", () => {
    renderShell();

    expect(screen.getByRole("tab", { name: "Value Model" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("link", { name: "Action Plan" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/action-plan"
    );
    expect(screen.getByRole("link", { name: "Executive Value Case" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/value-case"
    );
  });

  it("links back to the tenant-scoped intelligence workspace", () => {
    renderShell();

    expect(screen.getByRole("link", { name: "Back to Intelligence" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/intelligence/signals"
    );
  });
});
