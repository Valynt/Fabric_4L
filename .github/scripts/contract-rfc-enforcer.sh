#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# contract-rfc-enforcer.sh
#
# CI gate: Ensures that any PR modifying files under contracts/openapi/ or
# contracts/jsonschema/ references an approved Contract RFC issue.
#
# Usage:
#   In a GitHub Actions workflow, pass the PR body and changed files:
#     bash .github/scripts/contract-rfc-enforcer.sh "${{ github.event.pull_request.body }}" <changed_files_list>
#
#   For local testing:
#     bash .github/scripts/contract-rfc-enforcer.sh "Closes #42" "contracts/openapi/layer1-ingestion.json"
#
# Exit codes:
#   0 — No contract files changed, or RFC reference found.
#   1 — Contract files changed without an RFC reference.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PR_BODY="${1:-}"
CHANGED_FILES="${2:-}"

# If no changed files provided, try to detect from git diff against origin/main
if [[ -z "$CHANGED_FILES" ]]; then
  CHANGED_FILES=$(git diff --name-only origin/main...HEAD 2>/dev/null || echo "")
fi

# ── Step 1: Check if any contract files were modified ────────────────────────
CONTRACT_CHANGES=""
while IFS= read -r file; do
  case "$file" in
    contracts/openapi/*|contracts/jsonschema/*|contracts/tool-manifests/*)
      CONTRACT_CHANGES="${CONTRACT_CHANGES}${file}\n"
      ;;
  esac
done <<< "$CHANGED_FILES"

if [[ -z "$CONTRACT_CHANGES" ]]; then
  echo "✅ No contract files modified. RFC check skipped."
  exit 0
fi

echo "📋 Contract files modified:"
echo -e "$CONTRACT_CHANGES"

# ── Step 2: Check PR body for RFC reference ──────────────────────────────────
# Accepted patterns:
#   - "RFC #123" or "RFC-123"
#   - "Closes #123" or "Fixes #123" (standard GitHub issue close keywords)
#   - "contract-rfc: #123"
#   - "HOTFIX — retroactive RFC will follow" (emergency bypass)

HOTFIX_PATTERN="(HOTFIX|hotfix|EMERGENCY|emergency).*RFC"
RFC_PATTERN="(RFC[- ]?#?[0-9]+|[Cc]loses #[0-9]+|[Ff]ixes #[0-9]+|contract-rfc: ?#[0-9]+)"

if echo "$PR_BODY" | grep -qEi "$HOTFIX_PATTERN"; then
  echo "⚠️  HOTFIX detected. Emergency bypass accepted."
  echo "   Reminder: A retroactive RFC must be filed within 24 hours."
  exit 0
fi

if echo "$PR_BODY" | grep -qE "$RFC_PATTERN"; then
  RFC_REF=$(echo "$PR_BODY" | grep -oE "$RFC_PATTERN" | head -1)
  echo "✅ RFC reference found: $RFC_REF"
  exit 0
fi

# ── Step 3: Fail ─────────────────────────────────────────────────────────────
echo ""
echo "❌ CONTRACT RFC REQUIRED"
echo ""
echo "This PR modifies contract files but does not reference an approved RFC."
echo ""
echo "To fix this, either:"
echo "  1. Create a Contract RFC issue using the template and reference it in your PR body:"
echo "     e.g., 'Closes #123' or 'RFC #123'"
echo "  2. If this is an emergency hotfix, add 'HOTFIX — retroactive RFC will follow'"
echo "     to your PR description."
echo ""
echo "See contracts/GOVERNANCE.md for the full RFC process."
exit 1
