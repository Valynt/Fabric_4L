import { describe, it, expect, vi } from "vitest";
import type React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import ProspectSetupPage, {
  type ProspectSetupMode,
} from "@/pages/ProspectSetup";

const MODES: ProspectSetupMode[] = ["workflow", "value-pilot"];

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
  it.each(MODES)(
    "keeps launch action disabled without minimum prompt context (%s)",
    mode => {
      renderProspectSetup(<ProspectSetupPage mode={mode} />);
      expect(
        screen.getByRole("button", { name: "Launch Intelligence" })
      ).toBeDisabled();
    }
  );

  it.each(MODES)(
    "renders external loading state for launch action (%s)",
    mode => {
      renderProspectSetup(<ProspectSetupPage mode={mode} isSubmitting />);
      expect(
        screen.getByRole("button", { name: "Launching..." })
      ).toBeDisabled();
    }
  );

  it.each(MODES)(
    "renders submission error when creation fails (%s)",
    async mode => {
      const user = userEvent.setup();
      const onCreateSetup = vi.fn().mockRejectedValue(new Error("boom"));
      renderProspectSetup(
        <ProspectSetupPage mode={mode} onCreateSetup={onCreateSetup} />
      );

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
    }
  );
});
