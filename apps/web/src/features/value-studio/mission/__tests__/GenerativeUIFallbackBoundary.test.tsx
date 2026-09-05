/**
 * Regression tests for the generative-UI fallback boundary reset contract
 * (PR #1679 review, R3): a latched render failure must clear when the
 * wrapped projection identity (`resetKey`) changes — a recovered projection
 * must not stay hidden behind the fallback until the route remounts.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GenerativeUIFallbackBoundary } from "../components/GenerativeUIFallbackBoundary";

vi.mock("@/lib/telemetry", () => ({
  captureException: vi.fn(),
  createFeatureLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
    withContext: vi.fn(),
  }),
}));

function MaybeThrow({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("boom");
  return <div>healthy comparison</div>;
}

describe("GenerativeUIFallbackBoundary", () => {
  it("renders the static fallback after a child render failure", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <GenerativeUIFallbackBoundary componentName="BranchComparison" resetKey="p1">
        <MaybeThrow shouldThrow />
      </GenerativeUIFallbackBoundary>,
    );
    expect(screen.getByTestId("generative-ui-fallback")).toBeInTheDocument();
    expect(screen.queryByText("healthy comparison")).not.toBeInTheDocument();
  });

  it("resets a latched failure when the resetKey (projection identity) changes", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { rerender } = render(
      <GenerativeUIFallbackBoundary componentName="BranchComparison" resetKey="p1">
        <MaybeThrow shouldThrow />
      </GenerativeUIFallbackBoundary>,
    );
    expect(screen.getByTestId("generative-ui-fallback")).toBeInTheDocument();

    // A different projection (refetch / fixture switch / new version) arrives.
    rerender(
      <GenerativeUIFallbackBoundary componentName="BranchComparison" resetKey="p2">
        <MaybeThrow shouldThrow={false} />
      </GenerativeUIFallbackBoundary>,
    );
    expect(screen.getByText("healthy comparison")).toBeInTheDocument();
    expect(screen.queryByTestId("generative-ui-fallback")).not.toBeInTheDocument();
  });

  it("keeps the fallback latched while the resetKey is unchanged", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { rerender } = render(
      <GenerativeUIFallbackBoundary componentName="BranchComparison" resetKey="p1">
        <MaybeThrow shouldThrow />
      </GenerativeUIFallbackBoundary>,
    );
    expect(screen.getByTestId("generative-ui-fallback")).toBeInTheDocument();

    // Same projection identity re-renders (e.g. unrelated state change): the
    // failure stays latched so a broken projection does not flap.
    rerender(
      <GenerativeUIFallbackBoundary componentName="BranchComparison" resetKey="p1">
        <MaybeThrow shouldThrow={false} />
      </GenerativeUIFallbackBoundary>,
    );
    expect(screen.getByTestId("generative-ui-fallback")).toBeInTheDocument();
    expect(screen.queryByText("healthy comparison")).not.toBeInTheDocument();
  });
});
