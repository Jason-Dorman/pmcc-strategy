"""Cache file writes: whole or not at all, and never over an existing file (LDG §5, DEC-46)."""

from pathlib import Path

import pytest

from pmcc.data import files
from pmcc.data.files import replace_file, write_new


def test_write_new_writes_the_bytes_and_leaves_no_partial(tmp_path: Path) -> None:
    path = tmp_path / "a" / "unit.parquet"
    write_new(path, b"bars")
    assert path.read_bytes() == b"bars"
    assert list(path.parent.iterdir()) == [path]


def test_write_new_never_replaces_an_existing_file(tmp_path: Path) -> None:
    """The link refuses even a file the caller didn't check for (one that appeared meanwhile)."""
    path = tmp_path / "unit.parquet"
    path.write_bytes(b"first")
    with pytest.raises(FileExistsError):
        write_new(path, b"second")
    assert path.read_bytes() == b"first"
    assert list(tmp_path.iterdir()) == [path]


def test_write_new_interrupted_leaves_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(files.os, "link", fail)
    with pytest.raises(OSError, match="disk full"):
        write_new(tmp_path / "unit.parquet", b"bars")
    assert list(tmp_path.iterdir()) == []


def test_replace_file_replaces_whole(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    replace_file(path, b"old")
    replace_file(path, b"new")
    assert path.read_bytes() == b"new"
    assert list(tmp_path.iterdir()) == [path]


def test_replace_file_interrupted_keeps_the_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "manifest.json"
    replace_file(path, b"old")

    def fail(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(files.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        replace_file(path, b"new")
    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_write_new_is_not_blocked_by_a_partial_a_killed_write_left(tmp_path: Path) -> None:
    """A process killed mid-write leaves a `.partial`; it never blocks, and is never touched."""
    stale = tmp_path / "unit.parquet.partial"
    stale.write_bytes(b"killed")
    path = tmp_path / "unit.parquet"
    write_new(path, b"bars")
    assert path.read_bytes() == b"bars"
    assert stale.read_bytes() == b"killed"


def test_write_new_writing_that_fails_leaves_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def full(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(files.Path, "write_bytes", full)
    with pytest.raises(OSError, match="disk full"):
        write_new(tmp_path / "unit.parquet", b"bars")
    assert list(tmp_path.iterdir()) == []
