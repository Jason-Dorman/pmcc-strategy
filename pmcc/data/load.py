"""Loading one symbol's cache into frames keyed by `bar_end` (ARCHITECTURE §6.5). No network.

`load_symbol` reads what the sidecars record, never `manifest.json` (DEC-46), and refuses a cache
that doesn't match them: a unit file missing or changed since it was written, or a parquet with no
sidecar. Then, per unit:

1. Scan the parquet (polars, lazily).
2. Quantize prices to $0.0001 units, exactly as `Price.from_dollars` does (DEC-44).
3. Add `bar_end`, the bar's start + 1h in America/New_York (DEC-06).
4. Tag session bars (`session_bar`): bars ending on the hour from 10:00 to the session's close.
5. Mark quote validity (`valid_quote`): BID > 0, ASK > 0 and ASK ≥ BID (LDG §4.7).

The stock tape's trading days must match the calendar, or loading stops (DEC-33). Every bar is
kept for provenance; only session bars reach MarketView.
"""

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import final

import numpy as np
import numpy.typing as npt
import polars as pl

from pmcc.data.cache import STOCK_UNIT, CachedUnit, CacheError, SymbolCache, data_manifest_hash
from pmcc.data.calendar import sessions_from_tape
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import UNITS_PER_DOLLAR, Price

PRICE_FIELDS = ("BID", "ASK", "TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1")
_ET = "America/New_York"
# Past this many dollars, or this close to a half unit, a float's scaled value can't be trusted
# to round like its decimal repr; those few values go through `Price.from_dollars` itself.
_EXACT_BELOW_DOLLARS = 100_000.0
_HALF_TOLERANCE = 1e-6


@final
@dataclass(frozen=True, slots=True)
class SymbolData:
    """One symbol's cache, loaded: the stock tape and a frame per (expiry, right).

    Prices are Int64 counts of $0.0001 units. `data_manifest_hash` goes in every run manifest.
    """

    symbol: str
    stock: pl.DataFrame
    chains: Mapping[tuple[date, Right], pl.DataFrame]
    calendar: SessionCalendar
    data_manifest_hash: str


def load_symbol(root: Path, symbol: str, calendar: SessionCalendar) -> SymbolData:
    """`root/{symbol}/`, loaded. Raises `CacheError` for a cache its sidecars don't describe,
    and `CalendarMismatchError` when the stock tape's trading days aren't the calendar's."""
    cache = SymbolCache(root, symbol)
    units = verified_units(cache)
    stock = next((u for u in units if u.name == STOCK_UNIT), None)
    if stock is None:
        raise CacheError(f"{cache.dir} has no stock unit; fetch {symbol} first")
    stock_frame = _load_unit(cache, stock, calendar)
    last_day = stock.end_exclusive - timedelta(days=1)
    sessions_from_tape(calendar, stock_frame["bar_start_utc"], stock.start, last_day)
    chains = {
        (u.expiry, u.right): _load_unit(cache, u, calendar)
        for u in units
        if u.expiry is not None and u.right is not None
    }
    return SymbolData(
        symbol=symbol,
        stock=stock_frame,
        chains=chains,
        calendar=calendar,
        data_manifest_hash=data_manifest_hash(e for u in units for e in u.entries),
    )


def verified_units(cache: SymbolCache) -> tuple[CachedUnit, ...]:
    """The cached units, once every parquet is there, unchanged, and has a sidecar."""
    orphans = cache.orphans()
    if orphans:
        raise CacheError(
            f"parquet with no sidecar (a write was killed): {[str(p) for p in orphans]}; "
            "move them aside and fetch those units again"
        )
    units = cache.units()
    for unit in units:
        path = cache.parquet_path(unit.name)
        if not path.exists():
            raise CacheError(f"{path} is missing; its sidecar says it was written")
        if hashlib.sha256(path.read_bytes()).hexdigest() != unit.file_sha256:
            raise CacheError(f"{path} has changed since it was written (sha256 differs)")
    return units


def _load_unit(cache: SymbolCache, unit: CachedUnit, calendar: SessionCalendar) -> pl.DataFrame:
    frame = pl.scan_parquet(cache.parquet_path(unit.name)).collect()
    prices = [f for f in PRICE_FIELDS if f in frame.columns]
    frame = frame.with_columns(quantize(frame[f]) for f in prices)
    frame = frame.with_columns(
        bar_end=(pl.col("bar_start_utc") + pl.duration(hours=1)).dt.convert_time_zone(_ET)
    )
    return frame.with_columns(
        session_bar=pl.col("bar_end").is_in(
            _session_bar_ends(frame["bar_end"], calendar).implode()
        ),
        valid_quote=_valid_quote(frame.columns),
    )


def _session_bar_ends(bar_ends: pl.Series, calendar: SessionCalendar) -> pl.Series:
    """Every session bar's end over the days `bar_ends` span, per the calendar."""
    dtype = pl.Datetime("us", _ET)
    if bar_ends.is_empty():
        return pl.Series([], dtype=dtype)
    days: list[date] = bar_ends.dt.date().to_list()
    ends: list[datetime] = [
        end for s in calendar.sessions(min(days), max(days)) for end in s.bar_ends()
    ]
    return pl.Series(ends, dtype=dtype)


def _valid_quote(columns: Sequence[str]) -> pl.Expr:
    if "BID" not in columns or "ASK" not in columns:
        return pl.lit(False)
    bid, ask = pl.col("BID"), pl.col("ASK")
    return ((bid > 0) & (ask > 0) & (ask >= bid)).fill_null(False)


def quantize(dollars: pl.Series) -> pl.Series:
    """Float dollars → Int64 $0.0001 units, exactly as `Price.from_dollars` (half-even on the
    float's shortest repr, DEC-44). Null and NaN become null.

    Scaling in floating point rounds the same as the decimal repr except within float error of a
    half unit, or for huge values; those go through `Price.from_dollars`.
    """
    values: npt.NDArray[np.float64] = dollars.cast(pl.Float64).to_numpy()
    present = ~np.isnan(values)
    if np.isinf(values).any():
        raise ValueError(f"{dollars.name}: an infinite price")
    scaled = values * UNITS_PER_DOLLAR
    units = np.rint(np.where(present, scaled, 0.0)).astype(np.int64)
    doubtful = present & (
        (np.abs(scaled - np.floor(scaled) - 0.5) < _HALF_TOLERANCE)
        | (np.abs(values) >= _EXACT_BELOW_DOLLARS)
    )
    for i in np.flatnonzero(doubtful):
        units[i] = Price.from_dollars(float(values[i])).units
    return pl.Series(dollars.name, units, dtype=pl.Int64).set(pl.Series(~present), None)
