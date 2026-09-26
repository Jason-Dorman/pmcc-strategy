"""ET time helpers and `bar_end` (DEC-06, ARCHITECTURE §4.2).

LSEG stamps intraday bars tz-naive UTC at the bar's start (LDG §4.8). After load, the only
timestamp is `bar_end` in America/New_York, and it is the decision time.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BAR = timedelta(hours=1)


def to_et(t: datetime) -> datetime:
    """Convert a tz-aware time to ET. A naive time is refused: its zone would be a guess."""
    if t.utcoffset() is None:
        raise ValueError(f"expected a tz-aware datetime, got naive {t.isoformat()}")
    return t.astimezone(ET)


def at_et(day: date, clock: time) -> datetime:
    """The ET wall-clock time `clock` on `day`."""
    return datetime.combine(day, clock, tzinfo=ET)


def bar_end(bar_start: datetime) -> datetime:
    """`bar_start + 1h` in ET. A naive start is LSEG's UTC stamp; the hour is elapsed time."""
    start = bar_start.replace(tzinfo=UTC) if bar_start.tzinfo is None else bar_start
    return (start.astimezone(UTC) + BAR).astimezone(ET)
