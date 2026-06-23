import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { usePersistFn } from "./usePersistFn";

describe("usePersistFn", () => {
  it("returns a stable function reference across renders", () => {
    const { result, rerender } = renderHook(
      ({ fn }) => usePersistFn(fn),
      { initialProps: { fn: () => 1 } }
    );

    const firstRef = result.current;
    rerender({ fn: () => 2 });

    expect(result.current).toBe(firstRef);
  });

  it("always calls the latest function", () => {
    const fnA = vi.fn().mockReturnValue("a");
    const fnB = vi.fn().mockReturnValue("b");

    const { result, rerender } = renderHook(
      ({ fn }) => usePersistFn(fn),
      { initialProps: { fn: fnA } }
    );

    expect(result.current()).toBe("a");

    rerender({ fn: fnB });

    expect(result.current()).toBe("b");
    expect(fnA).toHaveBeenCalledTimes(1);
    expect(fnB).toHaveBeenCalledTimes(1);
  });

  it("preserves arguments and return value", () => {
    const fn = (prefix: string, suffix: number) => `${prefix}-${suffix}`;
    const { result } = renderHook(() => usePersistFn(fn));

    expect(result.current("answer", 42)).toBe("answer-42");
  });
});
