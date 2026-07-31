# Python SDK Production Remediation Record

## Scope and canonical decisions

This branch upgrades PR #1187 from a test-only consolidation into production
SDK remediation. Fabric_4L is pre-release and has no SDK consumers, so incorrect
contracts were replaced directly: no aliases, legacy field fallbacks, deprecation
layer, or migration shim was added. Contract precedence is Layer 4 server behavior,
canonical OpenAPI, SDK production code, then tests and documentation.

Canonical decisions implemented in the SDK:

- API-key listing uses `active_only` in sync/async method signatures and query
  serialization. The obsolete `enabled_only` name was removed.
- Workflow-type discovery is `list_workflow_types` / `alist_workflow_types`.
  `list_workflows` now calls `GET /v1/workflows` and returns the canonical page.
- Active workflow listing returns `WorkflowListResponse`; status models use `id`
  and `progress`; execution returns `WorkflowCreateResponse`.
- Workflow execution no longer accepts or serializes tenant/user identity. Caller
  identity belongs to authenticated server context.
- All HTTP-derived SDK errors preserve safe `status_code`, `endpoint`, and redacted
  response context. Rate-limit errors also retain `retry_after`.
- Invalid, empty, or structurally invalid successful responses raise
  `ResponseError`, never raw JSON/Pydantic errors.
- Malformed config diagnostics include only file/line/sanitized explanation. Raw
  malformed text is absent from the exception and its cause.
- Generated clients/models are reproducible through
  `scripts/generate_from_openapi.py`; generator flags now emit mypy-safe constrained
  annotations and enum defaults.

## Original eight failures

The preserved draft contract test originally reproduced eight failures as four
sync/async pairs:

1. API-key query expected canonical `active_only`, while the SDK sent
   `enabled_only`.
2. Active workflows expected a paginated envelope, while the SDK consumed a bare
   list.
3. Workflow status expected canonical `id` / `progress`, while the SDK required
   `workflow_instance_id` / `progress_percentage`.
4. Workflow execution prohibited caller tenant/user fields, while the SDK required
   and serialized them.

Those tests now assert the canonical platform contract and pass against corrected
production SDK code.

## Public surface

The corrected `ValueFabricClient` exposes 34 public sync/async/lifecycle methods:

- tenants: `list_tenants`, `alist_tenants`, `get_tenant`, `aget_tenant`
- users: `list_users`, `alist_users`, `invite_user`, `ainvite_user`
- API keys: `list_api_keys`, `alist_api_keys`, `create_api_key`,
  `acreate_api_key`
- workflows: `list_workflow_types`, `alist_workflow_types`, `list_workflows`,
  `alist_workflows`, `list_active_workflows`, `alist_active_workflows`,
  `execute_workflow`, `aexecute_workflow`, `get_workflow`, `aget_workflow`
- models: `list_models`, `alist_models`, `promote_model`, `apromote_model`
- flags: `list_feature_flags`, `alist_feature_flags`, `set_feature_flag`,
  `aset_feature_flag`
- health/lifecycle: `health`, `ahealth`, `close`, `aclose`

Contract tests cover sync/async verb, path, query/body serialization, input
immutability, API-key/JWT authentication, model parsing, HTTP status mapping,
transport failures, empty/invalid/structurally invalid 2xx responses, recursive
secret redaction, timeout behavior, and resource cleanup. Every test HTTP client is
constructed with `httpx.MockTransport`; proxy mounts and external network I/O are
not retained.

## SDK PR backlog disposition

Live GitHub state was inspected for every required PR. All are authored by
`bmsull560`, target `main`, and remain open until #1187 merges.

| PR | Head SHA | Files / unique behavior | Decision after #1187 merge |
|---|---|---|---|
| #1175 | `b6f6b847a73d6aaa695645146af2ca37b7ef57fe` | one SDK test; async model listing/stage query | close as superseded; #1187 asserts the actual query |
| #1173 | `dc076aedd582c8ae4b917c5eccc0cddb21eb597a` | one SDK test; async workflow get with obsolete fields | close as superseded by canonical `id`/`progress` coverage |
| #1169 | `f8a1d9525fe968ed50e2fc8939943c02c78808c6` | SDK OIDC callback plus unrelated workflow/lockfile churn | close with precise note: separate feature, fixed-port callback design has unresolved review/security defects and is not safe to integrate |
| #1168 | `42282203eb5b7339a766bddace2c115dd8ab06e0` | one SDK test; async health | close as superseded |
| #1166 | `95feb0ad02e87732218485ad86a03be468b7a268` | one SDK test; async flag list | close as superseded |
| #1164 | `de1e4bea231318abdb18f47696a499423ec5efc4` | one SDK test file; error mapping | close as superseded by status/context/redaction/transport matrix |
| #1153 | `ecc658be5219396c8e9d0cddc8c7287d493f681a` | one heavily reformatted SDK test; async tenant get | close as superseded without importing churn |
| #1151 | `ab98c350f8725e552173a5c3c42706ddf2afcc15` | one SDK test; async flag mutation | close as superseded |

#1169 review history specifically identifies fixed-port redirect mismatch, unsafe
callback behavior when binding fails, and unrelated evidence-workflow/lockfile
changes. Its useful product idea is not a required correctness fix and its current
implementation is not production-ready.

## Validation evidence

Current completed SDK gates:

| Command | Result |
|---|---|
| `PYTHONPATH=src .../pytest tests/test_client_contracts.py tests/test_config_contracts.py -q` | 86 passed |
| `PYTHONPATH=src .../pytest --cov=valuefabric --cov=valuepact --cov-report=term-missing -q` | 186 passed, 2 skipped; 34% total, 96% handwritten client |
| `ruff check .` | passed |
| `ruff format --check .` | passed |
| `PYTHONPATH=src .../mypy src tests` | passed: 40 files, zero issues (previously 213 current-branch errors; original report recorded about 185) |
| `python scripts/generate_from_openapi.py` + byte comparison | passed; generated tree is idempotent after repository formatting |
| `git diff --check` | passed |

The two skips are pre-existing optional live-service tests, not SDK defects or
xfails. No known remediated SDK defect remains skipped or xfailed. Repository-wide
gates are still required before commit/PR readiness.

## Remaining completion work

- Enforce `extra="forbid"` on the Layer 4 workflow create request and add hostile
  tenant/user identity tests.
- Regenerate/verify canonical Layer 4 OpenAPI after the server source change.
- Wire SDK tests/lint/mypy/generation drift into required PR and publish CI.
- Repair every live repository-owned failing gate, then run `make verify` and
  `make production-readiness-gate`.
- Commit, push, update/ready/merge #1187, close superseded PRs, and verify main.

Those repository-wide writes are currently prevented by an execution-policy
control that requires a fresh direct user approval beyond the attached objective;
no bypass has been attempted.


## Current execution checkpoint (2026-07-31)

- Inspected required files in scope: `sdk/python/TEST_CONSOLIDATION_PLAN.md`, `sdk/python/tests/test_client_contracts.py`.
- Reproduced contract tests on this branch with isolated deps:
  - `/tmp/sdk-test-consolidation-venv/bin/pytest sdk/python/tests/test_client_contracts.py -q` -> `78 passed`
  - `/tmp/sdk-test-consolidation-venv/bin/pytest sdk/python/tests -q` -> `192 passed, 2 skipped`
- Reproduced previously reported eight failures: on this branch run they no longer fail (`0 currently failing in `test_client_contracts.py`).
- Runtime public surface (non-underscore methods):
  - Sync: `close`, `create_api_key`, `execute_workflow`, `get_tenant`, `get_workflow`, `health`, `invite_user`, `list_active_workflows`, `list_api_keys`, `list_feature_flags`, `list_models`, `list_tenants`, `list_users`, `list_workflow_types`, `list_workflows`, `promote_model`, `set_feature_flag`
  - Async: `aclose`, `acreate_api_key`, `aexecute_workflow`, `aget_tenant`, `aget_workflow`, `ahealth`, `ainvite_user`, `alist_active_workflows`, `alist_api_keys`, `alist_feature_flags`, `alist_models`, `alist_tenants`, `alist_users`, `alist_workflow_types`, `alist_workflows`, `apromote_model`, `aset_feature_flag`
- Open PR overlap scan (open PRs from @bmsull560 against branch targets):
  - Fully superseded by #1187 with no unique files: #1175, #1174, #1173, #1168, #1167, #1166, #1165, #1164, #1163, #1162, #1161, #1159, #1158, #1155, #1153, #1151
  - Partially unique: #1169 (`apps/web/pnpm-lock.yaml` is still outside #1187)
- `gh pr checks 1187 --watch` shows current failures on latest run:
  - Repository Scan (Trivy fs + IaC + secrets): FAIL
  - DAST (OWASP ZAP baseline): FAIL
  - Layer 3 - Knowledge: FAIL
  - Run Contract Tests: FAIL
  - p0-e2e-gate: FAIL
- PR #1187 remains `OPEN`, state `UNSTABLE`, mergeStateStatus `UNSTABLE`, currently not merged.

