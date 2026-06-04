#!/usr/bin/env bash
# Compatibility wrapper for schema/index governance verification.
#
# The canonical checks live under scripts/ci/ and Makefile targets. In
# particular, make check-migration-heads delegates to
# scripts/ci/check_migration_entrypoints.py, which validates the maintained
# Alembic-managed service layout and enforces one migration head per service.
# Keep this wrapper thin so schema/index mandates cannot drift from the
# canonical migration governance gate.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

exec "${MAKE:-make}" check-migration-heads
