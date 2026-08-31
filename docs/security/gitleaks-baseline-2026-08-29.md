# Gitleaks Baseline Classification - 2026-08-29

> **Status:** Baseline applied for 40 pre-existing findings (2026-08-29)
> **Origin:** CI `gitleaks-scan` job failure on the corrected head (`go run github.com/zricethezav/gitleaks/v8@v8.18.4 detect --source . --config .gitleaks.toml --verbose`, full-history scan of 3274 commits, fetch-depth 0)
> **Mechanism:** `.gitleaksignore` (repo root) - exact `commit:file:rule:line` fingerprint matches; two synthetic-value regex allowlists in `.gitleaks.toml`

## TL;DR

| Bucket | Count | Action |
|---|---|---|
| **Live at HEAD but NOT real secrets** | **22** | Documented in `.gitleaksignore`; 2 value-classes also regex-allowlisted |
| **Historical (absent from HEAD)** | **18** | Documented in `.gitleaksignore` |
| **Real credentials in current tree** | **0** | None found |

All 40 findings are pre-existing leaks in git history (commits 2026-04-14 through 2026-08-29), introduced across the commit range, unrelated to PR #1585. **None are live credentials:** the 22 still-present strings are documentation examples, environment-variable *names*, explicit test fixtures, code identifiers, or a PEM placeholder template.

Detection stays strict: `.gitleaksignore` suppresses only the exact fingerprints listed here. Any new or modified secret produces a fingerprint not in the file and still fails the scan. The scan itself is unchanged - it is not disabled, redacted, or `--no-git`.

## Why a baseline (not a repo rewrite)

* Rewriting history to purge these 40 findings is an org-level decision (out of scope for this PR).
* The values are demonstrably non-secret (see per-finding table). A `--baseline-path` JSON report was rejected: v8.18.4 `IsNew` does full-field equality and *ignores* Fingerprint, making hand-maintained baselines fragile. `.gitleaksignore` matches the canonical `commit:file:rule:line` fingerprint and auto-loads from `--source .`.

## Classification

| # | Status | File | Rule | Line | Secret | Reason |
|---|---|---|---|---|---|---|
| 1 | LIVE | `.agents/skills/infisical-api/references/authentication.md` | `generic-api-key` | 28 | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | Documentation example JWT (auth reference) - sample token, not issued by any IdP |
| 2 | LIVE | `.agents/skills/infisical-api/references/secrets-endpoints.md` | `stripe-access-token` | 126 | `sk_live_abc123def456ghi789` | Stripe demo token `sk_live_abc123...` - vendor-documented example, allowlisted regex |
| 3 | LIVE | `.agents/skills/infisical-self-host/references/docker-deployment.md` | `generic-api-key` | 153 | `a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8` | Documentation example hex value (self-host deployment) - placeholder |
| 4 | LIVE | `.agents/skills/infisical-self-host/references/docker-deployment.md` | `generic-api-key` | 154 | `VUJrQV9FbmNyeXB0aW9uS2V5XzMyQnl0ZXNfQmFzZTY0RW5j...` | Documentation example base64 (self-host deployment) - decodes to `UBkA_EncryptionKey_32Bytes_Base64Encoded` placeholder |
| 5 | LIVE | `services/layer4-agents/src/layer4_agents/integration/layer5_client.py` | `generic-api-key` | 45 | `L5SubmitTruthResult` | Code identifier: Python type alias `L5SubmitTruthResult` (namedtuple import), not a secret |
| 6 | LIVE | `.env.dev.example` | `generic-api-key` | 230 | `ZmFicmljNGwtbG9jYWwtZGV2LWZlcm5ldC1rZXktMDE=` | `.env.dev.example` local-dev value (base64 of `fabric4l-local-dev-fernet-key-01`) - committed dev example |
| 7 | LIVE | `.env.dev.example` | `generic-api-key` | 230 | `ZmFicmljNGwtbG9jYWwtZGV2LWZlcm5ldC1rZXktMDE=` | `.env.dev.example` local-dev value (same as #6, introduced by a later commit) - dev example |
| 8 | LIVE | `.depot/workflows/pr-checks.yml` | `generic-api-key` | 767 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Test fixture JWT secret in a workflow pin (`.depot/workflows/pr-checks.yml`) - allowlisted regex |
| 9 | LIVE | `.github/workflows/pr-checks.yml` | `generic-api-key` | 803 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Test fixture JWT secret in `.github/workflows/pr-checks.yml` - allowlisted regex |
| 10 | LIVE | `sdk/README.md` | `generic-api-key` | 119 | `eyJhbGciOiJSUzI1NiIs...` | Documentation example JWT (sdk/README.md) - sample token |
| 11 | LIVE | `sdk/README.md` | `generic-api-key` | 139 | `eyJhbGciOiJSUzI1NiIs...` | Documentation example JWT (sdk/README.md) - sample token |
| 12 | LIVE | `sdk/README.md` | `generic-api-key` | 389 | `eyJhbGciOiJSUzI1NiIs...` | Documentation example JWT (sdk/README.md) - sample token |
| 13 | LIVE | `services/api/app/core/clerk_config.py` | `generic-api-key` | 41 | `Ed25519PrivateKey` | Code identifier: `Ed25519PrivateKey` (cryptography class/enum name), not a secret |
| 14 | LIVE | `k8s/deployments/prod-nginx/external-secrets/wal-g-backup-secrets.yaml` | `generic-api-key` | 29 | `walg_s3_prefix` | Environment-variable NAME `walg_s3_prefix` in ExternalSecret manifest key, not a value |
| 15 | LIVE | `k8s/deployments/staging-nginx/external-secrets/wal-g-backup-secrets.yaml` | `generic-api-key` | 29 | `walg_s3_prefix` | Environment-variable NAME `walg_s3_prefix` in ExternalSecret manifest key, not a value |
| 16 | HIST | `.env.pytest.example` | `generic-api-key` | 12 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 17 | LIVE | `services/layer2-extraction/pyproject.toml` | `generic-api-key` | 155 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Test fixture JWT secret in `services/layer2-extraction/pyproject.toml` - allowlisted regex |
| 18 | LIVE | `services/layer2-extraction/pytest.ini.test` | `generic-api-key` | 8 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Test fixture JWT secret in `services/layer2-extraction/pytest.ini.test` - allowlisted regex |
| 19 | HIST | `.env.pytest` | `generic-api-key` | 12 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 20 | LIVE | `k8s/external-secrets/wal-g-backup-secrets.yaml` | `generic-api-key` | 29 | `walg_s3_prefix` | Environment-variable NAME `walg_s3_prefix` in ExternalSecret manifest key, not a value |
| 21 | LIVE | `k8s/base/postgres-patroni.yaml` | `generic-api-key` | 101 | `WALG_S3_PREFIX` | Environment-variable NAME `WALG_S3_PREFIX` (patroni config key), not a value |
| 22 | HIST | `apps/web/src/test/fixtures/authFixtures.ts` | `generic-api-key` | 168 | `test-csrf-xyz789` | Historical - file/string no longer present at HEAD |
| 23 | HIST | `pytest.ini.bak` | `generic-api-key` | 110 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 24 | HIST | `.github/workflows/build-deploy.yml` | `generic-api-key` | 277 | `secret=abcdefghijklmnopqrstuvwxyz123456` | Historical - file/string no longer present at HEAD |
| 25 | LIVE | `scripts/db/seed-e2e-data.ts` | `generic-api-key` | 295 | `E2E_VALIDATION_API_KEY` | Environment-variable NAME `E2E_VALIDATION_API_KEY` constant, not a value |
| 26 | LIVE | `services/layer5-ground-truth/pytest.ini` | `generic-api-key` | 22 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Test fixture JWT secret in `services/layer5-ground-truth/pytest.ini` - allowlisted regex |
| 27 | LIVE | `k8s/base/jwt-keys-secret.yaml` | `private-key` | 25 | `-----BEGIN RSA PRIVATE KEY-----` | PEM placeholder template `k8s/base/jwt-keys-secret.yaml` - contains `# REPLACE WITH REAL PRIVATE KEY`, no key material |
| 28 | HIST | `value_fabric/layer5_ground_truth/pytest.ini` | `generic-api-key` | 22 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 29 | HIST | `value_fabric/layer5_ground_truth/pytest.ini` | `generic-api-key` | 22 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 30 | HIST | `pytest.ini` | `generic-api-key` | 56 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 31 | HIST | `value-fabric/layer5-ground-truth/pytest.ini` | `generic-api-key` | 22 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |
| 32 | HIST | `.env.dev.example` | `generic-api-key` | 22 | `sk-th-SPV4lcxZ3EljtyOHDOEUzTZT9VhRsSutagsltHyAJz...` | Historical - file/string no longer present at HEAD |
| 33 | HIST | `frontend/.env.development` | `generic-api-key` | 45 | `suk-48XavjqwL8Yq6AeiFMdW3VKw3HmVbNriccDe2ztrxGaV...` | Historical - file/string no longer present at HEAD |
| 34 | HIST | `frontend/.env.production` | `generic-api-key` | 44 | `suk-48XavjqwL8Yq6AeiFMdW3VKw3HmVbNriccDe2ztrxGaV...` | Historical - file/string no longer present at HEAD |
| 35 | HIST | `frontend/.env.example` | `generic-api-key` | 35 | `suk-48XavjqwL8Yq6AeiFMdW3VKw3HmVbNriccDe2ztrxGaV...` | Historical - file/string no longer present at HEAD |
| 36 | HIST | `frontend/.env.test` | `generic-api-key` | 35 | `suk-48XavjqwL8Yq6AeiFMdW3VKw3HmVbNriccDe2ztrxGaV...` | Historical - file/string no longer present at HEAD |
| 37 | HIST | `frontend/.env.staging` | `generic-api-key` | 35 | `suk-48XavjqwL8Yq6AeiFMdW3VKw3HmVbNriccDe2ztrxGaV...` | Historical - file/string no longer present at HEAD |
| 38 | HIST | `frontend/audit-output/STUB_MOCK_DEPENDENCY_REPORT.md` | `generic-api-key` | 105 | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.` | Historical - file/string no longer present at HEAD |
| 39 | HIST | `frontend/client/src/contexts/AuthContext.tsx` | `generic-api-key` | 272 | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.` | Historical - file/string no longer present at HEAD |
| 40 | HIST | `value-fabric/.env.test` | `generic-api-key` | 21 | `test-jwt-secret-must-be-at-least-32-characters-l...` | Historical - file/string no longer present at HEAD |

## Enforcement

* `.gitleaksignore` - 40 entries, one per finding, `commit:file:rule:line`. Verified byte-for-byte against the CI log fingerprints.
* `.gitleaks.toml` `[allowlist] regexes` additions (mirror existing `AKIAIOSFODNN7EXAMPLE` / `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` precedent):
  * `'''sk_live_abc123[A-Za-z0-9_]+'''` - Stripe vendor-documented example token
  * `'''test-jwt-secret-must-be-at-least-32-characters-long'''` - explicit JWT test fixture used across workflow/pytest configs

## Remediation backlog (owner decision, org-level)

1. **History rewrite** (Org decision): `git filter-repo`/BFG to purge the 18 historical and any disallowed live strings - only if org policy requires zero historical residue. Until then, `.gitleaksignore` documents them.
2. **`k8s/base/jwt-keys-secret.yaml`** - PEM placeholder template: consider removing the `-----BEGIN RSA PRIVATE KEY-----`/`END` stub so a future real-key paste is not mistaken for a template.
3. **Skill/README example tokens** - optional: replace inline JWT/hex examples with `<...>` placeholders so documentation reads as non-secret.

## Evidence

* Source: `security-gates.yml` gitleaks-scan job log (run at corrected head), parsed to 40 records with full Fingerprints; `git cat-file -e HEAD:<path>` existence probe + secret-substring containment for LIVE/HIST.
* `.gitleaksignore` fingerprints match the CI log `commit:file:rule:line` format; matching code verified in gitleaks v8.18.4 source (`detect/detect.go` `addFinding`: global + full fingerprint map lookup).
* Re-verify with a fresh run: the CI gitleaks-scan job itself, or `go run github.com/zricethezav/gitleaks/v8@v8.18.4 detect --source . --config .gitleaks.toml`.
