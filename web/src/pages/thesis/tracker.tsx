// The thesis page's tracker, credit spread and current state (UI-SPEC §6 › Thesis; T4-01; PO,
// TD-28). Each chart has its values in a table beside it.
import { useCallback, useMemo } from "react";

import { longDate } from "../../components/charts/axis";
import { Chart } from "../../components/charts/Chart";
import {
  creditOption,
  creditPoints,
  creditStart,
  trackerOption,
  type CreditLimits,
} from "../../components/charts/thesis";
import { KeyValue, type KeyValueRow } from "../../components/cells";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty, Note } from "../../components/Note";
import { iv, orDash, pct, ratio } from "../../format/number";
import {
  bps,
  bpsChange,
  creditLabel,
  eligibilityLabel,
  episodeLabel,
  level,
  outcomeLabel,
  signalDetail,
  signalLabel,
  variance,
  volPts,
} from "../../format/thesis";
import { timeET } from "../../format/time";
import type { Palette } from "../../theme/echarts";
import type {
  Thesis,
  ThesisCurrent,
  ThesisEpisode,
  ThesisParameters,
  ThesisPoint,
} from "../../types/generated/thesis";

/** The sessions the visible table shows; the rest are in its disclosure. */
const RECENT = 10;

const SESSION_COLUMNS: readonly TableColumn<ThesisPoint>[] = [
  { id: "day", header: "Session", sort: (r) => r.day, cell: (r) => r.day },
  { id: "vix", header: "VIX", num: true, sort: (r) => r.vix ?? undefined,
    cell: (r) => orDash(r.vix, level) },
  { id: "forecast", header: "30-day forecast", num: true, sort: (r) => r.forecast_vol ?? undefined,
    cell: (r) => orDash(r.forecast_vol, iv) },
  { id: "gap", header: "VIX − forecast", num: true, sort: (r) => r.forecast_gap_vol ?? undefined,
    cell: (r) => orDash(r.forecast_gap_vol, volPts) },
  { id: "rv5", header: "RV5", num: true, sort: (r) => r.rv_short ?? undefined,
    cell: (r) => orDash(r.rv_short, iv) },
  { id: "rv20", header: "RV20", num: true, sort: (r) => r.rv_long ?? undefined,
    cell: (r) => orDash(r.rv_long, iv) },
  { id: "realized", header: "Subsequent 30-day realized", num: true,
    sort: (r) => r.realized_vol ?? undefined,
    cell: (r) => (r.realized_vol === null ? outcomeLabel(r.outcome) : iv(r.realized_vol)) },
  { id: "end", header: "Outcome ends", sort: (r) => r.outcome_end ?? undefined,
    cell: (r) => orDash(r.outcome_end, String) },
  { id: "credit", header: "Credit spread", num: true, sort: (r) => r.credit_bps ?? undefined,
    cell: (r) => orDash(r.credit_bps, bps) },
  { id: "status", header: "Credit", sort: (r) => r.credit_status,
    cell: (r) => creditLabel(r.credit_status) },
];

const EPISODE_COLUMNS: readonly TableColumn<ThesisEpisode>[] = [
  { id: "shock", header: "VIX spike", sort: (e) => e.shock_day, cell: (e) => e.shock_day },
  { id: "end", header: "Search ends", sort: (e) => e.window_end, cell: (e) => e.window_end },
  { id: "status", header: "Search", sort: (e) => e.status, cell: (e) => episodeLabel(e.status) },
  { id: "candidate", header: "Candidate", sort: (e) => e.candidate_day ?? undefined,
    cell: (e) => orDash(e.candidate_day, String) },
  { id: "eligibility", header: "Credit at its decision", sort: (e) => e.eligibility ?? undefined,
    cell: (e) => orDash(e.eligibility, eligibilityLabel) },
  { id: "bps", header: "Spread", num: true, sort: (e) => e.credit_bps ?? undefined,
    cell: (e) => orDash(e.credit_bps, bps) },
  { id: "vix", header: "VIX", num: true, sort: (e) => e.vix ?? undefined,
    cell: (e) => orDash(e.vix, level) },
  { id: "realized", header: "Realized after", num: true, sort: (e) => e.realized_vol ?? undefined,
    cell: (e) => (e.realized_vol !== null ? iv(e.realized_vol)
      : orDash(e.outcome, outcomeLabel)) },
  { id: "outcome-end", header: "Outcome ends", sort: (e) => e.outcome_end ?? undefined,
    cell: (e) => orDash(e.outcome_end, String) },
  { id: "premium", header: "Variance premium", num: true, sort: (e) => e.premium ?? undefined,
    cell: (e) => orDash(e.premium, variance) },
  { id: "note", header: "Note", sort: (e) => e.note,
    cell: (e) => <div className="pm-notes" title={e.note}>{e.note}</div> },
];

/** The tracker's definition, the signal and the credit coverage, above the chart. */
function Definition({ thesis }: { thesis: Thesis }) {
  const from = creditStart(thesis.series);
  return (
    <Note>
      <p>
        <b>What it tracks.</b> VIX is the volatility the options market prices into the S&amp;P 500
        for the next 30 days. The forecast is what the index&apos;s recent returns imply for the
        same 30 days. The subsequent realized volatility is what the index then delivered, plotted
        at the day it is measured from: where VIX sits above it, options overpriced the moves that
        followed. A window that has not ended is blank, never zero. The lower pane is VIX minus the
        forecast, with the gap a candidate needs. Each marker is the first session after a VIX spike
        that met the rules; its shape and colour say what credit was at that session&apos;s decision.
        The exact rules are under Methodology and sources.
      </p>
      <p>
        Signal at {orDash(thesis.data_through, longDate)}:{" "}
        <b>{signalLabel(thesis.signal.status)}.</b> {signalDetail(thesis.signal)}{" "}
        {from === undefined ? "No session has credit data yet."
          : `Credit data starts ${longDate(from)}: every candidate before it is marked credit `
            + "data unavailable, not eligible or filtered out."}
      </p>
    </Note>
  );
}

export function Tracker({ thesis }: { thesis: Thesis }) {
  const { series, episodes } = thesis;
  const threshold = thesis.parameters?.minimum_forecast_gap ?? null;
  const build = useCallback((p: Palette) => trackerOption(p, series, episodes, threshold),
                            [series, episodes, threshold]);
  const newest = useMemo(() => [...series].reverse(), [series]);
  if (series.length === 0) return <Empty>No session in the tracker yet.</Empty>;
  return (
    <>
      <Definition thesis={thesis} />
      <Chart build={build} hero
             label={"VIX, the 30-day volatility forecast and the realized volatility that "
               + "followed, with VIX minus the forecast and each episode's candidate below"} />
      <DataTable label="Recent sessions" rows={newest.slice(0, RECENT)} columns={SESSION_COLUMNS}
                 rowId={(r) => r.day} />
      <Details summary="Every session" table lazy>
        <DataTable label="Every session" rows={newest} columns={SESSION_COLUMNS}
                   rowId={(r) => r.day} virtual />
      </Details>
      <Details summary="Every VIX spike and its candidate" table>
        <DataTable label="Every VIX spike" rows={[...episodes].reverse()}
                   columns={EPISODE_COLUMNS} rowId={(e) => e.episode_id} />
      </Details>
    </>
  );
}

// ---- credit -------------------------------------------------------------------------------------

function limitsOf(p: ThesisParameters | null): CreditLimits | null {
  return p === null ? null : { level: p.credit_maximum_level_bps,
                               short: p.credit_maximum_change_short_bps,
                               long: p.credit_maximum_change_long_bps };
}

interface CreditTest {
  name: string;
  value: number | null;
  limit: number | undefined;
  show: (v: number) => string;
}

function passes(t: CreditTest): string {
  if (t.value === null || t.limit === undefined) return "—";
  return t.value <= t.limit ? "Within" : "Over";
}

const CREDIT_TEST_COLUMNS: readonly TableColumn<CreditTest>[] = [
  { id: "name", header: "Test", sort: (t) => t.name, cell: (t) => t.name },
  { id: "value", header: "Latest", num: true, sort: (t) => t.value ?? undefined,
    cell: (t) => orDash(t.value, t.show) },
  { id: "limit", header: "Limit", num: true, sort: (t) => t.limit,
    cell: (t) => orDash(t.limit, (v) => `≤ ${t.show(v)}`) },
  { id: "passes", header: "Against it", sort: passes,
    cell: (t) => <span className={passes(t) === "Over" ? "pm-flag" : undefined}>{passes(t)}</span> },
];

function creditTests(c: ThesisCurrent, limits: CreditLimits | null): CreditTest[] {
  return [
    { name: "Level", value: c.credit_bps, limit: limits?.level, show: bps },
    { name: "Change over 5 observations", value: c.credit_change_short_bps, limit: limits?.short,
      show: bpsChange },
    { name: "Change over 20 observations", value: c.credit_change_long_bps, limit: limits?.long,
      show: bpsChange },
  ];
}

/** The latest spread against each limit, with the observation's date and when it became usable
 * (PO, TD-28: visible, never only in a tooltip). */
function CreditSummary({ current, limits }: { current: ThesisCurrent;
                                              limits: CreditLimits | null }) {
  return (
    <>
      <Note>
        <p>
          Credit at {longDate(current.day)}&apos;s decision:{" "}
          <b>{creditLabel(current.credit_status)}.</b>{" "}
          {current.credit_observation_date === null ? "No usable observation."
            : `The observation of ${longDate(current.credit_observation_date)}`
              + (current.credit_available_at === null ? "."
                : `, assumed available ${timeET(current.credit_available_at)}.`)}
          {current.credit_note && ` ${current.credit_note}.`}
        </p>
      </Note>
      <DataTable label="Credit tests" rows={creditTests(current, limits)}
                 columns={CREDIT_TEST_COLUMNS} rowId={(t) => t.name} grow narrow />
    </>
  );
}

const CREDIT_COLUMNS: readonly TableColumn<ThesisPoint>[] = [
  { id: "day", header: "Decision", sort: (r) => r.day, cell: (r) => r.day },
  { id: "obs", header: "Observation of", sort: (r) => r.credit_observation_date ?? undefined,
    cell: (r) => orDash(r.credit_observation_date, String) },
  { id: "bps", header: "Spread", num: true, sort: (r) => r.credit_bps ?? undefined,
    cell: (r) => orDash(r.credit_bps, bps) },
  { id: "short", header: "Change, 5", num: true,
    sort: (r) => r.credit_change_short_bps ?? undefined,
    cell: (r) => orDash(r.credit_change_short_bps, bpsChange) },
  { id: "long", header: "Change, 20", num: true,
    sort: (r) => r.credit_change_long_bps ?? undefined,
    cell: (r) => orDash(r.credit_change_long_bps, bpsChange) },
  { id: "status", header: "Credit", sort: (r) => r.credit_status,
    cell: (r) => creditLabel(r.credit_status) },
];

export function CreditSpread({ thesis }: { thesis: Thesis }) {
  const points = useMemo(() => creditPoints(thesis.series), [thesis.series]);
  const limits = useMemo(() => limitsOf(thesis.parameters), [thesis.parameters]);
  const build = useCallback((p: Palette) => creditOption(p, points, limits), [points, limits]);
  const newest = useMemo(() => [...points].reverse(), [points]);
  if (points.length === 0) return <Empty>No credit data in the tracker yet.</Empty>;
  return (
    <>
      <Chart build={build} label={"The high-yield credit spread as known at each session's "
        + "decision, with its limit and the sessions credit was unstable or unavailable"} />
      {thesis.current && <CreditSummary current={thesis.current} limits={limits} />}
      <Details summary="The values" table lazy>
        <DataTable label="Credit by session" rows={newest} columns={CREDIT_COLUMNS}
                   rowId={(r) => r.day} virtual />
      </Details>
      <div className="pm-source">
        ICE BofA US High Yield Index Option-Adjusted Spread, ICE Data Indices, LLC, retrieved from
        FRED, Federal Reserve Bank of St. Louis.
      </div>
    </>
  );
}

// ---- today's state ------------------------------------------------------------------------------

/** `35.89 (≥ 19.91)`: a value with the threshold it is read against. */
function against(value: string, threshold: string | null): string {
  return threshold === null ? value : `${value} (${threshold})`;
}

function stateRows(c: ThesisCurrent, p: ThesisParameters | null): KeyValueRow[] {
  return [
    ["VIX, against the spike level",
     against(orDash(c.vix, level), c.shock_level === null ? null : `≥ ${level(c.shock_level)}`)],
    ["Share of the prior year's sessions at or below it",
     orDash(c.vix_share_at_or_below, (v) => pct(v, 0))],
    ["VIX over its level 5 sessions earlier",
     against(orDash(c.vix_ratio, ratio), p === null ? null : `≥ ${ratio(p.minimum_vix_ratio)}`)],
    ["30-day volatility forecast", orDash(c.forecast_vol, iv)],
    ["VIX minus forecast",
     against(orDash(c.forecast_gap_vol, volPts),
             p === null ? null : `≥ ${(p.minimum_forecast_gap * 100).toFixed(1)} pts`)],
    ["Realized volatility, 5 sessions", orDash(c.rv_short, iv)],
    ["Realized volatility, 20 sessions", orDash(c.rv_long, iv)],
    ["Credit spread", orDash(c.credit_bps, bps)],
    ["Credit", creditLabel(c.credit_status)],
  ];
}

export function TodaysState({ thesis }: { thesis: Thesis }) {
  const c = thesis.current;
  if (c === null) return <Empty>No session in the tracker yet.</Empty>;
  return (
    <>
      <Note>
        <p><b>{signalLabel(thesis.signal.status)}.</b> {signalDetail(thesis.signal)}</p>
      </Note>
      <KeyValue label="Today's state" rows={stateRows(c, thesis.parameters)} />
      <Note>
        <p>Measured at the {longDate(c.day)} close. In brackets, what a spike or a candidate
          needs.</p>
      </Note>
    </>
  );
}
