import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GraphExplorerControls } from "./GraphExplorerControls";

describe("GraphExplorerControls", () => {
  it("calls onQueryChange when the user types", async () => {
    const onQueryChange = vi.fn();
    render(
      <GraphExplorerControls
        queryText=""
        onQueryChange={onQueryChange}
        onSearch={vi.fn()}
        onZoomIn={vi.fn()}
        onZoomOut={vi.fn()}
        onResetView={vi.fn()}
        scale={1}
        isSearching={false}
      />
    );

    const input = screen.getByPlaceholderText("Search entities...");
    await userEvent.type(input, "r");

    expect(onQueryChange).toHaveBeenLastCalledWith("r");
  });

  it("calls onSearch when the user presses Enter", async () => {
    const onSearch = vi.fn();
    render(
      <GraphExplorerControls
        queryText="revenue"
        onQueryChange={vi.fn()}
        onSearch={onSearch}
        onZoomIn={vi.fn()}
        onZoomOut={vi.fn()}
        onResetView={vi.fn()}
        scale={1}
        isSearching={false}
      />
    );

    const input = screen.getByPlaceholderText("Search entities...");
    await userEvent.type(input, "{enter}");

    expect(onSearch).toHaveBeenCalledTimes(1);
  });

  it("calls canvas action callbacks", async () => {
    const onZoomIn = vi.fn();
    const onZoomOut = vi.fn();
    const onResetView = vi.fn();
    render(
      <GraphExplorerControls
        queryText=""
        onQueryChange={vi.fn()}
        onSearch={vi.fn()}
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
        onResetView={onResetView}
        scale={1.5}
        isSearching={false}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /zoom in/i }));
    await userEvent.click(screen.getByRole("button", { name: /zoom out/i }));
    await userEvent.click(screen.getByRole("button", { name: /reset view/i }));

    expect(onZoomIn).toHaveBeenCalledTimes(1);
    expect(onZoomOut).toHaveBeenCalledTimes(1);
    expect(onResetView).toHaveBeenCalledTimes(1);
  });

  it("displays the current zoom scale", () => {
    render(
      <GraphExplorerControls
        queryText=""
        onQueryChange={vi.fn()}
        onSearch={vi.fn()}
        onZoomIn={vi.fn()}
        onZoomOut={vi.fn()}
        onResetView={vi.fn()}
        scale={1.25}
        isSearching={false}
      />
    );

    expect(screen.getByText("125%")).toBeInTheDocument();
  });
});
