"""DEC-83: the service's real error answers, recorded before any pull relies on the assumed codes.

- A never-listed RIC (an odd strike on last week's expiry), hourly and daily, in both forms.
- A live contract asked in the caret form (the other side of DEC-09).
- A field the RIC doesn't carry: `SETTLE`, since US listed equity options have no settlement
  price (LDG §4.7). NVDA's first probe found LSEG answers it with no values rather than an error,
  so a field name the service can't know is asked too.
- Batches: a listed RIC with a never-listed one, hourly and daily; and a listed pair asked for a
  field they don't carry.

Each answer is recorded as the service gave it (`ask`). The fetch treats a guessed RIC as
unanswered only on a no-data code (`TS.*.UserRequestError.*`). A never-listed RIC that fails with
any other code is asked again and ends as an outage, as it would in a fetch; the CLI prints its
text, and widening the codes is decided in DEC-83. One that answers anyway stops the report here.
"""

from datetime import date

from pmcc.data.fetch import BarRequest
from pmcc.data.probe.context import QUOTES, Json, Probe, ask, over
from pmcc.data.provider import Interval
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_DOLLAR, Price

NOT_CARRIED = "SETTLE"
UNKNOWN_FIELD = "PMCC_NO_SUCH_FIELD"
ODD_STRIKE = Price(3_700)  # + $0.37: no listed strike grid has it
NEXT_STRIKE = Price(10 * UNITS_PER_DOLLAR)
NEVER_LISTED = (
    "never_listed_hourly_expired_form",
    "never_listed_hourly_live_form",
    "never_listed_daily_expired_form",
    "never_listed_daily_live_form",
)


def probe_errors(probe: Probe, listed: OptionId, expired: date) -> Json:
    """`listed` is a live, listed call; `expired` a weekly expiry at least a week before the last
    session, so its contracts answer to the caret form (LDG §3)."""
    asked = {
        name: ask(probe, rics, request)
        for name, (rics, request) in _asks(probe, listed, expired).items()
    }
    return {
        "asks": {name: a.record for name, a in asked.items()},
        "codes_seen": sorted({code for a in asked.values() for code in a.codes}),
        "never_listed_is_no_data": all(asked[name].outcome == "no_data" for name in NEVER_LISTED),
    }


def _asks(probe: Probe, listed: OptionId, expired: date) -> dict[str, tuple[list[str], BarRequest]]:
    never = OptionId(probe.root, expired, Right.CALL, listed.strike + ODD_STRIKE)
    never_live = OptionId(probe.root, listed.expiry, Right.CALL, listed.strike + ODD_STRIKE)
    neighbour = OptionId(probe.root, listed.expiry, Right.CALL, listed.strike + NEXT_STRIKE)
    week, recent = probe.calendar.week_sessions(expired), probe.recent(5)
    good = build_ric(listed, RicForm.LIVE)
    hourly, daily = Interval.HOURLY, Interval.DAILY
    return {
        "never_listed_hourly_expired_form": (
            [build_ric(never, RicForm.EXPIRED)],
            over(week, QUOTES, hourly),
        ),
        "never_listed_hourly_live_form": (
            [build_ric(never, RicForm.LIVE)],
            over(week, QUOTES, hourly),
        ),
        "never_listed_daily_expired_form": (
            [build_ric(never, RicForm.EXPIRED)],
            over(week, QUOTES, daily),
        ),
        "never_listed_daily_live_form": (
            [build_ric(never, RicForm.LIVE)],
            over(week, QUOTES, daily),
        ),
        "live_contract_in_caret_form": (
            [build_ric(listed, RicForm.EXPIRED)],
            over(recent, QUOTES, hourly),
        ),
        "field_not_carried_hourly": ([good], over(recent, ("TRDPRC_1", NOT_CARRIED), hourly)),
        "field_not_carried_daily": ([good], over(recent, ("TRDPRC_1", NOT_CARRIED), daily)),
        "unknown_field_hourly": ([good], over(recent, ("TRDPRC_1", UNKNOWN_FIELD), hourly)),
        "batch_hourly_listed_and_never_listed": (
            [good, build_ric(never_live, RicForm.LIVE)],
            over(recent, QUOTES, hourly),
        ),
        "batch_daily_listed_and_never_listed": (
            [good, build_ric(never_live, RicForm.LIVE)],
            over(recent, QUOTES, daily),
        ),
        "batch_hourly_field_not_carried": (
            [good, build_ric(neighbour, RicForm.LIVE)],
            over(recent, ("BID", NOT_CARRIED), hourly),
        ),
    }
