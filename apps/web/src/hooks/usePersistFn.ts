import { useRef } from "react";

/**
 * usePersistFn instead of useCallback to reduce cognitive load.
 *
 * Creates a stable function reference that persists across renders without
 * needing dependency arrays. The returned function always calls the latest
 * version of the provided function.
 *
 * @param fn - The function to persist across renders
 * @returns A stable function reference with the same signature
 */
export function usePersistFn<Args extends unknown[], Return>(
  fn: (...args: Args) => Return
): (...args: Args) => Return {
  const fnRef = useRef<(...args: Args) => Return>(fn);
  fnRef.current = fn;

  const persistFn = useRef<(...args: Args) => Return>(
    ((...args: Args) => fnRef.current(...args)) as (...args: Args) => Return
  );

  return persistFn.current;
}
