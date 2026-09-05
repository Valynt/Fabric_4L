/**
 * Value Studio (mission-led) — projection adapter seam.
 *
 * Contract: FE-VOS-STUDIO-001, STEP 2 (adapter contracts). This is the single
 * data boundary for the page: components never fetch and never derive domain
 * state; they receive a `ValueStudioViewState` produced by an adapter.
 *
 * Phase 1 ships `FixtureValueStudioAdapter`, which serves the deterministic
 * named fixtures. Phase 2 replaces it with a TanStack Query adapter over the
 * backend projection endpoint without changing component props or view states.
 */

import {
  DEFAULT_VALUE_STUDIO_FIXTURE,
  getValueStudioFixture,
  isValueStudioFixtureName,
  type ValueStudioFixtureName,
} from "./fixtures";
import type { ValueStudioViewState } from "./types";

export interface ValueStudioProjectionRequest {
  readonly tenantSlug: string;
  readonly accountId: string;
  /**
   * Fixture selector, sourced from the `fixture` query parameter in Phase 1.
   * Removed when the backend adapter lands.
   */
  readonly fixtureName?: string | null;
}

export interface ValueStudioProjectionAdapter {
  getProjection(request: ValueStudioProjectionRequest): Promise<ValueStudioViewState>;
}

/**
 * Phase 1 adapter: deterministic fixtures, resolved synchronously and wrapped
 * in a promise so the seam matches the future async backend adapter.
 */
export class FixtureValueStudioAdapter implements ValueStudioProjectionAdapter {
  getProjection(request: ValueStudioProjectionRequest): Promise<ValueStudioViewState> {
    const requested = request.fixtureName ?? null;
    const fixtureName: ValueStudioFixtureName = isValueStudioFixtureName(requested)
      ? requested
      : DEFAULT_VALUE_STUDIO_FIXTURE;
    return Promise.resolve(getValueStudioFixture(fixtureName).view);
  }
}

export const fixtureValueStudioAdapter = new FixtureValueStudioAdapter();
