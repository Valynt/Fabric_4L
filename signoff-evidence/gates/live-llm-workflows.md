# Sign-off Gate: `live_llm_workflows_mandatory`

- **Release:** v1.0.0, repo `bmsull560/Fabric_4L`, main @ `e3ace52032f8c80436e46adee4fba27402ae9f31` (2026-08-10, merge PR #1271)
- **Gate authority:** Product + Platform Architecture (`release/v1/launch-contract.yaml:80-83`)
- **Status of the decision today:** `decision: pending` — a launch blocker per `launch-contract.yaml:51-53` ("pending entries are launch blockers until a named human authority records a decision here")
- **This packet recommends; it does not decide.**

---

## 1. Decision requested (paste-able)

> **Decision for `scope_decisions.live_llm_workflows_mandatory` in `release/v1/launch-contract.yaml`:**
> For the v1.0.0 golden path (journey j02-core-value-case), live (paid) LLM calls through
> `GovernedLLMClient` are **MANDATORY / NOT MANDATORY** *(strike one)* at release-candidate
> certification. If MANDATORY, the candidate-SHA-bound j02 certification (V1-GOLDEN-001/002)
> must execute the L4 value workflow and business-case generation against a real provider, with
> `structured_ai_output_schema_valid_percent: 100`, `ai_cross_tenant_retrieval_count: 0`, and
> `ai_unauthorized_tool_action_count: 0` (`launch-contract.yaml:112-114`) measured against live
> output. Fixture-backed (`mock_llm`) evaluation remains sufficient for PR-tier CI regardless.

---

## 2. Recommendation

**MANDATORY at release-candidate certification only; fixture-backed mocks remain sufficient for PR-tier CI** — conditional on landing the staged workflow path-filter patch before certification, because the eval pipeline currently cannot be trusted to trigger or to fail honestly.

Rationale: the entire LLM safety boundary (prompt guard, output guard, schema validation, cost caps) is already built and fail-closed on main, but no recorded evidence exists that any of it has ever been exercised against a live provider. The golden path's AI-specific launch targets are measured on live output by definition; certifying with `mock_llm` certifies the mock, not the product. The cost/risk of live calls is bounded (one certification run per candidate SHA), while the cost of mocking is an unverified core value proposition at public launch.

---

## 3. Evidence

### 3.1 The decision is open and blocking

- `release/v1/launch-contract.yaml:80-83` — `live_llm_workflows_mandatory: decision: pending`, authority Product + Platform Architecture, reference V1-EVALS-001.
- `release/v1/launch-contract.yaml:51-53` — pending scope decisions are launch blockers.

### 3.2 The safety boundary exists on main and fails closed

- `packages/shared/src/value_fabric/shared/llm_safety/` (last touched @ `c7b71c1c9125b360f7166cf651afe8a5fa4e0f16`): `prompt_guard.py`, `output_guard.py`, `pii_guard.py`, `token_limits.py`, `exceptions.py`, `observability.py`.
- `services/layer4-agents/src/layer4_agents/services/governed_llm_client.py` — imports `PromptGuard` (line 29), raises typed `LLMOutputValidationError` on schema failure (lines 34-49), enforces per-call token/cost caps (`_CostCapExceeded`). Recent commits: `a915ce6d6` "enforce schema validation in call_structured (fail-closed)", `474f25e3c` "screen non-system prompt content at GovernedLLMClient.call".
- `services/layer4-agents/src/layer4_agents/services/llm_output_parser.py` (last touched @ `b51a6b95d33a8540fcebe7425ef1c692927e7a8b`); contract boundary test at `tests/contract/test_llm_output_parser_boundary.py`.
- Boundary contract test for prompt-injection wiring: `tests/security/test_prompt_injection_wiring.py`.

### 3.3 Current evaluation is mock-based; no live-LLM eval results exist

- `tests/evals/conftest.py:41-46` — `mock_llm` fixture: "Mock LLM client — prevents real API calls in unit evals."
- `tests/evals/README.md:31-36` — `make evals` uses recorded responses; `make evals-full` (real LLM calls, `@pytest.mark.slow`) is the only live path (`Makefile:595-599`).
- `evals/manifest.yaml` (committed, per V1-EVALS-001) references existing runners; `evals/datasets/`, `evals/rubrics/`, `evals/adversarial/`, `evals/baselines/` contain only `.gitkeep` — **no curated datasets, rubrics, adversarial sets, or frozen baselines yet**.
- **No evidence found** of any eval run results under `artifacts/` (searched `artifacts/**/*eval*` — zero hits).

### 3.4 The evals pipeline has a live, staged-but-uncommitted defect

- `.github/workflows/ai-evals-pipeline.yml:6-25` (last touched @ `c1f673c760d516d45da4210638ec6f4c0bd6e694`) triggers on top-level `layer4-agents/**` and `layer2-extraction/src/**` paths that **do not exist in the repo** (canonical: `services/layer4-agents/**`, `services/layer2-extraction/src/layer2_extraction/**`). PR/push-triggered evals therefore effectively never fire for canonical agent/prompt/LLM-client changes.
- Staged fix exists: `signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch` — corrects all path filters to `services/...`, adds `packages/shared/.../llm_safety/**` and `evals/**`. **However, `git status` shows this file is untracked (`??`)** — it is not committed anywhere and protects nothing yet.
- Second silent-pass defect: the workflow's golden-traces job runs `tests/evals/test_golden_traces.py` (`ai-evals-pipeline.yml:368`), which **does not exist**; on missing results the analyzer sets `passed=true` (lines 417-419), i.e. the gate reports success by default.

### 3.5 The golden path is LLM-dependent

- `release/v1/journeys/j02-core-value-case.yaml:23-25` — golden path includes "Execute the L4 value workflow" and "generate the customer-facing business case", both LLM-backed via `GovernedLLMClient`.
- AI launch targets (`launch-contract.yaml:112-114`): schema-valid output 100%, zero cross-tenant retrieval, zero unauthorized tool actions — all are properties of live model output, not of mocks.

---

## 4. Blast radius

### Option A — Live LLM mandatory at certification (recommended)

- **Cost:** paid provider calls per candidate certification run (one j02 execution plus eval suite); CI secrets surface (`OPENAI_API_KEY` via Infisical OIDC, already wired in the workflow).
- **Risk:** live-call nondeterminism can flake the gate; mitigated by the deterministic-assertion design in V1-EVALS-001 (schema/tool/tenant gates are deterministic; model-graded rubrics are semantic-only).
- **Prerequisite work pulled into the critical path:** commit `ai-evals-path-filter.patch`, create `tests/evals/test_golden_traces.py` or remove the silent-pass branch, populate `evals/baselines/` after the first live run.
- **Gain:** the three AI launch targets are actually measured; provider failure modes (rate limits, cost caps, latency, malformed output) are exercised before customers hit them.

### Option B — Mocked at launch

- **What the golden path loses:** end-to-end proof that a real model's output passes schema validation, citation presence, prompt-injection screening, and tenant isolation inside j02. The P0 core-value-case certification would attest to `MagicMock(content="mocked response")` behavior.
- **Residual risk carried into GA:** any live-provider integration defect (auth, model name, response-shape drift, cost-cap misconfiguration) is first discovered by customers; the three AI targets in `launch-contract.yaml:112-114` would be unevidenced claims, conflicting with invariant "No unsupported legal, security, availability, or compliance claims" (`launch-contract.yaml:184`).
- **What it saves:** certification cost, flakiness, and the 3.4 prerequisite work — none of which disappears post-GA; it defers, it does not remove.

---

## 5. Approval block (one signature)

By signing, the signatory records the decision for `scope_decisions.live_llm_workflows_mandatory` on behalf of Product + Platform Architecture and accepts the blast radius of the chosen option above.

```
Decision recorded (MANDATORY at certification / NOT MANDATORY): ______________________

Name:  ______________________________
Role:  ______________________________   (Product / Platform Architecture authority)
Date:  ______________________________
Signature:  __________________________

Conditions / expiry (if any): _________________________________________________
```

_This packet is a recommendation artifact. No file outside `signoff-evidence/gates/live-llm-workflows.md` was modified; nothing was committed or pushed._
