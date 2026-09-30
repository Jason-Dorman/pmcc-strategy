"""Scenario builders: synthetic markets scripted to force one behaviour each (TEST-STRATEGY §5).

Each builder returns a `SyntheticSpec`. Unless it says otherwise, a scenario runs over two weeks:

- **Week 1:** Mon Aug 31 to Fri Sep 4 2026. The long is bought on Monday's first bar and the week's
  short on the same bar; the short expires Friday.
- **Week 2:** Tue Sep 8 (Labor Day closes Monday) to Fri Sep 11.

Spot sits at $100 unless the scenario moves it. Weeklies trade at 40% IV with a 4% spread and
monthlies at 20% with a 1% spread, so every E-T1 test passes on the first bar, and the baseline's
short (0.30 delta, $102) clears E-S5 against its long (0.80 delta, $90): at one IV for both, a
0.80-delta 180-DTE long carries more extrinsic than a 0.30-delta weekly's distance and premium, and
G-2 would skip every week.

A builder that moves spot relative to the week's short takes the short's strike, learned from
`quiet()` over the same Monday: nothing differs before the move, so the engine picks the same
short.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, time

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId
from tests.fixtures.synthetic.market import (
    Cell,
    IvSurface,
    QuoteHook,
    SpotPath,
    SyntheticSpec,
    knot,
)

MON = date(2026, 8, 31)
TUE = date(2026, 9, 1)
WED = date(2026, 9, 2)
THU = date(2026, 9, 3)
FRI = date(2026, 9, 4)
WEEK2_OPEN = date(2026, 9, 8)  # Tuesday: Labor Day closes Monday
WEEK2_END = date(2026, 9, 11)
WEEK1_EXPIRY = FRI
SPOT = 100.0


_BASE = SyntheticSpec(MON, WEEK2_END, spot=SPOT, iv=IvSurface(weekly=0.40, monthly=0.20))
LONG_DATED_DAYS = 45  # an expiry further out than this is a monthly (the long leg's)


def _spec(**changes: object) -> SyntheticSpec:
    return replace(_BASE, **changes)


def _flat(*knots: tuple[datetime, float]) -> SpotPath:
    """Flat at $100 through Monday's first bar (and the warm-up before it), then `knots`."""
    return SpotPath((knot(MON, 10, SPOT), *knots))


def _long_dated(option: OptionId, t: datetime) -> bool:
    return (option.expiry - t.date()).days > LONG_DATED_DAYS


def _at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


def random_walk(seed: int = 7) -> SyntheticSpec:
    """A seeded random walk with holes and trade prints: the general market."""
    return _spec(seed=seed, hole_rate=0.05, window_end=date(2026, 9, 25))


def quiet() -> SyntheticSpec:
    """Flat at $100: the short expires out of the money (X-S4)."""
    return _spec(path=_flat())


def premium_collapse() -> SyntheticSpec:
    """Spot falls to $94 by Tuesday's close and stays: the short loses most of its value (X-S1)."""
    return _spec(path=_flat(knot(MON, 16, SPOT), knot(TUE, 16, 94.0)))


def rally_through_strike() -> SyntheticSpec:
    """Spot rallies to $108 by Wednesday noon: the short's delta passes 0.60 (X-S2)."""
    return _spec(path=_flat(knot(MON, 16, SPOT), knot(WED, 12, 108.0)))


def friday_within_buffer(
    short_strike: float,
    buffer: float,
    *,
    unquoted_at_check: bool = False,
    close: float | None = None,
) -> SyntheticSpec:
    """Flat until Thursday's close, then at the Friday check spot sits `buffer` below the short's
    strike (X-S3 when `buffer` < 0.25 × EM), and closes at `close` (default: where it is). With
    `unquoted_at_check`, week 1's weeklies have no quote on the check bar, so X-S3's close waits
    for the next bar with one (DEC-28): the close bar has a bid only if the short finishes in the
    money there."""
    near = short_strike - buffer
    path = _flat(knot(THU, 16, SPOT), knot(FRI, 15, near), knot(FRI, 16, close or near))

    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell] | None:
        if option.expiry == WEEK1_EXPIRY and t == _at(FRI, 15):
            return None, None
        return bid, ask

    return _spec(path=path, quote_hook=hook if unquoted_at_check else None)


def late_friday_surge(
    short_strike: float, jump: float = 2.0, *, no_stock_quote_at_close: bool = False
) -> SyntheticSpec:
    """Flat through the Friday check, then the close bar jumps `jump` above the short's strike: the
    short finishes in the money (X-S5), and its stock is covered on Tuesday Sep 8. With
    `no_stock_quote_at_close`, the stock trades on that bar but has no BID/ASK, so the short
    stock's first mark is the closing spot, flagged stale (DEC-91)."""
    above = short_strike + jump
    path = _flat(knot(FRI, 15, SPOT), knot(FRI, 16, above), knot(WEEK2_END, 16, above))

    def stock(t: datetime, spot: float) -> tuple[Cell, Cell, Cell]:
        if t == _at(FRI, 16):
            return None, None, spot
        return round(spot - 0.01, 2), round(spot + 0.01, 2), spot

    return _spec(path=path, stock_hook=stock if no_stock_quote_at_close else None)


def long_delta_drop(*, wide_on_reopen: bool = False) -> SyntheticSpec:
    """Spot falls to $70 over week 1: at week 2's open the long's delta is under 0.50 (X-L1).
    With `wide_on_reopen`, the monthlies quote 40% wide all that session, so the reset sells but
    the re-entry never passes E-T1 (DEC-22's unfinished-reset row)."""
    path = _flat(knot(MON, 16, SPOT), knot(FRI, 16, 70.0), knot(WEEK2_END, 16, 70.0))
    return _spec(
        path=path, quote_hook=_wide_on(WEEK2_OPEN, monthly=True) if wide_on_reopen else None
    )


def long_falls_after_check() -> SyntheticSpec:
    """Flat through week 2's first bar, where the long passes its check, then spot falls to $70
    by 14:00. The long is checked once a week (DEC-28), so it isn't sold that session."""
    return _spec(path=_flat(knot(WEEK2_OPEN, 10, SPOT), knot(WEEK2_OPEN, 14, 70.0)))


def _wide_on(day: date, *, expiry: date | None = None, monthly: bool = False) -> QuoteHook:
    """Spreads of 40% of mid on `day`: selectable (the IV solves) but never passing E-T1."""

    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell] | None:
        hit = t.date() == day and (expiry is None or option.expiry == expiry)
        if hit and (not monthly or _long_dated(option, t)) and bid and ask:
            mid = (bid + ask) / 2
            return round(mid * 0.8, 2), round(mid * 1.2, 2)
        return bid, ask

    return hook


def no_quote_monday() -> SyntheticSpec:
    """Week 1's weeklies quote 40% wide all Monday: the frozen short never passes E-T1 (G-1)."""
    return _spec(path=_flat(), quote_hook=_wide_on(MON, expiry=WEEK1_EXPIRY))


def expensive_long() -> SyntheticSpec:
    """Monthlies at 80% IV: the long's extrinsic makes its debit beat the strike gap (G-2)."""
    return _spec(path=_flat(), iv=IvSurface(weekly=0.40, monthly=0.80))


def entry_retry() -> SyntheticSpec:
    """Monthlies quote 40% wide all Monday, so the long enters Tuesday (E-L1, E-T1 retry); the
    first short then waits for week 2."""
    return _spec(path=_flat(), quote_hook=_wide_on(MON, monthly=True))


def first_bar_wide(*, rally_to: float | None = None, monthly: bool = False) -> SyntheticSpec:
    """Week 1's weeklies (or with `monthly`, the monthlies) quote wide on Monday's first bar
    only: the leg enters on a later bar (E-T1). With `rally_to`, spot moves there by 11:00, so a
    fresh selection would pick another strike: the frozen one must still be the one traded
    (DEC-21)."""

    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell] | None:
        leg = _long_dated(option, t) if monthly else option.expiry == WEEK1_EXPIRY
        if leg and t == _at(MON, 10) and bid and ask:
            mid = (bid + ask) / 2
            return round(mid * 0.8, 2), round(mid * 1.2, 2)
        return bid, ask

    path = _flat() if rally_to is None else _flat(knot(MON, 11, rally_to))
    return _spec(path=path, quote_hook=hook)


def stale_long_marks() -> SyntheticSpec:
    """The monthlies have no quote on Wednesday: the long is marked stale that day."""

    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell] | None:
        if t.date() == WED and _long_dated(option, t):
            return None, None
        return bid, ask

    return _spec(path=_flat(), quote_hook=hook)


def half_day_week() -> SyntheticSpec:
    """Thanksgiving week 2026: Thursday closed, Friday Nov 27 a half-day and the weekly expiry, so
    its Friday check is the 13:00 close bar."""
    return replace(_BASE, window_start=date(2026, 11, 23), window_end=date(2026, 12, 4))


def independence_day_week() -> SyntheticSpec:
    """Jun 29 to Jul 10 2026: Friday Jul 3 is closed, so week 1's short expires Thursday Jul 2."""
    return replace(_BASE, window_start=date(2026, 6, 29), window_end=date(2026, 7, 10))


def long_unquoted_at_open(until_hour: int = 17) -> SyntheticSpec:
    """The monthlies have no quote on week 2's open (Tue Sep 8) before `until_hour`:00. The long is
    checked at its first fresh quote, and the short waits for it; with the default, the whole
    session, the long isn't checked and no short is sold that week (DEC-28)."""

    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell] | None:
        if t.date() == WEEK2_OPEN and t.hour < until_hour and _long_dated(option, t):
            return None, None
        return bid, ask

    return _spec(path=_flat(), quote_hook=hook)


def event_week(bump: float = 0.60) -> SyntheticSpec:
    """Week 1's weekly at `bump` IV, the next week's at 40%: the event gate's ratio (G-3)."""
    return _spec(path=_flat(), iv=replace(_BASE.iv, by_expiry={WEEK1_EXPIRY: bump}))


def rv_above_iv() -> SyntheticSpec:
    """A 60%-vol walk in the warm-up, options at 20% IV: IV ÷ RV20 under 1 (G-4)."""
    return _spec(seed=13, vol=0.60, iv=IvSurface(base=0.20))


def tiny_premium() -> SyntheticSpec:
    """Weeklies at 5% IV on a $0.50 grid: the OTM call nearest 0.30 delta is worth under $0.10
    (G-5)."""
    return _spec(path=_flat(), iv=IvSurface(weekly=0.05), weekly_step=0.5)


BUILDERS: dict[str, Callable[[], SyntheticSpec]] = {
    "random_walk": random_walk,
    "quiet": quiet,
    "premium_collapse": premium_collapse,
    "rally_through_strike": rally_through_strike,
    "friday_within_buffer": lambda: friday_within_buffer(102.0, 0.3),
    "friday_unquoted_at_check": lambda: friday_within_buffer(
        102.0, 0.3, unquoted_at_check=True, close=102.5
    ),
    "friday_unquoted_otm_close": lambda: friday_within_buffer(102.0, 0.3, unquoted_at_check=True),
    "long_unquoted_at_open": long_unquoted_at_open,
    "late_friday_surge": lambda: late_friday_surge(102.0),
    "surge_no_stock_quote": lambda: late_friday_surge(102.0, no_stock_quote_at_close=True),
    "long_delta_drop": long_delta_drop,
    "reset_reentry_wide": lambda: long_delta_drop(wide_on_reopen=True),
    "long_falls_after_check": long_falls_after_check,
    "short_frozen_then_rally": lambda: first_bar_wide(rally_to=103.0),
    "long_frozen_then_rally": lambda: first_bar_wide(rally_to=110.0, monthly=True),
    "no_quote_monday": no_quote_monday,
    "expensive_long": expensive_long,
    "entry_retry": entry_retry,
    "first_bar_wide": first_bar_wide,
    "stale_long_marks": stale_long_marks,
    "half_day_week": half_day_week,
    "independence_day_week": independence_day_week,
    "event_week": event_week,
    "rv_above_iv": rv_above_iv,
    "tiny_premium": tiny_premium,
}
"""Every builder, with example arguments where it takes some."""
