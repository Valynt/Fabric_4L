# Nebius Cloud Infrastructure Bootstrap for Fabric_4L

This directory contains host-level bootstrapping configuration for deploying Fabric_4L development VMs on [Nebius Cloud](https://nebius.com/).

---

## Architecture Boundaries

The environment enforces strict 3-tier ownership:

| Layer | Owner | Scope / Contents |
|---|---|---|
| **Infrastructure** | `infra/nebius/` | cloud-init, firewall rules (UFW), SSH hardening, fail2ban, Docker daemon |
| **Host OS** | Ubuntu 24.04 LTS | Kernel, AppArmor, systemd, unattended security upgrades |
| **Dev Environment** | `.devcontainer/` | Python 3.11, Node 22, pnpm, uv, kubectl, Infisical, cosign, rootless DinD |

> **Critical Invariant:** The host OS must never install Python, Node.js, pnpm, uv, or application dependencies directly. All runtime dependencies belong inside the containerized `.devcontainer` environment to prevent toolchain and configuration drift.

---

## Step-by-Step Provisioning Guide

### 1. Provision VM on Nebius Cloud

1. In the Nebius Cloud Console, launch a new Compute Instance:
   - **OS / Image**: Ubuntu 24.04 LTS
   - **Resources**: Recommended ≥ 4 vCPU, ≥ 16 GB RAM, ≥ 50 GB NVMe disk
2. Under **Metadata / User Data (Cloud-init)**, paste the contents of [`cloud-init.yaml`](./cloud-init.yaml).
3. Attach your SSH public key.
4. Launch the instance.

### 2. Connect via SSH

Once the instance is in running state:

```bash
ssh ubuntu@<NEBIUS_INSTANCE_IP>
```

### 3. Clone Repository

```bash
git clone https://github.com/bmsull560/Fabric_4L.git
cd Fabric_4L
```

### 4. Launch Dev Container

Install the Dev Container CLI if not already present on your client or run via VS Code Remote - SSH / Dev Containers:

```bash
# Using Dev Container CLI:
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . bash
```

Alternatively, open VS Code or Cursor:
- Connect to host via **Remote - SSH**.
- Open the `/home/ubuntu/Fabric_4L` folder.
- Click **Reopen in Container** when prompted.

### 5. Verify Environment

Inside the running Dev Container:

```bash
.devcontainer/verify.sh
```

All toolchain checks (Python 3.11, Node 22, pnpm, uv, Docker DinD sidecar, kubectl, kustomize, cosign, infisical, gh, make, jq) will validate automatically.
