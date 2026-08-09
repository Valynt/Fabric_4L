FROM mcr.microsoft.com/devcontainers/base@sha256:1a00517e89d3075f8c9dc8d9911404de0ff8991a4d71c62068573e9b016a89da

# Install build tools not present in base image
# (curl, wget, git, gnupg, ca-certificates, jq are already in devcontainers/base:bookworm)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install Infisical CLI (secret management)
RUN curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash \
    && apt-get install -y infisical \
    && rm -rf /var/lib/apt/lists/*

# Install Docker Compose v2 plugin (pinned, arch-aware)
ARG COMPOSE_VERSION=v2.35.1
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Install kubectl (pinned to 1.29 stable)
RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key \
    | gpg --dearmor -o /usr/share/keyrings/kubernetes-apt-keyring.gpg && \
    echo 'deb [signed-by=/usr/share/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' \
    | tee /etc/apt/sources.list.d/kubernetes.list && \
    apt-get update && apt-get install -y kubectl && rm -rf /var/lib/apt/lists/*

# Install kustomize (pinned, arch-aware — avoids curl|bash install pattern)
ARG KUSTOMIZE_VERSION=v5.4.3
RUN ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') && \
    curl -fsSL "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_${ARCH}.tar.gz" \
    | tar -xz -C /usr/local/bin/ kustomize

# Install cosign for image signing (pinned, arch-aware)
ARG COSIGN_VERSION=v2.4.1
RUN ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') && \
    curl -fsSLO "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-${ARCH}" && \
    chmod +x "cosign-linux-${ARCH}" && \
    mv "cosign-linux-${ARCH}" /usr/local/bin/cosign

# Set up Python path for workspace (all six layers + layer 2.5)
ENV PYTHONPATH=/workspace/services/layer1-ingestion/src:/workspace/services/layer2-extraction/src:/workspace/services/layer2-5-signal-refinery/src:/workspace/services/layer3-knowledge/src:/workspace/services/layer4-agents/src:/workspace/services/layer5-ground-truth/src:/workspace/services/layer6-benchmarks/src

# Ensure persistent temp directory exists for vscode user (fixes Windsurf server install race)
RUN mkdir -p /var/tmp && chown vscode:vscode /var/tmp && chmod 1777 /var/tmp

WORKDIR /workspace
