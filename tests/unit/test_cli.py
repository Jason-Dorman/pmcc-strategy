"""The `pmcc` command surface (ARCHITECTURE §3.1, Spec › CLI)."""

import json
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import date, datetime
from functools import partial
from pathlib import Path

import pytest
import structlog
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.config.calendar import load_calendar
from pmcc.config.universe import load_universe
from pmcc.data.cache import SymbolCache
from pmcc.data.coverage import Coverage
from pmcc.data.discovery import StepSource
from pmcc.data.fetch import Retry
from pmcc.data.probe import run_probe
from pmcc.data.provider import Interval, RawHistory
from pmcc.data.pull import prepare, pull_units
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from tests.fakes.market import FakeMarket

COMMANDS = ["fetch", "probe", "run", "batch", "calibrate", "export", "verify", "serve"]
NOW = datetime(2026, 9, 27, 12, tzinfo=ET)

runner = CliRunner()


def test_cli_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in COMMANDS:
        assert command in result.output


@pytest.mark.parametrize(
    ("args", "item"),
    [
        (["batch", "--universe", "configs/universe.yaml"], "P5-03"),
        (["calibrate"], "P3-09"),
        (["export", "--out", "web/public/data/"], "P4-05"),
        (["verify", "results/"], "P4-05"),
        (["serve"], "P7-06"),
    ],
)
def test_cli_stub_fails_loudly_naming_its_backlog_item(args: list[str], item: str) -> None:
    result = runner.invoke(app, args)

    assert result.exit_code == 1
    assert item in result.output


# --- pmcc probe (P1-04) -----------------------------------------------------------------------


@pytest.fixture
def market(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeMarket:
    """A fake market behind `lseg_session`, at a fixed `now`, working in `tmp_path`."""
    fake = FakeMarket(load_calendar(), NOW.date(), hourly_from=date(2026, 3, 1))

    @contextmanager
    def session() -> Generator[FakeMarket]:
        yield fake

    monkeypatch.chdir(tmp_path)  # logs/ and the report land here
    monkeypatch.setattr(cli, "lseg_session", session)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    monkeypatch.setattr(cli, "run_probe", partial(run_probe, retry=Retry(sleep=lambda _: None)))
    return fake


def _probe() -> tuple[int, str]:
    result = runner.invoke(app, ["probe", "--symbol", "nvda", "--out", "probes"])
    return result.exit_code, result.output


def test_cli_probe_writes_one_report_per_symbol_and_date(market: FakeMarket) -> None:
    code, output = _probe()

    assert code == 0, output
    assert Path("probes/NVDA_20260927.json").is_file()
    assert f"{market.calls} requests" in output


def test_cli_probe_refuses_to_overwrite_a_report_before_asking_anything(
    market: FakeMarket,
) -> None:
    _probe()
    calls = market.calls

    code, output = _probe()

    assert code == 1
    assert "never overwritten" in output
    assert market.calls == calls


@pytest.mark.parametrize("served", [5, 12])  # in the daily tape; in the DEC-83 asks
def test_cli_probe_dead_workspace_writes_nothing(market: FakeMarket, served: int) -> None:
    market.dies_after = served

    code, output = _probe()

    assert code == 1
    assert "wrote nothing" in output
    assert not Path("probes").exists()


def test_cli_probe_stopped_early_writes_its_report_and_fails(market: FakeMarket) -> None:
    market.odd_strikes_answer = {Interval.HOURLY}  # a never-listed RIC answers

    code, output = _probe()

    assert code == 1
    assert "stopped early" in output
    assert Path("probes/NVDA_20260927.json").is_file()


# --- pmcc fetch (P1-08) -----------------------------------------------------------------------

FETCH = ["fetch", "--symbol", "nvda", "--start", "2026-09-14", "--end", "2026-09-18"]
PROBE_REPORT = Path("data_cache/probes/NVDA_20260927.json")
STEP_RECORDS = {  # a $2.50 fallback near the money, where the fake measures $1
    "weekly_near_money": {"step_cents": 250, "anchor_answered": True},
    "monthly_deep_itm": {"step_cents": 500, "anchor_answered": True},
}

type Event = tuple[str, object]


@pytest.fixture(autouse=True)
def _reset_logging() -> Generator[None]:
    """The commands configure structlog for the process; put it back after each test."""
    yield
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def events() -> list[Event]:
    """What the command printed and asked, in order."""
    return []


@pytest.fixture
def fetch_market(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, events: list[Event]
) -> FakeMarket:
    """A fake market behind `lseg_session`, a probe report, and `tmp_path` as the working dir."""
    fake = FakeMarket(load_calendar(), NOW.date(), hourly_from=date(2026, 3, 1))
    served = fake.history

    def history(
        rics: Sequence[str], fields: Sequence[str], start: date, end: date, interval: Interval
    ) -> RawHistory:
        events.append(("request", tuple(rics)))
        return served(rics, fields, start, end, interval)

    @contextmanager
    def session() -> Generator[FakeMarket]:
        yield fake

    def say(text: str) -> None:
        events.append(("say", text))

    no_wait = Retry(sleep=lambda _: None)
    monkeypatch.setattr(fake, "history", history)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "lseg_session", session)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    monkeypatch.setattr(cli, "_say", say)
    monkeypatch.setattr(cli, "prepare", partial(prepare, retry=no_wait))
    monkeypatch.setattr(cli, "pull_units", partial(pull_units, retry=no_wait))
    PROBE_REPORT.parent.mkdir(parents=True)
    PROBE_REPORT.write_text(json.dumps({"increments": STEP_RECORDS}), encoding="utf-8")
    return fake


def _fetch(*extra: str) -> tuple[int, str]:
    result = runner.invoke(app, [*FETCH, *extra])
    return result.exit_code, result.output


def _said(events: list[Event]) -> str:
    return "\n".join(str(text) for kind, text in events if kind == "say")


def _cache() -> SymbolCache:
    return SymbolCache(Path("data_cache"), "NVDA")


def test_cli_fetch_plan_only_prints_the_estimate_and_asks_only_for_the_stock(
    fetch_market: FakeMarket, events: list[Event]
) -> None:
    code, output = _fetch("--plan-only")

    assert code == 0, output
    assert "RIC requests" in _said(events)
    assert "data_cache/probes/NVDA_20260927.json" in _said(events)
    assert [rics for kind, rics in events if kind == "request"] == [("NVDA.O",)]
    assert not Path("data_cache/NVDA").exists()


def test_cli_fetch_prints_the_estimate_before_any_option_request(
    fetch_market: FakeMarket, events: list[Event]
) -> None:
    code, output = _fetch()

    assert code == 0, output
    estimate = next(i for i, (kind, _) in enumerate(events) if kind == "say")
    assert "RIC requests" in str(events[estimate][1])
    asked = [(i, rics) for i, (kind, rics) in enumerate(events) if kind == "request"]
    options = [i for i, rics in asked if rics != ("NVDA.O",)]
    assert options
    assert estimate < options[0]


def test_cli_fetch_caches_every_unit_and_prints_the_coverage(
    fetch_market: FakeMarket, events: list[Event]
) -> None:
    code, output = _fetch()

    assert code == 0, output
    said = _said(events)
    units = _cache().unit_names()
    assert f"{len(units)} units written" in said
    assert "NVDA coverage" in said
    assert "IV failures (session bars with a valid mid" in said
    assert "Log: logs/fetch_" in said


def test_cli_fetch_prices_the_coverage_at_the_universes_r(
    fetch_market: FakeMarket, monkeypatch: pytest.MonkeyPatch
) -> None:
    rates: list[float] = []
    real = cli.coverage.coverage

    def spy(root: Path, symbol: str, calendar: SessionCalendar, rate: float) -> Coverage:
        rates.append(rate)
        return real(root, symbol, calendar, rate)

    monkeypatch.setattr(cli.coverage, "coverage", spy)

    code, output = _fetch()

    assert code == 0, output
    assert rates == [load_universe(load_calendar()).risk_free_rate.value]  # DEC-11, DEC-16


def test_cli_fetch_resumes_after_an_outage(fetch_market: FakeMarket, events: list[Event]) -> None:
    fetch_market.dies_after = 100

    code, output = _fetch()

    assert code == 1
    assert "run the same command again to resume" in output
    cached = set(_cache().unit_names())
    assert cached
    fetch_market.dies_after = None
    events.clear()

    code, output = _fetch()

    assert code == 0, output
    assert f"{len(set(_cache().unit_names()) - cached)} units written" in _said(events)
    assert ("request", ("NVDA.O",)) not in events  # the cached tape is planned from


def test_cli_fetch_needs_a_probe_report_before_asking_anything(fetch_market: FakeMarket) -> None:
    PROBE_REPORT.unlink()

    code, output = _fetch()

    assert code == 1
    assert "pmcc probe --symbol NVDA" in output
    assert fetch_market.calls == 0


def test_cli_fetch_refuses_a_symbol_outside_the_universe(fetch_market: FakeMarket) -> None:
    code, output = _fetch("--symbol", "AAPL")

    assert code == 1
    assert "isn't in configs/universe.yaml" in output
    assert fetch_market.calls == 0


def test_cli_fetch_refuses_a_cache_from_another_window(fetch_market: FakeMarket) -> None:
    _fetch()
    calls = fetch_market.calls

    code, output = _fetch("--start", "2026-09-21", "--end", "2026-09-25")

    assert code == 1
    assert "superseded/" in output
    assert fetch_market.calls == calls


def test_cli_fetch_gives_an_unmeasured_band_the_probe_reports_step(
    fetch_market: FakeMarket,
) -> None:
    fetch_market.unlisted = {17_000, 18_000, 19_000}  # the Sep 18 weekly's anchor and neighbours

    code, output = _fetch()

    assert code == 0, output
    (weekly,) = [u for u in _cache().units() if u.name == "chains/2026-09-18_C"]
    assert [(b.step, b.source) for b in weekly.bands] == [(250, StepSource.PROBE_REPORT)]


def test_cli_fetch_refuses_a_stopped_probe_report_before_asking_anything(
    fetch_market: FakeMarket,
) -> None:
    Path("data_cache/probes/NVDA_20260928.json").write_text(
        json.dumps({"symbol": "NVDA", "stopped": "a never-listed RIC answered"}), encoding="utf-8"
    )

    code, output = _fetch()

    assert code == 1
    assert "stopped early" in output
    assert fetch_market.calls == 0


def test_cli_fetch_refuses_a_window_ending_on_a_weekend_before_asking_anything(
    fetch_market: FakeMarket,
) -> None:
    code, output = _fetch("--end", "2026-09-19")

    assert code == 1
    assert "must start and end on sessions" in output
    assert fetch_market.calls == 0
