# Dependabot Vulnerability Triage — 2026-08-29

> **Status:** Investigation (ranked, not yet remediated)
> **Source:** `GET /repos/Valynt/Fabric_4L/dependabot/alerts?state=open` (150 alerts, snapshot 2026-08-29)
> **Scope:** All open alerts on the default branch

## TL;DR

| Bucket | Alerts | Action required |
|---|---|---|
| **Live code** | **14** | Yes — fix by regenerating lockfiles / version bumps |
| Archived docs snapshot (`docs/archive/`) | 136 | No — noise; recommend ignoring or exclude from Dependabot |

**1 critical alert exists but lives in the archived docs snapshot, not live code.** No critical or high alert currently reaches production runtime paths beyond 1 high `Protego` alert in Layer 1 ingestion (direct dependency, ReDoS in robots.txt parsing) and 13 high/medium npm alerts (all transitive, all have root-level `pnpm.overrides` already declared but **stale lockfiles**).

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

All of the following already have **root `pnpm.overrides`** in `package.json` but the lockfiles have **not been regenerated**, so installed versions are the vulnerable ones. Regenerating lockfiles (`pnpm install` at root and in `apps/web`, then commit both lockfiles) is the primary fix.

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

### Tier 3 — Noise: archived docs snapshot (136 alerts)

- `docs/archive/frontend-root-2026-05-02/source-snapshot/pnpm-lock.yaml` is an **archived snapshot** (not a live dependency root; the `pnpm-workspace.yaml` comment explicitly excludes `archive/` from canonical tooling).
- This includes the **only critical alert** (vitest `CVE-2026-47429`).
- **Recommended actions (pick one):**
  1. Add to `.github/dependabot.yml` an `ignore` rule for that directory, OR
  2. Add the archive lockfile to Dependabot's `ignore` list (`dependency-name: "*"` scoped), OR
  3. Delete the archived snapshot from the repo if no longer needed (docs decision).
- Removing this noise drops the alert count from **150 → 14**.

---

## 3. Why many alerts still resolve to vulnerable versions

`package.json` already declares:

```json
"overrides": {
  "undici@^7.0.0": "7.29.0",
  "brace-expansion@^1.1.7": "5.0.9",
  "brace-expansion@^2.0.1": "5.0.9",
  "brace-expansion@^5.0.0": "5.0.9",
  "fast-uri@<=3.1.4": "3.1.5",
  "js-yaml": "^4.2.0",
  "image-size": ">=1.2.2",
  "extract-zip": ">=2.0.2"
}
```

But the committed lockfiles **still contain the old versions**:

- `apps/web/pnpm-lock.yaml` → `undici@7.28.0`, `brace-expansion@5.0.8`, `image-size@2.0.1`, `extract-zip@2.0.1`, `js-yaml@4.3.0`
- `pnpm-lock.yaml` (root) → `fast-uri@3.1.4`, `image-size@2.0.1`

The overrides were added in commit `e36fb409e` ("fix(security): resolve unsafe pickle deserialization and supply chain advisories (#1399)", 2026-08-21) — **but the lockfiles were not regenerated afterward**. This is classic drift: manifest overrides are correct, lockfile is stale.

---

## 4. Recommended execution order

1. **Silence archive noise.** Add Dependabot ignore for `docs/archive/frontend-root-2026-05-02/source-snapshot` (or delete snapshot). Alerts: 150 → 14.
2. **Regenerate npm lockfiles.** `pnpm install` at root and `apps/web` so overrides take effect; verify with `pnpm install --frozen-lockfile` and `pnpm audit`. Clears 13 live npm alerts.
3. **Bump Protego.** `services/layer1-ingestion/pyproject.toml`: `protego>=0.3.0` → `protego>=0.6.2`, then `uv lock`. Clears 1 live pip alert.
4. **Keep `auditConfig.ignoreCves` accurate** in root `package.json` — currently lists `CVE-2026-14257` (brace-expansion) and `GHSA-qwww-vcr4-c8h2`; verify these are still legitimately ignored after the bump to `brace-expansion@5.0.9`.

---

## 5. Validation notes

- Alert data pulled via `gh api` from GitHub Dependabot API on 2026-08-29.
- No code or dependency changes were made during this investigation.
- Next step after remediation: re-run `gh api .../dependabot/alerts?state=open` to confirm live count drops to 0 (archive suppressed or removed).