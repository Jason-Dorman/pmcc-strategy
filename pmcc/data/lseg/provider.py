"""`LsegProvider`: the `HistoryProvider` over `ld.get_history` (ARCHITECTURE §5.1, DEC-49, DEC-83).

One call: the answer comes back as long rows, and any error as one of the port's failure classes.
The classification follows what lseg-data 2.1.1 actually raises (DEC-83;
`tests/unit/data/test_lseg_contract.py` runs the library's own code to pin it):

- `get_history` asks the historical-pricing service once per RIC. If no RIC answers, it raises an
  `LDError` whose text starts "No data to return" and lists each failure's code: a service code
  such as `TS.Intraday.UserRequestError.90001` (a never-listed RIC) or an HTTP status.
- A transport failure (a timeout, a refused connection) also comes back as an `LDError`, holding
  only the original exception's text: no class, no cause, no code.
- A desktop session never leaves Opened on its own, so a dead or signed-out Workspace shows up only
  as failing requests, never as a state (LDG §4.2 covers only a session that fails to open).

So only an `LDError` whose every code is a no-data code counts as no data. Any other `LDError` is
transient: asked again, and an outage if it persists. Errors of other classes are raised while
lseg-data builds its frame, so the answer came back but can't be read.
"""

import re
from collections.abc import Sequence
from datetime import date

from pmcc.data.lseg.api import LsegApi
from pmcc.data.lseg.shapes import to_long
from pmcc.data.provider import (
    Interval,
    NoDataError,
    ProviderOutageError,
    RawHistory,
    TransientError,
    UnreadableAnswerError,
)

# How lseg-data 2.1.1 reports that no RIC in a request answered (`validate_responses`): the prefix,
# then "(code, message)" for each distinct failure.
NO_DATA_PREFIX = "No data to return"
_SERVICE_CODE = re.compile(r"\(([^,\s()]+), ")
# The historical-pricing service's own "your request found nothing" codes, e.g. 90001 for a RIC it
# doesn't know. Only these make a RIC unanswered; HTTP statuses and permission codes don't.
NO_DATA_CODE = re.compile(r"TS[A-Z]*\.(?:Interday|Intraday|QS)\.UserRequestError\.[0-9]{5}")

# Errors a dead or slow connection raises when they arrive unwrapped. httpx's transport errors
# derive from `TransportError`; they're matched by name, as httpx is lseg-data's dependency.
_TRANSPORT_ERRORS = (TimeoutError, ConnectionError)
_TRANSPORT_NAMES = frozenset({"TransportError"})


def is_open(state: object) -> bool:
    """Whether an `open_state` says Opened. Pending and Closed are not open (LDG §4.2)."""
    return getattr(state, "name", None) == "Opened"


def service_codes(message: str) -> tuple[str, ...]:
    """The failure codes in lseg-data's "No data to return" message; none for any other text."""
    if not message.startswith(NO_DATA_PREFIX):
        return ()
    return tuple(_SERVICE_CODE.findall(message))


class LsegProvider:
    """Asks LSEG for history through an open session. Build it with `lseg_session()`."""

    def __init__(self, api: LsegApi) -> None:
        self._api = api

    def is_open(self) -> bool:
        return is_open(self._api.session.get_default().open_state)

    def history(
        self,
        rics: Sequence[str],
        fields: Sequence[str],
        start: date,
        end_exclusive: date,
        interval: Interval,
    ) -> RawHistory:
        if not self.is_open():
            raise ProviderOutageError("the LSEG session is not open; nothing was requested")
        try:
            frame = self._api.get_history(
                universe=list(rics),
                fields=list(fields),
                interval=interval.value,
                start=start.isoformat(),
                end=end_exclusive.isoformat(),
            )
        except Exception as exc:
            raise self._classify(exc) from exc
        return RawHistory(interval, to_long(frame, rics, fields, interval))

    def _classify(self, exc: Exception) -> Exception:
        described = f"{type(exc).__name__}: {exc}"
        if not self.is_open():
            return ProviderOutageError(f"the LSEG session closed during a request ({described})")
        if _is_ld_error(exc):
            return _service_failure(str(exc))
        if _is_transport(exc):
            return TransientError(described)
        return UnreadableAnswerError(str(exc), type(exc).__name__)


def _service_failure(message: str) -> Exception:
    codes = service_codes(message)
    if codes and all(NO_DATA_CODE.fullmatch(code) for code in codes):
        return NoDataError(message, codes)
    return TransientError(f"LDError: {message}")


def _is_ld_error(exc: BaseException) -> bool:
    # Matched by name: lseg.data is imported only when a session opens, and tests use a fake.
    return any(cls.__name__ == "LDError" for cls in type(exc).__mro__)


def _is_transport(exc: BaseException) -> bool:
    names = {cls.__name__ for cls in type(exc).__mro__}
    return isinstance(exc, _TRANSPORT_ERRORS) or bool(names & _TRANSPORT_NAMES)
