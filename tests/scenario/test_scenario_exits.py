"""Every exit rule fires in a full run (TEST-STRATEGY §4, §5; DEC-27, DEC-28, DEC-34). X-S3, X-S4
and X-S5 run the baseline without X-S1 (A5's config, "hold to the Friday check"): on a flat path
X-S1 would take the profit first. Every run checks INV-01 to INV-10 on every bar."""

from datetime import date
from pathlib import Path

from structlog.testing import capture_logs

from pmcc.accounting.events import StockId
from pmcc.domain.instruments import OptionId, Side
from pmcc.domain.money import Money, Price
from tests.fixtures.synthetic import scenarios as sc
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import NO_TAKE_PROFIT, at, only, rows, run

SHORT_STRIKE = Price.from_dollars(102)  # the baseline's week-1 short on these markets
EM_AT_ENTRY = "3.4400"  # its EM: 0.25 × EM = $0.86


def test_x_s1_takes_profit_after_a_premium_collapse(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "premium_collapse", sc.premium_collapse)
    close = only(out, "X-S1", Side.BUY)
    sold = only(out, "E-S1", Side.SELL) if len(rows(out, "E-S1")) == 1 else rows(out, "E-S1")[0]
    assert close.instrument == sold.instrument
    assert close.time.date() == sc.TUE
    assert close.fill is not None
    assert sold.fill is not None
    assert close.fill.units * 4 <= sold.fill.units  # at most 25% of the credit


def test_x_s2_closes_the_short_once_its_delta_passes_0_60(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "rally_through_strike", sc.rally_through_strike)
    close = only(out, "X-S2", Side.BUY)
    assert close.time.date() == sc.TUE
    delta = close.audit["delta"]
    assert isinstance(delta, float)
    assert delta > 0.60


def test_x_s3_closes_within_a_quarter_em_of_the_strike(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "friday_within_buffer", sc.BUILDERS["friday_within_buffer"],
              overrides=NO_TAKE_PROFIT)  # fmt: skip
    sold = rows(out, "E-S1", Side.SELL)[0]
    assert sold.audit["strike"] == "102.0000"
    assert sold.audit["em_at_entry"] == EM_AT_ENTRY
    close = only(out, "X-S3", Side.BUY)
    assert close.time == at(sc.FRI, 15)
    assert close.audit["spot"] == "101.7000"
    assert not [e for e in out.blotter if e.rule_id in ("X-S4", "X-S5") and e.time.date() == sc.FRI]


def test_x_s3_does_not_fire_outside_the_buffer(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    out = run(synthetic, tmp_path, "friday_outside_buffer",
              lambda: sc.friday_within_buffer(102.0, 1.0), overrides=NO_TAKE_PROFIT)  # fmt: skip
    assert rows(out, "X-S3") == []
    assert rows(out, "X-S4", Side.EXPIRE)[0].time == at(sc.FRI, 16)


def test_x_s3_without_a_quote_fills_on_the_next_bar(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "friday_unquoted_at_check",
              sc.BUILDERS["friday_unquoted_at_check"], overrides=NO_TAKE_PROFIT)  # fmt: skip
    close = only(out, "X-S3", Side.BUY)
    assert close.time == at(sc.FRI, 16)
    assert close.notes.endswith("delayed fill")
    pending = [r.time for r in out.ledger if "exit_pending" in r.flags]
    assert pending == [at(sc.FRI, 15)]
    assert rows(out, "X-S5") == []


def test_x_s3_pending_without_a_quote_at_the_close_falls_to_x_s4(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """DEC-28: no quote before the close, so X-S4/X-S5 resolve the short there (an OTM call on its
    expiry close has a zero bid)."""
    out = run(synthetic, tmp_path, "friday_unquoted_otm_close",
              sc.BUILDERS["friday_unquoted_otm_close"], overrides=NO_TAKE_PROFIT)  # fmt: skip
    assert rows(out, "X-S3") == []
    assert rows(out, "X-S4", Side.EXPIRE)[0].time == at(sc.FRI, 16)
    close = next(r for r in out.ledger if r.time == at(sc.FRI, 16))
    assert close.short is None
    assert "exit_pending" not in close.flags  # resolved on this bar: nothing is pending


def test_x_s4_a_quiet_week_expires_at_zero(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet, overrides=NO_TAKE_PROFIT)
    expire = only(out, "X-S4", Side.EXPIRE)
    assert expire.time == at(sc.FRI, 16)
    assert (expire.fill, expire.cash_delta) == (Price(0), Money.zero())
    after = next(r for r in out.ledger if r.time == at(sc.FRI, 16))
    assert after.short is None


def test_x_s5_a_late_surge_is_assigned_and_covered_next_session(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides=NO_TAKE_PROFIT)  # fmt: skip
    x_s5 = rows(out, "X-S5")
    assert [(e.side, e.time) for e in x_s5] == [
        (Side.ASSIGN, at(sc.FRI, 16)),
        (Side.SELL, at(sc.FRI, 16)),
        (Side.BUY, at(sc.WEEK2_OPEN, 10)),
    ]
    assign, sale, cover = x_s5
    assert isinstance(assign.instrument, OptionId)
    assert (sale.instrument, sale.qty, sale.fill) == (StockId("SYN"), 100, SHORT_STRIKE)
    assert sale.cash_delta == Money.from_dollars(10_200)
    assert (cover.instrument, cover.qty) == (StockId("SYN"), 100)
    weekend = next(r for r in out.ledger if r.time == at(sc.FRI, 16))
    assert weekend.stock is not None
    assert weekend.stock.shares == -100
    assert weekend.long is not None
    covered = next(r for r in out.ledger if r.time == at(sc.WEEK2_OPEN, 10))
    assert covered.stock is None


def test_x_s5_short_stock_carries_the_hedged_requirement(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """DEC-10: with the long held, no initial beyond the proceeds; maintenance 10% of its strike."""
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides=NO_TAKE_PROFIT)  # fmt: skip
    row = next(r for r in out.ledger if r.time == at(sc.FRI, 16))
    assert row.long is not None
    long_mv = row.long.mark.notional(100, 1)
    assert row.im == long_mv
    assert row.mm == long_mv + Money.from_dollars(900)  # 10% of the $90 long × 100 shares


def test_x_s5_can_leave_funds_negative_and_the_ledger_says_so(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides=NO_TAKE_PROFIT, cash=Money.from_dollars(1_300))  # fmt: skip
    negative = [r for r in out.ledger if "funds_negative" in r.flags]
    assert negative[0].time == at(sc.FRI, 16)
    assert negative[0].available_funds.units < 0
    # Stock sold at $102 and bought back at ~$104 leaves cash negative: the loss is realized, so
    # funds stay negative after the cover, and the ledger keeps saying so.
    after_cover = next(r for r in out.ledger if r.time == at(sc.WEEK2_OPEN, 10))
    assert after_cover.stock is None
    assert after_cover.cash.units < 0
    assert "funds_negative" in after_cover.flags


def test_x_l1_resets_the_long_and_re_enters(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    out = run(synthetic, tmp_path, "long_delta_drop", sc.long_delta_drop)
    sale = only(out, "X-L1", Side.SELL)
    assert sale.time == at(sc.WEEK2_OPEN, 10)
    delta = sale.audit["delta"]
    assert isinstance(delta, float)
    assert delta < 0.50
    entries = rows(out, "E-L1", Side.BUY)
    assert [e.time for e in entries] == [at(sc.MON, 10), at(sc.WEEK2_OPEN, 10)]
    assert entries[1].notes.startswith("re-entry after X-L1")


def test_x_l2_rolls_the_long_below_its_minimum_dte(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet, overrides="X-L2: {params: {min_dte: 170}}")
    sale = only(out, "X-L2", Side.SELL)
    assert sale.time == at(sc.WEEK2_OPEN, 10)
    assert sale.audit["dte"] == 164
    rebought = rows(out, "E-L1", Side.BUY)[1]
    assert isinstance(rebought.instrument, OptionId)
    assert rebought.instrument.expiry == date(2027, 3, 19)
    assert rebought.notes.startswith("re-entry after X-L2")


def test_x_e1_the_window_ends_mid_week_with_positions_marked(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet, overrides=NO_TAKE_PROFIT, end=sc.WED)
    last = out.ledger[-1]
    assert last.time == at(sc.WED, 16)
    assert last.short is not None
    assert last.long is not None
    assert [e.side for e in out.blotter] == [Side.BUY, Side.SELL]  # nothing liquidated
    long_mv, short_mv = last.long.mark.notional(100, 1), last.short.mark.notional(100, 1)
    assert last.nav == last.cash + long_mv - short_mv


def test_dec_91_the_stock_without_a_quote_is_first_marked_at_the_closing_spot(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "surge_no_stock_quote", sc.BUILDERS["surge_no_stock_quote"],
              overrides=NO_TAKE_PROFIT)  # fmt: skip
    row = next(r for r in out.ledger if r.time == at(sc.FRI, 16))
    assert row.stock is not None
    assert (row.stock.mark, row.stock.stale) == (Price.from_dollars(104), True)
    assert "stale_stock" in row.flags


def test_dec_20_the_stock_is_covered_before_the_long_is_checked(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides=f"{NO_TAKE_PROFIT}\nX-L2: {{params: {{min_dte: 170}}}}")  # fmt: skip
    tuesday = [e for e in out.blotter if e.time == at(sc.WEEK2_OPEN, 10)]
    assert [(e.rule_id, e.side) for e in tuesday[:2]] == [("X-S5", Side.BUY), ("X-L2", Side.SELL)]


def test_dec_34_x_l1_and_x_l2_firing_together_are_stamped_x_l1(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "long_delta_drop", sc.long_delta_drop,
              overrides="X-L2: {params: {min_dte: 170}}")  # fmt: skip
    assert only(out, "X-L1", Side.SELL).time == at(sc.WEEK2_OPEN, 10)
    assert rows(out, "X-L2") == []


def test_dec_27_an_unevaluated_rule_logs_its_contract_and_iv_code(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """On the expiry close bar an in-the-money short has a quote but no delta (T = 0): X-S2 is
    logged, not fired, and X-S5 resolves it."""
    with capture_logs() as logs:
        run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
            overrides=NO_TAKE_PROFIT)  # fmt: skip
    events = [e for e in logs if e["event"] == "engine.exit.unevaluated"]
    closing = [e for e in events if e["time"] == at(sc.FRI, 16).isoformat()]
    assert closing
    assert closing[0]["rule"] == "X-S2"
    assert closing[0]["iv_code"] == "EXPIRED"
    assert closing[0]["option"] == "SYN 2026-09-04 C 102.0000"
