# Ingress Profile Operations and Rollback

## Production-supported ingress profile

- **Supported production ingress strategy:** `nginx-path` (`k8s/deployments/prod-nginx`).
- **Experimental only:** `prod-gateway-api`, `prod-istio`.
- Deploy workflows enforce profile controls from `.fabric/prod-gates.policy.yaml` before deployment.

## Required controls (all deploy profiles)

1. CORS declaration annotation present in rendered NGINX Ingress.
2. Auth integration annotations present (`auth-url`, `auth-signin`, `auth-response-headers`).
3. Rate-limiting annotations present (`limit-rps`, `limit-rpm`, `limit-connections`, `limit-burst-multiplier`).
4. Ingress strategy fixed to `nginx-path`.

## Operational runbook by profile

### `pr-fast` (dev)
- Render: `kustomize build k8s/deployments/dev-nginx --load-restrictor=LoadRestrictionsNone`.
- Validate routing controls: `python scripts/ci/k8s_routing_check.py ... --deployment dev-nginx:nginx`.
- Apply: `kubectl apply -k k8s/deployments/dev-nginx`.

### `mainline-full` (staging)
- Render: `kustomize build k8s/deployments/staging-nginx --load-restrictor=LoadRestrictionsNone`.
- Validate routing controls: include `--deployment staging-nginx:nginx` in routing check.
- Apply: `kubectl apply -k k8s/deployments/staging-nginx`.
- Verify oauth2-proxy + ingress status before smoke tests.

### `release-candidate` (production)
- Render: `kustomize build k8s/deployments/prod-nginx --load-restrictor=LoadRestrictionsNone`.
- Validate routing controls and deploy profile policy checks.
- Apply only after prod-readiness artifacts and release policy gate succeed.

## Rollback steps

1. Identify last known-good immutable `IMAGE_REF` (`sha-...` or digest).
2. Re-run deploy workflow to same environment with previous immutable ref.
3. Confirm rollout success for all deployments.
4. Validate ingress control annotations still present in rendered manifests.
5. Record incident timeline and rollback evidence in release artifacts.
