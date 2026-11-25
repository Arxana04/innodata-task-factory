"""Solution Runner: manages isolated checkouts and safe patch applications.

Ensures that:
1. Every task validation begins from a clean, pristine Git checkout.
2. Reference patches are validated before applying (git apply --check).
3. Patch application errors are separated from test execution errors.
4. One task never pollutes or alters another task's repository state.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class PatchApplicationError(Exception):
    """Raised when a git patch fails to apply cleanly."""
    pass


class SolutionRunner:
    """Manages isolated Git checkouts and applies reference solutions."""

    def __init__(self, click_repo: Path, base_commit: str = "cf19179e8e2fd54c601378cec9e0d21bb12b6fb1"):
        self.click_repo = click_repo.resolve()
        self.base_commit = base_commit
        if not (self.click_repo / ".git").exists():
            raise FileNotFoundError(f"Click repository not found at {self.click_repo}")

    def create_isolated_checkout(self, target_dir: Path) -> Path:
        """Creates a fresh, isolated detached checkout from the base Click repository."""
        target_dir = target_dir.resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        # Use git clone --shared for speed and minimal disk space while keeping full isolation
        subprocess.run(
            ["git", "clone", "--shared", "--no-checkout", "--quiet", str(self.click_repo), str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(target_dir), "checkout", "--detach", self.base_commit, "--quiet"],
            check=True,
            capture_output=True,
            text=True,
        )
        return target_dir

    def apply_patch(self, checkout_dir: Path, patch_path: Path) -> None:
        """Validates and applies a patch file to a checkout."""
        checkout_dir = checkout_dir.resolve()
        patch_path = patch_path.resolve()

        if not patch_path.is_file():
            raise FileNotFoundError(f"Patch file does not exist: {patch_path}")

        # Check if patch applies cleanly
        check_proc = subprocess.run(
            ["git", "-C", str(checkout_dir), "apply", "--check", str(patch_path)],
            capture_output=True,
            text=True,
        )
        if check_proc.returncode != 0:
            raise PatchApplicationError(
                f"Patch {patch_path.name} failed dry-run check:\n{check_proc.stderr}"
            )

        # Apply patch
        apply_proc = subprocess.run(
            ["git", "-C", str(checkout_dir), "apply", str(patch_path)],
            capture_output=True,
            text=True,
        )
        if apply_proc.returncode != 0:
            raise PatchApplicationError(
                f"Patch {patch_path.name} failed to apply:\n{apply_proc.stderr}"
            )
