"""Leg attribution (Spec › Attribution; P6-03; PO, DEC-63): what each leg made over the run.

- **Short leg:** the net short premium, credits − buybacks: each sale's cash in and each close's
  cash out, net of fees; X-S4's expiry and X-S5's assignment buy back at $0. A short still open at
  the window's end is reported apart at its last mark (`short_open`), so the parts add up.
- **X-S5's stock**, apart from the short (DEC-63): its sale at the strike, its cover and, if still
  held, its last mark.
- **Long leg:** realized and unrealized P&L, its cash plus its last mark. The intrinsic part is
  each long's change in max(0, S − K) × 100 × contracts from the bar it was bought on to the bar it
  was sold on, or the last bar; S is the bar's spot (DEC-23), or the last spot before it when the
  bar had no trade. The extrinsic part is the rest, fees and friction included.
- **The series:** at each session's close, the long's P&L so far (realized, plus its mark) and the
  net short premium so far.

Every figure is exact integer money (DEC-44). The parts must add up to the run's P&L (long + net
short premium − short_open + stock), so a blotter row no leg claims can't go missing; a run whose
rows don't add up raises.
"""

from collections.abc import Sequence
from datetime import datetime

from pmcc.accounting.events import Event, Instrument
from pmcc.accounting.ledger import LedgerRow
from pmcc.analytics.records import (
    RunRecords,
    by_bar,
    cash,
    closes_long,
    closes_short,
    leg_value,
    opens_long,
    opens_short,
    stock_value,
    trades_long,
    trades_short,
)
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId
from pmcc.domain.money import Money, Price
from pmcc.export.analytics_models import LegAttribution, LegPoint


def leg_attribution(run: RunRecords) -> LegAttribution:
    """The run's legs. Raises `ValueError` for a run without bars, a long traded on a bar with no
    spot at or before it, or rows whose legs don't add up to the run's P&L."""
    blotter, ledger = run.blotter, run.ledger
    if not ledger:
        raise ValueError("a run without bars has no attribution")
    last = ledger[-1]
    credits = cash(e for e in blotter if opens_short(e))
    buybacks = -cash(e for e in blotter if closes_short(e))
    short_open = leg_value(last.short)
    stock = cash(e for e in blotter if not e.is_option) + stock_value(last.stock)
    long_pnl = cash(e for e in blotter if trades_long(e)) + leg_value(last.long)
    pnl = last.nav - run.starting_cash
    total = long_pnl + credits - buybacks - short_open + stock
    if total != pnl:
        raise ValueError(f"the legs add up to {total}, not the run's P&L {pnl}")
    intrinsic = _intrinsic_change(blotter, ledger)
    return LegAttribution(
        short_credits=credits.to_dollars(),
        short_buybacks=buybacks.to_dollars(),
        net_short_premium=(credits - buybacks).to_dollars(),
        short_open=short_open.to_dollars(),
        assignment_stock_pnl=stock.to_dollars(),
        long_pnl=long_pnl.to_dollars(),
        long_intrinsic=intrinsic.to_dollars(),
        long_extrinsic=(long_pnl - intrinsic).to_dollars(),
        series=_series(blotter, ledger),
    )


def _intrinsic_change(blotter: Sequence[Event], ledger: Sequence[LedgerRow]) -> Money:
    """Σ intrinsic at each long's exit (or the last bar) − Σ intrinsic at its entry."""
    spots = _spots(ledger)
    change = Money.zero()
    for event in blotter:
        if opens_long(event):
            change -= _intrinsic(event.instrument, event.qty, _spot(spots, event.time))
        elif closes_long(event):
            change += _intrinsic(event.instrument, event.qty, _spot(spots, event.time))
    last = ledger[-1]
    if last.long is not None:
        change += _intrinsic(last.long.option, last.long.qty, _spot(spots, last.time))
    return change


def _spots(ledger: Sequence[LedgerRow]) -> dict[datetime, Price]:
    """Each bar's spot, or the last one before it on a bar without a trade (DEC-23)."""
    found: dict[datetime, Price] = {}
    spot: Price | None = None
    for row in ledger:
        if row.spot is not None:
            spot = row.spot
        if spot is not None:
            found[row.time] = spot
    return found


def _spot(spots: dict[datetime, Price], time: datetime) -> Price:
    if time not in spots:
        raise ValueError(f"no spot at or before {time.isoformat()} for a long's intrinsic value")
    return spots[time]


def _intrinsic(option: Instrument, qty: int, spot: Price) -> Money:
    """A long call's max(0, S − K) × 100 × contracts."""
    if not isinstance(option, OptionId):
        raise ValueError(f"a long is a call, not {option}")
    return Price(max(0, spot.units - option.strike.units)).notional(OPTION_MULTIPLIER, qty)


def _series(blotter: Sequence[Event], ledger: Sequence[LedgerRow]) -> tuple[LegPoint, ...]:
    trades = by_bar(blotter)
    closes = {to_et(row.time).date(): at for at, row in enumerate(ledger)}  # a session's last bar
    long_cash, premium = Money.zero(), Money.zero()
    points: list[LegPoint] = []
    for at, row in enumerate(ledger):
        bar = trades.get(row.time, [])
        long_cash += cash(e for e in bar if trades_long(e))
        premium += cash(e for e in bar if trades_short(e))
        session = to_et(row.time).date()
        if closes[session] == at:
            points.append(LegPoint(session=session,
                                   long_pnl=(long_cash + leg_value(row.long)).to_dollars(),
                                   net_short_premium=premium.to_dollars()))  # fmt: skip
    return tuple(points)
