"""Suite-wide guards: no network, the repo's results and configs untouched, and deterministic
hypothesis profiles (TEST-STRATEGY §1)."""

import os
import socket
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import pytest
from hypothesis import settings

if TYPE_CHECKING:
    from tests.fixtures.synthetic.store import SyntheticMarkets

# No per-example deadline: a wall-clock limit makes a pass depend on machine load, and a whole
# fetch through pandas frames can take a few hundred ms on a busy Windows box.
settings.register_profile("dev", max_examples=50, deadline=None)
settings.register_profile("ci", max_examples=300, derandomize=True, database=None, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


class NetworkBlockedError(RuntimeError):
    """A test tried to open a network connection."""


def _refuse(*_args: object, **_kwargs: object) -> NoReturn:
    raise NetworkBlockedError("tests never touch the network; use FakeProvider")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block every outbound connection and name lookup, localhost included (LSEG listens there)."""
    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)


REPO = Path(__file__).resolve().parents[1]
GUARDED = (REPO / "results", REPO / "configs")  # what a stray `pmcc batch`/`calibrate` would write


def _snapshot() -> dict[str, tuple[int, int]]:
    return {
        p.relative_to(REPO).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for root in GUARDED
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.fixture(autouse=True)
def repo_untouched() -> Iterator[None]:
    """Fail any test that writes into the repo's results/ or configs/: a CLI test run from the repo
    directory once ran a real batch over the committed results (P5-03)."""
    before = _snapshot()
    yield
    after = _snapshot()
    if after != before:
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        pytest.fail(f"this test wrote into the repo: {changed}")


@pytest.fixture(scope="session")
def synthetic(tmp_path_factory: pytest.TempPathFactory) -> "SyntheticMarkets":
    """Synthetic markets, each generated once per session and shared (TEST-STRATEGY §5)."""
    from tests.fixtures.synthetic.store import SyntheticMarkets

    return SyntheticMarkets(tmp_path_factory.mktemp("synthetic"))
