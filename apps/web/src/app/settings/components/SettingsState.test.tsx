import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  SettingsMetricGrid,
  SettingsQueryState,
  SettingsSaveButton,
} from "./SettingsState";

describe("SettingsQueryState", () => {
  it("renders the standardized loading state", () => {
    render(
      <SettingsQueryState
        data={undefined}
        isLoading
        error={null}
        loadingLabel="Loading workspace settings..."
      >
        {() => <p>Loaded</p>}
      </SettingsQueryState>
    );

    expect(screen.getByText("Loading workspace settings...")).toBeInTheDocument();
  });

  it("renders the standardized error state", () => {
    render(
      <SettingsQueryState
        data={undefined}
        isLoading={false}
        error={new Error("Request failed")}
        loadingLabel="Loading"
        errorTitle="Failed to load workspace settings"
      >
        {() => <p>Loaded</p>}
      </SettingsQueryState>
    );

    expect(screen.getByText("Failed to load workspace settings")).toBeInTheDocument();
    expect(screen.getByText("Request failed")).toBeInTheDocument();
  });

  it("renders data and metric cards when the query succeeds", () => {
    render(
      <SettingsQueryState
        data={{ workspace: "Acme" }}
        isLoading={false}
        error={null}
        loadingLabel="Loading"
      >
        {(data) => (
          <SettingsMetricGrid
            metrics={[{ label: "Workspace name", value: data.workspace }]}
          />
        )}
      </SettingsQueryState>
    );

    expect(screen.getByText("Workspace name")).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
  });
});

describe("SettingsSaveButton", () => {
  it("disables duplicate submits while a mutation is pending", () => {
    const onClick = vi.fn();
    render(
      <SettingsSaveButton isPending onClick={onClick}>
        Save workspace
      </SettingsSaveButton>
    );

    const button = screen.getByRole("button", { name: "Saving..." });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});
