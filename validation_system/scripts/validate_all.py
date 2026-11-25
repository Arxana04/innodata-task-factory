#!/usr/bin/env python3
"""Main Validation Orchestrator: Runs 10 Harbor validations + Broken Check + Evidence Export."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validation_system.collector.evidence_collector import EvidenceCollector
from validation_system.runners.broken_check import BrokenReferenceChecker
from validation_system.runners.harbor_runner import HarborRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end Harbor validation orchestrator.")
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        default=PROJECT_ROOT / "tasks",
        help="Directory containing task packages.",
    )
    parser.add_argument(
        "--click-repo",
        type=Path,
        default=PROJECT_ROOT.parent / "click-8.5.1",
        help="Path to clean Click 8.5.1 checkout.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="Directory to save all results and evidence.",
    )
    parser.add_argument(
        "--task",
        action="append",
        dest="selected_tasks",
        help="Specific task(s) to evaluate. Default: all tasks in tasks-dir.",
    )

    args = parser.parse_args()

    harbor_bin = PROJECT_ROOT / ".venv/bin/harbor"
    python_bin = PROJECT_ROOT / ".venv/bin/python"

    if not harbor_bin.is_file():
        print(f"Error: Harbor not found at {harbor_bin}. Run setup first.", file=sys.stderr)
        return 1

    harbor_runner = HarborRunner(harbor_executable=harbor_bin)
    evidence_collector = EvidenceCollector(results_dir=args.results_dir)

    # Set baseline info
    evidence_collector.set_baseline({
        "target": "Click 8.5.1 (commit cf19179e8e2fd54c601378cec9e0d21bb12b6fb1)",
        "local_passed": 2433,
        "local_skipped": 25,
        "local_xfailed": 1,
        "docker_passed": 2434,
        "docker_skipped": 24,
        "docker_xfailed": 1,
    })

    # Discover tasks
    available_tasks = sorted(p for p in args.tasks_dir.iterdir() if p.is_dir() and (p / "task.toml").is_file())
    if args.selected_tasks:
        tasks_to_run = [p for p in available_tasks if p.name in args.selected_tasks]
    else:
        tasks_to_run = available_tasks

    print("=" * 80)
    print(f"Starting Harbor Validation Suite across {len(tasks_to_run)} tasks (Total: {len(tasks_to_run) * 2} runs)")
    print("=" * 80)

    all_passed = True

    for idx, task_path in enumerate(tasks_to_run, 1):
        task_name = task_path.name
        print(f"\n[{idx}/{len(tasks_to_run)}] Evaluating Task: {task_name}")

        for agent in ("nop", "oracle"):
            print(f"  -> Running Harbor {agent.upper()} agent...")
            out_dir = args.results_dir / "harbor" / task_name / agent
            run_res = harbor_runner.run_trial(task_dir=task_path, agent=agent, output_dir=out_dir)
            evidence_collector.add_harbor_run(run_res)

            status_str = "PASS" if run_res.success else "FAIL"
            print(
                f"     Result: {status_str} | Reward: {run_res.reward} (Expected: {run_res.expected_reward}) "
                f"| Feat: {run_res.feature_passed}/{run_res.feature_total} "
                f"| Reg: {run_res.regression_passed}/{run_res.regression_total} "
                f"| Time: {run_res.duration_sec}s"
            )
            if not run_res.success:
                all_passed = False
                if run_res.error_message:
                    print(f"     Error: {run_res.error_message}")

    # Run Deliberately Broken Reference Check
    print("\n" + "=" * 80)
    print("Running Deliberately Broken Reference Behavior Check...")
    print("=" * 80)
    broken_checker = BrokenReferenceChecker(click_repo=args.click_repo, python_executable=python_bin)
    target_broken_task = args.tasks_dir / "datetime-bounds"
    broken_res = broken_checker.run_broken_check(
        task_dir=target_broken_task,
        logs_dir=args.results_dir / "broken_check",
    )
    evidence_collector.set_broken_check(broken_res)
    print(f"  Task: {broken_res['task']}")
    print(f"  Mutation: {broken_res['mutation']}")
    print(f"  Reward Dropped: {broken_res['reward']} (Feature Failed: {broken_res['feature_failed']}, Feat Passed: {broken_res['feature_passed']})")
    print(f"  Verdict: {broken_res['verdict']}")

    # Export all reports
    print("\n" + "=" * 80)
    print("Exporting Validation Evidence & Reports...")
    print("=" * 80)
    evidence_collector.export_all()
    print(f"  -> JSON Report: {args.results_dir / 'summary.json'}")
    print(f"  -> CSV Report:  {args.results_dir / 'summary.csv'}")
    print(f"  -> Markdown:    {args.results_dir / 'validation_report.md'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
