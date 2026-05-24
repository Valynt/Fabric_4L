# Deprecated: Vault-backed ExternalSecrets

> **Status**: Deprecated — migration in progress to Infisical Kubernetes Operator.
>
> **Target**: `k8s/infisical/`

## Migration Path

1. Install the Infisical operator:
   ```bash
   helm repo add infisical-helm-charts https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/
   helm install infisical-operator infisical-helm-charts/secrets-operator
   ```

2. Create the universal-auth secret (once per cluster):
   ```bash
   kubectl create secret generic infisical-universal-auth \
     --from-literal=clientId=<CLIENT_ID> \
     --from-literal=clientSecret=<CLIENT_SECRET> \
     -n value-fabric
   ```

3. Apply the new InfisicalSecret manifests:
   ```bash
   kubectl apply -f k8s/infisical/infisical-secret.yml
   ```

4. Update deployments to reference the new Kubernetes Secrets created by the Infisical operator.

5. Remove the old ExternalSecrets and ClusterSecretStore once all services are migrated.

## Rollback

If Infisical is unavailable, the existing Vault-backed ExternalSecrets remain in place as a fallback until explicitly removed.
