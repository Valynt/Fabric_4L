# Remediation Allowlist

## P0.2 — Frontend dead-code validation (dynamic import analysis)

The following files were incorrectly flagged as "high-confidence unused exports" in the remediation plan. This allowlist records the runtime importer that keeps each file live.

| File | Status | Live importer / evidence |
|---|---|---|
| `apps/web/src/pages/studio/NarrativeTab.tsx` | **KEEP** | Dynamically imported by `apps/web/src/features/value-studio/studioTabRegistry.ts` as `lazy(() => import("@/pages/studio/NarrativeTab"))` and mounted as the `narrative` tab in the Value Studio workspace. |
| `apps/web/src/pages/InteractiveBusinessCase.tsx` | **KEEP** | Dynamically imported by `apps/web/src/shell/router.tsx` as `lazy(() => import("@/pages/InteractiveBusinessCase"))` and wired into the React Router route tree. |
| `apps/web/src/pages/intelligence/ROITab.tsx` | **REMOVED** | Deleted as dead code after verifying no `lazy(() => import(...))`, static import, re-export, route, or tab registry reference under `apps/web/src`; the active ROI calculator tab remains `@/pages/calculator/ROITab.tsx`. |
| `apps/web/src/pages/value-case/ValueCasePage.tsx` | **KEEP** | Dynamically imported by `apps/web/src/features/value-studio/studioTabRegistry.ts` as `lazy(() => import("@/pages/value-case/ValueCasePage"))` and mounted as the `value-case` tab. |
| `apps/web/src/pages/realization/RealizationPage.tsx` | **KEEP** | Dynamically imported by `apps/web/src/features/value-studio/studioTabRegistry.ts` as `lazy(() => import("@/pages/realization/RealizationPage"))` and mounted as the `value-realization` tab. |

### Methodology

- Searched `apps/web/src` for `lazy\(\s*\(\)\s*=>` patterns.
- Extracted the imported module paths and mapped them back to the five flagged files.
- Verified each importer registers the lazy component in a tab registry or route tree.
- Checked for static imports and re-exports referencing the five files.

### Notes

- `apps/web/src/pages/intelligence/ROITab.tsx` was removed as dead code; the active ROI calculator remains `apps/web/src/pages/calculator/ROITab.tsx`.

## Validation

Commands were re-run on the clean worktree to verify that the dynamic-import analysis did not break the frontend.

| Command | Exit code | Result | Notes |
|---|---|---|---|
| `pnpm --dir apps/web run typecheck` | `0` | **PASS** | `tsc --noEmit` completes with no errors. |
| `pnpm --dir apps/web run build` | `1` | **FAIL** | Fails due to pre-existing issues unrelated to the dead-code analysis: |

### Build failure details (pre-existing)

1. **Missing required production API environment variables.** `vite.config.ts` asserts the presence of layer route prefixes; without them the Vite config fails before bundling begins.

   ```text
   Error: Vite frontend build is missing required production API environment variables.
   - gateway API version prefix requires one of: VITE_API_VERSION_PREFIX, VITE_API_BASE
   - Layer 1 route prefix requires one of: VITE_LAYER1_ROUTE_PREFIX, VITE_L1_PREFIX
   - ...
   ```

2. **OpenTelemetry ESM bundling error.** When the required env vars are supplied, production bundling fails with a Rollup error in `@opentelemetry/sdk-trace-base`:

   ```text
   ../../node_modules/.pnpm/@opentelemetry+sdk-trace-base/.../config.js (17:9):
   "getEnv" is not exported by "../../node_modules/.pnpm/@opentelemetry+core/.../index.js",
   imported by "../../node_modules/.pnpm/@opentelemetry+sdk-trace-base/.../config.js".
   ```

Both failures reproduce on the clean worktree and are independent of the files listed in this allowlist. `typecheck` passes on its own; only `build` fails, and only for pre-existing environment/dependency reasons.

