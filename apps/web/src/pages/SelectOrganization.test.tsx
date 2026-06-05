import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const organizationListPropsSpy = vi.fn();
const mockOrganizationState = {
  isLoaded: true,
  organization: null as { id: string } | null,
};

vi.mock("@clerk/react", () => ({
  OrganizationList: (props: Record<string, unknown>) => {
    organizationListPropsSpy(props);
    return <div data-testid="organization-list" />;
  },
  useOrganization: () => mockOrganizationState,
}));

const mockUrls = {
  signInUrl: "/sign-in",
  signUpUrl: "/sign-up",
  afterSignInUrl: "/home",
  afterSignUpUrl: "/onboarding",
  selectOrgUrl: "/workspaces",
};

vi.mock("@/auth/clerkConfig", () => ({
  getClerkUrls: () => mockUrls,
}));

import SelectOrganizationPage from "./SelectOrganization";

describe("<SelectOrganizationPage />", () => {
  beforeEach(() => {
    organizationListPropsSpy.mockClear();
    mockOrganizationState.isLoaded = true;
    mockOrganizationState.organization = null;
    mockUrls.afterSignInUrl = "/home";
    mockUrls.selectOrgUrl = "/workspaces";
  });

  it("uses a safe fallback redirect when afterSignInUrl equals selectOrgUrl", () => {
    mockUrls.afterSignInUrl = "/workspaces";
    mockUrls.selectOrgUrl = "/workspaces";

    render(
      <MemoryRouter initialEntries={["/workspaces"]}>
        <Routes>
          <Route path="/workspaces" element={<SelectOrganizationPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("organization-list")).toBeInTheDocument();
    expect(organizationListPropsSpy).toHaveBeenCalledTimes(1);
    expect(organizationListPropsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        afterSelectOrganizationUrl: "/home",
        afterCreateOrganizationUrl: "/home",
      }),
    );
  });

  it("uses afterSignInUrl when it differs from selectOrgUrl", () => {
    mockUrls.afterSignInUrl = "/home";
    mockUrls.selectOrgUrl = "/workspaces";

    render(
      <MemoryRouter initialEntries={["/workspaces"]}>
        <Routes>
          <Route path="/workspaces" element={<SelectOrganizationPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(organizationListPropsSpy).toHaveBeenCalledTimes(1);
    expect(organizationListPropsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        afterSelectOrganizationUrl: "/home",
        afterCreateOrganizationUrl: "/home",
      }),
    );
  });

  it("forces /home when afterSignInUrl is a path variant of the picker route", () => {
    mockUrls.afterSignInUrl = "/workspaces/?next=foo";
    mockUrls.selectOrgUrl = "/select-organization";

    render(
      <MemoryRouter initialEntries={["/workspaces"]}>
        <Routes>
          <Route path="/workspaces" element={<SelectOrganizationPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(organizationListPropsSpy).toHaveBeenCalledTimes(1);
    expect(organizationListPropsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        afterSelectOrganizationUrl: "/home",
        afterCreateOrganizationUrl: "/home",
      }),
    );
  });
});
