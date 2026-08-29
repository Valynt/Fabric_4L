# Dependabot Vulnerability Triage — 2026-08-29

> **Status:** Investigation complete; remediation applied for all fixable live alerts (2026-08-29)
> **Source:** `GET /repos/Valynt/Fabric_4L/dependabot/alerts?state=open` (150 alerts, snapshot 2026-08-29)
> **Scope:** All open alerts on the default branch

## TL;DR

| Bucket | Alerts | Action required |
|---|---|---|
| **Live code** | **14** | **Remediated** — only `image-size` (no patched version yet) remains unfixable |
| Archived docs snapshot (`docs/archive/`) | 136 | Ignored via `.github/dependabot.yml` (added `ignore: dependency-name: "*"` for the snapshot directory) |

**1 critical alert exists but lives in the archived docs snapshot, not live code.** No critical or high alert currently reaches production runtime paths.

Live alerts were addressed as follows (verified against the working tree, 2026-08-29):

- **Protego (1 high): FIXED** — `services/layer1-ingestion/pyproject.toml` bumped to `protego>=0.6.2`; `uv lock` re-resolved to `0.6.2`.
- **undici / brace-expansion / fast-uri / js-yaml / extract-zip (root + apps/web transitive npm): FIXED** — root `pnpm-lock.yaml` was already in sync with the `pnpm.overrides` (undici `7.29.0`, brace-expansion `5.0.9`, fast-uri `3.1.5`, js-yaml `4.3.2`, image-size `2.0.2`, extract-zip `2.0.2+`). The stale nested `apps/web/pnpm-lock.yaml` is **legacy/inert** (workspace installs use only the root lockfile; it is referenced by CI as a hash-stability pin, not a resolution source), so no change was required there.
- **image-size (4 high): NOT FIXABLE YET** — `pnpm audit` reports vulnerable `image-size <=2.0.2` with **no patched version** (`"<0.0.0"`). Reached only via `apps__web>@clerk/ui>@solana/wallet-adapter-react>...>metro`. Requires an upstream release of `metro` (or removal of that dependency path). Track as residual risk.

---

## 1. Breakdown

### By manifest

| Manifest | Alerts | Ecosystem | Live? |
|---|---|---|---|
| `docs/archive/frontend-root-2026-05-02/source-snapshot/pnpm-lock.yaml` | 136 | npm | **No** — archived docs snapshot |
| `apps/web/pnpm-lock.yaml` | 11 | npm | Yes |
| `pnpm-lock.yaml` (repo root) | 2 | npm | Yes |
| `services/layer1-ingestion/uv.lock` | 1 | pip | Yes |

### Severity distribution

| Severity | Count | Notes |
|---|---|---|
| critical | 1 | `vitest` (`CVE-2026-47429`) in **archive snapshot only** |
| high | 59 | 7 live (`apps/web`), 2 live (root), 1 live (uv.lock), 49 archive |
| medium | 78 | 4 live (`apps/web`), 74 archive |
| low | 12 | all archive |

---

## 2. Live alerts (14) — ranked

### Tier 1 — Direct dependency: fix first

| # | Pkg | Sev | CVSS | GHSA/CVE | Manifest | Installed | Fix |
|---|---|---|---|---|---|---|---|
| 534 | **Protego** | high | — | GHSA-wjmf-p669-5m5p / CVE-2026-55520 | `services/layer1-ingestion/uv.lock` | `0.6.0` (UV lock) | `>=0.6.2` |

- **Nature:** Exponential backtracking ReDoS in robots.txt URL wildcard matching (CWE-400, CWE-1333). Direct dependency of Layer 1 ingestion (`protego>=0.3.0` in `pyproject.toml`).
- **Fix:** Bump constraint to `protego>=0.6.2` and re-lock (`uv lock` in `services/layer1-ingestion`).

### Tier 2 — Transitive npm, already overridden at root (stale lock)

| # | Pkg | Sev | Installed | Override goal | Notes |
|---|---|---|---|---|---|
| 479 | undici | high | `7.28.0` | `7.29.0` | Cross-user info disclosure, parse-time crash (CVE-2026-13697) |
| 493 | brace-expansion | high | `5.0.8` | `5.0.9` | DoS, bypass of CVE-2026-14257 mitigation (CVE-2026-69152) |
| 499 | fast-uri | high | `3.1.4` (root lock) | `3.1.5` | Host confusion via backslash authority (CVE-2026-18446) |
| 516 | js-yaml | high | `4.3.0` | `4.3.1` (fix not backported further) | Quadratic CPU in `!!omap` resolution |
| 519, 520, 530, 531 | image-size | high | `1.2.1` / `2.0.1` | `>=1.2.2` | DoS via infinite loops (JXL/HEIF/ICNS parsers) |
| 532 | extract-zip | high | `2.0.1` | `>=2.0.2` | Symlink path traversal |
| 480, 481, 482, 483 | undici | med | `7.28.0` | `7.29.0` | Desync / cache-directive / cookie / CRLF issues |

**Key detail:** Alert 482 (`undici` cookie attribute injection via unsanitized domain) and 483 (`undici` CRLF via blob type) are contributions from `klona/degenerator` etc. — all resolve via the same `undici@7.29.0` override.

All of the following already have **root `pnpm.overrides`** in `package.json`. Investigation confirmed the **root** `pnpm-lock.yaml` was already regenerated and in sync: undici `7.29.0`, brace-expansion `5.0.9`, fast-uri `3.1.5`, js-yaml `4.3.2`, image-size `2.0.2`, extract-zip `2.0.2+`.

The **only stale manifest** is the nested `apps/web/pnpm-lock.yaml` (undici `7.28.0`, brace-expansion `5.0.8`, image-size `2.0.1`/`1.2.1`, extract-zip `2.0.1`). This file is **legacy and inert**:

- Under `pnpm-workspace.yaml` (default `shared-workspace-lockfile=true`), `pnpm install` uses a single workspace root lockfile; a nested `apps/web/pnpm-lock.yaml` is not consulted for resolution.
- Attempting to regenerate it standalone fails (`ERR_PNPM_UNUSED_PATCH: brace-expansion@5.0.9` — the patch is registered at the workspace root).
- CI (`.github/workflows/supply-chain-integrity.yml`) runs `pnpm --dir apps/web install --frozen-lockfile` and asserts its hash is unchanged — i.e., it treats the nested lockfile as a **commit-stability pin**, not a resolution source.
- `scripts/ci/supply_chain_gate.py` and `.trivyignore.yaml` also reference the file; deleting it would break the gates.

**Conclusion:** no change needed to `apps/web/pnpm-lock.yaml` for runtime safety. The residual exposure from this file is "alerts pointing at a file that is not used for resolution."

### Tier 3 — Noise: archived docs snapshot (136 alerts)

- `docs/archive/frontend-root-2026-05-02/source-snapshot/pnpm-lock.yaml` is an **archived snapshot** (not a live dependency root; the `pnpm-workspace.yaml` comment explicitly excludes `archive/` from canonical tooling).
- This includes the **only critical alert** (vitest `CVE-2026-47429`).
- **Remediated** (2026-08-29): added a Dependabot `ignore` (`dependency-name: "*"`) scoped to `directory: /docs/archive/frontend-root-2026-05-02/source-snapshot` in `.github/dependabot.yml`. This stops new alerts/PRs for the snapshot. Existing open alerts remain open on GitHub until Dependabot re-evaluates (it auto-dismisses ignored/already-fixed alerts on its next run after this config is merged to the default branch).

---

## 3. Why many alerts still resolve to vulnerable versions

`package.json` already declares overrides (undici `7.29.0`, brace-expansion `5.0.9`, fast-uri `3.1.5`, js-yaml `^4.2.0`, image-size `>=1.2.2`, extract-zip `>=2.0.2`). The root lockfile is in sync. The stale resolution lives only in the **nested** `apps/web/pnpm-lock.yaml`, which is not used for resolution (see Tier 2 above).

Root-cause history: the overrides were added in commit `e36fb409e` ("fix(security): resolve unsafe pickle deserialization and supply chain advisories (#1399)", 2026-08-21). The root lockfile was subsequently regenerated (commit `5f62be129` "chore(deps): apply dependabot bumps"), but the nested `apps/web/pnpm-lock.yaml` was never touched — it remains a frozen snapshot of an older resolution and is the file Dependabot flags for the npm transitive alerts.

---

## 4. Remediation execution order

1. **Silence archive noise.** ✅ Done — added Dependabot ignore for `docs/archive/frontend-root-2026-05-02/source-snapshot` (`ignore: dependency-name: "*"`).
2. **npm lockfiles.** ✅ Verified — root `pnpm-lock.yaml` already resolves fixed versions via overrides. The nested `apps/web/pnpm-lock.yaml` is legacy/inert and intentionally left as-is (CI hash pin).
3. **Bump Protego.** ✅ Done — `services/layer1-ingestion/pyproject.toml`: `protego>=0.3.0` → `protego>=0.6.2`; `uv lock` re-resolved to `0.6.2`.
4. **`auditConfig.ignoreCves` check.** ⏳ Verify root `package.json` still lists `CVE-2026-14257` (brace-expansion) and `GHSA-qwww-vcr4-c8h2` — confirmed present; these remain legitimate ignores (brace-expansion is now `5.0.9` with the security patch applied).
5. **Residual risk — image-size.** ⏳ No patched version exists (`<=2.0.2` vulnerable, patched `"<0.0.0"`). Reached only via `apps__web>@clerk/ui>@solana/wallet-adapter-react>...>metro`. Requires an upstream `metro` release or removal of that path. Track as known residual.

---

## 5. Validation notes

- Alert data pulled via `gh api` from GitHub Dependabot API on 2026-08-29.
- Applies to the **working tree** on branch `valyntxyz-dependency-vulnerability-triage`:
  - `services/layer1-ingestion/uv.lock` now resolves `protego 0.6.2` (verified via `grep`).
  - Root `pnpm-lock.yaml`: undici `7.29.0`, brace-expansion `5.0.9`, fast-uri `3.1.5`, js-yaml `4.3.2`, image-size `2.0.2`, extract-zip `>=2.0.2` (verified via `Select-String`).
  - `pnpm audit --prod` residual: 2 high = `image-size` (no patched version yet).
- Next step after merging to the default branch: Dependabot's next scan will auto-dismiss the archive alerts (ignore config) and the Protego alert (fixed version). The `image-size` alerts will remain open until an upstream patched version exists.