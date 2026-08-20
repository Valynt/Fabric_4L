import { describe, expect, it, vi } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";

import {
  FabricOrganizationProfile,
  FabricOrganizationSwitcher,
  FabricSignIn,
  FabricSignUp,
  FabricUserButton,
} from "./ClerkControls";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

vi.mock("@clerk/react", () => ({
  UserButton: (props: Record<string, unknown>) => (
    <div data-testid="clerk-user-button" {...props} />
  ),
  OrganizationSwitcher: (props: Record<string, unknown>) => (
    <div data-testid="clerk-org-switcher" {...props} />
  ),
  SignIn: (props: Record<string, unknown>) => (
    <div data-testid="clerk-sign-in" {...props} />
  ),
  SignUp: (props: Record<string, unknown>) => (
    <div data-testid="clerk-sign-up" {...props} />
  ),
  OrganizationProfile: (props: Record<string, unknown>) => (
    <div data-testid="clerk-org-profile" {...props} />
  ),
}));

describe("ClerkControls", () => {
  it("renders null when Clerk auth is disabled (legacy mode)", () => {
    setAuthProvider("legacy");
    const { container } = render(
      <>
        <FabricUserButton />
        <FabricOrganizationSwitcher />
        <FabricSignIn />
        <FabricSignUp />
        <FabricOrganizationProfile />
      </>
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders all Clerk controls when Clerk auth is enabled", () => {
    setAuthProvider("clerk");
    render(
      <>
        <FabricUserButton />
        <FabricOrganizationSwitcher />
        <FabricSignIn />
        <FabricSignUp />
        <FabricOrganizationProfile />
      </>
    );

    expect(screen.getByTestId("clerk-user-button")).toBeDefined();
    expect(screen.getByTestId("clerk-org-switcher")).toBeDefined();
    expect(screen.getByTestId("clerk-sign-in")).toBeDefined();
    expect(screen.getByTestId("clerk-sign-up")).toBeDefined();
    expect(screen.getByTestId("clerk-org-profile")).toBeDefined();
  });
});
