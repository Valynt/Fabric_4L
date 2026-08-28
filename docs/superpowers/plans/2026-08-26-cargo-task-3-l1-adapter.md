# Task 3 — L1 AccountIntelligenceProvider adapter

Do not start this task until CARGO-EVAL-001 is signed and `tests/contract/test_cargo_eval_charter.py` is green.

## Goal

Land a replaceable `AccountIntelligenceProvider` port, a `FakeProvider` that passes the contract suite, and a Cargo adapter that fetches allowlisted MCP tools and persists immutable `RawSnapshot`s. Stop there.

L2 normalization to `Observation` is Task 4.

## Files

- `providers/account_intelligence/fake.py`
- `providers/account_intelligence/cargo/adapter.py`
- `providers/account_intelligence/cargo/mcp_client.py`
- `providers/account_intelligence/cargo/mapping.py`
- `tests/contract/test_cargo_l1_provider.py`
- `tests/contract/test_cargo_l1_behavior.py`

Do not put the port under `providers/cargo/provider.py`.

## Platform reuse

- Hash: `value_fabric.shared.crypto.canonical.canonical_hash`
- Idempotency: `IdempotencyService` key `{tenant_id, l1.account_intelligence.fetch, client_request_id}`, TTL 72h
- Errors: `ErrorEnvelope` / `ErrorCode`
- Kill switch: `TenantKillSwitch.check_status` — UNKNOWN is 503
- MCP: `mcp_gateway` only

L1 returns `FetchBatch` of `RawSnapshot`. FakeProvider and Cargo adapter must pass the same suite.
