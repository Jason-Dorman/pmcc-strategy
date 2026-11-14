"""The real platform opener against the real lseg-data 2.1.1, run offline (LD-05, DEC-83).

The platform session's tests use a fake opener, so this checks the one the nightly job runs: it
builds lseg-data's platform session from the credentials and makes it the default, and the
session starts Closed, with `open` and `close`. Building a session asks nothing of the network.
It also pins the trap `platform_session` guards against and `FakePlatformSession` copies: a
sign-in that can't reach LSEG makes `open()` return Closed rather than raise.
The library runs in a separate interpreter with sockets blocked and its config lookup pointed at
an empty folder, as in `test_lseg_contract.py`; the credentials are dummies.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]

LIBRARY = r"""
import json, socket, sys, warnings

def refuse(*args, **kwargs):
    raise RuntimeError("network blocked")

socket.socket.connect = refuse
socket.socket.connect_ex = refuse
socket.create_connection = refuse
socket.getaddrinfo = refuse
warnings.simplefilter("ignore")

sys.path.insert(0, sys.argv[1])
import lseg.data as ld
from pmcc.data.lseg.platform import PlatformCredentials, _platform_opener

session = _platform_opener(PlatformCredentials("dummy-key", "dummy-user", "dummy-pass"))
built = {
    "state": getattr(session.open_state, "name", None),
    "is_default": ld.session.get_default() is session,
    "calls": [callable(getattr(session, name, None)) for name in ("open", "close")],
    "kind": type(session).__name__,
}
try:
    returned = session.open()
    built["open"] = {"returned": getattr(returned, "name", None), "raised": None}
except Exception as exc:
    built["open"] = {"returned": None, "raised": type(exc).__name__}
built["state_after_open"] = getattr(session.open_state, "name", None)
print(json.dumps(built))
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    home = tmp_path_factory.mktemp("lseg-home")
    env = {k: v for k, v in os.environ.items() if k != "LD_LIB_CONFIG_PATH"}
    env.update(LDPLIB_ENV_DIR=str(home), HOME=str(home), USERPROFILE=str(home))
    run = subprocess.run(
        [sys.executable, "-c", LIBRARY, str(ROOT)],
        capture_output=True,
        text=True,
        cwd=home,
        env=env,
        timeout=300,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout.strip().splitlines()[-1])


def test_ld_05_the_opener_builds_lseg_datas_platform_session(built: dict[str, Any]) -> None:
    assert built["kind"] == "PlatformSession"


def test_ld_05_the_opener_makes_it_the_default_session(built: dict[str, Any]) -> None:
    assert built["is_default"] is True


def test_ld_05_the_session_starts_closed_with_open_and_close(built: dict[str, Any]) -> None:
    assert built["state"] == "Closed"
    assert built["calls"] == [True, True]


def test_ld_05_a_failed_sign_in_returns_closed_instead_of_raising(built: dict[str, Any]) -> None:
    assert built["open"] == {"returned": "Closed", "raised": None}
    assert built["state_after_open"] == "Closed"
