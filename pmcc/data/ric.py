"""Option RICs and OCC symbols (Spec › RIC builder; LDG §3; DEC-01, DEC-45, DEC-82).

A RIC is `{ROOT}{M}{DD}{YY}{SSSSS}.U`, plus `^{M}{YY}` in the expired form:

- `M` codes the expiry month and the right: calls `A`-`L`, puts `M`-`X`, January to December.
  The caret always takes the call letter, for puts too.
- `DD` is the expiry day, zero-padded (DEC-01); the parser also reads it unpadded.
- `SSSSS` is the strike in cents, so a RIC can't carry a strike above $999.99.
"""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price

MAX_STRIKE = Price(99_999 * UNITS_PER_CENT)  # $999.99, five digits of cents

_OCC_ROOT_WIDTH = 6
_OCC_MAX_STRIKE_MILLS = 99_999_999  # eight digits of $0.001

_MONTH_LETTERS = {Right.CALL: "ABCDEFGHIJKL", Right.PUT: "MNOPQRSTUVWX"}
_LETTER_CODES = {
    letter: (right, month)
    for right, letters in _MONTH_LETTERS.items()
    for month, letter in enumerate(letters, start=1)
}
# The month letter is the last letter before the digits, so a root may hold digits, as `OptionId`
# allows. Those digits split from the right: strike (5), year (2), then a one- or two-digit day.
_RIC = re.compile(
    r"(?P<root>[A-Z][A-Z0-9]*)(?P<letter>[A-X])"
    r"(?P<day>[0-9]{1,2})(?P<year>[0-9]{2})(?P<strike>[0-9]{5})\.U"
    r"(?P<caret>\^[A-X][0-9]{2})?"
)


class RicForm(StrEnum):
    """The two spellings of one contract. The value is what `ric_form_used` records (DEC-45)."""

    LIVE = "live"  # {ROOT}{M}{DD}{YY}{SSSSS}.U
    EXPIRED = "expired"  # the live form plus ^{M}{YY}


@final
@dataclass(frozen=True, slots=True)
class ParsedRic:
    """What a RIC names: the contract, and the form it was spelled in."""

    option: OptionId
    form: RicForm


def forms_to_ask(expiry: date, fetch_date: date) -> tuple[RicForm, ...]:
    """The forms to ask LSEG for a contract, in order (DEC-45).

    A contract expiring on or after the fetch date is live, so it gets no caret. An expired one is
    asked with the caret first, then live for whatever didn't answer: a contract switches from one
    form to the other over several days after it expires (LDG §3).
    """
    if expiry >= fetch_date:
        return (RicForm.LIVE,)
    return (RicForm.EXPIRED, RicForm.LIVE)


def build_ric(option: OptionId, form: RicForm) -> str:
    """The RIC of `option` in `form`. Raises if its strike or year doesn't fit the grammar.

    `form` may also be a form's value read back as text ("expired" from a manifest); anything
    else raises rather than quietly building the live form.
    """
    form = RicForm(form)
    expiry = option.expiry
    live = (
        f"{option.root}{_month_letter(option.right, expiry)}"
        f"{_day_field(expiry)}{_year_field(expiry)}{_strike_field(option)}.U"
    )
    return live + _caret(expiry) if form is RicForm.EXPIRED else live


def parse_ric(ric: str) -> ParsedRic:
    """The contract and form `ric` names, in either day spelling. Anything else raises."""
    match = _RIC.fullmatch(ric)
    if match is None:
        raise ValueError(f"not an option RIC: {ric!r}")
    right, month = _LETTER_CODES[match["letter"]]
    try:
        expiry = date(2000 + int(match["year"]), month, int(match["day"]))
        strike = Price(int(match["strike"]) * UNITS_PER_CENT)
        option = OptionId(match["root"], expiry, right, strike)
    except ValueError as exc:
        raise ValueError(f"not an option RIC: {ric!r} ({exc})") from exc
    return ParsedRic(option, _form(match["caret"], expiry, ric))


def occ_symbol(option: OptionId) -> str:
    """The OCC symbol, e.g. `QQQ   260918C00710000` (LDG §3).

    The root is left-justified in six characters (the padding is part of the symbol), then
    YYMMDD, C or P, and the strike in $0.001 as eight digits.
    """
    if len(option.root) > _OCC_ROOT_WIDTH:
        raise ValueError(f"an OCC root has at most {_OCC_ROOT_WIDTH} characters: {option.root!r}")
    mills = option.strike_cents * 10
    if mills > _OCC_MAX_STRIKE_MILLS:
        raise ValueError(f"strike {option.strike.to_dollars():.2f} is too wide for an OCC symbol")
    expiry = option.expiry
    return (
        f"{option.root:<{_OCC_ROOT_WIDTH}}{_year_field(expiry)}{expiry:%m%d}"
        f"{option.right.value}{mills:08d}"
    )


def _month_letter(right: Right, expiry: date) -> str:
    return _MONTH_LETTERS[right][expiry.month - 1]


def _day_field(expiry: date) -> str:
    # Zero-padded: the earlier project measured that only `05` resolves (DEC-01, LDG §3). If every
    # strike of an expiry dated the 1st-9th comes back unanswered, check this spelling first.
    return f"{expiry.day:02d}"


def _year_field(expiry: date) -> str:
    if not 2000 <= expiry.year <= 2099:
        raise ValueError(f"a two-digit year needs an expiry in 2000-2099: {expiry}")
    return f"{expiry.year % 100:02d}"


def _strike_field(option: OptionId) -> str:
    if option.strike > MAX_STRIKE:
        raise ValueError(
            f"strike {option.strike.to_dollars():.2f} does not fit the RIC's five-digit strike "
            f"field (max {MAX_STRIKE.to_dollars():.2f})"
        )
    return f"{option.strike_cents:05d}"


def _caret(expiry: date) -> str:
    return f"^{_month_letter(Right.CALL, expiry)}{_year_field(expiry)}"


def _form(caret: str | None, expiry: date, ric: str) -> RicForm:
    if caret is None:
        return RicForm.LIVE
    if caret != _caret(expiry):
        raise ValueError(
            f"a RIC's caret is the call letter and year of its expiry, {_caret(expiry)}: {ric!r}"
        )
    return RicForm.EXPIRED
