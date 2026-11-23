"""FRED's public CSV for one series (TD-05): the high-yield OAS if LSEG lacks its history.

FRED serves any series as `fredgraph.csv?id=SERIES`, with no API key: a header row
(`observation_date,SERIES`, or `DATE,SERIES` in older files) and one row a day, the value in the
series' units (BAMLH0A0HYM2 in percent: 3.52 is 352 bps), or an empty cell (`.` in older files)
where FRED has none. Read with the
standard library, so no new dependency. The request names no user or project: a generic client
name only (CLAUDE.md › FRED).

A request that fails raises `FredUnavailableError`, an outage: the caller aborts and writes
nothing, never "no data" (CLAUDE.md › FRED, TD-05). An answer that isn't the series' CSV raises
`FredError`. An empty cell or a `.` is a day FRED published without a value, kept as None, never as
zero.
"""

import csv
import http.client
import io
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import final
from urllib.request import Request, urlopen

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
USER_AGENT = "thesis-tracker/1.0"
TIMEOUT_SECONDS = 30
_DATE_HEADERS = frozenset({"observation_date", "DATE"})
_BLANK = frozenset({"", "."})

type GetText = Callable[[str], str]


class FredError(Exception):
    """FRED answered with something other than the series' CSV."""


class FredUnavailableError(Exception):
    """FRED didn't answer: a connection, an HTTP status, a cut-off body. An outage."""


@final
@dataclass(frozen=True, slots=True)
class FredSeries:
    """One series' observations, oldest first; a None value is a day FRED left blank (`.`)."""

    series: str
    observations: tuple[tuple[date, float | None], ...]

    @property
    def valued(self) -> tuple[tuple[date, float], ...]:
        return tuple((d, v) for d, v in self.observations if v is not None)


def http_get(url: str) -> str:
    """The body of a GET, as UTF-8 text. A failed request raises `FredUnavailableError`."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as answer:
            body: bytes = answer.read()
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise FredUnavailableError(f"FRED did not answer: {type(exc).__name__}: {exc}") from exc
    try:
        return body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FredError("FRED's answer is not UTF-8 text") from exc


def fetch_series(series: str, get: GetText = http_get) -> FredSeries:
    """`series` from FRED's CSV. Raises `FredUnavailableError` on a failed request and
    `FredError` on an unreadable answer."""
    return parse_csv(get(FRED_CSV.format(series=series)), series)


def parse_csv(text: str, series: str) -> FredSeries:
    """FRED's CSV for `series`: its two-column header, then a date and a value (or `.`) a row."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or len(rows[0]) != 2 or rows[0][0] not in _DATE_HEADERS or rows[0][1] != series:
        head = rows[0] if rows else []
        raise FredError(f"FRED's answer is not {series}'s CSV (header {head})")
    observations = tuple(_observation(row, series) for row in rows[1:] if row)
    days = [d for d, _ in observations]
    if days != sorted(set(days)):
        raise FredError(f"{series}'s dates are not strictly increasing")
    return FredSeries(series, observations)


def _observation(row: list[str], series: str) -> tuple[date, float | None]:
    if len(row) != 2:
        raise FredError(f"{series}: a row with {len(row)} cells: {row}")
    try:
        day = date.fromisoformat(row[0])
        value = None if row[1].strip() in _BLANK else float(row[1])
    except ValueError as exc:
        raise FredError(f"{series}: an unreadable row {row}") from exc
    return day, value
