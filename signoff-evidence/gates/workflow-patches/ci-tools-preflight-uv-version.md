# Workflow Patch Packet: CI Tools Image Preflight — uv version assertion

- **Patch file:** `signoff-evidence/gates/workflow-patches/ci-tools-preflight-uv-version.patch`
- **Target file:** `.github/workflows/supply-chain-integrity.yml`
- **Base commit:** `e3ace52032f8c80436e46adee4fba27402ae9f31` (`main`, verified via `git rev-parse HEAD` at packet creation)
- **Prepared:** 2026-08-11

> Note: the agent token cannot edit `.github/workflows/`, so the fix is delivered as an
> apply-ready patch. A maintainer with workflow-write permission must apply it.

## Rationale

The `CI Tools Image Preflight` job fails on every PR. The step "Pull image and verify
digest and tool versions" asserts tool versions inside the centrally managed CI tools
image using an exact full-line match (`grep -Fxq`). The pinned `uv` in the image prints
a platform suffix, so the exact match can never succeed. The failure cascades into the
`Supply Chain Summary` job, which then reports "One or more required supply-chain
controls failed or were unexpectedly skipped" and fails the whole workflow run.

## Defect

File: `.github/workflows/supply-chain-integrity.yml`, job `ci-tools-preflight`
("CI Tools Image Preflight", line 62), step "Pull image and verify digest and tool
versions" (line 73).

- **Line 86** — the helper: `if ! grep -Fxq -- "$expected" <<<"$output"; then`
  performs an exact full-line match against the command output.
- **Line 96** — the broken assertion: `assert_line "uv --version" "uv 0.11.6"`.

Observed failure from a real run (2026-08-10/11):

```
ASSERTION FAILED: uv --version
Expected: uv 0.11.6
Got:
uv 0.11.6 (x86_64-unknown-linux-gnu)
```

`uv` appends `(<target-triple>)` to its `--version` output, so `grep -Fxq` against the
bare `uv 0.11.6` string always fails even when the pinned version is correct.

### Why only the uv assertion is changed

Every other assertion in the step was checked against the same exact-match risk:

- **grype (line 91), syft (line 92), cosign (line 93)** — already pipe through `awk`
  extraction that isolates the version field, so any platform/extra text in the raw
  output never reaches the comparison. cosign's `GitVersion` field is a bare version
  string. Not at risk.
- **pip-audit (line 94), pip-licenses (line 95)** — print exactly
  `pip-audit 2.9.0` / `pip-licenses 5.0.0`, no suffix. Not at risk.
- **python (line 97)** — prints exactly `Python 3.12.10`. Not at risk.
- **node (line 98)** — prints exactly `v22.17.0`, no platform suffix. Not at risk.
- **pnpm (line 99)** — prints exactly `10.18.1`. Not at risk.

`uv` is the only tool whose `--version` output demonstrably carries a trailing platform
suffix (confirmed by the failing CI log), so the diff touches only line 96 plus an
explanatory comment.

## Fix

Replace the bare `uv --version` command with an `awk` field extraction, mirroring the
pattern already used for grype/syft/cosign in the same step:

```bash
assert_line "uv --version | awk '{print \$1, \$2}'" "uv 0.11.6"
```

`awk '{print $1, $2}'` reduces `uv 0.11.6 (x86_64-unknown-linux-gnu)` to `uv 0.11.6`,
which the existing `grep -Fxq` exact match then accepts. This was chosen over a
`grep -Eq` regex variant because it:

- keeps the existing `assert_line` helper and its exact-match semantics untouched
  (no new helper, no change to shared code paths used by the other 8 assertions);
- is consistent with the awk-extraction idiom already established three lines above;
- still fails closed on a genuinely different version (`uv 0.12.0 (…)` extracts to
  `uv 0.12.0`, which does not equal `uv 0.11.6`), and on any output shape where the
  version field is missing.

## Expected gate behavior change

- **Before:** `CI Tools Image Preflight` fails 100% of the time on the uv assertion,
  and `Supply Chain Summary` fails downstream. No PR can go green.
- **After:** the preflight passes when the image's uv version is the pinned `0.11.6`,
  regardless of a trailing platform suffix; it still fails on a genuinely different
  uv version, a missing uv binary, or a digest mismatch (unchanged digest check at
  line 80). `Supply Chain Summary` then reflects the real state of the remaining
  supply-chain controls.

No contract, tenant-isolation, migration, or runtime-code impact — this is a CI
workflow assertion fix only.

## Application (one command)

From the repository root, on a branch based on `main` at
`e3ace52032f8c80436e46adee4fba27402ae9f31`:

```bash
git apply signoff-evidence/gates/workflow-patches/ci-tools-preflight-uv-version.patch
```

Then commit with an account allowed to modify `.github/workflows/` and push. The patch
modifies exactly one file, `.github/workflows/supply-chain-integrity.yml`
(1 line replaced by 1 comment block + 1 assertion line).

## Verification evidence

Performed against `main` at `e3ace52032f8c80436e46adee4fba27402ae9f31`:

1. **Patch generation** — the workflow file was copied to a scratch directory
   (`.tmp/wp/{a,b}/.github/workflows/`), the fix applied to the `b` copy, and the
   diff produced with `git diff --no-index --src-prefix= --dst-prefix=`. Scratch
   copies were deleted afterward; no repo file was modified.
2. **Apply check:**

   ```
   $ git apply --check signoff-evidence/gates/workflow-patches/ci-tools-preflight-uv-version.patch
   GIT APPLY CHECK: PASS
   ```

3. **Assertion logic sanity check** (bash + awk simulation of the image output):

   - `uv 0.11.6 (x86_64-unknown-linux-gnu)` → extracts to `uv 0.11.6` →
     `grep -Fxq "uv 0.11.6"` **matches** (previously failed).
   - `uv 0.12.0 (x86_64-unknown-linux-gnu)` → extracts to `uv 0.12.0` →
     `grep -Fxq "uv 0.11.6"` **does not match** (still fails closed).

Not verified: an actual workflow run against the live CI tools image (requires pushing
to GitHub with workflow-write permission). Residual risk is minimal — the extraction
mirrors the grype/syft/cosign assertions already passing in the same step.
