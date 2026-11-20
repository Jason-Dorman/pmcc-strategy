"""NVDA's volatility for the live page (L4-02; PO, LD-33): its ATM implied vol about 30 days out
against its 20-day realized vol, one point a session, and the coming week's smile.

- **The tenor:** the weekly expiry nearest 30 calendar days after the session, a tie going to the
  later one. RV20 covers about a month of returns, so like is compared with like, and the line
  doesn't jump as an expiry nears.
- **ATM IV:** at the strike nearest the close (a tie going lower) among those whose call and put
  both have a valid bid and ask in the close bar, the mean of the two IVs. Each IV is the live
  picks' (LD-11): Black-Scholes from the mid, dividend yield 0, r of LD-13, T from the close to
  the expiry session's close, ACT/365. None where either doesn't solve.
- **RV20:** the sample standard deviation of the 20 daily log returns ending at the session's own
  close, × √252: that close and the 20 before it, each the last trade in its close bar, as the
  snapshot reads a close (LD-21).
- **The smile:** for the coming week's expiry (L-P2's, the one the wheel sells), the
  out-of-the-money side of the close snapshot: puts struck below the close and calls above, each
  with its IV and delta where they solve; and the put L-P3 would pick.

The files (LD-34): `live/vol.jsonl`, one point a session, only ever appended to; `live/smile.json`,
the last session's smile, replaced when a later session's is taken. Both hold numbers derived
from LSEG's quotes, never the quotes. `pmcc.live.vol_fetch` asks LSEG; these are pure.
"""

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import final

from pmcc.data.files import replace_file
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import UNITS_PER_CENT, Price
from pmcc.domain.quotes import Quote as BidAsk
from pmcc.domain.sessions import Session
from pmcc.live.names import RIGHT_NAMES, dollars, quote_dollars
from pmcc.live.rules import Pick, price_at_close
from pmcc.live.snapshot import CloseSnapshot, OptionQuote
from pmcc.pricing.expiry import years_between
from pmcc.pricing.measures import realized_vol

VOL_LOG = Path("live") / "vol.jsonl"
SMILE = Path("live") / "smile.json"

TENOR_DAYS = 30
RV_RETURNS = 20
ATM_REACH_CENTS = 750  # strikes asked either side of the close for the ATM pair
ATM_STEP_CENTS = 250  # NVDA lists $2.50 steps near the money, $5 below $150; both fall on $2.50
CATCH_UP = 10  # sessions a run fills without --since: a missed fortnight, not a backfill
DIGITS = 6  # places kept for a vol in the files

type Json = dict[str, object]
_DAY = timedelta(days=1)
_WEEK = timedelta(days=7)


class VolError(Exception):
    """The run can't make its points: nothing is written."""


@final
@dataclass(frozen=True, slots=True)
class VolPoint:
    """One session: its close, the tenor's expiry, the ATM strike and IVs, and RV20."""

    session: date
    close: Price
    expiry: date
    strike: Price | None  # None when no strike had both sides quoted
    call_iv: float | None
    put_iv: float | None
    rv20: float | None

    @property
    def atm_iv(self) -> float | None:
        if self.call_iv is None or self.put_iv is None:
            return None
        return (self.call_iv + self.put_iv) / 2

    def row(self) -> Json:
        return {
            "session": self.session.isoformat(),
            "close": dollars(self.close),
            "expiry": self.expiry.isoformat(),
            "strike": None if self.strike is None else dollars(self.strike),
            "call_iv": _rounded(self.call_iv),
            "put_iv": _rounded(self.put_iv),
            "atm_iv": _rounded(self.atm_iv),
            "rv20": _rounded(self.rv20),
        }


@final
@dataclass(frozen=True, slots=True)
class SmilePoint:
    strike: Price
    right: Right
    iv: float
    delta: float


@final
@dataclass(frozen=True, slots=True)
class Straddle:
    """The expiry's at-the-money straddle at the close (PO, LD-41): the strike nearest the close
    with both sides quoted (a tie goes lower), and its call's and put's mids summed, the market's
    expected move to expiry. A price derived from two quotes, not a quote."""

    strike: Price
    price: Price

    def doc(self) -> Json:
        return {"strike": dollars(self.strike), "price": quote_dollars(self.price)}


@final
@dataclass(frozen=True, slots=True)
class Smile:
    """The coming week's out-of-the-money IVs at a session's close, L-P3's pick, and the
    expiry's ATM straddle (LD-41)."""

    session: date
    expiry: date
    close: Price
    points: tuple[SmilePoint, ...]
    pick: Price | None
    straddle: Straddle | None = None

    def doc(self) -> Json:
        return {
            "session": self.session.isoformat(),
            "expiry": self.expiry.isoformat(),
            "close": dollars(self.close),
            "pick": None if self.pick is None else dollars(self.pick),
            "straddle": None if self.straddle is None else self.straddle.doc(),
            "points": [
                {
                    "strike": dollars(p.strike),
                    "right": RIGHT_NAMES[p.right],
                    "iv": round(p.iv, DIGITS),
                    "delta": round(p.delta, DIGITS),
                }
                for p in self.points
            ],
        }


def tenor_expiry(calendar: SessionCalendar, day: date) -> date:
    """The weekly expiry nearest `TENOR_DAYS` after `day`; a tie goes to the later one."""
    target = day + timedelta(days=TENOR_DAYS)
    expiries = calendar.weekly_expiries(target - _WEEK, target + _WEEK)
    return min(expiries, key=lambda e: (abs((e - target).days), -e.toordinal()))


def atm_ladder(close: Price) -> tuple[Price, ...]:
    """Every $2.50 strike within $7.50 of the close: the nearest listed strike is among them
    whether strikes are $2.50 or $5 apart."""
    cents = close.units // UNITS_PER_CENT
    low = -(-(cents - ATM_REACH_CENTS) // ATM_STEP_CENTS) * ATM_STEP_CENTS
    high = (cents + ATM_REACH_CENTS) // ATM_STEP_CENTS * ATM_STEP_CENTS
    return tuple(Price(c * UNITS_PER_CENT) for c in range(low, high + 1, ATM_STEP_CENTS))


def atm_point(
    session: Session,
    close: Price,
    expiry: Session,
    quotes: Sequence[OptionQuote],
    rate: float,
    rv20: float | None,
) -> VolPoint:
    """The session's point from the tenor's quotes at its close."""
    quoted = _quoted(quotes)
    strike = _atm_strike(quoted, close)
    if strike is None:
        return VolPoint(session.day, close, expiry.day, None, None, None, rv20)
    years = years_between(session.close_bar_end, expiry.close_bar_end)
    call = _iv(quoted[(Right.CALL, strike)], close, years, rate)
    put = _iv(quoted[(Right.PUT, strike)], close, years, rate)
    return VolPoint(session.day, close, expiry.day, Price(strike), call, put, rv20)


type _Quoted = dict[tuple[Right, int], OptionQuote]


def _quoted(quotes: Sequence[OptionQuote]) -> _Quoted:
    """The contracts with a valid quote in the close bar, by right and strike."""
    return {(q.option.right, q.option.strike.units): q for q in quotes if q.quoted_at_close}


def _atm_strike(quoted: _Quoted, close: Price) -> int | None:
    """The strike nearest the close with both its call and put quoted; a tie goes lower."""
    paired = [k for right, k in quoted if right is Right.CALL and (Right.PUT, k) in quoted]
    return min(paired, key=lambda k: (abs(k - close.units), k)) if paired else None


def _mid(quote: OptionQuote) -> Price:
    bar = quote.close
    if bar is None or bar.bid is None or bar.ask is None:
        raise VolError(f"{quote.ric} has no quote at the close")
    return BidAsk(bar.bid, bar.ask).mid


def straddle(snapshot: CloseSnapshot) -> Straddle | None:
    """The snapshot's ATM straddle (PO, LD-41); None when no strike has both sides quoted."""
    quoted = _quoted(snapshot.options)
    strike = _atm_strike(quoted, snapshot.close)
    if strike is None:
        return None
    call, put = _mid(quoted[(Right.CALL, strike)]), _mid(quoted[(Right.PUT, strike)])
    return Straddle(Price(strike), Price(call.units + put.units))


def _iv(quote: OptionQuote, close: Price, years: float, rate: float) -> float | None:
    iv = float(price_at_close([quote], close, years, rate, quote.option.right).iv[0])
    return iv if math.isfinite(iv) else None


def rv20_through(
    calendar: SessionCalendar, day: date, closes: Mapping[date, Price]
) -> float | None:
    """RV20 at `day`'s close: its close and the 20 before it; None if any is missing."""
    days = [s.day for s in calendar.sessions_before(day, RV_RETURNS)] + [day]
    found = [closes[d] for d in days if d in closes]
    return realized_vol(found) if len(found) == len(days) else None


def smile(
    snapshot: CloseSnapshot, rate: float, calendar: SessionCalendar, pick: Pick | None
) -> Smile:
    """The snapshot's out-of-the-money side, by strike, where IV and delta solve."""
    years = years_between(
        snapshot.session.close_bar_end, calendar.session(snapshot.expiry).close_bar_end
    )
    points = [
        point for right in (Right.PUT, Right.CALL) for point in _side(snapshot, right, years, rate)
    ]
    return Smile(
        snapshot.session.day,
        snapshot.expiry,
        snapshot.close,
        tuple(sorted(points, key=lambda p: p.strike)),
        None if pick is None else pick.option.strike,
        straddle(snapshot),
    )


def _side(snapshot: CloseSnapshot, right: Right, years: float, rate: float) -> list[SmilePoint]:
    close = snapshot.close.units
    otm = [
        q
        for q in snapshot.options
        if q.option.right is right
        and q.quoted_at_close
        and (q.option.strike.units < close if right is Right.PUT else q.option.strike.units > close)
    ]
    if not otm:
        return []
    priced = price_at_close(otm, snapshot.close, years, rate, right)
    return [
        SmilePoint(q.option.strike, right, float(priced.iv[i]), float(priced.delta[i]))
        for i, q in enumerate(otm)
        if math.isfinite(priced.iv[i]) and math.isfinite(priced.delta[i])
    ]


def sessions_to_fill(
    calendar: SessionCalendar, last: Session, done: frozenset[date], since: date | None
) -> tuple[Session, ...]:
    """The sessions a run makes points for, up to `last`, the last completed one: from `since`
    when given (a backfill); else those after the last point, or `last` alone on a first run.
    Raises `VolError` past `CATCH_UP` sessions without `since`, so a long pull is always asked
    for by hand, after its plan (CLAUDE.md › LSEG access)."""
    if since is not None:
        start = since
    elif not done:
        start = last.day
    else:
        start = max(done) + _DAY
    wanted = calendar.sessions(start, last.day) if start <= last.day else ()
    missing = tuple(s for s in wanted if s.day not in done)
    if since is None and len(missing) > CATCH_UP:
        raise VolError(
            f"{len(missing)} sessions since the last point ({max(done)}): more than {CATCH_UP}; "
            "backfill them with --since, after --plan-only"
        )
    return missing


def read_points(path: Path) -> tuple[Json, ...]:
    """The points in `path`, in file order; none when it doesn't exist yet."""
    if not path.exists():
        return ()
    lines = path.read_text(encoding="utf-8").splitlines()
    return tuple(json.loads(line) for line in lines if line.strip())


def append_points(path: Path, points: Sequence[VolPoint]) -> None:
    """One line a point, after what's there, which is never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    before = path.read_bytes() if path.exists() else b""
    lines = "".join(json.dumps(p.row(), ensure_ascii=False) + "\n" for p in points)
    replace_file(path, before + lines.encode("utf-8"))


def read_smile_session(path: Path) -> date | None:
    """The session `path`'s smile is from; None when there's none yet."""
    if not path.exists():
        return None
    session = json.loads(path.read_text(encoding="utf-8"))["session"]
    return date.fromisoformat(str(session))


def write_smile(path: Path, curve: Smile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(curve.doc(), indent=2, ensure_ascii=False) + "\n"
    replace_file(path, text.encode("utf-8"))


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, DIGITS)
