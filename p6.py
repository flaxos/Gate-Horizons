#!/usr/bin/env python3
"""Pydroid launcher for Gate Horizons.

This script is designed to be run directly in Pydroid.
It will:
1) verify core prerequisites,
2) update the current git checkout to latest remote changes,
3) ensure Python package prerequisites are installed,
4) run gate_horizons/main.py.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
MAIN_PATH = REPO_ROOT / "gate_horizons" / "main.py"

# Minimal runtime deps for the app entrypoint.
PYTHON_PACKAGES = {
    "kivy": "kivy",
}


def _pythonpath_with_repo() -> str:
    existing = os.environ.get("PYTHONPATH", "")
    if not existing:
        return str(REPO_ROOT)

    parts = [part for part in existing.split(os.pathsep) if part]
    repo_str = str(REPO_ROOT)
    if repo_str in parts:
        parts.remove(repo_str)
    parts.insert(0, repo_str)
    return os.pathsep.join(parts)


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    printable = " ".join(cmd)
    print(f"\n>>> {printable}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def check_python_version() -> None:
    if sys.version_info < (3, 11):
        raise RuntimeError(
            "Python 3.11+ is required. "
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
        else:
            print(f"[ok] Python package available: {module_name}")


def check_project_imports() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = _pythonpath_with_repo()

    probe = (
        "import json; "
        "import gate_horizons.main; "
        "print(json.dumps({'status': 'ok'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("[error] Import probe failed before launch. Details:")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        raise RuntimeError("Project import checks failed. Fix missing dependencies above.")

    print("[ok] Project import probe passed.")


def run_main() -> None:
    if not MAIN_PATH.exists():
        raise FileNotFoundError(f"main.py not found at expected path: {MAIN_PATH}")

    env = os.environ.copy()
    env["PYTHONPATH"] = _pythonpath_with_repo()

    print("\n[launch] Starting Gate Horizons...")
    result = subprocess.run([sys.executable, str(MAIN_PATH)], cwd=REPO_ROOT, env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "main.py exited with a non-zero status. "
            "Run this command manually for full logs: "
            f"{sys.executable} {MAIN_PATH}",
        )


def main() -> int:
    try:
        os.chdir(REPO_ROOT)
        print(f"[info] Repo root: {REPO_ROOT}")
        check_python_version()

        if check_git_available():
            update_repo_from_git()

        ensure_packages()
        check_project_imports()
        run_main()
        return 0
    except Exception as exc:  # noqa: BLE001 - launcher should show a friendly one-line failure
        print(f"\n[error] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
