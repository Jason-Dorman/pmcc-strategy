"""SPXW, the S&P 500's PM-settled weeklies: RICs, a close-bar chain and a rough condor (T1-01).

The probe's cost sample for R5 (TD-07): one ~30-day, 0.20-delta iron condor priced from the
close's quotes, never a trade and never a backtest. Every threshold is `configs/thesis.yaml`'s
`cost_sample` (spec §6.2's contract rules, §6.3's spread test, §7.2's fees; TD-14):

- **The expiry:** the session from the minimum to the maximum days after the session after the
  close (28 to 35), nearest the target (30), a tie going earlier.
- **RICs:** `{ROOT}{M}{DD}{YY}{SSSSS}.U`, as the equity options' (`pmcc.data.ric`), except that a
  strike of 1,000 or more is written in tenths (6,600 → `66000`) and, as LSEG's OPRA convention has
  it, its month letter in lower case. That spelling isn't pinned by any earlier probe, so the
  probe asks the at-the-money pair in each candidate spelling (root `SPXW` or `SPX`, letter lower or
  upper) and reports which LSEG answers before asking the chain in it.
- **Quotes:** each contract's bid and ask in the session's close bar (the hourly bar ending at
  16:00 ET), as the live wheel's snapshot reads them (LD-21); or, where LSEG answers SPXW only
  daily, the session's daily bar (its last bid and ask of the day; TD-18).
- **Deltas:** Black-Scholes on the spot implied by the at-the-money pair's put-call parity, so the
  index's dividends need no input; IV from the mid; a flat rough rate. Rough: labelled so wherever
  it's shown.
- **The condor:** the out-of-the-money put and call nearest ∓ the target delta (within the
  tolerance); wings at the smallest common width from the spot fraction of the index to the
  multiple of that, both quoted; every leg passing the spread test (ask − bid ≤ max(points,
  fraction × mid)). Its natural credit (short bids less long asks), its mid credit, the four legs'
  summed spread (a round trip at the natural price, entering and leaving, gives up about one full
  spread a leg), and the fee per contract a transaction: eight transactions for an entry and an
  exit, in index points at the multiplier.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from statistics import NormalDist
from typing import final

import numpy as np
import polars as pl

from pmcc.data.fetch import BarRequest, Retry, fetch_rics
from pmcc.data.provider import HistoryProvider, Interval, RawHistory
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.sessions import Session
from pmcc.live.snapshot import close_bar_rows
from pmcc.pricing.black_scholes import greeks
from pmcc.pricing.expiry import years_to_expiry
from pmcc.pricing.iv import IvCode, implied_vol
from pmcc.thesis.config import CostSampleConfig

ROOTS = ("SPXW", "SPX")
QUOTE_FIELDS = ("BID", "ASK")
TRANSACTIONS = 8  # four contracts, opened and closed
_LETTERS = {Right.CALL: "ABCDEFGHIJKL", Right.PUT: "MNOPQRSTUVWX"}
_DAY = timedelta(days=1)

type Rules = CostSampleConfig


@final
@dataclass(frozen=True, slots=True)
class Spelling:
    root: str
    lowercase: bool

    @property
    def name(self) -> str:
        return f"{self.root}, {'lower' if self.lowercase else 'upper'}-case month"


SPELLINGS = tuple(Spelling(root, lower) for root in ROOTS for lower in (True, False))


@final
@dataclass(frozen=True, slots=True)
class Leg:
    """One contract asked. `listed` when LSEG answered its RIC; its bid and ask in the close bar
    (None when it had none there)."""

    ric: str
    right: Right
    strike: int
    bid: float | None
    ask: float | None
    listed: bool = True
    iv: float | None = None
    delta: float | None = None

    @property
    def quoted(self) -> bool:
        """A finite bid at or above zero and an ask above zero, not below it (§6.3)."""
        bid, ask = self.bid, self.ask
        return bid is not None and ask is not None and 0 <= bid <= ask and ask > 0

    @property
    def mid(self) -> float | None:
        bid, ask = self.bid, self.ask
        return (bid + ask) / 2 if self.quoted and bid is not None and ask is not None else None

    @property
    def spread(self) -> float | None:
        bid, ask = self.bid, self.ask
        return ask - bid if self.quoted and bid is not None and ask is not None else None

    def tight(self, rules: Rules) -> bool:
        """§6.3's spread test: ask − bid ≤ max(points, fraction × mid)."""
        spread, mid = self.spread, self.mid
        if spread is None or mid is None or mid <= 0:
            return False
        return spread <= max(
            rules.maximum_spread_points, rules.maximum_spread_fraction_of_mid * mid
        )


@final
@dataclass(frozen=True, slots=True)
class Condor:
    short_put: Leg
    long_put: Leg
    short_call: Leg
    long_call: Leg
    width: int
    fees: float  # index points: the fee × 8 transactions ÷ the multiplier

    @property
    def legs(self) -> tuple[Leg, Leg, Leg, Leg]:
        return (self.short_put, self.long_put, self.short_call, self.long_call)

    @property
    def natural_credit(self) -> float:
        shorts = _f(self.short_put.bid) + _f(self.short_call.bid)
        return shorts - _f(self.long_put.ask) - _f(self.long_call.ask)

    @property
    def mid_credit(self) -> float:
        shorts = _f(self.short_put.mid) + _f(self.short_call.mid)
        return shorts - _f(self.long_put.mid) - _f(self.long_call.mid)

    @property
    def round_trip_spread(self) -> float:
        return sum(_f(leg.spread) for leg in self.legs)


def option_ric(spelling: Spelling, expiry: date, right: Right, strike: int) -> str:
    """`strike`'s RIC in `spelling`. Strikes of 1,000 or more in tenths; below it, in cents."""
    letter = _LETTERS[right][expiry.month - 1]
    field = strike * 10 if strike >= 1000 else strike * 100
    if not 0 < field <= 99_999:
        raise ValueError(f"strike {strike} doesn't fit a five-digit RIC strike")
    letter = letter.lower() if spelling.lowercase and strike >= 1000 else letter
    return f"{spelling.root}{letter}{expiry:%d}{expiry.year % 100:02d}{field:05d}.U"


def pick_expiry(calendar: SessionCalendar, execution: date, rules: Rules) -> date | None:
    """The session from the minimum to the maximum days after `execution` nearest the target, a
    tie going earlier; None when the calendar has none (or doesn't reach that far)."""
    span = range(rules.minimum_dte_calendar_days, rules.maximum_dte_calendar_days + 1)
    days = [execution + _DAY * n for n in span]
    sessions = [d for d in days if d <= calendar.last_day and calendar.is_session(d)]
    if not sessions:
        return None
    target = rules.target_dte_calendar_days
    return min(sessions, key=lambda d: (abs((d - execution).days - target), d))


def estimated_strikes(spot: float, vix: float, years: float, rules: Rules) -> tuple[float, float]:
    """The target-delta put's and call's strikes if every strike's IV were VIX's."""
    z = NormalDist().inv_cdf(1 - rules.absolute_short_delta_target)
    sigma = vix / 100
    root = sigma * math.sqrt(years)
    half = sigma * sigma * years / 2
    return spot * math.exp(-(z * root - half)), spot * math.exp(z * root + half)


def ladder(low: float, high: float, rules: Rules) -> tuple[int, ...]:
    """Every strike step from `low` to `high`, rounded outwards."""
    step = rules.strike_step_points
    return tuple(range(math.floor(low / step) * step, math.ceil(high / step) * step + 1, step))


def atm_strike(spot: float, rules: Rules) -> int:
    step = rules.strike_step_points
    return round(spot / step) * step


def close_quotes(
    provider: HistoryProvider,
    rics: Sequence[str],
    session: Session,
    interval: Interval = Interval.HOURLY,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> tuple[frozenset[str], dict[str, tuple[float | None, float | None]]]:
    """Which RICs LSEG listed, and each listed one's bid and ask in `session`'s close bar
    (hourly) or its daily bar."""
    request = BarRequest(QUOTE_FIELDS, session.day, session.day + _DAY, interval)
    result = fetch_rics(provider, rics, request, retry=retry)
    closing = _session_rows(result.history, session, interval)
    quotes: dict[str, tuple[float | None, float | None]] = {}
    for ric in result.answered:
        rows = closing.filter(pl.col("ric") == ric).iter_rows(named=True)
        cells = {r["field"]: r["value"] for r in rows}
        quotes[ric] = (_cell(cells.get("BID")), _cell(cells.get("ASK")))
    return result.answered, quotes


def _session_rows(history: RawHistory, session: Session, interval: Interval) -> pl.DataFrame:
    if interval is Interval.DAILY:
        return history.rows.filter(pl.col("bar_start") == session.day)
    return close_bar_rows(history, session)


def parity_spot(call: Leg, put: Leg, years: float, rules: Rules) -> float | None:
    """S·e^(−qT) from a same-strike pair: F = K + e^(rT)(C − P), discounted at r."""
    if call.mid is None or put.mid is None or call.strike != put.strike:
        return None
    rate = rules.rate_decimal
    forward = call.strike + math.exp(rate * years) * (call.mid - put.mid)
    return forward * math.exp(-rate * years) if forward > 0 else None


def priced(legs: Sequence[Leg], spot: float, years: float, rules: Rules) -> tuple[Leg, ...]:
    """`legs` with IV from each mid and Black-Scholes delta; unpriced where the IV doesn't solve."""
    if not legs:
        return ()
    mids = np.array([leg.mid if leg.mid is not None else np.nan for leg in legs])
    strikes = np.array([float(leg.strike) for leg in legs])
    calls = np.array([leg.right is Right.CALL for leg in legs])
    solved = implied_vol(mids, spot, strikes, years, rules.rate_decimal, calls)
    ok = solved.code == IvCode.OK
    vols = np.where(ok, solved.vol, 0.2)
    deltas = greeks(spot, strikes, years, rules.rate_decimal, vols, calls).delta
    return tuple(
        replace(leg, iv=float(solved.vol[i]), delta=float(deltas[i])) if ok[i] else leg
        for i, leg in enumerate(legs)
    )


def condor(legs: Sequence[Leg], spot: float, rules: Rules) -> Condor | None:
    """Spec §6.2's condor from priced `legs` (rough, see the module), or None if any part is
    missing: a short leg within the delta tolerance, or a common wing width with both wings."""
    target = rules.absolute_short_delta_target
    usable = [leg for leg in legs if leg.delta is not None and leg.tight(rules)]
    short_put = _nearest(usable, Right.PUT, -target, rules, lambda k: k < spot)
    short_call = _nearest(usable, Right.CALL, target, rules, lambda k: k > spot)
    if short_put is None or short_call is None:
        return None
    wings = {(leg.right, leg.strike): leg for leg in legs if leg.tight(rules)}
    for width in _widths(spot, rules):
        long_put = wings.get((Right.PUT, short_put.strike - width))
        long_call = wings.get((Right.CALL, short_call.strike + width))
        if long_put is not None and long_call is not None:
            fees = rules.fee_per_contract_transaction_usd * TRANSACTIONS / rules.contract_multiplier
            return Condor(short_put, long_put, short_call, long_call, width, fees)
    return None


def _widths(spot: float, rules: Rules) -> range:
    """The step widths from the spot fraction of the index to its multiple, smallest first."""
    step = rules.strike_step_points
    target = rules.target_wing_width_spot_fraction * spot
    widest = rules.maximum_wing_width_target_multiple * target
    return range(math.ceil(target / step) * step, math.floor(widest) + 1, step)


def _nearest(
    legs: Sequence[Leg], right: Right, target: float, rules: Rules, otm: Callable[[int], bool]
) -> Leg | None:
    found = [
        leg
        for leg in legs
        if leg.right is right
        and leg.delta is not None
        and otm(leg.strike)
        and abs(leg.delta - target) <= rules.delta_tolerance
    ]
    return min(
        found, key=lambda leg: (abs(_f(leg.delta) - target), _f(leg.spread), leg.ric), default=None
    )


def _cell(value: object) -> float | None:
    return float(value) if isinstance(value, float) and math.isfinite(value) else None


def _f(value: float | None) -> float:
    return 0.0 if value is None else value


def years_from_close(session: Session, calendar: SessionCalendar, expiry: date) -> float:
    return years_to_expiry(session.close_bar_end, calendar.session(expiry))
