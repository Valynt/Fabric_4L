# staging-nginx Deployment

This overlay combines the **staging environment** with **NGINX Ingress routing**.

## Purpose

Staging is a production-like pre-production environment that mirrors production configuration:

- Uses ExternalSecrets (same as prod)
- Uses 2 replicas for HA testing (same as prod)
- Uses SHA image digests (same as prod)
- Has distinct hostnames and labels from production

This deployment is the **last validation gate** before production promotion.

## Application host

`staging.value-fabric.example.com` serves both surfaces: `/api/v1/*` routes to the API gateway with the `/v1/*` upstream rewrite, while `/` routes to the frontend. Layer Services are never public.

## Usage

Build and validate:

```bash
kustomize build k8s/deployments/staging-nginx \
  --load-restrictor=LoadRestrictionsNone
```

Apply to cluster:

```bash
kustomize build k8s/deployments/staging-nginx \
  --load-restrictor=LoadRestrictionsNone | kubectl apply -f -
```

## Structure

```
staging-nginx/
├── kustomization.yaml    # Imports staging env + nginx routing + hostname replacements
├── hostname-config.yaml  # Staging-specific hostnames
└── README.md            # This file
```

## Promotion Path

```
dev-nginx → staging-nginx → prod-nginx
```

Staging validates the same artifact (SHA digest) that will run in production.
