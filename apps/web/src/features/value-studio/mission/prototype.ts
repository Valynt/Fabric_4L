/**
 * Value Studio (mission-led) — Slice 1 prototype gate.
 *
 * FE-VOS-STUDIO-001 Slice 1 renders a fixture-backed prototype with no live
 * backend projection. Per review, the route must stay behind an explicit
 * prototype flag so it cannot ship as a live product surface:
 *
 * - Production builds: DISABLED unless `VITE_ENABLE_VS_MISSION_PROTOTYPE=true`
 *   is explicitly set at build time.
 * - Dev/test builds: enabled by default so local development and CI tests can
 *   exercise the prototype.
 *
 * The `?fixture=` selector is a dev/test-only debug affordance. Production
 * builds ignore it even when the prototype flag is enabled, so callers cannot
 * select fictional scenarios in production.
 */

const isProductionBuild =
  import.meta.env.PROD || import.meta.env.VITE_APP_ENV === "production";

const prototypeFlag = import.meta.env.VITE_ENABLE_VS_MISSION_PROTOTYPE;

export const isValueStudioMissionPrototypeEnabled =
  !isProductionBuild || prototypeFlag === "true";

export const isValueStudioFixtureSelectorEnabled = !isProductionBuild;
