"""`thesis probe`'s report (T1-01): each source's section, one failing never hiding the others,
and a console line with counts and dates but no values."""

import json
from datetime import date, datetime

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.clock import ET
from pmcc.thesis import probe
from pmcc.thesis.fred import FredUnavailableError
from pmcc.thesis.probe import INDEX_RIC, VIX_RIC, Sources, describe, has_closes, run_probe
from tests.fakes.thesis_probe import (
    FRED_KEY,
    FRED_TEXT,
    RULES,
    ChainProvider,
    FakeFinder,
    daily,
    oas_table,
)

CAL = load_calendar()
NOW = datetime(2026, 11, 20, 22, 0, tzinfo=ET)  # Fri Nov 20's close is the last
SESSION = date(2026, 11, 20)
EXPIRY = date(2026, 12, 23)  # 30 days from Mon Nov 23
START = date(2026, 1, 2)


def _closes(spot: float = 6600.0, vix: float = 20.0) -> dict[str, dict[date, float]]:
    index = daily(START, [6000.0 + i for i in range(300)], CAL)
    fear = daily(START, [15.0 + (i % 7) for i in range(300)], CAL)
    index = {d: v for d, v in index.items() if d <= SESSION} | {SESSION: spot}
    fear = {d: v for d, v in fear.items() if d <= SESSION} | {SESSION: vix}
    return {INDEX_RIC: index, VIX_RIC: fear}


def _provider(**kwargs: object) -> ChainProvider:
    closes = kwargs.pop("closes", _closes())
    return ChainProvider(CAL, closes, SESSION, EXPIRY, **kwargs)  # pyright: ignore[reportArgumentType]


def _finder() -> FakeFinder:
    hit: dict[str, str | None] = {"RIC": "HYOAS=X", "DocumentTitle": "ICE BofA US High Yield OAS"}
    return FakeFinder(
        hits={probe.CREDIT_QUERIES[0]: [hit], probe.CREDIT_QUERIES[1]: [hit]},
        tables={"HYOAS=X": oas_table("HYOAS=X", [date(2014, 1, 2), date(2026, 11, 20)])},
    )


def _no_wait(_seconds: float) -> None:
    pass


def _report(
    provider: ChainProvider | None = None, finder: FakeFinder | None = None, fred: str = FRED_TEXT
) -> dict[str, object]:
    sources = Sources(
        provider or _provider(), finder or _finder(), lambda _url: fred, FRED_KEY, _no_wait
    )
    return run_probe(sources, CAL, NOW, RULES)


def _section(report: dict[str, object], *path: str) -> dict[str, object]:
    node: object = report
    for key in path:
        assert isinstance(node, dict)
        node = node[key]  # pyright: ignore[reportUnknownVariableType]
    assert isinstance(node, dict)
    return node  # pyright: ignore[reportUnknownVariableType]


def test_t1_01_closes_report_each_series_coverage() -> None:
    report = _report()
    index = _section(report, "closes", INDEX_RIC)

    assert index["first"] == START.isoformat()
    assert index["last"] == SESSION.isoformat()
    assert index["field_counts"] == {
        "TRDPRC_1": index["sessions"],
        "HIGH_1": 0,
        "LOW_1": 0,
        "OPEN_PRC": 0,
    }
    assert has_closes(report)


def test_t1_01_closes_report_days_one_series_lacks() -> None:
    closes = _closes()
    missing = sorted(closes[VIX_RIC])[10]
    del closes[VIX_RIC][missing]
    report = _report(_provider(closes=closes))

    assert _section(report, "closes", "index_not_vix") == {
        "count": 1,
        "first": [missing.isoformat()],
    }
    assert _section(report, "closes", "vix_not_index")["count"] == 0


def test_t1_01_closes_report_calendar_sessions_without_a_bar() -> None:
    closes = _closes()
    gap = date(2026, 3, 10)
    del closes[INDEX_RIC][gap]
    against = _section(_report(_provider(closes=closes)), "closes", INDEX_RIC, "against_calendar")

    assert gap.isoformat() in against["sessions_without_bar"]["first"]  # pyright: ignore[reportIndexIssue]


def test_t1_01_no_vix_means_the_probe_fails_its_one_hard_requirement() -> None:
    closes = _closes()
    del closes[VIX_RIC]
    report = _report(_provider(closes=closes))

    assert not has_closes(report)
    assert _section(report, "closes", "unanswered") == {VIX_RIC: "no_data"}


def test_t1_01_credit_on_lseg_reads_each_found_ric_once() -> None:
    section = _section(_report(), "credit_lseg")
    tables = section["tables"]

    assert isinstance(tables, list)
    assert len(tables) == 1  # pyright: ignore[reportUnknownArgumentType]
    table = tables[0]  # pyright: ignore[reportUnknownVariableType]
    assert table["ric"] == "HYOAS=X"
    assert table["columns"] == ["VALUE"]
    assert table["first"] == "2014-01-02"
    assert table["rows"] == 2


def test_t1_01_a_failing_search_is_reported_and_the_rest_still_runs() -> None:
    report = _report(finder=FakeFinder(fails=True))
    searches = _section(report, "credit_lseg")["searches"]

    assert all("TransientError" in s["error"] for s in searches)  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
    assert has_closes(report)
    assert _section(report, "credit_fred")["valued"] == 2
    assert _section(report, "spxw")["condor"] is not None


def test_t1_01_fred_coverage_counts_blank_days_apart() -> None:
    assert _section(_report(), "credit_fred") == {
        "series": "BAMLH0A0HYM2",
        "rows": 3,
        "valued": 2,
        "blank": 1,
        "first": "2023-11-20",
        "last": "2023-11-22",
        "last_value_percent": 3.98,
    }


def test_t1_01_a_fred_answer_that_isnt_json_is_reported() -> None:
    report = _report(fred="<html>maintenance</html>\n")
    assert "not JSON" in str(_section(report, "credit_fred")["error"])


def test_t1_01_fred_not_answering_is_an_outage_and_aborts() -> None:
    def down(_url: str) -> str:
        raise FredUnavailableError("FRED did not answer: TimeoutError")

    with pytest.raises(FredUnavailableError):
        run_probe(Sources(_provider(), _finder(), down, FRED_KEY, _no_wait), CAL, NOW, RULES)


def test_t1_01_an_lseg_outage_aborts_the_probe() -> None:
    class Down(ChainProvider):
        def history(self, *args: object, **kwargs: object) -> object:  # pyright: ignore[reportIncompatibleMethodOverride]
            raise ProviderOutageError("the LSEG session is not open")

    with pytest.raises(ProviderOutageError):
        _report(Down(CAL, _closes(), SESSION, EXPIRY))


def test_t1_01_a_ric_found_twice_is_read_once() -> None:
    hit: dict[str, str | None] = {"RIC": "HYOAS=X", "DocumentTitle": "OAS"}
    twin: dict[str, str | None] = {"RIC": "HYOAS=X", "DocumentTitle": "OAS, again"}
    finder = FakeFinder(
        hits={probe.CREDIT_QUERIES[0]: [hit, twin]},
        tables={"HYOAS=X": oas_table("HYOAS=X", [date(2014, 1, 2)])},
    )
    tables = _section(_report(finder=finder), "credit_lseg")["tables"]
    assert isinstance(tables, list)
    assert len(tables) == 1  # pyright: ignore[reportUnknownArgumentType]


def test_t1_01_listed_counts_ric_answers_not_close_quotes() -> None:
    counts = _section(_report(), "spxw", "counts")
    assert counts["listed"] == counts["asked"]


def test_t1_01_spxw_finds_the_spelling_lseg_answers() -> None:
    section = _section(_report(), "spxw")
    spellings = section["spellings"]

    assert section["spelling"] == "SPXW, lower-case month"
    assert section["expiry"] == EXPIRY.isoformat()
    assert section["dte"] == 30
    assert [s["listed"] for s in spellings] == [  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
        [True, True],
        [False, False],
        [False, False],
        [False, False],
    ]


def test_t1_01_spxw_prices_a_condor_with_its_cost_share() -> None:
    section = _section(_report(), "spxw")
    condor = _section(section, "condor")

    assert section["parity_spot"] == pytest.approx(6600.0, rel=1e-3)
    assert condor["width"] == 35
    assert condor["fees_points"] == pytest.approx(0.16)
    share = condor["round_trip_cost_share_of_mid_credit"]
    assert isinstance(share, float)
    assert 0 < share < 1


def test_t1_01_spxw_without_any_spelling_answering_reports_it() -> None:
    class Unlisted(ChainProvider):
        def _quote(self, ric: str) -> tuple[float, float] | None:
            return None

    provider = Unlisted(CAL, _closes(), SESSION, EXPIRY)
    section = _section(_report(provider), "spxw")
    assert section["error"] == "LSEG answered no spelling of the ATM pair"


def test_t1_01_the_console_shows_counts_and_dates_never_values() -> None:
    report = _report(_provider(closes=_closes(spot=6612.34, vix=21.87)))
    lines = describe(report)
    text = "\n".join(lines)

    assert len(lines) == 4
    for value in ("6612", "21.87", "3.98"):
        assert value not in text
    for day in ("2026-11-20", "2026-12-23"):
        assert day in text


def test_t1_01_the_report_is_json() -> None:
    json.dumps(_report(), allow_nan=False)
