"""Writing cache files: whole or not at all, and never over an existing file (LDG §5).

A file is written to a temporary `{name}.{random}.partial` beside it, then hard-linked into place.
A link fails if the target exists, even one that appeared since the check, so nothing is ever
replaced. The temporary file is removed however the write ends. Only a process killed mid-write
leaves one behind; nothing reads a `.partial`, and its unique name never blocks a later write. The
one file that is replaced is an index derived from files written this way (`replace_file`).
"""

import os
import tempfile
from pathlib import Path


def write_new(path: Path, data: bytes) -> None:
    """Write `data` to `path`, which mustn't exist yet. Raises `FileExistsError` if it does."""
    temp = _temporary(path, data)
    try:
        os.link(temp, path)  # fails if `path` exists; nothing is replaced
    finally:
        temp.unlink(missing_ok=True)


def replace_file(path: Path, data: bytes) -> None:
    """Write `data` to `path` whole, replacing what is there. Only for derived indexes."""
    temp = _temporary(path, data)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _temporary(path: Path, data: bytes) -> Path:
    """A new temporary file beside `path` holding `data`; removed again if writing it fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".partial")
    os.close(fd)  # closed first, so a failed write can always remove the file, on Windows too
    temp = Path(name)
    try:
        temp.write_bytes(data)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp
