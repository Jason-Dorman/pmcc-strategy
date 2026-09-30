"""The run's provenance: git SHA and dirtiness (PO, DEC-50), the lockfile hash, the version.
Each test builds a throwaway repository (`tests.fakes.git_repo`)."""

import hashlib
from importlib.metadata import version
from pathlib import Path

import pytest

from pmcc.export import manifest
from pmcc.export.manifest import ProvenanceError, git_state, lock_hash, provenance
from tests.fakes.git_repo import git, make_repo


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return make_repo(tmp_path, monkeypatch)


def test_dec_50_a_clean_tree_is_not_dirty_and_records_head(repo: Path) -> None:
    state = git_state(repo)

    assert state.sha == git(repo, "rev-parse", "HEAD").strip()
    assert len(state.sha) == 40
    assert state.dirty is False


def test_dec_50_a_modified_tracked_file_makes_the_tree_dirty(repo: Path) -> None:
    (repo / "pmcc" / "rules.py").write_text("X = 2\n", encoding="utf-8")

    assert git_state(repo).dirty is True


def test_dec_50_a_staged_change_makes_the_tree_dirty(repo: Path) -> None:
    (repo / "pmcc" / "rules.py").write_text("X = 2\n", encoding="utf-8")
    git(repo, "add", "pmcc/rules.py")

    assert git_state(repo).dirty is True


def test_dec_50_a_deleted_tracked_file_makes_the_tree_dirty(repo: Path) -> None:
    (repo / "pmcc" / "rules.py").unlink()

    assert git_state(repo).dirty is True


def test_dec_50_an_untracked_file_makes_the_tree_dirty(repo: Path) -> None:
    (repo / "configs").mkdir()
    (repo / "configs" / "variant.yaml").write_text("id: x\n", encoding="utf-8")

    assert git_state(repo).dirty is True


def test_dec_50_an_ignored_file_leaves_the_tree_clean(repo: Path) -> None:
    (repo / "data_cache").mkdir()
    (repo / "data_cache" / "stock.parquet").write_bytes(b"x")

    assert git_state(repo).dirty is False


def test_dec_50_changes_under_results_leave_the_tree_clean(repo: Path) -> None:
    (repo / "results" / "NVDA" / "baseline_pmcc.json").write_text('{"a":1}\n', encoding="utf-8")
    (repo / "results" / "TSLA").mkdir()
    (repo / "results" / "TSLA" / "baseline_pmcc.json").write_text("{}\n", encoding="utf-8")

    assert git_state(repo).dirty is False


def test_dec_50_a_file_named_like_results_elsewhere_still_counts(repo: Path) -> None:
    (repo / "pmcc" / "results").mkdir()
    (repo / "pmcc" / "results" / "x.py").write_text("\n", encoding="utf-8")

    assert git_state(repo).dirty is True


def test_dec_50_a_directory_that_isnt_a_repository_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))  # don't find a repo above it

    with pytest.raises(ProvenanceError, match="records the commit"):
        git_state(plain)


@pytest.mark.usefixtures("repo")  # for its isolated git config
def test_dec_50_a_repository_with_no_commit_fails_loudly(tmp_path: Path) -> None:
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "--quiet")

    with pytest.raises(ProvenanceError, match="rev-parse"):
        git_state(fresh)


def test_dec_50_git_missing_fails_loudly(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")

    with pytest.raises(ProvenanceError, match="git isn't installed"):
        git_state(repo)


def test_dec_50_lock_hash_is_the_lockfiles_sha256(repo: Path) -> None:
    assert lock_hash(repo / "uv.lock") == hashlib.sha256(b"lock\n").hexdigest()


def test_dec_50_a_missing_lockfile_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(ProvenanceError, match="lockfile"):
        lock_hash(tmp_path / "uv.lock")


def test_dec_50_provenance_gathers_git_lockfile_and_version(repo: Path) -> None:
    (repo / "pmcc" / "rules.py").write_text("X = 2\n", encoding="utf-8")

    found = provenance(repo)

    assert found.git == git_state(repo)
    assert found.git.dirty is True
    assert found.lock_hash == lock_hash(repo / "uv.lock")
    assert found.pmcc_version == version("pmcc")


def test_dec_50_provenance_defaults_to_this_checkout() -> None:
    assert (manifest.REPO_ROOT / "uv.lock").is_file()
    assert (manifest.REPO_ROOT / "pmcc" / "export" / "manifest.py").is_file()
