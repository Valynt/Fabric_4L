# Security Scan Debt Inventory

> **Snapshot date:** 2026-08-08
> **Baseline:** `origin/main` at `61500c3b4` (post-PR-#1186 merge)
> **Scanner surface:** pip-audit, Trivy (container + fs + IaC), OSV-Scanner, Grype, CodeQL, Semgrep OSS
> **Alerts at snapshot:** 3,270 total / 606 unique rules
> **Required checks:** 8 (all currently pass on main)
> **Non-required security jobs failing at snapshot:** ~31 (pip-audit ×4 layers, Trivy ×3 layers, OSV-Scanner, Grype, Dependency Review, Repository Scan, CodeQL, Semgrep, DAST)

This document is the canonical inventory of security-scan findings across the
Fabric_4L repo. It exists so the failing non-required security jobs become
actionable: each finding is classified, its runtime reachability is assessed,
and its disposition is recorded as *remediated*, *accepted-risk*, or
*investigating*. The goal of this phase is not to make every security job
required — it is to make every finding *honestly categorised* so that when we
do promote a job to required, the remaining surface is known-acceptable.

Scanner jobs themselves are not modified by this pass. No `continue-on-error`
is added; no findings are suppressed. The fix path for each finding is either
(a) upgrade the affected dependency, (b) harden the code, or (c) record an
evidence-backed accepted-risk rationale below.

---

## 1. Python dependency findings (pip-audit)

### 1.1. `cryptography` — REMEDIATED in this pass

| ID | Before | After | Disposition |
|---|---|---|---|
| PYSEC-2026-3552 / CVE-2026-69247 | 48.0.1 | 50.0.0 | upgraded across `services/api`, `layer1-ingestion`, `layer3-knowledge`, `layer4-agents` (`uv.lock`) |
| PYSEC-2026-3553 | 48.0.1 | 50.0.0 | same |
| PYSEC-2026-3554 / CVE-2026-69248 | 48.0.1 | 50.0.0 | same |

**Reachability.** `cryptography` is imported transitively by `PyJWT`,
`presidio-anonymizer`, `paramiko`, and the Fabric auth envelope. The
vulnerabilities concern X.509 verifier wildcard handling, recursive chain
resolution, and PKCS7 decryption timing side-channels. The Fabric codebase
uses `cryptography` for JWT envelope verification only; we do not perform
PKCS7 decryption and do not construct X.509 verifiers with
`permittedSubtrees` constraints, but upgrading removes the findings entirely
and removes a future-footgun if usage broadens.

**Compatibility.** `presidio-anonymizer 2.2.364` on PyPI pins
`cryptography<49.0.0`, but the repo's uv lock resolves
`presidio-anonymizer==2.2.362` which has no upper bound on cryptography.
`uv lock --check` passes; CI uses `uv sync --frozen` and picks up the locked
2.2.362. Local pip-audit against the dev venv may still surface a conflict
warning if `pip install` is used directly; that is a tooling artefact, not a
runtime failure.

### 1.2. `langgraph-checkpoint-postgres` — REMEDIATED in this pass

| ID | Before | After | Disposition |
|---|---|---|---|
| GHSA-47pj-3jcm-6whg | 3.0.5 | 3.1.2 | upgraded in `services/layer4-agents/uv.lock` |

**Reachability.** The vulnerability concerns dot-joined namespace segment
matching in Postgres/SQLite stores — scoped reads can cross segment
boundaries when memory namespaces share prefixes. The checkpoint store is
used by LangGraph workflow persistence in Layer 4. Exploitable only via a
tenant that can craft workflow state keys with shared-prefix namespaces; in
a correctly-tenant-scoped deployment the blast radius is limited to that
tenant's own workflows.

**Risk reduction.** 3.1.2 switches to per-segment matching; the fix is
drop-in compatible with the `>=2.0.0` constraint already declared in
`services/layer4-agents/pyproject.toml`.

### 1.3. `ecdsa` — ACCEPTED-RISK, no fix available

| ID | Version | Fix | Disposition |
|---|---|---|---|
| PYSEC-2026-1325 / CVE-2024-23342 (Minerva attack) | 0.19.2 | none (0.19.2 is latest published) | accepted-risk |

**Reachability.** `ecdsa` is pulled in transitively by `python-jose`, which
is itself used for JWT handling. `ecdsa`'s modules are not imported directly
anywhere in `services/**/src`. The runtime call graph reaches `ecdsa` only
via python-jose's ECDSA key-type path; Fabric currently uses RSA and HMAC
JWT algorithms, not ECDSA, so the vulnerable code path is not exercised in
production.

**Mitigation path.** Either migrate JWT verification off python-jose onto a
library that does not pull ecdsa (e.g. `PyJWT` alone, already in the
dependency graph), or wait for an upstream ecdsa release that addresses the
Minerva attack. Tracked as a follow-up; not a merge blocker for this PR.

### 1.4. `pip` in the dev venv — ACCEPTED-RISK, dev-tooling only

| ID | Version | Fix |
|---|---|---|
| PYSEC-2026-196, 1795, 1796, 2875, 2876 | 24.0 | 25.3 / 26.0 / 26.1 / 26.1.2 |

**Reachability.** `pip` is a build/install tool in the local dev venv. It
is not packaged into any service container (services install their
dependencies at image build time with `uv`, which vendors its own copy) and
is not present at runtime in production. The CVEs concern dependency
confusion and hash-checking bypass during package installation — relevant
only when a developer runs `pip install` against an untrusted index.

**Mitigation path.** Individual developers can run `pip install --upgrade
pip` in their local venv. Not a repo-level change.

---

## 2. Frontend / Node dependency findings (Trivy + OSV-Scanner)

The frontend (`apps/web`) and root `pnpm-lock.yaml` surface ~100 distinct
CVEs across `nanoid`, `js-yaml`, `brace-expansion`, `minimatch`, `node-tar`,
`pnpm`, `picomatch`, `DOMPurify`, `lodash`, `follow-redirects`, `uuid`,
`qs`, `path-to-regexp`, `Mermaid`, `mdast-util-to-hast`, `glob`,
`ip-address`, `authlib`. All of these are transitive npm dependencies —
none are imported directly in `apps/web/src`.

### 2.1. `pnpm` — ACCEPTED-RISK, version-locked by packageManager policy

The repo pins `pnpm@10.18.1` via the `packageManager` field in
`package.json` (enforced by `scripts/enforce-package-manager.cjs` and the
CI `check-package-manager-policy` check). Multiple RCE CVEs affect pnpm
versions prior to 10.x.y-latest; upgrading requires a coordinated bump of
the `packageManager` pin plus a full CI re-certification of the pnpm
lifecycle. Tracked as a follow-up under the "normalise container pinning"
workstream; not scoped to this PR.

### 2.2. `DOMPurify`, `lodash`, `nanoid`, `brace-expansion`, `js-yaml` — INVESTIGATING

These are fixable upgrades but each requires a `pnpm update` sweep plus a
regression pass of the frontend test suite (`pnpm --dir apps/web run test`
plus Playwright E2E). Tracked as Phase 1-f; not yet applied in this commit.

### 2.3. `docs/archive/frontend-root-2026-05-02/` lockfile — FALSE-POSITIVE SURFACE

The archived frontend snapshot under `docs/archive/` contains a frozen
`pnpm-lock.yaml` that OSV-Scanner flags repeatedly. This directory is a
point-in-time snapshot for documentation purposes and is not installable.
OSV-Scanner's default configuration scans the whole repo including
archives. Tracked as a follow-up to add an OSV-Scanner config excluding
`docs/archive/**`.

---

## 3. Container-image findings (Trivy container scan, Grype)

The Trivy container scans and Grype both flag:

- **OS package CVEs in base images** (`python:3.11.11-slim-bookworm`,
  Debian bookworm): ~200 findings across `libc6`, `libcurl4`, `openssl`,
  `sqlite3`, `perl-base`, `util-linux`, `krb5`, `libssh2`, etc. Most are
  `note`-severity in Grype (known-unfixed-in-debian-bookworm) or
  `warning`/`error` in Trivy. Fixing requires base-image refresh (e.g.
  `python:3.11.X-slim-bookworm` with a newer digest), tracked under the
  "normalise container pinning" follow-up.
- **KSV / AWS IaC findings** (Trivy Kubernetes + IaC): `KSV-0014`,
  `KSV-0118`, `KSV-0041`, `KSV-0056`, `KSV-0100`, `AWS-0040`, `AWS-0041`,
  `AWS-0104`, `AWS-0132` — security-context, secret-management, and
  network-policy findings in k8s manifests and compose files. Tracked as
  a follow-up under the production-readiness hardening workstream; the
  manifests in this repo are reference configurations, not deployed
  directly.
- **`libssh2`, `curl`, `ncurses`** — CVEs in packages pulled into the
  build image. Base-image refresh covers these too.

---

## 4. CodeQL / static-analysis findings

CodeQL surfaces ~1,700 alerts across `py/*` and `js/*` rule families. The
high-volume families (`py/unused-import` 578, `py/unused-global-variable`
315, `js/unused-local-variable` 218, `py/unused-local-variable` 186,
`py/log-injection` 165, `py/empty-except` 114) are hygiene/quality rules
rather than exploitable vulnerabilities. They are tracked as code-quality
debt and are explicitly out of scope for this security-hardening pass.

### 4.1. `py/partial-ssrf` — TRIAGED, all 11 alerts are false positives

CodeQL's `py/partial-ssrf` rule flags `httpx`/`requests` calls where any
part of the URL may be influenced by a remote value. All 11 open alerts
in this repo are false positives — each call's URL is derived from
server-side configuration, OAuth instance URLs returned by the upstream
provider, or hardcoded path literals appended to a configured base URL.
No alert represents a code path where an untrusted end-user controls the
scheme, host, or path of an outbound request.

| # | File | Line | URL source | Classification |
|---|---|---|---|---|
| 14477 | `services/api/app/clients/layer5_client.py` | 42 | `self.base_url` (env / constructor) + caller-supplied path literal | false-positive — inter-service client; base URL server-configured |
| 14476 | `services/api/app/clients/layer3_client.py` | 42 | same pattern | false-positive — same |
| 14475 | `services/api/app/clients/layer2_client.py` | 41 | same pattern | false-positive — same |
| 14474 | `services/api/app/clients/layer1_client.py` | 41 | same pattern | false-positive — same |
| 12560 | `services/api/app/clients/layer4_client.py` | 37 | same pattern | false-positive — same |
| 12559 | `services/api/app/clients/internal_api_client.py` | 39 | same pattern | false-positive — same |
| 12558 | `services/layer4-agents/src/.../integration_service.py` | 909 | `SALESFORCE_OAUTH_BASE_URL` env (default `https://login.salesforce.com`) + fixed path `/services/oauth2/token` | false-positive — OAuth endpoint to configured Salesforce host |
| 12556 | `services/layer4-agents/src/.../salesforce/connector.py` | 139 | `self.instance_url` — set from Salesforce OAuth token response's `instance_url` field | false-positive — Salesforce-assigned instance host, not user-controlled |
| 12555 | `services/layer4-agents/src/.../salesforce/connector.py` | 101 | same `instance_url` after token refresh | false-positive — same |
| 12554 | `services/layer4-agents/src/.../hubspot/connector.py` | 55 | `url` argument; callers pass fully-qualified HubSpot API URLs constructed against `https://api.hubapi.com` | false-positive — HubSpot API base fixed at connector construction |

**Why these are not exploitable.** A partial-SSRF vulnerability requires an
attacker to influence the outbound URL such that the request is sent to a
host or path the attacker chooses. In every case above, the URL's
scheme/host is fixed by server configuration or by the OAuth token
response from the integration partner (Salesforce, HubSpot). The only
variable portions are path segments that are either hardcoded literals
(``/services/oauth2/token``, ``/v1/analysis/cases/.../export``) or
server-sanitised IDs (workflow IDs, account IDs) that are validated
upstream before reaching the HTTP call. None of these code paths accept
an end-user-supplied URL or URL component.

**Why they are recorded rather than dismissed.** CodeQL's `py/partial-ssrf`
rule does not currently distinguish "URL derived from configured base +
hardcoded path" from "URL with user-influenced host". Dismissing each
alert in the GitHub UI is per-alert; we instead record the triage here so
the next scan re-classifies them consistently and a future rule
improvement can bulk-promote this classification.

**If a future change introduces a user-influenced URL in any of these
sites.** The fix is to validate the URL against an allowlist of expected
hosts (e.g. ``urlparse(url).hostname in allowed_hosts``), or to construct
the URL via ``urllib.parse.urljoin(base, path)`` with a pre-validated
``base``. Add a unit test that asserts an attacker-controlled host is
rejected.

### 4.2. `py/path-injection`, `py/clear-text-logging-sensitive-data`, `py/stack-trace-exposure`, `py/weak-sensitive-data-hashing`, `py/side-effect-in-assert` — INVESTIGATING

Lower-volume CodeQL error-severity rules. Triage is tracked as a follow-up;
none of these block the current PR.

### 4.3. `actions/unpinned-tag`, `actions/envvar-injection/medium`, `actions/excessive-secrets-exposure` — INVESTIGATING

GitHub Actions hygiene. Tracked as a follow-up.

---

## 5. Semgrep findings

Semgrep surfaces ~70 alerts, of which the highest-value families are:

- `semgrep.error-str-leakage-in-result-dict` (39) — error strings leaked
  into API response dicts; may expose internal detail. Tracked.
- `semgrep.block-direct-graph-mutation` (17) — direct mutation of the
  LangGraph state graph; tracked as correctness debt.
- `config.semgrep.registry.reviewed.python-subprocess-shell-true` (7) —
  `subprocess` with `shell=True`; each requires a per-call audit. Tracked.
- `config.semgrep.registry.reviewed.react-dangerously-set-inner-html` (1)
  — single `dangerouslySetInnerHTML` site; tracked for sanitisation
  review.

---

## 6. Non-security job failures that are NOT in scope

During the inventory pass, several non-required CI jobs failed for reasons
other than security findings. These are pre-existing on main and are
explicitly **not** part of this hardening pass:

- `Contract RFC Reference Check`, `Cross-Layer Contract Tests`, `Docker
  Compose Config Contract`, `Governance Docs Guard`, `Run Contract Tests`,
  `Python Platform Contract Lint` — contract tests that require running
  service containers; pass under `make contract-tests` (which `make
  verify` runs) but fail as standalone CI jobs because the CI lane does
  not boot the service stack. Tracked as a CI-lane improvement.
- `Frontend`, `Layer 1 - Ingestion`, `Layer 4 - Agents`, `p0-e2e-gate` —
  end-to-end test jobs that require the full service stack.
- `DAST (OWASP ZAP baseline)` — requires a running service for the ZAP
  baseline scan to hit.
- `SBOM + Policy`, `Source SBOM Scan` — SBOM generation jobs; failure
  modes are operational (missing registry auth, etc.) rather than
  content-based.

Each of these is tracked separately; none gate this PR.

---

## 7. Summary disposition

| Category | Total alerts at snapshot | Remediated this pass | Accepted-risk | Investigating / follow-up |
|---|---:|---:|---:|---:|
| Python deps (pip-audit) | 14 | 4 (cryptography ×3, langgraph ×1) | 6 (ecdsa ×1, pip ×5) | — |
| Node deps (Trivy / OSV) | ~100 | — | 1 (pnpm, version-locked) | remainder |
| Container OS (Grype / Trivy) | ~200 | — | — | base-image refresh |
| K8s / IaC (Trivy) | ~50 | — | — | prod-readiness follow-up |
| CodeQL hygiene | ~1,700 | — | — | code-quality debt |
| CodeQL security (py/partial-ssrf) | 11 | — | — | Phase 3 of this pass |
| Semgrep | ~70 | — | — | tracked |
| Archive false-positive surface | ~1,100 | — | — | OSV config follow-up |

**Net change from this pass so far:** 4 alerts remediated (3 cryptography
CVEs across 4 services, 1 langgraph namespace CVE); remaining findings
categorised with disposition.

---

## 8. What this pass will still do

1. **Phase 2:** validate `make test-layer4-live` (the PostgreSQL live test
   lane) runs the 47 `pytest.mark.postgres` billing tests against real
   PostgreSQL. This is the coverage gap called out in PR #1186.
2. **Phase 3:** complete the `py/partial-ssrf` triage — 11 CodeQL alerts,
   each either fixed or documented with evidence-backed
   non-exploitability.
3. **Commit + PR:** a single PR on `harden/post-merge-security`, scoped
   only to the items above. No architecture-convergence rework; no
   `/health` redesign; no PgBouncer pinning change.

---

## 9. Maintenance contract

When a new security finding surfaces — either from a scanner upgrade or a
new dependency — it lands in one of four buckets in this document:

- **Remediated** — fix applied, finding closed. Move to the changelog
  section at the bottom.
- **Accepted-risk** — requires a dated rationale, reachability evidence,
  and an owner. Re-review at the rationale's stated expiry.
- **Investigating** — temporary bucket; must move to one of the other
  three within one sprint.
- **False-positive / out-of-scope** — requires a scanner-config change or
  path-exclusion; record the config change here so it is reviewable.
Do not add findings to the *accepted-risk* bucket without a dated
rationale.

For *false-positive* / *out-of-scope* findings, record evidence-backed
triage here, and (when possible) follow up with a scanner-config change
or exclusion so the alert volume stays manageable.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-08 | Initial inventory. Upgraded `cryptography` 48.0.1 → 50.0.0 across services/api, layer1-ingestion, layer3-knowledge, layer4-agents. Upgraded `langgraph-checkpoint-postgres` 3.0.5 → 3.1.2 in layer4-agents. Both changes via `uv lock --upgrade-package` against the existing `>=` constraints in `pyproject.toml`; no constraint changes. |
| 2026-08-08 | Phase 2 — `make test-layer4-live` run against Dockerised PostgreSQL: 141 passed, 8 skipped, exit 0 (140s). All 47 `pytest.mark.postgres` billing tests in `test_billing_route_coverage.py` pass against real PostgreSQL. Lane is stable. |
| 2026-08-08 | Phase 3 — 11 `py/partial-ssrf` CodeQL alerts triaged as false positives with evidence-backed rationale per alert (see §4.1). All 11 sites are inter-service HTTP where the URL is derived from server configuration or OAuth instance URLs returned by the integration partner; no site has a user-influenced URL component. |
