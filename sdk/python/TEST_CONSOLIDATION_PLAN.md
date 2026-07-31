# Python SDK Test Consolidation and Certification Record

## Scope, isolation, and baseline

- Branch: `codex/sdk-test-consolidation`
- Base: `origin/main` at `f0800e4c1c60b72645aa9303b3c073d94135c8a9`
- Worktree: `.tmp/sdk-test-consolidation`, separate from concurrent work.
- Initial state: tracked worktree clean; the two user-owned untracked artifacts
  `TEST_CONSOLIDATION_PLAN.md` and `tests/test_client_contracts.py` were
  preserved and completed.
- Allowed writes: `sdk/python/tests/**` and this SDK test document only.
- Owners: `/sdk/python/` is assigned to `@value-fabric/backend-leads` and
  `@value-fabric/architects` in `.github/CODEOWNERS`; historical source/test
  commits are primarily authored by `bmsull560`.
- Supported SDK Python: `>=3.10`; validation environment: CPython 3.12.3.
- Package structure: hand-written `valuefabric` client/auth/models/errors/CLI,
  generated L3/L4 clients, `valuepact`, and one shared `tests/` suite.
- Canonical local command: `cd sdk/python && python -m pytest`; available
  validation also includes Ruff, mypy, compile checks, and pytest-cov.

Pre-consolidation committed suite: **102 collected, 100 passed, 2 skipped,
0 xfailed, 2 warnings** in 2.68s. Adding the preserved draft contract test
produced **110 collected, 100 passed, 8 failed, 2 skipped**. Its measured
pre-fix coverage was 28% overall and 74% for `client.py`.

The editor/sandbox helper could not initialize because Bubblewrap failed with
`bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Approved shell
commands and exact Python heredoc writes worked, so this was not a delivery
blocker. No dependency was missing or added.

## Reproduced eight failures and disposition

Command:

```bash
PYTHONPATH=src /tmp/fabric4l-sdk-test-venv/bin/python -m pytest tests/test_client_contracts.py -q
```

Result: **8 collected, 8 failed**, as four sync/async pairs:

1. Test required `active_only`; the public SDK and CLI expose/send
   `enabled_only`.
2. Test supplied a paginated active-workflow envelope; the public SDK consumes
   a bare list.
3. Test supplied `id` / `progress`; the public SDK model requires
   `workflow_instance_id` / `progress_percentage`.
4. Test prohibited workflow `tenant_id` / `user_id`; both are required by the
   public SDK signature and README example.

These unsupported assumptions were rewritten to certify the current public SDK
without changing production code. The cross-layer differences are retained as
explicit product-contract drift below.

## Complete public-method coverage matrix

`P` means a deterministic positive request/response test. `N(shared)` means the
common sync/async transport and HTTP mapping layer is tested through `health`;
it is intentionally not duplicated for every wrapper. `E` records optional,
auth, malformed, lifecycle, or immutability coverage. All HTTP tests use
`httpx.MockTransport`, so an external request is impossible.

| Method | Mode | Endpoint / verb | Request parameters/body | Response | Positive | Negative | Edge case | Remaining method gap | Open PR |
|---|---|---|---|---|---|---|---|---|---|
| `list_tenants` | sync | `GET /v1/tenants` | status, limit, offset query | `list[Tenant]` | P | N(shared) | non-default pagination | none | — |
| `alist_tenants` | async | same | same | same | P | N(shared) | parity | none | — |
| `get_tenant` | sync | `GET /v1/tenants/{id}` | path id | `Tenant` | P | N(shared) | typed UUID model | none | #1153 |
| `aget_tenant` | async | same | same | same | P | N(shared) | parity | none | #1153 |
| `list_users` | sync | `GET /v1/users` | limit, offset query | `list[User]` | P | N(shared) | non-default pagination | none | — |
| `alist_users` | async | same | same | same | P | N(shared) | parity | none | — |
| `invite_user` | sync | `POST /v1/users/invite` | email, role, display name | `User` | P | N(shared) | optional display name | none | — |
| `ainvite_user` | async | same | same | same | P | N(shared) | parity | none | — |
| `list_api_keys` | sync | `GET /v1/api-keys` | `enabled_only` query | `list[APIKey]` | P | N(shared) | API-key auth header | route-name drift | — |
| `alist_api_keys` | async | same | same | same | P | N(shared) | parity/auth | route-name drift | — |
| `create_api_key` | sync | `POST /v1/api-keys` | name, role, expiry, rate limit | `APIKeyCreateResult` | P | N(shared) | optional fields | none | — |
| `acreate_api_key` | async | same | same | same | P | N(shared) | parity | none | — |
| `list_workflows` | sync | `GET /v1/workflows/types` | none | `list[WorkflowTypeInfo]` envelope | P | N(shared) | envelope mapping | none | — |
| `alist_workflows` | async | same | same | same | P | N(shared) | parity | none | — |
| `list_active_workflows` | sync | `GET /v1/workflows/active` | none | `list[Workflow]` | P | N(shared) | list mapping | canonical envelope drift | — |
| `alist_active_workflows` | async | same | same | same | P | N(shared) | parity | canonical envelope drift | — |
| `execute_workflow` | sync | `POST /v1/workflows` | type, tenant, user, inputs, priority, id | `dict` | P | N(shared) | optional id/input immutability | identity-contract drift | — |
| `aexecute_workflow` | async | same | same | same | P | N(shared) | parity/immutability | identity-contract drift | — |
| `get_workflow` | sync | `GET /v1/workflows/{id}` | path id | `Workflow` | P | N(shared) | full field mapping | route-field drift | #1173 |
| `aget_workflow` | async | same | same | same | P | N(shared) | parity | route-field drift | #1173 |
| `list_models` | sync | `GET /v1/models` | optional stage query | `list[ModelVersion]` | P | N(shared) | stage filter | none | #1175 |
| `alist_models` | async | same | same | same | P | N(shared) | parity | none | #1175 |
| `promote_model` | sync | `POST /v1/models/{id}/promote` | stage, optional reason | `ModelVersion` | P | N(shared) | reason | none | — |
| `apromote_model` | async | same | same | same | P | N(shared) | parity | none | — |
| `list_feature_flags` | sync | `GET /v1/feature-flags` | limit, offset query | `list[FeatureFlag]` | P | N(shared) | pagination | none | #1166 |
| `alist_feature_flags` | async | same | same | same | P | N(shared) | parity | none | #1166 |
| `set_feature_flag` | sync | `PUT /v1/feature-flags/{key}` | enabled, rollout, description | `FeatureFlag` | P | N(shared) | optional description | none | #1151 |
| `aset_feature_flag` | async | same | same | same | P | N(shared) | parity | none | #1151 |
| `health` | sync | `GET /health` | none | `HealthResponse` | P | full N | API key/JWT, malformed JSON/model, timeout | malformed JSON SDK mapping | #1168/#1164 |
| `ahealth` | async | same | same | same | P | full N | parity | malformed JSON SDK mapping | #1168/#1164 |
| `close` / context | sync | lifecycle | none | client closed | P | — | context exit | none | — |
| `aclose` / context | async | lifecycle | none | client closed | P | — | async context exit | none | — |

Configuration certification covers valid profiles, scalar/list parsing,
unknown-value fallback, invalid table structure, malformed lines, missing
files/fields, explicit-profile precedence, safe `ConfigurationError`, and CLI
exit behavior. Environment-variable precedence is not implemented by this SDK,
so no behavior was invented.

## Error certification

Both sync and async paths cover connection refusal, read timeout, malformed
JSON, malformed Pydantic models, and HTTP 400, 401, 403, 404, 409, 422, 429,
500, and 503. Assertions cover SDK exception type, safe response body,
`retry-after`, generic status code, and credential non-disclosure. Specialized
400/401/404/429 exceptions do not expose status codes; this is recorded as a
product gap rather than asserted falsely.

## Open SDK PR dispositions

Current PR state was refreshed through `gh`; all entries are open, authored by
`bmsull560`, and target `main`. Each diff/file list was inspected. No PR was
closed, rebased, modified, or merged.

| PR / head SHA | Files changed | Missing on main? | Equivalent here? | Classification | Recommended action |
|---|---|---|---|---|---|
| #1175 `b6f6b847a73d6aaa695645146af2ca37b7ef57fe` | `tests/test_client.py` | async model request assertions | yes, stronger paired test | valid but duplicated | close only after #1187 review/merge |
| #1173 `dc076aedd582c8ae4b917c5eccc0cddb21eb597a` | `tests/test_client.py` | async workflow retrieval | yes, stronger paired test | valid but duplicated | close only after #1187 review/merge |
| #1169 `f8a1d9525fe968ed50e2fc8939943c02c78808c6` | workflow, web lockfile, SDK auth source | auth product feature, not test backlog | no; intentionally excluded | conflicting/out of scope | review separately; do not close from this mission |
| #1168 `42282203eb5b7339a766bddace2c115dd8ab06e0` | `tests/test_client.py` | async health assertion | yes, stronger paired/auth/error test | valid but duplicated | close only after #1187 review/merge |
| #1166 `95feb0ad02e87732218485ad86a03be468b7a268` | `tests/test_client.py` | async feature listing | yes, paired request/query/model test | valid but duplicated | close only after #1187 review/merge |
| #1164 `de1e4bea231318abdb18f47696a499423ec5efc4` | `tests/test_client.py` | broad error mapping | yes, expanded nine-status/transport matrix | valid but insufficient alone | close only after #1187 review/merge |
| #1153 `ecc658be5219396c8e9d0cddc8c7287d493f681a` | `tests/test_client.py` (large rewrite) | async tenant retrieval | yes, focused paired test | valid coverage plus conflicting churn | close only after #1187 review/merge |
| #1151 `ab98c350f8725e552173a5c3c42706ddf2afcc15` | `tests/test_client.py` | async flag mutation | yes, stronger verb/path/body/model test | valid but duplicated | close only after #1187 review/merge |

## Product defects / contract drift left unchanged

- Layer 4 API-key routes use `active_only`; the public SDK uses `enabled_only`.
- Canonical active-workflow responses use a page envelope and route schemas use
  `id` / `progress`; the SDK uses a bare list and
  `workflow_instance_id` / `progress_percentage`.
- Workflow route documentation derives identity from authenticated context;
  the documented SDK requires and serializes tenant/user arguments.
- Specialized error subclasses preserve bodies but not status codes.
- Successful malformed JSON escapes as `json.JSONDecodeError` rather than an
  SDK-specific error.
- Corrupt profile parse errors include the raw malformed line and can echo a
  secret; a strict xfail regression records this security-relevant defect.

These need separately authorized production/contract work. No SDK production
file was changed.

## Validation record

| Command | Exit | Observed result |
|---|---:|---|
| `PYTHONPATH=src .../python -m pytest tests/test_client_contracts.py tests/test_config_contracts.py -q` | 0 | 82 collected; 81 passed, 1 xfailed in 3.34s |
| `PYTHONPATH=src .../python -m pytest -q` | 0 | 184 collected; 181 passed, 2 skipped, 1 xfailed, 2 warnings in 5.94s |
| `PYTHONPATH=src .../python -m pytest --cov=valuefabric --cov-report=term-missing -q` | 0 | 181 passed, 2 skipped, 1 xfailed, 2 warnings in 7.77s; 31% total, 97% `client.py`, 93% CLI config |
| `ruff check tests/test_client_contracts.py tests/test_config_contracts.py` | 0 | all checks passed; existing pyproject deprecation warning only |
| `ruff format --check tests/test_client_contracts.py tests/test_config_contracts.py` | 0 | 2 files already formatted |
| non-writing `compile(...)` over `src/**/*.py` and `tests/**/*.py` | 0 | 40 files compiled |
| `PYTHONPATH=src .../mypy src tests` | 1 | existing strict baseline: 185 errors in 16 files; zero errors in either changed test file |
| `git diff --check` | 0 | no whitespace errors |
| `git fetch origin main` | 0 | `origin/main` remains the branch base `f0800e4c...` |

The repository exposes no separate SDK contract-lint command. `make sdk` is a
generator and was not run because generated-client writes are forbidden. The
HTTP contract assertions in the focused suite are the applicable SDK contract
lint for this test-only scope.

The two warnings are pre-existing Pydantic serializer warnings in generated L3
search tests. Strict mypy is not green on current main because generated
clients, SDK production, and legacy tests contain the recorded baseline; no
manifest or source change was made to mask it.

## Independent review

Final review proved that:

- every public method parsed from `ValueFabricClient` appears in the matrix;
- all 184 collected test node IDs are unique and exercise the public calls;
- all HTTP responders are attached through `httpx.MockTransport`;
- caller-owned workflow input remains unchanged;
- sync/async clients are closed in test cleanup;
- no unsupported canonical assumption is asserted as current SDK behavior;
- only this document and files under `sdk/python/tests/**` differ from main;
- no workflow, manifest, lockfile, generated, security, auth, tenant, container,
  CI, or infrastructure file differs.
