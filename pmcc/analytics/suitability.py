"""The symbol suitability screen (Spec › Symbol suitability screen; P6-08; PO, DEC-66).

Five measures per symbol from point-in-time data, read once a week at the first bar of each
week-open session in the window, through the `MarketView` on that bar (so nothing later is
readable), from what quant's rules see there:

- **the long** is quant's E-L2/E-L3 pick (lowest extrinsic ÷ delta); its extrinsic ÷ (delta ×
  spot) and its spread are read;
- **the short** is quant's E-S2/E-S3 pick against that long (lowest strike at or above spot +
  k × EM); its spread is read, and its credit after half-spread (mid − half-spread, its bid) ÷
  the long's mid. A week without a long has no short: a short is sold against a long (E-S1);
- **IV ÷ RV20** is the front week's ATM IV ÷ RV20, G-4's inputs, whatever the picks;
- **G-3** is quant's gate on the front week, whatever the picks: fire, pass or `n/a`.

The picks needn't pass E-T1: the screen measures the contracts quant would trade, not whether a
bar's spread lets it. Each measure is over the weeks it could be read, and its count is published.
A spread is (ASK − BID) ÷ mid, exact as E-T1's test is; spreads and credits are fractions of
the integer BID and ASK, so the medians and means don't
depend on order (INV-13); extrinsic ÷ delta and IV ÷ RV20 are floats, averaged with `fmean`.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction
from typing import Self, final

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.quotes import Quote
from pmcc.export.analytics_models import Suitability, SuitabilityRow
from pmcc.strategy.gates import EventRatioGate
from pmcc.strategy.measures import atm_reading, rv20_at
from pmcc.strategy.ports import GateStatus, HeldLeg, MarketView
from pmcc.strategy.registry import Strategy
from pmcc.strategy.selectors import LongSelector, ShortSelector
from pmcc.strategy.trigger import spread_share


@final
@dataclass(frozen=True, slots=True)
class Screen:
    """The rules the screen reads with: quant's long and short selectors and its G-3."""

    long: LongSelector
    short: ShortSelector
    event: EventRatioGate

    @classmethod
    def of(cls, strategy: Strategy) -> Self:
        """`strategy`'s rules. Raises `ValueError` if it has no G-3 (only quant's has, with its
        variants that keep it)."""
        gates = [g for g in strategy.gates if isinstance(g, EventRatioGate)]
        if not gates:
            raise ValueError(f"the suitability screen reads G-3, which {strategy.config.id} lacks")
        return cls(strategy.long_selector, strategy.short_selector, gates[0])


@final
@dataclass(frozen=True, slots=True)
class WeekReading:
    """One week's measures; None where the week couldn't give one."""

    session: date  # the week-open session
    long_extrinsic_per_delta: float | None  # a fraction of spot
    long_spread: Fraction | None  # (ASK − BID) ÷ mid
    short_spread: Fraction | None
    credit: Fraction | None  # the short's bid ÷ the long's mid
    iv_over_rv20: float | None
    g3: GateStatus


def sample_bars(calendar: SessionCalendar, start: date, end: date) -> tuple[datetime, ...]:
    """The first bar's end of each week-open session from `start` to `end`."""
    return tuple(s.bar_ends()[0] for s in calendar.sessions(start, end)
                 if calendar.week_open(s.day).day == s.day)  # fmt: skip


def read_week(view: MarketView, screen: Screen) -> WeekReading:
    """The week's measures as of `view.now`."""
    front = screen.short.expiry.expiry(view)
    long = _long(view, screen)
    short = None if long is None else _short(view, screen, long)
    return WeekReading(
        session=view.now.date(),
        long_extrinsic_per_delta=None if long is None else long.per_delta,
        long_spread=None if long is None else spread_share(long.quote),
        short_spread=None if short is None else spread_share(short),
        credit=None if long is None or short is None else _credit(short, long.quote),
        iv_over_rv20=_iv_over_rv20(view, front),
        g3=screen.event.check(view, front).status,
    )


def suitability_row(symbol: str, readings: Sequence[WeekReading], screen: Screen) -> SuitabilityRow:
    """`symbol`'s row: each measure over the weeks that gave it."""
    per_delta = [
        r.long_extrinsic_per_delta for r in readings if r.long_extrinsic_per_delta is not None
    ]
    longs = [r.long_spread for r in readings if r.long_spread is not None]
    shorts = [r.short_spread for r in readings if r.short_spread is not None]
    credits = [r.credit for r in readings if r.credit is not None]
    ratios = [r.iv_over_rv20 for r in readings if r.iv_over_rv20 is not None]
    evaluated = [r.g3 for r in readings if r.g3 is not GateStatus.NA]
    return SuitabilityRow(
        symbol=symbol,
        weeks=len(readings),
        long_weeks=len(longs),
        long_extrinsic_per_delta_pct_spot=statistics.fmean(per_delta) if per_delta else None,
        median_spread_long_pct=_median(longs),
        short_weeks=len(shorts),
        median_spread_short_pct=_median(shorts),
        weekly_credit_after_half_spread_pct_long_cost=_mean(credits),
        iv_rv20_weeks=len(ratios),
        iv_over_rv20=statistics.fmean(ratios) if ratios else None,
        g3_weeks=len(evaluated),
        g3_fires=sum(s is GateStatus.FIRE for s in evaluated),
        g3_max_ratio=screen.event.max_ratio,
    )


def suitability(rows: Sequence[SuitabilityRow]) -> Suitability:
    """`universe/suitability.json`, symbols in alphabetical order. Raises `ValueError` if a
    symbol has two rows."""
    symbols = [r.symbol for r in rows]
    twice = sorted({s for s in symbols if symbols.count(s) > 1})
    if twice:
        raise ValueError(f"the suitability screen has two rows for {', '.join(twice)}")
    return Suitability(rows=tuple(sorted(rows, key=lambda r: r.symbol)))


@final
@dataclass(frozen=True, slots=True)
class _Long:
    option: OptionId
    quote: Quote
    per_delta: float  # extrinsic ÷ (delta × spot)


def _long(view: MarketView, screen: Screen) -> _Long | None:
    """Quant's long on the bar; None without a pick."""
    spot = view.spot()
    selection = screen.long.select(view)
    if spot is None or selection is None:
        return None
    option = selection.option
    chain = view.chain(option.expiry, Right.CALL)
    row = chain.row(option.strike)
    quote = None if row is None else chain.quotes.quote(row)
    if row is None or quote is None:
        raise EngineError(f"E-L3 picked {option}, which has no quote at {view.now}")
    extrinsic = quote.mid.units - max(0, spot.units - option.strike.units)  # as E-L3 reads it
    return _Long(option, quote, extrinsic / (float(chain.quotes.delta[row]) * spot.units))


def _short(view: MarketView, screen: Screen, long: _Long) -> Quote | None:
    """Quant's short against the long, as its quote; None without a pick."""
    selection = screen.short.select(view, HeldLeg(long.option, 1, long.quote.mid, view.now))
    if selection is None:
        return None
    quote = view.quote(selection.option)
    if quote is None:
        raise EngineError(f"E-S3 picked {selection.option}, which has no quote at {view.now}")
    return quote


def _iv_over_rv20(view: MarketView, front: date) -> float | None:
    iv, rv = atm_reading(view, front).iv, rv20_at(view)
    return None if iv is None or rv is None or rv == 0 else iv / rv


def _credit(short: Quote, long: Quote) -> Fraction:
    """mid − half-spread is the bid; the long at its mid, as the fill model buys it."""
    return Fraction(short.bid.units, long.mid.units)


def _median(values: Sequence[Fraction]) -> float | None:
    return float(statistics.median(values)) if values else None


def _mean(values: Sequence[Fraction]) -> float | None:
    return float(sum(values, Fraction(0)) / len(values)) if values else None
