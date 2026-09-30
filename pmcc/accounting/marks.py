"""Marks: what each held instrument is valued at on a bar (Spec › Ledger, ARCHITECTURE §9).

A mark is the bar's mid when the instrument has a valid quote. Without one, the last valid mid is
carried forward for marking only and flagged stale: a stale mark never fills and never triggers a
rule (DEC-27). The stock is marked the same way, at its BID/ASK mid (PO, DEC-23).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import final

from pmcc.accounting.events import Instrument
from pmcc.domain.money import Price


@final
@dataclass(frozen=True, slots=True)
class Mark:
    price: Price
    as_of: datetime  # the bar whose mid it is
    stale: bool


type Marks = Mapping[Instrument, Mark]


def carry(
    previous: Marks, fresh: Mapping[Instrument, Price | None], now: datetime
) -> dict[Instrument, Mark]:
    """This bar's marks for the instruments in `fresh`: each one's mid, or else its previous mark,
    now stale. An instrument with neither is left out; valuing it then raises."""
    marks: dict[Instrument, Mark] = {}
    for instrument, mid in fresh.items():
        if mid is not None:
            marks[instrument] = Mark(mid, now, stale=False)
        elif instrument in previous:
            last = previous[instrument]
            marks[instrument] = Mark(last.price, last.as_of, stale=True)
    return marks
