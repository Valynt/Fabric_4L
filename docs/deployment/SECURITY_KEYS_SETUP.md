# Security Keys Deployment Guide

Deploy JWT RSA keys and API key cache secrets for the security hardening implemented in Q2 2026.

## Prerequisites

- OpenSSL installed
- kubectl configured for your cluster
- Access to your secrets manager (Vault, AWS Secrets Manager, etc.)

## Quick Start

```bash
# 1. Generate all secrets
./scripts/generate-jwt-keys.sh ./jwt-keys
./scripts/generate-secrets.ps1   # On Windows
# OR manually generate API_KEY_CACHE_SECRET:
export API_KEY_CACHE_SECRET=$(openssl rand -hex 32)

# 2. Create Kubernetes secrets
kubectl create secret generic jwt-keys \
  --from-file=jwt-private.pem=./jwt-keys/jwt-private.pem \
  --from-file=jwt-public.pem=./jwt-keys/jwt-public.pem \
  -n value-fabric

kubectl create secret generic api-key-cache-secret \
  --from-literal=API_KEY_CACHE_SECRET="$API_KEY_CACHE_SECRET" \
  -n value-fabric

# 3. Deploy with updated manifests
kubectl apply -k k8s/base
```

## What Each Secret Does

### JWT Keys (jwt-keys Secret)

- **Purpose**: RS256 asymmetric signing for JWT tokens
- **Files**: `jwt-private.pem` (signing), `jwt-public.pem` (verification)
- **Rotation**: Can rotate independently by updating secret and restarting pods

### API Key Cache Secret (api-key-cache-secret)

- **Purpose**: HMAC-SHA256 key for secure API key fingerprinting in Redis
- **Value**: 64-character hex string (32 bytes)
- **Rotation**: Cache invalidation required on rotation (keys will need re-validation)

## Production Options

### Option 1: External Secrets Operator (Recommended)

Sync from Vault/AWS Secrets Manager:

```yaml
# k8s/external-secrets/jwt-keys-es.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: jwt-keys
  namespace: value-fabric
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
  target:
    name: jwt-keys
    template:
      data:
        jwt-private.pem: "{{ .jwt_private_key }}"
        jwt-public.pem: "{{ .jwt_public_key }}"
  data:
    - secretKey: jwt_private_key
      remoteRef:
        key: fabric/jwt
        property: private_key
    - secretKey: jwt_public_key
      remoteRef:
        key: fabric/jwt
        property: public_key
```

### Option 2: Sealed Secrets

Encrypt for git with kubeseal:

```bash
# Generate keys first
./scripts/generate-jwt-keys.sh

# Create and seal the secret
kubectl create secret generic jwt-keys \
  --from-file=./jwt-keys/jwt-private.pem \
  --from-file=./jwt-keys/jwt-public.pem \
  --dry-run=client -o yaml | \
  kubeseal --controller-namespace=sealed-secrets \
  --format=yaml > k8s/base/jwt-keys-sealed.yaml

# Commit the sealed secret
git add k8s/base/jwt-keys-sealed.yaml
```

### Option 3: CI/CD Injection

Generate during pipeline and inject:

```yaml
# GitHub Actions example
- name: Generate JWT Keys
  run: |
    ./scripts/generate-jwt-keys.sh /tmp/jwt-keys
    kubectl create secret generic jwt-keys \
      --from-file=/tmp/jwt-keys/jwt-private.pem \
      --from-file=/tmp/jwt-keys/jwt-public.pem \
      -n value-fabric --dry-run=client -o yaml | kubectl apply -f -
```

## Verification

```bash
# Check secrets exist
kubectl get secrets -n value-fabric | grep -E "jwt-keys|api-key-cache"

# Verify pod mounts
cubectl exec -n value-fabric deploy/layer4-agents -- ls -la /secrets/

# Check environment variables
kubectl exec -n value-fabric deploy/layer4-agents -- env | grep -E "JWT|ENVIRONMENT"
```

## Troubleshooting

### Pod fails to start with "JWT key not found"
- Verify secret exists: `kubectl get secret jwt-keys -n value-fabric`
- Check volume mount: `kubectl describe pod <pod-name> -n value-fabric`

### "DEV_AUTH_BYPASS cannot be enabled in production"
- Check ENVIRONMENT is set to "production": `kubectl set env deploy/layer4-agents ENVIRONMENT=production`
- Verify bypass flags (DEV_AUTH_BYPASS, ALLOW_INSECURE_DEV_AUTH_BYPASS, ALLOW_DEV_AUTH_BYPASS, AUTH_BYPASS_ENABLED) are not set in committed/shared configs

### API key cache returns different hashes on restart
- Verify API_KEY_CACHE_SECRET is set consistently across all pods
- Check logs: `kubectl logs -n value-fabric deploy/layer4-agents | grep "API_KEY_CACHE_SECRET"`

## Security Checklist

- [ ] JWT keys are 2048-bit RSA minimum
- [ ] Private key has 0600 permissions
- [ ] API_KEY_CACHE_SECRET is 32+ bytes random
- [ ] ENVIRONMENT=production in all production pods
- [ ] DEV_AUTH_BYPASS is unset in production
- [ ] Secrets are NOT committed to git (use templates only)
- [ ] External Secrets Operator or Sealed Secrets in production
