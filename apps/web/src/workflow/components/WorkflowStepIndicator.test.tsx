import { render, screen } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, expect, it } from "vitest";

import {
  WorkflowStepIndicator,
  type WorkflowStep,
} from "./WorkflowStepIndicator";

expect.extend(toHaveNoViolations);

const steps: WorkflowStep[] = [
  { id: "scope", label: "Scope" },
  { id: "intelligence", label: "Intelligence" },
  { id: "studio", label: "Model" },
  { id: "deliverables", label: "Deliver" },
];

describe("WorkflowStepIndicator", () => {
  it("marks the active step as the current workflow step", () => {
    render(
      <WorkflowStepIndicator
        steps={steps}
        activeStepId="studio"
        completedStepIds={["scope"]}
      />
    );

    expect(screen.getByLabelText("Model: Current step")).toHaveAttribute(
      "aria-current",
      "step"
    );
    expect(screen.getByText("Model in progress")).toBeInTheDocument();
  });

  it("labels completed steps and updates progress copy", () => {
    render(
      <WorkflowStepIndicator
        steps={steps}
        activeStepId="deliverables"
        completedStepIds={["scope", "intelligence", "studio"]}
      />
    );

    expect(screen.getByLabelText("Scope: Completed")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Intelligence: Completed")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Model: Completed")).toBeInTheDocument();
    expect(screen.getByText("3 of 4 steps completed")).toBeInTheDocument();
    expect(
      screen.getByLabelText("3 of 4 workflow steps completed")
    ).toBeInTheDocument();
  });

  it("renders an empty state when no workflow steps are available", () => {
    render(<WorkflowStepIndicator steps={[]} />);

    expect(screen.getByLabelText("Workflow progress")).toBeInTheDocument();
    expect(
      screen.getByText("No workflow steps available.")
    ).toBeInTheDocument();
    expect(screen.getByText("Empty")).toBeInTheDocument();
  });

  it("provides accessible labels without axe violations", async () => {
    const { container } = render(
      <WorkflowStepIndicator
        steps={steps}
        activeStepId="intelligence"
        completedStepIds={["scope"]}
      />
    );

    expect(
      screen.getByRole("navigation", { name: "Workflow progress" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Workflow steps" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Intelligence: Current step")).toHaveAttribute(
      "aria-current",
      "step"
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
