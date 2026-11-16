"""`pmcc live-probe` (L1-02; LD-05): tonight's close snapshot over the headless LSEG session.

It reads the credentials from the environment, writes one report and never overwrites it, prints
counts but no prices (LD-21), never shows a credential (LINV-09), and writes nothing when LSEG
fails.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.data.fetch import Retry
from pmcc.data.lseg import LsegProvider, PlatformCredentials
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.live.snapshot import take_snapshot
from tests.fakes.lseg import FakeLseg, fake_provider

NOW = datetime(2026, 11, 13, 22, 0, tzinfo=ET)
INDEX = (datetime(2026, 11, 13, 19), datetime(2026, 11, 13, 20), datetime(2026, 11, 13, 21))
ENV = {"LSEG_APP_KEY": "key-0123", "LSEG_USERNAME": "user@example.edu", "LSEG_PASSWORD": "s3cr3t!"}
PUT = build_ric(
    OptionId("NVDA", datetime(2026, 11, 20).date(), Right.PUT, Price.from_dollars("195")),
    RicForm.LIVE,
)

runner = CliRunner()


def _fake(quoted: bool = True) -> FakeLseg:
    bid = 3.0 if quoted else 0.0
    return FakeLseg(
        listed={
            "NVDA.O": {"TRDPRC_1": [199.0, 200.0, 201.5]},
            PUT: {"BID": [2.9, bid, None], "ASK": [3.1, 3.2, None]},
        },
        index=INDEX,
    )


@pytest.fixture
def lseg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[FakeLseg]:
    """A fake LSEG behind `platform_session`, at a fixed `now`, working in `tmp_path`. Put the
    market to serve in the list; the credentials the command passed are recorded on the fixture."""
    served: list[FakeLseg] = [_fake()]
    opened: list[PlatformCredentials] = []

    @contextmanager
    def session(credentials: PlatformCredentials) -> Generator[LsegProvider]:
        opened.append(credentials)
        yield fake_provider(served[0])

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "platform_session", session)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    monkeypatch.setattr(
        cli, "take_snapshot", partial(take_snapshot, retry=Retry(sleep=lambda _: None))
    )
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return served


def _probe() -> tuple[int, str]:
    result = runner.invoke(app, ["live-probe", "--symbol", "nvda", "--out", "probes"])
    return result.exit_code, result.output


def _reports() -> list[Path]:
    return sorted(Path("probes").glob("live_NVDA_*.json")) if Path("probes").exists() else []


def test_l1_02_live_probe_writes_one_timestamped_report(lseg: list[FakeLseg]) -> None:
    code, output = _probe()

    assert code == 0, output
    assert [p.name for p in _reports()] == ["live_NVDA_20261113T220000.json"]
    assert "listed 1 puts and 0 calls" in output


def test_ld_21_live_probe_prints_no_prices(lseg: list[FakeLseg]) -> None:
    _, output = _probe()

    assert "200.00" not in output
    assert "3.20" not in output


def test_linv_09_live_probe_never_prints_a_credential(lseg: list[FakeLseg]) -> None:
    _, output = _probe()

    assert not any(value in output for value in ENV.values())


@pytest.mark.parametrize("missing", sorted(ENV))
def test_ld_05_live_probe_without_a_credential_asks_nothing_and_writes_nothing(
    lseg: list[FakeLseg], monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.delenv(missing)

    code, output = _probe()

    assert code == 1
    assert missing in output
    assert lseg[0].requests == []
    assert _reports() == []


def test_l1_02_live_probe_writes_nothing_when_lseg_stops_answering(
    lseg: list[FakeLseg],
) -> None:
    lseg[0] = FakeLseg(listed={"NVDA.O": {"TRDPRC_1": [199.0, 200.0, 201.5]}}, every_status=503)

    code, output = _probe()

    assert code == 1
    assert "wrote nothing" in output
    assert _reports() == []


def test_l1_02_live_probe_fails_but_keeps_the_report_when_nothing_is_quoted(
    lseg: list[FakeLseg],
) -> None:
    lseg[0] = _fake(quoted=False)

    code, output = _probe()

    assert code == 1
    assert "no option had a valid bid and ask" in output
    assert len(_reports()) == 1
