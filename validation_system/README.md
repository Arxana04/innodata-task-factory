# Innodata AI Hackathon — Validation & Infrastructure Pipeline

This directory contains the modular validation system for evaluating five independent Harbor coding tasks generated from Click 8.5.1 (`cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`).

---

## Architecture Overview

```text
validation_system/
├── baseline/
│   ├── Dockerfile         # Dockerfile to build & test original Click 8.5.1 baseline
│   └── run_baseline.sh    # Executes original 2,433 Click tests in container
├── runners/
│   ├── solution_runner.py # Manages isolated Git checkouts and patch applications
│   ├── test_runner.py     # Executes task verifier and parses feature/regression XML
│   ├── harbor_runner.py   # Orchestrates Harbor 0.25.0 NOP & Oracle container trials
│   └── broken_check.py    # Injects deliberate bug to test non-vacuousness
├── collector/
│   └── evidence_collector.py # Gathers metrics into JSON, CSV, and Markdown
└── scripts/
    ├── setup_env.sh       # One-click environment setup (uv, venv, Harbor 0.25.0)
    ├── build_baseline.sh  # Runs baseline verification
    ├── validate_all.py    # Python orchestrator
    └── validate_all.sh    # Single-command execution of all 10 Harbor runs
```

---

## Quick Start / Reproducibility

### 1. Prerequisites
- macOS (Apple Silicon or Intel) or Linux
- Docker Engine running (via Colima or Docker Desktop)
- `uv` installed (`brew install uv`)

### 2. Setup Environment
```bash
./validation_system/scripts/setup_env.sh
```

### 3. Run Baseline Verification
```bash
./validation_system/scripts/build_baseline.sh
```
Target: **2,434 passed, 24 skipped, 1 xfailed** inside Docker Debian container.

### 4. Run Full Validation Suite (10 Harbor Runs + Broken Check)
```bash
./validation_system/scripts/validate_all.sh
```

---

## Results & Evidence
All artifacts, metrics, and logs are automatically exported to `results/`:
- `results/summary.json`: Complete machine-readable summary.
- `results/summary.csv`: Tabular spreadsheet data for presentation and grading.
- `results/validation_report.md`: Formatted markdown summary report.
- `results/harbor/`: Full trial trajectories, verifier XMLs, and logs for each run.
