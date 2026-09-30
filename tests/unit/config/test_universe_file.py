"""`configs/universe.yaml`: the PO's window, r and identifiers (DEC-07, DEC-11, DEC-12), checked
against the calendar they run on (P1-05)."""

import json
import math
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from pmcc.config.calendar import load_calendar
from pmcc.config.universe import (
    MIN_WEEKS,
    UNIVERSE_PATH,
    continuous_rate,
    load_universe,
    read_universe_file,
)
from pmcc.data.discovery import SessionRange, plan_symbol, stock_unit
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain import Money, OptionId, Price, Right

CAL = load_calendar()
UNIVERSE = load_universe(CAL)

# The PO's universe (DEC-15), in the spec's order, at each primary listing (DEC-12).
PRIMARY_LISTINGS = {"QQQ": "QQQ.O", "NVDA": "NVDA.O", "TSLA": "TSLA.O"}


def test_universe_file_holds_the_po_window() -> None:
    assert (UNIVERSE.window.start, UNIVERSE.window.end) == (date(2026, 3, 30), date(2026, 9, 25))
    assert UNIVERSE_PATH.parts[-2:] == ("configs", "universe.yaml")


def test_universe_file_window_is_26_whole_weeks() -> None:
    start, end = UNIVERSE.window.start, UNIVERSE.window.end
    assert CAL.week_open(start).day == start
    assert CAL.week_final(end).day == end
    assert len(CAL.weekly_expiries(start, end)) == 26
    assert len(CAL.sessions(start, end)) == 125


def test_universe_file_r_is_dgs3mo_at_the_last_close_before_the_window() -> None:
    rate = UNIVERSE.risk_free_rate
    assert (rate.value, rate.quoted_pct, rate.series) == (0.0371, 3.73, "DGS3MO")
    assert rate.as_of == date(2026, 3, 27)
    assert rate.as_of == CAL.sessions_before(UNIVERSE.window.start, 1)[0].day
    assert "fred.stlouisfed.org/series/DGS3MO" in rate.source


def test_universe_file_lists_the_po_universe_at_its_primary_listings() -> None:
    assert tuple(u.symbol for u in UNIVERSE.symbols) == tuple(PRIMARY_LISTINGS)
    assert {u.symbol: u.stock_ric for u in UNIVERSE.symbols} == PRIMARY_LISTINGS
    assert all(u.option_root == u.symbol for u in UNIVERSE.symbols)


def test_universe_file_roots_build_option_rics() -> None:
    for u in UNIVERSE.symbols:
        option = OptionId(u.option_root, date(2026, 9, 18), Right.CALL, Price.from_dollars(100))
        assert build_ric(option, RicForm.LIVE) == f"{u.option_root}I182610000.U"


def _flat_tape(first: date, last: date) -> list[SessionRange]:
    """Every session, $100-$110, closes alternating by 1%: enough to plan with."""
    sessions = CAL.sessions(first, last)
    closes = [105 * math.exp(0.01 * (i % 2)) for i in range(len(sessions))]
    return [
        SessionRange(s.day, Price.from_dollars(100), Price.from_dollars(110), Price.from_dollars(c))
        for s, c in zip(sessions, closes, strict=True)
    ]


def test_universe_file_calendar_covers_everything_the_fetch_plan_asks() -> None:
    start, end = UNIVERSE.window.start, UNIVERSE.window.end
    warm_up = stock_unit(CAL, start, end)
    plan = plan_symbol(CAL, _flat_tape(warm_up.start, end), start, end)
    expiries = sorted({u.expiry for u in plan.units if u.expiry is not None})
    assert warm_up.start == date(2026, 2, 13)  # 30 sessions before Mar 30 (Presidents' Day out)
    assert date(2026, 10, 2) in expiries  # G-3's next weekly after the window
    assert expiries[-1] == date(2027, 6, 17)  # the last monthly within 270 DTE of Sep 25
    assert expiries[-1] <= CAL.last_day


# --- Refusals ---------------------------------------------------------------------------------


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "universe.yaml"
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def _rate(
    value: str = "0.0371",
    quoted: str = "3.73",
    series: str = "DGS3MO",
    as_of: str = "2026-03-27",
    source: str = ", source: x",
) -> str:
    return f"{{value: {value}, quoted_pct: {quoted}, series: {series}, as_of: {as_of}{source}}}"


def _body(
    start: str = "2026-03-30",
    end: str = "2026-09-25",
    rate: str = _rate(),
    symbols: str = "[{symbol: SPY, stock_ric: SPY.P, option_root: SPY}]",
    extra: str = "",
) -> str:
    return (
        f"window: {{start: {start}, end: {end}}}\n"
        f"risk_free_rate: {rate}\n"
        f"symbols: {symbols}\n"
        f"{extra}"
    )


def _one(entry: str) -> str:
    return _body(symbols=f"[{{{entry}}}]")


def test_universe_file_reads_a_minimal_file(tmp_path: Path) -> None:
    universe = load_universe(CAL, _write(tmp_path, _body()))
    assert [u.symbol for u in universe.symbols] == ["SPY"]


def test_universe_file_starting_cash_is_unset_until_p3_09() -> None:
    assert UNIVERSE.starting_cash is None


def test_universe_file_starting_cash_is_optional(tmp_path: Path) -> None:
    assert read_universe_file(_write(tmp_path, _body())).starting_cash is None


@pytest.mark.parametrize(("text", "units"), [("25000", 250_000_000), ("12345.6789", 123_456_789)])
def test_universe_file_reads_starting_cash_as_exact_money(
    tmp_path: Path, text: str, units: int
) -> None:
    universe = read_universe_file(_write(tmp_path, _body(extra=f"starting_cash: {text}\n")))

    assert universe.starting_cash == Money(units)


MALFORMED = {
    # Unknown keys, at every level.
    "unknown-key": _body(extra="starting_capital: 10000\n"),
    # Starting cash (DEC-30): dollars, exact to $0.0001, not negative.
    "cash-negative": _body(extra="starting_cash: -1\n"),
    "cash-sub-unit": _body(extra="starting_cash: 10000.00005\n"),
    "cash-text": _body(extra="starting_cash: ten thousand\n"),
    "cash-bool": _body(extra="starting_cash: true\n"),
    "unknown-window-key": _body().replace("end: 2026-09-25}", "end: 2026-09-25, warmup: 45}"),
    "unknown-rate-key": _body(rate=_rate(source=", source: x, basis: discount")),
    "unknown-symbol-key": _one("symbol: SPY, stock_ric: SPY.P, option_root: SPY, optoin_root: X"),
    # The window and the list.
    "end-before-start": _body(start="2026-09-25", end="2026-03-30"),
    "no-symbols": _body(symbols="[]"),
    "symbol-twice": _body(
        symbols="[{symbol: SPY, stock_ric: SPY.P, option_root: SPY},"
        " {symbol: SPY, stock_ric: SPY.N, option_root: SPY}]"
    ),
    # Stock RICs: another symbol's (unrelated, or only sharing a prefix), no venue, a bad venue.
    "other-symbols-ric": _one("symbol: AMD, stock_ric: AAPL.O, option_root: AMD"),
    "prefix-symbols-ric": _one("symbol: SPY, stock_ric: SPYG.P, option_root: SPY"),
    "longer-symbols-ric": _one("symbol: AMDL, stock_ric: AMD.O, option_root: AMDL"),
    "ric-without-venue": _one("symbol: SPY, stock_ric: SPY, option_root: SPY"),
    "ric-lower-case-venue": _one("symbol: SPY, stock_ric: SPY.p, option_root: SPY"),
    "ric-three-letter-venue": _one("symbol: SPY, stock_ric: SPY.PQX, option_root: SPY"),
    "lower-case-root": _one("symbol: SPY, stock_ric: SPY.P, option_root: spy"),
    # r: no source, an empty source or series, known too late, or not its quote converted.
    "rate-without-source": _body(rate=_rate(source="")),
    "rate-empty-source": _body(rate=_rate(source=', source: ""')),
    "rate-empty-series": _body(rate=_rate(series='""')),
    "rate-not-known-before-the-window": _body(rate=_rate(as_of="2026-03-30")),
    "rate-1bp-high": _body(rate=_rate(value="0.0372")),
    "rate-1bp-low": _body(rate=_rate(value="0.0370")),
    "rate-2bp-high": _body(rate=_rate(value="0.0373")),
    "quote-typo": _body(rate=_rate(quoted="3.74")),
    "quote-typo-low": _body(rate=_rate(quoted="3.72")),
}


@pytest.mark.parametrize("body", MALFORMED.values(), ids=MALFORMED.keys())
def test_universe_file_refuses_a_malformed_file(tmp_path: Path, body: str) -> None:
    with pytest.raises(ValidationError):
        read_universe_file(_write(tmp_path, body))


@pytest.mark.parametrize(
    "body",
    [
        _one("symbol: SPY, stock_ric: SPY.P, stock_ric: SPY.N, option_root: SPY"),
        _body() + "window: {start: 2026-04-06, end: 2026-09-25}\n",  # valid on its own
    ],
    ids=["key-twice-in-an-entry", "top-level-key-twice"],
)
def test_universe_file_refuses_a_key_given_twice(tmp_path: Path, body: str) -> None:
    # yaml.safe_load would keep the last value silently.
    with pytest.raises(ValueError, match="more than once"):
        read_universe_file(_write(tmp_path, body))


ROOTS = ["SPY", "A1", "X", "spy", "1X", "BRK.B", "SP Y", "", "SPÝ", "SPY\n", "SPY "]


@pytest.mark.parametrize("root", ROOTS)
def test_universe_file_roots_follow_option_ids_rule(tmp_path: Path, root: str) -> None:
    try:
        OptionId(root, date(2026, 9, 18), Right.CALL, Price.from_dollars(100))
        option_id_takes_it = True
    except ValueError:
        option_id_takes_it = False
    entry = f"symbol: SPY, stock_ric: SPY.P, option_root: {json.dumps(root)}"
    try:
        read_universe_file(_write(tmp_path, _one(entry)))
        loader_takes_it = True
    except ValidationError:
        loader_takes_it = False
    assert loader_takes_it == option_id_takes_it


def test_universe_window_must_start_on_a_week_open_session(tmp_path: Path) -> None:
    body = _body(start="2026-03-31")  # a Tuesday after a trading Monday
    with pytest.raises(ValueError, match="week-open"):
        load_universe(CAL, _write(tmp_path, body))


def test_universe_window_may_start_the_tuesday_after_labor_day(tmp_path: Path) -> None:
    body = _body(start="2026-09-08", end="2026-11-13", rate=_rate(as_of="2026-09-04"))
    assert load_universe(CAL, _write(tmp_path, body)).window.start == date(2026, 9, 8)


def test_universe_window_must_end_on_a_week_final_session(tmp_path: Path) -> None:
    body = _body(end="2026-09-24")  # a Thursday before a trading Friday
    with pytest.raises(ValueError, match="week-final"):
        load_universe(CAL, _write(tmp_path, body))


def test_universe_window_may_end_on_the_thursday_before_good_friday(tmp_path: Path) -> None:
    body = _body(start="2026-01-26", end="2026-04-02", rate=_rate(as_of="2026-01-23"))
    universe = load_universe(CAL, _write(tmp_path, body))
    assert len(CAL.weekly_expiries(universe.window.start, universe.window.end)) == MIN_WEEKS


def test_universe_window_needs_at_least_ten_weeks(tmp_path: Path) -> None:
    body = _body(end="2026-05-29")  # 9 weeks from Mar 30
    with pytest.raises(ValueError, match="at least 10 weeks"):
        load_universe(CAL, _write(tmp_path, body))


def test_universe_window_outside_the_calendar_raises(tmp_path: Path) -> None:
    body = _body(start="2028-01-03", end="2028-03-31", rate=_rate(as_of="2027-12-30"))
    with pytest.raises(ValueError, match="outside the calendar"):
        load_universe(CAL, _write(tmp_path, body))


@pytest.mark.parametrize("pct", [0.05, 3.73, 5.25, 12.0])
def test_continuous_rate_discounts_a_91_day_bill_to_its_quoted_price(pct: float) -> None:
    # Investment basis: a 91-day bill at y costs 1 / (1 + y * 91/365) (simple interest, ACT/365).
    r = continuous_rate(pct)
    assert math.isclose(math.exp(-r * 91 / 365), 1 / (1 + pct / 100 * 91 / 365), rel_tol=1e-12)
    assert 0 < r < pct / 100


def test_continuous_rate_of_the_po_quote_rounds_to_the_stated_r() -> None:
    # ln(1 + 0.0373 * 91/365) * 365/91, worked to 40 digits with decimal.Decimal.
    assert math.isclose(continuous_rate(3.73), 0.037127633007523278, rel_tol=1e-15)
    assert round(continuous_rate(3.73), 4) == UNIVERSE.risk_free_rate.value
