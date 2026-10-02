"""The fill-assumption check's sample (P6-07; PO, DEC-64): every trade print paired with its bar's
end-of-bar mid, from the cache. `pmcc.analytics.fillcheck` fits them.

- **A pair** is one call's session bar inside the window with a TRDPRC_1 (LSEG leaves it out of a
  bar without a trade) and a valid quote at the bar's end (BID > 0, ASK ≥ BID). Its mid rounds
  half-even to $0.0001, as a fill at mid does (DEC-44).
- **Shorts** are a chain's bars over its weekly's dates, the prior week's first session to the
  expiry, as the weekly call bands are fetched (DEC-16). **Longs** are its bars before those
  dates, which only a monthly long candidate has. Puts are neither.
- **A monthly that is also a weekly expiry** is one cached unit holding both bands (DEC-16): its
  shorts are the strikes from its near-money band's padded floor up, and its longs the strikes up
  to its deep-in-the-money bands' padded top, so a deep call two weeks from expiry is never a
  short, nor an out-of-the-money one a long. A unit whose sidecar records only one region, or
  none, keeps every strike.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import final

import polars as pl

from pmcc.data.cache import CachedBand, CachedUnit
from pmcc.data.discovery import (
    LONG_PAD_STEPS,
    WEEKLY_BELOW_STEPS,
    Band,
    Pad,
    Region,
    weekly_dates,
)
from pmcc.data.load import SymbolData
from pmcc.domain.instruments import Right

SHORTS, LONGS = "shorts", "longs"
_ORDER = ("bar_end", "_expiry", "strike_cents")


@final
@dataclass(frozen=True, slots=True)
class FillSample:
    """One group's pairs as columns of $0.0001 units, ordered by bar, expiry and strike."""

    mid: tuple[int, ...]
    trade: tuple[int, ...]
    spread: tuple[int, ...]


def fill_pairs(data: SymbolData, units: Sequence[CachedUnit],
               window: tuple[date, date]) -> dict[str, FillSample]:  # fmt: skip
    """The shorts' and the longs' pairs over `window` (first and last session, inclusive)."""
    start, end = window
    parts: dict[str, list[pl.DataFrame]] = {SHORTS: [], LONGS: []}
    for unit in units:
        if unit.expiry is None or unit.right is not Right.CALL:
            continue
        day = pl.col("bar_end").dt.date()
        bars = (
            data.chains[(unit.expiry, unit.right)]
            .filter(pl.col("session_bar") & pl.col("valid_quote") & day.is_between(start, end))
            .filter(pl.col("TRDPRC_1").is_not_null())
            .with_columns(_expiry=pl.lit(unit.expiry))
        )
        weekly_from, _ = weekly_dates(data.calendar, unit.expiry, end)
        floor, top = _strike_limits(unit.bands)
        strike = pl.col("strike_cents")
        parts[SHORTS].append(bars.filter((day >= weekly_from) & (strike >= floor)))
        parts[LONGS].append(bars.filter((day < weekly_from) & (strike <= top)))
    return {group: _sample(frames) for group, frames in parts.items()}


def _strike_limits(bands: Sequence[CachedBand]) -> tuple[int, int | float]:
    """In cents, the lowest short and the highest long strike of a unit that holds both bands;
    no limit otherwise."""
    near = [b for b in bands if b.region is Region.NEAR_MONEY]
    deep = [b for b in bands if b.region is Region.DEEP_ITM]
    if not (near and deep):
        return 0, float("inf")
    floor = min(_ladder(b, Pad(WEEKLY_BELOW_STEPS), Pad(0))[0] for b in near)
    top = max(_ladder(b, Pad(0), Pad(LONG_PAD_STEPS))[-1] for b in deep)
    return floor, top


def _ladder(band: CachedBand, below: Pad, above: Pad) -> tuple[int, ...]:
    """The band's strikes in cents, padded as the fetch padded that edge (ARCHITECTURE §6.3)."""
    return Band(band.region, band.low, band.high, below, above).ladder(band.step)


def _sample(frames: Sequence[pl.DataFrame]) -> FillSample:
    columns = ("BID", "ASK", "TRDPRC_1", *_ORDER)
    if not frames:
        return FillSample((), (), ())
    bars = pl.concat([f.select(columns) for f in frames]).sort(_ORDER, maintain_order=True)
    total = pl.col("BID") + pl.col("ASK")
    half = total // 2
    odd_half = (total % 2 == 1) & (half % 2 == 1)  # x.5 units rounds half-even: up to the even
    pairs = bars.select(
        mid=half + odd_half.cast(pl.Int64),
        trade=pl.col("TRDPRC_1"),
        spread=pl.col("ASK") - pl.col("BID"),
    )
    return FillSample(*(tuple(pairs[c].to_list()) for c in ("mid", "trade", "spread")))
