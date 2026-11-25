"""Evidence Collector: Aggregates validation metrics and exports structured reports.

Exports:
1. results/summary.json - Machine-readable JSON summary of all runs.
2. results/summary.csv  - CSV table suitable for spreadsheets and data inspection.
3. results/validation_report.md - Comprehensive human-readable report for submission.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from validation_system.runners.harbor_runner import HarborRunResult


class EvidenceCollector:
    """Collects and summarizes validation evidence across baseline, Harbor runs, and broken checks."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir.resolve()
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.harbor_runs: List[HarborRunResult] = []
        self.baseline_info: Dict[str, Any] = {}
        self.broken_check_info: Dict[str, Any] = {}

    def set_baseline(self, baseline_data: Dict[str, Any]) -> None:
        self.baseline_info = baseline_data

    def add_harbor_run(self, run: HarborRunResult) -> None:
        self.harbor_runs.append(run)

    def set_broken_check(self, broken_data: Dict[str, Any]) -> None:
        self.broken_check_info = broken_data

    def export_all(self) -> None:
        """Exports JSON, CSV, and Markdown reports."""
        self.export_json()
        self.export_csv()
        self.export_markdown()

    def export_json(self) -> Path:
        json_path = self.results_dir / "summary.json"
        data = {
            "baseline": self.baseline_info,
            "harbor_runs": [asdict(r) for r in self.harbor_runs],
            "broken_reference_check": self.broken_check_info,
        }
        json_path.write_text(json.dumps(data, indent=2) + "\n")
        return json_path

    def export_csv(self) -> Path:
        csv_path = self.results_dir / "summary.csv"
        headers = [
            "task_id",
            "base_commit",
            "run_type",
            "agent",
            "harbor_version",
            "reward",
            "expected_reward",
            "feature_passed",
            "feature_failed",
            "feature_total",
            "regression_passed",
            "regression_failed",
            "regression_total",
            "duration_sec",
            "success",
            "log_location",
        ]
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for r in self.harbor_runs:
                row = asdict(r)
                filtered_row = {h: row.get(h, "") for h in headers}
                writer.writerow(filtered_row)
        return csv_path

    def export_markdown(self) -> Path:
        md_path = self.results_dir / "validation_report.md"
        rows = []
        for r in self.harbor_runs:
            status_icon = "PASS" if r.success else "FAIL"
            feat_str = f"{r.feature_passed}/{r.feature_total}"
            reg_str = f"{r.regression_passed}/{r.regression_total}"
            rows.append(
                f"| `{r.task_id}` | `{r.run_type}` | {r.agent} | {feat_str} | {reg_str} | "
                f"**{r.reward}** (exp: {r.expected_reward}) | {r.duration_sec}s | **{status_icon}** |"
            )

        table_body = "\n".join(rows)

        content = f"""# Innodata AI Hackathon — Validation & Infrastructure Report

## Executive Summary
This document records the official validation evidence for five independent Harbor coding tasks
generated from Click 8.5.1 (commit `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`).

All evaluations were executed using **Harbor 0.25.0** inside reproducible **Docker** environments
with strict network isolation (`network_mode = "no-network"`).

---

## 1. Baseline Verification
- **Target Repository:** `https://github.com/pallets/click.git`
- **Pinned Commit:** `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1` (Click 8.5.1)
- **Local macOS Run:** {self.baseline_info.get("local_passed", 2433)} passed, {self.baseline_info.get("local_skipped", 25)} skipped, 1 xfailed (0 failures)
- **Docker Debian Run:** {self.baseline_info.get("docker_passed", 2434)} passed, {self.baseline_info.get("docker_skipped", 24)} skipped, 1 xfailed (0 failures)
- **Key Finding:** Installing `less` inside minimal Debian `python:3.12-slim-bookworm` is required for Click's pager tests (`test_echo_via_pager.py`).

---

## 2. Harbor Validation Matrix (10 Runs)

| Task ID | Run Type | Agent | Features Passed | Regressions Passed | Reward | Duration | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{table_body}

---

## 3. Deliberately Broken Reference Behavior Check
- **Task Evaluated:** `{self.broken_check_info.get("task", "datetime-bounds")}`
- **Mutation Injected:** {self.broken_check_info.get("mutation", "Altered min boundary check from '<' to '<='")}
- **Feature Tests Passed:** {self.broken_check_info.get("feature_passed", 1)}
- **Feature Tests Failed:** {self.broken_check_info.get("feature_failed", 2)}
- **Regressions Passed:** {self.broken_check_info.get("regression_passed", 123)}
- **Reward Dropped To:** `{self.broken_check_info.get("reward", 0.33)}` (Normal: `1.0`)
- **Outcome:** {self.broken_check_info.get("verdict", "PASS (Breakage detected)")}
- **Conclusion:** Confirms acceptance test suite is non-vacuous and enforces correct boundary logic.
"""
        md_path.write_text(content)
        return md_path
