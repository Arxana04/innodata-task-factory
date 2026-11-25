"""Generate Harbor tasks from a clean Click checkout."""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from textwrap import dedent

from recipes import RECIPES, Recipe

BASE_COMMIT = "cf19179e8e2fd54c601378cec9e0d21bb12b6fb1"
UPSTREAM = "https://github.com/pallets/click.git"
ROOT = Path(__file__).resolve().parent
TEST_FILE = "test_feature.py"
LOCKED_TEST_PACKAGES = ("pytest", "iniconfig", "packaging", "pluggy", "pygments")


def git(repo: Path, *args: str, strip: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip("\n") if strip else result.stdout


def check_checkout(repo: Path, commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("--commit must be a full, lowercase 40-character Git SHA.")
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("--repo must point to the root of the Click checkout.")
    if git(repo, "rev-parse", "HEAD") != commit:
        raise ValueError(f"Check out {commit} before generating or verifying tasks.")
    if git(repo, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("The starter checkout must be clean, including untracked files.")


def read_source(repo: Path, commit: str, path: str) -> str:
    return git(repo, "show", f"{commit}:{path}", strip=False)


def render_patch(repo: Path, commit: str, recipe: Recipe) -> str:
    originals: dict[str, str] = {}
    transformed: dict[str, str] = {}
    for edit in recipe.edits:
        if edit.path not in originals:
            source = read_source(repo, commit, edit.path)
            originals[edit.path] = transformed[edit.path] = source
        transformed[edit.path] = edit.apply(transformed[edit.path])

    patches = []
    for path, source in transformed.items():
        compile(source, path, "exec")
        if source == originals[path]:
            raise ValueError(f"{recipe.id} did not change {path}.")
        changes = difflib.unified_diff(
            originals[path].splitlines(keepends=True),
            source.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        patches.append(f"diff --git a/{path} b/{path}\n" + "".join(changes))
    return "".join(patches)


def write_package(directory: Path, recipe: Recipe, repo: Path, commit: str) -> None:
    source = dedent(recipe.tests).lstrip()
    test_names = [
        node.name
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    if not test_names:
        raise ValueError(f"{recipe.id} defines no feature test functions.")

    lock = tomllib.loads(read_source(repo, commit, "uv.lock"))
    versions = {package["name"]: package["version"] for package in lock["package"]}
    requirements = " ".join(
        f"{name}=={versions[name]}" for name in LOCKED_TEST_PACKAGES
    )
    for section in ("environment", "solution", "tests"):
        (directory / section).mkdir(parents=True)

    (directory / "instruction.md").write_text(dedent(recipe.instruction).lstrip())
    (directory / "task.toml").write_text(
        f'''schema_version = "1.4"

[metadata]
repository = "{UPSTREAM}"
base_commit = "{commit}"
license = "BSD-3-Clause"
category = "software-engineering"
feature = "{recipe.id}"

[verifier]
timeout_sec = 300.0

[agent]
timeout_sec = 900.0

[environment]
workdir = "/app"
network_mode = "no-network"
'''
    )
    (directory / "environment/Dockerfile").write_text(
        f'''FROM python:3.12-slim-bookworm

RUN apt-get update \\
    && apt-get install -y --no-install-recommends ca-certificates git \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git init \\
    && git remote add origin {UPSTREAM} \\
    && git fetch --depth=1 origin {commit} \\
    && git checkout --detach FETCH_HEAD \\
    && test "$(git rev-parse HEAD)" = "{commit}"

RUN python -m pip install --no-cache-dir --no-deps {requirements} flit-core==3.12.0 \\
    && python -m pip install --no-cache-dir --no-deps --no-build-isolation -e .
'''
    )
    patch = directory / "solution/reference.patch"
    patch.write_text(render_patch(repo, commit, recipe))
    git(repo, "apply", "--check", str(patch))
    (directory / "solution/solve.sh").write_text(
        '#!/bin/sh\nset -eu\n'
        'solution_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'git -C "${1:-/app}" apply "$solution_dir/reference.patch"\n'
    )
    (directory / "tests/test.sh").write_text(
        '#!/bin/sh\nset -eu\n'
        'tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'exec python "$tests_dir/verify.py" --repo /app --logs /logs/verifier\n'
    )
    (directory / "solution/solve.sh").chmod(0o755)
    (directory / "tests/test.sh").chmod(0o755)
    (directory / "tests" / TEST_FILE).write_text(source)
    (directory / "tests/verify.py").write_bytes((ROOT / "verify.py").read_bytes())
    (directory / "tests/fail_to_pass.json").write_text(
        json.dumps([f"{TEST_FILE}::{name}" for name in test_names], indent=2) + "\n"
    )
    (directory / "tests/pass_to_pass.json").write_text(
        json.dumps(recipe.regressions, indent=2) + "\n"
    )


def generate(repo: Path, commit: str, output: Path, selected: list[str]) -> None:
    check_checkout(repo, commit)
    if output.is_relative_to(repo):
        raise ValueError("Write generated tasks outside the starter checkout.")
    if output.exists() or output.is_symlink():
        raise ValueError(f"Output already exists: {output}. Pick a new directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    recipes = [RECIPES[name] for name in dict.fromkeys(selected or RECIPES)]
    with tempfile.TemporaryDirectory(prefix=".factory-", dir=output.parent) as temporary:
        staging = Path(temporary) / "tasks"
        for recipe in recipes:
            write_package(staging / recipe.id, recipe, repo, commit)
        staging.rename(output)
    for recipe in recipes:
        print(output / recipe.id)


def check_local(
    repo: Path,
    commit: str,
    tasks: Path,
    python: Path,
    logs: Path,
    selected: list[str],
) -> int:
    check_checkout(repo, commit)
    if logs.is_relative_to(repo):
        raise ValueError("Write validation logs outside the starter checkout.")
    available = sorted(item.name for item in tasks.iterdir() if item.is_dir())
    task_names = list(dict.fromkeys(selected or available))
    if not task_names:
        raise ValueError(f"No task directories found in {tasks}.")

    logs.mkdir(parents=True, exist_ok=False)
    report = []
    for name in task_names:
        task = tasks / name
        config = tomllib.loads((task / "task.toml").read_text())
        if config["metadata"]["base_commit"] != commit:
            raise ValueError(f"{task} was generated for a different commit.")
        for agent, expected in (("nop", 0.0), ("oracle", 1.0)):
            run_dir = logs / name / agent
            run_dir.mkdir(parents=True)
            with tempfile.TemporaryDirectory(prefix="click-check-") as temporary:
                checkout = Path(temporary) / "click"
                git(repo, "clone", "--shared", "--no-checkout", "--quiet", str(repo), str(checkout))
                git(checkout, "checkout", "--detach", commit)
                if agent == "oracle":
                    subprocess.run(["sh", str(task / "solution/solve.sh"), str(checkout)], check=True)
                result = subprocess.run(
                    [
                        str(python),
                        str(task / "tests/verify.py"),
                        "--repo",
                        str(checkout),
                        "--logs",
                        str(run_dir),
                    ],
                    capture_output=True,
                    text=True,
                )
                (run_dir / "verifier.log").write_text(result.stdout + result.stderr)
            reward_file = run_dir / "reward.txt"
            reward = float(reward_file.read_text()) if reward_file.is_file() else None
            passed = result.returncode == 0 and reward == expected
            print(f"{name:28} {agent:6} reward={reward} expected={expected} {'PASS' if passed else 'FAIL'}")
            report.append({
                "task": name,
                "agent": agent,
                "reward": reward,
                "expected": expected,
                "passed": passed,
                "logs": str(run_dir.relative_to(logs)),
            })
    (logs / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if all(row["passed"] for row in report) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("generate", "Build Harbor packages from a clean Click checkout."),
        ("check-local", "Run the packaged verifier and solution locally."),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--repo", type=Path, required=True)
        command.add_argument("--commit", default=BASE_COMMIT)
        command.add_argument("--task", action="append", choices=sorted(RECIPES))

    commands.choices["generate"].add_argument("--out", type=Path, required=True)
    local = commands.choices["check-local"]
    local.add_argument("--tasks", type=Path, required=True)
    local.add_argument("--logs", type=Path, required=True)
    local.add_argument("--python", type=Path, default=Path(sys.executable))

    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate(args.repo.resolve(), args.commit, args.out.parent.resolve() / args.out.name, args.task)
            return 0
        # Keep a virtualenv interpreter's symlink intact.
        return check_local(
            args.repo.resolve(), args.commit, args.tasks.resolve(),
            args.python.absolute(), args.logs.parent.resolve() / args.logs.name, args.task,
        )
    except subprocess.CalledProcessError as error:
        print((error.stderr or str(error)).strip(), file=sys.stderr)
    except (ValueError, OSError, KeyError) as error:
        print(error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
