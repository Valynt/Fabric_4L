/**
 * Navigation helper utilities.
 */

/**
 * Returns true when the given pathname matches the route pattern.
 *
 * Supports exact matches and prefix matches at segment boundaries.
 * A trailing `/*` suffix on the pattern is stripped before matching so
 * both `/foo` and `/foo/*` correctly match `/foo/bar`.
 * Leading and trailing slashes are normalised so callers don't need to be precise.
 */
export function isRouteActive(pathname: string, pattern: string): boolean {
  const normalise = (s: string) => s.replace(/\/+$/, "") || "/";
  const p = normalise(pathname);
  const r = normalise(pattern.replace(/\/\*$/, ""));

  if (r === "/") return p === "/";

  // Exact match or prefix match at a segment boundary.
  return p === r || p.startsWith(r + "/");
}
