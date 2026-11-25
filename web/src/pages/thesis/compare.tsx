// The thesis page's historical comparison of versions A and B (UI-SPEC §6 › Thesis; PO, TD-33): one
// compact table over every qualifying stretch, the spacing views and observations behind a
// disclosure, and the original spike-based version apart, as a reference. No version is declared
// better: the figures are descriptive, and a gap is not a trading return.
import { longDate } from "../../components/charts/axis";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { count, iv, orDash } from "../../format/number";
import { level, outcomeLabel, variance, volPts } from "../../format/thesis";
import type { Thesis, ThesisComparison, ThesisObservation, ThesisVersion, ThesisView } from "../../types/generated/thesis";
import { OriginalReference } from "./original";
import { Disclosure, NotAvailable, Section } from "./parts";
import { countingSentence, period, versionName, viewName, viewOf } from "./versions";

type Measure = readonly [name: string, show: (v: ThesisView) => string];

const MEASURES: readonly Measure[] = [
  ["Qualifying stretches", (v) => count(v.selected)],
  ["Completed 30-day outcomes", (v) => count(v.completed)],
  ["Average volatility gap", (v) => (v.mean_gap === null ? "None completed" : volPts(v.mean_gap))],
  ["Worst volatility gap", (v) => (v.worst_gap === null || v.worst_day === null ? "None completed"
    : `${volPts(v.worst_gap)} (${longDate(v.worst_day)})`)],
];

function Compact({ c }: { c: ThesisComparison }) {
  return (
    <table className="th-compare th-wide" aria-label="Versions A and B, all qualifying stretches">
      <thead>
        <tr>
          <th scope="col">All qualifying stretches</th>
          {c.versions.map((v) => <th scope="col" key={v.key}>{versionName(v)}</th>)}
        </tr>
      </thead>
      <tbody>
        {MEASURES.map(([name, show]) => (
          <tr key={name}>
            <th scope="row">{name}</th>
            {c.versions.map((v) => {
              const view = viewOf(v, "all");
              return <td key={v.key}>{view ? show(view) : "Not in this file"}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

interface ViewRow {
  version: ThesisVersion;
  view: ThesisView;
  name: string;
}

const VIEW_COLUMNS: readonly TableColumn<ViewRow>[] = [
  { id: "version", header: "Version", sort: (r) => r.version.key, cell: (r) => r.version.key },
  { id: "view", header: "Counting view", sort: (r) => r.name, cell: (r) => r.name },
  { id: "selected", header: "Selected", num: true, sort: (r) => r.view.selected,
    cell: (r) => count(r.view.selected) },
  { id: "completed", header: "Completed", num: true, sort: (r) => r.view.completed,
    cell: (r) => count(r.view.completed) },
  { id: "pending", header: "Pending", num: true, sort: (r) => r.view.pending,
    cell: (r) => count(r.view.pending) },
  { id: "incomplete", header: "Incomplete", num: true, sort: (r) => r.view.incomplete,
    cell: (r) => count(r.view.incomplete) },
  { id: "mean", header: "Gap, mean", num: true, sort: (r) => r.view.mean_gap ?? undefined,
    cell: (r) => orDash(r.view.mean_gap, volPts) },
  { id: "median", header: "Gap, median", num: true, sort: (r) => r.view.median_gap ?? undefined,
    cell: (r) => orDash(r.view.median_gap, volPts) },
  { id: "worst", header: "Gap, worst", num: true, sort: (r) => r.view.worst_gap ?? undefined,
    cell: (r) => orDash(r.view.worst_gap, volPts) },
  { id: "worst-day", header: "Worst on", sort: (r) => r.view.worst_day ?? undefined,
    cell: (r) => orDash(r.view.worst_day, String) },
  { id: "premium", header: "Variance premium, mean", num: true,
    sort: (r) => r.view.mean_premium ?? undefined, cell: (r) => orDash(r.view.mean_premium, variance) },
];

function kept(flag: boolean): string {
  return flag ? "Kept" : "—";
}

const OBSERVATION_COLUMNS: readonly TableColumn<ThesisObservation>[] = [
  { id: "day", header: "Stretch starts", sort: (o) => o.day, cell: (o) => o.day },
  { id: "end", header: "Stretch ends", sort: (o) => o.stretch_end, cell: (o) => o.stretch_end },
  { id: "sessions", header: "Sessions", num: true, sort: (o) => o.stretch_sessions,
    cell: (o) => count(o.stretch_sessions) },
  { id: "ten", header: "10-session view", sort: (o) => kept(o.ten_session),
    cell: (o) => kept(o.ten_session) },
  { id: "thirty", header: "30-day view", sort: (o) => kept(o.thirty_day),
    cell: (o) => kept(o.thirty_day) },
  { id: "vix", header: "VIX", num: true, sort: (o) => o.vix ?? undefined,
    cell: (o) => orDash(o.vix, level) },
  { id: "realized", header: "Following 30 days", num: true, sort: (o) => o.realized_vol ?? undefined,
    cell: (o) => (o.realized_vol === null ? outcomeLabel(o.outcome) : iv(o.realized_vol)) },
  { id: "gap", header: "Gap", num: true, sort: (o) => o.vol_gap ?? undefined,
    cell: (o) => orDash(o.vol_gap, volPts) },
  { id: "premium", header: "Variance premium", num: true, sort: (o) => o.premium ?? undefined,
    cell: (o) => orDash(o.premium, variance) },
  { id: "window", header: "Window ends", sort: (o) => o.outcome_end ?? undefined,
    cell: (o) => orDash(o.outcome_end, String) },
];

function Details({ c }: { c: ThesisComparison }) {
  const rows = c.versions.flatMap((version) => version.views.map((view) => ({
    version, view, name: viewName(view.key, c) })));
  return (
    <>
      <p>The table sets out three ways of counting each version&apos;s stretches. Spacing keeps the
        first stretch, then each one far enough after the last one kept. These are ways of counting,
        not trades, and the dates are chosen before any outcome is read.</p>
      <DataTable label="Counting views" rows={rows} columns={VIEW_COLUMNS}
                 rowId={(r) => `${r.version.key}-${r.view.key}`} grow />
      <p>The all-stretches and {c.spacing_sessions}-session views can hold overlapping 30-day
        outcomes. The {c.spacing_calendar_days}-day view reduces that overlap; its observations are
        still not statistically independent. Pending and incomplete outcomes are counted as selected
        and left out of every average.</p>
      {c.versions.map((v) => (
        <div key={v.key}>
          <p>
            The table lists version {v.key}&apos;s stretch starts, newest first, and the views that
            keep each. Its conditions held on {count(v.qualifying_days)} sessions in all
            {v.unconfirmed_stretches > 0 && `, and ${count(v.unconfirmed_stretches)} more stretches `
              + "start after a session that could not be assessed, so they are not counted"}.
          </p>
          <DataTable label={`Version ${v.key} observations`} rows={[...v.observations].reverse()}
                     columns={OBSERVATION_COLUMNS} rowId={(o) => o.day} />
        </div>
      ))}
    </>
  );
}

function Comparison({ c }: { c: ThesisComparison }) {
  return (
    <>
      <Compact c={c} />
      <p>A positive volatility gap means options priced more volatility than subsequently occurred. A
        negative gap means the market moved more than options had priced in. The worst gap is the most
        negative observation in this sample; it is not a trading loss or portfolio drawdown.</p>
      <p>{countingSentence(c)}</p>
      <p className="th-caption">
        Analysis period: {period(c)}. The volatility gap is VIX minus the actual volatility of the
        following 30 days. Stretches can start days apart, so their 30-day outcomes can overlap and
        are not independent.
      </p>
      <p>
        <b>These are exploratory, descriptive results from a short period. They do not establish
          trading profitability, and neither version is shown to be better.</b> The options
        backtest would have to test the difference.
      </p>
      <Disclosure title="Explore the spacing views, medians and observations" wide>
        <Details c={c} />
      </Disclosure>
    </>
  );
}

export function Evidence({ thesis }: { thesis: Thesis }) {
  return (
    <Section id="evidence" title="Preliminary historical evidence"
             intro={<>Does waiting for calmer markets improve the observed volatility premium enough to
               justify fewer opportunities? A qualifying stretch is an unbroken run of sessions on
               which a version&apos;s conditions all hold, counted once, from its first session.</>}>
      {thesis.comparison ? <Comparison c={thesis.comparison} /> : (
        <NotAvailable>The two versions&apos; results are not in this data file. They arrive with the
          next nightly update.</NotAvailable>
      )}
      <Disclosure title="Original spike-based version (reference)" wide>
        <OriginalReference thesis={thesis} />
      </Disclosure>
    </Section>
  );
}
