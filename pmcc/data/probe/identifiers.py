"""DEC-12: the stock RIC and its exchange suffix, the daily tape, splits and the max strike.

LDG verified only `QQQ.O` and `UUUU.K`, so every usual suffix is asked and every one that answers
is recorded. The probe works on with the first that answers, in `SUFFIXES` order; that isn't
always the primary listing (Arca ETFs answer `.N` first), and the PO picks each symbol's RIC at
P1-05. The daily tape also checks the holiday table against LSEG's trading days (DEC-33).

The largest daily moves can only show a split LSEG hasn't adjusted for. Its history is
split-adjusted: XLE's 2-for-1 split on Dec 5 2025 left no jump (DEC-12), so splits are checked
against corporate actions, not here.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import final

import polars as pl

from pmcc.data.calendar import check_trading_days, describe
from pmcc.data.discovery import EM_WEEK_YEARS, WEEKLY_EM_MULTIPLE, SessionRange, band_vol
from pmcc.data.fetch import BarRequest, fetch_rics
from pmcc.data.probe.context import Json, Probe, ask, dollars, over, price
from pmcc.data.provider import Interval, RawHistory
from pmcc.data.ric import MAX_STRIKE

SUFFIXES = (".O", ".N", ".P", ".A", ".K", ".Z")  # Nasdaq, NYSE, Arca, American, then others
DAILY_FIELDS = ("TRDPRC_1", "HIGH_1", "LOW_1")
SPLIT_LIKE = math.log(1.4)  # a day's close-to-close move beyond ±40% looks like a split
LARGEST_MOVES = 3
YEAR_SESSIONS = 252


class ProbeStoppedError(Exception):
    """The probe can't go on for this symbol. The CLI reports it and writes nothing."""


def stock_candidates(symbol: str) -> tuple[str, ...]:
    return tuple(f"{symbol}{suffix}" for suffix in SUFFIXES)


def resolve_stock(probe: Probe) -> tuple[Json, str]:
    """Ask each candidate alone for its last 10 daily closes; the record and the RIC to go on with.

    Alone and once, so each wrong suffix's answer is the service's own daily answer for a
    never-listed RIC (DEC-83), and an unexpected code is recorded instead of ending the probe.
    """
    candidates = stock_candidates(probe.symbol)
    request = over(probe.recent(10), ("TRDPRC_1",), Interval.DAILY)
    asked = {ric: ask(probe, [ric], request) for ric in candidates}
    closes = {ric: _last(a.history) for ric, a in asked.items() if a.outcome == "answered"}
    answered = [ric for ric, close in closes.items() if close is not None]
    if not answered:
        raise ProbeStoppedError(f"no stock RIC answered for {probe.symbol}: asked {candidates}")
    return {
        "candidates": {ric: a.record for ric, a in asked.items()},
        "answered": answered,
        "last_close": {ric: closes[ric] for ric in answered},
        "chosen": answered[0],
    }, answered[0]


def _last(history: RawHistory | None) -> float | None:
    if history is None or history.rows.is_empty():
        return None
    return float(history.rows.sort("bar_start")["value"][-1])


@final
@dataclass(frozen=True, slots=True)
class DailyTape:
    """The stock's daily bars from the calendar's first day to the last session, one row a day."""

    frame: pl.DataFrame  # day, TRDPRC_1, HIGH_1, LOW_1

    def close_on_or_before(self, day: date) -> float | None:
        rows = self.frame.filter(pl.col("day") <= day).drop_nulls("TRDPRC_1")
        return None if rows.is_empty() else float(rows["TRDPRC_1"][-1])

    def ranges(self) -> list[SessionRange]:
        """Each day as a `SessionRange`, for the plan's volatility."""
        rows = self.frame.drop_nulls(["TRDPRC_1", "HIGH_1", "LOW_1"])
        return [
            SessionRange(r["day"], price(r["LOW_1"]), price(r["HIGH_1"]), price(r["TRDPRC_1"]))
            for r in rows.iter_rows(named=True)
        ]


def daily_tape(probe: Probe, stock_ric: str) -> DailyTape:
    last = probe.last_session.day
    request = BarRequest(
        DAILY_FIELDS, probe.calendar.first_day, last + timedelta(days=1), Interval.DAILY
    )
    rows = fetch_rics(probe.provider, [stock_ric], request, retry=probe.retry).series(stock_ric)
    frame = (
        rows.pivot(on="field", index="bar_start", values="value")
        .rename({"bar_start": "day"})
        .sort("day")
    )
    for column in DAILY_FIELDS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None, pl.Float64()).alias(column))
    return DailyTape(frame.select("day", *DAILY_FIELDS))


def tape_checks(probe: Probe, tape: DailyTape) -> Json:
    """Splits, the max strike needed, and the table against LSEG's trading days."""
    return {
        "daily_bars": tape.frame.height,
        "first_day": _iso(tape.frame["day"].min()),
        "largest_moves": _largest_moves(tape),
        "max_strike": _max_strike(tape),
        "calendar_check": _calendar_check(probe, tape),
    }


def _largest_moves(tape: DailyTape) -> list[Json]:
    moves = (
        tape.frame.drop_nulls("TRDPRC_1")
        .with_columns(move=pl.col("TRDPRC_1").log().diff())
        .drop_nulls("move")
        .sort(pl.col("move").abs(), descending=True)
        .head(LARGEST_MOVES)
    )
    return [
        {
            "day": r["day"].isoformat(),
            "close_ratio": round(math.exp(r["move"]), 4),
            "split_like": abs(r["move"]) > SPLIT_LIKE,
        }
        for r in moves.iter_rows(named=True)
    ]


def _max_strike(tape: DailyTape) -> Json:
    """The weekly call band's top over the last year: high + 2.5 EMest (DEC-48), vs $999.99."""
    ranges = tape.ranges()[-(YEAR_SESSIONS + 1) :]
    if len(ranges) <= 21:
        return {"note": "too few daily bars to estimate"}
    high = max(dollars(r.high) for r in ranges)
    sigma = band_vol(ranges, ranges[0].day, ranges[-1].day)  # every RV20 in the year
    top = high * (1 + WEEKLY_EM_MULTIPLE * sigma * math.sqrt(EM_WEEK_YEARS))
    return {
        "year_high": high,
        "band_vol": round(sigma, 4),
        "band_top_estimate": round(top, 2),
        "fits_ric_strike_field": top <= dollars(MAX_STRIKE),
    }


def _calendar_check(probe: Probe, tape: DailyTape) -> Json:
    days = set(tape.frame["day"].to_list())
    start = max(probe.calendar.first_day, min(days, default=probe.calendar.first_day))
    mismatch = check_trading_days(probe.calendar, days, start, probe.last_session.day)
    return {
        "from": start.isoformat(),
        "to": probe.last_session.day.isoformat(),
        "ok": mismatch.ok,
        "traded_but_closed": [d.isoformat() for d in mismatch.traded_but_closed],
        "session_without_bars": [d.isoformat() for d in mismatch.session_without_bars],
        "detail": None if mismatch.ok else describe(probe.calendar, mismatch),
    }


def _iso(value: object) -> str | None:
    return value.isoformat() if isinstance(value, date) else None
