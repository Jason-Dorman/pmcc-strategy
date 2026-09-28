"""P1-04 probes over a synthetic market behind the port (`tests/fakes/market.py`).

One report is built once, over a market whose hourly history starts on Mar 1 2026; each test reads
one check from it. The market's prices step $0.01 an hour, so only the close bar (15:00 ET start)
matches the daily close and closing quote, as DEC-06 expects of LSEG.
"""

import json
import math
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any, cast

import polars as pl
import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.fetch import Retry
from pmcc.data.probe import ProbeStoppedError, probe_path, run_probe, write_report
from pmcc.data.probe.bars import compare
from pmcc.data.probe.context import Json, Probe
from pmcc.data.probe.coverage import MAX_STRIKES, delta_strikes, strike_for_delta
from pmcc.data.probe.depth import Sample, reaches_back_to
from pmcc.data.probe.identifiers import DailyTape, tape_checks
from pmcc.data.provider import Interval, ProviderOutageError, raw_schema
from pmcc.domain.clock import ET, to_et
from tests.fakes.market import FakeMarket, not_found

CAL = load_calendar()
NOW = datetime(2026, 9, 27, 12, tzinfo=ET)  # a Sunday: the last session is Fri Sep 25
TODAY = NOW.date()
HOURLY_FROM = date(2026, 3, 1)
NO_WAIT = Retry(sleep=lambda _: None)


def _market(today: date = TODAY, **kwargs: Any) -> FakeMarket:
    return FakeMarket(CAL, today, hourly_from=HOURLY_FROM, **kwargs)


@pytest.fixture(scope="module")
def market() -> FakeMarket:
    return _market()


@pytest.fixture(scope="module")
def report(market: FakeMarket) -> Json:
    return run_probe(market, "NVDA", CAL, NOW, NO_WAIT)


def _get(node: object, *path: str) -> object:
    """The value at `path` in a report's nested dicts."""
    for key in path:
        assert isinstance(node, dict), path
        node = cast("dict[str, object]", node)[key]
    return node


# --- The report as a whole --------------------------------------------------------------------


def test_probe_report_runs_every_check_and_counts_its_requests(
    report: Json, market: FakeMarket
) -> None:
    for section in ("identifiers", "errors", "bars", "fields", "increments", "coverage", "depth"):
        assert section in report
    assert report["stopped"] is None
    assert report["requests"] == market.calls
    assert (report["last_session"], report["fetch_date"]) == ("2026-09-25", "2026-09-27")


def test_probe_report_is_json_ready(report: Json, tmp_path: Path) -> None:
    path = tmp_path / "NVDA_20260927.json"
    write_report(report, path)
    assert json.loads(path.read_text(encoding="utf-8"))["symbol"] == "NVDA"


# --- DEC-12 and the calendar ------------------------------------------------------------------


def test_dec_12_probe_asks_every_suffix_alone_and_chooses_the_one_that_answers(
    report: Json,
) -> None:
    stock = _get(report, "identifiers", "stock")
    assert _get(stock, "chosen") == "NVDA.O"
    assert _get(stock, "answered") == ["NVDA.O", "NVDA.N", "NVDA.P", "NVDA.A", "NVDA.Z"]
    wrong = _get(stock, "candidates", "NVDA.K")
    assert _get(wrong, "outcome") == "no_data"
    assert _get(wrong, "codes") == [not_found(Interval.DAILY)]


def test_dec_12_probe_goes_on_with_the_first_suffix_in_order_that_answers() -> None:
    report = run_probe(_market(stocks=("NVDA.P", "NVDA.N")), "NVDA", CAL, NOW, NO_WAIT)
    assert _get(report, "identifiers", "stock", "answered") == ["NVDA.N", "NVDA.P"]
    assert _get(report, "identifiers", "stock", "chosen") == "NVDA.N"
    assert _get(report, "bars", "stock_ric") == "NVDA.N"


def test_dec_12_probe_finds_no_split_and_a_strike_that_fits(report: Json) -> None:
    moves = cast("list[object]", _get(report, "identifiers", "largest_moves"))
    assert moves
    assert not any(_get(m, "split_like") for m in moves)
    assert _get(report, "identifiers", "max_strike", "fits_ric_strike_field") is True


def test_dec_33_probe_checks_the_holiday_table_against_the_daily_tape(report: Json) -> None:
    check = _get(report, "identifiers", "calendar_check")
    assert _get(check, "ok") is True
    assert (_get(check, "from"), _get(check, "to")) == ("2025-01-02", "2026-09-25")


def test_dec_33_probe_reports_a_tape_that_disagrees_with_the_table() -> None:
    # The tape trades on Jul 3 2026 (closed in the table) and not on Mar 5 2025 (a session).
    market = _market(traded_closed={date(2026, 7, 3)}, untraded={date(2025, 3, 5)})
    check = _get(run_probe(market, "NVDA", CAL, NOW, NO_WAIT), "identifiers", "calendar_check")
    assert _get(check, "ok") is False
    assert _get(check, "traded_but_closed") == ["2026-07-03"]
    assert _get(check, "session_without_bars") == ["2025-03-05"]
    assert "Independence Day" in str(_get(check, "detail"))


# --- DEC-83 -----------------------------------------------------------------------------------


@pytest.mark.parametrize("interval", ["hourly", "daily"])
@pytest.mark.parametrize("form", ["expired", "live"])
def test_dec_83_probe_records_the_never_listed_answer(
    report: Json, interval: str, form: str
) -> None:
    asked = _get(report, "errors", "asks", f"never_listed_{interval}_{form}_form")
    assert _get(asked, "outcome") == "no_data"
    assert _get(asked, "codes") == [not_found(Interval(interval))]
    assert "No data to return" in str(_get(asked, "message"))


def test_dec_83_probe_records_a_field_the_ric_does_not_carry(report: Json) -> None:
    asked = _get(report, "errors", "asks", "field_not_carried_hourly")
    assert _get(asked, "outcome") == "answered"  # left out, as LSEG did (DEC-83)
    assert _get(asked, "fields_with_values") == ["TRDPRC_1"]


def test_dec_83_probe_records_how_batches_holding_a_failure_answer(report: Json) -> None:
    asks = _get(report, "errors", "asks")
    hourly = _get(asks, "batch_hourly_listed_and_never_listed")
    daily = _get(asks, "batch_daily_listed_and_never_listed")
    assert _get(hourly, "outcome") == "unreadable"
    assert _get(daily, "outcome") == "answered"
    unattributable = _get(asks, "batch_hourly_field_not_carried", "error_class")
    assert unattributable == "Unattributable"
    assert _get(daily, "answered") == ["NVDAJ162618000.U"]


def test_dec_83_probe_gathers_every_code_it_saw(report: Json) -> None:
    codes = _get(report, "errors", "codes_seen")
    assert codes == sorted({not_found(Interval.HOURLY), not_found(Interval.DAILY)})
    assert _get(report, "errors", "never_listed_is_no_data") is True


@pytest.mark.parametrize("interval", [Interval.HOURLY, Interval.DAILY])
def test_dec_83_probe_stops_when_any_never_listed_ric_answers(interval: Interval) -> None:
    # Each interval's never-listed asks answer alone, so `any` in place of `all` would pass one.
    stopped = run_probe(_market(odd_strikes_answer={interval}), "NVDA", CAL, NOW, NO_WAIT)
    assert "no-data code" in str(stopped["stopped"])
    assert "bars" not in stopped
    assert _get(stopped, "errors", "never_listed_is_no_data") is False


def test_dec_83_never_listed_failing_with_another_code_is_an_outage_not_a_report() -> None:
    # Not a no-data code: asked again like any fetch (DEC-49), then an outage; nothing to write.
    with pytest.raises(ProviderOutageError, match="SomethingElse"):
        run_probe(_market(never_listed_transient=True), "NVDA", CAL, NOW, NO_WAIT)


# --- DEC-06 -----------------------------------------------------------------------------------


def test_dec_06_probe_finds_the_close_print_and_quote_in_the_1500_bar(report: Json) -> None:
    summary = _get(report, "bars", "summary")
    assert _get(summary, "sessions") == 5
    assert _get(summary, "stock_close_print_in_close_hour_bar") == 5
    assert _get(summary, "option_closing_quote_in_close_hour_bar") == 5
    assert _get(summary, "stock_close_print_by_bar_start") == {"15:00": 5}


def test_dec_06_probe_keeps_the_raw_bars_as_evidence(report: Json) -> None:
    sessions = _get(report, "bars", "sessions")
    assert isinstance(sessions, list)
    first = cast("list[object]", sessions)[0]
    assert _get(first, "stock", "first_bar_start") == "04:00"
    assert _get(first, "stock", "last_bar_start") == "19:00"
    assert _get(first, "option", "last_bar_start") == "16:00"


# --- DEC-13 -----------------------------------------------------------------------------------


def test_dec_13_probe_asks_each_field_paired_with_trdprc_1(
    report: Json, market: FakeMarket
) -> None:
    assert _get(report, "fields", "option", "refused") == []
    assert len(cast("list[str]", _get(report, "fields", "option", "carried"))) == 8
    asked = [fields for _, fields, *_ in market.requests if "NUM_MOVES" in fields]
    assert ("TRDPRC_1", "NUM_MOVES") in asked


# --- DEC-14 -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("region", "step"),
    [
        ("weekly_near_money", 100),
        ("weekly_near_money_expired", 100),
        ("monthly_near_money", 100),
        ("monthly_deep_itm", 500),
    ],
)
def test_dec_14_probe_measures_each_regions_increment(report: Json, region: str, step: int) -> None:
    assert _get(report, "increments", region, "step_cents") == step
    assert _get(report, "increments", region, "anchor_answered") is True


def test_dec_14_expired_weekly_answers_in_the_caret_form(report: Json) -> None:
    assert _get(report, "increments", "weekly_near_money_expired", "forms_used") == ["expired"]


# --- DEC-08 and DEC-09 ------------------------------------------------------------------------


def test_dec_08_probe_measures_mid_availability_and_spread(report: Json) -> None:
    pooled = _get(report, "coverage", "pooled")
    assert _get(pooled, "valid_mid_share") == 1.0
    assert _get(pooled, "below_intrinsic") == 0
    spread = _get(pooled, "median_spread_pct")
    assert isinstance(spread, float)
    assert 0 < spread < 1
    assert _get(report, "coverage", "session_bars_per_contract") == 20 * 7


def test_dec_09_live_contracts_answer_in_the_live_form_only(report: Json) -> None:
    live = _get(report, "coverage", "live_form")
    assert _get(live, "answered") == _get(live, "asked")
    assert _get(live, "forms_asked") == ["live"]
    assert _get(live, "forms_used") == ["live"]


def test_dec_08_strike_for_delta_inverts_black_scholes_delta() -> None:
    spot, vol, years = 180.0, 0.4, 0.5
    for delta in (0.9, 0.7):
        strike = strike_for_delta(spot, vol, years, delta)
        d1 = (math.log(spot / strike) + vol**2 * years / 2) / (vol * math.sqrt(years))
        assert NormalDist().cdf(d1) == pytest.approx(delta, abs=1e-12)


def test_dec_08_delta_strikes_sit_on_the_grid_and_are_thinned_to_eight() -> None:
    wide_band = delta_strikes(500.0, 0.6, 0.5, 100)
    assert len(wide_band) == MAX_STRIKES
    assert all(k % 100 == 0 for k in wide_band)
    assert delta_strikes(100.0, 0.0001, 0.5, 500) == [10_000]  # narrower than a step


# --- DEC-07 -----------------------------------------------------------------------------------


def test_dec_07_probe_finds_how_far_back_hourly_bars_go(report: Json) -> None:
    back_to = _get(report, "depth", "back_to")
    assert back_to == {
        "stock": "2026-03-23",
        "weekly_call": "2026-03-23",
        "long_call": "2026-03-23",
    }


def test_dec_07_a_gap_stops_the_reach_even_if_older_weeks_answer() -> None:
    samples = [
        Sample(date(2026, 8, 24), {}, {"stock": True}),
        Sample(date(2026, 7, 27), {}, {"stock": False}),
        Sample(date(2026, 6, 22), {}, {"stock": True}),
    ]
    assert reaches_back_to(samples, "stock") == "2026-08-24"
    assert reaches_back_to(samples[1:], "stock") is None


# --- Failures ---------------------------------------------------------------------------------


@pytest.mark.parametrize("served", [0, 3, 6, 8, 12, 17, 30, 60, 90])
def test_probe_dead_workspace_is_an_outage_at_every_stage(served: int) -> None:
    # A dying Workspace reaches the port only as transient failures (DEC-83): whether it dies in
    # the suffix asks, the daily tape, the DEC-83 asks (calls 8-18) or the quote checks, the probe
    # raises and returns nothing to write.
    with pytest.raises(ProviderOutageError, match="Unauthorized"):
        run_probe(_market(dies_after=served), "NVDA", CAL, NOW, NO_WAIT)


def test_probe_stops_when_no_stock_ric_answers() -> None:
    with pytest.raises(ProbeStoppedError, match="no stock RIC answered for ZZZZ"):
        run_probe(_market(), "ZZZZ", CAL, NOW, NO_WAIT)


# --- The report file --------------------------------------------------------------------------


def test_probe_path_is_symbol_and_date() -> None:
    assert probe_path(Path("probes"), "NVDA", date(2026, 9, 27)) == Path(
        "probes/NVDA_20260927.json"
    )


def test_probe_report_is_written_sorted_with_lf_and_nan_as_null(tmp_path: Path) -> None:
    path = tmp_path / "probes" / "X_20260927.json"
    write_report({"b": math.nan, "a": [1.5, math.inf]}, path)
    raw = path.read_bytes()
    assert raw == b'{\n  "a": [\n    1.5,\n    null\n  ],\n  "b": null\n}\n'
    assert list(path.parent.iterdir()) == [path]  # no partial file left


def test_probe_report_is_never_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "X_20260927.json"
    write_report({"first": True}, path)
    with pytest.raises(FileExistsError, match="never overwritten"):
        write_report({"second": True}, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"first": True}


# --- DEC-47 -----------------------------------------------------------------------------------

WEEK = ["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"]


@pytest.mark.parametrize("interval", ["daily", "hourly"])
@pytest.mark.parametrize(
    ("window", "days"),
    [("first_session", WEEK[:1]), ("week", WEEK), ("last_session", WEEK[-1:])],
)
def test_dec_47_probe_records_the_days_each_window_returns(
    report: Json, interval: str, window: str, days: list[str]
) -> None:
    edge = _get(report, "edges", f"{window}_{interval}")
    assert _get(edge, "start") == days[0]
    assert _get(edge, "days") == days  # the fake reads start and end as LSEG is assumed to


def test_dec_14_probe_records_the_bar_dates_each_increment_request_returned(report: Json) -> None:
    assert _get(report, "increments", "monthly_deep_itm", "bar_dates") == ["2026-09-25"]


def test_dec_83_probe_asks_a_field_name_the_service_cannot_know(report: Json) -> None:
    asked = _get(report, "errors", "asks", "unknown_field_hourly")
    assert _get(asked, "fields") == ["TRDPRC_1", "PMCC_NO_SUCH_FIELD"]


# --- Runs early in a week, and edge values ----------------------------------------------------

TUESDAY = datetime(2026, 9, 22, 11, tzinfo=ET)  # the last session is Mon Sep 21


def test_dec_47_edges_use_the_last_complete_week_when_run_mid_week() -> None:
    market = _market(today=TUESDAY.date())
    report = run_probe(market, "NVDA", CAL, TUESDAY, NO_WAIT)
    week = _get(report, "edges", "week_hourly")
    assert (_get(week, "start"), _get(week, "end_exclusive")) == ("2026-09-14", "2026-09-19")
    assert _get(week, "days") == [
        "2026-09-14",
        "2026-09-15",
        "2026-09-16",
        "2026-09-17",
        "2026-09-18",
    ]
    edge_ends = [end for rics, _, _, end, _ in market.requests if rics == ("NVDA.O",)]
    assert max(edge_ends) <= TUESDAY.date()


def test_dec_83_expired_weekly_is_at_least_a_week_before_the_last_session() -> None:
    report = run_probe(_market(today=TUESDAY.date()), "NVDA", CAL, TUESDAY, NO_WAIT)
    ric = cast(
        "list[str]", _get(report, "errors", "asks", "never_listed_hourly_expired_form", "rics")
    )[0]
    assert ric.startswith("NVDAI1126")  # Sep 11, not Sep 18 (3 days before Mon Sep 21)
    assert _get(report, "increments", "weekly_near_money_expired", "expiry") == "2026-09-11"


def test_dec_13_a_field_that_comes_back_without_values_is_empty_not_carried() -> None:
    report = run_probe(_market(empty_fields={"NUM_MOVES"}), "NVDA", CAL, NOW, NO_WAIT)
    assert _get(report, "fields", "option", "empty") == ["NUM_MOVES"]
    assert "NUM_MOVES" not in cast("list[str]", _get(report, "fields", "option", "carried"))


def _tape(closes: list[float], highs: list[float] | None = None) -> DailyTape:
    days = [s.day for s in CAL.sessions(date(2025, 6, 2), date(2026, 9, 25))][-len(closes) :]
    highs = highs or [c + 1 for c in closes]
    frame = pl.DataFrame(
        {"day": days, "TRDPRC_1": closes, "HIGH_1": highs, "LOW_1": [c - 1 for c in closes]}
    )
    return DailyTape(frame)


def _probe() -> Probe:
    return Probe("NVDA", "NVDA", CAL, _market(), NOW, NO_WAIT)


def test_dec_12_a_halved_close_is_split_like_and_leads_the_largest_moves() -> None:
    closes = [100.0 + (i % 2) for i in range(60)] + [50.0 + (i % 2) for i in range(60)]
    [top, *_] = cast("list[object]", tape_checks(_probe(), _tape(closes))["largest_moves"])
    assert _get(top, "split_like") is True
    assert _get(top, "close_ratio") == pytest.approx(0.5, abs=0.01)


def test_dec_12_max_strike_flags_a_band_top_past_999_99() -> None:
    closes = [900.0 * (1 + 0.02 * (-1) ** i) for i in range(260)]
    record = cast("dict[str, object]", tape_checks(_probe(), _tape(closes))["max_strike"])
    top = cast("float", record["band_top_estimate"])
    high = cast("float", record["year_high"])
    sigma = cast("float", record["band_vol"])
    assert top == pytest.approx(high * (1 + 2.5 * sigma * math.sqrt(5 / 252)), rel=1e-4)
    assert record["fits_ric_strike_field"] is False


def test_dec_06_a_quote_matches_only_when_bid_and_ask_both_do() -> None:
    day = date(2026, 9, 25)
    stamp = datetime(2026, 9, 25, 15, tzinfo=ET).astimezone(UTC)
    rows = [("BID", 1.0), ("ASK", 1.2)]
    hourly = pl.DataFrame(
        [{"bar_start": stamp, "ric": "X", "field": f, "value": v} for f, v in rows],
        schema=raw_schema(Interval.HOURLY),
    )
    daily_rows = [
        {"bar_start": day, "ric": "X", "field": "BID", "value": 1.0},
        {"bar_start": day, "ric": "X", "field": "ASK", "value": 1.3},
    ]
    daily = pl.DataFrame(daily_rows, schema=raw_schema(Interval.DAILY))
    assert compare(hourly, daily, day, ("BID", "ASK")).matching_bar_starts == []
    assert compare(hourly, daily, day, ("BID",)).matching_bar_starts == ["15:00"]


@pytest.mark.parametrize(
    ("now", "last"),
    [
        (datetime(2026, 9, 25, 15, 59, tzinfo=ET), date(2026, 9, 24)),  # before the close
        (datetime(2026, 9, 25, 16, 0, tzinfo=ET), date(2026, 9, 25)),  # at the close
        (datetime(2026, 9, 8, 9, 0, tzinfo=ET), date(2026, 9, 4)),  # Tue after Labor Day
        (datetime(2026, 11, 27, 13, 0, tzinfo=ET), date(2026, 11, 27)),  # half-day close
        (datetime(2026, 9, 26, 1, 0, tzinfo=UTC), date(2026, 9, 25)),  # UTC Sat = ET Fri 21:00
    ],
)
def test_probe_last_session_is_the_latest_whose_close_has_passed(now: datetime, last: date) -> None:
    probe = Probe("NVDA", "NVDA", CAL, _market(), to_et(now), NO_WAIT)
    assert probe.last_session.day == last
