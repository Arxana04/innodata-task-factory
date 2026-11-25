"""Deliberately Broken Reference Behavior Check.

Requirements (Section 2.E):
"For at least one task, intentionally break an existing reference behavior in
a throwaway checkout and verify that the tests detect it."

This proves that our acceptance tests are non-vacuous (they don't simply pass everything).
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from validation_system.runners.solution_runner import SolutionRunner
from validation_system.runners.test_runner import TestResult, TestRunner


class BrokenReferenceChecker:
    """Verifies that intentional reference breakages are caught by tests."""

    def __init__(self, click_repo: Path, python_executable: Path):
        self.solution_runner = SolutionRunner(click_repo)
        self.test_runner = TestRunner(python_executable)

    def run_broken_check(
        self,
        task_dir: Path,
        logs_dir: Path,
    ) -> Dict[str, Any]:
        """Applies reference patch, introduces an intentional flaw, and runs verifier."""
        task_dir = task_dir.resolve()
        logs_dir = logs_dir.resolve()
        logs_dir.mkdir(parents=True, exist_ok=True)

        task_name = task_dir.name
        with tempfile.TemporaryDirectory(prefix="broken-check-") as tmp_dir:
            checkout = Path(tmp_dir) / "click"
            self.solution_runner.create_isolated_checkout(checkout)

            # Apply correct reference patch
            patch_file = task_dir / "solution/reference.patch"
            self.solution_runner.apply_patch(checkout, patch_file)

            # Introduce deliberate bug:
            # In datetime-bounds, the feature adds min/max bounds checking.
            # In src/click/types.py, change 'self.min and value < self.min' to '<='
            types_file = checkout / "src/click/types.py"
            original_code = types_file.read_text()

            # Target the min bounds check
            if "if self.min is not None and value < self.min:" in original_code:
                broken_code = original_code.replace(
                    "if self.min is not None and value < self.min:",
                    "if self.min is not None and value <= self.min:",
                )
            elif "value < self.min" in original_code:
                broken_code = original_code.replace("value < self.min", "value <= self.min")
            else:
                # Fallback: break DateTime.convert return
                broken_code = original_code.replace(
                    "return value",
                    "return None",
                    1,
                )

            types_file.write_text(broken_code)

            # Execute verifier on the broken code
            result: TestResult = self.test_runner.run_tests_with_verifier(
                task_dir=task_dir,
                checkout_dir=checkout,
                logs_dir=logs_dir / "broken_run",
                run_type="oracle",
            )

            # The tests must fail or reward must decrease below 1.0!
            detected = (result.reward is not None and result.reward < 1.0) or (result.feature_failed > 0)

            return {
                "task": task_name,
                "mutation": "Altered min boundary check from '<' to '<='",
                "reward": result.reward,
                "feature_passed": result.feature_passed,
                "feature_failed": result.feature_failed,
                "regression_passed": result.regression_passed,
                "regression_failed": result.regression_failed,
                "breakage_detected": detected,
                "logs": result.log_path,
                "verdict": "PASS (Breakage accurately detected by verifier)" if detected else "FAIL (Uncaught breakage)",
            }
