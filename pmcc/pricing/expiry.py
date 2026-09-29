"""Time to expiry and days to expiry (PO, DEC-24).

- **T** is calendar time from the decision to the expiry session's close (16:00 ET, or 13:00 on a
  half-day), in years, ACT/365: elapsed seconds ÷ 31,536,000. It is zero at the close bar and
  negative after it.
- **DTE** (E-L2, X-L2) is calendar days from the decision's ET date to the expiry date.
"""

from datetime import UTC, date, datetime

from pmcc.domain.clock import to_et
from pmcc.domain.sessions import Session

SECONDS_PER_YEAR = 365 * 24 * 3600


def years_to_expiry(now: datetime, expiry: Session) -> float:
    """T in years from `now` to `expiry`'s close. `now` must be tz-aware.

    Both ends go to UTC first: Python subtracts two times in the same zone by wall clock, which
    would lose or gain the hour of a clock change in between.
    """
    elapsed = expiry.close_bar_end.astimezone(UTC) - to_et(now).astimezone(UTC)
    return elapsed.total_seconds() / SECONDS_PER_YEAR


def days_to_expiry(now: datetime, expiry: date) -> int:
    """Calendar days from `now`'s ET date to `expiry`."""
    return (expiry - to_et(now).date()).days
