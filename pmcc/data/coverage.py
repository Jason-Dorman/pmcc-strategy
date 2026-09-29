"""The coverage summary printed after a fetch (ARCHITECTURE §6.1 step 5). It reads the cache only.

- **Valid mid (PO, 2026-09-28):** the share of session bars with a valid quote (BID > 0, ASK > 0,
  ASK ≥ BID), out of every session bar the calendar has over each answered contract's unit dates.
  A bar that never came back counts as having no mid.
- **Near the money:** weekly calls whose strike lies inside the unit's stock range (its
  near-money band before padding), over the weekly's own dates. A monthly Friday that is also a
  weekly expiry is one merged unit running from its first long-candidate session; its near-money
  strikes count only from the prior week's first session (PO, DEC-16). This is P1-09's ≥ 90%
  measure.
- **Counts:** contracts requested, answered and unanswered, per unit and per kind (LDG §5).
- **Flags:** bands whose step wasn't measured (DEC-14), units that answered nothing (DEC-83's
  residual risk) and fields that never came back (DEC-13).
- **IV failures (P2-04; PO, DEC-16):** session bars with a valid quote before the expiry close,
  priced by the chain pricer at the universe's r, whose IV didn't solve, by reason: below the
  no-arbitrage floor, above the cap, no convergence, no spot.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import final

import polars as pl
import structlog

from pmcc.data.cache import CachedUnit, Status, SymbolCache
from pmcc.data.discovery import Region, StepSource, UnitKind, unit_kind, weekly_dates
from pmcc.data.load import SymbolData, load_symbol
from pmcc.data.ric import parse_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.pricing.chain import PricedSymbol, price_symbol
from pmcc.pricing.iv import IvCode

_DAY = timedelta(days=1)
# Why a quoted contract got no IV. NO_QUOTE is the valid-mid line's; EXPIRED is the expiry close.
IV_FAILURES = (IvCode.BELOW_FLOOR, IvCode.ABOVE_CAP, IvCode.NO_CONVERGENCE, IvCode.NO_SPOT)
_NOT_PRICED = (IvCode.NO_QUOTE, IvCode.EXPIRED)

log = structlog.get_logger()


@dataclass
class Tally:
    """Contracts and session bars, summed over units."""

    units: int = 0
    requested: int = 0
    answered: int = 0
    unanswered: int = 0
    expected: int = 0  # session bars over the answered contracts' unit dates
    valid: int = 0  # of those, bars with a valid quote

    def add(self, other: "Tally") -> None:
        self.units += other.units
        self.requested += other.requested
        self.answered += other.answered
        self.unanswered += other.unanswered
        self.expected += other.expected
        self.valid += other.valid

    @property
    def share(self) -> float | None:
        return self.valid / self.expected if self.expected else None


@dataclass
class IvTally:
    """Session bars with a valid quote before the expiry close (`priced`), and why those whose
    IV didn't solve failed."""

    priced: int = 0
    failed: dict[IvCode, int] = field(default_factory=lambda: dict.fromkeys(IV_FAILURES, 0))

    @classmethod
    def of(cls, codes: dict[IvCode, int]) -> "IvTally":
        priced = sum(n for code, n in codes.items() if code not in _NOT_PRICED)
        return cls(priced, {code: codes.get(code, 0) for code in IV_FAILURES})

    def add(self, other: "IvTally") -> None:
        self.priced += other.priced
        for code, n in other.failed.items():
            self.failed[code] += n

    @property
    def failures(self) -> int:
        return sum(self.failed.values())


@final
@dataclass(frozen=True, slots=True)
class UnitCoverage:
    """One cached unit's coverage. `near` covers its near-the-money weekly calls only."""

    name: str
    kind: UnitKind
    tally: Tally
    near: Tally
    iv: IvTally
    unmeasured: int  # bands whose step is the probe report's
    fields_missing: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True)
class Coverage:
    symbol: str
    units: tuple[UnitCoverage, ...]
    by_kind: dict[UnitKind, Tally] = field(default_factory=dict[UnitKind, Tally])

    @property
    def near_money(self) -> Tally:
        total = Tally()
        for unit in self.units:
            total.add(unit.near)
        return total

    @property
    def iv(self) -> IvTally:
        total = IvTally()
        for unit in self.units:
            total.add(unit.iv)
        return total


def coverage(root: Path, symbol: str, calendar: SessionCalendar, rate: float) -> Coverage:
    """Every cached unit's coverage, loaded and priced as the backtest loads and prices it, with
    `rate` as r (DEC-11)."""
    data = load_symbol(root, symbol, calendar)
    priced = price_symbol(data.stock, data.chains, calendar, rate)
    units = tuple(_unit(u, data, _iv(u, priced)) for u in SymbolCache(root, symbol).units())
    by_kind: dict[UnitKind, Tally] = {}
    for unit in units:
        by_kind.setdefault(unit.kind, Tally()).add(unit.tally)
    return Coverage(symbol, units, by_kind)


def _iv(unit: CachedUnit, priced: PricedSymbol) -> IvTally:
    if unit.expiry is None or unit.right is None:
        return IvTally()  # the stock
    return IvTally.of(priced.codes(unit.expiry, unit.right))


def _unit(unit: CachedUnit, data: SymbolData, iv: IvTally) -> UnitCoverage:
    kind = unit_kind(unit.right, {b.region for b in unit.bands})
    if unit.expiry is None or unit.right is None:
        frame = data.stock
    else:
        frame = data.chains[(unit.expiry, unit.right)]
    answered = [e.ric for e in unit.entries if e.status is Status.ANSWERED and e.ric is not None]
    calendar, last = data.calendar, unit.end_exclusive - _DAY
    tally = Tally(
        units=1,
        requested=len(unit.entries),
        answered=len(answered),
        unanswered=len(unit.entries) - len(answered),
    )
    tally.add(_bars(frame, calendar, (unit.start, last), answered))
    near = Tally()
    if unit.expiry is not None and kind in (UnitKind.WEEKLY_CALLS, UnitKind.BOTH_CALLS):
        near_rics = _near_money(unit, answered)
        near.answered = len(near_rics)
        first, _ = weekly_dates(calendar, unit.expiry, last)
        near.add(_bars(frame, calendar, (max(first, unit.start), last), near_rics))
    return UnitCoverage(
        name=unit.name,
        kind=kind,
        tally=tally,
        near=near,
        iv=iv,
        unmeasured=sum(b.source is StepSource.PROBE_REPORT for b in unit.bands),
        fields_missing=tuple(f for f in unit.fields if answered and f not in unit.fields_returned),
    )


def _bars(
    frame: pl.DataFrame, calendar: SessionCalendar, dates: tuple[date, date], rics: Sequence[str]
) -> Tally:
    """`rics`' session bars from `dates[0]` to `dates[1]`: every one the calendar has
    (`expected`), and those with a valid quote (`valid`)."""
    first, last = dates
    bars = sum(len(s.bar_ends()) for s in calendar.sessions(first, last))
    inside = pl.col("bar_end").dt.date().is_between(first, last)
    counts = (
        frame.filter(pl.col("session_bar") & pl.col("valid_quote") & inside).group_by("ric").len()
    )
    valid = dict(zip(counts["ric"].to_list(), counts["len"].to_list(), strict=True))
    return Tally(expected=bars * len(rics), valid=sum(valid.get(r, 0) for r in rics))


def _near_money(unit: CachedUnit, answered: Sequence[str]) -> list[str]:
    """The answered calls whose strike lies in a near-money band, before padding."""
    near = [b for b in unit.bands if b.region is Region.NEAR_MONEY]
    return [
        ric
        for ric in answered
        if any(b.low <= parse_ric(ric).option.strike <= b.high for b in near)
    ]


def describe(cov: Coverage) -> str:
    """The summary as printed; each unit's line goes to the log (`fetch.coverage.unit`)."""
    for unit in cov.units:
        log.info(
            "fetch.coverage.unit",
            symbol=cov.symbol,
            unit=unit.name,
            kind=unit.kind.value,
            requested=unit.tally.requested,
            answered=unit.tally.answered,
            unanswered=unit.tally.unanswered,
            valid_mid=_pct(unit.tally),
            near_money_valid_mid=_pct(unit.near) if unit.near.answered else None,
            iv_priced=unit.iv.priced,
            iv_failed=unit.iv.failures,
            unmeasured_bands=unit.unmeasured,
            fields_missing=list(unit.fields_missing),
        )
    lines = [
        f"{cov.symbol} coverage: session bars with a valid mid, of every session bar over each "
        "answered contract's unit dates",
        f"  {'kind':<24}{'units':>7}{'requested':>11}{'answered':>10}{'unanswered':>12}"
        f"{'valid mid':>11}",
    ]
    for kind in UnitKind:
        t = cov.by_kind.get(kind)
        if t is not None:
            lines.append(
                f"  {kind.value:<24}{t.units:>7}{t.requested:>11,}{t.answered:>10,}"
                f"{t.unanswered:>12,}{_pct(t):>11}"
            )
    near = cov.near_money
    lines.append(
        f"Near-the-money weekly calls (strike inside the unit's stock range): {_pct(near)} of "
        f"{near.expected:,} session bars, {near.answered:,} contracts"
    )
    lines.append(_iv_line(cov.iv))
    lines.extend(_flags(cov))
    log.info(
        "fetch.coverage",
        symbol=cov.symbol,
        units=len(cov.units),
        near_money_valid_mid=_pct(near),
        iv_priced=cov.iv.priced,
        iv_failed=cov.iv.failures,
        **{k.value: _pct(t) for k, t in cov.by_kind.items()},
    )
    return "\n".join(lines)


def _iv_line(iv: IvTally) -> str:
    share = "n/a" if not iv.priced else f"{100 * iv.failures / iv.priced:.1f}%"
    reasons = ", ".join(f"{_REASONS[c]} {n:,}" for c, n in iv.failed.items())
    return (
        f"IV failures (session bars with a valid mid, before the expiry close): {share}, "
        f"{iv.failures:,} of {iv.priced:,} ({reasons})"
    )


_REASONS = {
    IvCode.BELOW_FLOOR: "below the floor",
    IvCode.ABOVE_CAP: "above the cap",
    IvCode.NO_CONVERGENCE: "no convergence",
    IvCode.NO_SPOT: "no spot",
}


def _flags(cov: Coverage) -> list[str]:
    unmeasured = [u.name for u in cov.units if u.unmeasured]
    silent = [u.name for u in cov.units if u.tally.requested and not u.tally.answered]
    missing = sorted({f for u in cov.units for f in u.fields_missing})
    return [
        f"Bands whose strike step wasn't measured (DEC-14): {_names(unmeasured)}",
        f"Units that answered nothing: {_names(silent)}",
        f"Fields that never came back: {_names(missing)}",
    ]


def _names(names: Sequence[str]) -> str:
    return ", ".join(names) if names else "none"


def _pct(t: Tally) -> str:
    share = t.share
    return "n/a" if share is None else f"{100 * share:.1f}%"
