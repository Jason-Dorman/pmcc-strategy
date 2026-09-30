"""Suite-wide guards: no network, and deterministic hypothesis profiles (TEST-STRATEGY §1)."""

import os
import socket
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


@pytest.fixture(scope="session")
def synthetic(tmp_path_factory: pytest.TempPathFactory) -> "SyntheticMarkets":
    """Synthetic markets, each generated once per session and shared (TEST-STRATEGY §5)."""
    from tests.fixtures.synthetic.store import SyntheticMarkets

    return SyntheticMarkets(tmp_path_factory.mktemp("synthetic"))
