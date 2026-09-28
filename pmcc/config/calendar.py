"""`configs/calendar.yaml`: the NYSE holiday table, validated into a `SessionCalendar` (DEC-33).

The file is found from this module, not the working directory, like the LSEG config.
"""

from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pmcc.config.yaml_file import read_yaml
from pmcc.domain.calendar import SessionCalendar

CALENDAR_PATH = Path(__file__).resolve().parents[2] / "configs" / "calendar.yaml"


class DayEntry(BaseModel):
    """One listed day and why it's listed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    day: date
    name: str = Field(min_length=1)


class CalendarFile(BaseModel):
    """The table as the YAML holds it: its span, its sources, closures and early closes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: list[str] = Field(min_length=1)
    first_day: date
    last_day: date
    closed: list[DayEntry]
    early_closes: list[DayEntry]

    def to_calendar(self) -> SessionCalendar:
        """The calendar. Raises `ValueError` for a day listed twice, or one the calendar refuses."""
        for kind, entries in (("closed", self.closed), ("early_closes", self.early_closes)):
            twice = sorted(d for d, n in Counter(e.day for e in entries).items() if n > 1)
            if twice:
                raise ValueError(f"{kind} lists a day more than once: {twice}")
        return SessionCalendar(
            self.first_day,
            self.last_day,
            closed={e.day: e.name for e in self.closed},
            early_closes={e.day: e.name for e in self.early_closes},
        )


def read_calendar_file(path: Path = CALENDAR_PATH) -> CalendarFile:
    """The validated file, sources included (the Methodology page cites them)."""
    return CalendarFile.model_validate(read_yaml(path))


def load_calendar(path: Path = CALENDAR_PATH) -> SessionCalendar:
    return read_calendar_file(path).to_calendar()
