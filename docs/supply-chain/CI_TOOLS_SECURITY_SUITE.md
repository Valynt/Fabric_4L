# Supply-chain CI tools image

The supply-chain workflow uses only the immutable image reference declared as
`CI_TOOLS_IMAGE` in `.github/workflows/supply-chain.yml`. A mutable tag is never an
operational fallback.

## Publisher and pinned contents

The trusted publisher is the `value-fabric/ci-tools` repository workflow
`.github/workflows/publish-ci-tools.yml`; its canonical build definition is
`tools/ci/security-suite/Dockerfile`. The publisher uses the GitHub Actions identity,
`packages: write`, BuildKit `provenance: mode=max`, and BuildKit SBOM generation.

| Component | Version |
| --- | --- |
| grype | 0.104.1 |
| syft | 1.30.0 |
| cosign | 2.5.3 |
| pip-audit | 2.9.0 |
| pip-licenses | 5.0.0 |
| Python | 3.12.10 |
| Node.js | 22.17.0 |
| uv | 0.11.6 |
| pnpm | 10.18.1 |

## Digest lookup and verification

After a successful publisher run, copy the digest-qualified reference from the
`security-suite-digest-<commit>` artifact (or the workflow summary). Independently
confirm the registry manifest before updating the consumer:

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin
IMAGE=ghcr.io/value-fabric/ci-tools/security-suite@sha256:<digest>
docker pull "$IMAGE"
docker image inspect --format '{{json .RepoDigests}}' "$IMAGE"
```

Verify the GitHub Actions provenance attached by BuildKit. The certificate identity
must name the trusted publisher workflow:

```bash
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp='https://github.com/value-fabric/ci-tools/.github/workflows/publish-ci-tools.yml@refs/heads/main' \
  --certificate-oidc-issuer='https://token.actions.githubusercontent.com' \
  ghcr.io/value-fabric/ci-tools/security-suite@sha256:<digest>
```

Use a token with `read:packages` only when the package is private. GitHub Actions in
this repository uses `${{ github.token }}` and the workflow-level `packages: read`
permission. The `ci-tools-preflight` job pulls the exact digest, checks `RepoDigests`,
and asserts all nine tool/runtime versions before container-dependent jobs start.

## Rotation

1. Update explicit versions in the Dockerfile; keep the Python base tag and manifest
   digest pinned together.
2. Review upstream release notes and security advisories.
3. Merge in the trusted publisher repository and run `Publish CI Tools Security Suite`.
4. Download its digest record, authenticate with package-read access, pull by digest,
   verify provenance, inspect `RepoDigests`, and execute the nine version checks.
5. Replace `CI_TOOLS_IMAGE` with that verified digest-qualified reference. Never add a
   tag-only or `latest` fallback.
6. Run `python -m pytest tests/ci/test_supply_chain_ci_tools_policy.py
   --no-mandatory-dep-check -q` and the workflow-reference checks, then merge through
   normal review.
7. Retain the previous digest for rollback. Roll back only by restoring that known-good
   digest-qualified reference.
