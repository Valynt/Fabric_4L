# Live Workflow Validation

`docker-compose.live.yml` is the canonical local/Bunnyshell live validation stack for Fabric_4L. It combines the frontend with the full backend-integrated L1-L6 stack so Playwright can exercise real user workflows against live services instead of mocked or partial environments.

## Purpose

- Keep [docker-compose.backend-integrated.yml](/workspaces/Fabric_4L/docker-compose.backend-integrated.yml) as the backend-only validation stack.
- Keep [docker-compose.release-smoke.yml](/workspaces/Fabric_4L/docker-compose.release-smoke.yml) as the release-smoke backend stack.
- Keep [docker-compose.dev.yml](/workspaces/Fabric_4L/docker-compose.dev.yml) as the partial developer stack.
- Keep [docker-compose.e2e.yml](/workspaces/Fabric_4L/docker-compose.e2e.yml) as the deterministic minimal Playwright backend.
- Use [docker-compose.live.yml](/workspaces/Fabric_4L/docker-compose.live.yml) for live workflow validation and Bunnyshell imports.

## Stack Contents

- Frontend: `frontend` from `apps/web`
- Backend layers: `layer1`, `layer1-worker`, `layer2`, `layer3`, `layer4`, `layer5`, `layer5-migrate`, `layer6`
- Backing stores: `postgres`, `redis`, `neo4j`, `minio`, `minio-init`
- Optional seed service: `live-seed` under the `seed` profile

## Frontend Runtime

The frontend runs its existing Vite dev server on container port `3001` and is published on host port `3001` for live validation.

- Public frontend URL: `http://localhost:3001`
- Internal frontend health URL: `http://frontend:3001`

The Vite proxy is configured to route live API traffic to Docker service names inside the live stack. For local backend-integrated runs outside Docker, `pnpm run dev:live` starts Vite on port `3001` with mocks disabled and proxy targets defaulted to the backend-integrated host ports (`8001` through `8006`).

Important:

- This repo still uses `VITE_API_BASE` for the browser path prefix.
- Browser API clients use relative `/api/v1` paths and do not call `VITE_API_BASE_URL` directly.
- The Vite dev server proxies those browser requests server-side to `VITE_PROXY_L4_URL` and the other layer proxy targets.
- `VITE_API_BASE_URL` is intentionally not set in the live stack, so the browser is never pointed at Docker-internal hostnames like `http://layer4:8000`.
- `VITE_USE_MOCKS` is forced to `false` in the live stack.
- `VITE_ENABLE_MOCK_FALLBACK` is forced to `false` in the live stack.

## Ports

Published host ports for live validation:

- Frontend: `3001 -> 3001`
- Layer 4: `8004 -> 8000`

Internal-only services in `docker-compose.live.yml`:

- Layer 1
- Layer 2
- Layer 3
- Layer 5
- Layer 6
- postgres
- redis
- neo4j
- minio
- minio-init

## Start The Live Stack

From repo root:

```bash
docker compose -f docker-compose.live.yml config
docker compose -f docker-compose.live.yml up -d
docker compose -f docker-compose.live.yml ps
```

## Health Verification

```bash
curl http://localhost:3001
curl http://localhost:8004/health
```

Layer 1, Layer 2, Layer 3, Layer 5, and Layer 6 remain internal in the live stack. If you need to inspect them locally, either use `docker compose exec` inside the network or temporarily add debug port mappings.

## Seed Path

Manual live seed from the frontend workspace:

```bash
cd apps/web
PLAYWRIGHT_BACKEND_URL=http://localhost:8004 pnpm run seed:live
```

`seed:live` fails closed if `PLAYWRIGHT_BACKEND_URL` is missing or if frontend mock flags are enabled. The older `seed:e2e` command remains available for non-live backend-integrated development, but live validation should use `seed:live` so the guardrails are enforced consistently.

Or use the compose one-off service:

```bash
docker compose -f docker-compose.live.yml --profile seed run --rm live-seed
```

The seed path is intended to create or reconcile the live validation tenant and deterministic test actors, including:

- admin user
- sales user
- reviewer user
- read-only user
- prospect account
- value pack
- evidence
- benchmarks
- formulas
- approval/export-safe test state

The seed service is not started automatically.

## Automated Live Validation Gate

From repo root, run the fail-closed automation gate:

```bash
# Validate compose syntax and frontend guardrails only — no containers started.
scripts/ci/run_live_workflow_validation.sh --config-only

# Start the live stack, probe all layer health endpoints, write a timestamped
# evidence artifact, then tear down. Completes in ~5 minutes.
scripts/ci/run_live_workflow_validation.sh --smoke

# Full validation with seed and Playwright P0 suite.
scripts/ci/run_live_workflow_validation.sh --seed --playwright
```

### Validation Modes

| Mode | Containers started | Health probed | Teardown | CI trigger |
|---|---|---|---|---|
| `--config-only` | No | No | N/A | PR/push to `main` (path-filtered) |
| `--smoke` | Yes | Yes (all layers) | Yes (automatic) | Every push to `release/**` |
| `--no-start` | No | Yes (running stack) | No | Manual / `workflow_dispatch` |
| `--remote` | No | Yes (URL-based) | No | Manual / `workflow_dispatch` |
| (default / `full`) | Yes | Yes | No | Manual / `workflow_dispatch` |

### Smoke Mode Evidence Artifact

`--smoke` writes a SHA-stamped JSON artifact to:

```
artifacts/live-workflow-validation/live-stack-smoke-evidence-<sha>.json
```

The artifact contains per-layer container health states, endpoint probe results, and a top-level `result: PASS | FAIL` field. It is uploaded to GitHub Actions with 90-day retention under the artifact name `live-stack-smoke-evidence-<sha>`.

This artifact is the evidence required to close the live-stack CI gap identified in Sprint 1A of `docs/launch/sprint-launch-plan.md`.

### CI Wiring

- **PR / push to `main`** (path-filtered): `live-validation-gate` job runs `--config-only`.
- **Push to `release/**`** (any path): `live-smoke-gate` job runs `--smoke` automatically.
- **`workflow_dispatch`**: Both jobs are available; select mode from the dropdown.

## Playwright Live Commands

From `apps/web`:

```bash
PLAYWRIGHT_LIVE_MODE=true \
PLAYWRIGHT_LIVE_FRONTEND_URL=http://localhost:3001 \
PLAYWRIGHT_BACKEND_URL=http://localhost:8004 \
pnpm run test:e2e:live:p0
```

Available scripts in [apps/web/package.json](/workspaces/Fabric_4L/apps/web/package.json):

- `dev:live`
- `seed:live`
- `test:e2e:live`
- `test:e2e:live:p0`
- `test:e2e:live:golden-path`

These scripts map the live URLs into the existing Playwright contract using:

- `PLAYWRIGHT_BASE_URL`
- `PLAYWRIGHT_BACKEND_URL`

They fail closed if any of these are missing:

- `PLAYWRIGHT_LIVE_MODE`
- `PLAYWRIGHT_LIVE_FRONTEND_URL`
- `PLAYWRIGHT_BACKEND_URL`

They also fail closed if `VITE_USE_MOCKS`, `VITE_ENABLE_MOCK_FALLBACK`, `MSW`, or `MOCKS_ENABLED` is truthy. A live PASS cannot be produced from a mock-enabled browser session.

## Bunnyshell Usage

Import [docker-compose.live.yml](/workspaces/Fabric_4L/docker-compose.live.yml) into Bunnyshell for live workflow validation.

Bunnyshell should detect:

- `frontend`
- `layer1`
- `layer1-worker`
- `layer2`
- `layer3`
- `layer4`
- `layer5`
- `layer5-migrate`
- `layer6`
- `postgres`
- `redis`
- `neo4j`
- `minio`
- `minio-init`

If Playwright is running outside the Bunnyshell environment, override with the public URLs exposed by Bunnyshell rather than Docker-internal names:

- `PLAYWRIGHT_LIVE_FRONTEND_URL=https://<frontend-public-url>`
- `PLAYWRIGHT_BACKEND_URL=https://<layer4-public-url>`

Browser traffic should still go through the frontend public URL so the Vite proxy can route requests to the live backend services.

## Required Environment Variables

Frontend live stack settings:

```env
VITE_API_BASE=/api/v1
VITE_PROXY_L1_URL=http://layer1:8000
VITE_PROXY_L2_URL=http://layer2:8000
VITE_PROXY_L3_URL=http://layer3:8001
VITE_PROXY_L4_URL=http://layer4:8000
VITE_PROXY_L5_URL=http://layer5:8005
VITE_PROXY_L6_URL=http://layer6:8006
```

Local development fallback remains:

```env
VITE_API_BASE=/api/v1
VITE_PROXY_L4_URL=http://localhost:8004
```

Playwright live validation settings:

```env
PLAYWRIGHT_LIVE_MODE=true
PLAYWRIGHT_LIVE_FRONTEND_URL=http://localhost:3001
PLAYWRIGHT_BACKEND_URL=http://localhost:8004
```

## PASS / FAIL / BLOCKED Rules

- `PASS`: compose resolves, the required services become healthy, seed succeeds if invoked, and the targeted Playwright live suite completes without failures.
- `FAIL`: compose resolves but one or more required services, seed steps, or Playwright live tests fail.
- `BLOCKED`: compose foundation exists, but runtime health validation or Playwright live execution was not performed or could not be completed in the current environment.

## Live Environment Gate

Run these checks in order before any P0 live workflow validation:

1. Bunnyshell deploy succeeds.
2. Frontend public URL opens.
3. Layer 4 public health responds.
4. The frontend can make a real API call to Layer 4 from browser context.
5. Layer 1 internal health passes.
6. Layer 2 internal health passes.
7. Layer 3 internal health passes at `http://layer3:8001/health`.
8. Layer 5 internal health passes at `http://layer5:8005/api/v1/health`.
9. Layer 6 internal health passes at `http://layer6:8006/health`.
10. Postgres, Redis, Neo4j, and MinIO are healthy.
11. Layer 5 migration completes successfully.
12. MinIO init completes successfully.
13. Seed command succeeds or the seed blocker is documented.
14. Playwright can open the frontend.
15. Playwright can authenticate into the app.

If the gate fails, live validation remains `BLOCKED`. Do not substitute mocked E2E for this gate.

## Bunnyshell Live Environment Gate Report

| Check | Status | Evidence | Fix Needed |
| --- | --- | --- | --- |
| Bunnyshell deploy | Blocked | Not run from this environment | Run Bunnyshell deployment |
| Frontend public URL | Blocked | Not run from this environment | Open `https://frontend-{{ env.base_domain }}` |
| Layer 4 public health | Blocked | Not run from this environment | Check `https://layer4-{{ env.base_domain }}/health` |
| Browser API call to Layer 4 | Blocked | Browser connectivity not validated | Verify a real `/api/v1/agents/...` request in browser devtools |
| L1 internal health | Blocked | Not run from this environment | Check `http://layer1:8000/health` inside network |
| L2 internal health | Blocked | Not run from this environment | Check `http://layer2:8000/health` inside network |
| L3 internal health | Blocked | Not run from this environment | Check `http://layer3:8001/health` inside network |
| L5 internal health | Blocked | Not run from this environment | Check `http://layer5:8005/api/v1/health` inside network |
| L6 internal health | Blocked | Not run from this environment | Check `http://layer6:8006/health` inside network |
| Postgres | Blocked | Not run from this environment | Confirm service healthy in Bunnyshell |
| Redis | Blocked | Not run from this environment | Confirm service healthy in Bunnyshell |
| Neo4j | Blocked | Not run from this environment | Confirm service healthy in Bunnyshell |
| MinIO | Blocked | Not run from this environment | Confirm service healthy in Bunnyshell |
| Layer 5 migration | Blocked | Migration not executed here | Review `layer5-migrate` completion |
| MinIO init | Blocked | Init job not executed here | Review `minio-init` completion |
| Seed command | Blocked | Seed not executed here | Run seed or document blocker |
| Playwright opens frontend | Blocked | Live Playwright not executed | Run live Playwright after gate passes |
| Playwright authenticates | Blocked | Live Playwright not executed | Validate login or dev-auth flow |

## Validation Report

| Check | Result |
| --- | --- |
| compose config valid | Pending runtime validation command |
| frontend included | Yes |
| L1–L6 included | Yes |
| backing stores included | Yes |
| frontend port | 3001 |
| Vite proxy env-driven | Yes |
| browser API path verified from source | Yes |
| local dev fallback preserved | Yes |
| health checks defined | Yes |
| automated live validation gate | Yes — `scripts/ci/run_live_workflow_validation.sh` |
| seed path documented | Yes — guarded by `seed:live` |
| Playwright live command documented | Yes — guarded by `live-env-guard.mjs` |
| runtime health validation | Sprint 1 backend-integrated L1-L6 startup now healthy; canonical `docker-compose.live.yml` still requires full runtime validation |
| Playwright live execution | Blocked |
| Bunnyshell import target | `docker-compose.live.yml` |

## Scope Note

This setup creates the live stack required to run validation. It does not imply that live workflows already pass.

## Second Sprint Loop: Evidence, Seed, and Browser Artifact Hardening

The second live-readiness loop extends the fail-closed validation model. The canonical command remains `scripts/ci/run_live_workflow_validation.sh`, but the runner now writes a richer evidence bundle under `artifacts/live-workflow-validation` or the `ARTIFACT_DIR` override. The bundle includes a Markdown summary, resolved compose configuration, container status, JSON-lines health state, endpoint probe results, sanitized per-service logs, optional seed output, and optional Playwright evidence.

| Area | New behavior | Operational effect |
|---|---|---|
| Gate evidence | Failure paths collect sanitized container status, health, endpoint probes, and service logs. | A blocked or failed run now leaves enough evidence for remediation without requiring noisy raw console logs. |
| Seed verification | `scripts/db/seed-e2e-data.ts` supports `SEED_REPORT_JSON`, `--report-json`, `SEED_STRICT=true`, and `--strict`. | Deterministic seed readiness is machine-readable, and strict seed runs fail closed when any required seed area is not present. |
| Live Playwright | Live mode writes HTML, JUnit, and trace artifacts to deterministic locations via `PLAYWRIGHT_HTML_REPORT`, `PLAYWRIGHT_JUNIT_FILE`, and `PLAYWRIGHT_OUTPUT_DIR`. | A requested browser validation cannot be treated as complete unless durable browser evidence exists. |
| Mock ban | The central `mockSequentialResponses` helper rejects live mode, and backend-required tests reject mock flags. | Live P0 validation cannot silently pass through route fulfillment helpers intended for fixture-only tests. |

For a configuration-only check, run `ARTIFACT_DIR=/tmp/fabric-live-config ./scripts/ci/run_live_workflow_validation.sh --config-only`. For a full live run with deterministic seed and browser evidence, run `RUN_LIVE_SEED=true RUN_LIVE_PLAYWRIGHT=true ./scripts/ci/run_live_workflow_validation.sh --seed --playwright` against the live stack. A result should only be considered live-valid when the summary reports `PASS` and the referenced seed and Playwright artifacts exist.

## Third Sprint Loop: Machine-Readable Evidence and Seed Preflight Contract

The third live-readiness loop hardens the validation gate for CI and operator consumption. In addition to the existing Markdown summary, the live validation runner now emits `live-workflow-validation-summary.json` and `artifact-manifest.json` under the configured artifact directory. The JSON summary is the preferred machine-readable contract for CI promotion rules because it records the validation status, detail, requested seed and Playwright modes, resolved endpoint URLs, and expected artifact paths. The artifact manifest records every generated file with relative path, type, and size so a downstream job can archive evidence without scraping the console log.

| Artifact | Purpose | Required for config-only gate | Required for full live gate |
|---|---|---:|---:|
| `live-workflow-validation-summary.md` | Human-readable gate result and artifact index. | Yes | Yes |
| `live-workflow-validation-summary.json` | Machine-readable status, detail, URL, and artifact-presence contract. | Yes | Yes |
| `artifact-manifest.json` | Durable inventory of files generated beneath the artifact root. | Yes | Yes |
| `docker-compose.live.resolved.yml` | Resolved compose configuration used by the gate. | Yes | Yes |
| `endpoint-probes.tsv` | Frontend and backend endpoint status codes. | No | Yes |
| `redacted-environment-metadata.json` | Validation mode, release SHA, live URLs, mock-disabled flags, and configured remote service names without secret values. | Yes | Yes |
| `seed-report.json` | Strict deterministic seed contract and backend preflight details. | Only when seed is requested | Required when seed is requested |
| `playwright/html`, `playwright/junit.xml`, and trace ZIP files | Browser validation evidence. | Only when Playwright is requested | Required when Playwright is requested |

The deterministic seed runner now performs a backend contract preflight before mutating data. Required probes include `/health`, the account read route, and the analysis case list route. Optional probes, such as tenant settings discovery, are recorded in the seed report but do not independently block seeding unless the strict seed report later records a required seed area as missing or blocked. This preserves the fail-closed rule: a full live validation cannot be promoted as **PASS** from partial seed data or missing browser artifacts.

For an already deployed Bunnyshell or equivalent live stack, use the runner's remote mode instead of local Docker Compose container inspection. The remote mode requires `PLAYWRIGHT_LIVE_FRONTEND_URL`, `PLAYWRIGHT_BACKEND_URL`, and `LIVE_SERVICE_HEALTH_URLS` entries in `name=url` format for each required service. By default, remote validation requires health probes for `layer1`, `layer2`, `layer3`, `layer4`, `layer5`, `layer6`, `postgres`, `redis`, `neo4j`, and `minio`; if the data stores are only reachable through a controlled proxy, provide those proxied health URLs rather than exposing raw store credentials or ports.

## Fourth-loop CI gate, artifact schema, and marginal-value stop criteria

The fourth autonomous sprint loop adds the last material live-readiness hardening layer before additional loops become nominal. The repository now includes a path-scoped GitHub Actions workflow at `.github/workflows/live-workflow-validation.yml`. Pull requests and pushes that modify the canonical live validation surfaces run the live validation gate in **config-only** mode by default, then validate the generated artifact schema and upload the evidence directory. Manual `workflow_dispatch` runs can request `config-only`, `no-start`, or `full` validation and can independently enable strict seeding and live Playwright execution.

The machine-readable evidence contract is enforced by `scripts/ci/validate_live_workflow_artifacts.py`. The validator checks `live-workflow-validation-summary.json`, `artifact-manifest.json`, required core artifact presence, optional endpoint probes, and optional strict seed reports. This makes the live gate auditable in CI without claiming a full live PASS unless the live stack, seed, and browser artifacts are actually produced under fail-closed live settings.

| Sprint | Implemented increment | Validation implication |
| --- | --- | --- |
| Sprint 10 | CI integration for the live workflow validation gate | Live-readiness surfaces now trigger a repository-owned validation workflow with uploaded artifacts. |
| Sprint 11 | Artifact schema validator | Generated summaries and manifests are structurally checked before reviewers rely on them. |
| Sprint 12 | Explicit stop criteria for additional sprint loops | Further loops should stop unless they remove a live-stack blocker, add a missing deterministic gate, or replace manual interpretation with enforceable automation. |

Additional autonomous sprint loops should now be considered **nominal value** unless a fresh assessment identifies one of the following material outcomes: a remaining live-stack service can be made healthy, a seed or Playwright contract can be verified against real backend behavior, CI can execute a previously manual fail-closed gate that is not already automated, or a documented blocker can be converted into deterministic validation. Pure documentation expansion, cosmetic refactoring, duplicate wrapper commands, or additional summaries over the same artifacts should not justify another loop.

Because the current automation identity may not have permission to update protected GitHub Actions workflow paths directly, the fourth loop also stores the proposed workflow definition at `docs/validation/ci-templates/live-workflow-validation.yml`. A maintainer with workflow-write permission can copy that file to `.github/workflows/live-workflow-validation.yml` to enable the same manual and path-scoped CI gate without changing the validation runner contract.

## Fifth-loop Closure: Proper-Environment Readiness, Not Live Success

The fifth live-readiness loop stops local live debugging and focuses on clean, auditable code that can run efficiently in a properly provisioned live environment. The artifact schema validator now checks generated evidence for high-confidence secret patterns by default, and the workflow-template installer gives maintainers with workflow-write permission a deterministic way to install or verify the reviewed GitHub Actions workflow without relying on an automation identity that cannot update protected workflow paths.

| Area | Current repository state | Required before claiming live PASS |
| --- | --- | --- |
| Artifact validation | `scripts/ci/validate_live_workflow_artifacts.py` validates summary and manifest contracts, optional seed and endpoint artifacts, and obvious secret material in bounded text artifacts. | Validate the evidence bundle generated by the real live run. |
| Workflow installation | `scripts/ci/install_live_workflow_template.py` can install or check the reviewed workflow template for maintainers. | A maintainer with workflow-write permission should install the template if repository CI should own this gate. |
| Runtime validation | Local debugging has stopped; repository code is prepared for proper-environment execution. | Run `scripts/ci/run_live_workflow_validation.sh --seed --playwright` in a live environment with healthy services and mocks disabled. |
| Live PASS status | Not claimed by this loop. | Only claim PASS when the stack, seed, browser login, workflow execution, and persisted-state verification all complete against live services. |

Additional loops should not continue to add nominal guardrails over the same artifacts. Future work should be triggered by evidence from a proper live environment, such as a newly observed service health failure, seed contract failure, browser workflow failure, or persistence failure.
