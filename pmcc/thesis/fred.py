"""FRED's official API for one series (TD-05, TD-17): the high-yield OAS if LSEG lacks its history.

`fred/series/observations?series_id=SERIES&api_key=KEY&file_type=json` answers with JSON: an
`observations` list, each with a `date` and a `value` in the series' units (BAMLH0A0HYM2 in
percent: 3.52 is 352 bps), `.` where FRED has none (kept as None, never zero). Read with the
standard library, so no new dependency. The request carries the series, the key and the format,
and a generic client name: nothing about the user or the project (CLAUDE.md › FRED).

The key is `FRED_API_KEY`: a GitHub secret in Actions, an environment variable locally (TD-17).
It is never printed: not in a repr, an error or a log. Every message that leaves this module is
masked first, the key as typed and URL-encoded (it rides in the URL).

- **FRED not answering** (a connection, a timeout, a cut-off body, HTTP 429 or a 5xx) is asked
  again after each wait, then raises `FredUnavailableError`: an outage, so the caller aborts and
  writes nothing, never "no data".
- **FRED refusing the request** (any other 4xx: a bad key, an unknown series) or answering with
  something that isn't the series' observations raises `FredError`, at once: the same request would
  get the same answer.
"""

import http.client
import json
import time
import urllib.error
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import cast, final
from urllib.parse import quote, quote_plus, urlencode
from urllib.request import Request, urlopen

FRED_API = "https://api.stlouisfed.org/fred/series/observations"
KEY_ENV = "FRED_API_KEY"
USER_AGENT = "thesis-tracker/1.0"
TIMEOUT_SECONDS = 60
# A request is tried this many times, waiting these seconds between tries, before FRED counts as
# unavailable (the first Actions run timed out at 30 s on the public CSV, TD-14).
RETRY_WAITS = (10.0, 30.0)
MASK = "***"
_RATE_LIMITED = 429

type GetText = Callable[[str], str]


class FredError(Exception):
    """FRED refused the request, or answered with something other than the series' observations."""


class FredUnavailableError(Exception):
    """FRED didn't answer: a connection, a timeout, a cut-off body, HTTP 429 or 5xx. An outage."""


@final
@dataclass(frozen=True, slots=True)
class FredKey:
    """FRED's API key. Never printed."""

    value: str = field(repr=False)

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "FredKey":
        """`FRED_API_KEY` from the environment. Missing or blank raises, naming the variable."""
        value = environ.get(KEY_ENV, "").strip()
        if not value:
            raise FredUnavailableError(
                f"{KEY_ENV} not set: FRED's API needs it (a GitHub secret in Actions, an "
                "environment variable locally). Nothing was requested."
            )
        return cls(value)

    def __str__(self) -> str:
        return repr(self)

    def masked(self, text: str) -> str:
        """`text` with the key replaced by `***`, as typed and URL-encoded."""
        forms = {self.value, quote(self.value, safe=""), quote_plus(self.value)}
        for form in sorted(forms, key=len, reverse=True):
            text = text.replace(form, MASK)
        return text


@final
@dataclass(frozen=True, slots=True)
class FredSeries:
    """One series' observations, oldest first; a None value is a day FRED left blank (`.`)."""

    series: str
    observations: tuple[tuple[date, float | None], ...]

    @property
    def valued(self) -> tuple[tuple[date, float], ...]:
        return tuple((d, v) for d, v in self.observations if v is not None)


def series_url(series: str, key: FredKey) -> str:
    query = urlencode({"series_id": series, "api_key": key.value, "file_type": "json"})
    return f"{FRED_API}?{query}"


def http_get(url: str) -> str:
    """The body of a GET, as UTF-8 text. Raises `FredUnavailableError` when FRED doesn't answer
    and `FredError` when it refuses. Messages may hold the URL's key: `fetch_series` masks them."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as answer:
            body: bytes = answer.read()
    except urllib.error.HTTPError as exc:
        raise _refused(exc) from None
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise FredUnavailableError(f"FRED did not answer: {type(exc).__name__}: {exc}") from None
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        raise FredError("FRED's answer is not UTF-8 text") from None


def _refused(exc: urllib.error.HTTPError) -> Exception:
    if exc.code == _RATE_LIMITED or exc.code >= 500:
        return FredUnavailableError(f"FRED did not answer: HTTP {exc.code}")
    return FredError(f"FRED refused the request: HTTP {exc.code}: {_error_message(exc)}")


def _error_message(exc: urllib.error.HTTPError) -> str:
    """FRED's own `error_message`, if its body holds one."""
    try:
        body: object = json.loads(exc.read().decode("utf-8"))
    except (OSError, ValueError):
        return "no reason given"
    message = cast(dict[str, object], body).get("error_message") if isinstance(body, dict) else None
    return str(message) if message else "no reason given"


def fetch_series(
    series: str,
    key: FredKey,
    get: GetText = http_get,
    waits: tuple[float, ...] = RETRY_WAITS,
    sleep: Callable[[float], None] = lambda seconds: time.sleep(seconds),
) -> FredSeries:
    """`series` from FRED's API, asked again after each wait in `waits` while FRED doesn't
    answer. Raises `FredUnavailableError` once every try has failed, and `FredError` when FRED
    refuses or its answer can't be read. The key never appears in either."""
    try:
        return _fetch(series, series_url(series, key), get, waits, sleep)
    except FredUnavailableError as exc:
        raise FredUnavailableError(key.masked(str(exc))) from None
    except FredError as exc:
        raise FredError(key.masked(str(exc))) from None


def _fetch(
    series: str, url: str, get: GetText, waits: tuple[float, ...], sleep: Callable[[float], None]
) -> FredSeries:
    for wait in waits:
        try:
            return parse_observations(get(url), series)
        except FredUnavailableError:
            sleep(wait)
    return parse_observations(get(url), series)


def parse_observations(text: str, series: str) -> FredSeries:
    """The API's JSON for `series`: an `observations` list of `date` and `value`, dates strictly
    increasing."""
    try:
        body: object = json.loads(text)
    except ValueError:
        raise FredError(f"FRED's answer for {series} is not JSON") from None
    rows = cast(dict[str, object], body).get("observations") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise FredError(f"FRED's answer for {series} holds no observations list")
    observations = tuple(_observation(row, series) for row in cast(list[object], rows))
    days = [d for d, _ in observations]
    if days != sorted(set(days)):
        raise FredError(f"{series}'s dates are not strictly increasing")
    return FredSeries(series, observations)


def _observation(row: object, series: str) -> tuple[date, float | None]:
    if not isinstance(row, dict):
        raise FredError(f"{series}: an observation that isn't an object")
    fields = cast(dict[str, object], row)
    day, value = fields.get("date"), fields.get("value")
    if not isinstance(day, str) or not isinstance(value, str):
        raise FredError(f"{series}: an observation without a date and a value")
    try:
        return date.fromisoformat(day), None if value.strip() in {"", "."} else float(value)
    except ValueError:
        raise FredError(f"{series}: an unreadable observation on {day!r}") from None
