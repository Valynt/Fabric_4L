import { useRef } from "react";

type PersistableFunction = (...args: never[]) => unknown;

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
export function usePersistFn<T extends PersistableFunction>(fn: T): T {
  const fnRef = useRef<T>(fn);
  fnRef.current = fn;

  const persistFn = useRef<T>(
    ((...args: Parameters<T>): ReturnType<T> =>
      fnRef.current(...args) as ReturnType<T>) as T
  );

  return persistFn.current;
}
