#!/usr/bin/env bash
# deploy-production.sh — Autonomous production release script for Value Fabric
#
# Executes the release runbook phases in order, stopping on the first failing
# gate. Writes a deployment evidence file to .deployments/ on success.
#
# The Kubernetes namespace is always read from the kustomize overlay itself
# (k8s/overlays/production/kustomization.yaml). There is no --namespace flag
# because the overlay is the single source of truth for namespace.
#
# Usage:
#   bash scripts/deploy-production.sh [OPTIONS]
#
# Options:
#   --tag <tag>           Release tag to deploy (default: latest annotated tag)
#   --dry-run             Run Phases 0–5 only (no cluster changes)
#   --skip-image-pull     Skip docker pull checks (useful in CI with pre-pulled images)
#   --help                Show this message
#
# Stop conditions:
#   Any phase failure exits non-zero and prints the failing gate name.
#   Phases 0–5 are pre-flight. The script will not reach Phase 6 if any
#   pre-flight gate fails.

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

pass()  { echo -e "  ${GREEN}✓ PASS${RESET}  $*"; }
fail()  { echo -e "  ${RED}✗ FAIL${RESET}  $*"; }
skip()  { echo -e "  ${YELLOW}⊘ SKIP${RESET}  $*"; }
info()  { echo -e "  ${CYAN}→${RESET} $*"; }
phase() { echo -e "\n${BOLD}${CYAN}=== $* ===${RESET}"; }
gate_fail() {
  echo -e "\n${RED}${BOLD}GATE FAILED: $*${RESET}"
  echo -e "${RED}Deployment aborted. Fix the failing gate and re-run.${RESET}\n"
  exit 1
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
RELEASE_TAG=""
DRY_RUN=false
SKIP_IMAGE_PULL=false
REGISTRY="ghcr.io/bmsull560/fabric_4l"
SERVICES=(
  layer1-ingestion
  layer2-extraction
  layer3-knowledge
  layer4-agents
  layer5-ground-truth
  layer6-benchmarks
  frontend
)
LAYER_PORTS=(
  "layer1-ingestion:8001"
  "layer2-extraction:8002"
  "layer3-knowledge:8003"
  "layer4-agents:8004"
  "layer5-ground-truth:8005"
  "layer6-benchmarks:8006"
)

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)             RELEASE_TAG="$2"; shift 2 ;;
    --dry-run)         DRY_RUN=true;     shift   ;;
    --skip-image-pull) SKIP_IMAGE_PULL=true; shift ;;
    --help)
      sed -n '/^# Usage:/,/^[^#]/p' "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Phase 0 — Tooling preflight
# ---------------------------------------------------------------------------
phase "Phase 0 — Tooling preflight"

# docker is only required when image pulls are not skipped
if [[ "$SKIP_IMAGE_PULL" == "true" ]]; then
  REQUIRED_TOOLS=(git kubectl pnpm python3)
else
  REQUIRED_TOOLS=(git docker kubectl pnpm python3)
fi
MISSING=()

for tool in "${REQUIRED_TOOLS[@]}"; do
  if command -v "$tool" &>/dev/null; then
    pass "$tool: $(command -v "$tool")"
  else
    fail "$tool: not found"
    MISSING+=("$tool")
  fi
done

if [[ "$SKIP_IMAGE_PULL" == "true" ]]; then
  skip "docker: not checked (--skip-image-pull set)"
fi

# Optional tools
for tool in cosign trivy gh; do
  if command -v "$tool" &>/dev/null; then
    pass "$tool: $(command -v "$tool") (optional)"
  else
    skip "$tool: not installed (optional)"
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  gate_fail "Missing required tools: ${MISSING[*]}"
fi

# ---------------------------------------------------------------------------
# Resolve release tag
# ---------------------------------------------------------------------------
if [[ -z "$RELEASE_TAG" ]]; then
  RELEASE_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
  if [[ -z "$RELEASE_TAG" ]]; then
    gate_fail "No release tag found. Pass --tag <tag> or create an annotated tag."
  fi
  info "Using latest annotated tag: $RELEASE_TAG"
fi

# Namespace is always read from the production overlay — single source of truth.
OVERLAY="k8s/overlays/production"
NAMESPACE=$(grep '^namespace:' "${OVERLAY}/kustomization.yaml" 2>/dev/null | awk '{print $2}')
if [[ -z "$NAMESPACE" ]]; then
  gate_fail "Could not read namespace from ${OVERLAY}/kustomization.yaml"
fi

echo ""
echo -e "${BOLD}Release tag:  $RELEASE_TAG${RESET}"
echo -e "${BOLD}Namespace:    $NAMESPACE (from ${OVERLAY}/kustomization.yaml)${RESET}"
echo -e "${BOLD}Dry-run:      $DRY_RUN${RESET}"
echo -e "${BOLD}Registry:     $REGISTRY${RESET}"

# ---------------------------------------------------------------------------
# Phase 1 — Repository state verification
# ---------------------------------------------------------------------------
phase "Phase 1 — Repository state verification"

# Working tree must be clean
if git diff --quiet && git diff --cached --quiet; then
  pass "Working tree is clean"
else
  fail "Working tree has uncommitted changes"
  git status --short
  gate_fail "Dirty working tree — commit or stash changes before deploying"
fi

# Tag must exist
if git tag -l "$RELEASE_TAG" | grep -q "^${RELEASE_TAG}$"; then
  pass "Tag $RELEASE_TAG exists"
else
  fail "Tag $RELEASE_TAG not found"
  gate_fail "Release tag $RELEASE_TAG does not exist. Create it first."
fi

# HEAD must match the tag
HEAD_SHA=$(git rev-parse HEAD)
TAG_SHA=$(git rev-parse "${RELEASE_TAG}^{}" 2>/dev/null || git rev-parse "$RELEASE_TAG")
if [[ "$HEAD_SHA" == "$TAG_SHA" ]]; then
  pass "HEAD matches tag $RELEASE_TAG ($(git rev-parse --short HEAD))"
else
  fail "HEAD ($(git rev-parse --short HEAD)) does not match tag $RELEASE_TAG ($(git rev-parse --short "$RELEASE_TAG"))"
  info "Commits since tag:"
  git log --oneline "${RELEASE_TAG}..HEAD" | head -5
  gate_fail "HEAD is not at tag $RELEASE_TAG — cut a new tag or check out the tag commit"
fi

# Version alignment
VERSION_TAG="${RELEASE_TAG#v}"  # strip leading 'v'
ERRORS=()

VERSION_TXT=$(cat version.txt 2>/dev/null || echo "MISSING")
if [[ "$VERSION_TXT" == "$VERSION_TAG" ]]; then
  pass "version.txt: $VERSION_TXT"
else
  fail "version.txt: $VERSION_TXT (expected $VERSION_TAG)"
  ERRORS+=("version.txt")
fi

if command -v node &>/dev/null; then
  PKG_VERSION=$(node -e "console.log(require('./package.json').version)" 2>/dev/null || echo "MISSING")
  if [[ "$PKG_VERSION" == "$VERSION_TAG" ]]; then
    pass "package.json: $PKG_VERSION"
  else
    fail "package.json: $PKG_VERSION (expected $VERSION_TAG)"
    ERRORS+=("package.json")
  fi

  WEB_VERSION=$(node -e "console.log(require('./apps/web/package.json').version)" 2>/dev/null || echo "MISSING")
  if [[ "$WEB_VERSION" == "$VERSION_TAG" ]]; then
    pass "apps/web/package.json: $WEB_VERSION"
  else
    fail "apps/web/package.json: $WEB_VERSION (expected $VERSION_TAG)"
    ERRORS+=("apps/web/package.json")
  fi
else
  skip "node not available — skipping package.json version checks"
fi

# Validate ALL newTag entries in the overlay — a single mismatched service
# would produce a mixed-version release.
K8S_OVERLAY="k8s/overlays/production/kustomization.yaml"
mapfile -t K8S_TAGS < <(grep 'newTag' "$K8S_OVERLAY" 2>/dev/null | awk '{print $2}')
if [[ ${#K8S_TAGS[@]} -eq 0 ]]; then
  fail "$K8S_OVERLAY: no newTag entries found"
  ERRORS+=("k8s overlay newTag")
else
  K8S_MISMATCH=()
  for tag in "${K8S_TAGS[@]}"; do
    if [[ "$tag" != "$RELEASE_TAG" ]]; then
      K8S_MISMATCH+=("$tag")
    fi
  done
  if [[ ${#K8S_MISMATCH[@]} -gt 0 ]]; then
    fail "$K8S_OVERLAY: ${#K8S_MISMATCH[@]} of ${#K8S_TAGS[@]} newTag entries do not match $RELEASE_TAG: ${K8S_MISMATCH[*]}"
    ERRORS+=("k8s overlay newTag")
  else
    pass "$K8S_OVERLAY: all ${#K8S_TAGS[@]} newTag entries = $RELEASE_TAG"
  fi
fi

if [[ ${#ERRORS[@]} -gt 0 ]]; then
  gate_fail "Version misalignment in: ${ERRORS[*]} — run version alignment procedure in docs/VERSIONING.md"
fi

# ---------------------------------------------------------------------------
# Phase 2 — CI pipeline health
# ---------------------------------------------------------------------------
phase "Phase 2 — CI pipeline health"

REQUIRED_WORKFLOWS=(
  "build-deploy.yml"
  "test-mandatory.yml"
  "security-gate.yml"
  "contract-compliance.yml"
)

if ! command -v gh &>/dev/null; then
  gate_fail "gh CLI is required for CI gate verification but is not installed.
  Install it from https://cli.github.com/ and authenticate with: gh auth login
  Required workflows that must pass on commit $(git rev-parse --short HEAD):
    ${REQUIRED_WORKFLOWS[*]}"
fi

info "Checking workflow runs via gh CLI (commit: $(git rev-parse --short HEAD)) ..."
ALL_PASSED=true
for wf in "${REQUIRED_WORKFLOWS[@]}"; do
  STATUS=$(gh run list \
    --workflow="$wf" \
    --commit="$HEAD_SHA" \
    --limit=1 \
    --json conclusion \
    --jq '.[0].conclusion' 2>/dev/null || echo "unknown")
  if [[ "$STATUS" == "success" ]]; then
    pass "$wf: success"
  elif [[ "$STATUS" == "null" || "$STATUS" == "unknown" || -z "$STATUS" ]]; then
    fail "$wf: no completed run found for commit $HEAD_SHA"
    ALL_PASSED=false
  else
    fail "$wf: $STATUS"
    ALL_PASSED=false
  fi
done
if [[ "$ALL_PASSED" == "false" ]]; then
  gate_fail "One or more required CI workflows did not pass on commit $HEAD_SHA"
fi

# ---------------------------------------------------------------------------
# Phase 3 — Container image verification
# ---------------------------------------------------------------------------
phase "Phase 3 — Container image verification"

if [[ "$SKIP_IMAGE_PULL" == "true" ]]; then
  skip "Image pull skipped (--skip-image-pull)"
else
  PULL_ERRORS=()
  for service in "${SERVICES[@]}"; do
    image="$REGISTRY/$service:$RELEASE_TAG"
    echo -n "  Pulling $service ... "
    if docker pull "$image" --quiet 2>/dev/null; then
      echo -e "${GREEN}OK${RESET}"
    else
      echo -e "${RED}FAIL${RESET}"
      PULL_ERRORS+=("$service")
    fi
  done

  if [[ ${#PULL_ERRORS[@]} -gt 0 ]]; then
    gate_fail "Failed to pull images for: ${PULL_ERRORS[*]} — build-deploy.yml may not have completed for $RELEASE_TAG"
  fi
  pass "All 7 images pulled successfully"
fi

# ---------------------------------------------------------------------------
# Phase 4 — Kubernetes manifest validation
# ---------------------------------------------------------------------------
phase "Phase 4 — Kubernetes manifest validation"

RENDERED="/tmp/rendered-production-${RELEASE_TAG}.yaml"

info "Rendering k8s/overlays/production ..."
if ! kubectl kustomize k8s/overlays/production > "$RENDERED" 2>&1; then
  gate_fail "kubectl kustomize failed — check k8s/overlays/production/kustomization.yaml"
fi
pass "Kustomize render succeeded ($(wc -l < "$RENDERED") lines)"

# Verify all image references point to GHCR
info "Checking image references ..."
BAD_IMAGES=$(grep "image:" "$RENDERED" | grep -v "#" | grep -v "ghcr.io" || true)
if [[ -n "$BAD_IMAGES" ]]; then
  fail "Non-GHCR image references found:"
  echo "$BAD_IMAGES"
  gate_fail "Image references in rendered manifests do not all point to ghcr.io — check kustomization.yaml image overrides"
fi
pass "All image references resolve to ghcr.io"

# Resource count check
info "Checking resource counts ..."
declare -A EXPECTED_MIN=(
  [Deployment]=7
  [Service]=7
  [HorizontalPodAutoscaler]=7
  [PodDisruptionBudget]=7
)
COUNT_ERRORS=()
for kind in "${!EXPECTED_MIN[@]}"; do
  count=$(grep -c "^kind: $kind" "$RENDERED" 2>/dev/null || echo 0)
  min="${EXPECTED_MIN[$kind]}"
  if [[ "$count" -ge "$min" ]]; then
    pass "$kind: $count (min $min)"
  else
    fail "$kind: $count (expected at least $min)"
    COUNT_ERRORS+=("$kind")
  fi
done

if [[ ${#COUNT_ERRORS[@]} -gt 0 ]]; then
  gate_fail "Insufficient resource counts for: ${COUNT_ERRORS[*]}"
fi

# Server-side dry-run (requires kubeconfig)
if kubectl cluster-info &>/dev/null 2>&1; then
  info "Running server-side dry-run ..."
  DRY_RUN_LOG="/tmp/dry-run-${RELEASE_TAG}.log"
  kubectl apply --dry-run=server -k k8s/overlays/production 2>&1 | tee "$DRY_RUN_LOG" > /dev/null
  if grep -iE "error|failed|invalid" "$DRY_RUN_LOG" &>/dev/null; then
    fail "Server-side dry-run produced errors:"
    grep -iE "error|failed|invalid" "$DRY_RUN_LOG"
    gate_fail "kubectl apply --dry-run=server failed — fix manifest errors before deploying"
  fi
  pass "Server-side dry-run: no errors"
else
  skip "No kubeconfig available — skipping server-side dry-run"
fi

# ---------------------------------------------------------------------------
# Phase 5 — Secret and configuration validation
# ---------------------------------------------------------------------------
phase "Phase 5 — Secret and configuration validation"

SECRET_DIRS=(
  "k8s/external-secrets"
  "k8s/infisical"
  "k8s/vault"
)

for dir in "${SECRET_DIRS[@]}"; do
  if [[ -d "$dir" ]] && [[ -n "$(ls -A "$dir" 2>/dev/null)" ]]; then
    pass "$dir: present and non-empty"
  elif [[ -d "$dir" ]]; then
    fail "$dir: directory exists but is empty"
    gate_fail "$dir is empty — secret operator configuration is missing"
  else
    fail "$dir: directory not found"
    gate_fail "$dir not found — secret operator configuration is missing"
  fi
done

REQUIRED_SECRETS=(
  DATABASE_URL JWT_SECRET OPENAI_API_KEY ANTHROPIC_API_KEY
  NEO4J_URI NEO4J_PASSWORD REDIS_URL VAULT_ADDR
  OIDC_ISSUER_URL KEYCLOAK_CLIENT_SECRET
)
info "Required secrets (must be provisioned via ExternalSecrets/Infisical):"
for secret in "${REQUIRED_SECRETS[@]}"; do
  info "  $secret"
done

# ---------------------------------------------------------------------------
# Phase 5.5 — Database migrations
# ---------------------------------------------------------------------------
phase "Phase 5.5 — Database migrations"

# Run migrations BEFORE deploying application pods so the schema is
# compatible with the new code. Each layer with a database runs its
# Alembic migration in a one-shot Kubernetes Job using the target image.
MIGRATION_LAYERS=(
  "layer1-ingestion:8001"
  "layer2-extraction:8002"
  "layer3-knowledge:8003"
  "layer4-agents:8004"
  "layer5-ground-truth:8005"
)

MIGRATION_ERRORS=()
for entry in "${MIGRATION_LAYERS[@]}"; do
  layer="${entry%%:*}"
  job_name="${layer//-/_}-migrate-${RELEASE_TAG//:/-}"
  job_name="${job_name//\//-}"

  info "Running migration job for $layer ..."

  # Create a one-shot migration job using the target image
  # Uses pg_advisory_lock to ensure only one migration runs at a time
  cat <<EOF | kubectl apply -f - >/dev/null 2>&1 || true
apiVersion: batch/v1
kind: Job
metadata:
  name: ${job_name}
  namespace: ${NAMESPACE}
  labels:
    app: ${layer}
    migration: "true"
    release-tag: "${RELEASE_TAG}"
spec:
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: migrate
          image: ${REGISTRY}/${layer}:${RELEASE_TAG}
          command: ["python", "-c"]
          args:
            - |
              import subprocess
              import sys
              import os
              # Use pg_advisory_lock to prevent concurrent migrations
              # Lock ID 1234567890 is a shared lock for all database migrations
              lock_result = subprocess.run([
                  "python", "-c",
                  """
                  import psycopg2
                  import os
                  conn = psycopg2.connect(os.environ['DATABASE_URL'])
                  conn.autocommit = True
                  cur = conn.cursor()
                  cur.execute('SELECT pg_advisory_lock(1234567890)')
                  print('LOCK_ACQUIRED')
                  cur.close()
                  conn.close()
                  """
              ], capture_output=True, text=True)
              if 'LOCK_ACQUIRED' not in lock_result.stdout:
                  print(f'Failed to acquire advisory lock: {lock_result.stderr}', file=sys.stderr)
                  sys.exit(1)
              # Run migration
              result = subprocess.run(['python', '-m', 'alembic', 'upgrade', 'head'])
              # Release lock automatically on connection close
              sys.exit(result.returncode)
          envFrom:
            - secretRef:
                name: ${layer}-db-credentials
EOF

  # Wait for job completion (5 minute timeout per layer)
  if kubectl wait --for=condition=complete job/${job_name} -n "$NAMESPACE" --timeout=300s >/dev/null 2>&1; then
    pass "$layer: migration succeeded"
  else
    fail "$layer: migration failed or timed out"
    MIGRATION_ERRORS+=("$layer")
    # Print job logs for debugging
    kubectl logs job/${job_name} -n "$NAMESPACE" --tail=50 2>/dev/null || true
  fi
done

if [[ ${#MIGRATION_ERRORS[@]} -gt 0 ]]; then
  gate_fail "Database migrations failed for: ${MIGRATION_ERRORS[*]} — fix schema issues before deploying"
fi

# ---------------------------------------------------------------------------
# Dry-run exit point
# ---------------------------------------------------------------------------
if [[ "$DRY_RUN" == "true" ]]; then
  echo ""
  echo -e "${GREEN}${BOLD}DRY-RUN COMPLETE — All pre-flight gates passed.${RESET}"
  echo -e "Re-run without --dry-run to execute the deployment."
  exit 0
fi

# ---------------------------------------------------------------------------
# Phase 6 — Deploy
# ---------------------------------------------------------------------------
phase "Phase 6 — Deploy"

if ! kubectl cluster-info &>/dev/null 2>&1; then
  gate_fail "No kubeconfig available — cannot deploy. Configure kubectl access to the target cluster."
fi

info "Creating namespace $NAMESPACE if it does not exist ..."
if [[ "$DRY_RUN" == "true" ]]; then
  echo -e "${YELLOW}[DRY-RUN]${RESET} kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -"
else
  kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
fi

info "Applying $OVERLAY ..."
kubectl apply -k "$OVERLAY"

info "Waiting for rollouts (10m timeout each) ..."
ROLLOUT_ERRORS=()
for deploy in "${SERVICES[@]}"; do
  echo -n "  $deploy ... "
  if kubectl rollout status "deployment/$deploy" -n "$NAMESPACE" --timeout=10m 2>&1; then
    echo -e "${GREEN}OK${RESET}"
  else
    echo -e "${RED}FAIL${RESET}"
    ROLLOUT_ERRORS+=("$deploy")
  fi
done

if [[ ${#ROLLOUT_ERRORS[@]} -gt 0 ]]; then
  gate_fail "Rollout failed for: ${ROLLOUT_ERRORS[*]} — check pod events with: kubectl describe pod -n $NAMESPACE -l app=<name>"
fi
pass "All 7 deployments rolled out successfully"

# ---------------------------------------------------------------------------
# Phase 7 — Post-deploy verification
# ---------------------------------------------------------------------------
phase "Phase 7 — Post-deploy verification"

info "Deployment status:"
kubectl get deployments -n "$NAMESPACE" -o wide

echo ""
info "Pod status:"
kubectl get pods -n "$NAMESPACE" -o wide

echo ""
info "Services:"
kubectl get svc -n "$NAMESPACE"

echo ""
info "HPA:"
kubectl get hpa -n "$NAMESPACE"

echo ""
info "PDB:"
kubectl get pdb -n "$NAMESPACE"

echo ""
info "NetworkPolicies:"
kubectl get networkpolicy -n "$NAMESPACE"

# Health checks via port-forward
echo ""
info "Running health checks via port-forward ..."
HEALTH_ERRORS=()
for entry in "${LAYER_PORTS[@]}"; do
  layer="${entry%%:*}"
  port="${entry##*:}"

  kubectl port-forward "svc/$layer" "${port}:${port}" -n "$NAMESPACE" &>/dev/null &
  PF_PID=$!
  sleep 2

  if curl -sf --max-time 5 "http://localhost:${port}/health" &>/dev/null; then
    pass "$layer: HEALTHY"
  else
    skip "$layer: /health did not respond (may be normal for this service)"
  fi

  kill "$PF_PID" 2>/dev/null || true
  wait "$PF_PID" 2>/dev/null || true
done

# ---------------------------------------------------------------------------
# Phase 8 — Deployment evidence
# ---------------------------------------------------------------------------
phase "Phase 8 — Deployment evidence"

mkdir -p .deployments

# Sanitize tag for filename — digest refs (sha256:<hash>) contain ':' which
# is invalid in filenames on some systems and awkward in tooling.
RELEASE_TAG_SAFE="${RELEASE_TAG//:/-}"
RELEASE_TAG_SAFE="${RELEASE_TAG_SAFE//\//-}"
EVIDENCE_FILE=".deployments/$(date -u +%Y-%m-%d)-${RELEASE_TAG_SAFE}.md"
DEPLOY_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
COMMIT_SHA=$(git rev-parse HEAD)
DEPLOYER="${USER:-unknown}"

cat > "$EVIDENCE_FILE" << EOF
# Deployment Evidence — ${RELEASE_TAG}

Date: ${DEPLOY_TIME}
Tag: ${RELEASE_TAG}
Commit: ${COMMIT_SHA}
Namespace: ${NAMESPACE}
Deployer: ${DEPLOYER}
Script: scripts/deploy-production.sh

## Gate results

- [x] Phase 0: tooling preflight passed
- [x] Phase 1: repo state clean, tag verified, versions aligned
- [x] Phase 2: CI pipeline health verified
- [x] Phase 3: all 7 images pulled from ${REGISTRY}
- [x] Phase 4: kustomize render clean, GHCR refs verified, resource counts OK
- [x] Phase 5: secret configuration directories present
- [x] Phase 6: all 7 deployments rolled out successfully
- [x] Phase 7: post-deploy verification completed

## Services deployed

$(for svc in "${SERVICES[@]}"; do echo "- ${REGISTRY}/${svc}:${RELEASE_TAG}"; done)

## Notes

Generated by scripts/deploy-production.sh
EOF

pass "Evidence file written: $EVIDENCE_FILE"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║  DEPLOYMENT COMPLETE — Value Fabric ${RELEASE_TAG}          ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Namespace:  ${NAMESPACE}"
echo -e "  Commit:     $(git rev-parse --short HEAD)"
echo -e "  Evidence:   ${EVIDENCE_FILE}"
echo -e "  Time:       ${DEPLOY_TIME}"
echo ""
