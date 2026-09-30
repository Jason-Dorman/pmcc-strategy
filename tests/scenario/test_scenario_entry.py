"""Entry, sizing and the skip-week gates in full runs (TEST-STRATEGY §4, §5; DEC-20 to DEC-22,
DEC-28). Every run checks INV-01 to INV-10 on every bar."""

from datetime import date
from fractions import Fraction
from pathlib import Path

from pmcc.domain.instruments import OptionId, Side
from pmcc.domain.money import Money, Price
from pmcc.strategy.ports import GateStatus
from tests.fixtures.synthetic import scenarios as sc
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import at, only, rows, run


def _short(event_instrument: object) -> OptionId:
    assert isinstance(event_instrument, OptionId)
    return event_instrument


def test_e_l1_the_long_enters_on_the_windows_first_bar(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet)
    long = only(out, "E-L1", Side.BUY)
    assert long.time == at(sc.MON, 10)
    assert long.fill == long.limit  # spread_capture 0: at mid
    assert long.audit["delta"] is not None


def test_e_l1_retries_the_next_session_after_e_t1_fails_all_day(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "entry_retry", sc.entry_retry)
    assert only(out, "E-L1", Side.BUY).time == at(sc.TUE, 10)
    week1 = out.gate_log[0]
    assert (week1.rule_id, week1.notes) == ("E-S1", "no long held")


def test_e_t1_the_short_enters_on_the_first_bar_that_passes(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "first_bar_wide", sc.first_bar_wide)
    short = only(out, "E-S1", Side.SELL)
    assert short.time == at(sc.MON, 11)
    assert out.gate_log[0].decision_time == at(sc.MON, 11)


def test_e_l4_an_underfunded_account_never_enters(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet, cash=Money.from_dollars(1_000))
    assert out.blotter == ()
    blocked = [r.time for r in out.ledger if "entry_blocked" in r.flags]
    assert blocked[0] == at(sc.MON, 10)
    assert len(blocked) == 9  # once a session: E-L1 retries the next one
    assert {g.rule_id for g in out.gate_log} == {"E-S1"}


def test_e_s1_the_short_is_sold_on_the_week_open_session_after_labor_day(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "rally_through_strike", sc.rally_through_strike)
    sold = rows(out, "E-S1", Side.SELL)
    assert [e.time for e in sold] == [at(sc.MON, 10), at(sc.WEEK2_OPEN, 10)]
    assert [g.session for g in out.gate_log] == [sc.MON, sc.WEEK2_OPEN]


def test_e_s2_the_short_expires_on_the_weeks_final_session(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "independence_day_week", sc.independence_day_week)
    first = only(out, "E-S1", Side.SELL) if len(rows(out, "E-S1")) == 1 else rows(out, "E-S1")[0]
    assert _short(first.instrument).expiry == date(2026, 7, 2)


def test_e_s4_the_short_matches_the_long_quantity(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet, overrides="E-L4: {params: {contracts: 2}}",
              cash=Money.from_dollars(20_000))  # fmt: skip
    assert only(out, "E-L1", Side.BUY).qty == 2
    assert only(out, "E-S1", Side.SELL).qty == 2


def test_e_s5_the_entry_records_its_terms(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet)
    short = only(out, "E-S1", Side.SELL)
    assert short.audit["e_s5_satisfied"] is True
    assert short.audit["e_s5_strike_gap"] == "12.0000"
    assert short.audit["funds_after"] is not None


def test_g_1_a_short_that_never_passes_e_t1_skips_the_week(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "no_quote_monday", sc.no_quote_monday)
    week1 = out.gate_log[0]
    assert (week1.outcome, week1.rule_id, week1.decision_time) == ("skipped", "G-1", None)
    assert [g.status for g in week1.gates] == [GateStatus.FIRE, GateStatus.NOT_EVALUATED]
    assert week1.selected is not None  # a short was selected and frozen, then never passed
    assert not [e for e in rows(out, "E-S1") if e.time.date() == sc.MON]


def test_g_2_an_expensive_long_fails_e_s5_and_skips_the_week(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "expensive_long", sc.expensive_long)
    assert rows(out, "E-S1") == []
    for week in out.gate_log:
        assert (week.outcome, week.rule_id) == ("skipped", "G-2")
        assert [g.status for g in week.gates] == [GateStatus.PASS, GateStatus.FIRE]
        assert week.gates[1].values["satisfied"] is False


def test_dec_22_one_gate_log_row_per_week_open_session(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "random_walk", sc.random_walk)
    sessions = [g.session for g in out.gate_log]
    assert len(sessions) == len(set(sessions)) == 4
    assert all(out.gate_log[i].session.weekday() <= 1 for i in range(4))


def test_dec_28_the_short_waits_for_the_long_check(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "long_unquoted_until_noon", lambda: sc.long_unquoted_at_open(12))
    week2 = out.gate_log[1]
    assert week2.session == sc.WEEK2_OPEN
    assert week2.decision_time is not None
    assert week2.decision_time >= at(sc.WEEK2_OPEN, 12)


def test_dec_28_a_long_never_quoted_at_the_open_blocks_the_short(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "long_unquoted_at_open", sc.long_unquoted_at_open)
    week2 = out.gate_log[1]
    assert (week2.rule_id, week2.notes) == ("E-S1", "long not checked: no fresh long quote")
    assert not [e for e in out.blotter if e.time.date() == sc.WEEK2_OPEN]


def test_fills_follow_spread_capture_and_the_fee(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "quiet", sc.quiet,
              fill_model="{spread_capture: 0.5, fee_per_contract: 0.65}")  # fmt: skip
    long, short = only(out, "E-L1", Side.BUY), only(out, "E-S1", Side.SELL)
    for event, sign in ((long, 1), (short, -1)):
        bid, ask = event.audit["bid"], event.audit["ask"]
        assert isinstance(bid, int)
        assert isinstance(ask, int)
        assert event.fill == Price(round(Fraction(bid + ask, 2) + sign * Fraction(ask - bid, 4)))
        assert event.fee == Money.from_dollars("0.65")
    assert long.fill is not None
    assert long.limit is not None
    assert long.fill > long.limit


def test_dec_34_entry_notes_carry_the_decision_bars_e_t1_spread_and_e_s5_terms(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """The short froze at 10:00 (40% wide) and filled at 11:00: its notes carry the 11:00 spread
    that passed E-T1 and the E-S5 terms, not the freeze bar's mid and spread."""
    out = run(synthetic, tmp_path, "first_bar_wide", sc.first_bar_wide)
    short = only(out, "E-S1", Side.SELL)
    bid, ask = short.audit["bid"], short.audit["ask"]
    assert isinstance(bid, int)
    assert isinstance(ask, int)
    spread = round(2 * (ask - bid) / (ask + bid), 6)
    assert short.audit["e_t1_spread"] == spread
    assert f"e_t1_spread {spread}" in short.notes
    assert "strike_gap 12.0000" in short.notes
    assert "net_debit" in short.notes
    assert "spread_pct" not in short.notes
    assert "mid" not in short.audit
    assert short.audit["selected_at"] == at(sc.MON, 10).isoformat()
    assert out.gate_log[0].notes == short.notes
    long = only(out, "E-L1", Side.BUY)
    assert "e_t1_spread" in long.notes
    assert "spread_pct" not in long.notes


def test_dec_21_the_short_frozen_on_the_first_bar_is_the_one_sold(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """Spot rallies to $103 by 11:00, when a fresh selection would pick a higher strike."""
    out = run(
        synthetic, tmp_path, "short_frozen_then_rally", sc.BUILDERS["short_frozen_then_rally"]
    )
    sold = rows(out, "E-S1", Side.SELL)[0]
    assert sold.time == at(sc.MON, 11)
    assert _short(sold.instrument).strike == Price.from_dollars(102)
    assert sold.audit["selected_at"] == at(sc.MON, 10).isoformat()


def test_dec_21_the_long_frozen_on_the_first_bar_is_the_one_bought(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """Spot rallies to $110 by 11:00, when a fresh selection would pick a higher strike."""
    out = run(synthetic, tmp_path, "long_frozen_then_rally", sc.BUILDERS["long_frozen_then_rally"])
    long = only(out, "E-L1", Side.BUY)
    assert long.time == at(sc.MON, 11)
    assert _short(long.instrument).strike == Price.from_dollars(90)


def test_dec_28_the_long_is_checked_once_a_week(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """The long passes its check at week 2's first bar; its delta falls under 0.50 by 14:00, but
    it isn't checked again that week."""
    out = run(synthetic, tmp_path, "long_falls_after_check", sc.BUILDERS["long_falls_after_check"])
    assert rows(out, "X-L1") == rows(out, "X-L2") == []
    late = next(r for r in out.ledger if r.time == at(sc.WEEK2_OPEN, 14))
    assert late.long is not None
    assert late.long.delta is not None
    assert late.long.delta < 0.50


def test_dec_91_a_short_entry_that_would_leave_funds_negative_is_skipped_as_e_l4(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides="X-S1: {remove: true}", cash=Money.from_dollars(1_300))  # fmt: skip
    week2 = out.gate_log[1]
    assert (week2.outcome, week2.rule_id) == ("skipped", "E-L4")
    assert week2.notes.startswith("available funds would go negative")
    assert not [e for e in rows(out, "E-S1") if e.time.date() == sc.WEEK2_OPEN]


def test_dec_22_an_unfinished_reset_logs_its_rule_and_why(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    wide = run(synthetic, tmp_path, "reset_reentry_wide", sc.BUILDERS["reset_reentry_wide"])
    week2 = wide.gate_log[1]
    assert (week2.rule_id, week2.notes) == ("X-L1", "re-entry after X-L1 didn't pass E-T1")
    poor = run(synthetic, tmp_path, "long_delta_drop", sc.long_delta_drop,
               cash=Money.from_dollars(1_300))  # fmt: skip
    week2 = poor.gate_log[1]
    assert week2.rule_id == "X-L1"
    assert week2.notes.startswith("re-entry after X-L1 blocked by E-L4")
