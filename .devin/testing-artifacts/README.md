# DEPRECATED — Testing Artifacts

**This directory is deprecated.** All test audit artifacts have been consolidated to `.windsurf/testing/`.

## What Happened

Multiple directories (`testing/`, `testing-artifacts/`, `testing-assurance/`) contained overlapping but divergent versions of the same reports. This violated the DRY principle and caused confusion about which version was canonical.

## Where to Find Things

- **Current artifacts:** `.windsurf/testing/`
- **Archived historical variants:** `.windsurf/archive/testing-dedup/`

## Action Required

If you reference files in this directory, update paths to `.windsurf/testing/`.
This directory will be removed in a future cleanup pass.
