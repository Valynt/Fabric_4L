import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageHeader } from "./PageHeader";

describe("PageHeader", () => {
  it("wraps actions in a responsive action group", () => {
    render(
      <PageHeader
        title="Workflow readiness"
        subtitle="Release-significant state coverage"
        actions={
          <>
            <button>Review evidence</button>
            <button>Run gate</button>
          </>
        }
      />,
    );

    const action = screen.getByRole("button", { name: "Review evidence" });
    const actionGroup = action.parentElement;

    expect(screen.getByRole("heading", { name: "Workflow readiness" })).toBeInTheDocument();
    expect(actionGroup).toHaveClass("flex", "w-full", "flex-wrap", "sm:w-auto");
  });

  it("renders wrapped breadcrumb navigation with accessible labeling", () => {
    render(
      <PageHeader
        title="Evidence"
        breadcrumbs={[
          { label: "Governance", href: "/governance" },
          { label: "Evidence" },
        ]}
      />,
    );

    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toHaveClass("flex-wrap");
    expect(screen.getByRole("link", { name: "Governance" })).toHaveAttribute("href", "/governance");
  });
});
