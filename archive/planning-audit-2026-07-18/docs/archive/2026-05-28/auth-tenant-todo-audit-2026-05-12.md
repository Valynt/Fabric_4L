# Auth/Tenant TODO-FIXME Audit (2026-05-12)

## Classification and Release Decision

| Source | Pending Item | Ownership Domain | Release-safe outcome | Evidence |
|---|---|---|---|---|
| `docs/operations/tenant-management-phase-2-provisioning.md` | Webhook idempotency follow-up for `X-Webhook-ID` persistence verification. | **Identity** (Layer 4 tenant provisioning + tenant onboarding controls). | **production-readiness gate exception** under **SEC-4271** (Owner: Platform Identity, Expiry: 2026-10-31). In-memory dedupe currently exists; durable dedupe store is deferred and must be closed before enabling high-availability multi-replica webhook processing. | Runtime webhook route currently deduplicates with process-local cache only. |
| `docs/gate-alignment/implementation-plan-phases-1-3.md` | Redis-backed audit ledger chain-head persistence (`GET`/`SET`) placeholders. | **Audit ledger persistence** (shared audit ledger chain integrity). | **implemented now with tests** (closed as implemented). Redis `GET` + compare-and-set `SET` are implemented in `LedgerCommitHandler` and exercised by ledger tests. | `packages/shared/src/value_fabric/shared/audit/ledger.py`, `tests/shared/audit/test_ledger_chain.py`. |
| `docs/gate-alignment/implementation-plan-phases-1-3.md` | Retrieval-time ACL enforcement gap in phase 3.2 narrative. | **Retrieval-time ACL** (Layer 4 memory retrieval authorization boundary). | **production-readiness gate exception** under **SEC-4318** (Owner: Layer 4 Agents, Expiry: 2027-03-31). Gate exception requires compensating controls: tenant-partitioned retrieval only, audit tracing on retrieval, and explicit release note that per-document ACL enforcement is not yet active. | Gap remains documented as future phase work in implementation plan narrative. |

## Production-Readiness Gate Exceptions (Recorded)

| Exception ID | Scope | Risk owner | Approved on | Expiry | Compensating controls |
|---|---|---|---|---|---|
| SEC-4271 | Webhook idempotency persistence for `X-Webhook-ID` | Platform Identity | 2026-05-12 | 2026-10-31 | Signature verification, timestamp replay window, tenant existence verification, process-local dedupe cache. |
| SEC-4318 | Retrieval-time ACL enforcement in memory gateway phase 3.2 | Layer 4 Agents | 2026-05-12 | 2027-03-31 | Tenant-partitioned retrieval scope, audit event emission with chain linkage, security review required before ACL gate closure. |

## TODO/FIXME Security Marker Validation

Validated on 2026-05-12:

- `python scripts/ci/prod_stub_scan.py` passed with no unresolved security-critical auth/tenant TODO/FIXME markers in release-scoped runtime paths.
- `python scripts/ci/python_contract_lint.py --changed-only` reported zero findings for changed files.

## Notes

- Sweep scope: `docs/governance/`, `docs/operations/`, `docs/gate-alignment/`, `docs/launch/`, `docs/audit/`, and `config/production-readiness/`.
- This audit intentionally distinguishes implementation-complete items from explicitly time-bounded gate exceptions to keep production status truthful.
