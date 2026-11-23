"""FRED's official API (TD-05, TD-17): its observations, blank days, retries, refusals, and a key
that never shows."""

import http.client
import io
import json
import urllib.error
from datetime import date
from email.message import Message
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest

from pmcc.thesis import fred
from pmcc.thesis.fred import (
    FRED_API,
    FredError,
    FredKey,
    FredUnavailableError,
    fetch_series,
    parse_observations,
    series_url,
)

KEY = FredKey("0123456789abcdef0123456789abcdef")
SERIES = "BAMLH0A0HYM2"


def _json(*rows: tuple[str, str]) -> str:
    return json.dumps({"observations": [{"date": d, "value": v} for d, v in rows]})


def _no_wait(_seconds: float) -> None:
    pass


def test_td_17_reads_the_observations_and_keeps_blank_days_as_none() -> None:
    series = parse_observations(
        _json(("2023-11-20", "4.01"), ("2023-11-21", "."), ("2023-11-22", "3.98")), SERIES
    )
    assert series.observations == (
        (date(2023, 11, 20), 4.01),
        (date(2023, 11, 21), None),
        (date(2023, 11, 22), 3.98),
    )
    assert series.valued == ((date(2023, 11, 20), 4.01), (date(2023, 11, 22), 3.98))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "<html>maintenance</html>",
        json.dumps({"error_code": 400}),
        json.dumps({"observations": "none"}),
        json.dumps({"observations": [["2024-01-02", "3.5"]]}),
        json.dumps({"observations": [{"date": "2024-01-02"}]}),
        _json(("2024-01-02", "n/a")),
        _json(("2024-01-03", "3.5"), ("2024-01-02", "3.6")),  # out of order
        _json(("2024-01-02", "3.5"), ("2024-01-02", "3.6")),  # a day twice
    ],
)
def test_td_17_an_answer_that_isnt_the_series_raises(text: str) -> None:
    with pytest.raises(FredError):
        parse_observations(text, SERIES)


def test_td_17_the_url_asks_the_api_for_the_series_as_json() -> None:
    url = urlsplit(series_url(SERIES, KEY))
    assert f"{url.scheme}://{url.netloc}{url.path}" == FRED_API
    assert parse_qs(url.query) == {
        "series_id": [SERIES],
        "api_key": [KEY.value],
        "file_type": ["json"],
    }


def test_td_17_the_key_comes_from_the_environment_and_never_prints() -> None:
    key = FredKey.from_env({"FRED_API_KEY": KEY.value})
    assert key.value == KEY.value
    assert KEY.value not in repr(key)
    assert KEY.value not in str(key)


@pytest.mark.parametrize("environ", [{}, {"FRED_API_KEY": "  "}])
def test_td_17_a_missing_key_raises_naming_the_variable(environ: dict[str, str]) -> None:
    with pytest.raises(FredUnavailableError, match="FRED_API_KEY not set"):
        FredKey.from_env(environ)


def test_td_14_fred_is_asked_again_before_it_counts_as_unavailable() -> None:
    answers: list[str | Exception] = [
        FredUnavailableError("FRED did not answer: TimeoutError"),
        FredUnavailableError("FRED did not answer: HTTP 503"),
        _json(("2024-01-02", "3.5")),
    ]
    waited: list[float] = []

    def get(_url: str) -> str:
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    series = fetch_series(SERIES, KEY, get, waits=(10.0, 30.0), sleep=waited.append)
    assert series.valued == ((date(2024, 1, 2), 3.5),)
    assert waited == [10.0, 30.0]


def test_td_14_fred_unavailable_on_every_try_is_an_outage() -> None:
    tries: list[str] = []

    def down(url: str) -> str:
        tries.append(url)
        raise FredUnavailableError("FRED did not answer: TimeoutError")

    with pytest.raises(FredUnavailableError):
        fetch_series(SERIES, KEY, down, waits=(1.0, 2.0), sleep=_no_wait)
    assert len(tries) == 3


def test_td_14_an_unreadable_answer_is_not_asked_again() -> None:
    tries: list[str] = []

    def html(url: str) -> str:
        tries.append(url)
        return "<html>maintenance</html>"

    with pytest.raises(FredError):
        fetch_series(SERIES, KEY, html, waits=(1.0,), sleep=_no_wait)
    assert len(tries) == 1


def test_td_17_no_error_ever_shows_the_key() -> None:
    def leaky(url: str) -> str:
        raise FredUnavailableError(f"FRED did not answer: URLError for {url}")

    with pytest.raises(FredUnavailableError) as raised:
        fetch_series(SERIES, KEY, leaky, waits=(), sleep=_no_wait)
    assert KEY.value not in str(raised.value)
    assert "***" in str(raised.value)
    assert raised.value.__cause__ is None


def _http_error(code: int, body: dict[str, object] | None = None) -> urllib.error.HTTPError:
    stream = io.BytesIO(json.dumps(body).encode() if body is not None else b"")
    return urllib.error.HTTPError(FRED_API, code, "status", Message(), stream)


@pytest.mark.parametrize(
    ("error", "raises"),
    [
        (TimeoutError("The read operation timed out"), FredUnavailableError),
        (http.client.IncompleteRead(b"obs"), FredUnavailableError),
        (ValueError("bad URL"), FredUnavailableError),
        (_http_error(503), FredUnavailableError),
        (_http_error(429), FredUnavailableError),
        (_http_error(400, {"error_message": "Bad Request. api_key is not registered."}), FredError),
    ],
)
def test_td_17_a_failed_request_is_an_outage_and_a_refusal_is_not(
    error: Exception, raises: type[Exception], monkeypatch: pytest.MonkeyPatch
) -> None:
    def urlopen(request: Request, timeout: float) -> object:
        raise error

    monkeypatch.setattr(fred, "urlopen", urlopen)
    with pytest.raises(raises):
        fred.http_get(series_url(SERIES, KEY))


def test_td_17_a_refusal_carries_freds_reason() -> None:
    error = _http_error(400, {"error_message": "Bad Request. Unknown series."})
    refused = fred._refused(error)  # pyright: ignore[reportPrivateUsage]
    assert isinstance(refused, FredError)
    assert "HTTP 400: Bad Request. Unknown series." in str(refused)
