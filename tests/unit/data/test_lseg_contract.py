"""FakeLseg against the real lseg-data 2.1.1, run offline (DEC-83).

FakeLseg ports what lseg-data does with the service's answers. These tests feed the same answers
to lseg-data's own code and compare, so the fake can't be kinder than the library, and an
upgrade that changes what the adapter relies on fails here. The library runs in a separate
interpreter with sockets blocked and its config lookup pointed at an empty folder: no
credentials are read, and nothing leaves the machine.
"""

# pandas has no type stubs, so pyright strict can't see through its return types (DEC-83).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

import pandas as pd
import pytest

from tests.fakes.lseg import (
    DAYS,
    NOT_FOUND,
    REFUSED,
    TIMED_OUT,
    Answer,
    FakeLseg,
    build,
    build_one,
    no_data_message,
)

A, B = "NVDAJ182618000.U^J26", "NVDAJ182618500.U^J26"
NEVER = "NVDAJ182699900.U^J26"
QUOTES = ["BID", "ASK"]
QUIET: dict[str, list[float | None]] = {"BID": [None] * 3, "ASK": [None] * 3}
HOURLY = {A: {"BID": [5.0, 5.1, None], "ASK": [5.2, 5.3, None]}, B: {"BID": [3.0, None, 3.2]}}
DAILY = {A: {"BID": [5.0, 5.5], "ASK": [5.2, 5.7]}, B: {"BID": [3.0, 3.5], "ASK": [3.1, 3.6]}}

# name -> (fake, RICs asked, fields asked, interval)
SCENARIOS: dict[str, tuple[FakeLseg, list[str], list[str], str]] = {
    "two rics, two fields": (FakeLseg(listed=HOURLY), [A, B], QUOTES, "hourly"),
    "hourly batch holding a never-listed ric": (
        FakeLseg(listed=HOURLY),
        [A, NEVER],
        QUOTES,
        "hourly",
    ),
    "daily batch holding a never-listed ric": (
        FakeLseg(listed=DAILY, index=DAYS),
        [A, NEVER, B],
        QUOTES,
        "daily",
    ),
    "daily batch holding an http failure": (
        FakeLseg(listed=DAILY, index=DAYS, http_status={B: 503}),
        [A, B],
        QUOTES,
        "daily",
    ),
    "first ric answers one field": (
        FakeLseg(listed=HOURLY, answers_with={A: {"ASK"}}),
        [A, B],
        QUOTES,
        "hourly",
    ),
    "last ric answers one field": (
        FakeLseg(listed=HOURLY, answers_with={B: {"ASK"}}),
        [A, B],
        QUOTES,
        "hourly",
    ),
    "each ric answers a different field": (
        FakeLseg(listed=HOURLY, answers_with={A: {"ASK"}, B: {"BID"}}),
        [A, B],
        QUOTES,
        "hourly",
    ),
    "one field asked": (FakeLseg(listed=HOURLY), [A, B], ["BID"], "hourly"),
    "a listed ric with no bars": (
        FakeLseg(listed={**HOURLY, B: QUIET}),
        [A, B],
        QUOTES,
        "hourly",
    ),
    "one ric": (FakeLseg(listed=HOURLY), [A], QUOTES, "hourly"),
    "one ric with no bars": (FakeLseg(listed={A: QUIET}), [A], QUOTES, "hourly"),
}

FAILURES: list[tuple[str | int, str]] = [
    (NOT_FOUND["hourly"], f"{NEVER} - The universe is not found"),
    (503, "Service Unavailable"),
    (NOT_FOUND["hourly"], "a repeated code is listed once"),
]

# Runs in the separate interpreter; reads a job as JSON on stdin, writes results as JSON.
LIBRARY = r"""
import json, logging, socket, sys, warnings

def refuse(*args, **kwargs):
    raise RuntimeError("network blocked")

socket.socket.connect = refuse
socket.socket.connect_ex = refuse
socket.create_connection = refuse
socket.getaddrinfo = refuse
warnings.simplefilter("ignore")

import httpx
import pandas as pd
from lseg.data._access_layer import _data_provider
from lseg.data._access_layer._containers import UniverseContainer
from lseg.data._errors import LDError
from lseg.data.content import historical_pricing
from lseg.data.content._entire_data_provider import entire_create_response
from lseg.data.content._historical_data_provider import validate_responses
from lseg.data.content._historical_df_builder import historical_builder
from lseg.data.delivery._data._endpoint_data import Error
from lseg.data.delivery._data._response import Response

def frame(df):
    return {
        "columns": [list(c) if isinstance(c, tuple) else c for c in df.columns],
        "name": df.columns.name,
        "index": [str(i) for i in df.index],
        "values": [
            [None if pd.isna(v) else float(v) for v in row]
            for row in df.astype(object).values.tolist()
        ],
    }

def build(job):
    try:
        if len(job["rics"]) == 1:
            df = historical_builder.build_one(job["raws"][0], job["fields"], job["axis"])
        else:
            universe = UniverseContainer(job["rics"])
            df = historical_builder.build(job["raws"], universe, job["fields"], job["axis"])
        return frame(df)
    except Exception as exc:
        return {"raises": [type(exc).__name__, str(exc)]}

def failed(code, message):
    return Response(False, None, [Error(code, message)], None, 1, None, {}, None)

def flattened(error):
    definition = historical_pricing.summaries.Definition
    original = definition.get_data

    def get_data(self, *args, **kwargs):
        raise error

    definition.get_data = get_data
    try:
        return _data_provider.get_hp_data(
            universe=["X.O"], fields=["BID"], interval="hourly", start="2026-09-14",
            end="2026-09-15", adjustments=None, count=None, logger=logging.getLogger("c"),
        )[2]
    finally:
        definition.get_data = original

job = json.load(sys.stdin)
responses = [failed(code, message) for code, message in job["failures"]]
try:
    validate_responses(responses)
    raised = None
except LDError as exc:
    raised = {"message": exc.message, "attached": exc.response is responses}
json.dump({
    "builds": {name: build(b) for name, b in job["builds"].items()},
    "validate": raised,
    "hourly_failed_raw": entire_create_response(responses[:1], {}, [], {})._data_raw,
    "flattened": [
        flattened(httpx.ReadTimeout(job["transport"][0])),
        flattened(httpx.ConnectError(job["transport"][1])),
    ],
}, sys.stdout)
"""


def _frame(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "columns": [list(c) if isinstance(c, tuple) else c for c in df.columns],
        "name": df.columns.name,
        "index": [str(i) for i in df.index],
        "values": [
            [None if pd.isna(v) else float(v) for v in row]
            for row in df.astype(object).values.tolist()
        ],
    }


def _fake_build(
    raws: Sequence[object], rics: Sequence[str], fields: Sequence[str], axis: str
) -> Any:
    try:
        return _frame(
            build_one(raws[0], fields, axis) if len(rics) == 1 else build(raws, fields, axis)
        )
    except Exception as exc:
        return {"raises": [type(exc).__name__, str(exc)]}


def _job() -> dict[str, Any]:
    builds: dict[str, Any] = {}
    for name, (fake, rics, fields, interval) in SCENARIOS.items():
        raws = [a.raw for a in fake.answers(rics, fields, interval)]
        axis = "Date" if interval == "daily" else "Timestamp"
        builds[name] = {"raws": raws, "rics": rics, "fields": fields, "axis": axis}
    return {"builds": builds, "failures": FAILURES, "transport": [TIMED_OUT, REFUSED]}


@pytest.fixture(scope="module")
def library(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """lseg-data's own answers to the job, from an isolated interpreter."""
    home = tmp_path_factory.mktemp("lseg-home")
    env = {k: v for k, v in os.environ.items() if k != "LD_LIB_CONFIG_PATH"}
    env.update(LDPLIB_ENV_DIR=str(home), HOME=str(home), USERPROFILE=str(home))
    run = subprocess.run(
        [sys.executable, "-c", LIBRARY],
        input=json.dumps(_job()),
        capture_output=True,
        text=True,
        cwd=home,
        env=env,
        timeout=300,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_lseg_contract_fake_builds_the_frame_lseg_data_builds(
    library: dict[str, Any], scenario: str
) -> None:
    job = _job()["builds"][scenario]

    ours = _fake_build(job["raws"], job["rics"], job["fields"], job["axis"])

    assert ours == library["builds"][scenario]


def test_lseg_contract_no_answer_lists_each_code_once_as_the_fake_does(
    library: dict[str, Any],
) -> None:
    answers = [Answer(NEVER, {"data": []}, failure) for failure in FAILURES]

    assert library["validate"] == {"message": no_data_message(answers), "attached": True}


def test_lseg_contract_failed_hourly_ric_leaves_a_raw_without_headers(
    library: dict[str, Any],
) -> None:
    [answer] = FakeLseg().answers([NEVER], QUOTES, "hourly")

    assert library["hourly_failed_raw"] == answer.raw


def test_lseg_contract_transport_failure_keeps_only_its_text(library: dict[str, Any]) -> None:
    assert library["flattened"] == [TIMED_OUT, REFUSED]
