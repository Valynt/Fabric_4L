# syntax=docker/dockerfile:1.7
# Python is pinned by patch version and immutable Docker Hub manifest digest.
FROM python:3.12.10-slim-bookworm@sha256:85824326bc4ae27a1abb5bc0dd9e08847aa5fe73d8afb593b1b45b7cb4180f57

ARG TARGETARCH
ARG GRYPE_VERSION=0.104.1
ARG SYFT_VERSION=1.30.0
ARG COSIGN_VERSION=2.5.3
ARG PIP_AUDIT_VERSION=2.9.0
ARG PIP_LICENSES_VERSION=5.0.0
ARG UV_VERSION=0.11.6
ARG NODE_VERSION=22.17.0
ARG PNPM_VERSION=10.18.1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl git xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && test "${TARGETARCH}" = "amd64" \
    && curl --fail --location --silent --show-error \
      "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/grype_${GRYPE_VERSION}_linux_amd64.tar.gz" \
      | tar -xz -C /usr/local/bin grype \
    && curl --fail --location --silent --show-error \
      "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/syft_${SYFT_VERSION}_linux_amd64.tar.gz" \
      | tar -xz -C /usr/local/bin syft \
    && curl --fail --location --silent --show-error --output /usr/local/bin/cosign \
      "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64" \
    && chmod 0755 /usr/local/bin/cosign \
    && curl --fail --location --silent --show-error \
      "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
      | tar -xJ --strip-components=1 -C /usr/local \
    && pip install --no-cache-dir \
      "pip-audit==${PIP_AUDIT_VERSION}" \
      "pip-licenses==${PIP_LICENSES_VERSION}" \
      "uv==${UV_VERSION}" \
    && corepack enable \
    && corepack prepare "pnpm@${PNPM_VERSION}" --activate

LABEL org.opencontainers.image.source="https://github.com/value-fabric/ci-tools" \
      org.opencontainers.image.description="Pinned Value Fabric supply-chain security toolchain"

# Match the GitHub-hosted runner UID so mounted workspaces remain writable while
# the security toolchain itself executes without root privileges.
USER 1001:1001
