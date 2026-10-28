"""The wheel's verdicts and Trade P&L at their edges (W3-01; WD-28, WD-29)."""

from datetime import date, datetime
from decimal import Decimal

from pmcc.accounting.events import Event, StockId, expected_cash
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.export.wheel_models import WheelMetrics
from pmcc.wheel.analytics import trade_pnls, verdicts
from tests.scenario.winv10_run import BENCHMARKS

FRI = date(2026, 9, 4)
PUT = OptionId("SYN", FRI, Right.PUT, Price.from_dollars(98))
STOCK = StockId("SYN")


def _metrics(pnl: str = "100", sharpe: float | None = 1.0, ret: float = 0.02) -> WheelMetrics:
    return WheelMetrics(pnl=Decimal(pnl), return_on_starting_cash=ret, max_drawdown=Decimal(0),
                        max_drawdown_pct=0.0, sharpe_annualized=sharpe, sessions=5)  # fmt: skip


def test_wd_29_a_tie_is_not_met() -> None:
    sharpe = BENCHMARKS.baseline_pmcc.sharpe_annualized
    ret = BENCHMARKS.sp500.price_return

    claims = verdicts(_metrics("0", sharpe, ret), BENCHMARKS)

    assert [v.met for v in claims] == [False, False, False]


def test_wd_29_a_missing_sharpe_is_not_met() -> None:
    claims = verdicts(_metrics(sharpe=None), BENCHMARKS)

    assert (claims[1].wheel, claims[1].met) == (None, False)


def test_wd_29_a_claim_is_judged_on_its_published_value() -> None:
    # 1e-7 above the S&P's return prints as the same number, so it doesn't beat it.
    claims = verdicts(_metrics(ret=BENCHMARKS.sp500.price_return + 1e-7), BENCHMARKS)

    assert (claims[2].wheel, claims[2].met) == (BENCHMARKS.sp500.price_return, False)


def _event(hour: int, side: Side, instrument: OptionId | StockId, qty: int,
           fill: Price | None, fee: Money | None = None) -> Event:  # fmt: skip
    when = datetime(2026, 9, 4 if hour >= 16 else 1, hour % 24, tzinfo=ET)
    fee = fee or Money.zero()
    cash = Money.zero() if fill is None else expected_cash(side, instrument, qty, fill, fee)
    return Event(when, side, instrument, qty, fill, fill, cash, RuleId("W-P1"), fee=fee)


def test_wd_28_trade_pnl_nets_fees_and_counts_shares_from_their_purchase() -> None:
    fee = Money.from_dollars(Decimal("0.65"))
    sale = _event(10, Side.SELL, PUT, 1, Price.from_dollars(Decimal("1.50")), fee)
    assigned = Event(datetime(2026, 9, 4, 16, tzinfo=ET), Side.ASSIGN, PUT, 1, None, None,
                     Money.zero(), RuleId("W-X2"))  # fmt: skip
    bought = _event(16, Side.BUY, STOCK, 100, Price.from_dollars(98))
    sold = _event(17, Side.SELL, STOCK, 100, Price.from_dollars(101))

    assert trade_pnls([sale, assigned, bought, sold]) == [
        None,
        Money.from_dollars(Decimal("149.35")),
        None,
        Money.from_dollars(300),
    ]
