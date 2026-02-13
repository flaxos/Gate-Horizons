#!/usr/bin/env python3
"""Pydroid launcher for Gate Horizons.

This script is designed to be run directly in Pydroid.
It will:
1) verify core prerequisites,
2) update the current git checkout to latest remote changes,
3) ensure Python package prerequisites are installed,
4) run the Gate Horizons entry point.
"""

from __future__ import annotations

import importlib.util
import importlib
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
MAIN_PATH = REPO_ROOT / "gate_horizons" / "main.py"
LEGACY_MAIN_PATH = REPO_ROOT / "main.py"

# Minimal runtime deps for the app entrypoint.
PYTHON_PACKAGES = {
    "kivy": "kivy",
}

# Pydroid's stable channel commonly ships Python 3.10.x.
# Keep launcher compatibility aligned with supported runtime syntax.
MIN_PYTHON_VERSION = (3, 10)


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    printable = " ".join(cmd)
    print(f"\n>>> {printable}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON_VERSION:
        minimum = ".".join(str(part) for part in MIN_PYTHON_VERSION)
        raise RuntimeError(
            f"Python {minimum}+ is required. "
            f"Current version: {sys.version.split()[0]}",
        )
    print(f"[ok] Python version: {sys.version.split()[0]}")


def check_git_available() -> bool:
    git = shutil.which("git")
    if not git:
        print("[warn] git is not available in PATH. Skipping repo update.")
        return False
    print(f"[ok] git found: {git}")
    return True


def update_repo_from_git() -> None:
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        print("[warn] Not a git checkout (.git missing). Skipping repo update.")
        return

    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    print(f"[ok] current branch: {branch}")

    try:
        _run(["git", "fetch", "--all", "--prune"], cwd=REPO_ROOT)
        _run(["git", "pull", "--ff-only"], cwd=REPO_ROOT)
        print("[ok] Repository updated to latest remote revision.")
    except subprocess.CalledProcessError as exc:
        print(f"[warn] git update failed ({exc}). Continuing with local checkout.")


def ensure_packages() -> None:
    for module_name, pip_name in PYTHON_PACKAGES.items():
        if importlib.util.find_spec(module_name) is None:
            print(f"[info] Missing package '{module_name}'. Installing '{pip_name}'...")
            _run([sys.executable, "-m", "pip", "install", "--upgrade", pip_name])
        try:
            imported_module = importlib.import_module(module_name)
            version = getattr(imported_module, "__version__", "unknown")
            print(f"[ok] Python package available: {module_name} (version: {version})")
        except Exception as exc:  # noqa: BLE001 - show import failure details in launcher logs
            print(f"[warn] Package '{module_name}' is installed but failed to import: {exc}")
            print(f"[info] Attempting to reinstall '{pip_name}'...")
            _run([sys.executable, "-m", "pip", "install", "--upgrade", pip_name])


def run_main() -> None:
    if not MAIN_PATH.exists() and not LEGACY_MAIN_PATH.exists():
        raise FileNotFoundError(
            "No runnable entry point found. Expected one of:\n"
            f"- {MAIN_PATH}\n"
            f"- {LEGACY_MAIN_PATH}",
        )

    run_candidates: list[list[str]] = [
        [sys.executable, "-m", "gate_horizons"],
    ]
    if LEGACY_MAIN_PATH.exists():
        run_candidates.append([sys.executable, str(LEGACY_MAIN_PATH)])
    if MAIN_PATH.exists():
        run_candidates.append([sys.executable, str(MAIN_PATH)])

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(REPO_ROOT))

    print("\n[launch] Starting Gate Horizons...")
    failures: list[tuple[list[str], subprocess.CalledProcessError]] = []
    for run_target in run_candidates:
        print(f"[launch] Trying: {' '.join(run_target)}")
        try:
            subprocess.run(
                run_target,
                cwd=REPO_ROOT,
                env=env,
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            return
        except subprocess.CalledProcessError as exc:
            failures.append((run_target, exc))
            print(
                f"[warn] Launch failed (exit code {exc.returncode}) for: {' '.join(run_target)}",
            )

    cmd_text = "\n".join(
        f"- {' '.join(cmd)} (exit code {exc.returncode})" for cmd, exc in failures
    )
    raise RuntimeError(f"All launch attempts failed:\n{cmd_text}")


def main() -> int:
    try:
        os.chdir(REPO_ROOT)
        print(f"[info] Repo root: {REPO_ROOT}")
        check_python_version()

        if check_git_available():
            update_repo_from_git()

        ensure_packages()
        run_main()
        return 0
    except Exception as exc:  # noqa: BLE001 - launcher should show a friendly one-line failure
        print(f"\n[error] {exc}")
        print("[debug] Full traceback:")
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
