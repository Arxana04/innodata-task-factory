#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== Building and Verifying Click 8.5.1 Baseline Container ==="
"${PROJECT_ROOT}/validation_system/baseline/run_baseline.sh"
