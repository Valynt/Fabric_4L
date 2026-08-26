# Cargo Evaluation Signals & Integration POC Implementation Plan

Goal: evaluate Cargo as a replaceable AccountIntelligenceProvider. Fabric owns
meaning. Cargo owns commodity observation.

## Architecture

```text
Cargo MCP (read-only)
        |
        v
L1 AccountIntelligenceProvider.fetch
        |  RawSnapshot / FetchBatch
        v
L2 ACL / normalizer
        |  Observation
        v
L3 tenant-scoped knowledge
        v
L4 ValuePacks / hypotheses   L5 review   L6 baseline vs treatment
```

L1 does not emit Observation, valueDriverTags, KPI, ROI, or Fabric confidence.
Normalization to Observation is L2, not "the L1 ACL."

## Global constraints

- Cargo is never authoritative for tenant/account identity or economic meaning.
- No Cargo types outside `providers/account_intelligence/cargo/`.
- Provenance class is L2 (`TRACEABLE` / `PARTIALLY_TRACEABLE` / `OPAQUE`).
- `valueDriverTags` empty on ingest.
- Four read-only MCP servers only. Context Agent excluded.
- Hard gates are non-compensable.
- Green slugs only (`docs/cargo/allowlist.json`).

## Task 1 — discovery (done)

`docs/cargo/signals-catalog.md`

## Task 2 — charter freeze (this PR)

- `docs/cargo/eval-charter-001.md` — draft pending signatures
- `docs/cargo/allowlist.json`
- `tests/contract/test_cargo_eval_charter.py`
- L1 type foundation only: `port.py`, `models.py`, `slugs.py`

Do not start Task 3 until Product + Platform + Security sign the charter.

## Task 3 — L1 adapter (blocked on signatures)

Files:

- `providers/account_intelligence/fake.py`
- `providers/account_intelligence/cargo/adapter.py`
- `providers/account_intelligence/cargo/mcp_client.py`
- `providers/account_intelligence/cargo/mapping.py`
- `tests/contract/test_cargo_l1_provider.py`
- `tests/contract/test_cargo_l1_behavior.py`

L1 returns FetchBatch of RawSnapshot. FakeProvider and Cargo adapter pass the
same suite. Platform hasher / idempotency / ErrorEnvelope / TenantKillSwitch only.

## Task 4 — L2 normalizer

`services/layer2-extraction/.../normalizers/cargo_normalizer.py`

Reads RawSnapshot, classifies provenance, emits Observation with empty
valueDriverTags.

## Later

L3 lineage, L4 ValuePack tagging, blinded pairs, L5/L6 scorecard, kill-switch
proof, decision record.
