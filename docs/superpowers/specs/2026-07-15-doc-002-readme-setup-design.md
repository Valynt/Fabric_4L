# DOC-002 README Setup Contract Design

## Finding

The README command table describes `make setup` as installing dependencies, starting development services, and applying migrations. The Makefile defines `setup` as installing Python service development dependencies only. The README Quickstart already documents frontend installation, infrastructure startup, and migrations as separate commands.

## Design

Update only the stale command-table description so it states that `make setup` installs Python service development dependencies. Preserve the existing Quickstart, command names, and links to the canonical development documentation.

Extend the existing documentation contract test to assert both the canonical description and the absence of the stale description. This prevents the specific setup-contract drift from returning without introducing a new checker or CI job.

## Scope

- `README.md`: correct the `make setup` command-table description.
- `tests/docs/test_command_map.py`: add the focused regression assertion.
- `docs/superpowers/specs/2026-07-15-doc-002-readme-setup-design.md`: record this approved bounded design.
- `docs/superpowers/plans/2026-07-15-doc-002-readme-setup.md`: record the implementation checklist for the bounded remediation.

No runtime code, public contracts, dependencies, lockfiles, generated files, workflows, migrations, or security controls change.

## Validation

Run the targeted documentation contract test first. Then run the repository's command-map or documentation validation target if available. Report any environment limitation explicitly.

## Rollback

Revert the README and test commit together. Rollback would restore the known documentation mismatch and is therefore appropriate only if the Makefile's `setup` contract changes in the same rollback.
