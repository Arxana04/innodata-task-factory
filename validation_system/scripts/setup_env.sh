#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== [1/4] Creating Python 3.12 Virtual Environment ==="
cd "${PROJECT_ROOT}"
uv venv --python 3.12 .venv

echo "=== [2/4] Installing Harbor 0.25.0 and Testing Dependencies ==="
uv pip install --python .venv harbor==0.25.0 pytest==9.0.2 iniconfig==2.3.0 packaging==26.0 pluggy==1.6.0 pygments==2.20.0 flit-core==3.12.0 docker

echo "=== [3/4] Ensuring Docker Compose and Buildx Plugins are Linked ==="
mkdir -p "${HOME}/.docker/cli-plugins"
if [ -f "/opt/homebrew/lib/docker/cli-plugins/docker-compose" ]; then
    ln -sf /opt/homebrew/lib/docker/cli-plugins/docker-compose "${HOME}/.docker/cli-plugins/docker-compose"
fi
if [ -f "/opt/homebrew/lib/docker/cli-plugins/docker-buildx" ]; then
    ln -sf /opt/homebrew/lib/docker/cli-plugins/docker-buildx "${HOME}/.docker/cli-plugins/docker-buildx"
fi

echo "=== [4/4] Verifying Setup ==="
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
"${PROJECT_ROOT}/.venv/bin/harbor" --version
"${PROJECT_ROOT}/.venv/bin/pytest" --version
docker compose version
docker buildx version

echo "=== Setup Complete! ==="
