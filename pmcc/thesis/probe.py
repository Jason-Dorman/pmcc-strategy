"""`thesis probe`: what the thesis's data sources actually hold (T1-01; TD-04, TD-05, TD-07).

Four sections:

1. **Closes:** the S&P 500 index's (`.SPX`) and VIX's (`.VIX`) daily bars from 2014-01-01 over the
   platform session: each field's count, the first and last session, the days one has and the
   other lacks, and the days either disagrees with the session calendar where it reaches.
2. **Credit on LSEG:** search for ICE BofA US High Yield OAS, and each of the first few RICs found
   read as a daily table with whatever columns LSEG sends: their names, rows, first and last day.
3. **Credit on FRED:** BAMLH0A0HYM2 from its official API (TD-05, TD-17): rows, valued days, first
   and last. FRED refusing the request or answering unreadably is reported; FRED not answering is
   an outage.
4. **SPXW:** the chain about 30 days out at the last close, and a rough 0.20-delta condor priced
   from it (`pmcc.thesis.spxw`): R5's cost sample (TD-07).

Each section reports its source's answer, or why it couldn't be read (a search refused, no SPXW
spelling listed), so one section's failure doesn't hide the others'. An outage, LSEG's session
dropping or FRED not answering, aborts the whole probe with nothing written (TD-14).

The report, with every value, goes to a file (gitignored; in Actions a one-day artifact, as the
live probe's, LD-21). The console line carries counts and dates only. Nothing is cached and
nothing committed: the probe decides what T3-01 pulls, it isn't a pull.
"""

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol, cast, final

import polars as pl

from pmcc.data.fetch import BarRequest, fetch_rics
from pmcc.data.provider import (
    DailyTable,
    HistoryProvider,
    Interval,
    NoDataError,
    TransientError,
    UnreadableAnswerError,
)
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.sessions import Session
from pmcc.live.snapshot import last_completed, next_session
from pmcc.thesis import spxw
from pmcc.thesis.config import CostSampleConfig
from pmcc.thesis.fred import FredError, FredKey, FredSeries, fetch_series

INDEX_RIC = ".SPX"
VIX_RIC = ".VIX"
CLOSE = "TRDPRC_1"
CLOSE_FIELDS = (CLOSE, "HIGH_1", "LOW_1", "OPEN_PRC")
HISTORY_START = date(2014, 1, 1)
CREDIT_QUERIES = (
    "ICE BofA US High Yield Index Option-Adjusted Spread",
    "BAMLH0A0HYM2",
    "US High Yield OAS",
    "ICE BofA US High Yield Index",
)
SEARCH_SELECT = "RIC,DocumentTitle"
SEARCH_TOP = 10
MAX_TABLES = 6
FRED_SERIES = "BAMLH0A0HYM2"
LISTED = 10  # days listed in a mismatch, besides the count
_DAY = timedelta(days=1)

# What a section's source may raise and still have answered: reported in the section. An outage
# (`ProviderOutageError`, `FredUnavailableError`) isn't caught: it aborts the probe, which then
# writes nothing (CLAUDE.md, LSEG access and FRED).
SOURCE_ERRORS = (TransientError, UnreadableAnswerError, NoDataError, ValueError)

type Json = dict[str, object]
type GetText = Callable[[str], str]


class SeriesFinder(Protocol):
    """LSEG's search and column-agnostic daily history (`pmcc.data.lseg.discovery`)."""

    def search(self, query: str, select: str, top: int) -> list[dict[str, str | None]]: ...

    def table(self, ric: str, start: date, end_exclusive: date) -> DailyTable: ...


@final
@dataclass(frozen=True, slots=True)
class Sources:
    provider: HistoryProvider
    finder: SeriesFinder
    get_text: GetText
    fred_key: FredKey
    sleep: Callable[[float], None] = lambda seconds: time.sleep(seconds)  # between FRED's tries


def run_probe(
    sources: Sources, calendar: SessionCalendar, now: datetime, rules: CostSampleConfig
) -> Json:
    """The probe's report: when, then each section. Raises on an outage, before any report."""
    end = now.date() + _DAY
    closes_report, closes = closes_section(sources.provider, calendar, HISTORY_START, end)
    return {
        "taken_at": now.isoformat(),
        "history_start": HISTORY_START.isoformat(),
        "closes": closes_report,
        "credit_lseg": credit_lseg_section(sources.finder, HISTORY_START, end),
        "credit_fred": fred_section(sources.get_text, sources.fred_key, sources.sleep),
        "spxw": spxw_section(sources.provider, calendar, now, closes, rules),
    }


# --- 1. closes -------------------------------------------------------------------------------


def closes_section(
    provider: HistoryProvider, calendar: SessionCalendar, start: date, end_exclusive: date
) -> tuple[Json, dict[str, dict[date, float]]]:
    request = BarRequest(CLOSE_FIELDS, start, end_exclusive, Interval.DAILY)
    try:
        result = fetch_rics(provider, [INDEX_RIC, VIX_RIC], request)
    except SOURCE_ERRORS as exc:
        return {"error": _error(exc)}, {}
    rows = result.history.rows
    closes = {ric: _closes(rows, ric) for ric in (INDEX_RIC, VIX_RIC)}
    report: Json = {
        ric: _series_report(rows, ric, closes[ric], calendar) for ric in (INDEX_RIC, VIX_RIC)
    }
    report["unanswered"] = {ric: str(result.misses[ric].reason) for ric in result.unanswered}
    report["index_not_vix"] = _days(set(closes[INDEX_RIC]) - set(closes[VIX_RIC]))
    report["vix_not_index"] = _days(set(closes[VIX_RIC]) - set(closes[INDEX_RIC]))
    return report, closes


def _closes(rows: pl.DataFrame, ric: str) -> dict[date, float]:
    picked = rows.filter((pl.col("ric") == ric) & (pl.col("field") == CLOSE)).sort("bar_start")
    return dict(zip(picked["bar_start"].to_list(), picked["value"].to_list(), strict=True))


def _series_report(
    rows: pl.DataFrame, ric: str, closes: Mapping[date, float], calendar: SessionCalendar
) -> Json:
    mine = rows.filter(pl.col("ric") == ric)
    counts = {f: mine.filter(pl.col("field") == f).height for f in CLOSE_FIELDS}
    days = sorted(closes)
    return {
        "field_counts": counts,
        "sessions": len(days),
        "first": days[0].isoformat() if days else None,
        "last": days[-1].isoformat() if days else None,
        "last_close": closes[days[-1]] if days else None,
        "against_calendar": _against_calendar(days, calendar),
    }


def _against_calendar(days: Sequence[date], calendar: SessionCalendar) -> Json:
    """Where the tape and the calendar overlap: calendar sessions with no bar, bars on days the
    calendar closes (the calendar answers only inside its span)."""
    if not days:
        return {"span": None}
    low, high = max(days[0], calendar.first_day), min(days[-1], calendar.last_day)
    if low > high:
        return {"span": None}
    have = {d for d in days if low <= d <= high}
    sessions = {s.day for s in calendar.sessions(low, high)}
    return {
        "span": [low.isoformat(), high.isoformat()],
        "sessions_without_bar": _days(sessions - have),
        "bars_on_closed_days": _days(have - sessions),
    }


def _days(days: set[date]) -> Json:
    ordered = sorted(days)
    return {"count": len(ordered), "first": [d.isoformat() for d in ordered[:LISTED]]}


# --- 2. credit on LSEG -----------------------------------------------------------------------


def credit_lseg_section(finder: SeriesFinder, start: date, end_exclusive: date) -> Json:
    searches: list[Json] = []
    rics: list[str] = []
    for query in CREDIT_QUERIES:
        try:
            hits = finder.search(query, SEARCH_SELECT, SEARCH_TOP)
        except SOURCE_ERRORS as exc:
            searches.append({"query": query, "error": _error(exc)})
            continue
        searches.append({"query": query, "hits": hits})
        rics = list(dict.fromkeys([*rics, *(ric for hit in hits if (ric := hit.get("RIC")))]))
    tables = [_table_report(finder, ric, start, end_exclusive) for ric in rics[:MAX_TABLES]]
    return {"searches": searches, "tables": tables}


def _table_report(finder: SeriesFinder, ric: str, start: date, end_exclusive: date) -> Json:
    try:
        table = finder.table(ric, start, end_exclusive)
    except SOURCE_ERRORS as exc:
        return {"ric": ric, "error": _error(exc)}
    days = [day for day, _ in table.rows]
    return {
        "ric": ric,
        "columns": list(table.columns),
        "rows": len(table.rows),
        "first": days[0].isoformat() if days else None,
        "last": days[-1].isoformat() if days else None,
        "valued": {name: len(table.column(name)) for name in table.columns},
        "last_row": list(table.rows[-1][1]) if table.rows else None,
    }


# --- 3. credit on FRED -----------------------------------------------------------------------


def fred_section(
    get_text: GetText, key: FredKey, sleep: Callable[[float], None] = time.sleep
) -> Json:
    try:
        series = fetch_series(FRED_SERIES, key, get_text, sleep=sleep)
    except FredError as exc:
        return {"series": FRED_SERIES, "error": _error(exc)}
    return _fred_report(series)


def _fred_report(series: FredSeries) -> Json:
    valued = series.valued
    return {
        "series": series.series,
        "rows": len(series.observations),
        "valued": len(valued),
        "blank": len(series.observations) - len(valued),
        "first": valued[0][0].isoformat() if valued else None,
        "last": valued[-1][0].isoformat() if valued else None,
        "last_value_percent": valued[-1][1] if valued else None,
    }


# --- 4. SPXW ---------------------------------------------------------------------------------


def spxw_section(
    provider: HistoryProvider,
    calendar: SessionCalendar,
    now: datetime,
    closes: Mapping[str, Mapping[date, float]],
    rules: CostSampleConfig,
) -> Json:
    try:
        session = last_completed(calendar, now)
        execution = next_session(calendar, now).day
    except ValueError as exc:
        return {"error": _error(exc)}
    spot = closes.get(INDEX_RIC, {}).get(session.day)
    vix = closes.get(VIX_RIC, {}).get(session.day)
    expiry = spxw.pick_expiry(calendar, execution, rules)
    base: Json = {"session": session.day.isoformat(), "execution": execution.isoformat()}
    if spot is None or vix is None or expiry is None:
        return base | {"error": f"no index or VIX close for {session.day}, or no expiry"}
    base |= {"expiry": expiry.isoformat(), "dte": (expiry - execution).days, "index_close": spot}
    try:
        return base | _chain(provider, _Market(calendar, session, expiry, spot, vix), rules)
    except SOURCE_ERRORS as exc:
        return base | {"error": _error(exc)}


@final
@dataclass(frozen=True, slots=True)
class _Market:
    """The close the chain is read at."""

    calendar: SessionCalendar
    session: Session
    expiry: date
    spot: float
    vix: float

    @property
    def years(self) -> float:
        return spxw.years_from_close(self.session, self.calendar, self.expiry)


def _chain(provider: HistoryProvider, market: _Market, rules: CostSampleConfig) -> Json:
    atm = spxw.atm_strike(market.spot, rules)
    spellings, chosen = _spelling(provider, market, atm)
    if chosen is None:
        return {"spellings": spellings, "error": "LSEG answered no spelling of the ATM pair"}
    legs = _ladder_legs(provider, market, chosen, atm, rules)
    pair = {leg.right: leg for leg in legs if leg.strike == atm}
    forward_spot = None
    if Right.CALL in pair and Right.PUT in pair:
        forward_spot = spxw.parity_spot(pair[Right.CALL], pair[Right.PUT], market.years, rules)
    spot = forward_spot or market.spot
    priced = spxw.priced(legs, spot, market.years, rules)
    found = spxw.condor(priced, spot, rules)
    return {
        "spellings": spellings,
        "spelling": chosen.name,
        "years": market.years,
        "rate": rules.rate_decimal,
        "parity_spot": forward_spot,
        "counts": _leg_counts(priced, rules),
        "condor": _condor_report(found),
        "legs": [_leg_row(leg, rules) for leg in priced],
    }


def _spelling(
    provider: HistoryProvider, market: _Market, atm: int
) -> tuple[list[Json], spxw.Spelling | None]:
    rights = (Right.CALL, Right.PUT)
    rics = {
        s: tuple(spxw.option_ric(s, market.expiry, right, atm) for right in rights)
        for s in spxw.SPELLINGS
    }
    asked = [r for pair in rics.values() for r in pair]
    listed, _ = spxw.close_quotes(provider, asked, market.session)
    report: list[Json] = [
        {"spelling": s.name, "rics": list(pair), "listed": [r in listed for r in pair]}
        for s, pair in rics.items()
    ]
    chosen = next((s for s, pair in rics.items() if all(r in listed for r in pair)), None)
    return report, chosen


def _ladder_legs(
    provider: HistoryProvider,
    market: _Market,
    spelling: spxw.Spelling,
    atm: int,
    rules: CostSampleConfig,
) -> list[spxw.Leg]:
    put_k, call_k = spxw.estimated_strikes(market.spot, market.vix, market.years, rules)
    puts = spxw.ladder(put_k * rules.put_window_low, put_k * rules.put_window_high, rules)
    calls = spxw.ladder(call_k * rules.call_window_low, call_k * rules.call_window_high, rules)
    wanted = [(Right.PUT, k) for k in puts] + [(Right.CALL, k) for k in calls]
    unique = list(dict.fromkeys([*wanted, (Right.PUT, atm), (Right.CALL, atm)]))
    rics = {spxw.option_ric(spelling, market.expiry, right, k): (right, k) for right, k in unique}
    listed, quotes = spxw.close_quotes(provider, list(rics), market.session)
    return [
        spxw.Leg(ric, right, k, *quotes.get(ric, (None, None)), listed=ric in listed)
        for ric, (right, k) in rics.items()
    ]


def _leg_counts(legs: Sequence[spxw.Leg], rules: CostSampleConfig) -> Json:
    return {
        "asked": len(legs),
        "listed": len([leg for leg in legs if leg.listed]),
        "quoted": len([leg for leg in legs if leg.quoted]),
        "tight": len([leg for leg in legs if leg.tight(rules)]),
        "priced": len([leg for leg in legs if leg.delta is not None]),
    }


def _condor_report(found: spxw.Condor | None) -> Json | None:
    if found is None:
        return None
    mid = found.mid_credit
    cost = found.round_trip_spread + found.fees
    return {
        "legs": [_leg_row(leg) for leg in found.legs],  # each passed the spread test
        "width": found.width,
        "natural_credit": found.natural_credit,
        "mid_credit": mid,
        "max_loss_at_natural": found.width - found.natural_credit,
        "round_trip_spread": found.round_trip_spread,
        "fees_points": found.fees,
        "round_trip_cost_share_of_mid_credit": cost / mid if mid > 0 else None,
    }


def _leg_row(leg: spxw.Leg, rules: CostSampleConfig | None = None) -> Json:
    """A leg's row, with `tight` (the spread test) when `rules` are given."""
    row: Json = {
        "ric": leg.ric,
        "right": leg.right.name.lower(),
        "strike": leg.strike,
        "bid": leg.bid,
        "ask": leg.ask,
        "iv": leg.iv,
        "delta": leg.delta,
        "listed": leg.listed,
    }
    if rules is not None:
        row["tight"] = leg.tight(rules)
    return row


def has_closes(report: Json) -> bool:
    """Whether both the index's and VIX's closes came back: the probe's one hard requirement."""
    closes = _section(report, "closes")
    return all(_section(closes, ric).get("sessions") for ric in (INDEX_RIC, VIX_RIC))


# --- the console line ------------------------------------------------------------------------


def describe(report: Json) -> list[str]:
    """Counts and dates only, no values (LD-21's rule for the live probe, kept here)."""
    return [
        _describe_closes(_section(report, "closes")),
        _describe_lseg(_section(report, "credit_lseg")),
        _describe_fred(_section(report, "credit_fred")),
        _describe_spxw(_section(report, "spxw")),
    ]


def _section(report: Json, name: str) -> Json:
    section = report.get(name)
    return cast(Json, section) if isinstance(section, dict) else {}


def _sections(value: object) -> list[Json]:
    items = cast(list[object], value) if isinstance(value, list) else []
    return [cast(Json, item) for item in items if isinstance(item, dict)]


def _describe_closes(section: Json) -> str:
    if "error" in section:
        return f"Closes: failed: {section['error']}"
    parts: list[str] = []
    for ric in (INDEX_RIC, VIX_RIC):
        s = _section(section, ric)
        parts.append(f"{ric} {s.get('sessions', 0)} sessions, {s.get('first')} to {s.get('last')}")
    gaps = (
        _section(section, "index_not_vix").get("count"),
        _section(section, "vix_not_index").get("count"),
    )
    return f"Closes: {'; '.join(parts)}; index-only days {gaps[0]}, VIX-only days {gaps[1]}."


def _describe_lseg(section: Json) -> str:
    found = _sections(section.get("tables"))
    read = [f"{t.get('ric')} ({t.get('rows', 'error')} rows)" for t in found]
    return (
        f"Credit on LSEG: {len(CREDIT_QUERIES)} searches; tables read: {', '.join(read) or 'none'}."
    )


def _describe_fred(section: Json) -> str:
    if "error" in section:
        return f"Credit on FRED: failed: {section['error']}"
    return (
        f"Credit on FRED: {section.get('series')} {section.get('valued')} valued days, "
        f"{section.get('first')} to {section.get('last')}."
    )


def _describe_spxw(section: Json) -> str:
    if "error" in section:
        return f"SPXW: {section['error']}"
    counts = _section(section, "counts")
    found = "a condor priced" if section.get("condor") else "no condor found"
    return (
        f"SPXW: expiry {section.get('expiry')} ({section.get('dte')} days), spelling "
        f"{section.get('spelling')}; {counts.get('asked')} asked, {counts.get('quoted')} quoted at "
        f"the close, {counts.get('tight')} within the spread test; {found}."
    )


def _error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"
