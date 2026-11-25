"""Harbor Runner: Executes NOP and Oracle evaluations using Harbor 0.25.0.

Requirements:
- Starts task from a clean, containerized Docker environment.
- Enforces network isolation (network_mode = "no-network").
- Validates NOP: Feature FAIL, Regression PASS, Reward 0.0.
- Validates Oracle: Feature PASS, Regression PASS, Reward 1.0.
- Captures Harbor artifacts (result.json, verifier logs, reward.txt).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class HarborRunResult:
    task_id: str
    base_commit: str
    run_type: str  # "nop" or "oracle"
    harbor_version: str
    agent: str
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
    log_location: str
    trial_uri: Optional[str] = None
    error_message: Optional[str] = None


class HarborRunner:
    """Manages execution and evidence extraction for Harbor tasks."""

    def __init__(
        self,
        harbor_executable: Path,
        docker_host: str = "unix:///Users/mahipatni/.colima/default/docker.sock",
    ):
        self.harbor_executable = harbor_executable.resolve()
        self.docker_host = docker_host
        if not self.harbor_executable.is_file():
            raise FileNotFoundError(f"Harbor executable not found at {self.harbor_executable}")

    def run_trial(
        self,
        task_dir: Path,
        agent: str,  # "nop" or "oracle"
        output_dir: Path,
    ) -> HarborRunResult:
        """Runs a single Harbor trial and parses output evidence."""
        task_dir = task_dir.resolve()
        task_name = task_dir.name
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        expected_reward = 0.0 if agent == "nop" else 1.0
        env = dict(os.environ, DOCKER_HOST=self.docker_host)

        start_time = time.time()
        proc = subprocess.run(
            [
                str(self.harbor_executable),
                "run",
                "-p",
                str(task_dir),
                "-a",
                agent,
                "-k",
                "1",
                "-o",
                str(output_dir),
                "--no-delete",
                "-y",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        duration = round(time.time() - start_time, 2)

        # Locate the trial directory
        # Harbor creates output_dir/<timestamp>/<task-name>__<hash>/
        trial_dirs = list(output_dir.glob("*/*__*"))
        if not trial_dirs:
            # Fallback: look for any trial folder
            trial_dirs = list(output_dir.glob("*__*"))

        if not trial_dirs:
            return HarborRunResult(
                task_id=task_name,
                base_commit="cf19179e8e2fd54c601378cec9e0d21bb12b6fb1",
                run_type=agent,
                harbor_version="0.25.0",
                agent=agent,
                reward=None,
                expected_reward=expected_reward,
                feature_passed=0,
                feature_failed=0,
                feature_total=0,
                regression_passed=0,
                regression_failed=0,
                regression_total=0,
                duration_sec=duration,
                success=False,
                log_location=str(output_dir),
                error_message=f"No trial directory created. Stderr: {proc.stderr[:300]}",
            )

        trial_dir = trial_dirs[-1]
        verifier_dir = trial_dir / "verifier"

        # Read reward
        reward_file = verifier_dir / "reward.txt"
        reward = float(reward_file.read_text().strip()) if reward_file.is_file() else None

        # Parse test manifests
        features_json = task_dir / "tests/fail_to_pass.json"
        regressions_json = task_dir / "tests/pass_to_pass.json"
        feature_total = len(json.loads(features_json.read_text())) if features_json.is_file() else 0
        regression_total = len(json.loads(regressions_json.read_text())) if regressions_json.is_file() else 0

        # Parse XML counts
        reg_passed = reg_failed = 0
        feat_passed = feat_failed = 0

        reg_xml = verifier_dir / "regressions.xml"
        if reg_xml.is_file():
            cases = ET.parse(reg_xml).findall(".//testcase")
            reg_passed = sum(len(c) == 0 for c in cases)
            reg_failed = sum(c.find("failure") is not None for c in cases)

        feat_xml = verifier_dir / "features.xml"
        if feat_xml.is_file():
            cases = ET.parse(feat_xml).findall(".//testcase")
            feat_passed = sum(len(c) == 0 for c in cases)
            feat_failed = sum(c.find("failure") is not None for c in cases)

        # Parse result.json
        trial_uri = None
        result_json = trial_dir / "result.json"
        if result_json.is_file():
            try:
                data = json.loads(result_json.read_text())
                trial_uri = data.get("trial_uri")
            except Exception:
                pass

        success = (proc.returncode == 0) and (reward == expected_reward) and (reg_failed == 0)

        return HarborRunResult(
            task_id=task_name,
            base_commit="cf19179e8e2fd54c601378cec9e0d21bb12b6fb1",
            run_type=agent,
            harbor_version="0.25.0",
            agent=agent,
            reward=reward,
            expected_reward=expected_reward,
            feature_passed=feat_passed,
            feature_failed=feat_failed,
            feature_total=feature_total,
            regression_passed=reg_passed,
            regression_failed=reg_failed,
            regression_total=regression_total,
            duration_sec=duration,
            success=success,
            log_location=str(trial_dir),
            trial_uri=trial_uri,
            error_message=None if success else f"Exit code {proc.returncode}, Reward {reward} != {expected_reward}",
        )
