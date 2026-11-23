"""FRED's public CSV (TD-05): its header, blank days, and failures that are never "no data"."""

import http.client
from datetime import date
from urllib.request import Request

import pytest

from pmcc.thesis import fred
from pmcc.thesis.fred import FRED_CSV, FredError, FredUnavailableError, fetch_series, parse_csv


def test_td_05_reads_the_current_header_and_keeps_blank_days_as_none() -> None:
    text = "observation_date,BAMLH0A0HYM2\n2023-11-20,4.01\n2023-11-21,.\n2023-11-22,3.98\n"
    series = parse_csv(text, "BAMLH0A0HYM2")

    assert series.observations == (
        (date(2023, 11, 20), 4.01),
        (date(2023, 11, 21), None),
        (date(2023, 11, 22), 3.98),
    )
    assert series.valued == ((date(2023, 11, 20), 4.01), (date(2023, 11, 22), 3.98))


def test_td_05_reads_the_older_date_header() -> None:
    assert parse_csv("DATE,BAMLH0A0HYM2\n2024-01-02,3.5\n", "BAMLH0A0HYM2").valued == (
        (date(2024, 1, 2), 3.5),
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "<html>Service unavailable</html>\n",
        "observation_date,DGS10\n2024-01-02,4.0\n",  # another series
        "observation_date,BAMLH0A0HYM2\n2024-01-03,3.5\n2024-01-02,3.6\n",  # out of order
        "observation_date,BAMLH0A0HYM2\n2024-01-02,3.5\n2024-01-02,3.6\n",  # a day twice
        "observation_date,BAMLH0A0HYM2\n2024-01-02,n/a\n",
        "observation_date,BAMLH0A0HYM2\n2024-01-02,3.5,extra\n",
    ],
)
def test_td_05_an_answer_that_isnt_the_series_raises(text: str) -> None:
    with pytest.raises(FredError):
        parse_csv(text, "BAMLH0A0HYM2")


def test_td_05_fetch_asks_the_series_csv_url() -> None:
    asked: list[str] = []

    def get(url: str) -> str:
        asked.append(url)
        return "observation_date,BAMLH0A0HYM2\n2024-01-02,3.5\n"

    fetch_series("BAMLH0A0HYM2", get)

    assert asked == [FRED_CSV.format(series="BAMLH0A0HYM2")]
    assert asked[0].startswith("https://fred.stlouisfed.org/")


def test_td_05_an_empty_cell_is_a_blank_day_as_fred_writes_it_now() -> None:
    text = "observation_date,BAMLH0A0HYM2\n2024-12-24,2.87\n2024-12-25,\n2024-12-26,2.90\n"
    series = parse_csv(text, "BAMLH0A0HYM2")
    assert series.observations[1] == (date(2024, 12, 25), None)
    assert len(series.valued) == 2


@pytest.mark.parametrize(
    "error",
    [TimeoutError("timed out"), http.client.IncompleteRead(b"obs"), ValueError("bad URL")],
)
def test_td_05_a_failed_request_is_an_outage(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    def urlopen(request: Request, timeout: float) -> object:
        raise error

    monkeypatch.setattr(fred, "urlopen", urlopen)
    with pytest.raises(FredUnavailableError, match="did not answer"):
        fred.http_get(FRED_CSV.format(series="BAMLH0A0HYM2"))
