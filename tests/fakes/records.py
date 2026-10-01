"""Hand-made run records for the analytics tests (P6): a ledger of NAVs, blotter rows and gate-log
decisions, written out so each test's expected numbers can be worked by hand.

A ledger row here carries only what the analytics read (its time, NAV and whether a long is held);
its other fields are placeholders. A blotter row's cash follows from its fill, as the engine's do.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import final

from pmcc.accounting.events import Event, StockId, expected_cash
from pmcc.accounting.ledger import LedgerRow, LegRow
from pmcc.domain.clock import at_et
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId

ROOT = "SYN"
FEE = Money.from_dollars("0.65")
LONG = OptionId(ROOT, date(2027, 1, 15), Right.CALL, Price.from_dollars(80))
LONG_2 = OptionId(ROOT, date(2027, 3, 19), Right.CALL, Price.from_dollars(85))
STOCK = StockId(ROOT)


def short_call(expiry: date) -> OptionId:
    return OptionId(ROOT, expiry, Right.CALL, Price.from_dollars(105))


def at(day: date, hour: int = 16) -> datetime:
    return at_et(day, time(hour))


def bar(day: date, nav: str, hour: int = 16, *, long: bool = True) -> LedgerRow:
    """A ledger row at `hour` (the close bar by default) with NAV `nav` dollars."""
    held = LegRow(LONG, 1, Price.from_dollars(40), False, 0.8) if long else None
    value = Money.from_dollars(nav)
    zero = Money.zero()
    return LedgerRow(at(day, hour), held, None, None, value, value, zero, zero, value, value, ())


def trade(when: datetime, side: Side, instrument: OptionId | StockId, fill: str | None,
          rule: str, fee: Money = FEE) -> Event:  # fmt: skip
    """One blotter row of one contract (or 100 shares of stock, which pay no fee)."""
    price = None if fill is None else Price.from_dollars(fill)
    qty = 1 if isinstance(instrument, OptionId) else 100
    fee = Money.zero() if side in (Side.EXPIRE, Side.ASSIGN) or qty == 100 else fee
    cash = expected_cash(side, instrument, qty, price, fee)
    return Event(when, side, instrument, qty, price, price, cash, RuleId(rule), fee=fee)


@final
@dataclass(frozen=True, slots=True)
class Decision:
    """A gate-log row as the analytics read it."""

    session: date
    outcome: str
    rule_id: RuleId


def sold(session: date) -> Decision:
    return Decision(session, "sold", RuleId("E-S1"))


def skipped(session: date, rule: str) -> Decision:
    return Decision(session, "skipped", RuleId(rule))


@final
@dataclass(frozen=True, slots=True)
class Records:
    """A run's records, shaped as the engine's `RunOutput` is."""

    ledger: tuple[LedgerRow, ...]
    blotter: tuple[Event, ...] = ()
    gate_log: tuple[Decision, ...] = ()
    starting_cash: Money = field(default_factory=lambda: Money.from_dollars(10_000))


def week_of_closes(monday: date, closes: Sequence[str], *, long: bool = True) -> list[LedgerRow]:
    """One close bar per weekday from `monday`, at `closes` dollars."""
    return [bar(date.fromordinal(monday.toordinal() + i), nav, long=long)
            for i, nav in enumerate(closes)]  # fmt: skip


W1, W2, W3 = date(2026, 9, 14), date(2026, 9, 21), date(2026, 9, 28)  # their Mondays
FRI_1, FRI_3 = date(2026, 9, 18), date(2026, 10, 2)


def three_weeks() -> Records:
    """Three weeks from $10,000, the long held throughout.

    Session closes: week 1 10,050 · 10,100 · 9,950 · 10,000 · 10,200; week 2 10,150 · 9,995 ·
    10,050 · 10,100 · 10,098; week 3 10,300 · 10,250 · 10,350 · 10,400 · 10,500. Two bars inside a
    session: Mon Sep 14 at 10:00 (9,999.35, the long's fee) and 11:00 (10,000), and Wed Sep 16 at
    11:00 (9,900).

    - Week 1: the long bought at $40.00 (cost $4,000.65); a short sold for $2.00 (credit $199.35)
      and bought back by X-S1 at $0.50 ($50.65). P&L +200.
    - Week 2: G-2 skips the week. P&L −102.
    - Week 3: X-L2 sells the long at $45.00 and a new one is bought at $50.00 ($5,000.65); a short
      sold for $1.00 ($99.35) expires worthless (X-S4). P&L +402.
    """
    mon_1, wed_1, mon_3 = W1, date(2026, 9, 16), W3
    ledger = [
        bar(mon_1, "9999.35", 10), bar(mon_1, "10000", 11), bar(mon_1, "10050"),
        bar(date(2026, 9, 15), "10100"), bar(wed_1, "9900", 11), bar(wed_1, "9950"),
        bar(date(2026, 9, 17), "10000"), bar(FRI_1, "10200"),
        *week_of_closes(W2, ["10150", "9995", "10050", "10100", "10098"]),
        *week_of_closes(W3, ["10300", "10250", "10350", "10400", "10500"]),
    ]  # fmt: skip
    blotter = (
        trade(at(mon_1, 10), Side.BUY, LONG, "40.00", "E-L1"),
        trade(at(mon_1, 11), Side.SELL, short_call(FRI_1), "2.00", "E-S1"),
        trade(at(wed_1, 12), Side.BUY, short_call(FRI_1), "0.50", "X-S1"),
        trade(at(mon_3, 10), Side.SELL, LONG, "45.00", "X-L2"),
        trade(at(mon_3, 10), Side.BUY, LONG_2, "50.00", "E-L1"),
        trade(at(mon_3, 11), Side.SELL, short_call(FRI_3), "1.00", "E-S1"),
        trade(at(FRI_3), Side.EXPIRE, short_call(FRI_3), "0", "X-S4"),
    )
    return Records(tuple(ledger), blotter, (sold(W1), skipped(W2, "G-2"), sold(W3)))
