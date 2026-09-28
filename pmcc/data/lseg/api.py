"""The slice of the `lseg.data` module this adapter calls, as a protocol (DEC-83).

The real module satisfies it, and so does the test fake, so the adapter is tested with no
network. Keep it to what `pmcc/data/lseg/` actually calls, like the stubs in `typings/lseg/`.
"""

from collections.abc import Iterable
from datetime import date, datetime
from typing import Protocol


class LsegSession(Protocol):
    @property
    def open_state(self) -> object: ...


class LsegSessions(Protocol):
    def get_default(self) -> LsegSession: ...


class LsegApi(Protocol):
    @property
    def session(self) -> LsegSessions: ...

    def open_session(
        self,
        name: str | None = None,
        app_key: str | None = None,
        config_name: str | None = None,
    ) -> object: ...

    def close_session(self) -> None: ...

    def get_history(
        self,
        universe: str | Iterable[str],
        fields: str | Iterable[str] | None = None,
        interval: str | None = None,
        start: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
    ) -> object: ...
