#!/usr/bin/env bash
# Fail-closed live workflow validation runner for Fabric_4L.
#
# This script is intentionally conservative: it always validates compose syntax
# and service health, and it runs seed/Playwright only when explicitly enabled.
# It writes sanitized evidence artifacts under artifacts/live-workflow-validation.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.live.yml}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-fabric4l_live_validation}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$ROOT_DIR/artifacts/live-workflow-validation}"
FRONTEND_URL="${PLAYWRIGHT_LIVE_FRONTEND_URL:-http://localhost:3001}"
BACKEND_URL="${PLAYWRIGHT_BACKEND_URL:-http://localhost:8004}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-360}"
RUN_LIVE_SEED="${RUN_LIVE_SEED:-false}"
RUN_LIVE_PLAYWRIGHT="${RUN_LIVE_PLAYWRIGHT:-false}"
LIVE_SERVICE_HEALTH_URLS="${LIVE_SERVICE_HEALTH_URLS:-}"
REQUIRED_REMOTE_SERVICE_NAMES="${REQUIRED_REMOTE_SERVICE_NAMES:-layer1,layer2,layer3,layer4,layer5,layer6,postgres,redis,neo4j,minio}"
LIVE_ENVIRONMENT_NAME="${LIVE_ENVIRONMENT_NAME:-}"
RELEASE_CANDIDATE_SHA="${RELEASE_CANDIDATE_SHA:-${GITHUB_SHA:-}}"
CONFIG_ONLY="false"
START_STACK="true"
REMOTE_STACK="false"
SMOKE_MODE="false"

resolve_node_bin() {
  if command -v node >/dev/null 2>&1; then
    command -v node
    return 0
  fi

  local candidate
  for candidate in \
    "/c/Program Files/nodejs/node.exe" \
    "/mnt/c/Program Files/nodejs/node.exe" \
    "C:/Program Files/nodejs/node.exe"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

NODE_BIN="${NODE_BIN:-$(resolve_node_bin || true)}"
FINALIZED="false"

node_bin_available() {
  if [[ -z "$NODE_BIN" ]]; then
    return 1
  fi
  if [[ -x "$NODE_BIN" ]]; then
    return 0
  fi
  command -v "$NODE_BIN" >/dev/null 2>&1
}

json_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/}"
  printf '%s' "$value"
}

artifact_exists_json() {
  if [[ -e "$1" ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

usage() {
  cat <<'USAGE'
Usage: scripts/ci/run_live_workflow_validation.sh [options]

Options:
  --config-only       Validate docker-compose.live.yml and frontend guardrails only.
  --smoke             Start the live stack, probe all layer health endpoints, write a
                      timestamped evidence artifact, then tear down. Completes in ~5 min.
                      Used for automatic CI validation on release/** and main branches.
  --no-start          Do not start or rebuild containers; probe the currently running stack.
  --remote            Probe an already deployed remote live stack by URL instead of docker-compose containers.
  --seed              Run the guarded live seed step after services become healthy.
  --playwright        Run the guarded live Playwright P0 suite after services become healthy.
  --help              Show this help text.

Environment overrides:
  COMPOSE_FILE=docker-compose.live.yml
  COMPOSE_PROJECT_NAME=fabric4l_live_validation
  ARTIFACT_DIR=artifacts/live-workflow-validation
  PLAYWRIGHT_LIVE_FRONTEND_URL=http://localhost:3001
  PLAYWRIGHT_BACKEND_URL=http://localhost:8004
  LIVE_SERVICE_HEALTH_URLS="layer1=https://.../health,layer2=https://.../health"
  REQUIRED_REMOTE_SERVICE_NAMES=layer1,layer2,layer3,layer4,layer5,layer6,postgres,redis,neo4j,minio
  LIVE_ENVIRONMENT_NAME=bunnyshell-fabric-live
  RELEASE_CANDIDATE_SHA=<full-sha>
  HEALTH_TIMEOUT_SECONDS=360
  RUN_LIVE_SEED=true|false
  RUN_LIVE_PLAYWRIGHT=true|false
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config-only)
      CONFIG_ONLY="true"
      START_STACK="false"
      ;;
    --smoke)
      SMOKE_MODE="true"
      ;;
    --no-start)
      START_STACK="false"
      ;;
    --remote)
      START_STACK="false"
      REMOTE_STACK="true"
      ;;
    --seed)
      RUN_LIVE_SEED="true"
      ;;
    --playwright)
      RUN_LIVE_PLAYWRIGHT="true"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

mkdir -p "$ARTIFACT_DIR"
LOG_FILE="$ARTIFACT_DIR/live-workflow-validation.log"
SUMMARY_FILE="$ARTIFACT_DIR/live-workflow-validation-summary.md"
SUMMARY_JSON_FILE="$ARTIFACT_DIR/live-workflow-validation-summary.json"
ARTIFACT_MANIFEST_FILE="$ARTIFACT_DIR/artifact-manifest.json"
COMPOSE_CONFIG_FILE="$ARTIFACT_DIR/docker-compose.live.resolved.yml"
CONTAINER_STATUS_FILE="$ARTIFACT_DIR/container-status.txt"
HEALTH_STATUS_FILE="$ARTIFACT_DIR/container-health.jsonl"
ENDPOINT_PROBES_FILE="$ARTIFACT_DIR/endpoint-probes.tsv"
ENVIRONMENT_METADATA_FILE="$ARTIFACT_DIR/redacted-environment-metadata.json"
SERVICE_LOG_DIR="$ARTIFACT_DIR/service-logs"
SEED_REPORT_JSON="$ARTIFACT_DIR/seed-report.json"
PLAYWRIGHT_ARTIFACT_DIR="$ARTIFACT_DIR/playwright"
PLAYWRIGHT_HTML_REPORT="$PLAYWRIGHT_ARTIFACT_DIR/html"
PLAYWRIGHT_JUNIT_FILE="$PLAYWRIGHT_ARTIFACT_DIR/junit.xml"

exec > >(tee "$LOG_FILE") 2>&1

cd "$ROOT_DIR"

services=(postgres redis neo4j minio layer1 layer2 layer3 layer4 layer5 layer6 frontend)
remote_service_names=()
remote_service_urls=()

section() {
  printf '\n## %s\n' "$1"
}

sanitize_stream() {
  perl -pe '
    s#(postgresql|postgres|mysql|redis|mongodb)://[^\s@]+:[^\s@]+@#$1://[REDACTED]@#ig;
    s#(Authorization:\s*)\S+#$1[REDACTED]#ig;
    s#((?:password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)\s*[=:]\s*)\S+#$1[REDACTED]#ig;
    s#(^\s*[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY)[A-Z0-9_]*:\s*)\S+#$1[REDACTED]#ig;
  '
}

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\r'/}"
  value="${value//$'\n'/\\n}"
  printf '%s' "$value"
}

json_bool_file_exists() {
  if [[ -e "$1" ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

write_minimal_summary_without_node() {
  local status="$1"
  local detail="$2"
  local escaped_status escaped_detail generated_at
  FINALIZED="true"
  escaped_status="$(json_escape "$status")"
  escaped_detail="$(json_escape "$detail")"
  generated_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || printf '')"

  cat > "$SUMMARY_FILE" <<SUMMARY
# Live Workflow Validation Summary

| Field | Value |
| --- | --- |
| status | ${status} |
| detail | ${detail} |
| compose_file | ${COMPOSE_FILE} |
| frontend_url | ${FRONTEND_URL} |
| backend_url | ${BACKEND_URL} |
| log_file | ${LOG_FILE} |
| summary_json | ${SUMMARY_JSON_FILE} |
| artifact_manifest | ${ARTIFACT_MANIFEST_FILE} |

SUMMARY

  cat > "$ARTIFACT_MANIFEST_FILE" <<JSON
{
  "generatedAt": "$(json_escape "$generated_at")",
  "status": "${escaped_status}",
  "artifactRoot": "$(json_escape "$ARTIFACT_DIR")",
  "entries": []
}
JSON

  cat > "$SUMMARY_JSON_FILE" <<JSON
{
  "generatedAt": "$(json_escape "$generated_at")",
  "status": "${escaped_status}",
  "detail": "${escaped_detail}",
  "composeFile": "$(json_escape "$COMPOSE_FILE")",
  "frontendUrl": "$(json_escape "$FRONTEND_URL")",
  "backendUrl": "$(json_escape "$BACKEND_URL")",
  "artifacts": {
    "markdownSummary": "$(json_escape "$SUMMARY_FILE")",
    "jsonSummary": "$(json_escape "$SUMMARY_JSON_FILE")",
    "manifest": "$(json_escape "$ARTIFACT_MANIFEST_FILE")",
    "log": "$(json_escape "$LOG_FILE")"
  },
  "artifactPresence": {
    "markdownSummary": $(json_bool_file_exists "$SUMMARY_FILE"),
    "jsonSummary": true,
    "manifest": $(json_bool_file_exists "$ARTIFACT_MANIFEST_FILE"),
    "log": $(json_bool_file_exists "$LOG_FILE")
  }
}
JSON
}

write_environment_metadata() {
  export VALIDATION_MODE="$([[ "$REMOTE_STACK" == "true" ]] && echo remote-live || echo compose-live)"
  export ENVIRONMENT_METADATA_FILE
  export LIVE_ENVIRONMENT_NAME
  export RELEASE_CANDIDATE_SHA
  export FRONTEND_URL
  export BACKEND_URL
  export RUN_LIVE_SEED
  export RUN_LIVE_PLAYWRIGHT
  export REQUIRED_REMOTE_SERVICE_NAMES
  export REMOTE_SERVICE_NAMES="${remote_service_names[*]:-}"
  export GITHUB_RUN_ID="${GITHUB_RUN_ID:-}"
  export GITHUB_RUN_ATTEMPT="${GITHUB_RUN_ATTEMPT:-}"
  export GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-}"
  export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-}"
  "$NODE_BIN" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const githubRunUrl = process.env.GITHUB_RUN_ID && process.env.GITHUB_SERVER_URL && process.env.GITHUB_REPOSITORY
  ? `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`
  : '';
const splitList = (value) => (value || '').split(/[\s,]+/).map((item) => item.trim()).filter(Boolean);
const payload = {
  generatedAt: new Date().toISOString(),
  validationMode: process.env.VALIDATION_MODE,
  liveEnvironmentName: process.env.LIVE_ENVIRONMENT_NAME || '',
  releaseCandidateSha: process.env.RELEASE_CANDIDATE_SHA || '',
  githubRunUrl,
  githubRunAttempt: process.env.GITHUB_RUN_ATTEMPT || '',
  frontendUrl: process.env.FRONTEND_URL,
  backendUrl: process.env.BACKEND_URL,
  seedRequested: process.env.RUN_LIVE_SEED === 'true',
  playwrightRequested: process.env.RUN_LIVE_PLAYWRIGHT === 'true',
  mocksDisabled: true,
  mockFlags: {
    VITE_USE_MOCKS: 'false',
    VITE_ENABLE_MOCK_FALLBACK: 'false',
  },
  requiredRemoteServiceNames: splitList(process.env.REQUIRED_REMOTE_SERVICE_NAMES),
  configuredRemoteServiceNames: splitList(process.env.REMOTE_SERVICE_NAMES),
};
fs.mkdirSync(path.dirname(process.env.ENVIRONMENT_METADATA_FILE), { recursive: true });
fs.writeFileSync(process.env.ENVIRONMENT_METADATA_FILE, `${JSON.stringify(payload, null, 2)}
`);
NODE
}

parse_remote_service_health_urls() {
  remote_service_names=()
  remote_service_urls=()
  if [[ -z "$LIVE_SERVICE_HEALTH_URLS" ]]; then
    fail "BLOCKED" "LIVE_SERVICE_HEALTH_URLS is required in --remote mode"
  fi

  local entry name url
  while IFS= read -r entry; do
    entry="${entry#"${entry%%[![:space:]]*}"}"
    entry="${entry%"${entry##*[![:space:]]}"}"
    [[ -z "$entry" ]] && continue
    if [[ "$entry" != *=* ]]; then
      fail "BLOCKED" "remote service health entry must use name=url format: $entry"
    fi
    name="${entry%%=*}"
    url="${entry#*=}"
    if [[ -z "$name" || -z "$url" ]]; then
      fail "BLOCKED" "remote service health entry must include non-empty name and URL: $entry"
    fi
    if [[ ! "$url" =~ ^https?:// ]]; then
      fail "BLOCKED" "remote service health URL for $name must be http(s): $url"
    fi
    remote_service_names+=("$name")
    remote_service_urls+=("$url")
  done < <(printf '%s\n' "$LIVE_SERVICE_HEALTH_URLS" | tr ',' '\n')

  local required found candidate
  while IFS= read -r required; do
    required="${required#"${required%%[![:space:]]*}"}"
    required="${required%"${required##*[![:space:]]}"}"
    [[ -z "$required" ]] && continue
    found="false"
    for candidate in "${remote_service_names[@]}"; do
      if [[ "$candidate" == "$required" ]]; then
        found="true"
        break
      fi
    done
    if [[ "$found" != "true" ]]; then
      fail "BLOCKED" "required remote service health URL is missing: $required"
    fi
  done < <(printf '%s\n' "$REQUIRED_REMOTE_SERVICE_NAMES" | tr ',' '\n')
}

write_summary() {
  local status="$1"
  local detail="$2"
  if ! node_bin_available; then
    write_minimal_summary_without_node "$status" "$detail"
    return
  fi

  FINALIZED="true"
  cat > "$SUMMARY_FILE" <<SUMMARY
# Live Workflow Validation Summary

| Field | Value |
| --- | --- |
| status | ${status} |
| detail | ${detail} |
| compose_file | ${COMPOSE_FILE} |
| frontend_url | ${FRONTEND_URL} |
| backend_url | ${BACKEND_URL} |
| seed_requested | ${RUN_LIVE_SEED} |
| playwright_requested | ${RUN_LIVE_PLAYWRIGHT} |
| log_file | ${LOG_FILE} |
| summary_json | ${SUMMARY_JSON_FILE} |
| artifact_manifest | ${ARTIFACT_MANIFEST_FILE} |
| compose_config | ${COMPOSE_CONFIG_FILE} |
| container_status | ${CONTAINER_STATUS_FILE} |
| health_status | ${HEALTH_STATUS_FILE} |
| endpoint_probes | ${ENDPOINT_PROBES_FILE} |
| environment_metadata | ${ENVIRONMENT_METADATA_FILE} |
| service_logs | ${SERVICE_LOG_DIR} |
| seed_report_json | ${SEED_REPORT_JSON} |
| playwright_artifacts | ${PLAYWRIGHT_ARTIFACT_DIR} |

SUMMARY
  write_environment_metadata
  write_machine_summary "$status" "$detail"
  write_artifact_manifest "$status"
  # Refresh after manifest generation so required artifactPresence flags reflect the final evidence set.
  write_machine_summary "$status" "$detail"
}

write_machine_summary() {
  local status="$1"
  local detail="$2"
  export STATUS="$status"
  export DETAIL="$detail"
  export SUMMARY_JSON_FILE
  export LOG_FILE
  export SUMMARY_FILE
  export ARTIFACT_MANIFEST_FILE
  export COMPOSE_FILE
  export COMPOSE_CONFIG_FILE
  export CONTAINER_STATUS_FILE
  export HEALTH_STATUS_FILE
  export ENDPOINT_PROBES_FILE
  export ENVIRONMENT_METADATA_FILE
  export SERVICE_LOG_DIR
  export SEED_REPORT_JSON
  export PLAYWRIGHT_ARTIFACT_DIR
  export FRONTEND_URL
  export BACKEND_URL
  export RUN_LIVE_SEED
  export RUN_LIVE_PLAYWRIGHT
  "$NODE_BIN" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const exists = (p) => Boolean(p) && fs.existsSync(p);
const payload = {
  generatedAt: new Date().toISOString(),
  status: process.env.STATUS,
  detail: process.env.DETAIL,
  composeFile: process.env.COMPOSE_FILE,
  frontendUrl: process.env.FRONTEND_URL,
  backendUrl: process.env.BACKEND_URL,
  seedRequested: process.env.RUN_LIVE_SEED === 'true',
  playwrightRequested: process.env.RUN_LIVE_PLAYWRIGHT === 'true',
  artifacts: {
    markdownSummary: process.env.SUMMARY_FILE,
    jsonSummary: process.env.SUMMARY_JSON_FILE,
    manifest: process.env.ARTIFACT_MANIFEST_FILE,
    log: process.env.LOG_FILE,
    composeConfig: process.env.COMPOSE_CONFIG_FILE,
    containerStatus: process.env.CONTAINER_STATUS_FILE,
    healthStatus: process.env.HEALTH_STATUS_FILE,
    endpointProbes: process.env.ENDPOINT_PROBES_FILE,
    environmentMetadata: process.env.ENVIRONMENT_METADATA_FILE,
    serviceLogs: process.env.SERVICE_LOG_DIR,
    seedReportJson: process.env.SEED_REPORT_JSON,
    playwrightArtifacts: process.env.PLAYWRIGHT_ARTIFACT_DIR,
  },
  artifactPresence: {
    markdownSummary: exists(process.env.SUMMARY_FILE),
    jsonSummary: exists(process.env.SUMMARY_JSON_FILE),
    manifest: exists(process.env.ARTIFACT_MANIFEST_FILE),
    log: exists(process.env.LOG_FILE),
    composeConfig: exists(process.env.COMPOSE_CONFIG_FILE),
    containerStatus: exists(process.env.CONTAINER_STATUS_FILE),
    healthStatus: exists(process.env.HEALTH_STATUS_FILE),
    endpointProbes: exists(process.env.ENDPOINT_PROBES_FILE),
    environmentMetadata: exists(process.env.ENVIRONMENT_METADATA_FILE),
    seedReportJson: exists(process.env.SEED_REPORT_JSON),
    playwrightArtifacts: exists(process.env.PLAYWRIGHT_ARTIFACT_DIR),
  },
};
fs.mkdirSync(path.dirname(process.env.SUMMARY_JSON_FILE), { recursive: true });
fs.writeFileSync(process.env.SUMMARY_JSON_FILE, `${JSON.stringify(payload, null, 2)}
`);
NODE
}

write_artifact_manifest() {
  local status="$1"
  export STATUS="$status"
  export ARTIFACT_DIR
  export ARTIFACT_MANIFEST_FILE
  "$NODE_BIN" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.ARTIFACT_DIR;
const entries = [];
// Ensure the manifest can include itself when the artifact set is walked.
fs.mkdirSync(path.dirname(process.env.ARTIFACT_MANIFEST_FILE), { recursive: true });
if (!fs.existsSync(process.env.ARTIFACT_MANIFEST_FILE)) {
  fs.writeFileSync(process.env.ARTIFACT_MANIFEST_FILE, '');
}
function walk(dir) {
  if (!fs.existsSync(dir)) return;
  for (const name of fs.readdirSync(dir).sort()) {
    const abs = path.join(dir, name);
    const rel = path.relative(root, abs) || '.';
    const stat = fs.statSync(abs);
    entries.push({ path: rel, type: stat.isDirectory() ? 'directory' : 'file', bytes: stat.isFile() ? stat.size : 0 });
    if (stat.isDirectory()) walk(abs);
  }
}
walk(root);
const payload = { generatedAt: new Date().toISOString(), status: process.env.STATUS, artifactRoot: root, entries };
fs.writeFileSync(process.env.ARTIFACT_MANIFEST_FILE, `${JSON.stringify(payload, null, 2)}
`);
NODE
}

compose_ps_safe() {
  docker-compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" ps 2>&1 | sanitize_stream || true
}

probe_endpoint() {
  local name="$1"
  local url="$2"
  local output_file="$3"
  local code
  code="$(curl -k -L -sS -o "$output_file" -w '%{http_code}' --max-time 15 "$url" 2>>"$ARTIFACT_DIR/curl-errors.log" || true)"
  if [[ -z "$code" ]]; then
    code="000"
  fi
  printf '%s\t%s\t%s\n' "$name" "$url" "$code" >> "$ENDPOINT_PROBES_FILE"
  [[ "$code" =~ ^2|3[0-9][0-9]$ ]]
}

collect_remote_evidence() {
  local reason="$1"
  mkdir -p "$SERVICE_LOG_DIR"
  {
    echo "# Remote Live Stack Status"
    echo "reason=$reason"
    echo "mode=remote-live"
    echo "environment=${LIVE_ENVIRONMENT_NAME:-unknown}"
    echo "release_candidate_sha=${RELEASE_CANDIDATE_SHA:-unknown}"
    echo "docker_compose=not-used"
  } > "$CONTAINER_STATUS_FILE"

  : > "$HEALTH_STATUS_FILE"
  if [[ -f "$ENDPOINT_PROBES_FILE" ]]; then
    awk -F '\t' 'NR > 1 { printf("{\"service\":\"%s\",\"url\":\"%s\",\"state\":\"http_%s\"}\n", $1, $2, $3) }' "$ENDPOINT_PROBES_FILE" >> "$HEALTH_STATUS_FILE"
  fi

  {
    echo "Remote Bunnyshell/live validation does not have local docker logs."
    echo "Retain Bunnyshell deployment logs or provider logs alongside this artifact bundle."
  } > "$SERVICE_LOG_DIR/remote-live-stack.log"
}

collect_evidence() {
  local reason="$1"
  section "evidence collection: $reason"
  if [[ "$REMOTE_STACK" == "true" ]]; then
    collect_remote_evidence "$reason"
    echo "remote evidence artifacts written under $ARTIFACT_DIR"
    return
  fi
  mkdir -p "$SERVICE_LOG_DIR"
  {
    echo "# Container Status"
    echo "reason=$reason"
    compose_ps_safe
  } > "$CONTAINER_STATUS_FILE"

  : > "$HEALTH_STATUS_FILE"
  for service in "${services[@]}"; do
    local cid state
    cid="$(docker-compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || true)"
    if [[ -z "$cid" ]]; then
      printf '{"service":"%s","container_id":"","state":"missing"}\n' "$service" >> "$HEALTH_STATUS_FILE"
      continue
    fi
    state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo inspect-failed)"
    printf '{"service":"%s","container_id":"%s","state":"%s"}\n' "$service" "$cid" "$state" >> "$HEALTH_STATUS_FILE"
    docker logs --tail 160 "$cid" 2>&1 | sanitize_stream > "$SERVICE_LOG_DIR/${service}.log" || true
  done

  : > "$ENDPOINT_PROBES_FILE"
  printf 'name\turl\tstatus_code\n' > "$ENDPOINT_PROBES_FILE"
  probe_endpoint frontend "$FRONTEND_URL" "$ARTIFACT_DIR/frontend-probe.html" || true
  probe_endpoint backend_health "$BACKEND_URL/health" "$ARTIFACT_DIR/backend-health.json" || true

  echo "evidence artifacts written under $ARTIFACT_DIR"
}

fail() {
  local status="$1"
  local detail="$2"
  echo "ERROR: $detail" >&2
  if [[ "$CONFIG_ONLY" != "true" ]]; then
    collect_evidence "$detail"
  fi
  write_summary "$status" "$detail"
  exit 1
}

on_unhandled_error() {
  local exit_code="$?"
  local line_no="$1"
  if [[ "$FINALIZED" != "true" ]]; then
    if [[ "$CONFIG_ONLY" != "true" ]]; then
      collect_evidence "unhandled error at line $line_no"
    fi
    write_summary "FAIL" "unhandled error at line $line_no; exit code $exit_code"
  fi
  exit "$exit_code"
}
trap 'on_unhandled_error $LINENO' ERR

if [[ "${VITE_USE_MOCKS:-false}" =~ ^(1|true|yes|on)$ ]] || [[ "${VITE_ENABLE_MOCK_FALLBACK:-false}" =~ ^(1|true|yes|on)$ ]]; then
  fail "FAIL" "mock flags must not be enabled for live workflow validation"
fi

section "tooling"
if [[ "$REMOTE_STACK" == "true" ]]; then
  echo "remote live validation mode enabled; docker-compose container inspection is skipped"
else
  command -v docker-compose >/dev/null || fail "BLOCKED" "docker-compose is required in this validation environment"
  docker-compose --version
fi
node_bin_available || fail "BLOCKED" "node is required in this validation environment"
"$NODE_BIN" --version
pnpm --version || true

section "frontend guardrails"
(
  cd apps/web
  export PLAYWRIGHT_LIVE_MODE=true
  export PLAYWRIGHT_LIVE_FRONTEND_URL="$FRONTEND_URL"
  export PLAYWRIGHT_BACKEND_URL="$BACKEND_URL"
  export VITE_USE_MOCKS=false
  export VITE_ENABLE_MOCK_FALLBACK=false
  "$NODE_BIN" scripts/live-env-guard.mjs test
)

section "compose config"
if [[ "$REMOTE_STACK" == "true" ]]; then
  {
    echo "# Remote live validation mode"
    echo "# docker-compose config is not used for this run."
    echo "remote_live_validation: true"
    echo "frontend_url: ${FRONTEND_URL}"
    echo "backend_url: ${BACKEND_URL}"
  } > "$COMPOSE_CONFIG_FILE"
  echo "remote validation metadata saved to $COMPOSE_CONFIG_FILE"
else
  docker-compose -f "$COMPOSE_FILE" config | sanitize_stream > "$COMPOSE_CONFIG_FILE"
  echo "resolved compose saved to $COMPOSE_CONFIG_FILE"
fi

if [[ "$CONFIG_ONLY" == "true" ]]; then
  write_summary "PASS" "compose config and frontend live guardrails passed"
  echo "config-only validation completed"
  exit 0
fi

if [[ "$REMOTE_STACK" == "true" ]]; then
  section "remote service URL preflight"
  parse_remote_service_health_urls
  echo "configured remote service health checks: ${remote_service_names[*]}"
elif [[ "$START_STACK" == "true" ]]; then
  section "stack startup"
  docker-compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build
else
  section "stack startup skipped"
  echo "probing currently running containers"
fi

if [[ "$REMOTE_STACK" != "true" ]]; then
  section "health wait"
  deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    unhealthy=()
    for service in "${services[@]}"; do
      cid="$(docker-compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || true)"
      if [[ -z "$cid" ]]; then
        unhealthy+=("$service:missing")
        continue
      fi
      state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo inspect-failed)"
      if [[ "$state" != "healthy" && "$state" != "running" ]]; then
        unhealthy+=("$service:$state")
      fi
    done
    if [[ ${#unhealthy[@]} -eq 0 ]]; then
      echo "all required services are healthy/running"
      break
    fi
    echo "waiting for services: ${unhealthy[*]}"
    sleep 10
  done

  if (( SECONDS >= deadline )); then
    section "container status"
    compose_ps_safe || true
    fail "BLOCKED" "timed out waiting for live stack health"
  fi
fi

section "endpoint probes"
: > "$ENDPOINT_PROBES_FILE"
printf 'name\turl\tstatus_code\n' > "$ENDPOINT_PROBES_FILE"
probe_endpoint frontend "$FRONTEND_URL" "$ARTIFACT_DIR/frontend-probe.html" || fail "FAIL" "frontend probe failed at $FRONTEND_URL"
probe_endpoint backend_health "$BACKEND_URL/health" "$ARTIFACT_DIR/backend-health.json" || fail "FAIL" "backend health probe failed at $BACKEND_URL/health"
if [[ "$REMOTE_STACK" == "true" ]]; then
  for index in "${!remote_service_names[@]}"; do
    probe_endpoint "${remote_service_names[$index]}" "${remote_service_urls[$index]}" "$ARTIFACT_DIR/remote-${remote_service_names[$index]}-probe.json" || fail "FAIL" "remote service probe failed for ${remote_service_names[$index]} at ${remote_service_urls[$index]}"
  done
fi
cat "$ENDPOINT_PROBES_FILE"

if [[ "$RUN_LIVE_SEED" == "true" ]]; then
  section "live seed"
  if [[ "$REMOTE_STACK" == "true" ]]; then
    (
      cd apps/web
      PLAYWRIGHT_LIVE_MODE=true \
      PLAYWRIGHT_BACKEND_URL="$BACKEND_URL" \
      SEED_REPORT_JSON="$SEED_REPORT_JSON" \
      SEED_STRICT=true \
      VITE_USE_MOCKS=false \
      VITE_ENABLE_MOCK_FALLBACK=false \
      pnpm run seed:live
    )
  else
    docker-compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" --profile seed run --rm \
      -e SEED_REPORT_JSON=/artifacts/seed-report.json \
      -e SEED_STRICT=true \
      -v "$ARTIFACT_DIR:/artifacts" \
      live-seed
  fi
fi

if [[ "$RUN_LIVE_PLAYWRIGHT" == "true" ]]; then
  section "live playwright p0"
  mkdir -p "$PLAYWRIGHT_ARTIFACT_DIR"
  (
    cd apps/web
    PLAYWRIGHT_LIVE_MODE=true \
    PLAYWRIGHT_LIVE_FRONTEND_URL="$FRONTEND_URL" \
    PLAYWRIGHT_BACKEND_URL="$BACKEND_URL" \
    PLAYWRIGHT_HTML_REPORT="$PLAYWRIGHT_HTML_REPORT" \
    PLAYWRIGHT_JUNIT_FILE="$PLAYWRIGHT_JUNIT_FILE" \
    PLAYWRIGHT_OUTPUT_DIR="$PLAYWRIGHT_ARTIFACT_DIR/test-results" \
    VITE_USE_MOCKS=false \
    VITE_ENABLE_MOCK_FALLBACK=false \
    pnpm run test:e2e:live:p0
  )

  [[ -f "$PLAYWRIGHT_HTML_REPORT/index.html" ]] || fail "FAIL" "Playwright HTML report is missing at $PLAYWRIGHT_HTML_REPORT/index.html"
  [[ -f "$PLAYWRIGHT_JUNIT_FILE" ]] || fail "FAIL" "Playwright JUnit report is missing at $PLAYWRIGHT_JUNIT_FILE"
  if ! find "$PLAYWRIGHT_ARTIFACT_DIR/test-results" -type f -name '*.zip' -print -quit 2>/dev/null | grep -q .; then
    fail "FAIL" "Playwright live trace artifact is missing under $PLAYWRIGHT_ARTIFACT_DIR/test-results"
  fi
fi

if [[ "$SMOKE_MODE" == "true" ]]; then
  section "smoke evidence artifact"
  SMOKE_EVIDENCE_FILE="$ARTIFACT_DIR/live-stack-smoke-evidence-${RELEASE_CANDIDATE_SHA:-unknown}.json"
  export ENDPOINT_PROBES_FILE
  export HEALTH_STATUS_FILE
  export RELEASE_CANDIDATE_SHA="${RELEASE_CANDIDATE_SHA:-}"
  export COMPOSE_FILE
  export FRONTEND_URL
  export BACKEND_URL
  export SMOKE_EVIDENCE_FILE
  "$NODE_BIN" <<'SMOKE_NODE'
const fs = require('node:fs');
const path = require('node:path');
const probesFile = process.env.ENDPOINT_PROBES_FILE;
const healthFile = process.env.HEALTH_STATUS_FILE;
const probes = [];
if (fs.existsSync(probesFile)) {
  const lines = fs.readFileSync(probesFile, 'utf8').trim().split('\n').slice(1);
  for (const line of lines) {
    const [name, url, status_code] = line.split('\t');
    if (name) probes.push({ name, url, status_code: parseInt(status_code, 10) || 0 });
  }
}
const containerHealth = [];
if (fs.existsSync(healthFile)) {
  const lines = fs.readFileSync(healthFile, 'utf8').trim().split('\n').filter(Boolean);
  for (const line of lines) {
    try { containerHealth.push(JSON.parse(line)); } catch (_) {}
  }
}
const allProbesPass = probes.length > 0 && probes.every(p => p.status_code >= 200 && p.status_code < 400);
const allContainersHealthy = containerHealth.length > 0 && containerHealth.every(c => c.state === 'healthy' || c.state === 'running');
const payload = {
  generatedAt: new Date().toISOString(),
  mode: 'smoke',
  releaseCandidateSha: process.env.RELEASE_CANDIDATE_SHA || 'unknown',
  composeFile: process.env.COMPOSE_FILE,
  frontendUrl: process.env.FRONTEND_URL,
  backendUrl: process.env.BACKEND_URL,
  endpointProbes: probes,
  containerHealth,
  allProbesPass,
  allContainersHealthy,
  result: allProbesPass && allContainersHealthy ? 'PASS' : 'FAIL',
};
fs.mkdirSync(path.dirname(process.env.SMOKE_EVIDENCE_FILE), { recursive: true });
fs.writeFileSync(process.env.SMOKE_EVIDENCE_FILE, JSON.stringify(payload, null, 2) + '\n');
console.log('smoke evidence written to ' + process.env.SMOKE_EVIDENCE_FILE);
console.log('result: ' + payload.result);
SMOKE_NODE

  section "smoke teardown"
  docker-compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" down --volumes --remove-orphans 2>&1 | sanitize_stream || true
  echo "live stack torn down"
fi

collect_evidence "successful validation"
write_summary "PASS" "live stack health probes passed; seed/playwright statuses reflect requested options"
section "summary"
cat "$SUMMARY_FILE"
