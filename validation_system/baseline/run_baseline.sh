#!/usr/bin/env bash
set -euo pipefail

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOGS_DIR="${PROJECT_ROOT}/results/baseline"

mkdir -p "${LOGS_DIR}"

export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"

IMAGE_NAME="click-baseline:8.5.1"
LOG_FILE="${LOGS_DIR}/docker_baseline.log"

echo "=== [1/2] Building Click 8.5.1 Baseline Docker Image (${IMAGE_NAME}) ==="
docker build -t "${IMAGE_NAME}" -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}"

echo "=== [2/2] Running Click Test Suite inside Docker Container ==="
docker run --rm "${IMAGE_NAME}" pytest -q | tee "${LOG_FILE}"

echo "=== Baseline Test Execution Finished. Log saved to: ${LOG_FILE} ==="
