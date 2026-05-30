#!/usr/bin/env bash
# scripts/release-gate.sh — Enforcement-grade Release Gate orchestrator for Value Fabric
# Usage: bash scripts/release-gate.sh [PROFILE]
# Profile: any profile defined in .fabric/prod-gates.policy.yaml (default: release-candidate)
set -uo pipefail

PROFILE="${1:-release-candidate}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARTIFACT_DIR="${ROOT}/artifacts/release"
LOG_DIR="${ARTIFACT_DIR}/logs"
POLICY_FILE="${ROOT}/.fabric/prod-gates.policy.yaml"
mkdir -p "$LOG_DIR"

# Use relative path for Python (native Windows Python doesn't understand /c/... paths)
POLICY_FILE_REL=".fabric/prod-gates.policy.yaml"

# Associative arrays for gate metadata
declare -A GATE_TARGET
declare -A GATE_CLASS
declare -A GATE_REQUIRED
declare -A GATE_CAVEAT
declare -A GATE_STATUS
declare -A GATE_REASON
declare -A GATE_ARTIFACTS

# ── Negative validation: policy file ─────────────────────────────────────────
if [ ! -s "$POLICY_FILE" ]; then
    echo "❌ Negative check FAILED: Policy file $POLICY_FILE missing or empty"
    exit 1
fi

_PYTHON="${PYTHON:-python3}"
if ! command -v "$_PYTHON" > /dev/null 2>&1; then
    _PYTHON="python"
fi

if ! $_PYTHON -c "import yaml; yaml.safe_load(open('$POLICY_FILE_REL'))" 2>/dev/null; then
    echo "❌ Negative check FAILED: Policy file is not valid YAML"
    exit 1
fi

# ── Negative validation: profile existence ───────────────────────────────────
PROFILE_VALID=$($_PYTHON -c "
import yaml
with open('$POLICY_FILE_REL') as f:
    data = yaml.safe_load(f)
print('true' if '$PROFILE' in data.get('profiles', {}) else 'false')
")
if [ "$PROFILE_VALID" != "true" ]; then
    echo "❌ Negative check FAILED: Unknown profile '$PROFILE'"
    VALID_PROFILES=$($_PYTHON -c "
import yaml
with open('$POLICY_FILE_REL') as f:
    data = yaml.safe_load(f)
print(', '.join(sorted(data.get('profiles', {}).keys())))
")
    echo "   Valid profiles: $VALID_PROFILES"
    exit 1
fi

# ── Parse policy YAML once into shell-readable metadata ──────────────────────
$_PYTHON - "$PROFILE" "$POLICY_FILE_REL" <<'PYEOF' > "${LOG_DIR}/policy-meta.txt"
import yaml, sys
profile_name = sys.argv[1]
policy_file = sys.argv[2]
with open(policy_file) as f:
    data = yaml.safe_load(f)
profile = data['profiles'][profile_name]
for gate in profile.get('gates', []):
    g = data['gate-definitions'][gate]
    target = g.get('target', gate)
    klass = g.get('class', 'blocking')
    required = 'true' if g.get('required', False) else 'false'
    caveat = g.get('caveat', '')
    artifact_dir = g.get('artifact-dir', '')
    print(f"GATE:{gate}:{target}:{klass}:{required}:{artifact_dir}:{caveat}")
PYEOF

GATES=""
while IFS= read -r line; do
    if [[ "$line" == GATE:* ]]; then
        IFS=':' read -r _ gate target klass required artifact_dir caveat <<< "$line"
        GATES="$GATES $gate"
        GATE_TARGET[$gate]="$target"
        GATE_CLASS[$gate]="$klass"
        GATE_REQUIRED[$gate]="$required"
        GATE_CAVEAT[$gate]="$caveat"
        GATE_ARTIFACTS[$gate]="$artifact_dir"
        GATE_STATUS[$gate]="NOT_RUN"
    fi
done < "${LOG_DIR}/policy-meta.txt"
GATES="${GATES# }"

# ── Negative validation: required gate targets must exist in Makefile ─────────
MISSING_TARGETS=0
for gate in $GATES; do
    target="${GATE_TARGET[$gate]}"
    if ! make -C "$ROOT" -n "$target" > /dev/null 2>&1; then
        echo "❌ Negative check FAILED: Makefile target '$target' for gate '$gate' does not exist"
        MISSING_TARGETS=$((MISSING_TARGETS + 1))
    fi
done
if [ "$MISSING_TARGETS" -gt 0 ]; then
    echo "   $MISSING_TARGETS required gate target(s) missing from Makefile — aborting"
    exit 1
fi

# ── Helper: run a Makefile target ────────────────────────────────────────────
run_target() {
    local gate="$1"
    local target="${GATE_TARGET[$gate]}"
    local logfile="${LOG_DIR}/${target}.log"
    echo "→ [$gate] $target ..." | tee -a "$LOG_DIR/release-gate.log"
    if make -C "$ROOT" "$target" > "$logfile" 2>&1; then
        echo "   ✅ $gate" | tee -a "$LOG_DIR/release-gate.log"
        GATE_STATUS[$gate]="PASS"
    else
        local rc=$?
        # Classify the failure
        if grep -q "PLACEHOLDER" "$logfile" 2>/dev/null; then
            GATE_REASON[$gate]="PLACEHOLDER"
        elif grep -q "advisory" "$logfile" 2>/dev/null; then
            GATE_REASON[$gate]="ADVISORY_FAIL"
        else
            GATE_REASON[$gate]="FAIL"
        fi
        echo "   ❌ $gate (see ${logfile})" | tee -a "$LOG_DIR/release-gate.log"
        GATE_STATUS[$gate]="FAIL"
    fi
}

echo "🚀 Release Gate — Profile: $PROFILE"
echo "   Root:    $ROOT"
echo "   Policy:  $POLICY_FILE"
echo "   Artifacts: $ARTIFACT_DIR"
echo ""

# ── Step 1: Policy validation (hard-fail) ────────────────────────────────────
run_target "policy"
if [ "${GATE_STATUS[policy]}" != "PASS" ]; then
    echo "❌ Policy validation failed — aborting"
    exit 1
fi

# ── Step 2: Optional lint (hard-fail when included in profile) ───────────────
if [ -n "${GATE_TARGET[lint]:-}" ]; then
    run_target "lint"
fi

# ── Step 3: Remaining gates from policy profile ──────────────────────────────
for gate in $GATES; do
    if [ "$gate" = "policy" ] || [ "$gate" = "lint" ]; then
        continue  # Already run
    fi
    run_target "$gate"
done

# ── Step 4: Negative validation checks ───────────────────────────────────────
echo ""
echo "→ Running negative validation checks ..."
NEGATIVE_PASS=0
NEGATIVE_TOTAL=0

# 4a: Broken lint must fail
NEGATIVE_TOTAL=$((NEGATIVE_TOTAL + 1))
if [ -z "${GATE_TARGET[lint]:-}" ]; then
    echo "   ℹ️  Negative: lint not in profile — skipping"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
elif [ "${GATE_STATUS[lint]}" = "FAIL" ]; then
    echo "   ✅ Negative: Broken lint correctly fails gate"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
else
    echo "   ⚠️  Negative: Broken lint check not exercised (lint passed)"
fi

# 4b: Missing required artifact must fail sign-manifest
NEGATIVE_TOTAL=$((NEGATIVE_TOTAL + 1))
if [ "${GATE_STATUS[sign-manifest]:-}" = "FAIL" ]; then
    echo "   ✅ Negative: Missing artifacts correctly fails sign-manifest"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
else
    echo "   ℹ️  Negative: sign-manifest not in profile or passed"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
fi

# 4c: Missing summary must fail render-summary
NEGATIVE_TOTAL=$((NEGATIVE_TOTAL + 1))
if [ "${GATE_STATUS[summary]:-}" = "FAIL" ]; then
    echo "   ✅ Negative: Missing summary correctly fails render-summary"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
else
    echo "   ℹ️  Negative: render-summary not in profile or passed"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
fi

# 4d: Release-candidate profiles must not contain unclassified placeholder gates
NEGATIVE_TOTAL=$((NEGATIVE_TOTAL + 1))
if [ "$PROFILE" = "release-candidate" ]; then
    PLACEHOLDER_FAIL=0
    PLACEHOLDER_TOTAL=0
    for gate in $GATES; do
        if [ "${GATE_CLASS[$gate]}" = "placeholder" ]; then
            PLACEHOLDER_TOTAL=$((PLACEHOLDER_TOTAL + 1))
            if [ "${GATE_STATUS[$gate]}" = "FAIL" ]; then
                PLACEHOLDER_FAIL=$((PLACEHOLDER_FAIL + 1))
            fi
        fi
    done
    if [ "$PLACEHOLDER_TOTAL" -eq 0 ]; then
        echo "   ✅ Negative: No unclassified placeholder gates remain in release-candidate"
        NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
    elif [ "$PLACEHOLDER_FAIL" -eq "$PLACEHOLDER_TOTAL" ]; then
        echo "   ✅ Negative: Placeholder gates fail closed in release-candidate ($PLACEHOLDER_FAIL/$PLACEHOLDER_TOTAL)"
        NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
    else
        echo "   ⚠️  Negative: Some placeholder gates did not fail closed in release-candidate"
    fi
else
    echo "   ℹ️  Negative: Placeholder enforcement only checked in release-candidate"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
fi

# 4e: Broken smoke must fail if smoke is blocking
NEGATIVE_TOTAL=$((NEGATIVE_TOTAL + 1))
if [ "${GATE_CLASS[smoke]:-}" = "blocking" ] && [ "${GATE_STATUS[smoke]:-}" = "FAIL" ]; then
    echo "   ✅ Negative: Broken smoke correctly fails (smoke is blocking)"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
elif [ "${GATE_CLASS[smoke]:-}" = "advisory" ]; then
    echo "   ℹ️  Negative: Smoke is advisory — failure does not block"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
elif [ -z "${GATE_CLASS[smoke]:-}" ]; then
    echo "   ℹ️  Negative: Smoke not in profile — skipping"
    NEGATIVE_PASS=$((NEGATIVE_PASS + 1))
else
    echo "   ⚠️  Negative: Smoke check not exercised as expected"
fi

# ── Step 5: Profile-specific enforcement ─────────────────────────────────────
# release-candidate: placeholder gates either must be absent after graduation or fail closed.
# If a placeholder passes, that is suspicious — it means it was silently promoted.
PLACEHOLDER_UNEXPECTED_PASS=0
if [ "$PROFILE" = "release-candidate" ]; then
    for gate in $GATES; do
        if [ "${GATE_CLASS[$gate]}" = "placeholder" ] && [ "${GATE_STATUS[$gate]}" = "PASS" ]; then
            PLACEHOLDER_UNEXPECTED_PASS=$((PLACEHOLDER_UNEXPECTED_PASS + 1))
            echo "   ⚠️  Placeholder gate '$gate' unexpectedly passed — may have been silently promoted"
        fi
    done
fi

# ── Final decision ───────────────────────────────────────────────────────────
echo ""

# Count results
BLOCKING_PASS=0
BLOCKING_FAIL=0
BLOCKING_TOTAL=0
ADVISORY_PASS=0
ADVISORY_FAIL=0
ADVISORY_TOTAL=0
PLACEHOLDER_FAIL_COUNT=0
ARTIFACT_PASS=0
ARTIFACT_FAIL=0
ARTIFACT_TOTAL=0
SKIPPED_CHECKS=""
ACCEPTED_CAVEATS=""

for gate in $GATES; do
    class="${GATE_CLASS[$gate]}"
    status="${GATE_STATUS[$gate]}"
    caveat="${GATE_CAVEAT[$gate]}"
    if [ "$class" = "blocking" ]; then
        BLOCKING_TOTAL=$((BLOCKING_TOTAL + 1))
        if [ "$status" = "PASS" ]; then
            BLOCKING_PASS=$((BLOCKING_PASS + 1))
        else
            BLOCKING_FAIL=$((BLOCKING_FAIL + 1))
        fi
    elif [ "$class" = "advisory" ]; then
        ADVISORY_TOTAL=$((ADVISORY_TOTAL + 1))
        if [ "$status" = "PASS" ]; then
            ADVISORY_PASS=$((ADVISORY_PASS + 1))
        else
            ADVISORY_FAIL=$((ADVISORY_FAIL + 1))
            if [ -n "$caveat" ]; then
                ACCEPTED_CAVEATS="${ACCEPTED_CAVEATS}- $gate: $caveat\n"
            fi
        fi
    elif [ "$class" = "placeholder" ]; then
        if [ "$status" = "FAIL" ]; then
            PLACEHOLDER_FAIL_COUNT=$((PLACEHOLDER_FAIL_COUNT + 1))
            if [ -n "$caveat" ]; then
                ACCEPTED_CAVEATS="${ACCEPTED_CAVEATS}- $gate: $caveat\n"
            fi
        fi
    elif [ "$class" = "artifact" ]; then
        ARTIFACT_TOTAL=$((ARTIFACT_TOTAL + 1))
        if [ "$status" = "PASS" ]; then
            ARTIFACT_PASS=$((ARTIFACT_PASS + 1))
        else
            ARTIFACT_FAIL=$((ARTIFACT_FAIL + 1))
        fi
    fi
done

HARD_FAIL=0
FINAL_DECISION="PASS"
FAIL_REASONS=""

if [ "$BLOCKING_FAIL" -gt 0 ]; then
    HARD_FAIL=1
    FINAL_DECISION="FAIL"
    FAIL_REASONS="${FAIL_REASONS}Blocking gate(s) failed ($BLOCKING_FAIL/$BLOCKING_TOTAL). "
fi
if [ "$ARTIFACT_FAIL" -gt 0 ]; then
    HARD_FAIL=1
    FINAL_DECISION="FAIL"
    FAIL_REASONS="${FAIL_REASONS}Artifact gate(s) failed ($ARTIFACT_FAIL/$ARTIFACT_TOTAL). "
fi
if [ "$PROFILE" = "release-candidate" ] && [ "$PLACEHOLDER_FAIL_COUNT" -gt 0 ]; then
    HARD_FAIL=1
    FINAL_DECISION="FAIL"
    FAIL_REASONS="${FAIL_REASONS}Placeholder gate(s) failed ($PLACEHOLDER_FAIL_COUNT) in release-candidate. "
fi
if [ "$PROFILE" = "release-candidate" ] && [ "$PLACEHOLDER_UNEXPECTED_PASS" -gt 0 ]; then
    HARD_FAIL=1
    FINAL_DECISION="FAIL"
    FAIL_REASONS="${FAIL_REASONS}Placeholder gate(s) unexpectedly passed ($PLACEHOLDER_UNEXPECTED_PASS) — silent promotion detected. "
fi

echo "========================================"
echo "Release Gate Results — Profile: $PROFILE"
echo "========================================"
printf "  Blocking:   %d/%d passed\n" "$BLOCKING_PASS" "$BLOCKING_TOTAL"
printf "  Advisory:   %d/%d passed\n" "$ADVISORY_PASS" "$ADVISORY_TOTAL"
printf "  Artifact:   %d/%d passed\n" "$ARTIFACT_PASS" "$ARTIFACT_TOTAL"
printf "  Placeholder:%d failed (release-candidate blocks on these)\n" "$PLACEHOLDER_FAIL_COUNT"
printf "  Negative:   %d/%d checks validated\n" "$NEGATIVE_PASS" "$NEGATIVE_TOTAL"
echo ""

if [ $HARD_FAIL -eq 0 ]; then
    echo "✅ PASS — All blocking gates passed, no placeholders in release-candidate"
else
    echo "❌ FAIL — $FAIL_REASONS"
fi
echo ""
echo "Logs:    $LOG_DIR"
echo "Summary: $ARTIFACT_DIR/summary.md"
echo "========================================"

# Write machine-readable result file for summary renderer
GIT_SHA="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
cat > "$ARTIFACT_DIR/gate-result.json" <<EOF
{
  "profile": "$PROFILE",
  "decision": "$FINAL_DECISION",
  "git_sha": "$GIT_SHA",
  "blocking_pass": $BLOCKING_PASS,
  "blocking_total": $BLOCKING_TOTAL,
  "advisory_pass": $ADVISORY_PASS,
  "advisory_total": $ADVISORY_TOTAL,
  "artifact_pass": $ARTIFACT_PASS,
  "artifact_total": $ARTIFACT_TOTAL,
  "placeholder_fail": $PLACEHOLDER_FAIL_COUNT,
  "negative_pass": $NEGATIVE_PASS,
  "negative_total": $NEGATIVE_TOTAL,
  "fail_reasons": "$FAIL_REASONS",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

# The summary gate may run before the final decision file exists. Re-render it
# after gate-result.json is written so evidence records the current run instead
# of stale prior-run PASS/FAIL data.
if [ -f "$ROOT/scripts/ops/render-release-summary.sh" ]; then
    bash "$ROOT/scripts/ops/render-release-summary.sh" >> "$LOG_DIR/gate-summary.log" 2>&1 || {
        echo "❌ Final summary render failed after gate-result.json was written" | tee -a "$LOG_DIR/release-gate.log"
        exit 1
    }
fi

exit $HARD_FAIL
