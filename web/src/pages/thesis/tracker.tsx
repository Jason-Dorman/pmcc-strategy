// The thesis page's daily tracker (UI-SPEC §6 › Thesis; PO, TD-30): one chart of what was priced in
// and what followed, with range presets over its zoom; the signal's details on demand, on the same
// axis and zoom; and the raw tables behind named disclosures.
import { useCallback, useMemo, useState } from "react";

import { longDate } from "../../components/charts/axis";
import { Chart } from "../../components/charts/Chart";
import {
  creditStart,
  lastSessions,
  priceOption,
  trackerOption,
  TRACKER_SERIES,
  type Range,
} from "../../components/charts/thesis";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { iv, orDash } from "../../format/number";
import {
  bps,
  creditLabel,
  eligibilityLabel,
  episodeLabel,
  isStale,
  level,
  outcomeLabel,
  points,
  variance,
  volPts,
} from "../../format/thesis";
import type { Palette } from "../../theme/echarts";
import type { Thesis, ThesisEpisode, ThesisPoint } from "../../types/generated/thesis";
import { Disclosure, Legend, NotAvailable, Section, Toggle, type Key } from "./parts";

/** The range presets, in sessions; a recent one is the default. */
const PRESETS = [
  { name: "6 months", sessions: 126 },
  { name: "1 year", sessions: 252 },
  { name: "3 years", sessions: 756 },
  { name: "All", sessions: Number.POSITIVE_INFINITY },
] as const;
const DEFAULT_PRESET = PRESETS[1];

const PRICE_KEYS: readonly Key[] = [
  { name: TRACKER_SERIES.vix, mark: "th-key-line th-key-vix" },
  { name: TRACKER_SERIES.forecast, mark: "th-key-line th-key-forecast" },
  { name: TRACKER_SERIES.realized, mark: "th-key-line th-key-realized" },
];

function detailKeys(threshold: number | null): Key[] {
  return [
    { name: "Search window after a VIX spike", mark: "th-key-area th-key-window" },
    { name: TRACKER_SERIES.gap, mark: "th-key-line th-key-gap" },
    ...(threshold === null ? []
      : [{ name: `Gap a qualifying observation needs, ${points(threshold)} volatility points`,
           mark: "th-key-line th-key-threshold" }]),
    { name: "Qualifying observation, credit stable", mark: "th-key-eligible", glyph: "●" },
    { name: "Qualifying observation, credit not stable", mark: "th-key-filtered", glyph: "■" },
    { name: "Qualifying observation, credit data unavailable", mark: "th-key-unavailable",
      glyph: "▲" },
    { name: "No credit data", mark: "th-key-area th-key-nocredit" },
  ];
}

/** The gap and the qualifying rules in words, with the details they explain. */
function SignalDetails({ thesis }: { thesis: Thesis }) {
  const p = thesis.parameters;
  const from = creditStart(thesis.series);
  return (
    <>
      <p>
        The lower pane is VIX minus our forecast, in volatility points. After a spike in VIX we
        search a fixed window, shaded, for the first session where market swings have eased and that
        gap is wide enough. Each marker is that session. Its shape and colour say what credit was at
        its own assessment, which never moves it to another day.{" "}
        {from === undefined ? "No session has credit data yet."
          : `Credit data starts ${longDate(from)}: earlier observations are marked unavailable, `
            + "neither stable nor unstable."}
      </p>
      {p === null && <NotAvailable>The gap a qualifying observation needs is not in this data file,
        so its line is not drawn. It arrives with the next nightly update.</NotAvailable>}
      <Legend label="Signal details legend" keys={detailKeys(p?.minimum_forecast_gap ?? null)} />
    </>
  );
}

const SESSION_COLUMNS: readonly TableColumn<ThesisPoint>[] = [
  { id: "day", header: "Session", sort: (r) => r.day, cell: (r) => r.day },
  { id: "vix", header: "VIX", num: true, sort: (r) => r.vix ?? undefined,
    cell: (r) => orDash(r.vix, level) },
  { id: "forecast", header: "Our forecast", num: true, sort: (r) => r.forecast_vol ?? undefined,
    cell: (r) => orDash(r.forecast_vol, iv) },
  { id: "gap", header: "VIX − forecast", num: true, sort: (r) => r.forecast_gap_vol ?? undefined,
    cell: (r) => orDash(r.forecast_gap_vol, volPts) },
  { id: "rv5", header: "5-day volatility", num: true, sort: (r) => r.rv_short ?? undefined,
    cell: (r) => orDash(r.rv_short, iv) },
  { id: "rv20", header: "20-day volatility", num: true, sort: (r) => r.rv_long ?? undefined,
    cell: (r) => orDash(r.rv_long, iv) },
  { id: "realized", header: "Following 30 days", num: true,
    sort: (r) => r.realized_vol ?? undefined,
    cell: (r) => (r.realized_vol === null ? outcomeLabel(r.outcome) : iv(r.realized_vol)) },
  { id: "end", header: "Window ends", sort: (r) => r.outcome_end ?? undefined,
    cell: (r) => orDash(r.outcome_end, String) },
  { id: "credit", header: "Credit spread", num: true, sort: (r) => r.credit_bps ?? undefined,
    cell: (r) => orDash(r.credit_bps, bps) },
  { id: "status", header: "Credit", sort: (r) => r.credit_status,
    cell: (r) => creditLabel(r.credit_status) },
];

const EPISODE_COLUMNS: readonly TableColumn<ThesisEpisode>[] = [
  { id: "shock", header: "VIX spike", sort: (e) => e.shock_day, cell: (e) => e.shock_day },
  { id: "end", header: "Search ends", sort: (e) => e.window_end, cell: (e) => e.window_end },
  { id: "status", header: "Search result", sort: (e) => e.status,
    cell: (e) => episodeLabel(e.status) },
  { id: "candidate", header: "Qualifying observation", sort: (e) => e.candidate_day ?? undefined,
    cell: (e) => orDash(e.candidate_day, String) },
  { id: "eligibility", header: "Credit at its assessment", sort: (e) => e.eligibility ?? undefined,
    cell: (e) => orDash(e.eligibility, eligibilityLabel) },
  { id: "outcome", header: "Outcome", sort: (e) => e.outcome ?? undefined,
    cell: (e) => orDash(e.outcome, outcomeLabel) },
  { id: "premium", header: "Variance premium", num: true, sort: (e) => e.premium ?? undefined,
    cell: (e) => orDash(e.premium, variance) },
  { id: "note", header: "Note", sort: (e) => e.note,
    cell: (e) => <div className="pm-notes" title={e.note}>{e.note}</div> },
];

function RawTables({ thesis }: { thesis: Thesis }) {
  const newest = useMemo(() => [...thesis.series].reverse(), [thesis.series]);
  const episodes = useMemo(() => [...thesis.episodes].reverse(), [thesis.episodes]);
  return (
    <>
      <Disclosure title="View daily observations" wide>
        <p>The table lists every session, newest first, with what was priced in, our forecast, and
          what followed once its 30 days completed.</p>
        <DataTable label="Daily observations" rows={newest} columns={SESSION_COLUMNS}
                   rowId={(r) => r.day} virtual />
      </Disclosure>
      <Disclosure title="View volatility spikes and qualifying observations" wide>
        <p>The table lists every VIX spike, newest first, with whether a session in its search
          window qualified and what credit was at that session.</p>
        <DataTable label="Volatility spikes" rows={episodes} columns={EPISODE_COLUMNS}
                   rowId={(e) => e.episode_id} />
      </Disclosure>
    </>
  );
}

function Presets({ value, onPick }: { value: string | null; onPick: (name: string) => void }) {
  return (
    <div className="th-presets" role="group" aria-label="Period shown">
      {PRESETS.map((p) => (
        <button key={p.name} type="button" className="th-button" aria-pressed={value === p.name}
                onClick={() => { onPick(p.name); }}>
          {p.name}
        </button>
      ))}
    </div>
  );
}

const PRICE_LABEL = "Market-priced volatility, our forecast and the volatility of the following 30 "
  + "days, by session";
const DETAIL_LABEL = `${PRICE_LABEL}, with the gap between VIX and the forecast and each qualifying `
  + "observation below";

/** The chart, its presets, its slider and its details. A preset or the details toggle sets the
 * window; the slider only reports it, so dragging is never interrupted by a redraw. */
function TrackerChart({ thesis }: { thesis: Thesis }) {
  const { series, episodes } = thesis;
  const threshold = thesis.parameters?.minimum_forecast_gap ?? null;
  const [range, setRange] = useState<Range>(() =>
    lastSessions(series.length, DEFAULT_PRESET.sessions));
  const [dragged, setDragged] = useState<Range | null>(null);
  const [preset, setPreset] = useState<string | null>(DEFAULT_PRESET.name);
  const [details, setDetails] = useState(false);
  const build = useCallback((p: Palette) => (details
    ? trackerOption(p, series, episodes, threshold, range)
    : priceOption(p, series, range)), [details, series, episodes, threshold, range]);
  const onZoom = useCallback((next: Range) => { setDragged(next); setPreset(null); }, []);
  const pick = (name: string) => {
    const found = PRESETS.find((p) => p.name === name) ?? DEFAULT_PRESET;
    setPreset(found.name);
    setDragged(null);
    setRange(lastSessions(series.length, found.sessions)); // a new object, so a same pick resets
  };
  const toggle = () => {
    if (dragged) setRange(dragged);
    setDragged(null);
    setDetails((open) => !open);
  };
  return (
    <div className="th-wide">
      <div className="th-controls">
        <Presets value={preset} onPick={pick} />
        <Toggle open={details} onToggle={toggle} controls="signal-details"
                show="Show signal details" hide="Hide signal details" />
      </div>
      <Legend label="Tracker legend" keys={PRICE_KEYS} />
      <Chart build={build} hero={details} onZoom={onZoom}
             label={details ? DETAIL_LABEL : PRICE_LABEL} />
      <p className="th-caption">
        Annualized volatility, in percent. Drag the ends of the bar under the chart for any other
        period. Data through {orDash(thesis.data_through, longDate)}
        {isStale(thesis) && "; the data feed is out of date"}.
      </p>
      <div id="signal-details">{details && <SignalDetails thesis={thesis} />}</div>
    </div>
  );
}

export function Tracker({ thesis }: { thesis: Thesis }) {
  return (
    <Section id="tracker" title="How much volatility was priced in—and what followed?"
             intro={<>Compare the market-priced line with the actual-volatility line to see whether
               the market priced more movement than subsequently occurred. The newest
               actual-volatility values remain blank until their 30-day windows finish.</>}>
      <p>
        <b>Realized volatility</b> is the size of the swings that actually happened. Each
        actual-volatility value is drawn at the day its 30 days began, so it can be compared with
        what was priced in then. It became known only after that window ended.
      </p>
      {thesis.series.length === 0 ? <NotAvailable>No session is in the tracker yet.</NotAvailable>
        : <TrackerChart thesis={thesis} />}
      <RawTables thesis={thesis} />
    </Section>
  );
}
