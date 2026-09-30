"""A throwaway git repository for provenance tests (PO, DEC-50).

It lives under pytest's temporary directory, with git's global and system config shut out, so the
machine's settings (signing, hooks, line endings) can't reach it. The project's own repository is
only ever read (DEC-59).
"""

import os
import subprocess
from pathlib import Path

import pytest


def make_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed repository: a tracked module, a tracked result, a `.gitignore` and a lockfile."""
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "repo"
    (root / "results" / "NVDA").mkdir(parents=True)
    (root / "pmcc").mkdir()
    (root / "pmcc" / "rules.py").write_text("X = 1\n", encoding="utf-8")
    (root / "results" / "NVDA" / "baseline_pmcc.json").write_text("{}\n", encoding="utf-8")
    (root / ".gitignore").write_text("data_cache/\n", encoding="utf-8")
    (root / "uv.lock").write_text("lock\n", encoding="utf-8", newline="\n")
    git(root, "init", "--quiet")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "first")
    return root


def git(root: Path, *args: str) -> str:
    identity = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid"]
    done = subprocess.run(["git", "-C", str(root), *identity, *args], capture_output=True,
                          text=True, check=True, env=os.environ.copy())  # fmt: skip
    return done.stdout
