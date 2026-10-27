"""The S&P 500 benchmark file (W1-03, WD-03, WD-17): two closes that bracket the window."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.config.universe import load_universe
from pmcc.wheel.benchmarks import BENCHMARKS_PATH, BenchmarkError, load_sp500

CAL = load_calendar()
WINDOW = load_universe(CAL).window

GOOD = """\
sp500:
  series: SP500
  start: {day: 2026-03-27, close: '6368.85'}
  end: {day: 2026-09-25, close: '7743.41'}
  source: S&P Dow Jones Indices LLC, S&P 500 [SP500], via FRED
"""


def _load(tmp_path: Path, text: str) -> object:
    path = tmp_path / "benchmarks.yaml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return load_sp500(CAL, WINDOW.start, WINDOW.end, path)


def test_wd_17_the_committed_file_brackets_the_window() -> None:
    sp500 = load_sp500(CAL, WINDOW.start, WINDOW.end, BENCHMARKS_PATH)
    assert (sp500.start.day, sp500.end.day) == (date(2026, 3, 27), date(2026, 9, 25))
    assert (sp500.start.close, sp500.end.close) == (Decimal("6368.85"), Decimal("7743.41"))
    assert "fred.stlouisfed.org/series/SP500" in sp500.source


def test_wd_17_price_return_is_end_over_start_less_one() -> None:
    sp500 = load_sp500(CAL, WINDOW.start, WINDOW.end, BENCHMARKS_PATH)
    assert sp500.price_return == Decimal("7743.41") / Decimal("6368.85") - 1


def test_wd_17_start_must_be_the_last_close_before_the_window(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkError, match="2026-03-27"):
        _load(tmp_path, GOOD.replace("2026-03-27", "2026-03-26"))


def test_wd_17_end_must_be_the_windows_last_close(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkError, match="2026-09-25"):
        _load(tmp_path, GOOD.replace("2026-09-25", "2026-09-24"))


@pytest.mark.parametrize(
    ("old", "new"),
    [("2026-03-27", "2026-03-30"), ("2026-09-25", "2026-09-28")],  # the window's first close; after
)
def test_wd_17_a_close_later_than_the_window_allows_is_refused(
    tmp_path: Path, old: str, new: str
) -> None:
    with pytest.raises(BenchmarkError, match=old):
        _load(tmp_path, GOOD.replace(old, new))


@pytest.mark.parametrize("bad", ["'0'", "'-1'"])
def test_wd_17_a_close_must_be_positive(tmp_path: Path, bad: str) -> None:
    with pytest.raises(BenchmarkError):
        _load(tmp_path, GOOD.replace("'6368.85'", bad))


def test_wd_17_refuses_an_unknown_key(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkError):
        _load(tmp_path, GOOD + "  total_return: true\n")
