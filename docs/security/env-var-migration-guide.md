# Environment Variable Migration Guide

## Overview

The environment variable structure has been reorganized to align with Infisical's path-based secret management. This guide helps you migrate existing deployments to the new structure.

## Key Changes

### Old Structure
Previously, environment variables were defined in a flat `.env` file without path annotations.

### New Structure
Environment variables are now organized by Infisical paths:
- `/shared` - Cross-service configuration
- `/infra` - Infrastructure credentials
- `/apps/web` - Frontend runtime/build
- `/layer1-ingestion` - Layer 1 service configuration
- `/layer2-extraction` - Layer 2 service configuration
- `/layer2-5-signal-refinery` - Layer 2.5 service configuration
- `/layer3-knowledge` - Layer 3 service configuration
- `/layer4-agents` - Layer 4 service configuration
- `/layer5-ground-truth` - Layer 5 service configuration
- `/layer6-benchmarks` - Layer 6 service configuration

## Migration Steps

### 1. Local Development

**Before:**
```bash
cp .env.example .env
# Edit .env with your values
docker compose up
```

**After:**
```bash
# Option 1: Using Infisical CLI (recommended)
infisical login
pnpm env:dev && docker compose -f docker-compose.dev.yml --env-file .env.generated up -d

# Option 2: Manual migration (if you don't have Infisical access)
cp .env.example .env
# Map your old .env values to the new structure
docker compose up
```

### 2. Environment Variable Mapping

| Old Variable | New Path | Notes |
|-------------|----------|-------|
| `APP_ENV` | `/shared/APP_ENV` | Moved to shared |
| `POSTGRES_HOST` | `/infra/POSTGRES_HOST` | Moved to infra |
| `POSTGRES_PASSWORD` | `/infra/POSTGRES_PASSWORD` | Moved to infra |
| `REDIS_URL` | `/infra/REDIS_URL` | Moved to infra |
| `NEO4J_URI` | `/infra/NEO4J_URI` | Moved to infra |
| `OPENAI_API_KEY` | `/layer2-extraction/OPENAI_API_KEY` | Layer-specific |
| `VITE_API_BASE_URL` | `/apps/web/VITE_API_BASE_URL` | Frontend-specific |

### 3. CI/CD Migration

**Before:**
```yaml
- name: Set secrets
  run: |
    echo "POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}" >> .env
```

**After:**
```yaml
- name: Fetch secrets from Infisical
  uses: Infisical/secrets-action@v1
  with:
    method: oidc
    env-slug: ${{ github.environment }}
    project-slug: fabric4l
    identity-id: ${{ secrets.INFISICAL_IDENTITY_ID }}
    secret-path: /shared
```

### 4. Production Deployment

**Before:**
```bash
kubectl create secret generic app-secrets \
  --from-literal=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  --from-literal=JWT_SECRET=$JWT_SECRET
```

**After:**
```bash
# Infisical injects secrets at runtime via the Infisical Agent
# No manual secret management required
kubectl apply -f k8s/deployments/prod-gateway-api/
```

## Breaking Changes

1. **Flat structure removed**: Environment variables are no longer in a single file
2. **Path annotations added**: `.env.example` now includes Infisical path comments
3. **Infisical required for production**: Production deployments must use Infisical for secret management

## Rollback Procedure

If you need to rollback to the old structure:

1. Restore your previous `.env` file from backup
2. Remove Infisical integration from CI/CD workflows
3. Revert service startup scripts to use `.env` instead of Infisical injection

## Validation

After migration, verify:

```bash
# Check that services start correctly
docker compose -f docker-compose.dev.yml up

# Verify environment variables are loaded
docker compose -f docker-compose.dev.yml exec layer2-extraction env | grep OPENAI_API_KEY
```

## Support

For issues with migration:
- Check `docs/security/secrets-management.md` for detailed Infisical setup
- Review `.env.example` for the complete new structure
- Contact the platform team for Infisical access issues
