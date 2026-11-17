"""Reading Sanji's book (LIVE-SPEC › Data, Trade rules; L2-02; L-B1, L-B2; PO, LD-14).

Sanji writes three files into the repo: `price_history.json` at the root (the course's price job,
daily bars per tracked conid), and `positions.json` and `fills.json` (under `mkt/` on the order
page, at the root in the assignment: both are looked for, `mkt/` first, LD-04).

- **L-B1, the book is current:** the latest date in `price_history.json`, over every instrument
  in it, is the last completed session. Every instrument counts, so NVDA's entry, tracked since
  2026-11-14 and empty until the price job's next run, doesn't make a current book look stale.
- **L-B2, the book is readable:** with no `positions.json` and no `fills.json`, nothing has ever
  filled, and the book is cash alone: the starting cash (LD-09). Sanji wasn't resolving orders
  when this was built ("Sanji does not resolve these orders yet", the order page), so its formats
  were never seen; once either file appears, it is unreadable until its format is known and this
  module reads it (L5-01). An unreadable book is never guessed at (PO, LD-14): the run writes no
  new order and fails.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import cast, final

from pmcc.domain.instruments import OptionId
from pmcc.domain.money import Money, Price
from pmcc.live.names import SANJI_DIR

PRICE_HISTORY = "price_history.json"
POSITIONS = "positions.json"
FILLS = "fills.json"


class BookError(Exception):
    """The book can't be trusted: stale (L-B1) or unreadable (L-B2). No new order (LD-14)."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(f"{rule}: {message}")
        self.rule = rule


class WheelState(StrEnum):
    CASH = "cash"
    PUT = "put"
    SHARES = "shares"
    CALL = "call"


@final
@dataclass(frozen=True, slots=True)
class Book:
    """The wheel's position as Sanji's files show it."""

    state: WheelState
    cash: Money
    cost_basis: Price | None = None  # per share, while shares are held
    short_option: OptionId | None = None


def sanji_file(root: Path, name: str) -> Path | None:
    """Where Sanji's `name` is: under `mkt/` first, then the root; None if in neither."""
    for path in (root / SANJI_DIR / name, root / name):
        if path.exists():
            return path
    return None


def last_priced_session(root: Path) -> date:
    """The latest date in `price_history.json`, over every instrument. Raises `BookError` (L-B1)
    if the file is missing, unreadable, or holds no bars."""
    path = root / PRICE_HISTORY
    if not path.is_file():
        raise BookError("L-B1", f"no {PRICE_HISTORY}: Sanji's price job hasn't written one")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        days = [date.fromisoformat(day) for entry in _entries(data) for day in _bars(entry)]
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as exc:
        raise BookError("L-B1", f"{PRICE_HISTORY} can't be read: {exc}") from None
    if not days:
        raise BookError("L-B1", f"{PRICE_HISTORY} holds no daily bars")
    return max(days)


def check_current(root: Path, last_completed: date) -> str | None:
    """L-B1: the book is as of `last_completed`; None when it is. While Sanji has written no book
    (neither positions nor fills), it has resolved nothing, so the cash book can't have moved: a
    stale price file is then a warning, returned, and the night goes ahead (PO, LD-32). Once it
    has, a stale price file raises `BookError`."""
    priced = last_priced_session(root)
    if priced == last_completed:
        return None
    behind = (
        f"{PRICE_HISTORY} runs to {priced}, but the last completed session is "
        f"{last_completed}: Sanji hasn't caught up"
    )
    if all(sanji_file(root, name) is None for name in (POSITIONS, FILLS)):
        return f"{behind}; it has resolved nothing, so the cash book can't have moved"
    raise BookError("L-B1", f"{behind}, so the book may be stale")


def read_book(root: Path, starting_cash: Money) -> Book:
    """L-B2: the book from Sanji's files. Raises `BookError` when it can't be read as one of the
    four states."""
    found = [path for name in (POSITIONS, FILLS) if (path := sanji_file(root, name)) is not None]
    if not found:
        return Book(WheelState.CASH, starting_cash)
    names = ", ".join(str(path.relative_to(root)) for path in found)
    raise BookError(
        "L-B2",
        f"Sanji has written {names}, whose format isn't known yet (Sanji wasn't resolving orders "
        "when the live wheel was built); read it before trading on it (L5-01)",
    )


def _entries(data: object) -> list[Mapping[str, object]]:
    if not isinstance(data, dict):
        raise TypeError("expected an object of conids")
    entries = cast(dict[str, object], data).values()
    if not all(isinstance(entry, dict) for entry in entries):
        raise TypeError("every conid's entry must be an object")
    return [cast(Mapping[str, object], entry) for entry in entries]


def _bars(entry: Mapping[str, object]) -> list[str]:
    history = entry.get("price_history", {})
    if not isinstance(history, dict):
        raise TypeError("price_history must be an object of dates")
    return list(cast(dict[str, object], history))
