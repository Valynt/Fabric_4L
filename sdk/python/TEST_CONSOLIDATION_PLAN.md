# Python SDK Test Consolidation Record

## Scope and branch

- Branch: `codex/sdk-test-consolidation`
- Base: `origin/main` at `f0800e4c1c60b72645aa9303b3c073d94135c8a9`
- Allowed writes: `sdk/python/tests/**` and this file only.
- Production SDK, generated clients, workflows, manifests, lockfiles, dependencies,
  security, authentication, tenancy, and infrastructure are out of scope.
- HTTP tests use `httpx.MockTransport`; no test performs network I/O.

## Reproduced starting state

Command:

```bash
PYTHONPATH=src /tmp/fabric4l-sdk-test-venv/bin/python -m pytest tests/test_client_contracts.py -q
```

Result: **8 collected, 8 failed**. The failures occurred as four equivalent
sync/async pairs:

1. The test required query parameter `active_only`; the public SDK method and
   CLI expose and send `enabled_only`.
2. The test supplied a paginated active-workflow envelope; the public SDK
   method consumes a bare list of `Workflow` objects.
3. The test supplied route fields `id` and `progress`; the public SDK model
   requires `workflow_instance_id` and `progress_percentage`.
4. The test prohibited `tenant_id` and `user_id` in workflow execution; both
   arguments are required by the public SDK signature and shown in its README.

These were unsupported test assumptions in this test-only mission. They were
replaced with assertions for the SDK's current documented public behavior.
The cross-layer differences remain production contract drift and were not
silently "fixed" in tests or production code.

## Public client surface inventory

All HTTP operations have synchronous and asynchronous forms.

| Domain | Sync / async methods | HTTP contract currently implemented | Consolidated evidence |
|---|---|---|---|
| Tenants | `list_tenants` / `alist_tenants`; `get_tenant` / `aget_tenant` | `GET /v1/tenants`; `GET /v1/tenants/{id}` | Existing list tests plus consolidated paired get test |
| Users | `list_users` / `alist_users`; `invite_user` / `ainvite_user` | `GET /v1/users`; `POST /v1/users/invite` | Existing sync and async tests |
| API keys | `list_api_keys` / `alist_api_keys`; `create_api_key` / `acreate_api_key` | `GET /v1/api-keys?enabled_only=`; `POST /v1/api-keys` | Paired request/auth/model test plus existing create tests |
| Workflows | `list_workflows` / `alist_workflows`; `list_active_workflows` / `alist_active_workflows`; `execute_workflow` / `aexecute_workflow`; `get_workflow` / `aget_workflow` | `GET /v1/workflows/types`; `GET /v1/workflows/active`; `POST /v1/workflows`; `GET /v1/workflows/{id}` | Paired active, execute, and get contract tests plus existing list tests |
| Models | `list_models` / `alist_models`; `promote_model` / `apromote_model` | `GET /v1/models`; `POST /v1/models/{id}/promote` | Paired list test plus existing promote tests |
| Feature flags | `list_feature_flags` / `alist_feature_flags`; `set_feature_flag` / `aset_feature_flag` | `GET /v1/feature-flags`; `PUT /v1/feature-flags/{key}` | Paired set test plus existing list tests |
| Health | `health` / `ahealth` | `GET /health` | Paired request/model test |
| Lifecycle | `close` / `aclose`; sync and async context managers | Close the corresponding `httpx` client | Existing SDK lifecycle behavior retained |

The consolidated error matrix covers sync and async status handling for 400,
401, 403, 404, 409, 422, 429, 500, and 503; response context; retry-after;
credential non-disclosure; and transport connection failures.

## Current open SDK PR inventory

Queried with `gh pr list` from `bmsull560/Fabric_4L`. All listed PRs are authored
by `bmsull560`, target `main`, and were compared by changed files and head SHA.
No overlapping PR was closed.

| PR | Head SHA | Files | Disposition / unique coverage |
|---|---|---|---|
| #1175 | `b6f6b847a73d6aaa695645146af2ca37b7ef57fe` | `sdk/python/tests/test_client.py` | Superseded locally by paired `list_models` / `alist_models` request, query, and model assertions |
| #1173 | `dc076aedd582c8ae4b917c5eccc0cddb21eb597a` | `sdk/python/tests/test_client.py` | Superseded locally by paired `get_workflow` / `aget_workflow` assertions |
| #1169 | `f8a1d9525fe968ed50e2fc8939943c02c78808c6` | workflow, lockfile, SDK auth source | Excluded: production authentication and forbidden workflow/lockfile scope; no test-only unique coverage |
| #1168 | `42282203eb5b7339a766bddace2c115dd8ab06e0` | `sdk/python/tests/test_client.py` | Superseded locally by paired `health` / `ahealth` request and model assertions |
| #1166 | `95feb0ad02e87732218485ad86a03be468b7a268` | `sdk/python/tests/test_client.py` | Existing suite already covers async listing; paired feature-flag mutation coverage was added |
| #1164 | `de1e4bea231318abdb18f47696a499423ec5efc4` | `sdk/python/tests/test_client.py` | Expanded locally into a paired nine-status error matrix plus connection and secret-safety assertions |
| #1153 | `ecc658be5219396c8e9d0cddc8c7287d493f681a` | `sdk/python/tests/test_client.py` | Superseded locally by paired `get_tenant` / `aget_tenant` request and model assertions |
| #1151 | `ab98c350f8725e552173a5c3c42706ddf2afcc15` | `sdk/python/tests/test_client.py` | Superseded locally by paired set/aset feature-flag verb, path, body, and model assertions |

## Known production-contract drift left unchanged

- Layer 4 API-key routes use `active_only`; the public SDK exposes
  `enabled_only`.
- Canonical active-workflow route responses use a page envelope and route
  schemas use `id` / `progress`; the public SDK consumes a list with
  `workflow_instance_id` / `progress_percentage`.
- Workflow route documentation derives caller identity from authenticated
  context, while the SDK's documented execution API requires and serializes
  caller-provided tenant/user identifiers.
- Specialized 400/401/404/429 exceptions retain response bodies but do not
  expose status codes; generic `APIError` does.
- Successful malformed JSON currently escapes as the decoder exception rather
  than an SDK-specific error.

These are product decisions/defects requiring a separately authorized SDK
source change and coordinated contract review. They are not hidden by false
canonical assertions in this consolidation.

## Validation record

- Focused contract suite: **36 collected, 36 passed** in 1.67s.
- Complete SDK suite: **138 collected; 136 passed, 2 skipped, 2 warnings** in
  4.00s. Both warnings are existing Pydantic serializer warnings in generated
  Layer 3 search-client tests.
- Complete suite with coverage: **136 passed, 2 skipped, 2 warnings** in 6.05s;
  total package coverage **29%**, hand-written `client.py` coverage **86%**.
- Ruff check: passed for `tests/test_client_contracts.py`.
- Ruff format check: passed for `tests/test_client_contracts.py`.
- Non-writing compile validation: **39 Python files compiled**.
- `git diff --check`: passed.
- Scope audit: exactly `sdk/python/tests/test_client_contracts.py` and this file.
- Final `git fetch origin main`: branch base and `origin/main` both remain
  `f0800e4c1c60b72645aa9303b3c073d94135c8a9`.
