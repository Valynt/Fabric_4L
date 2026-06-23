import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { createWrapperWithRouterPath } from "@/test-utils";
import { useWorkflowContext } from "./useWorkflowContext";

describe("useWorkflowContext behavior invariants", () => {
  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("valid workflow parameters are parsed from URL", () => {
    const wrapper = createWrapperWithRouterPath(
      "/accounts/new?wfAccountId=url-account&wfSessionId=url-session&wfStep=4"
    );
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBe("url-account");
    expect(result.current.sessionId).toBe("url-session");
    expect(result.current.step?.stepIndex).toBe(4);
  });

  it("zero-indexed step is parsed correctly", () => {
    const wrapper = createWrapperWithRouterPath("/accounts/new?wfStep=0");
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.step?.stepIndex).toBe(0);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior — missing params get safe defaults
  // ───────────────────────────────────────────────────────────────────────────
  it("missing workflow parameters return safe defaults", () => {
    const wrapper = createWrapperWithRouterPath("/accounts/new");
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBeUndefined();
    expect(result.current.sessionId).toBeUndefined();
    expect(result.current.step).toEqual({ stepIndex: 0, stepKey: "unknown", activeTab: undefined });
  });

  it("partial parameters return defaults for missing fields", () => {
    const wrapper = createWrapperWithRouterPath("/accounts/new?wfAccountId=only-account");
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBe("only-account");
    expect(result.current.sessionId).toBeUndefined();
    expect(result.current.step?.stepIndex).toBe(0);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("invalid numeric step is surfaced as NaN rather than coerced to default", () => {
    const wrapper = createWrapperWithRouterPath("/accounts/new?wfStep=not-a-number");
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(Number.isNaN(result.current.step?.stepIndex)).toBe(true);
  });

  it("negative step index is preserved as-is for downstream validation", () => {
    const wrapper = createWrapperWithRouterPath("/accounts/new?wfStep=-1");
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.step?.stepIndex).toBe(-1);
  });
});
