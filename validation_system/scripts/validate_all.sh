#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"

# Execute the python validation orchestrator inside our Python 3.12 virtualenv
exec "${PROJECT_ROOT}/.venv/bin/python" "${SCRIPT_DIR}/validate_all.py" "$@"
