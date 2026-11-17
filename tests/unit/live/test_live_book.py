"""Reading Sanji's book (L2-02; L-B1, L-B2; PO, LD-14).

The book must be current (the price file runs to the last completed session) and readable; while
Sanji has written no book, a stale price file is a warning instead (PO, LD-32). No
positions or fills means nothing ever filled: cash alone. Sanji's position and fill formats were
never seen (it wasn't resolving orders), so either file appearing stops the run until it's read.
"""

from datetime import date
from pathlib import Path

import pytest

from pmcc.domain.money import Money
from pmcc.live.book import (
    BookError,
    WheelState,
    check_current,
    last_priced_session,
    read_book,
    sanji_file,
)
from tests.fakes.live import sanji_root

FRIDAY = date(2026, 11, 13)
CASH = Money.from_dollars("25000")


def _sanji_fills(root: Path) -> None:
    """Sanji's fills file, as it will be once Sanji resolves an order (its format is unknown)."""
    (root / "mkt").mkdir(exist_ok=True)
    (root / "mkt" / "fills.json").write_text("[]" + chr(10), encoding="utf-8", newline=chr(10))


def test_l_b1_the_latest_bar_over_every_instrument_counts(tmp_path: Path) -> None:
    # NVDA is tracked but has no bars yet; SPY's run to Friday.
    sanji_root(tmp_path, FRIDAY, extra_days=[date(2026, 11, 12)])

    assert last_priced_session(tmp_path) == FRIDAY


def test_l_b1_a_book_priced_to_the_last_session_is_current(tmp_path: Path) -> None:
    assert check_current(sanji_root(tmp_path, FRIDAY), FRIDAY) is None


def test_l_b1_a_book_a_session_behind_is_stale_once_sanji_has_a_book(tmp_path: Path) -> None:
    sanji_root(tmp_path, date(2026, 11, 12))
    _sanji_fills(tmp_path)

    with pytest.raises(BookError, match="L-B1") as raised:
        check_current(tmp_path, FRIDAY)

    assert raised.value.rule == "L-B1"


def test_ld_32_with_no_sanji_book_a_stale_price_file_is_a_warning(tmp_path: Path) -> None:
    """Sanji has written no positions or fills, so it has resolved nothing and the cash
    book can't have moved: the run goes ahead and says why (PO, LD-32)."""
    warning = check_current(sanji_root(tmp_path, date(2026, 11, 12)), FRIDAY)

    assert warning is not None
    assert "runs to 2026-11-12" in warning
    assert "resolved nothing" in warning


@pytest.mark.parametrize("text", [None, "{", "[]", '{"1": {"price_history": []}}', "{}"])
def test_l_b1_a_missing_or_unreadable_price_file_is_stale(tmp_path: Path, text: str | None) -> None:
    if text is not None:
        (tmp_path / "price_history.json").write_text(text, encoding="utf-8")

    with pytest.raises(BookError, match="L-B1"):
        last_priced_session(tmp_path)


def test_l_b2_no_positions_and_no_fills_is_cash_alone(tmp_path: Path) -> None:
    book = read_book(tmp_path, CASH)

    assert book.state is WheelState.CASH
    assert book.cash == CASH
    assert book.cost_basis is None
    assert book.short_option is None


@pytest.mark.parametrize(
    "where", ["mkt/positions.json", "positions.json", "mkt/fills.json", "fills.json"]
)
def test_l_b2_a_sanji_file_of_unknown_format_stops_the_run(tmp_path: Path, where: str) -> None:
    path = tmp_path / where
    path.parent.mkdir(exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(BookError, match="L-B2") as raised:
        read_book(tmp_path, CASH)

    assert where.split("/")[-1] in str(raised.value)


def test_ld_04_sanjis_files_are_looked_for_under_mkt_first(tmp_path: Path) -> None:
    (tmp_path / "mkt").mkdir()
    for path in (tmp_path / "mkt" / "fills.json", tmp_path / "fills.json"):
        path.write_text("[]", encoding="utf-8")

    assert sanji_file(tmp_path, "fills.json") == tmp_path / "mkt" / "fills.json"
    assert sanji_file(tmp_path, "positions.json") is None
