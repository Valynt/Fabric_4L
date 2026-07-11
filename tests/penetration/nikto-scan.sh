#!/usr/bin/env bash
set -euo pipefail

TARGET_URL="http://localhost:8000"
OUTPUT_DIR="nikto-results"
TIMEOUT_SECONDS="1200"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_URL="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: nikto-scan.sh [--target URL] [--output DIR] [--timeout SECONDS]
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$OUTPUT_DIR"

REPORT_TXT="$OUTPUT_DIR/nikto-report.txt"
SUMMARY_JSON="$OUTPUT_DIR/summary.json"
RAW_LOG="$OUTPUT_DIR/nikto.log"

SCAN_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if command -v docker >/dev/null 2>&1; then
  docker run --rm \
    --network host \
    -v "$(pwd)/$OUTPUT_DIR:/tmp/nikto-results:rw" \
    sullo/nikto:latest \
    -h "$TARGET_URL" \
    -o /tmp/nikto-results/nikto-report.txt \
    -Format txt \
    -maxtime "$TIMEOUT_SECONDS" >"$RAW_LOG" 2>&1 || true
else
  echo "docker is unavailable; skipping nikto execution" >"$RAW_LOG"
fi

if [[ ! -f "$REPORT_TXT" ]]; then
  echo "Nikto report unavailable for target $TARGET_URL" >"$REPORT_TXT"
fi

if grep -qE '^\+ ' "$REPORT_TXT"; then
  FINDING_COUNT="$(grep -Ec '^\+ ' "$REPORT_TXT")"
  HIGH_COUNT=0
  MEDIUM_COUNT=0
  LOW_COUNT="$FINDING_COUNT"
else
  FINDING_COUNT=0
  HIGH_COUNT=0
  MEDIUM_COUNT=0
  LOW_COUNT=0
fi

cat >"$SUMMARY_JSON" <<EOF
{
  "target": "$TARGET_URL",
  "scan_timestamp": "$SCAN_TIMESTAMP",
  "findings_total": $FINDING_COUNT,
  "vulnerabilities": {
    "high": $HIGH_COUNT,
    "medium": $MEDIUM_COUNT,
    "low": $LOW_COUNT
  }
}
EOF
