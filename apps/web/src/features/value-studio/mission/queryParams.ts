/**
 * Value Studio (mission-led) — URL query parameter contract.
 *
 * `?lens=`    presentation lens selection (FE-LENS-004: survives refresh)
 * `?decision=` deep-link into the Review Required rail (initial focus §9)
 * `?fixture=`  Phase-1 named fixture selector (removed with the backend adapter)
 *
 * Parsing is total and type-safe: unknown values fall back to defaults.
 */

import { AUDIENCE_LENSES, type AudienceLens } from "./types";
import { isValueStudioFixtureName, type ValueStudioFixtureName } from "./fixtures";

export const VALUE_STUDIO_QUERY_KEYS = {
  lens: "lens",
  decision: "decision",
  fixture: "fixture",
} as const;

export function isAudienceLens(value: string): value is AudienceLens {
  return (AUDIENCE_LENSES as readonly string[]).includes(value);
}

export function parseLensParam(raw: string | null): AudienceLens | null {
  return raw !== null && isAudienceLens(raw) ? raw : null;
}

export function parseFixtureParam(raw: string | null): ValueStudioFixtureName | null {
  return isValueStudioFixtureName(raw) ? raw : null;
}

/** Decision deep-link id, e.g. `?decision=DISP-01`. Null when absent. */
export function parseDecisionParam(raw: string | null): string | null {
  return raw !== null && raw.length > 0 ? raw : null;
}
