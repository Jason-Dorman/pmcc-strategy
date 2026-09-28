"""`LsegProvider`: one `get_history` call, read into long polars rows (LDG §4; DEC-49, DEC-83).

Every frame lseg-data builds becomes `(bar_start, ric, field, value)` rows or is rejected, and
every failure becomes one of the port's classes. Only the service's no-data codes count as no
data: an HTTP status, a permission code or a transport failure never do.
"""

# pandas has no type stubs, so pyright strict can't see through its return types (DEC-83).
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportMissingTypeStubs=false

from datetime import UTC, date, datetime

import pandas as pd
import polars as pl
import pytest

from pmcc.data.lseg import LsegProvider
from pmcc.data.lseg.provider import service_codes
from pmcc.data.lseg.shapes import to_long
from pmcc.data.provider import (
    Interval,
    NoDataError,
    ProviderOutageError,
    RawHistory,
    TransientError,
    UnreadableAnswerError,
    raw_schema,
)
from tests.fakes.lseg import (
    DAYS,
    FIELD_NOT_CARRIED,
    NOT_FOUND,
    Answer,
    FakeLseg,
    OpenState,
    fake_provider,
    no_data_error_for,
    no_data_message,
)

A, B, C = "NVDAJ182618000.U^J26", "NVDAJ182618500.U^J26", "NVDAJ182619000.U^J26"
NEVER = "NVDAJ182699900.U^J26"
START, END = date(2026, 9, 14), date(2026, 9, 15)
QUOTES = ("BID", "ASK")


def _bars(bid: float, ask: float) -> dict[str, list[float | None]]:
    return {"BID": [bid, bid + 0.1, None], "ASK": [ask, ask + 0.1, None]}


LISTED = {A: _bars(5.0, 5.2), B: _bars(3.0, 3.1), C: _bars(1.0, 1.1)}


def _ask(
    fake: FakeLseg,
    rics: tuple[str, ...] = (A, B),
    fields: tuple[str, ...] = QUOTES,
    interval: Interval = Interval.HOURLY,
) -> RawHistory:
    return fake_provider(fake).history(rics, fields, START, END, interval)


def _cells(history: RawHistory) -> set[tuple[str, str, float]]:
    rows = history.rows.select("ric", "field", "value").iter_rows()
    return {(ric, name, round(value, 4)) for ric, name, value in rows}


EXPECTED_AB = {
    (A, "BID", 5.0),
    (A, "BID", 5.1),
    (A, "ASK", 5.2),
    (A, "ASK", 5.3),
    (B, "BID", 3.0),
    (B, "BID", 3.1),
    (B, "ASK", 3.1),
    (B, "ASK", 3.2),
}

# --- The request ----------------------------------------------------------------------------


def test_lseg_provider_asks_for_the_rics_fields_dates_and_interval() -> None:
    fake = FakeLseg(listed=LISTED)

    _ask(fake)

    [request] = fake.requests
    assert request.universe == (A, B)
    assert request.fields == QUOTES
    assert request.interval == "hourly"
    assert (request.start, request.end) == ("2026-09-14", "2026-09-15")


# --- Frames as lseg-data builds them (LDG §4.5) ---------------------------------------------


def test_lseg_provider_reads_several_rics_as_ric_field_columns() -> None:
    assert _cells(_ask(FakeLseg(listed=LISTED))) == EXPECTED_AB


def test_lseg_provider_reads_one_ric_as_field_columns() -> None:
    # lseg-data names the columns after the RIC; field columns must not be read as RICs.
    history = _ask(FakeLseg(listed=LISTED), rics=(A,))

    assert _cells(history) == {c for c in EXPECTED_AB if c[0] == A}


def test_lseg_provider_reads_flat_ric_columns_when_one_field_was_asked() -> None:
    history = _ask(FakeLseg(listed=LISTED), fields=("ASK",))

    assert _cells(history) == {c for c in EXPECTED_AB if c[1] == "ASK"}


def test_lseg_provider_rejects_flat_ric_columns_when_several_fields_were_asked() -> None:
    # A answers only ASK and B only BID. lseg-data lays them out one column per RIC and names
    # the columns after B's field, so A's asks would be filed as bids (DEC-83).
    fake = FakeLseg(listed=LISTED, answers_with={A: {"ASK"}, B: {"BID"}})

    with pytest.raises(UnreadableAnswerError, match="RIC columns"):
        _ask(fake)


@pytest.mark.parametrize(
    ("answers_with", "error_class"),
    [({A: {"ASK"}}, "IndexError"), ({B: {"ASK"}}, "ValueError")],
    ids=["first-answers-one-field", "last-answers-one-field"],
)
def test_lseg_provider_rics_answering_different_fields_is_unreadable(
    answers_with: dict[str, set[str]], error_class: str
) -> None:
    with pytest.raises(UnreadableAnswerError) as caught:
        _ask(FakeLseg(listed=LISTED, answers_with=answers_with))

    assert caught.value.error_class == error_class


def test_lseg_provider_reads_a_listed_ric_with_no_bars_as_no_rows() -> None:
    quiet: dict[str, list[float | None]] = {"BID": [None] * 3, "ASK": [None] * 3}

    history = _ask(FakeLseg(listed={**LISTED, B: quiet}))

    assert history.rics() == {A}


def test_lseg_provider_returns_rows_in_the_raw_schema_sorted() -> None:
    history = _ask(FakeLseg(listed=LISTED))

    assert history.rows.schema == raw_schema(Interval.HOURLY)
    assert history.rows.equals(history.rows.sort("ric", "field", "bar_start"))
    assert history.rows["value"].null_count() == 0


# --- Timestamps (LDG §4.8) ------------------------------------------------------------------


def test_lseg_provider_keeps_the_hourly_stamp_as_utc_bar_start() -> None:
    history = _ask(FakeLseg(listed=LISTED), rics=(A,), fields=("BID",))

    # LSEG's 17:00 is 17:00 UTC, the bar's start: not shifted, not read as ET.
    assert history.rows["bar_start"].to_list() == [
        datetime(2026, 9, 14, 17, tzinfo=UTC),
        datetime(2026, 9, 14, 18, tzinfo=UTC),
    ]


def test_lseg_provider_keeps_daily_bars_as_dates() -> None:
    fake = FakeLseg(listed={A: {"BID": [5.0, 5.5]}}, index=DAYS)

    history = _ask(fake, rics=(A,), fields=("BID",), interval=Interval.DAILY)

    assert history.rows.schema == raw_schema(Interval.DAILY)
    assert history.rows["bar_start"].to_list() == [date(2026, 9, 14), date(2026, 9, 15)]
    assert fake.requests[0].interval == "daily"


# --- What the service says: no data, or a failure (DEC-49, DEC-83) --------------------------


def test_lseg_provider_never_listed_ric_is_no_data_with_its_code() -> None:
    with pytest.raises(NoDataError) as caught:
        _ask(FakeLseg(listed=LISTED), rics=(NEVER,))

    assert caught.value.codes == (NOT_FOUND["hourly"],)


def test_lseg_provider_field_the_ric_does_not_carry_is_no_data_with_its_own_code() -> None:
    fake = FakeLseg(listed=LISTED, carried=set(QUOTES))

    with pytest.raises(NoDataError) as caught:
        _ask(fake, rics=(A,), fields=("BID", "SETTLE"))

    assert caught.value.codes == (FIELD_NOT_CARRIED,)


def test_lseg_provider_hourly_batch_holding_a_never_listed_ric_is_unreadable() -> None:
    # lseg-data fails to build the frame (LDG §4.4's UniverseContainer TypeError).
    with pytest.raises(UnreadableAnswerError, match="UniverseContainer") as caught:
        _ask(FakeLseg(listed=LISTED), rics=(A, NEVER, B))

    assert caught.value.error_class == "TypeError"


def test_lseg_provider_daily_batch_answers_without_a_never_listed_ric() -> None:
    fake = FakeLseg(listed={A: {"BID": [5.0, 5.5]}, B: {"BID": [3.0, 3.5]}}, index=DAYS)

    history = _ask(fake, rics=(A, NEVER, B), fields=("BID",), interval=Interval.DAILY)

    assert history.rics() == {A, B}


@pytest.mark.parametrize("status", [401, 403, 500, 503])
def test_lseg_provider_http_status_is_transient_never_no_data(status: int) -> None:
    with pytest.raises(TransientError, match=str(status)):
        _ask(FakeLseg(listed=LISTED, http_status={A: status}), rics=(A,))


def test_lseg_provider_signed_out_workspace_is_transient_never_no_data() -> None:
    with pytest.raises(TransientError, match="401"):
        _ask(FakeLseg(listed=LISTED, every_status=401))


def test_lseg_provider_permission_code_is_transient_never_no_data() -> None:
    with pytest.raises(TransientError, match="UserNotPermission"):
        _ask(FakeLseg(listed=LISTED, denied={A}), rics=(A,))


def test_lseg_provider_no_data_and_http_codes_together_are_transient() -> None:
    with pytest.raises(TransientError, match="503"):
        _ask(FakeLseg(listed=LISTED, http_status={B: 503}), rics=(NEVER, B))


def test_lseg_provider_timeout_flattened_into_an_ld_error_is_transient() -> None:
    # lseg-data keeps only the text "timed out": no class, no cause, no code (DEC-83).
    with pytest.raises(TransientError, match="timed out"):
        _ask(FakeLseg(listed=LISTED, timeouts=1))


def test_lseg_provider_dead_workspace_is_transient_while_the_session_says_opened() -> None:
    fake = FakeLseg(listed=LISTED, dies_after=0)

    with pytest.raises(TransientError, match="connection"):
        _ask(fake)

    assert fake.state is OpenState.Opened


@pytest.mark.parametrize("error", [TimeoutError(), ConnectionError()])
def test_lseg_provider_unwrapped_transport_error_is_transient(error: Exception) -> None:
    with pytest.raises(TransientError):
        _ask(FakeLseg(listed=LISTED, raises=[error]))


def test_lseg_provider_other_error_while_building_is_unreadable() -> None:
    with pytest.raises(UnreadableAnswerError) as caught:
        _ask(FakeLseg(listed=LISTED, raises=[KeyError("universe")]))

    assert caught.value.error_class == "KeyError"


# --- The session (LDG §4.2) -----------------------------------------------------------------


@pytest.mark.parametrize("state", [OpenState.Closed, OpenState.Pending])
def test_lseg_provider_session_not_opened_raises_before_any_request(state: OpenState) -> None:
    fake = FakeLseg(listed=LISTED, state=state)

    with pytest.raises(ProviderOutageError, match="not open"):
        LsegProvider(fake).history((A,), QUOTES, START, END, Interval.HOURLY)

    assert fake.requests == []


def test_lseg_provider_error_after_the_session_closed_is_an_outage_not_no_data() -> None:
    # Something closes the session during the call: its error must not be filed as no data.
    fake = FakeLseg(listed=LISTED)
    provider = fake_provider(fake)

    def close_then_fail() -> Exception:
        fake.state = OpenState.Closed
        return no_data_error_for(NEVER)

    fake.raises.append(close_then_fail)

    with pytest.raises(ProviderOutageError, match="closed"):
        provider.history((A, B), QUOTES, START, END, Interval.HOURLY)


# --- Reading lseg-data's "No data to return" message ----------------------------------------


def test_lseg_provider_service_codes_reads_each_failure_code() -> None:
    answers = [
        Answer(NEVER, {"data": []}, (NOT_FOUND["hourly"], f"{NEVER} - The universe is not found")),
        Answer(B, {"data": []}, (503, "Service Unavailable")),
    ]

    assert service_codes(no_data_message(answers)) == (NOT_FOUND["hourly"], "503")


def test_lseg_provider_service_codes_reads_nothing_from_other_text() -> None:
    assert service_codes("timed out (TS.Intraday.UserRequestError.90001, x)") == ()


# --- The normalizer on shapes lseg-data 2.1.1 doesn't build ---------------------------------


def test_to_long_reads_field_ric_columns() -> None:
    columns = pd.MultiIndex.from_tuples([("BID", A), ("BID", B)])
    frame = pd.DataFrame(
        [[5.0, 3.0]], index=pd.DatetimeIndex(["2026-09-14 17:00"]), columns=columns
    )

    rows = to_long(frame, (A, B), QUOTES, Interval.HOURLY)

    assert rows.select("ric", "field").rows() == [(A, "BID"), (B, "BID")]


def test_to_long_converts_an_aware_index_to_utc() -> None:
    index = pd.DatetimeIndex(["2026-09-14 13:00"]).tz_localize("America/New_York")
    frame = pd.DataFrame({"BID": [5.0]}, index=index)

    rows = to_long(frame, (A,), ("BID",), Interval.HOURLY)

    assert rows["bar_start"].to_list() == [datetime(2026, 9, 14, 17, tzinfo=UTC)]


@pytest.mark.parametrize("dtype", ["Float64", "float64", "Int64", "object"])
def test_to_long_reads_plain_nullable_and_object_columns(dtype: str) -> None:
    frame = pd.DataFrame({"BID": [5, None]}, index=pd.DatetimeIndex(["2026-09-14"] * 2))

    rows = to_long(frame.astype(dtype), (A,), ("BID",), Interval.HOURLY)

    assert rows["value"].to_list() == [5.0]


def test_to_long_drops_text_that_is_not_a_number() -> None:
    frame = pd.DataFrame({"BID": ["5.0", "n/a"]}, index=pd.DatetimeIndex(["2026-09-14"] * 2))

    rows = to_long(frame, (A,), ("BID",), Interval.HOURLY)

    assert rows["value"].to_list() == [5.0]


def test_to_long_ignores_columns_nobody_asked_for() -> None:
    columns = pd.MultiIndex.from_tuples([(A, "BID"), (A, "EXTRA"), ("OTHER.O", "BID")])
    frame = pd.DataFrame([[5.0, 1.0, 2.0]], index=pd.DatetimeIndex(["2026-09-14"]), columns=columns)

    rows = to_long(frame, (A,), ("BID",), Interval.HOURLY)

    assert rows.select("ric", "field").rows() == [(A, "BID")]


def test_to_long_answer_with_only_unasked_fields_is_no_rows() -> None:
    columns = pd.MultiIndex.from_tuples([(A, "EXTRA"), (B, "EXTRA")])
    frame = pd.DataFrame([[1.0, 2.0]], index=pd.DatetimeIndex(["2026-09-14"]), columns=columns)

    rows = to_long(frame, (A, B), ("BID",), Interval.HOURLY)

    assert rows.is_empty()
    assert rows.schema == raw_schema(Interval.HOURLY)


@pytest.mark.parametrize("interval", list(Interval))
@pytest.mark.parametrize("frame", [None, pd.DataFrame()])
def test_to_long_empty_answer_is_no_rows_in_the_raw_schema(
    frame: pd.DataFrame | None, interval: Interval
) -> None:
    rows = to_long(frame, (A,), ("BID",), interval)

    assert rows.is_empty()
    assert rows.schema == raw_schema(interval)


def test_to_long_rejects_columns_that_match_no_ric_or_field() -> None:
    frame = pd.DataFrame({"???": [1.0]}, index=pd.DatetimeIndex(["2026-09-14"]))

    with pytest.raises(UnreadableAnswerError, match="attribute"):
        to_long(frame, (A, B), ("BID",), Interval.HOURLY)


def test_to_long_rejects_a_multiindex_holding_none_of_the_rics() -> None:
    columns = pd.MultiIndex.from_tuples([("OTHER.O", "BID")])
    frame = pd.DataFrame([[1.0]], index=pd.DatetimeIndex(["2026-09-14"]), columns=columns)

    with pytest.raises(UnreadableAnswerError, match="no level"):
        to_long(frame, (A, B), ("BID",), Interval.HOURLY)


def test_to_long_rejects_field_columns_for_several_rics() -> None:
    frame = pd.DataFrame({"BID": [1.0]}, index=pd.DatetimeIndex(["2026-09-14"]))

    with pytest.raises(UnreadableAnswerError, match="attribute"):
        to_long(frame, (A, B), ("BID",), Interval.HOURLY)


def test_to_long_rejects_ric_columns_named_for_a_field_not_asked() -> None:
    frame = pd.DataFrame({A: [1.0], B: [2.0]}, index=pd.DatetimeIndex(["2026-09-14"]))
    frame.columns.name = "ASK"

    with pytest.raises(UnreadableAnswerError, match="named"):
        to_long(frame, (A, B), ("BID",), Interval.HOURLY)


def test_to_long_rejects_an_answer_that_is_not_a_frame() -> None:
    with pytest.raises(UnreadableAnswerError, match="DataFrame"):
        to_long("nope", (A,), ("BID",), Interval.HOURLY)


def test_raw_history_refuses_rows_in_the_wrong_schema() -> None:
    with pytest.raises(ValueError, match="schema"):
        RawHistory(Interval.HOURLY, pl.DataFrame({"ric": [A]}))
