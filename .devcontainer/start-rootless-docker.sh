#!/usr/bin/env bash
set -euo pipefail

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DOCKER_HOST="unix://${XDG_RUNTIME_DIR}/docker.sock"
mkdir -p "$XDG_RUNTIME_DIR" "$HOME/.local/share/docker"

rootless_script=/usr/share/docker.io/contrib/dockerd-rootless.sh
if [[ ! -x "$rootless_script" ]]; then
  echo "ERROR: rootless Docker launcher is unavailable in the pinned base toolchain." >&2
  exit 1
fi

exec "$rootless_script" \
  --host="$DOCKER_HOST" \
  --host=tcp://0.0.0.0:2375 \
  --storage-driver=vfs \
  --iptables=false \
  --log-level=warn
