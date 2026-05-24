/**
 * Test helper for switching VITE_AUTH_PROVIDER inside a single test without
 * leaking state to neighboring tests. Restores the original value on exit
 * regardless of how the inner function terminates.
 *
 * Usage:
 *   await withAuthProvider("clerk", async () => {
 *     // ... isClerkAuthEnabled() === true here ...
 *   });
 */
type EnvBag = Record<string, unknown>;

const AUTH_PROVIDER_KEY = "VITE_AUTH_PROVIDER";

function env(): EnvBag {
  // Vitest leaves import.meta.env writable. We assert it as a mutable bag.
  return import.meta.env as unknown as EnvBag;
}

export function setAuthProvider(value: string | undefined): void {
  if (value === undefined) {
    delete env()[AUTH_PROVIDER_KEY];
  } else {
    env()[AUTH_PROVIDER_KEY] = value;
  }
}

export async function withAuthProvider<T>(
  value: string | undefined,
  fn: () => Promise<T> | T,
): Promise<T> {
  const previous = env()[AUTH_PROVIDER_KEY] as string | undefined;
  setAuthProvider(value);
  try {
    return await fn();
  } finally {
    setAuthProvider(previous);
  }
}
