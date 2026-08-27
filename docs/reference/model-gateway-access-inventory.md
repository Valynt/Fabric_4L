# Model Gateway Access Inventory

> Pass 0 perimeter revalidation artifact for the "Model Gateway Access
> Rearchitecture" (Pass 0–Pass 6).
> Inventory is pinned to commit `0ce9add4d8dd724ea3b9aec68801d9cd2389c7b0`.

This document classifies **every LLM modeling + embeddings invocation path** in
the runtime (non-test, non-`.agent`, non-`archive`) across layers 2 and 4, plus
the provider-boundary enforcement tooling that ratchets them. It is the
structural baseline against which Passes 1–6 measure progress.

---

## 1. Classification legend

| Class | Meaning |
|---|---|
| **governed** | Call routes through `GovernedLLMClient` → `llm_provider.get_provider` → typed adapter; cost caps, prompt screening, auth-scoped attribution, audit events. |
| **cascade-governed** | Routes through `conversation._generate_response` tier cascade; each rung delegates to governed components, but tier *selection* is hardcoded (no policy input). |
| **legacy-allowlisted** | Uses provider SDK/hostnames directly; recorded in `scripts/ci/check_model_provider_boundaries.py::LEGACY_DIRECT_ACCESS` (7 paths, P0 baseline). |
| **ungoverned-new** | Direct provider access **not** in the allowlist that would need new entries (must not happen; ratchet blocks). |
| **untracked** | Provider-shaped routing outside the runtime roots `services/` + `packages/`, or declared-but-unread config. |

---

## 2. Governed call paths (`GovernedLLMClient` consumers)

The governed gateway is `services/layer4-agents/src/layer4_agents/services/governed_llm_client.py`.
`call()` enforces cost caps (`max_cost_per_call_usd`), `call_structured()` adds
schema/JSON handling, and `_resolve_model`/`_resolve_budget` route provider +
model. Verified consumers (12 call sites, 7 modules):

| # | Module | Line(s) | Notes |
|---|--------|---------|-------|
| 1 | `workflows/whitespace.py` | 209, 515 | Gap/needs analysis |
| 2 | `workflows/roi_calculator.py` | 778 | ROI calculator |
| 3 | `workflows/business_case.py` | 478, 1204 | Section content via prompt registry |
| 4 | `workflows/base.py` | 537 | In-memory `HarnessRun` attribution |
| 5 | `agents/signal_detection.py` | 605 | Degrades to heuristic on raise |
| 6 | `tools/generation_tools.py` | 119 | Traced/cost-governed tool |
| 7 | `services/narrative_builder_service.py` | 336 | Narrative generation |
| 8 | `services/llm_intent_classifier.py` | ~124 | Harness-aware structured calls |

All are **governed**. No direct SDK import; attribution via `HarnessRun`.

## 3. Cascade path (`conversation.py`, lines 883–1132)

The conversational cascade `_generate_response` is a **cascade-governed** path:

- Rung 1: mutation tool → governed
- Rung 2: `ConversationAgent.execute` → governed
- Rung 3: `_generate_via_c1` (Thesys/C1 proxy) → **ungoverned primary tier**
- Rung 4: heuristic response (hardcoded)

Degradation bookkeeping (`failed_tiers`, `response_tier`, `provider`,
`fallback`, `degraded`, `degradation_reason` in `generation_metadata`) exists,
and `_emit_degradation_audit` (lines 1014–1043) emits `llm_degradation_applied`
only when `degraded`. Rung 3 succeeding as a *primary* tier emits **no**
`llm_degradation_applied` event and is not governed by cost caps or host
allowlisting.

## 4. Thesys/C1 proxy (`api/routes/c1.py`)

**legacy-allowlisted** + **ungoverned**. SSE/streaming proxy to Thesys. Direct
HTTP, no `max_cost_per_call_usd`, no per-call audit for primary usage, no
tenant/run attribution on the request object, no prompt-injection screen.

- Push to governed gateway: Pass 2.
- **Out-of-scope correction:** On-disk Authorization header is
  `f"Bearer {THESYS_API_KEY}"` (verified byte-level). There is **no**
  `"******"` bug. Do not "fix" it.

## 5. Legacy-allowlisted direct paths (ratchet tracked, 7 paths)

From `scripts/ci/check_model_provider_boundaries.py` (`LEGACY_DIRECT_ACCESS`):

| Path | Provider exposure | Pass |
|------|-------------------|------|
| `services/layer2-extraction/src/layer2_extraction/shared/llm_client.py` | SDK imports | Pass 4 |
| `services/layer4-agents/src/layer4_agents/api/routes/c1.py` | Thesys host | Pass 2 |
| `services/layer4-agents/src/layer4_agents/config/settings.py` | provider validation | Pass 1 (validators) |
| `services/layer4-agents/src/layer4_agents/services/anthropic_provider.py` | SDK adapter | Pass 2 (behind gateway) |
| `services/layer4-agents/src/layer4_agents/services/conversation.py` | cascade | Pass 1 |
| `services/layer4-agents/src/layer4_agents/services/llm_provider.py` | factory | Pass 1 |
| `services/layer4-agents/src/layer4_agents/services/together_provider.py` | SDK adapter | Pass 2 |

Ratchet currently healthy: `Model-provider boundary ratchet passed (7 legacy
paths tracked)` at `0ce9add4d`. CI gate also enforces provider modules
`{openai, anthropic, together, thesys}` and hosts `api.openai.com`,
`api.anthropic.com`, `api.together.ai`, `api.thesys.dev`.

**No "unknown provider silently falls back to Together" behavior exists.** The
provider factory (`llm_provider.py` 273–285) and `Settings` validator fail
closed with `UnknownLLMProviderError` on providers outside
`SUPPORTED_LLM_PROVIDERS`.

## 6. Registry client (stub, fail-closed)

`model_registry_client.py`:
- `ModelRegistryClient.get_model()` fails closed unless
  `GATEWAY_BOOTSTRAP_MODE=true` **and** `FALLBACK_MODEL` names the approved
  bootstrap model; otherwise it raises `RegistryUnavailable` after emitting
  `model_registry_unavailable_fail_closed`.
- `_fetch_from_registry()` (line 64) is a **stub** — raises
  `RegistryUnavailable` unconditionally. No HTTP, no cache, no signature
  verification.
- Target: Pass 3 (real fetch + signed cache; fail-closed on
  expired/unsigned; TanStack/TTL telemetry on stale).

## 7. Embeddings — not yet an `EmbeddingSpace` type

- `tools/knowledge_tools.py` (lines 270–411): semantic search resolves raw
  provider/model strings for embeddings (`text-embedding-3-large` for OpenAI
  default, provider-dependent fallback). `EmbeddingSpace` type absent.
- Adapters expose `embed()` (Anthropic raises `NotImplementedError`-style for
  native embeddings with a clear message; OpenAI/Together return
  `LLMEmbeddingResponse`) — **runtime adapter interface exists** in
  `llm_adapter_interfaces.LLMEmbeddingResponse`.
- Target: Pass 5 (introduce `EmbeddingSpace` mapping + registry resolution).

## 8. Declared-but-unread config (drift)

`config/harness.runtime.yaml`:
- `degradation_policies` (lines 77–102) is **declared but never read** by any
  code. Repo-wide search excluding `.agent/`, `node_modules/`, `__pycache__`,
  `site-packages/` returns only the YAML self-reference.
- `token_budgets`, `retry`, `max_cost_per_call_usd` are consumed by
  `GovernedLLMClient`.
- `llm:` block declares per-provider models (including `embedding: null` for
  anthropic).

This is the "declare vs. enforce" drift that Pass 1 repairs: typed schema,
startup validation, cascade evaluator consuming `degradation_policies`.

## 9. Untracked (outside runtime roots, informational)

- `.agent/harness/llm.py` — dev harness provider shims (not shipped runtime).
- `packages/shared/.../secrets/reload.py` + `security/config.py` — provider
  names in secret/security config, not invocation paths.
- `services/../tests/` and `tests/` — test fixtures, excluded by ratchet.

---

## 10. Reconciliation summary

| Class | Count |
|---|---|
| Governed consumers | 12 call sites / 7 modules |
| Cascade-governed | 1 (`conversation.py`) |
| Legacy-allowlisted direct | 7 paths (exact ratchet match) |
| Ungoverned-new | 0 (ratchet enforces) |
| Registry | 1 stub client (fail-closed) |
| Embeddings | 1 raw-string path (`knowledge_tools.py`) |
| Declared-but-unread config | `degradation_policies` only |

**Allowlist reconciles exactly with the inventory**: every legacy path in the
inventory appears in `LEGACY_DIRECT_ACCESS`; the ratchet reports no
stale/extra entries. No unsupported claims remain.

---

## 11. Pass mapping (from the approved Pass 0–Pass 6 plan)

| Pass | Deliverable | Inventory anchor |
|------|-------------|------------------|
| 1 | Typed `degradation_policies` schema + startup validation + cascade evaluator + audits | §3, §8 |
| 2 | Thesys/C1 behind gateway; SSE kept; shrink allowlist by 3 | §4, §5 |
| 3 | Real `_fetch_from_registry` + signed cache | §6 |
| 4 | Layer 2 compat adapter | §5 (llm_client.py) |
| 5 | `EmbeddingSpace` + registry resolution | §7 |
| 6 | Enforcement perimeter + list-page + secrets → **migration proposal** | §5 (post-migration) |