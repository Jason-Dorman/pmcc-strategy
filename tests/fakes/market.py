"""`FakeMarket`: a `HistoryProvider` over a small synthetic market, for code that consumes the port.

The probes (P1-04) ask many dated questions of one market, which `FakeLseg`'s fixed bars can't
answer. This fake answers at the port instead, the way `LsegProvider` answers over lseg-data
(DEC-83; FakeProvider and the contract test pin that behaviour):

- Each RIC answers with its bars from `start` up to `end_exclusive`, or fails on its own when it
  was never listed. A field it doesn't carry is left out of its answer (P1-04 probes, DEC-83).
- If no RIC answered, `NoDataError` with each distinct code, in lseg-data's message format.
- An hourly batch holding a RIC that failed can't be read (`UnreadableAnswerError`, the
  `UniverseContainer` TypeError); a daily batch answers without it.
- Several RICs whose answers each carry one of several fields asked can't be attributed either:
  lseg-data builds flat RIC columns, which the reader refuses (DEC-83).
- A Workspace that dies or signs out shows up only as `TransientError`: a desktop session never
  leaves Opened, so `LsegProvider` sees failing requests, never a closed session (DEC-83).
- There are no bars on or after `today`.

The market: one stock, answering under every RIC in `stocks`, whose close alternates 1% either
side of `spot` day by day; weekly and monthly calls and puts on a $1 grid within $20 of spot and a
$5 grid beyond. Hourly bars exist from `hourly_from`; an option lists 280 days before it expires. An
expired contract answers only in the caret form and a live one only in the live form. In every bar,
prices step by $0.01 an hour, so only the close bar (starting 15:00 ET) matches the daily close and
closing quote.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

import polars as pl

from pmcc.data.provider import (
    Interval,
    NoDataError,
    RawHistory,
    TransientError,
    UnreadableAnswerError,
    raw_schema,
)
from pmcc.data.ric import RicForm, parse_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId
from pmcc.domain.sessions import Session

ROOT = "NVDA"
STOCKS = ("NVDA.O", "NVDA.N", "NVDA.P", "NVDA.A", "NVDA.Z")  # as LSEG answered for NVDA
CARRIED = frozenset(
    {"BID", "ASK", "TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1", "ACVOL_UNS", "NUM_MOVES"}
)
NEAR_MONEY_DOLLARS = 20
LISTED_DAYS = 280
ODD_CENTS = 37  # the probe's never-listed strikes end in $0.37
STOCK_HOURS = range(4, 20)  # ET bar starts 04:00-19:00
OPTION_HOURS = range(9, 17)  # 09:00-16:00, the 16:00 stub included
PRINT_HOUR = 12  # options trade once a day, in the 12:00 bar
DEAD_WORKSPACE = (  # what LsegProvider raises for a signed-out Workspace (DEC-83)
    "LDError: No data to return, please check errors: ERROR: No successful response.\n"
    "(401, Unauthorized)"
)

type Row = dict[str, object]


def not_found(interval: Interval) -> str:
    """LSEG's code for a never-listed RIC (P1-04 probes, DEC-83)."""
    number = "90001" if interval is Interval.HOURLY else "70005"
    return f"TS.{_kind(interval)}.UserRequestError.{number}"


def _kind(interval: Interval) -> str:
    return "Intraday" if interval is Interval.HOURLY else "Interday"


@dataclass
class FakeMarket:
    """A synthetic market behind the `HistoryProvider` port. See the module docstring.

    - `dies_after`: requests served before Workspace dies; every later one is transient.
    - `never_listed_transient`: never-listed RICs fail without a no-data code (transient).
    - `odd_strikes_answer`: intervals in which the probe's never-listed $x.37 strikes answer.
    - `empty_fields`: fields every RIC answers with no values.
    - `traded_closed` and `untraded`: days the stock trades although the table closes them, and
      table sessions it doesn't trade, so its tape disagrees with the calendar.
    """

    calendar: SessionCalendar
    today: date
    spot: float = 180.0
    hourly_from: date = date(2025, 1, 1)
    stocks: Sequence[str] = STOCKS
    dies_after: int | None = None
    never_listed_transient: bool = False
    odd_strikes_answer: Collection[Interval] = ()
    empty_fields: Collection[str] = ()
    traded_closed: Collection[date] = ()
    untraded: Collection[date] = ()
    calls: int = 0
    requests: list[tuple[tuple[str, ...], tuple[str, ...], date, date, Interval]] = field(
        default_factory=list[tuple[tuple[str, ...], tuple[str, ...], date, date, Interval]]
    )

    def history(
        self,
        rics: Sequence[str],
        fields: Sequence[str],
        start: date,
        end_exclusive: date,
        interval: Interval,
    ) -> RawHistory:
        self.calls += 1
        if self.dies_after is not None and self.calls > self.dies_after:
            raise TransientError(DEAD_WORKSPACE)
        self.requests.append((tuple(rics), tuple(fields), start, end_exclusive, interval))
        answers = {ric: self._answer(ric, fields, start, end_exclusive, interval) for ric in rics}
        failed = {ric: a for ric, a in answers.items() if isinstance(a, str)}
        if len(failed) == len(answers):
            raise self._nobody_answered(failed, interval)
        if failed and interval is Interval.HOURLY:
            raise UnreadableAnswerError(
                "'UniverseContainer' object is not subscriptable", "TypeError"
            )
        rows = [row for a in answers.values() if not isinstance(a, str) for row in a]
        if len(rics) > 1 and len(set(fields)) > 1 and len(set(fields) & CARRIED) == 1:
            raise UnreadableAnswerError("RIC columns for several fields asked", "Unattributable")
        frame = pl.DataFrame(rows, schema=raw_schema(interval))
        return RawHistory(interval, frame.sort("ric", "field", "bar_start"))

    def spot_on(self, day: date) -> float:
        return self.spot * (1 + 0.01 * (-1) ** day.toordinal())

    def _nobody_answered(self, failed: dict[str, str], interval: Interval) -> Exception:
        if self.never_listed_transient and not_found(interval) in failed.values():
            return TransientError("LDError: (TS.Intraday.SomethingElse.12345, unexpected)")
        codes = tuple(dict.fromkeys(failed.values()))
        heads = ", ".join(f"({code}, {ric.split('.')[0]})" for ric, code in failed.items())
        message = f"No data to return, please check errors: ERROR: No successful response.\n{heads}"
        return NoDataError(message, codes)

    def _answer(
        self, ric: str, fields: Sequence[str], start: date, end: date, interval: Interval
    ) -> list[Row] | str:
        option = self._option(ric, interval)
        if ric not in self.stocks and option is None:
            return not_found(interval)
        days = [
            s for s in self._sessions(start, end, option) if self._has_bars(s.day, option, interval)
        ]
        return [row for s in days for row in self._rows(ric, fields, s, option, interval)]

    def _option(self, ric: str, interval: Interval) -> OptionId | None:
        try:
            parsed = parse_ric(ric)
        except ValueError:
            return None
        option, expiry = parsed.option, parsed.option.expiry
        live = expiry >= self.today
        if option.root != ROOT or (parsed.form is RicForm.LIVE) != live:
            return None
        if not (self._is_expiry(expiry) and self._on_grid(option, interval)):
            return None
        return option

    def _is_expiry(self, expiry: date) -> bool:
        if not self.calendar.is_session(expiry):
            return False
        weekly = self.calendar.week_final(expiry).day == expiry
        return weekly or self.calendar.monthly_expiry(expiry.year, expiry.month) == expiry

    def _on_grid(self, option: OptionId, interval: Interval) -> bool:
        if option.strike_cents % 100 == ODD_CENTS:
            return interval in self.odd_strikes_answer
        near = abs(option.strike_cents / 100 - self.spot) <= NEAR_MONEY_DOLLARS
        return option.strike_cents % (100 if near else 500) == 0

    def _sessions(
        self, start: date, end_exclusive: date, option: OptionId | None
    ) -> tuple[Session, ...]:
        first = max(start, self.calendar.first_day)
        last = min(end_exclusive, self.today) - timedelta(days=1)
        if first > last:
            return ()
        sessions = [s for s in self.calendar.sessions(first, last) if s.day not in self.untraded]
        if option is None:
            sessions += [Session(d) for d in self.traded_closed if first <= d <= last]
        return tuple(sorted(sessions))

    def _has_bars(self, day: date, option: OptionId | None, interval: Interval) -> bool:
        if interval is Interval.HOURLY and day < self.hourly_from:
            return False
        if option is None:
            return day not in self.untraded
        return option.expiry - timedelta(days=LISTED_DAYS) <= day <= option.expiry

    def _rows(
        self,
        ric: str,
        fields: Sequence[str],
        session: Session,
        option: OptionId | None,
        interval: Interval,
    ) -> list[Row]:
        close_hour = session.close.hour - 1
        if interval is Interval.DAILY:
            stamps: list[tuple[object, int]] = [(session.day, close_hour)]
        else:
            hours = STOCK_HOURS if option is None else OPTION_HOURS
            stamps = [(_utc(session.day, h), h) for h in hours]
        rows: list[Row] = []
        for stamp, hour in stamps:
            values = self._values(session.day, hour - close_hour, option, interval)
            rows.extend(
                {"bar_start": stamp, "ric": ric, "field": f, "value": values[f]}
                for f in fields
                if f in CARRIED and f not in self.empty_fields and values.get(f) is not None
            )
        return rows

    def _values(
        self, day: date, offset: int, option: OptionId | None, interval: Interval
    ) -> dict[str, float | None]:
        """A bar's values; `offset` is its start in hours after the close bar's start."""
        spot = self.spot_on(day)
        if option is None:
            last = spot + 0.01 * offset
            high, low = (
                (spot + 1, spot - 1) if interval is Interval.DAILY else (last + 0.5, last - 0.5)
            )
            return {
                "TRDPRC_1": last,
                "OPEN_PRC": last,
                "HIGH_1": high,
                "LOW_1": low,
                "BID": last - 0.01,
                "ASK": last + 0.01,
                "ACVOL_UNS": 1000.0,
                "NUM_MOVES": 10.0,
            }
        intrinsic = max(0.0, spot - option.strike_cents / 100)
        mid = intrinsic + 1 + 0.01 * (option.expiry - day).days
        bid = mid - 0.05 + 0.01 * offset
        traded = interval is Interval.DAILY or offset == PRINT_HOUR - 15
        trade = round(mid, 4) if traded else None
        return {
            "BID": round(bid, 4),
            "ASK": round(bid + 0.10, 4),
            "TRDPRC_1": trade,
            "OPEN_PRC": trade,
            "HIGH_1": trade,
            "LOW_1": trade,
            "ACVOL_UNS": 5.0 if traded else None,
            "NUM_MOVES": 20.0,
        }


def _utc(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET).astimezone(UTC)
