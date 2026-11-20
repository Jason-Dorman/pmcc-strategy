"""NVDA's volatility for the live page (L4-02; PO, LD-33): the tenor, ATM IV, RV20, the smile, the
sessions a run fills, and the files it keeps."""

import json
import math
from datetime import date
from pathlib import Path

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from pmcc.live.rules import select
from pmcc.live.snapshot import CloseSnapshot
from pmcc.live.vol import (
    VolError,
    VolPoint,
    append_points,
    atm_ladder,
    atm_point,
    read_points,
    read_smile_session,
    rv20_through,
    sessions_to_fill,
    smile,
    tenor_expiry,
    write_smile,
)
from pmcc.pricing.measures import realized_vol
from tests.fakes.live import snapshot
from tests.fakes.vol import RATE, option_quotes

TUESDAY = date(2026, 11, 17)
EXPIRY = date(2026, 12, 18)
IV_TOLERANCE = 0.01  # the quotes are rounded to the cent


@pytest.fixture(scope="module")
def calendar() -> SessionCalendar:
    return load_calendar()


def _price(dollars: str) -> Price:
    return Price.from_dollars(dollars)


# --- The tenor ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (
            date(2026, 11, 17),
            date(2026, 12, 18),
        ),  # Dec 17 is 1 day before the 18th, 6 after the 11th
        (date(2026, 11, 13), date(2026, 12, 11)),  # Dec 13 (a Sunday): 2 days after the 11th
        (date(2026, 11, 16), date(2026, 12, 18)),  # Dec 16: 2 days before the 18th
    ],
)
def test_ld_33_the_tenor_is_the_weekly_expiry_nearest_30_days_out(
    calendar: SessionCalendar, day: date, expected: date
) -> None:
    assert tenor_expiry(calendar, day) == expected


def test_ld_33_a_tie_between_two_expiries_goes_to_the_later(calendar: SessionCalendar) -> None:
    # 30 days after Sat May 23 2026 is Mon Jun 22: Juneteenth closes Fri Jun 19, so that week
    # expires Thu Jun 18, 4 days before; Fri Jun 26 is 4 days after.
    assert tenor_expiry(calendar, date(2026, 5, 23)) == date(2026, 6, 26)


# --- ATM IV ---------------------------------------------------------------------------------------


def test_ld_33_the_atm_ladder_holds_the_nearest_strike_at_either_spacing() -> None:
    ladder = atm_ladder(_price("155.46"))

    assert ladder == tuple(_price(s) for s in ("150", "152.50", "155", "157.50", "160", "162.50"))


def test_ld_33_atm_iv_is_the_mean_of_the_call_and_put_at_the_strike_nearest_the_close(
    calendar: SessionCalendar,
) -> None:
    session = calendar.session(TUESDAY)
    quotes = option_quotes(calendar, session, EXPIRY, 155.46, [150, 152.5, 155, 157.5, 160],
                           call_vol=0.40, put_vol=0.60)  # fmt: skip

    point = atm_point(session, _price("155.46"), calendar.session(EXPIRY), quotes, RATE, 0.45)

    assert point.strike == _price("155")
    assert point.call_iv is not None
    assert point.put_iv is not None
    assert abs(point.call_iv - 0.40) < IV_TOLERANCE
    assert abs(point.put_iv - 0.60) < IV_TOLERANCE
    assert point.atm_iv == pytest.approx((point.call_iv + point.put_iv) / 2)
    assert (point.expiry, point.rv20) == (EXPIRY, 0.45)


def test_ld_33_atm_skips_a_strike_without_both_sides_quoted(calendar: SessionCalendar) -> None:
    session = calendar.session(TUESDAY)
    quotes = option_quotes(calendar, session, EXPIRY, 155.46, [150, 155, 160],
                           unquoted=[(Right.PUT, 155)])  # fmt: skip

    point = atm_point(session, _price("155.46"), calendar.session(EXPIRY), quotes, RATE, None)

    assert point.strike == _price("160")  # $4.54 away, nearer than $150's $5.46


def test_ld_33_a_tie_for_the_atm_strike_goes_lower(calendar: SessionCalendar) -> None:
    session = calendar.session(TUESDAY)
    quotes = option_quotes(calendar, session, EXPIRY, 156.25, [155, 157.5])

    point = atm_point(session, _price("156.25"), calendar.session(EXPIRY), quotes, RATE, None)

    assert point.strike == _price("155")


def test_ld_33_no_strike_with_both_sides_quoted_has_no_atm_iv(calendar: SessionCalendar) -> None:
    session = calendar.session(TUESDAY)
    quotes = option_quotes(calendar, session, EXPIRY, 155.46, [155],
                           unquoted=[(Right.CALL, 155)])  # fmt: skip

    point = atm_point(session, _price("155.46"), calendar.session(EXPIRY), quotes, RATE, 0.4)

    assert (point.strike, point.call_iv, point.put_iv, point.atm_iv) == (None, None, None, None)
    assert point.rv20 == 0.4


# --- RV20 -----------------------------------------------------------------------------------------


def _closes(calendar: SessionCalendar, day: date, count: int) -> dict[date, Price]:
    days = [s.day for s in calendar.sessions_before(day, count - 1)] + [day]
    return {d: _price(f"{150 + (i % 5) * 1.5 - (i % 3):.2f}") for i, d in enumerate(days)}


def test_ld_33_rv20_is_the_20_returns_ending_at_the_sessions_own_close(
    calendar: SessionCalendar,
) -> None:
    closes = _closes(calendar, TUESDAY, 21)

    rv = rv20_through(calendar, TUESDAY, closes)

    assert rv == pytest.approx(realized_vol([closes[d] for d in sorted(closes)]))
    moved = {**closes, TUESDAY: _price("170")}
    assert rv20_through(calendar, TUESDAY, moved) != rv  # its own close counts


def test_ld_33_rv20_is_none_without_all_21_closes(calendar: SessionCalendar) -> None:
    closes = _closes(calendar, TUESDAY, 21)
    del closes[min(closes)]

    assert rv20_through(calendar, TUESDAY, closes) is None


# --- The smile ------------------------------------------------------------------------------------


def test_ld_33_the_smile_is_the_out_of_the_money_side_with_the_pick(
    calendar: SessionCalendar,
) -> None:
    snap = snapshot(calendar, vol=0.55)
    pick = select(snap, Right.PUT, 0.30, RATE, calendar)

    curve = smile(snap, RATE, calendar, pick)

    close = snap.close.units
    assert curve.points
    assert all((p.right is Right.PUT) == (p.strike.units < close) for p in curve.points)
    assert all(p.strike.units != close for p in curve.points)
    assert [p.strike for p in curve.points] == sorted(p.strike for p in curve.points)
    assert all(abs(p.iv - 0.55) < 0.02 for p in curve.points)
    assert all((p.delta < 0) == (p.right is Right.PUT) for p in curve.points)
    assert pick is not None
    assert curve.pick == pick.option.strike
    assert (curve.session, curve.expiry) == (snap.session.day, snap.expiry)


def test_ld_33_the_smile_leaves_out_a_contract_without_a_quote(calendar: SessionCalendar) -> None:
    snap = snapshot(calendar, unquoted=["150.00"])

    curve = smile(snap, RATE, calendar, None)

    assert _price("150") not in {p.strike for p in curve.points}
    assert curve.pick is None


# --- The expected move: the ATM straddle (PO, LD-41) ----------------------------------------------


def _mid(snap: CloseSnapshot, strike: str, right: Right) -> int:
    quote = next(
        q.close
        for q in snap.options
        if q.option.strike == _price(strike) and q.option.right is right
    )
    assert quote is not None
    assert quote.bid is not None
    assert quote.ask is not None
    return (quote.bid.units + quote.ask.units) // 2


def test_ld_41_the_straddle_is_the_call_and_put_mids_at_the_strike_nearest_the_close(
    calendar: SessionCalendar,
) -> None:
    snap = snapshot(calendar)  # closes at $162.83

    curve = smile(snap, RATE, calendar, None)

    assert curve.straddle is not None
    assert curve.straddle.strike == _price("162.50")
    expected = _mid(snap, "162.50", Right.CALL) + _mid(snap, "162.50", Right.PUT)
    assert abs(curve.straddle.price.units - expected) <= 1  # each mid rounds half-even


def test_ld_41_the_straddle_skips_a_strike_without_both_sides_quoted(
    calendar: SessionCalendar,
) -> None:
    snap = snapshot(calendar, unquoted=["162.50"])

    curve = smile(snap, RATE, calendar, None)

    assert curve.straddle is not None
    assert curve.straddle.strike == _price("165.00")


def test_ld_41_no_strike_with_both_sides_quoted_has_no_straddle(
    calendar: SessionCalendar,
) -> None:
    snap = snapshot(calendar, strikes=["160.00", "165.00"], unquoted=["160.00", "165.00"])

    assert smile(snap, RATE, calendar, None).straddle is None


# --- Which sessions a run fills -------------------------------------------------------------------


def test_ld_34_a_first_run_fills_the_last_session_alone(calendar: SessionCalendar) -> None:
    filled = sessions_to_fill(calendar, calendar.session(TUESDAY), frozenset(), None)

    assert [s.day for s in filled] == [TUESDAY]


def test_ld_34_a_run_fills_every_session_since_the_last_point(calendar: SessionCalendar) -> None:
    done = frozenset({date(2026, 11, 12)})

    filled = sessions_to_fill(calendar, calendar.session(TUESDAY), done, None)

    assert [s.day for s in filled] == [date(2026, 11, 13), date(2026, 11, 16), TUESDAY]


def test_ld_34_an_up_to_date_file_fills_nothing(calendar: SessionCalendar) -> None:
    assert sessions_to_fill(calendar, calendar.session(TUESDAY), frozenset({TUESDAY}), None) == ()


def test_ld_34_more_than_a_fortnight_behind_needs_a_backfill(calendar: SessionCalendar) -> None:
    done = frozenset({date(2026, 10, 1)})

    with pytest.raises(VolError, match="--since"):
        sessions_to_fill(calendar, calendar.session(TUESDAY), done, None)


def test_ld_34_since_fills_the_sessions_missing_from_that_day(calendar: SessionCalendar) -> None:
    done = frozenset({date(2026, 11, 13), TUESDAY})

    filled = sessions_to_fill(calendar, calendar.session(TUESDAY), done, date(2026, 11, 12))

    assert [s.day for s in filled] == [date(2026, 11, 12), date(2026, 11, 16)]


# --- The files ------------------------------------------------------------------------------------


def _point(day: date, atm: float | None = 0.5) -> VolPoint:
    return VolPoint(day, _price("155.46"), EXPIRY, _price("155"), atm, atm, 0.45)


def test_ld_34_points_append_one_line_each_and_read_back(tmp_path: Path) -> None:
    path = tmp_path / "live" / "vol.jsonl"
    append_points(path, [_point(date(2026, 11, 16))])
    first = path.read_bytes()

    append_points(path, [_point(TUESDAY, None)])

    assert path.read_bytes().startswith(first)  # never rewritten
    rows = read_points(path)
    assert [r["session"] for r in rows] == ["2026-11-16", "2026-11-17"]
    assert rows[1]["atm_iv"] is None
    assert rows[0] == {
        "session": "2026-11-16", "close": "155.46", "expiry": "2026-12-18", "strike": "155.00",
        "call_iv": 0.5, "put_iv": 0.5, "atm_iv": 0.5, "rv20": 0.45,
    }  # fmt: skip
    assert b"\r" not in path.read_bytes()


def test_ld_34_no_file_is_no_points(tmp_path: Path) -> None:
    assert read_points(tmp_path / "vol.jsonl") == ()
    assert read_smile_session(tmp_path / "smile.json") is None


def test_ld_34_the_smile_file_is_replaced_and_names_its_session(
    tmp_path: Path, calendar: SessionCalendar
) -> None:
    path = tmp_path / "live" / "smile.json"
    snap = snapshot(calendar)
    write_smile(path, smile(snap, RATE, calendar, None))

    doc = json.loads(path.read_text(encoding="utf-8"))

    assert read_smile_session(path) == snap.session.day
    assert doc["expiry"] == snap.expiry.isoformat()
    assert doc["close"] == "162.83"
    assert doc["pick"] is None
    assert set(doc["straddle"]) == {"strike", "price"}  # LD-41
    assert doc["straddle"]["strike"] == "162.50"
    assert float(doc["straddle"]["price"]) > 0
    first = doc["points"][0]
    assert set(first) == {"strike", "right", "iv", "delta"}
    assert first["right"] == "put"
    assert math.isfinite(first["iv"])
