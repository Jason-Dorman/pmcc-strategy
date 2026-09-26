# Minimal stub for lseg-data 2.1.1 (DEC-42). Extend it when pmcc/data/lseg/ needs more.
from collections.abc import Iterable
from datetime import date, datetime
from enum import Enum

from pandas import DataFrame

from . import errors as errors
from . import session as session

__version__: str

class OpenState(Enum):
    Opened = "Opened"
    Pending = "Pending"
    Closed = "Closed"

def open_session(
    name: str | None = None, app_key: str | None = None, config_name: str | None = None
) -> session.Session: ...
def close_session() -> None: ...
def get_history(
    universe: str | Iterable[str],
    fields: str | Iterable[str] | None = None,
    interval: str | None = None,
    start: str | date | datetime | None = None,
    end: str | date | datetime | None = None,
    adjustments: str | None = None,
    count: int | None = None,
    parameters: str | dict[str, object] | None = None,
) -> DataFrame: ...
