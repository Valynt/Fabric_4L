import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const mutateAsync = vi.fn();

vi.mock("@/hooks/useGovernance", () => ({
  useAcceptInvite: () => ({
    mutateAsync,
    isPending: false,
  }),
}));

import AcceptInvite from "./AcceptInvite";

function renderPage(initialPath = "/accept-invite?token=test-token") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/accept-invite" element={<AcceptInvite />} />
        <Route path="/sign-in" element={<div>SIGN_IN_PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("<AcceptInvite />", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
  });

  it("submits token + password and redirects on success", async () => {
    mutateAsync.mockResolvedValueOnce({ id: "u1" });
    const user = userEvent.setup();

    renderPage();

    await user.type(screen.getByLabelText(/full name/i), "Invited User");
    await user.type(screen.getByLabelText(/^password$/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.click(screen.getByRole("button", { name: /accept invitation/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        token: "test-token",
        password: "SecurePass123!",
        name: "Invited User",
      });
    });
    expect(await screen.findByText("SIGN_IN_PAGE")).toBeInTheDocument();
  });

  it("shows mismatch error when passwords differ", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/^password$/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "DifferentPass123!");
    await user.click(screen.getByRole("button", { name: /accept invitation/i }));

    expect(screen.getByTestId("accept-invite-error")).toHaveTextContent(/passwords do not match/i);
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("shows generic token error on backend rejection", async () => {
    mutateAsync.mockRejectedValueOnce(new Error("bad token"));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/^password$/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.click(screen.getByRole("button", { name: /accept invitation/i }));

    expect(await screen.findByTestId("accept-invite-error")).toHaveTextContent(/invalid or expired invitation token/i);
  });
});
