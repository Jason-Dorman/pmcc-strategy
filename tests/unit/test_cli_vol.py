"""`pmcc vol` (L4-02; PO, LD-33; LD-34): the night's volatility points and smile, over a fake
LSEG. It prints counts, never prices; asks LSEG nothing when both files are current; plans a
backfill before pulling it; and on any failure writes nothing and exits 1."""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.config.calendar import load_calendar
from pmcc.data.provider import HistoryProvider
from pmcc.domain.clock import ET
from pmcc.live.vol import SMILE, VOL_LOG
from tests.fakes.vol import VolProvider

NOW = datetime(2026, 11, 17, 22, 47, tzinfo=ET)
TUESDAY = date(2026, 11, 17)

runner = CliRunner()


def _closes() -> dict[date, float]:
    calendar = load_calendar()
    days = [s.day for s in calendar.sessions(date(2026, 9, 1), TUESDAY)]
    return {d: round(150 + 4 * ((i * 3) % 7) / 7 + 0.1 * i, 2) for i, d in enumerate(days)}


@pytest.fixture
def lseg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[VolProvider]:
    """Each LSEG session opened, as its fake provider."""
    opened: list[VolProvider] = []
    monkeypatch.chdir(tmp_path)  # logs/ land here
    monkeypatch.setattr(cli, "_now", lambda: NOW)

    @contextmanager
    def session() -> Generator[HistoryProvider]:
        provider = VolProvider(load_calendar(), _closes())
        opened.append(provider)
        yield provider

    monkeypatch.setattr(cli, "_platform", session)
    return opened


def _vol(root: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["vol", "--symbol", "nvda", "--root", str(root), *args])
    return result.exit_code, result.output


def test_l4_02_vol_writes_the_nights_point_and_smile(
    tmp_path: Path, lseg: list[VolProvider]
) -> None:
    code, output = _vol(tmp_path)

    assert code == 0, output
    (row,) = [json.loads(line) for line in (tmp_path / VOL_LOG).read_text().splitlines()]
    assert row["session"] == TUESDAY.isoformat()
    assert row["atm_iv"] is not None
    assert row["rv20"] is not None
    smile = json.loads((tmp_path / SMILE).read_text())
    assert smile["session"] == TUESDAY.isoformat()
    assert smile["points"]
    assert len(lseg) == 1  # one session for the points and the smile
    assert "1 point" in output
    assert "$" not in output  # counts, never prices (LD-21)
    assert output.isascii()


def test_ld_34_a_second_run_the_same_night_asks_lseg_nothing(
    tmp_path: Path, lseg: list[VolProvider]
) -> None:
    _vol(tmp_path)
    before = (tmp_path / VOL_LOG).read_bytes()

    code, output = _vol(tmp_path)

    assert code == 0, output
    assert "up to date" in output
    assert len(lseg) == 1
    assert (tmp_path / VOL_LOG).read_bytes() == before


def test_ld_34_plan_only_prints_the_estimate_and_writes_nothing(
    tmp_path: Path, lseg: list[VolProvider]
) -> None:
    code, output = _vol(tmp_path, "--since", "2026-10-01", "--plan-only")

    assert code == 0, output
    assert "sessions (2026-10-01 to 2026-11-17)" in output
    assert "requests" in output
    assert not (tmp_path / VOL_LOG).exists()
    assert not (tmp_path / SMILE).exists()
    assert lseg[0].asked == [("NVDA.O",)]  # the plan asks for the closes alone


def test_ld_34_since_backfills_every_session(tmp_path: Path, lseg: list[VolProvider]) -> None:
    code, output = _vol(tmp_path, "--since", "2026-11-10")

    assert code == 0, output
    rows = [json.loads(line) for line in (tmp_path / VOL_LOG).read_text().splitlines()]
    assert [r["session"] for r in rows] == [
        "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-16", "2026-11-17",
    ]  # fmt: skip


def test_ld_34_an_outage_writes_nothing_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lseg: list[VolProvider]
) -> None:
    @contextmanager
    def down() -> Generator[HistoryProvider]:
        yield VolProvider(load_calendar(), _closes(), down=True)

    monkeypatch.setattr(cli, "_platform", down)

    code, output = _vol(tmp_path)

    assert code == 1
    assert "no volatility written" in output
    assert not (tmp_path / VOL_LOG).exists()
    assert not (tmp_path / SMILE).exists()


def test_ld_34_vol_refuses_a_symbol_the_config_does_not_trade(
    tmp_path: Path, lseg: list[VolProvider]
) -> None:
    result = runner.invoke(app, ["vol", "--symbol", "spy", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "NVDA" in result.output
    assert lseg == []
