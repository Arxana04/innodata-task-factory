"""Grade a single task using local pytest results."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def run_tests(
    repo: Path, logs: Path, name: str, targets: list[str]
) -> tuple[int, int]:
    report = logs / f"{name}.xml"
    env = dict(os.environ, PYTHONPATH=str(repo / "src"))
    with (logs / f"{name}.log").open("w") as log:
        status = subprocess.run(
            [
                sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                f"--junitxml={report}", *targets,
            ],
            cwd=repo,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        ).returncode
    if status not in (0, 1) or not report.is_file():
        raise RuntimeError(f"{name} could not run. See {logs / (name + '.log')}")
    cases = ET.parse(report).findall(".//testcase")
    passed = sum(len(case) == 0 for case in cases)
    failed = sum(case.find("failure") is not None for case in cases)
    if not cases or any(case.find("error") is not None for case in cases):
        raise RuntimeError(f"{name} reported a test execution error.")
    print(f"{name}: {passed} passed, {failed} failed, {len(cases) - passed - failed} skipped")
    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    args = parser.parse_args()

    tests = Path(__file__).resolve().parent
    repo = args.repo.resolve()
    logs = args.logs.resolve()
    logs.mkdir(parents=True, exist_ok=True)
    reward_file = logs / "reward.txt"
    reward_file.unlink(missing_ok=True)

    features = json.loads((tests / "fail_to_pass.json").read_text())
    regressions = json.loads((tests / "pass_to_pass.json").read_text())
    if not features or not regressions:
        raise ValueError("Both test manifests must contain selectors.")

    regression_passed, regression_failed = run_tests(repo, logs, "regressions", regressions)
    feature_passed, feature_failed = run_tests(
        repo, logs, "features", [str(tests / name) for name in features]
    )
    if regression_passed + regression_failed == 0 or feature_passed + feature_failed != len(features):
        raise RuntimeError("Expected tests were skipped or did not run.")

    reward = 0.0 if regression_failed else feature_passed / len(features)
    reward_file.write_text(f"{reward}\n")
    print(f"reward: {reward}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
