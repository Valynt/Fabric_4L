# Deployable Service Image Map

This repository has **eight deployable backend services** under `services/`, each backed by a Dockerfile and a compose build definition in `docker-compose.full.yml` (and via `extends` in `docker-compose.prod.yml`):

1. `services/api` → `docker-compose.full.yml` service `api-gateway` (build context `./services/api`)
2. `services/layer1-ingestion` → service `layer1-ingestion` (build context `.` + `services/layer1-ingestion/Dockerfile.live`)
3. `services/layer2-extraction` → service `layer2-extraction` (build context `.` + `services/layer2-extraction/Dockerfile.full`)
4. `services/layer2-5-signal-refinery` → service `layer2-5-signal-refinery` (build context `.` + `services/layer2-5-signal-refinery/Dockerfile`)
5. `services/layer3-knowledge` → service `layer3-knowledge` (build context `.` + `services/layer3-knowledge/Dockerfile.full`)
6. `services/layer4-agents` → service `layer4-agents` (build context `.` + `services/layer4-agents/Dockerfile.full`)
7. `services/layer5-ground-truth` → service `layer5-ground-truth` (build context `.` + `services/layer5-ground-truth/Dockerfile.full`)
8. `services/layer6-benchmarks` → service `layer6-benchmarks` (build context `.` + `services/layer6-benchmarks/Dockerfile.full`)

Billing is owned by Layer 4 (`services/layer4-agents`); there is no standalone Layer 7 billing service. See `docs/architecture/layer7-billing.md`.

Kubernetes base manifests use image placeholders resolved by `k8s/base/kustomization.yaml`:

- `services/api` → `api-gateway` deployment (`k8s/base/api-gateway.yml`)
- `services/layer1-ingestion` → `k8s/base/layer1-ingestion.yml`
- `services/layer2-extraction` → `k8s/base/layer2-extraction.yml`
- `services/layer2-5-signal-refinery` → `k8s/base/layer2-5-signal-refinery.yml`
- `services/layer3-knowledge` → `k8s/base/layer3-knowledge.yml`
- `services/layer4-agents` → `k8s/base/layer4-agents.yml`
- `services/layer5-ground-truth` → `k8s/base/layer5-ground-truth.yml`
- `services/layer6-benchmarks` → `k8s/base/layer6-benchmarks.yml`

Root-level deployable app directory:

- `apps/web` image build/deploy path is maintained separately from backend services.
