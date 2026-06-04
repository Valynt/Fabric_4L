# Container Policy

## Production Dockerfiles

Production Dockerfiles are:

- `apps/web/Dockerfile`
- `services/api/Dockerfile`
- `services/layer1-ingestion/Dockerfile`
- `services/layer2-extraction/Dockerfile`
- `services/layer2-5-signal-refinery/Dockerfile`
- `services/layer3-knowledge/Dockerfile`
- `services/layer4-agents/Dockerfile`
- `services/layer5-ground-truth/Dockerfile`
- `services/layer6-benchmarks/Dockerfile`

## Base Image Pinning

Production base images must use one of:

- A digest-pinned reference with `@sha256:`.
- A patch-pinned runtime tag such as `python:3.11.13-slim-bookworm`.
- A centrally controlled build argument whose default is patch-pinned.

Do not use:

- `latest`
- Major-only tags such as `node:22`
- Minor-only tags such as `python:3.11`
- Floating distribution tags such as `node:22-alpine`

## Runtime Hardening

Production images must:

- Run as a non-root user.
- Include a `HEALTHCHECK`.
- Use frozen dependency installs.
- Be scanned for OS and library vulnerabilities.
- Be signed and verified before promotion.

Local command:

```bash
pnpm container:scan
```

