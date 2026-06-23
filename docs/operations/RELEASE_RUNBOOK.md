# Production Release Runbook

**Repo:** bmsull560/Fabric_4L  
**Registry:** ghcr.io/bmsull560/fabric_4l  
**Namespace:** fabric-4l-prod  
**Last updated:** 2026-05-14

---

## Release decision: tag vs HEAD

Before executing any phase, establish which commit you are deploying.

```bash
# Show current HEAD and the most recent release tag
git log --oneline -1
git describe --tags --abbrev=0

# Show commits between the last tag and HEAD
git log --oneline $(git describe --tags --abbrev=0)..HEAD
```

**If HEAD is ahead of the last tag** (the normal case after active development),
you must cut a new tag and publish a GitHub Release before deploying. Do not
deploy HEAD as if it were the last tag — the images built by CI are tagged from
the commit SHA, not from a stale tag.

```bash
# 1. Cut a new annotated tag (adjust version per semver policy in docs/VERSIONING.md)
git tag -a v1.1.0 -m "release(1.1.0): <one-line summary>"
git push origin v1.1.0
```

> ⚠️ **A bare tag push does not trigger `build-deploy.yml`.** The workflow only
> fires on `push` to branches and on `release: published` events. Pushing a tag
> alone starts no CI run and produces no release-tagged image.

```
# 2. Publish a GitHub Release from the tag — this is what triggers the build:
#    https://github.com/bmsull560/Fabric_4L/releases/new
#    → Tag: v1.1.0 (select the tag you just pushed)
#    → Publish release
```

Only after the release is published will `build-deploy.yml` run and push
`ghcr.io/bmsull560/fabric_4l/<service>:v1.1.0` for all 7 services. Wait for
that run to complete (green) before proceeding to Phase 3.

**If HEAD matches the tag exactly** (`git describe --tags --exact-match` returns
the tag with no suffix), a GitHub Release for that tag must already be published
and the corresponding `build-deploy.yml` run must have completed successfully
before proceeding.

---

## Phase 0 — Tooling preflight

```bash
command -v git      && git --version
command -v docker   && docker --version
command -v kubectl  && kubectl version --client 2>/dev/null | head -1
command -v pnpm     && pnpm --version
command -v python3  && python3 --version
# Optional but recommended
command -v cosign   || echo "cosign: not installed (optional)"
command -v trivy    || echo "trivy: not installed (optional)"
```

All required tools must be present before continuing.

---

## Phase 1 — Repository state verification

```bash
git checkout main
git pull origin main

# Must show: nothing to commit, working tree clean
git status

# Confirm the release tag exists
RELEASE_TAG="v1.1.0"   # set to the tag you are deploying
git tag -l "$RELEASE_TAG"

# Confirm HEAD matches the tag
git describe --tags --exact-match 2>/dev/null || echo "WARNING: HEAD is not at a tag"

# Version alignment check
echo "version.txt:           $(cat version.txt)"
echo "package.json:          $(node -e "console.log(require('./package.json').version)")"
echo "apps/web package.json: $(node -e "console.log(require('./apps/web/package.json').version)")"
echo "K8s prod overlay tag:  $(grep 'newTag' k8s/overlays/production/kustomization.yaml | head -1)"
```

Expected: every source reads the same version. If any source diverges, run the
version alignment procedure in `docs/VERSIONING.md` before continuing.

---

## Phase 2 — CI pipeline health

Verify the following workflows passed on the commit you are deploying:

| Workflow | Purpose | Required |
|---|---|---|
| `build-deploy.yml` | Build + push container images | ✅ |
| `pr-checks.yml` | Required test suite | ✅ |
| `security-gates.yml` | CVE scanning | ✅ |
| `contract-compliance.yml` | Contract validation | ✅ |
| `critical-gates.yml` | Pre-deployment checks | ✅ |
| `prod-readiness.yml` | Go/no-go gate | ✅ |

Check at: https://github.com/bmsull560/Fabric_4L/actions

Do not proceed if any required workflow failed on the target commit.

---

## Phase 3 — Container image verification

```bash
REGISTRY="ghcr.io/bmsull560/fabric_4l"
RELEASE_TAG="v1.1.0"   # must match the tag cut in the release decision step

echo "=== Pulling all 7 service images ==="
for service in \
  layer1-ingestion \
  layer2-extraction \
  layer3-knowledge \
  layer4-agents \
  layer5-ground-truth \
  layer6-benchmarks \
  frontend; do

  image="$REGISTRY/$service:$RELEASE_TAG"
  echo -n "  $service ... "
  docker pull "$image" --quiet && echo "OK" || echo "FAIL — stop here"
done
```

All 7 images must pull successfully. If any fail, the `build-deploy.yml` run
for the release tag has not completed or failed — do not proceed.

---

## Phase 4 — Kubernetes manifest validation

### 4.1 Render and inspect

```bash
# Render the production overlay
kubectl kustomize k8s/overlays/production > /tmp/rendered-production.yaml

echo "Total lines: $(wc -l < /tmp/rendered-production.yaml)"

# Verify all 7 service images resolve to GHCR
echo "=== Image references in rendered manifests ==="
grep "image:" /tmp/rendered-production.yaml | grep -v "#" | sort | uniq

# Every line must match: ghcr.io/bmsull560/fabric_4l/<service>:<tag>
# If any line still shows services/<name>:main or apps/web:main,
# the kustomization image mapping is broken — stop here.
```

### 4.2 Resource count check

```bash
for kind in Deployment Service HorizontalPodAutoscaler PodDisruptionBudget NetworkPolicy; do
  count=$(grep -c "^kind: $kind" /tmp/rendered-production.yaml || echo 0)
  echo "  $kind: $count"
done
# Expected: 7 Deployments, 7+ Services, 7 HPAs, 7+ PDBs, 7+ NetworkPolicies
```

### 4.3 Server-side dry-run (requires kubeconfig)

```bash
kubectl apply --dry-run=server -k k8s/overlays/production 2>&1 | tee /tmp/dry-run.log

grep -iE "error|failed|invalid" /tmp/dry-run.log && echo "VALIDATION FAILED" || echo "VALIDATION PASSED"
```

---

## Phase 5 — Secret and configuration validation

```bash
# ExternalSecrets operator configuration
ls k8s/external-secrets/

# Infisical operator configuration
ls k8s/infisical/

# Vault integration
ls k8s/vault/
```

Required secrets (must be provisioned via ExternalSecrets before deployment):

```
DATABASE_URL          NEO4J_URI             VAULT_ADDR
JWT_SECRET            NEO4J_PASSWORD        OIDC_ISSUER_URL
OPENAI_API_KEY        REDIS_URL             KEYCLOAK_CLIENT_SECRET
ANTHROPIC_API_KEY
```

---

## Autonomous deploy script

All phases below can be executed automatically via:

```bash
# Full deploy (Phases 0–8)
bash scripts/deploy-production.sh --tag v1.1.0

# Pre-flight only — no cluster changes (Phases 0–5)
bash scripts/deploy-production.sh --tag v1.1.0 --dry-run

# Skip docker pull checks (useful in CI where images are pre-pulled)
bash scripts/deploy-production.sh --tag v1.1.0 --skip-image-pull
```

The namespace is always read from `k8s/overlays/production/kustomization.yaml`
and cannot be overridden — the overlay is the single source of truth.

The script stops on the first failing gate and prints the gate name. It writes
a deployment evidence file to `.deployments/` on successful completion.

---

## Phase 6 — Deploy

### Option A — GitHub Actions (recommended)

The `deploy.yml` workflow triggers on release publish. To deploy:

1. Confirm the release tag exists and all CI gates passed (Phase 2).
2. Navigate to https://github.com/bmsull560/Fabric_4L/releases
3. Publish the release for the tag (or trigger `deploy.yml` manually via
   workflow dispatch).
4. Monitor: https://github.com/bmsull560/Fabric_4L/actions/workflows/deploy.yml

### Option B — deploy-production.sh (manual fallback)

Use the deploy script for a guided, gated manual deploy. It runs all preflight
checks, CI gate verification, image pull, version alignment, and rollout waits
in sequence. The namespace is always read from `k8s/overlays/production/kustomization.yaml`
and cannot be overridden — this ensures apply and rollout checks always target
the same namespace.

```bash
bash scripts/deploy-production.sh --tag v1.2.3
# Add --dry-run to preview without applying
# Add --skip-image-pull to skip docker pull verification
```

### Option C — kubectl kustomize (bare manual fallback)

```bash
NAMESPACE="fabric-4l-prod"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -k k8s/overlays/production

for deploy in \
  layer1-ingestion layer2-extraction layer3-knowledge \
  layer4-agents layer5-ground-truth layer6-benchmarks frontend; do
  echo "Waiting for $deploy ..."
  kubectl rollout status "deployment/$deploy" -n "$NAMESPACE" --timeout=10m
done
```

> **Note:** A Helm chart (`infra/helm/value-fabric/`) does not exist in this
> repository. Helm-based deployment is not available. Use Option A or Option B.

---

## Phase 7 — Post-deploy verification

```bash
NAMESPACE="fabric-4l-prod"

kubectl get deployments -n "$NAMESPACE" -o wide
kubectl get pods       -n "$NAMESPACE" -o wide
kubectl get svc        -n "$NAMESPACE"
kubectl get hpa        -n "$NAMESPACE"
kubectl get pdb        -n "$NAMESPACE"
kubectl get networkpolicy -n "$NAMESPACE"
```

Health checks via port-forward:

```bash
for layer in layer1-ingestion layer2-extraction layer3-knowledge \
             layer4-agents layer5-ground-truth layer6-benchmarks; do
  port=$(case $layer in
    layer1-ingestion)   echo 8001 ;;
    layer2-extraction)  echo 8002 ;;
    layer3-knowledge)   echo 8003 ;;
    layer4-agents)      echo 8004 ;;
    layer5-ground-truth) echo 8005 ;;
    layer6-benchmarks)  echo 8006 ;;
  esac)
  kubectl port-forward "svc/$layer" "${port}:${port}" -n "$NAMESPACE" &
  PID=$!; sleep 2
  curl -sf "http://localhost:${port}/health" && echo "$layer: HEALTHY" \
    || echo "$layer: no /health endpoint (may be normal)"
  kill $PID 2>/dev/null
done
```

---

## Phase 8 — Deployment evidence

When deploying via GitHub Actions (`deploy.yml`), the evidence file is
generated and committed to `main` automatically after a successful production
deploy. No manual action is required for Option A deploys.

For manual deploys (Option B) or script-based deploys, the evidence file is
written by `scripts/deploy-production.sh` at the end of Phase 8. To create it
manually:

```bash
RELEASE_TAG="v1.1.0"
EVIDENCE_FILE=".deployments/$(date -u +%Y-%m-%d)-${RELEASE_TAG}.md"

mkdir -p .deployments

cat > "$EVIDENCE_FILE" << EOF
# Deployment Evidence — $RELEASE_TAG

Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Tag: $RELEASE_TAG
Commit: $(git rev-parse HEAD)
Deployer: <name>

## Gate results

- [ ] Phase 1: repo state clean, tag verified
- [ ] Phase 2: all CI workflows passed
- [ ] Phase 3: all 7 images pulled
- [ ] Phase 4: kustomize render clean, GHCR refs verified
- [ ] Phase 5: secrets provisioned
- [ ] Phase 6: rollout completed
- [ ] Phase 7: all pods Running, health checks passed

## Notes

<any observations>
EOF

echo "Evidence file: $EVIDENCE_FILE"
```

---

## Phase 9 — Rollback

If deployment fails, execute within 5 minutes:

```bash
NAMESPACE="fabric-4l-prod"

for deploy in \
  layer1-ingestion layer2-extraction layer3-knowledge \
  layer4-agents layer5-ground-truth layer6-benchmarks frontend; do
  kubectl rollout undo "deployment/$deploy" -n "$NAMESPACE"
  kubectl rollout status "deployment/$deploy" -n "$NAMESPACE" --timeout=5m
done

kubectl get deployments -n "$NAMESPACE"
kubectl get pods        -n "$NAMESPACE"
```

---

## Go/no-go decision matrix

| Gate | Criteria | Verified by |
|---|---|---|
| Clean working tree | `git status` clean | Phase 1 |
| HEAD at release tag | `git describe --exact-match` returns tag | Phase 1 |
| Version alignment | All sources match release version | Phase 1 |
| CI pipelines passed | All required workflows green on tag commit | Phase 2 |
| All 7 images present | `docker pull` succeeds for each | Phase 3 |
| GHCR refs in manifests | `grep image:` shows `ghcr.io/bmsull560/...` | Phase 4 |
| Dry-run clean | Zero errors from `--dry-run=server` | Phase 4 |
| Secrets provisioned | ExternalSecrets/Infisical configured | Phase 5 |
| All pods Running | `kubectl get pods` shows Running | Phase 7 |
| Health checks pass | `/health` returns 200 for all layers | Phase 7 |
| HPA active | `kubectl get hpa` shows targets | Phase 7 |
| PDB active | `kubectl get pdb` shows budgets | Phase 7 |

**Deploy only when all gates are verified.** Do not mark a gate PASS without
running the corresponding verification command.
