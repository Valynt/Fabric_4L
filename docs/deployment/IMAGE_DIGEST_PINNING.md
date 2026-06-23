# Image Digest Pinning for Production Deployments

This document describes the process for pinning container image digests in production deployments to ensure immutability and reproducibility.

## Why Digest Pinning?

Container image tags like `:main`, `:latest`, or `:dev` are mutable - the same tag can point to different image versions over time. This creates security and reproducibility risks:

- **Security**: An attacker could push a malicious image to the `:main` tag
- **Reproducibility**: You can't guarantee which image version was deployed
- **Rollback**: Difficult to roll back to a known-good state

SHA256 digests are immutable - they uniquely identify a specific image layer composition.

## Release-Time Digest Injection

During release promotion, the CI pipeline should:

1. **Build images with specific tags**
   ```bash
   docker build -t ghcr.io/bmsull560/fabric_4l/layer4-agents:v1.2.3 .
   docker push ghcr.io/bmsull560/fabric_4l/layer4-agents:v1.2.3
   ```

2. **Compute SHA256 digests**
   ```bash
   docker pull ghcr.io/bmsull560/fabric_4l/layer4-agents:v1.2.3
   docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/bmsull560/fabric_4l/layer4-agents:v1.2.3
   # Output: ghcr.io/bmsull560/fabric_4l/layer4-agents@sha256:abc123...
   ```

3. **Update production overlay kustomization.yaml**
   ```yaml
   images:
     - name: services/layer4-agents
       newName: ghcr.io/bmsull560/fabric_4l/layer4-agents
       digest: sha256:abc123def456...
   ```

4. **Verify CI gate passes**
   ```bash
   scripts/ci/check-k8s-image-digests.sh
   ```

## Kustomize Digest Pinning Format

### Method 1: Using `digest` field (recommended)
```yaml
images:
  - name: services/layer4-agents
    newName: ghcr.io/bmsull560/fabric_4l/layer4-agents
    digest: sha256:abc123def456...
```

### Method 2: Direct image reference in manifests
```yaml
containers:
  - name: api
    image: ghcr.io/bmsull560/fabric_4l/layer4-agents@sha256:abc123def456...
```

## CI Gate Enforcement

The `scripts/ci/check-k8s-image-digests.sh` script enforces digest pinning in production overlays:

- **Checked overlays**: `k8s/overlays/production`, `k8s/overlays/staging`
- **Blocked tags**: `:main`, `:latest`, `:dev`, `:master`, `:develop`
- **Failure**: CI fails if mutable tags are found in production overlays

## Dev/Staging Exception

Base and development manifests may use mutable tags (`:main`) for convenience:

- `k8s/base/kustomization.yaml` uses `newTag: main` for all images
- `k8s/` layer manifests use `:main` tags directly
- This is acceptable for development environments

Only production-like overlays must use digest-pinned images.

## Verification

After deployment, verify the deployed image digest:

```bash
kubectl get deployment layer4-agents -n value-fabric -o jsonpath='{.spec.template.spec.containers[0].image}'
# Should output: ghcr.io/bmsull560/fabric_4l/layer4-agents@sha256:abc123...
```

## Rollback

To roll back to a previous digest:

1. Update the overlay kustomization.yaml with the previous digest
2. Apply the overlay: `kubectl apply -k k8s/overlays/production`
3. Verify the deployment rolled back

## References

- [Kubernetes Documentation: Image Pull Policy](https://kubernetes.io/docs/concepts/containers/images/#updating-images)
- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [Kustomize Image Transformers](https://kubectl.docs.kubernetes.io/guides/kustomize/#image-transformer)
