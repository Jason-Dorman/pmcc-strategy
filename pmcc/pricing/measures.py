"""The measures the rules read, as the PO settled them on 2026-09-28 (P2-03).

- **Spot and close (DEC-23):** spot on a bar is the underlying's TRDPRC_1 in that bar, and a
  session's close is the spot of its close bar (16:00 ET, or 13:00 on a half-day). A short is ITM
  at expiry only if that close is above its strike; a close on the strike is OTM, as OCC
  auto-exercises only from $0.01 in the money.
- **ATM strike, ATM IV, EM (DEC-25):** the ATM strike is the listed strike nearest spot, the lower
  on a tie. ATM IV is the ATM *call's* IV. EM is the front week's ATM call mid + ATM put mid; with
  either quote missing it is unavailable.
- **RV20 (DEC-26):** the sample standard deviation of the last 20 daily log returns * √252, from
  the 21 closes of the sessions before the current one.

Which strikes are listed, and which quotes are fresh, is MarketView's (P3-02); these functions
take what it hands them.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime

import numpy as np

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.domain.sessions import Session
from pmcc.pricing.chain import PricedQuotes

RV_RETURNS = 20
TRADING_DAYS_PER_YEAR = 252


def atm_strike(strikes: Iterable[Price], spot: Price) -> Price | None:
    """The strike nearest `spot`, the lower on a tie; None with no strikes."""
    return min(strikes, key=lambda k: (abs(k.units - spot.units), k.units), default=None)


def atm_iv(calls: PricedQuotes, atm: Price) -> float | None:
    """The ATM call's IV on this bar, or None if it has no row or its IV didn't solve."""
    row = calls.at(atm)
    return None if row is None or not calls.eligible[row] else float(calls.iv[row])


def expected_move(call: Quote | None, put: Quote | None) -> Price | None:
    """The ATM straddle's mid: call mid + put mid, each rounded as a fill is (DEC-44)."""
    return None if call is None or put is None else call.mid + put.mid


def session_close(session: Session, last_trades: Mapping[datetime, Price]) -> Price | None:
    """The TRDPRC_1 of `session`'s close bar, keyed by `bar_end`; None if it has none."""
    return last_trades.get(session.close_bar_end)


def itm_at_expiry(closing_spot: Price, strike: Price) -> bool:
    """X-S4/X-S5: a call is ITM at expiry only if the close is above its strike."""
    return closing_spot > strike


def realized_vol(closes: Sequence[Price]) -> float:
    """The sample standard deviation of the closes' daily log returns, annualized by √252."""
    logs = np.log(np.array([c.units for c in closes], dtype=np.float64))
    return float(np.std(np.diff(logs), ddof=1)) * math.sqrt(TRADING_DAYS_PER_YEAR)


def rv20(calendar: SessionCalendar, now: datetime,
         last_trades: Mapping[datetime, Price]) -> float | None:  # fmt: skip
    """RV20 at `now` from the closes of the 21 sessions before `now`'s session, never its own.
    None if any of those closes is missing."""
    sessions = calendar.sessions_before(to_et(now).date(), RV_RETURNS + 1)
    closes = [session_close(s, last_trades) for s in sessions]
    present = [c for c in closes if c is not None]
    return realized_vol(present) if len(present) == len(closes) else None
