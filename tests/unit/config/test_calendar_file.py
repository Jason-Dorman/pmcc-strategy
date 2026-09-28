"""`configs/calendar.yaml`: the shipped NYSE table and the known cases it must produce (DEC-33)."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from pmcc.config.calendar import CALENDAR_PATH, load_calendar, read_calendar_file
from pmcc.domain.sessions import HALF_DAY_CLOSE

CAL = load_calendar()


def test_calendar_file_loads_2025_to_2027_with_its_sources() -> None:
    table = read_calendar_file()
    assert (table.first_day, table.last_day) == (date(2025, 1, 1), date(2027, 12, 31))
    assert any("nyse.com" in source for source in table.source)
    assert CALENDAR_PATH.parts[-2:] == ("configs", "calendar.yaml")


def test_e_s2_weekly_expiry_is_thu_jul_2_2026_when_jul_3_is_closed() -> None:
    assert not CAL.is_session(date(2026, 7, 3))
    assert CAL.week_final(date(2026, 6, 29)).day == date(2026, 7, 2)
    assert CAL.session(date(2026, 7, 2)).close != HALF_DAY_CLOSE  # NYSE: a full day in 2026


def test_e_s1_week_open_is_tue_sep_8_2026_after_labor_day() -> None:
    assert CAL.week_open(date(2026, 9, 10)).day == date(2026, 9, 8)


def test_e_s2_weekly_expiry_is_thu_jun_18_2026_when_juneteenth_is_closed() -> None:
    assert CAL.week_final(date(2026, 6, 15)).day == date(2026, 6, 18)


def test_e_l2_june_2026_monthly_expires_thu_jun_18() -> None:
    assert CAL.monthly_expiry(2026, 6) == date(2026, 6, 18)


def test_e_l2_june_2027_monthly_expires_thu_jun_17() -> None:
    assert not CAL.is_session(date(2027, 6, 18))  # Juneteenth observed on the Friday
    assert CAL.monthly_expiry(2027, 6) == date(2027, 6, 17)


def test_calendar_file_carries_the_unscheduled_jan_9_2025_closure() -> None:
    assert CAL.closed_days(date(2025, 1, 9), date(2025, 1, 9)) == {
        date(2025, 1, 9): "National Day of Mourning (President Carter)"
    }


@pytest.mark.parametrize(
    "day", [date(2025, 7, 3), date(2025, 11, 28), date(2025, 12, 24), date(2026, 11, 27)]
)
def test_calendar_file_early_closes_end_at_13(day: date) -> None:
    assert CAL.session(day).close == HALF_DAY_CLOSE


def test_calendar_file_has_ten_or_eleven_closures_a_year() -> None:
    counts = {
        year: len(CAL.closed_days(date(year, 1, 1), date(year, 12, 31)))
        for year in (2025, 2026, 2027)
    }
    assert counts == {2025: 11, 2026: 10, 2027: 10}


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "calendar.yaml"
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


HEADER = "source: [somewhere]\nfirst_day: 2026-01-01\nlast_day: 2026-12-31\n"


def test_calendar_file_refuses_a_day_listed_twice(tmp_path: Path) -> None:
    twice = "  - {day: 2026-01-19, name: a}\n  - {day: 2026-01-19, name: b}\n"
    body = HEADER + "closed:\n" + twice + "early_closes: []\n"
    with pytest.raises(ValueError, match="more than once"):
        load_calendar(_write(tmp_path, body))


def test_calendar_file_refuses_a_weekend_closure(tmp_path: Path) -> None:
    body = HEADER + "closed:\n  - {day: 2026-01-17, name: Saturday}\nearly_closes: []\n"
    with pytest.raises(ValueError, match="weekend"):
        load_calendar(_write(tmp_path, body))


def test_calendar_file_refuses_a_key_given_twice(tmp_path: Path) -> None:
    # yaml.safe_load would keep the second `closed` and silently drop the first's holidays.
    body = HEADER + "closed:\n  - {day: 2026-01-19, name: a}\nearly_closes: []\nclosed: []\n"
    with pytest.raises(ValueError, match="more than once"):
        read_calendar_file(_write(tmp_path, body))


@pytest.mark.parametrize(
    "body",
    [
        "first_day: 2026-01-01\nlast_day: 2026-12-31\nclosed: []\nearly_closes: []\n",  # no source
        HEADER + "closed: []\nearly_closes: []\nextra: 1\n",  # an unknown key
        HEADER + "closed:\n  - {day: 2026-01-19}\nearly_closes: []\n",  # a closure with no name
    ],
)
def test_calendar_file_refuses_a_malformed_table(tmp_path: Path, body: str) -> None:
    with pytest.raises(ValidationError):
        read_calendar_file(_write(tmp_path, body))
