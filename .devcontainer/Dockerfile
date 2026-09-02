# syntax=docker/dockerfile:1.7
FROM mcr.microsoft.com/devcontainers/base@sha256:b8c3669fb4cc652621b3386517c40ab3e151e827de958d6fe75528798ffb5727 AS toolchain

ARG COMPOSE_VERSION=v2.35.1
ARG KUBECTL_VERSION=v1.29.15
ARG KUSTOMIZE_VERSION=v5.4.3
ARG COSIGN_VERSION=v2.4.1
ARG INFISICAL_VERSION=0.41.11
ARG UV_VERSION=0.11.6

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential docker.io uidmap dbus-user-session slirp4netns fuse-overlayfs \
      pipx make jq curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN PIPX_BIN_DIR=/usr/local/bin PIPX_HOME=/opt/pipx pipx install "uv==${UV_VERSION}" \
    && uv --version

RUN arch="$(dpkg --print-architecture)" \
    && case "$arch" in amd64|arm64) ;; *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; esac \
    && curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${arch}" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose \
    && chmod 0755 /usr/local/lib/docker/cli-plugins/docker-compose \
    && curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl" -o /usr/local/bin/kubectl \
    && chmod 0755 /usr/local/bin/kubectl \
    && curl -fsSL "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_${arch}.tar.gz" \
      | tar -xz -C /usr/local/bin kustomize \
    && curl -fsSL "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-${arch}" -o /usr/local/bin/cosign \
    && chmod 0755 /usr/local/bin/cosign \
    && curl -fsSL "https://github.com/Infisical/infisical/releases/download/infisical-cli%2Fv${INFISICAL_VERSION}/infisical_${INFISICAL_VERSION}_linux_${arch}.deb" -o /tmp/infisical.deb \
    && dpkg -i /tmp/infisical.deb \
    && rm /tmp/infisical.deb

RUN mkdir -p /workspace/Fabric_4L /workspace-support /run/user/1000 /var/tmp \
    && chown -R vscode:vscode /workspace/Fabric_4L /workspace-support /run/user/1000 /var/tmp \
    && chmod 0700 /run/user/1000 \
    && chmod 1777 /var/tmp

ENV PYTHONPATH=/workspace/Fabric_4L/packages/shared/src:/workspace/Fabric_4L/services/api:/workspace/Fabric_4L/services/layer1-ingestion/src:/workspace/Fabric_4L/services/layer2-extraction/src:/workspace/Fabric_4L/services/layer2-5-signal-refinery/src:/workspace/Fabric_4L/services/layer3-knowledge/src:/workspace/Fabric_4L/services/layer4-agents/src:/workspace/Fabric_4L/services/layer5-ground-truth/src:/workspace/Fabric_4L/services/layer6-benchmarks/src:/workspace/Fabric_4L/services/layer7-billing/src
WORKDIR /workspace/Fabric_4L
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD bash -lc 'test -d /workspace/Fabric_4L && test -w /var/tmp'

FROM toolchain AS development
USER vscode
ENV PNPM_HOME=/home/vscode/.local/share/pnpm
ENV PATH="${PNPM_HOME}:${PATH}"

FROM toolchain AS docker-daemon
COPY --chown=vscode:vscode .devcontainer/start-rootless-docker.sh /workspace-support/start-rootless-docker.sh
RUN chmod 0755 /workspace-support/start-rootless-docker.sh
USER vscode
