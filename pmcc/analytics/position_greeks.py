"""Position Greeks (PO, DEC-120): the position's net δ, Γ, θ and vega at every bar, and each leg's
mean over the bars both legs were held, against the textbook PMCC's +δ, −Γ, +θ, +vega.

- **Units** are dollars from DEC-24's: δ × 100 × contracts (shares), Γ × 100 × contracts (shares
  per $1 of spot), θ ÷ 365 × 100 × contracts ($ a calendar day; θ is per year, ACT/365), vega ÷ 100
  × 100 × contracts ($ a vol point; vega is per 1.00 of vol). The short's are negated.
- **A bar's net** is the long's plus the short's plus, for δ, X-S5's stock (its shares). A Greek
  is null on a bar that holds nothing, or where a held leg's is unknown; the ledger's Greeks are
  used as it recorded them, a stale mark's included.
- **The table** averages each Greek over the bars ending with both legs held and it known for
  both, so a week with no short, and every weekend, stays out of it; `bars` counts them.
"""

from collections.abc import Sequence
from math import fsum

from pmcc.accounting.ledger import LedgerRow, LegRow
from pmcc.analytics.records import RunRecords
from pmcc.domain.instruments import OPTION_MULTIPLIER
from pmcc.export.analytics_models import GreekPoint, PositionGreekRow, PositionGreeks

DAYS_A_YEAR = 365  # DEC-24: ACT/365
VOL_POINT = 0.01  # one vol point, in DEC-24's units of 1.00
# The textbook PMCC's signs: long delta, short gamma, long theta, long vega.
EXPECTED = (("delta", 1), ("gamma", -1), ("theta", 1), ("vega", 1))

type _Greeks = tuple[float | None, float | None, float | None, float | None]
_NONE: _Greeks = (None, None, None, None)


def position_greeks(run: RunRecords) -> PositionGreeks:
    """The run's position Greeks, bar by bar and averaged per leg."""
    series: list[GreekPoint] = []
    longs: list[_Greeks] = []
    shorts: list[_Greeks] = []
    nets: list[_Greeks] = []
    for row in run.ledger:
        long, short = _dollars(row.long, 1), _dollars(row.short, -1)
        net = _net(row, long, short)
        series.append(GreekPoint(time=row.time, short_open=row.short is not None, delta=net[0],
                                 gamma=net[1], theta=net[2], vega=net[3]))  # fmt: skip
        if row.long is not None and row.short is not None:
            longs.append(long)
            shorts.append(short)
            nets.append(net)
    rows = tuple(_row(i, longs, shorts, nets) for i in range(len(EXPECTED)))
    return PositionGreeks(rows=rows, series=tuple(series))


def _dollars(leg: LegRow | None, sign: int) -> _Greeks:
    """A held leg's Greeks in dollar units, negated for the short; all None when none is held."""
    if leg is None:
        return _NONE
    g = leg.greeks
    size = sign * OPTION_MULTIPLIER * leg.qty
    return (_scaled(g.delta, size), _scaled(g.gamma, size), _scaled(g.theta, size / DAYS_A_YEAR),
            _scaled(g.vega, size * VOL_POINT))  # fmt: skip


def _scaled(value: float | None, by: float) -> float | None:
    return None if value is None else value * by


def _net(row: LedgerRow, long: _Greeks, short: _Greeks) -> _Greeks:
    """The bar's net: each Greek of every leg held, X-S5's shares added to δ."""
    held = [g for leg, g in ((row.long, long), (row.short, short)) if leg is not None]
    if not held:
        return _NONE
    delta, gamma, theta, vega = (_sum([g[i] for g in held]) for i in range(len(EXPECTED)))
    if row.stock is not None and delta is not None:
        delta += row.stock.shares
    return delta, gamma, theta, vega


def _sum(values: Sequence[float | None]) -> float | None:
    """The values' sum, or None if any is unknown."""
    known = [v for v in values if v is not None]
    return fsum(known) if len(known) == len(values) else None


def _row(i: int, longs: Sequence[_Greeks], shorts: Sequence[_Greeks],
         nets: Sequence[_Greeks]) -> PositionGreekRow:  # fmt: skip
    """Greek `i` averaged over the both-legs bars where it is known for both legs."""
    component, sign = EXPECTED[i]
    known = [(lg, sh, nt) for lg, sh, nt in ((a[i], b[i], c[i]) for a, b, c
             in zip(longs, shorts, nets, strict=True))
             if lg is not None and sh is not None and nt is not None]  # fmt: skip
    if not known:
        return PositionGreekRow(component=component, expected_sign=sign, long=None, short=None,
                                net=None, share_with_sign=None, bars=0)  # fmt: skip
    n = len(known)
    return PositionGreekRow(
        component=component,
        expected_sign=sign,
        long=fsum(lg for lg, _, _ in known) / n,
        short=fsum(sh for _, sh, _ in known) / n,
        net=fsum(nt for _, _, nt in known) / n,
        share_with_sign=sum(1 for _, _, nt in known if nt * sign > 0) / n,
        bars=n,
    )
