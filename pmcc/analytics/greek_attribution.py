"""Greek attribution (Spec › Attribution; P6-04; PO, DEC-63, DEC-76): each leg's change, bar by
bar, against what its Greeks predicted.

- **A bar's change (ΔV)** for a leg is its P&L over the bar: its value at the bar's end, plus the
  cash of its trades on the bar, less its value at the previous bar's end. A leg's value is its
  mark × 100 × contracts, negative for the short. So a leg's changes add up to its P&L, and a
  trade's friction and fees (none at the default fill model) fall in the residual.
- **The prediction** for a leg held at the previous bar's end, per share: δΔS + ½Γ(ΔS)² + θΔt +
  νΔσ, with that bar's Greeks as the ledger recorded them (DEC-24 units); ΔS is the change in spot,
  Δt the elapsed years (ACT/365, in UTC) and Δσ the change in the contract's IV. It is × 100 ×
  contracts, negated for the short. The IV at the bar's end is the leg's own while it is still
  held, or else the IV its closing fill was at (`fill_iv` in the fill's audit).
- **Residual = actual − predicted.** A held bar is residual whole when the prediction can't be
  made: a stale mark at either end, no spot at either end, an IV or Greek unknown (a call under its
  floor has DEC-27's Greeks but no IV), or a close without a fill (X-S4's expiry, X-S5's
  assignment). Those bars are counted per leg.
- **Sums are exact:** each float is summed as the fraction it is, so no total depends on the order
  of the bars, and a leg's components add up to its change exactly before they are published.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from pmcc.accounting.events import Event
from pmcc.accounting.ledger import LedgerRow, LegRow
from pmcc.analytics.records import RunRecords, by_bar, cash, leg_value, trades_long, trades_short
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Side
from pmcc.domain.money import UNITS_PER_DOLLAR, Money
from pmcc.export.analytics_models import GreekAttribution, GreekLeg, GreekRow, ResidualPoint
from pmcc.pricing.expiry import years_between

LONG, SHORT = "long", "short"
COMPONENTS = ("delta", "gamma", "theta", "vega")
RESIDUAL = "residual"

type _Parts = tuple[Fraction, Fraction, Fraction, Fraction]  # delta, gamma, theta, vega: dollars
_NONE: _Parts = (Fraction(0), Fraction(0), Fraction(0), Fraction(0))


@dataclass
class _Tally:
    """One leg over the run."""

    parts: list[Fraction] = field(default_factory=lambda: [Fraction(0)] * len(COMPONENTS))
    residual: Fraction = Fraction(0)
    change: Money = field(default_factory=Money.zero)
    held: int = 0
    unattributed: int = 0


def greek_attribution(run: RunRecords) -> GreekAttribution:
    """The run's Greek attribution, the long leg's rows first."""
    tallies = {LONG: _Tally(), SHORT: _Tally()}
    trades = by_bar(run.blotter)
    points: list[ResidualPoint] = []
    cumulative = Fraction(0)
    before: LedgerRow | None = None
    for row in run.ledger:
        bar = trades.get(row.time, [])
        for leg, tally in tallies.items():
            cumulative += _bar(tally, leg, before, row, bar)
        points.append(ResidualPoint(time=row.time, cumulative=float(cumulative)))
        before = row
    return GreekAttribution(
        legs=tuple(_leg(leg, t) for leg, t in tallies.items()),
        rows=tuple(row for leg, t in tallies.items() for row in _rows(leg, t)),
        residual=tuple(points),
    )


def _bar(tally: _Tally, leg: str, before: LedgerRow | None, row: LedgerRow,
         bar: Sequence[Event]) -> Fraction:  # fmt: skip
    """Adds the bar's change and its parts to `tally`; returns the bar's residual."""
    actual = _change(leg, before, row, bar)
    held = None if before is None else _held(before, leg)
    parts = _NONE
    if before is not None and held is not None:
        tally.held += 1
        predicted = _predict(leg, held, before, row, bar)
        if predicted is None:
            tally.unattributed += 1
        else:
            parts = predicted
    residual = Fraction(actual.units, UNITS_PER_DOLLAR) - sum(parts, Fraction(0))
    tally.change += actual
    tally.parts = [total + part for total, part in zip(tally.parts, parts, strict=True)]
    tally.residual += residual
    return residual


def _held(row: LedgerRow, leg: str) -> LegRow | None:
    return row.long if leg == LONG else row.short


def _sign(leg: str) -> int:
    return 1 if leg == LONG else -1


def _change(leg: str, before: LedgerRow | None, row: LedgerRow, bar: Sequence[Event]) -> Money:
    """The leg's value at `row`, plus its trades' cash on the bar, less its value at `before`."""
    trades = cash(e for e in bar if (trades_long(e) if leg == LONG else trades_short(e)))
    then = Money.zero() if before is None else leg_value(_held(before, leg))
    return (leg_value(_held(row, leg)) - then) * _sign(leg) + trades


def _predict(leg: str, held: LegRow, before: LedgerRow, row: LedgerRow,
             bar: Sequence[Event]) -> _Parts | None:  # fmt: skip
    """δΔS, ½Γ(ΔS)², θΔt and νΔσ for the position, or None if any input is unknown or stale."""
    g = held.greeks
    iv, delta, gamma, theta, vega = g.iv, g.delta, g.gamma, g.theta, g.vega
    if iv is None or delta is None or gamma is None or theta is None or vega is None:
        return None
    end_iv = _end_iv(held.option, _held(row, leg), bar)
    if held.stale or end_iv is None or before.spot is None or row.spot is None:
        return None
    ds = (row.spot.units - before.spot.units) / UNITS_PER_DOLLAR
    dt = years_between(before.time, row.time)
    per_share = (delta * ds, 0.5 * gamma * ds * ds, theta * dt, vega * (end_iv - iv))
    size = _sign(leg) * OPTION_MULTIPLIER * held.qty
    d, gm, th, v = (Fraction(p) * size for p in per_share)
    return d, gm, th, v


def _end_iv(option: OptionId, after: LegRow | None, bar: Sequence[Event]) -> float | None:
    """The contract's IV at the bar's end: its own if still held (unless stale), else its closing
    fill's. An expiry or assignment has none."""
    if after is not None and after.option == option:
        return None if after.stale else after.greeks.iv
    for event in bar:
        if event.instrument == option and event.side in (Side.BUY, Side.SELL):
            iv = event.audit.get("fill_iv")
            return iv if isinstance(iv, float) else None
    return None


def _leg(leg: str, tally: _Tally) -> GreekLeg:
    return GreekLeg(leg=leg, change=tally.change.to_dollars(), bars_held=tally.held,
                    bars_unattributed=tally.unattributed)  # fmt: skip


def _rows(leg: str, tally: _Tally) -> list[GreekRow]:
    change = Fraction(tally.change.units, UNITS_PER_DOLLAR)
    named = [*zip(COMPONENTS, tally.parts, strict=True), (RESIDUAL, tally.residual)]
    return [GreekRow(leg=leg, component=name, dollars=float(value),
                     share_of_change=float(value / change) if change else None)
            for name, value in named]  # fmt: skip
