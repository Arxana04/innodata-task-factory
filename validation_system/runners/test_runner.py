"""Test Runner: Loads tasks dynamically and executes tests locally.

Distinguishes between:
- Feature tests (fail_to_pass.json): Expected to FAIL on NOP, PASS on Oracle.
- Regression tests (pass_to_pass.json): Expected to PASS on both NOP and Oracle.
Captures stdout, stderr, execution duration, and structured results.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TestResult:
    task_name: str
    run_type: str  # "nop" or "oracle"
    reward: Optional[float]
    expected_reward: float
    feature_passed: int
    feature_failed: int
    feature_total: int
    regression_passed: int
    regression_failed: int
    regression_total: int
    duration_sec: float
    success: bool
    log_path: str
    error_message: Optional[str] = None


class TestRunner:
    """Reusable runner that executes and grades tasks against a given Click checkout."""

    def __init__(self, python_executable: Optional[Path] = None):
        # Keep a virtualenv interpreter's symlink intact so sys.executable retains venv packages
        self.python_executable = (
            python_executable.absolute() if python_executable else Path(sys.executable).absolute()
        )

    @staticmethod
    def load_task_metadata(task_dir: Path) -> Dict[str, Any]:
        """Loads and parses task.toml metadata without hardcoding task names."""
        task_dir = task_dir.resolve()
        toml_path = task_dir / "task.toml"
        if not toml_path.is_file():
            raise FileNotFoundError(f"task.toml not found in {task_dir}")
        return tomllib.loads(toml_path.read_text())

    def run_tests_with_verifier(
        self,
        task_dir: Path,
        checkout_dir: Path,
        logs_dir: Path,
        run_type: str = "oracle",
    ) -> TestResult:
        """Executes tests using the task's verify.py against checkout_dir."""
        task_dir = task_dir.resolve()
        checkout_dir = checkout_dir.resolve()
        logs_dir = logs_dir.resolve()
        logs_dir.mkdir(parents=True, exist_ok=True)

        metadata = self.load_task_metadata(task_dir)
        task_name = task_dir.name
        expected_reward = 0.0 if run_type == "nop" else 1.0

        features_spec = json.loads((task_dir / "tests/fail_to_pass.json").read_text())
        regressions_spec = json.loads((task_dir / "tests/pass_to_pass.json").read_text())

        start_time = time.time()
        verifier_script = task_dir / "tests/verify.py"

        log_file = logs_dir / f"{task_name}_{run_type}.log"
        proc = subprocess.run(
            [
                str(self.python_executable),
                str(verifier_script),
                "--repo",
                str(checkout_dir),
                "--logs",
                str(logs_dir),
            ],
            capture_output=True,
            text=True,
        )
        duration = round(time.time() - start_time, 3)

        # Write execution logs
        full_log = f"=== STDOUT ===\n{proc.stdout}\n=== STDERR ===\n{proc.stderr}"
        log_file.write_text(full_log)

        # Parse reward
        reward_file = logs_dir / "reward.txt"
        reward = float(reward_file.read_text().strip()) if reward_file.is_file() else None

        # Parse XML reports for detailed counts
        reg_passed = reg_failed = 0
        feat_passed = feat_failed = 0

        reg_xml = logs_dir / "regressions.xml"
        if reg_xml.is_file():
            cases = ET.parse(reg_xml).findall(".//testcase")
            reg_passed = sum(len(c) == 0 for c in cases)
            reg_failed = sum(c.find("failure") is not None for c in cases)

        feat_xml = logs_dir / "features.xml"
        if feat_xml.is_file():
            cases = ET.parse(feat_xml).findall(".//testcase")
            feat_passed = sum(len(c) == 0 for c in cases)
            feat_failed = sum(c.find("failure") is not None for c in cases)

        success = proc.returncode == 0 and reward == expected_reward

        return TestResult(
            task_name=task_name,
            run_type=run_type,
            reward=reward,
            expected_reward=expected_reward,
            feature_passed=feat_passed,
            feature_failed=feat_failed,
            feature_total=len(features_spec),
            regression_passed=reg_passed,
            regression_failed=reg_failed,
            regression_total=len(regressions_spec),
            duration_sec=duration,
            success=success,
            log_path=str(log_file),
            error_message=None if success else f"Return code {proc.returncode}, reward {reward}",
        )
