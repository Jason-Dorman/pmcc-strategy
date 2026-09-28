"""DEC-13: which of the spec's fields hourly bars carry, on an option RIC and on the stock RIC.

LDG §4.6 said a field a RIC doesn't carry fails the whole request; the P1-04 probes found LSEG
leaves it out of the answer instead (DEC-83). Either way, each field is asked on its own, paired
with TRDPRC_1, over the last 5 sessions. A field is `carried` when it came back with values,
`empty` when the request answered but the field had none (how a field the RIC lacks looks), and
`refused` when the service answered with a no-data code (its record keeps the answer).
"""

from collections.abc import Sequence

from pmcc.data.probe.context import Json, Probe, ask, over
from pmcc.data.provider import Interval
from pmcc.domain.sessions import Session

# Spec › Fields and bars; the stock also needs BID/ASK for the stock fills after X-S5 (DEC-13).
OPTION_FIELDS = ("BID", "ASK", "TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1", "ACVOL_UNS", "NUM_MOVES")
STOCK_FIELDS = ("TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1", "BID", "ASK", "ACVOL_UNS", "NUM_MOVES")
SESSIONS = 5


def probe_fields(probe: Probe, stock_ric: str, option_ric: str) -> Json:
    sessions = probe.recent(SESSIONS)
    return {
        "option": each_field(probe, option_ric, OPTION_FIELDS, sessions),
        "stock": each_field(probe, stock_ric, STOCK_FIELDS, sessions),
    }


def each_field(probe: Probe, ric: str, fields: Sequence[str], sessions: Sequence[Session]) -> Json:
    records: dict[str, Json] = {}
    status: dict[str, str] = {}
    for name in fields:
        pair = ("TRDPRC_1",) if name == "TRDPRC_1" else ("TRDPRC_1", name)
        asked = ask(probe, [ric], over(sessions, pair, Interval.HOURLY))
        values = 0 if asked.history is None else asked.history.rows.filter(field=name).height
        status[name] = _status(asked.outcome, values)
        records[name] = {**asked.record, "status": status[name], "values": values}
    return {
        "ric": ric,
        "carried": [f for f in fields if status[f] == "carried"],
        "empty": [f for f in fields if status[f] == "empty"],
        "refused": [f for f in fields if status[f] == "refused"],
        "asks": records,
    }


def _status(outcome: str, values: int) -> str:
    if outcome != "answered":
        return "refused"
    return "carried" if values else "empty"
