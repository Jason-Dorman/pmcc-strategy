"""A hand-built `MarketView` for rule unit tests: chains row by row, so a test can put a delta, a
spread or a strike exactly on a rule's threshold (TEST-STRATEGY §4)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

import numpy as np

from pmcc.config.calendar import load_calendar
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_DOLLAR, Price
from pmcc.domain.quotes import Quote
from pmcc.pricing.chain import PricedQuotes
from pmcc.pricing.iv import IvCode
from pmcc.strategy.ports import ChainSnapshot, ExpiryKind, LookAheadError

ROOT = "SYN"
CALENDAR = load_calendar()


@dataclass(frozen=True, slots=True)
class Row:
    """One contract on the bar: strike and quote in dollars, and its delta and IV code."""

    strike: float | str
    bid: float | str | None
    ask: float | str | None
    delta: float = float("nan")
    code: IvCode = IvCode.OK
    iv: float = 0.30


def chain(
    expiry: date, now: datetime, rows: Sequence[Row], right: Right = Right.CALL
) -> ChainSnapshot:
    valid = [r.bid is not None and r.ask is not None for r in rows]
    bid = np.array([_units(r.bid) for r in rows], dtype=np.int64)
    ask = np.array([_units(r.ask) for r in rows], dtype=np.int64)
    ok = np.array(valid, dtype=np.bool_)
    mid = np.where(ok, (bid + ask) / (2 * UNITS_PER_DOLLAR), np.nan)
    spread = np.where(ok, (ask - bid) / UNITS_PER_DOLLAR, np.nan) / mid
    code = np.array([r.code if v else IvCode.NO_QUOTE for r, v in zip(rows, valid, strict=True)],
                    dtype=np.int8)  # fmt: skip
    floats = np.zeros(len(rows))
    quotes = PricedQuotes(
        strike=np.array([_units(r.strike) for r in rows], dtype=np.int64),
        bid=bid,
        ask=ask,
        valid=ok,
        mid=mid,
        spread_pct=spread,
        iv=np.array([r.iv if c == IvCode.OK else np.nan for r, c in zip(rows, code, strict=True)]),
        code=code,
        delta=np.array([r.delta for r in rows], dtype=np.float64),
        gamma=floats,
        theta=floats,
        vega=floats,
        extrinsic=floats,
    )
    return ChainSnapshot(expiry, right, now, quotes)


def _units(dollars: float | str | None) -> int:
    return 0 if dollars is None else Price.from_dollars(dollars).units


@dataclass
class StubView:
    now: datetime
    spot_price: Price | None = None
    chains: Mapping[tuple[date, Right], Sequence[Row]] = field(
        default_factory=dict[tuple[date, Right], Sequence[Row]]
    )
    listed: Mapping[ExpiryKind, tuple[date, ...]] = field(
        default_factory=dict[ExpiryKind, tuple[date, ...]]
    )
    root: str = ROOT

    def _gate(self, at: datetime | None) -> datetime:
        t = self.now if at is None else at
        if t > self.now:
            raise LookAheadError("stub: read after now")
        return t

    def spot(self, at: datetime | None = None) -> Price | None:
        self._gate(at)
        return self.spot_price

    def stock_quote(self, at: datetime | None = None) -> Quote | None:
        self._gate(at)
        return None

    def quote(self, option: OptionId, at: datetime | None = None) -> Quote | None:
        snapshot = self.chain(option.expiry, option.right, at)
        row = snapshot.row(option.strike)
        return None if row is None else snapshot.quotes.quote(row)

    def chain(self, expiry: date, right: Right, at: datetime | None = None) -> ChainSnapshot:
        return chain(expiry, self._gate(at), self.chains.get((expiry, right), ()), right)

    def expiries(self, kind: ExpiryKind, at: datetime | None = None) -> tuple[date, ...]:
        self._gate(at)
        return self.listed.get(kind, ())

    def close_trades(self, at: datetime | None = None) -> Mapping[datetime, Price]:
        self._gate(at)
        return {}

    def calendar(self) -> SessionCalendar:
        return CALENDAR
