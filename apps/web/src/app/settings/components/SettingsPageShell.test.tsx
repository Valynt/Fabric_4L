import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { SettingsPageShell } from "./SettingsPageShell";

interface TestData {
  name: string;
}

function TestChild({ data }: { data: TestData }) {
  return <div data-testid="child">{data.name}</div>;
}

describe("SettingsPageShell", () => {
  it("renders loading state", () => {
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        data={undefined}
        isLoading
        error={null}
        loadingLabel="Loading workspace..."
      />
    );
    expect(screen.getByText("Loading workspace...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        data={undefined}
        isLoading={false}
        error={new Error("boom")}
        loadingLabel="Loading workspace..."
        errorTitle="Failed to load workspace"
      />
    );
    expect(screen.getByText("Failed to load workspace")).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("renders empty state", () => {
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        data={undefined}
        isLoading={false}
        error={null}
        loadingLabel="Loading workspace..."
        emptyLabel="No workspace settings"
      />
    );
    expect(screen.getByText("No workspace settings")).toBeInTheDocument();
  });

  it("renders title, metrics, and children when data is available", () => {
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        description="Manage workspace settings"
        data={{ name: "Acme" }}
        isLoading={false}
        error={null}
        loadingLabel="Loading workspace..."
        metrics={[{ label: "Name", value: "Acme" }]}
      >
        {(data) => <TestChild data={data} />}
      </SettingsPageShell>
    );
    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(screen.getByText("Manage workspace settings")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByTestId("child")).toHaveTextContent("Acme");
  });

  it("calls onSave when save button is clicked", () => {
    const onSave = vi.fn();
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        data={{ name: "Acme" }}
        isLoading={false}
        error={null}
        loadingLabel="Loading workspace..."
        onSave={onSave}
        dirty
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it("disables save button when not dirty", () => {
    const onSave = vi.fn();
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        data={{ name: "Acme" }}
        isLoading={false}
        error={null}
        loadingLabel="Loading workspace..."
        onSave={onSave}
        dirty={false}
      />
    );
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  });

  it("does not render save button when readOnly", () => {
    render(
      <SettingsPageShell<TestData>
        title="Workspace"
        data={{ name: "Acme" }}
        isLoading={false}
        error={null}
        loadingLabel="Loading workspace..."
        onSave={vi.fn()}
        readOnly
      />
    );
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();
  });
});
