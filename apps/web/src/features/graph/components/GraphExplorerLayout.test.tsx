import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { GraphExplorerLayout } from "./GraphExplorerLayout";

describe("GraphExplorerLayout", () => {
  it("renders the three slots", () => {
    render(
      <GraphExplorerLayout
        controls={<div data-testid="controls-slot">Controls</div>}
        canvas={<div data-testid="canvas-slot">Canvas</div>}
        inspector={<div data-testid="inspector-slot">Inspector</div>}
      />
    );

    expect(screen.getByTestId("controls-slot")).toHaveTextContent("Controls");
    expect(screen.getByTestId("canvas-slot")).toHaveTextContent("Canvas");
    expect(screen.getByTestId("inspector-slot")).toHaveTextContent("Inspector");
  });
});
