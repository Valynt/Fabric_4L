# Workflow Patch Packet: `ai-evals-pipeline.yml` path-filter repair

- **Patch file:** `signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch`
- **Target file:** `.github/workflows/ai-evals-pipeline.yml`
- **Base:** `main` @ `e3ace52032f8c80436e46adee4fba27402ae9f31`
- **Issue:** #1259 (V1-AI-001), second half — the first half (fail-closed LLM output parse
  boundary) landed in PR #1268. This packet carries the workflow half, which could not be
  merged by the agent because its token lacks `.github/workflows/**` write scope.
- **Task alignment:** `release/v1/tasks/V1-EVALS-001.yaml` (manifest-first AI evaluation
  coverage; deterministic AI gates enforced in `ai-evals-pipeline.yml`).

## Apply (one command, from repo root)

```bash
git apply signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch
```

Then commit with a token that has `workflows` scope, e.g.:

```bash
git add .github/workflows/ai-evals-pipeline.yml
git commit -m "fix(ci): repair ai-evals-pipeline path filters for monorepo layout (#1259)"
```

## Defect summary (one line)

Every repo-relative path in the workflow's `paths:` filters predates the monorepo layout —
none of them exist on disk — so the AI evaluation pipeline silently never triggers on
AI-relevant changes (including the `llm_safety` boundary fixed in PR #1268), and the
in-job discovery/install steps reference the same stale paths and would fail or no-op even
when the workflow is dispatched manually.

## Defect detail (current file, line references)

### 1. Stale `paths:` filters — `.github/workflows/ai-evals-pipeline.yml:8-15` (`pull_request`) and `:18-25` (`push`)

| Current filter entry | Status on disk |
|---|---|
| `layer4-agents/skills/**` | missing `services/` prefix → `services/layer4-agents/skills/**` |
| `layer4-agents/agents/**` | does not exist → canonical is `services/layer4-agents/src/layer4_agents/agents/**` |
| `layer4-agents/prompts/**` | missing `services/` prefix → `services/layer4-agents/prompts/**` |
| `layer4-agents/src/registry/**` | missing prefix + wrong package → `services/layer4-agents/src/layer4_agents/registry/**` |
| `layer2-extraction/src/integration/model_registry_client.py` | does not exist; the model registry client lives at `services/layer4-agents/src/layer4_agents/model_registry_client.py` |
| `layer2-extraction/src/shared/llm_client.py` | missing prefix + wrong package → `services/layer2-extraction/src/layer2_extraction/shared/llm_client.py` |
| `tests/evals/**` | **correct** — the only entry that matches anything |

Because GitHub path filters match against real repo paths, six of seven entries can never
match. The pipeline today fires only on `tests/evals/**` changes or `workflow_dispatch`.

Missing AI-relevant paths that must trigger the gate:

- `packages/shared/src/value_fabric/shared/llm_safety/**` — the fail-closed parse boundary
  merged in PR #1268 changed exactly this tree and the eval gate did **not** run.
- `evals/**` — root eval manifest/datasets/rubrics/adversarial/baselines per V1-EVALS-001
  (`evals/manifest.yaml` exists on main).
- `services/layer4-agents/src/layer4_agents/skills/**` — runtime skill package.
- `.github/workflows/ai-evals-pipeline.yml` — self-reference so edits to this pipeline are
  themselves gated.

### 2. Stale discovery greps — `:77-79`

`discover-skills` greps the diff for `^layer4-agents/skills/.*\.md$`,
`^layer4-agents/agents/.*\.md$`, `^layer4-agents/prompts/.*\.md$`. With the same stale
prefixes, `should_run` would stay `false` even after fixing the workflow-level filters,
and `setup-evals` (which is gated on `should_run_evals == 'true'` at `:112`) would be
skipped. Prefixes corrected; `agents` now points at the canonical
`services/layer4-agents/src/layer4_agents/agents/`.

### 3. Stale working-directory references (same defect family, required for the repaired trigger to run green)

- `cd layer4-agents` → `cd services/layer4-agents` at `:138`, `:203`, `:301`, `:347`.
- `sys.path.insert(0, 'layer4-agents/src')` → `'services/layer4-agents/src'` at `:226`.

Without these, the first real trigger of the repaired pipeline fails at the install step —
the gate would go from silently-skipped to always-red. Same one-line stale-prefix defect,
fixed in the same patch to keep the repair atomic.

## Checked and intentionally NOT changed

- **`merge_group`:** no workflow in `.github/workflows/` uses `merge_group`; the repo does
  not run a merge queue. Adding it would be speculative redesign, out of scope.
- **Job-level `if:` conditions:** the fork-PR guards
  (`github.event.pull_request.head.repo.full_name == github.repository`) are security
  controls for Infisical OIDC secrets, not stale path logic — untouched.
- **Infisical `secret-path` values** (`/layer2-extraction`, `/layer4-agents`): these are
  Infisical paths, not repo paths — untouched.
- **Prompt grep extension** (`.*\.md$`): prompt dirs also contain `output_schema.json`;
  kept `.md`-only to preserve the original discovery semantics (minimal diff). Follow-up
  candidate, not a blocker: schema changes already trigger the workflow-level filter.

## Expected gate behavior change

| Scenario | Before patch | After patch |
|---|---|---|
| PR touches `packages/shared/.../llm_safety/**` (e.g. PR #1268) | pipeline does not trigger | triggers; evals gate the PR |
| PR touches `services/layer4-agents/{skills,prompts}/**` | pipeline does not trigger | triggers; `discover-skills` finds changes, evals run |
| PR touches `evals/**` (V1-EVALS-001 manifest/datasets) | pipeline does not trigger | triggers |
| PR touches only `tests/evals/**` | triggers (only working entry) | triggers (unchanged) |
| PR touches unrelated paths (e.g. `apps/web/**`) | does not trigger | does not trigger (unchanged) |
| Manual `workflow_dispatch` | runs, but `cd layer4-agents` fails at install | runs; install/discovery resolve real paths |

The deployment-gate semantics (85% pass threshold, `EVAL_THRESHOLD`, blocking PR check
`AI Evaluation Pipeline`) are unchanged — this patch only repairs *when* and *whether* the
gate executes.

## Verification performed

```bash
# Patch generated from scratch a/b copies via git diff --no-index; YAML of the
# repaired file validated with PyYAML (safe_load OK).
git apply --check signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch
# → exit 0 (APPLY-CHECK: OK) against main @ e3ace52032f8c80436e46adee4fba27402ae9f31

# Round-trip: applied the patch to a clean copy of the workflow in /tmp and diffed
# against the YAML-validated repaired copy → identical.

git apply --stat signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch
# → .github/workflows/ai-evals-pipeline.yml | 48 +++++++++++++++-------------
#   1 file changed, 28 insertions(+), 20 deletions(-)
```

No other files are touched by the patch. Nothing was committed or pushed by the agent.
