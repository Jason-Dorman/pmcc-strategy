"""DEC-08 and DEC-09: long-dated coverage now, and whether live contracts answer in the live form.

Calls on the monthly nearest 180 DTE, at strikes spanning about delta 0.90 to 0.70, over the last
20 sessions of hourly BID/ASK. The pricer isn't built yet (P2), so the strikes come from
Black-Scholes with r = 0 and the stock's 60-session realized volatility: a probe's estimate, not
the backtest's delta. Per contract, and pooled:

- the share of session bars with a valid mid (BID > 0, ASK > 0, ASK >= BID);
- the median spread as a % of mid;
- bars whose mid is below intrinsic, max(0, S - K), with S the stock's print in the same bar.
  With r > 0 the no-arbitrage floor S - K*exp(-rT) is higher, so this is a lower bound on the IV
  failures DEC-08 counts; the r-dependent count waits for DEC-11.

The contracts are live, so they are asked in the live form only (DEC-45); the record says how
many answered (DEC-09).
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from statistics import NormalDist
from typing import final

import polars as pl

from pmcc.data.fetch import fetch_contracts, fetch_rics
from pmcc.data.probe.context import Json, Probe, over, session_bar_ends, valid_mid, wide
from pmcc.data.provider import Interval
from pmcc.data.ric import forms_to_ask
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price

DELTAS = (0.90, 0.70)
MAX_STRIKES = 8
SESSIONS = 20
FIELDS = ("BID", "ASK", "TRDPRC_1")
_YEAR_DAYS = 365


def strike_for_delta(spot: float, vol: float, years: float, delta: float) -> float:
    """The strike whose Black-Scholes call delta is `delta` (r = q = 0)."""
    root_t = vol * math.sqrt(years)
    return spot * math.exp(-NormalDist().inv_cdf(delta) * root_t + root_t**2 / 2)


def delta_strikes(spot: float, vol: float, years: float, step: int) -> list[int]:
    """Strikes in cents on the `step` grid from delta 0.90 to 0.70, at most 8, evenly thinned.

    If the band is narrower than one step, the grid strike nearest its middle.
    """
    low, high = (strike_for_delta(spot, vol, years, d) * 100 for d in DELTAS)
    grid = list(range(math.ceil(low / step) * step, math.floor(high / step) * step + 1, step))
    if not grid:
        return [max(step, round((low + high) / 2 / step) * step)]
    if len(grid) <= MAX_STRIKES:
        return grid
    picks = {round(i * (len(grid) - 1) / (MAX_STRIKES - 1)) for i in range(MAX_STRIKES)}
    return [grid[i] for i in sorted(picks)]


@final
@dataclass(frozen=True, slots=True)
class ContractCoverage:
    ric: str
    strike: float
    valid_mid_bars: int
    median_spread_pct: float | None
    below_intrinsic: int

    def record(self) -> Json:
        spread = self.median_spread_pct
        return {
            "ric": self.ric,
            "strike": self.strike,
            "valid_mid_bars": self.valid_mid_bars,
            "median_spread_pct": None if spread is None else round(spread, 3),
            "below_intrinsic": self.below_intrinsic,
        }


def probe_coverage(
    probe: Probe, stock_ric: str, spot: float, vol: float, expiry: date, step: int
) -> Json:
    years = (expiry - probe.last_session.day).days / _YEAR_DAYS
    options = [
        OptionId(probe.root, expiry, Right.CALL, Price(k * UNITS_PER_CENT))
        for k in delta_strikes(spot, vol, years, step)
    ]
    sessions = probe.recent(SESSIONS)
    options_asked = over(sessions, FIELDS, Interval.HOURLY)
    result = fetch_contracts(probe.provider, options, options_asked, probe.today, retry=probe.retry)
    stock_asked = over(sessions, ("TRDPRC_1",), Interval.HOURLY)
    stock = fetch_rics(probe.provider, [stock_ric], stock_asked, retry=probe.retry)
    ends = session_bar_ends(sessions)
    strikes = {ric: o.strike_cents / 100 for o, ric in result.answered.items()}
    bars = session_quotes(result.history.rows, stock.series(stock_ric), ends, strikes)
    contracts = per_contract(bars)
    return {
        "expiry": expiry.isoformat(),
        "dte": (expiry - probe.last_session.day).days,
        "vol_used": round(vol, 4),
        "spot": spot,
        "sessions": [sessions[0].day.isoformat(), sessions[-1].day.isoformat()],
        "session_bars_per_contract": ends.len(),
        "contracts": [c.record() for c in contracts],
        "pooled": pooled(bars, contracts, ends.len(), len(options)),
        "live_form": {
            "asked": len(options),
            "answered": len(result.answered),
            "forms_asked": [f.value for f in forms_to_ask(expiry, probe.today)],
            "forms_used": sorted({f.value for f in result.ric_form_used.values()}),
        },
    }


def session_quotes(
    rows: pl.DataFrame, stock: pl.DataFrame, ends: pl.Series, strikes: Mapping[str, float]
) -> pl.DataFrame:
    """One row per contract and session bar: `valid`, `mid`, `spread_pct`, `spot`, `strike`."""
    quotes = wide(rows).filter(pl.col("end").is_in(ends.implode()))
    for column in ("BID", "ASK"):
        if column not in quotes.columns:
            quotes = quotes.with_columns(pl.lit(None, pl.Float64()).alias(column))
    spots = wide(stock)
    spots = (
        spots.select("end", pl.col("TRDPRC_1").alias("spot"))
        if "TRDPRC_1" in spots.columns
        else pl.DataFrame(schema={"end": spots.schema["end"], "spot": pl.Float64()})
    )
    mid = (pl.col("BID") + pl.col("ASK")) / 2
    return (
        quotes.join(spots, on="end", how="left")
        .with_columns(valid=valid_mid(quotes).fill_null(False), mid=mid)
        .with_columns(
            spread_pct=(pl.col("ASK") - pl.col("BID")) / pl.col("mid") * 100,
            strike=pl.col("ric").replace_strict(dict(strikes), return_dtype=pl.Float64()),
        )
    )


def per_contract(bars: pl.DataFrame) -> list[ContractCoverage]:
    below = pl.col("valid") & (pl.col("mid") < (pl.col("spot") - pl.col("strike")).clip(0))
    per = bars.group_by("ric").agg(
        strike=pl.col("strike").first(),
        valid_mid_bars=pl.col("valid").sum(),
        median_spread_pct=pl.col("spread_pct").filter(pl.col("valid")).median(),
        below_intrinsic=below.fill_null(False).sum(),
    )
    return [ContractCoverage(**row) for row in per.sort("strike").iter_rows(named=True)]


def pooled(
    bars: pl.DataFrame, contracts: list[ContractCoverage], bars_each: int, asked: int
) -> Json:
    valid = bars.filter(pl.col("valid"))
    spread = valid["spread_pct"].median() if valid.height else None
    return {
        "contracts_asked": asked,
        "contracts_with_bars": len(contracts),
        "valid_mid_share": round(valid.height / (bars_each * asked), 4) if asked else None,
        "median_spread_pct": None if spread is None else round(float(str(spread)), 3),
        "below_intrinsic": sum(c.below_intrinsic for c in contracts),
    }
