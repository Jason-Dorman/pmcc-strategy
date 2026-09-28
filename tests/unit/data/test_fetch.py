"""Batched history requests: INV-12, batches of 25, verdicts, retries and outages (DEC-49, DEC-83).

Everything runs through the real `LsegProvider` over `FakeLseg`, which fails the way lseg-data
2.1.1 does, so the adapter's classification and frame reading are exercised too (TEST-STRATEGY
§6). A RIC is unanswered only on the service's own word; any other failure ends in an outage.
"""

from collections.abc import Sequence
from datetime import date

import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st
from structlog.testing import capture_logs

from pmcc.data.fetch import (
    BATCH_SIZE,
    BarRequest,
    MissReason,
    Retry,
    fetch_contracts,
    fetch_rics,
)
from pmcc.data.provider import Interval, ProviderOutageError, RawHistory, raw_schema
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from tests.fakes.lseg import (
    DAYS,
    NOT_FOUND,
    FakeLseg,
    OpenState,
    fake_provider,
)

QUOTES = ("BID", "ASK")
REQUEST = BarRequest(QUOTES, date(2026, 9, 14), date(2026, 9, 15), Interval.HOURLY)
DAILY = BarRequest(QUOTES, date(2026, 9, 14), date(2026, 9, 16), Interval.DAILY)
FETCH_DATE = date(2026, 9, 26)
EXPIRED = date(2026, 9, 18)  # before the fetch date: caret first, then live
LIVE = date(2027, 1, 15)  # after it: live only
NEVER = "NVDAI182699900.U^I26"


def _bars() -> dict[str, list[float | None]]:
    return {"BID": [1.0, 1.1, None], "ASK": [1.2, 1.3, None]}


def _rics(n: int) -> list[str]:
    return [f"NVDAI1826{10_000 + 50 * i:05d}.U^I26" for i in range(n)]


def _no_wait() -> tuple[Retry, list[float]]:
    waits: list[float] = []
    return Retry(sleep=waits.append), waits


def _call(strike: int, expiry: date = EXPIRED) -> OptionId:
    return OptionId("NVDA", expiry, Right.CALL, Price.from_dollars(strike))


def _asked(fake: FakeLseg) -> list[tuple[str, ...]]:
    return [r.universe for r in fake.requests]


# --- INV-12: missing RICs return empty series, never exceptions ------------------------------


def test_inv_12_missing_ric_returns_an_empty_series_not_an_exception() -> None:
    [a, b] = _rics(2)
    fake = FakeLseg(listed={a: _bars(), b: _bars()})

    result = fetch_rics(fake_provider(fake), [a, NEVER, b], REQUEST)

    assert result.unanswered == (NEVER,)
    assert result.series(NEVER).is_empty()
    assert result.series(NEVER).schema == raw_schema(Interval.HOURLY)
    assert result.series(a).height == 4


def test_inv_12_batch_of_only_missing_rics_returns_empty_series() -> None:
    never = [f"NVDAI182699{i:03d}.U^I26" for i in range(3)]

    result = fetch_rics(fake_provider(FakeLseg()), never, REQUEST)

    assert result.unanswered == tuple(never)
    assert all(result.misses[r].reason is MissReason.NO_DATA for r in never)
    assert result.history.rows.is_empty()


def test_inv_12_missing_contract_under_both_forms_is_empty_not_an_exception() -> None:
    result = fetch_contracts(fake_provider(FakeLseg()), [_call(999)], REQUEST, FETCH_DATE)

    assert result.unanswered == (_call(999),)
    assert result.history.rows.is_empty()


@pytest.mark.parametrize("request_", [REQUEST, DAILY], ids=["hourly", "daily"])
def test_inv_12_nothing_answered_is_empty_in_the_raw_schema(request_: BarRequest) -> None:
    result = fetch_rics(fake_provider(FakeLseg(index=DAYS)), [NEVER], request_)

    assert result.history.rows.schema == raw_schema(request_.interval)


# --- Batches and verdicts (LDG §4.4) --------------------------------------------------------


def test_fetch_asks_at_most_25_rics_per_request() -> None:
    rics = _rics(60)
    fake = FakeLseg(listed={r: _bars() for r in rics})

    result = fetch_rics(fake_provider(fake), rics, REQUEST)

    assert BATCH_SIZE == 25
    assert [len(u) for u in _asked(fake)] == [25, 25, 10]
    assert result.answered == frozenset(rics)


def test_fetch_hourly_batch_holding_a_missing_ric_is_asked_again_one_ric_at_a_time() -> None:
    # lseg-data can't build an hourly batch holding a failed RIC (the UniverseContainer error).
    [a, b] = _rics(2)
    fake = FakeLseg(listed={a: _bars(), b: _bars()})

    result = fetch_rics(fake_provider(fake), [a, NEVER, b], REQUEST)

    assert _asked(fake) == [(a, NEVER, b), (a,), (NEVER,), (b,)]
    assert result.answered == {a, b}
    [batch_error, never_error] = result.errors
    assert (batch_error.rics, batch_error.error_class) == ((a, NEVER, b), "TypeError")
    assert (never_error.rics, never_error.codes) == ((NEVER,), (NOT_FOUND["hourly"],))


def test_fetch_ric_left_out_of_a_daily_answer_is_asked_again_alone() -> None:
    [a, b] = _rics(2)
    fake = FakeLseg(listed={a: {"BID": [5.0, 5.1]}, b: {"BID": [3.0, 3.1]}}, index=DAYS)

    result = fetch_rics(fake_provider(fake), [a, NEVER, b], DAILY)

    assert _asked(fake) == [(a, NEVER, b), (NEVER,)]
    assert result.misses[NEVER].codes == (NOT_FOUND["daily"],)


def test_fetch_listed_ric_with_no_bars_is_unanswered_as_empty() -> None:
    [a, quiet] = _rics(2)
    fake = FakeLseg(listed={a: _bars(), quiet: {"BID": [None] * 3, "ASK": [None] * 3}})

    result = fetch_rics(fake_provider(fake), [a, quiet], REQUEST)

    assert _asked(fake) == [(a, quiet), (quiet,)]
    assert result.misses[quiet].reason is MissReason.EMPTY


def test_fetch_asks_a_repeated_ric_once() -> None:
    [a] = _rics(1)
    fake = FakeLseg(listed={a: _bars()})

    result = fetch_rics(fake_provider(fake), [a, a], REQUEST)

    assert _asked(fake) == [(a,)]
    assert result.requested == (a,)


def test_fetch_field_the_rics_do_not_carry_is_left_out_and_the_rics_still_answer() -> None:
    # As LSEG answered SETTLE in the P1-04 probes: each RIC's answer carries only BID, so the batch
    # comes back as flat RIC columns that can't be attributed, and each RIC is asked alone.
    rics = _rics(2)
    fake = FakeLseg(listed={r: _bars() for r in rics}, carried=set(QUOTES))
    request = BarRequest(("BID", "SETTLE"), REQUEST.start, REQUEST.end_exclusive, REQUEST.interval)

    result = fetch_rics(fake_provider(fake), rics, request)

    assert result.answered == frozenset(rics)
    assert result.unanswered == ()
    assert set(result.history.rows["field"].to_list()) == {"BID"}
    assert [e.error_class for e in result.errors] == ["Unattributable"]
    assert _asked(fake) == [tuple(rics), (rics[0],), (rics[1],)]


def test_fetch_logs_a_rejected_batch() -> None:
    [a] = _rics(1)
    fake = FakeLseg(listed={a: _bars()})

    with capture_logs() as logs:
        fetch_rics(fake_provider(fake), [a, NEVER], REQUEST)

    [event] = [e for e in logs if e["event"] == "fetch.batch.rejected"]
    assert event["size"] == 2
    assert event["error_class"] == "TypeError"


def test_fetch_logs_each_unanswered_ric_with_its_form_reason_and_codes() -> None:
    with capture_logs() as logs:
        fetch_rics(fake_provider(FakeLseg()), [NEVER, "NVDA.O"], REQUEST)

    events = {e["ric"]: e for e in logs if e["event"] == "fetch.ric.unanswered"}
    assert events[NEVER]["form"] == "expired"
    assert events[NEVER]["reason"] == "no_data"
    assert events[NEVER]["codes"] == [NOT_FOUND["hourly"]]
    # lseg-data cuts each failure's text at its first dot, so only the code and RIC stem survive.
    assert NOT_FOUND["hourly"] in events[NEVER]["message"]
    assert events["NVDA.O"]["form"] is None


def test_fetch_drops_rows_for_rics_nobody_asked_for() -> None:
    class Chatty:
        """A provider that answers every request with an extra RIC's bars too."""

        def history(
            self,
            rics: Sequence[str],
            fields: Sequence[str],
            start: date,
            end_exclusive: date,
            interval: Interval,
        ) -> RawHistory:
            fake = FakeLseg(listed={r: _bars() for r in [*rics, NEVER]})
            return fake_provider(fake).history(
                [*rics, NEVER], fields, start, end_exclusive, interval
            )

    [a] = _rics(1)

    result = fetch_rics(Chatty(), [a], REQUEST)

    assert result.answered == {a}


# --- Retries and outages (LDG §4.3, DEC-49) -------------------------------------------------


def test_fetch_transient_timeouts_that_recover_retry_the_same_request_with_backoff() -> None:
    rics = _rics(2)
    fake = FakeLseg(listed={r: _bars() for r in rics}, timeouts=2)
    retry, waits = _no_wait()

    with capture_logs() as logs:
        result = fetch_rics(fake_provider(fake), rics, REQUEST, retry=retry)

    assert _asked(fake) == [tuple(rics)] * 3
    assert waits == [2.0, 4.0]
    assert result.answered == frozenset(rics)
    assert [e["attempt"] for e in logs if e["event"] == "fetch.retry"] == [1, 2]


def test_fetch_sustained_timeouts_are_an_outage_after_three_attempts() -> None:
    fake = FakeLseg(listed={r: _bars() for r in _rics(2)}, timeouts=1_000)
    retry, waits = _no_wait()

    with pytest.raises(ProviderOutageError, match="3 attempts"):
        fetch_rics(fake_provider(fake), _rics(2), REQUEST, retry=retry)

    assert len(fake.requests) == 3
    assert waits == [2.0, 4.0]


def test_fetch_workspace_that_dies_mid_pull_is_an_outage_and_returns_nothing() -> None:
    # The session still says Opened; only the requests fail (DEC-83).
    rics = _rics(30)
    fake = FakeLseg(listed={r: _bars() for r in rics}, dies_after=1)

    with pytest.raises(ProviderOutageError):
        fetch_rics(fake_provider(fake), rics, REQUEST, retry=_no_wait()[0])

    assert fake.state is OpenState.Opened
    assert _asked(fake) == [tuple(rics[:25])] + [tuple(rics[25:])] * 3


def test_fetch_signed_out_workspace_is_an_outage_never_unanswered() -> None:
    fake = FakeLseg(listed={r: _bars() for r in _rics(2)}, every_status=401)

    with pytest.raises(ProviderOutageError, match="401"):
        fetch_rics(fake_provider(fake), _rics(2), REQUEST, retry=_no_wait()[0])


def test_fetch_ric_hidden_by_an_http_failure_is_an_outage_never_unanswered() -> None:
    # Daily: the batch answers without the failed RIC, which then fails on its own too.
    [a, flaky] = _rics(2)
    fake = FakeLseg(
        listed={a: {"BID": [5.0, 5.1]}, flaky: {"BID": [3.0, 3.1]}},
        http_status={flaky: 503},
        index=DAYS,
    )

    with pytest.raises(ProviderOutageError, match="503"):
        fetch_rics(fake_provider(fake), [a, flaky], DAILY, retry=_no_wait()[0])


def test_fetch_permission_code_is_an_outage_never_unanswered() -> None:
    [a] = _rics(1)
    fake = FakeLseg(listed={a: _bars()}, denied={a})

    with pytest.raises(ProviderOutageError, match="UserNotPermission"):
        fetch_rics(fake_provider(fake), [a], REQUEST, retry=_no_wait()[0])


def test_fetch_outage_while_asking_one_ric_at_a_time_returns_nothing() -> None:
    # The batch is split, then Workspace dies: no RIC may be filed as unanswered.
    [a, b] = _rics(2)
    fake = FakeLseg(listed={a: _bars(), b: _bars()}, dies_after=1)

    with pytest.raises(ProviderOutageError):
        fetch_rics(fake_provider(fake), [a, NEVER, b], REQUEST, retry=_no_wait()[0])

    assert _asked(fake) == [(a, NEVER, b)] + [(a,)] * 3


def test_fetch_single_ric_answer_that_stays_unreadable_is_an_outage() -> None:
    [a] = _rics(1)
    fake = FakeLseg(listed={a: _bars()}, raises=[KeyError("x"), KeyError("x"), KeyError("x")])

    with pytest.raises(ProviderOutageError, match="KeyError"):
        fetch_rics(fake_provider(fake), [a], REQUEST, retry=_no_wait()[0])


def test_fetch_closed_session_raises_before_any_request() -> None:
    fake = FakeLseg(listed={r: _bars() for r in _rics(2)})
    provider = fake_provider(fake)
    fake.close_session()

    with pytest.raises(ProviderOutageError, match="not open"):
        fetch_rics(provider, _rics(2), REQUEST)

    assert fake.requests == []


# --- Arguments --------------------------------------------------------------------------------


def test_fetch_retry_needs_at_least_one_attempt() -> None:
    with pytest.raises(ValueError, match="at least 1 attempt"):
        Retry(attempts=0)


def test_fetch_batch_size_below_one_raises() -> None:
    with pytest.raises(ValueError, match="batch size"):
        fetch_rics(fake_provider(FakeLseg()), _rics(1), REQUEST, batch_size=0)


def test_fetch_contracts_strike_above_the_ric_limit_raises_before_any_request() -> None:
    fake = FakeLseg()

    with pytest.raises(ValueError, match=r"999\.99"):
        fetch_contracts(fake_provider(fake), [_call(180), _call(1000)], REQUEST, FETCH_DATE)

    assert fake.requests == []


# --- Contracts: the form policy (DEC-45, LDG §3) --------------------------------------------


def test_fetch_contracts_expired_contract_answering_to_its_caret_is_asked_once() -> None:
    option = _call(180)
    caret = build_ric(option, RicForm.EXPIRED)
    fake = FakeLseg(listed={caret: _bars()})

    result = fetch_contracts(fake_provider(fake), [option], REQUEST, FETCH_DATE)

    assert _asked(fake) == [(caret,)]
    assert result.answered == {option: caret}
    assert result.ric_form_used == {caret: RicForm.EXPIRED}


def test_fetch_contracts_expired_contract_answering_only_live_falls_back() -> None:
    option = _call(180)
    caret, live = build_ric(option, RicForm.EXPIRED), build_ric(option, RicForm.LIVE)
    fake = FakeLseg(listed={live: _bars()})

    result = fetch_contracts(fake_provider(fake), [option], REQUEST, FETCH_DATE)

    assert _asked(fake) == [(caret,), (live,)]
    assert result.answered == {option: live}
    assert result.ric_form_used == {live: RicForm.LIVE}
    assert result.history.rics() == {live}
    assert result.misses[caret].reason is MissReason.NO_DATA


def test_fetch_contracts_unexpired_contract_is_asked_live_only() -> None:
    option = _call(120, expiry=LIVE)
    live = build_ric(option, RicForm.LIVE)
    fake = FakeLseg(listed={live: _bars()})

    result = fetch_contracts(fake_provider(fake), [option], REQUEST, FETCH_DATE)

    assert _asked(fake) == [(live,)]
    assert result.ric_form_used == {live: RicForm.LIVE}


def test_fetch_contracts_second_round_asks_only_what_did_not_answer() -> None:
    by_caret, by_live, neither = _call(170), _call(180), _call(190)
    fake = FakeLseg(
        listed={
            build_ric(by_caret, RicForm.EXPIRED): _bars(),
            build_ric(by_live, RicForm.LIVE): _bars(),
        }
    )

    result = fetch_contracts(fake_provider(fake), [by_caret, by_live, neither], REQUEST, FETCH_DATE)

    second_round = (build_ric(by_live, RicForm.LIVE), build_ric(neither, RicForm.LIVE))
    assert second_round in _asked(fake)
    assert set(result.answered) == {by_caret, by_live}
    assert result.unanswered == (neither,)


def test_fetch_contracts_counts_one_contract_per_strike_not_per_form() -> None:
    answered, missing = _call(180), _call(999)
    fake = FakeLseg(listed={build_ric(answered, RicForm.LIVE): _bars()})

    result = fetch_contracts(fake_provider(fake), [answered, missing], REQUEST, FETCH_DATE)

    assert len(result.requested) == 4  # two contracts, each asked in two forms
    assert len(result.answered) + len(result.unanswered) == 2


def test_fetch_contracts_rows_are_sorted_across_form_rounds() -> None:
    # 180 answers to its caret in round one; 170 answers only live in round two.
    late, early = _call(170), _call(180)
    fake = FakeLseg(
        listed={build_ric(late, RicForm.LIVE): _bars(), build_ric(early, RicForm.EXPIRED): _bars()}
    )

    result = fetch_contracts(fake_provider(fake), [late, early], REQUEST, FETCH_DATE)

    rows = result.history.rows
    assert rows["ric"].n_unique() == 2
    assert rows.equals(rows.sort("ric", "field", "bar_start"))


def test_fetch_contracts_outage_between_form_rounds_returns_nothing() -> None:
    option = _call(180)
    fake = FakeLseg(listed={build_ric(option, RicForm.LIVE): _bars()}, dies_after=1)

    with pytest.raises(ProviderOutageError):
        fetch_contracts(fake_provider(fake), [option], REQUEST, FETCH_DATE, retry=_no_wait()[0])


# --- Property: every contract is answered or unanswered, whatever LSEG does -----------------

Listing = st.sampled_from(["caret", "live", "none"])


@given(
    listings=st.lists(st.tuples(Listing, st.booleans()), min_size=1, max_size=40),
    batch_size=st.integers(min_value=1, max_value=30),
)
def test_fetch_contracts_every_contract_is_answered_or_unanswered_never_both(
    listings: list[tuple[str, bool]], batch_size: int
) -> None:
    options = [
        _call(100 + i, expiry=LIVE if live_only else EXPIRED)
        for i, (_, live_only) in enumerate(listings)
    ]
    forms = {"caret": RicForm.EXPIRED, "live": RicForm.LIVE}
    listed = {
        build_ric(o, forms[how]): _bars()
        for o, (how, _) in zip(options, listings, strict=True)
        if how != "none"
    }
    fake = FakeLseg(listed=listed)

    result = fetch_contracts(
        fake_provider(fake), options, REQUEST, FETCH_DATE, batch_size=batch_size
    )

    assert max(len(u) for u in _asked(fake)) <= batch_size
    assert set(result.answered) | set(result.unanswered) == set(options)
    assert not set(result.answered) & set(result.unanswered)
    for option, (how, live_only) in zip(options, listings, strict=True):
        answerable = how == "live" or (how == "caret" and not live_only)
        assert (option in result.answered) is answerable
        if answerable:
            ric = result.answered[option]
            assert result.ric_form_used[ric] is forms[how]
            assert not result.history.rows.filter(pl.col("ric") == ric).is_empty()
