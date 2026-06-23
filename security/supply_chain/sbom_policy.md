# SBOM Policy

## Requirement

All production builds must generate SBOM evidence:

- Pull requests and pushes generate source SBOMs for each maintained backend layer.
- Production image verification generates CycloneDX and SPDX SBOMs for backend service images and `apps-web`.
- CI uploads SBOM and vulnerability scan artifacts with retention suitable for release evidence.
- Deploy validation must reject missing, empty, unsigned, or digest-mismatched SBOM artifacts.

## Format

Required formats:

- CycloneDX JSON for scanner interoperability and vulnerability evaluation.
- SPDX JSON for license and compliance exchange.

Local command:

```bash
pnpm sbom
```

The local command writes:

- `artifacts/supply-chain/fabric-4l-source-sbom.cdx.json`
- `artifacts/supply-chain/sbom-summary.json`

## Ownership

Security Engineering owns this policy. SRE owns image build and deploy enforcement. Service owners are responsible for resolving dependency inventory drift in their layers.

## Failure Policy

Production promotion fails when:

- A required SBOM is missing or empty.
- An SBOM does not reference the expected image or source scope.
- A deployed image digest does not match the SBOM subject.
- SBOM vulnerability evaluation reports unapproved critical or high findings.

