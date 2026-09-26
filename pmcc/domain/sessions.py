"""Trading sessions and their session bars (DEC-06, ARCHITECTURE §4.2).

A session bar is an hourly bar whose ET start is 09:00 through the hour before the close, so its
`bar_end` runs from 10:00 to the close (16:00, or 13:00 on a half-day). Extended-hours bars and
the post-close stub belong to no session. Which days trade, and when they close, is the
calendar's job (P1-06); a `Session` only knows its own day.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import final

from pmcc.domain.clock import at_et, to_et

FIRST_BAR_END = time(10)  # the 09:00-10:00 ET bar
REGULAR_CLOSE = time(16)
HALF_DAY_CLOSE = time(13)


def _on_the_hour(t: time) -> bool:
    return t.tzinfo is None and t == time(t.hour)


@final
@dataclass(frozen=True, order=True, slots=True)
class Session:
    day: date
    close: time = REGULAR_CLOSE

    def __post_init__(self) -> None:
        if not (_on_the_hour(self.close) and FIRST_BAR_END <= self.close <= REGULAR_CLOSE):
            raise ValueError(f"session close must be on the hour, 10:00-16:00 ET: {self.close}")

    @property
    def is_half_day(self) -> bool:
        return self.close < REGULAR_CLOSE

    @property
    def close_bar_end(self) -> datetime:
        """The close bar's end: the session close, and the expiry instant (DEC-24)."""
        return at_et(self.day, self.close)

    def bar_ends(self) -> tuple[datetime, ...]:
        hours = range(FIRST_BAR_END.hour, self.close.hour + 1)
        return tuple(at_et(self.day, time(h)) for h in hours)

    def contains(self, bar_end: datetime) -> bool:
        """Whether the bar ending at `bar_end` is one of this session's bars."""
        return to_et(bar_end) in self.bar_ends()

    def is_close_bar(self, bar_end: datetime) -> bool:
        return to_et(bar_end) == self.close_bar_end


def session_of(bar_end: datetime, sessions: Mapping[date, Session]) -> Session | None:
    """The session a bar belongs to, or None for extended-hours bars and non-trading days."""
    session = sessions.get(to_et(bar_end).date())
    return session if session is not None and session.contains(bar_end) else None
