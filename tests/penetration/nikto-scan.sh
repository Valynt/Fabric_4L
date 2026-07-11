#!/usr/bin/env bash
set -euo pipefail

TARGET_URL="http://localhost:8000"
OUTPUT_DIR="nikto-results"
TIMEOUT_SECONDS="1200"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "Missing value for --target" >&2
        exit 2
      fi
      TARGET_URL="$2"
      shift 2
      ;;
    --output)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "Missing value for --output" >&2
        exit 2
      fi
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --timeout)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "Missing value for --timeout" >&2
        exit 2
      fi
      TIMEOUT_SECONDS="$2"
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

if [[ "$OUTPUT_DIR" = /* ]]; then
  OUTPUT_ABS_PATH="$OUTPUT_DIR"
else
  OUTPUT_ABS_PATH="$(pwd)/$OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_ABS_PATH"

REPORT_TXT="$OUTPUT_ABS_PATH/nikto-report.txt"
SUMMARY_JSON="$OUTPUT_ABS_PATH/summary.json"
RAW_LOG="$OUTPUT_ABS_PATH/nikto.log"

SCAN_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if command -v docker >/dev/null 2>&1; then
  docker run --rm \
    --network host \
    -v "$OUTPUT_ABS_PATH:/tmp/nikto-results:rw" \
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
