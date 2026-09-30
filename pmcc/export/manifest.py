"""Where a run came from: the git commit and whether the tree was dirty, the lockfile's hash and
the package version (Spec › Run manifest; PO, DEC-50).

The tree is dirty when a tracked file is modified or staged, or git sees an untracked file it
doesn't ignore, anywhere but `results/`: an untracked config or module can change a run, and a
run's own results must not make the next run dirty. Git is read only (`rev-parse`, `status`
without optional locks); nothing here changes the repository (DEC-59).
"""

import hashlib
import subprocess
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import final

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCKFILE = "uv.lock"
RESULTS_DIR = "results"


class ProvenanceError(Exception):
    """The run's provenance can't be read: not a git checkout, or no lockfile."""


@final
@dataclass(frozen=True, slots=True)
class GitState:
    sha: str
    dirty: bool


@final
@dataclass(frozen=True, slots=True)
class Provenance:
    """Everything in the manifest that comes from the checkout rather than the run."""

    git: GitState
    lock_hash: str
    pmcc_version: str


def provenance(repo: Path = REPO_ROOT) -> Provenance:
    return Provenance(git_state(repo), lock_hash(repo / LOCKFILE), version("pmcc"))


def git_state(repo: Path) -> GitState:
    """HEAD's SHA, and whether the tree differs from it outside `results/`."""
    sha = _git(repo, "rev-parse", "--verify", "HEAD").strip()
    changes = _git(repo, "status", "--porcelain", "--untracked-files=normal", "--", ".",
                   f":(exclude){RESULTS_DIR}")  # fmt: skip
    return GitState(sha, bool(changes.strip()))


def lock_hash(path: Path) -> str:
    """sha256 of the lockfile's bytes (LF on every OS, `.gitattributes`)."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        raise ProvenanceError(f"{path} is missing; a run records its lockfile's hash") from None


def _git(repo: Path, *args: str) -> str:
    command = ["git", "--no-optional-locks", "-C", str(repo), *args]
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise ProvenanceError("git isn't installed; a run records its commit") from None
    if done.returncode != 0:
        raise ProvenanceError(
            f"`git {' '.join(args)}` failed in {repo}: {done.stderr.strip()}; "
            "a run records the commit it ran from"
        )
    return done.stdout
