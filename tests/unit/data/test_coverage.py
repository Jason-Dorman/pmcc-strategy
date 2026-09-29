"""The coverage summary (P1-08): valid mids over calendar session bars (PO, 2026-09-28).

A one-session cache built from `FakeLseg` pulls (`tests/fakes/pulls.py`): Mon Sep 14 2026 has 7
session bars, and the fake's bars start 13:00, 14:00 and 15:00 ET. The stock quotes all three; the
$100 call quotes the first two (its third bar has no values, so LSEG leaves it out), and the $105
call's second quote has a zero bid, so only its first is valid. The weekly's step was found on a
neighbour anchor, which is measured, so it is never flagged (PO, DEC-14).
"""

from datetime import date, datetime
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import SymbolCache
from pmcc.data.coverage import IV_NOTE, coverage, describe
from pmcc.data.discovery import Band, Pad, Region, StepMeasure, StepSource, Unit, UnitKind
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from tests.fakes.lseg import Bars
from tests.fakes.pulls import (
    CHAIN,
    DAY,
    EXPIRY,
    PUTS,
    market,
    option_bars,
    pull_chain,
    pull_stock,
)

CAL = load_calendar()
SESSION_BARS = 7
NEAR = Band(Region.NEAR_MONEY, Price.from_dollars(99), Price.from_dollars(101), Pad(4), Pad(6))
DEEP = Band(Region.DEEP_ITM, Price.from_dollars(60), Price.from_dollars(90), Pad(2), Pad(2))
ZERO_BID: Bars = {"BID": [1.0, 0.0, None], "ASK": [1.2, 1.3, None], "TRDPRC_1": [1.1, None, None]}


@pytest.fixture(autouse=True)
def cached(tmp_path: Path) -> SymbolCache:
    """The one-session cache in `tmp_path`, for every test."""
    fake = market({100: option_bars(), 105: ZERO_BID}, puts={100: option_bars()})
    cache = SymbolCache(tmp_path, "NVDA")
    cache.write_unit(pull_stock(fake))
    weekly = Unit(CHAIN.name, DAY, DAY, EXPIRY, Right.CALL, (NEAR,))
    neighbour = StepMeasure(DAY, (10_000, 9_000, 11_000), (9_000, 9_100), 100, StepSource.NEIGHBOUR)
    cache.write_unit(
        pull_chain(fake, [100, 105, 999], unit=weekly, steps=[100], increments=[neighbour])
    )
    puts = Unit(PUTS.name, DAY, DAY, EXPIRY, Right.PUT, (NEAR,))
    cache.write_unit(pull_chain(fake, [100], unit=puts, steps=[100]))
    return cache


def test_coverage_counts_valid_mids_over_every_calendar_session_bar(tmp_path: Path) -> None:
    cov = coverage(tmp_path, "NVDA", CAL)

    weekly = cov.by_kind[UnitKind.WEEKLY_CALLS]
    assert (weekly.requested, weekly.answered, weekly.unanswered) == (3, 2, 1)
    assert (weekly.expected, weekly.valid) == (2 * SESSION_BARS, 2 + 1)
    stock = cov.by_kind[UnitKind.STOCK]
    assert (stock.expected, stock.valid) == (SESSION_BARS, 3)
    assert [t.units for t in cov.by_kind.values()] == [1, 1, 1]


def test_coverage_near_the_money_is_weekly_calls_inside_the_stock_range(tmp_path: Path) -> None:
    cov = coverage(tmp_path, "NVDA", CAL)

    near = cov.near_money
    assert near.answered == 1  # $100 is inside $99-$101; $105 isn't, and puts never count
    assert (near.expected, near.valid) == (SESSION_BARS, 2)


def test_coverage_describes_kinds_near_money_and_leaves_iv_failures_out(tmp_path: Path) -> None:
    with capture_logs() as logs:
        text = describe(coverage(tmp_path, "NVDA", CAL))

    # units, requested, answered, unanswered, valid mid
    rows = {line.split()[0]: line.split()[-5:] for line in text.splitlines()[2:5]}
    assert rows == {
        "stock": ["1", "1", "1", "0", "42.9%"],
        "weekly": ["1", "3", "2", "1", "21.4%"],
        "puts": ["1", "1", "1", "0", "28.6%"],
    }
    assert "28.6% of 7 session bars, 1 contracts" in text  # near the money: 2 of 7
    assert "Near-the-money weekly calls" in text
    assert IV_NOTE in text
    assert text.isascii()  # Git Bash prints it in cp1252 on Windows (DEC-58)
    assert "not counted until the chain pricer adds them (P2-04" in IV_NOTE
    units = [e for e in logs if e["event"] == "fetch.coverage.unit"]
    assert {e["unit"] for e in units} == {"stock", CHAIN.name, PUTS.name}
    assert [e for e in logs if e["event"] == "fetch.coverage"]


def test_coverage_flags_unmeasured_steps_silent_units_and_missing_fields(tmp_path: Path) -> None:
    cache = SymbolCache(tmp_path / "flags", "NVDA")
    fake = market({100: option_bars()})
    cache.write_unit(pull_stock(fake, fields=("BID", "ASK", "TRDPRC_1", "ACVOL_UNS")))
    later = Unit("chains/2026-09-25_C", DAY, DAY, EXPIRY.replace(day=25), Right.CALL, (DEEP,))
    unmeasured = StepMeasure(EXPIRY, (8_000, 7_000, 9_000), (), 500, StepSource.PROBE_REPORT)
    cache.write_unit(pull_chain(fake, [999], unit=later, steps=[500], increments=[unmeasured]))

    text = describe(coverage(tmp_path / "flags", "NVDA", CAL))

    assert "wasn't measured (DEC-14): chains/2026-09-25_C" in text
    assert "Units that answered nothing: chains/2026-09-25_C" in text
    assert "Fields that never came back: ACVOL_UNS" in text.splitlines()


def test_coverage_flags_nothing_on_a_clean_cache(tmp_path: Path) -> None:
    text = describe(coverage(tmp_path, "NVDA", CAL))

    assert "wasn't measured (DEC-14): none" in text
    assert "Units that answered nothing: none" in text
    assert "Fields that never came back: none" in text


# --- A merged unit: a monthly Friday that is also a weekly expiry (PO, DEC-16) -----------------

# One bar a session, starting 14:00 ET, from Tue Sep 1 to Mon Sep 14 2026 (Labor Day out). The
# weekly part of the Sep 18 expiry runs from the prior week's first session, Tue Sep 8.
MERGED_DAYS = (1, 2, 3, 4, 8, 9, 10, 11, 14)
WEEKLY_PART = 5  # Sep 8, 9, 10, 11 and 14


def _merged_cache(root: Path) -> SymbolCache:
    index = [datetime(2026, 9, d, 18) for d in MERGED_DAYS]
    n = len(index)
    quoted: Bars = {"BID": [1.0] * n, "ASK": [1.2] * n}
    late: Bars = {"BID": [None] * 4 + [1.0] * 5, "ASK": [None] * 4 + [1.2] * 5}
    stock: Bars = {"BID": [180.0] * n, "ASK": [180.1] * n, "TRDPRC_1": [180.05] * n}
    fake = market({100: late, 101: late, 80: quoted}, stock=stock, index=index)
    cache = SymbolCache(root, "NVDA")
    cache.write_unit(pull_stock(fake))
    merged = Unit(CHAIN.name, date(2026, 9, 1), DAY, EXPIRY, Right.CALL, (NEAR, DEEP))
    cache.write_unit(pull_chain(fake, [80, 100, 101], unit=merged, steps=[100, 500]))
    return cache


def test_coverage_near_money_counts_a_merged_unit_over_its_weekly_part(tmp_path: Path) -> None:
    _merged_cache(tmp_path / "merged")

    cov = coverage(tmp_path / "merged", "NVDA", CAL)

    near = cov.near_money
    assert near.answered == 2  # $100 and $101 (the band's top); $80 is in the deep band
    assert (near.expected, near.valid) == (2 * WEEKLY_PART * SESSION_BARS, 2 * WEEKLY_PART)
    both = cov.by_kind[UnitKind.BOTH_CALLS]
    assert both.expected == 3 * len(MERGED_DAYS) * SESSION_BARS  # the kind row: the whole unit
    assert both.valid == len(MERGED_DAYS) + 2 * WEEKLY_PART
