// The thesis page's latest assessment, and the credit conditions behind it (UI-SPEC §6 › Thesis;
// PO, TD-30, TD-33, TD-35). Each version's result, by the backend's own state, the three readings
// that explain it, and the data's dates and freshness. The original version's spike-search state
// plays no part here.
// The full credit chart and its values sit behind "Explore credit conditions".
import { useCallback, useMemo } from "react";

import { longDate } from "../../components/charts/axis";
import { Chart } from "../../components/charts/Chart";
import { creditOption, creditPoints, CREDIT_SERIES, type CreditLimits } from "../../components/charts/thesis";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { orDash } from "../../format/number";
import { bps, bpsChange, creditLabel, isStale } from "../../format/thesis";
import { timeET } from "../../format/time";
import type { Palette } from "../../theme/echarts";
import type { Thesis, ThesisCurrent, ThesisParameters, ThesisPoint, ThesisVersion } from "../../types/generated/thesis";
import { creditText, observations, type Verdict } from "./assessment";
import { Disclosure, Legend, NotAvailable, Section, Titled, VerdictTag } from "./parts";
import { stateLabel, stateVerdict, stretchNote, versionName } from "./versions";

function Freshness({ thesis }: { thesis: Thesis }) {
  const stale = isStale(thesis);
  return (
    <div className="th-meta">
      <span className={stale ? "th-feed th-feed-stale" : "th-feed"} role="status">
        <span aria-hidden="true">{stale ? "!" : "✓"}</span>{" "}
        {stale ? "Data feed out of date: an update is overdue or failed" : "Data feed up to date"}
      </span>
      <span>Data through {orDash(thesis.data_through, longDate)}</span>
      <span>Last updated {timeET(thesis.generated_at)}</span>
      <span>
        {thesis.expected_by === null ? "Next update time not in this file"
          : `Next update expected by ${timeET(thesis.expected_by)}`}
      </span>
    </div>
  );
}

/** A version's result at the latest session; the readings below say why. An ordinary session with
 * no setup is neutral: it looks like neither a failure nor missing data (TD-35). */
function VersionResult({ version }: { version: ThesisVersion }) {
  const met = stateVerdict(version.latest);
  const mark = met === null ? "unknown" : met ? "met" : "unmet";
  const note = stretchNote(version.latest);
  return (
    <Titled className="th-version" title={versionName(version)}>
      <p className={`th-verdict th-verdict-${mark}`}>
        <span aria-hidden="true">{met === null ? "?" : met ? "✓" : "○"}</span>{" "}
        {stateLabel(version.latest)}
      </p>
      {note && <p>{note}</p>}
    </Titled>
  );
}

function Readings({ thesis, current }: { thesis: Thesis; current: ThesisCurrent }) {
  return (
    <>
      <h3 className="th-h3">Readings at the {longDate(current.day)} close</h3>
      <div className="th-observations">
        {observations(thesis).map((o) => (
          <div className="th-observation" key={o.name}>
            <h4 className="th-h4">{o.name}</h4>
            <p>{o.text}</p>
            <VerdictTag met={o.met} />
          </div>
        ))}
      </div>
    </>
  );
}

export function Assessment({ thesis }: { thesis: Thesis }) {
  const c = thesis.current;
  return (
    <Section id="assessment" title="Latest assessment">
      <div className="th-assessment th-wide">
        {thesis.comparison ? (
          <div className="th-versions">
            {thesis.comparison.versions.map((v) => <VersionResult key={v.key} version={v} />)}
          </div>
        ) : (
          <NotAvailable>The two versions&apos; results are not in this data file. They arrive with the
            next nightly update.</NotAvailable>
        )}
        <p className="th-caption">
          Each version is read at every session&apos;s close. “Research conditions met” is a research
          classification, not a trade. The readings below show the conditions behind each result.
        </p>
        {c === null ? <NotAvailable>No session is in the tracker yet.</NotAvailable>
          : <Readings thesis={thesis} current={c} />}
        <Freshness thesis={thesis} />
      </div>
      <p className="th-caption">
        <b>VIX</b> is the volatility that S&amp;P 500 option prices imply for the next 30 days,
        called implied volatility. <b>Volatility</b> measures how strongly prices fluctuate; the
        figures here are expressed on an annualized basis. A <b>volatility point</b> is one
        percentage point of annualized volatility, and a <b>basis point</b> is one hundredth of a
        percentage point.
      </p>
      <h3 className="th-h3">Why credit matters</h3>
      <p>
        Credit spreads measure the additional yield investors demand to hold corporate debt. We use
        their level and recent changes to help distinguish a temporary rise in equity volatility
        from broader financial stress.
      </p>
      <Disclosure title="Explore credit conditions" wide><Credit thesis={thesis} /></Disclosure>
    </Section>
  );
}

// ---- credit in detail ---------------------------------------------------------------------------

function limitsOf(p: ThesisParameters | null): CreditLimits | null {
  return p === null ? null : { level: p.credit_maximum_level_bps,
                               short: p.credit_maximum_change_short_bps,
                               long: p.credit_maximum_change_long_bps };
}

interface CreditTest {
  name: string;
  value: number | null;
  limit: number | undefined;
  ok: Verdict;
  show: (v: number) => string;
}

const TEST_COLUMNS: readonly TableColumn<CreditTest>[] = [
  { id: "name", header: "Check", sort: (t) => t.name, cell: (t) => t.name },
  { id: "value", header: "Latest", num: true, sort: (t) => t.value ?? undefined,
    cell: (t) => (t.value === null ? "Not available" : t.show(t.value)) },
  { id: "limit", header: "Limit", num: true, sort: (t) => t.limit,
    cell: (t) => (t.limit === undefined ? "Not in this file" : `at most ${t.show(t.limit)}`) },
  { id: "ok", header: "Result", sort: (t) => String(t.ok), cell: (t) => <VerdictTag met={t.ok} /> },
];

function tests(c: ThesisCurrent, limits: CreditLimits | null): CreditTest[] {
  return [
    { name: "Level of the spread", value: c.credit_bps, limit: limits?.level, show: bps,
      ok: c.credit_level_ok },
    { name: "Change over 5 observations", value: c.credit_change_short_bps, limit: limits?.short,
      show: bpsChange, ok: c.credit_change_short_ok },
    { name: "Change over 20 observations", value: c.credit_change_long_bps, limit: limits?.long,
      show: bpsChange, ok: c.credit_change_long_ok },
  ];
}

function dates(c: ThesisCurrent): string {
  if (c.credit_observation_date === null) return "No observation was usable at this decision.";
  const usable = c.credit_available_at === null
    ? "When it became usable is not in this file."
    : `We assume it became usable at ${timeET(c.credit_available_at)}.`;
  return `The latest observation is dated ${longDate(c.credit_observation_date)}. ${usable}`;
}

const CREDIT_COLUMNS: readonly TableColumn<ThesisPoint>[] = [
  { id: "day", header: "Decision", sort: (r) => r.day, cell: (r) => r.day },
  { id: "obs", header: "Observation of", sort: (r) => r.credit_observation_date ?? undefined,
    cell: (r) => orDash(r.credit_observation_date, String) },
  { id: "bps", header: "Spread", num: true, sort: (r) => r.credit_bps ?? undefined,
    cell: (r) => orDash(r.credit_bps, bps) },
  { id: "short", header: "Change, 5 obs.", num: true,
    sort: (r) => r.credit_change_short_bps ?? undefined,
    cell: (r) => orDash(r.credit_change_short_bps, bpsChange) },
  { id: "long", header: "Change, 20 obs.", num: true,
    sort: (r) => r.credit_change_long_bps ?? undefined,
    cell: (r) => orDash(r.credit_change_long_bps, bpsChange) },
  { id: "status", header: "Credit", sort: (r) => r.credit_status,
    cell: (r) => creditLabel(r.credit_status) },
];

function Credit({ thesis }: { thesis: Thesis }) {
  const points = useMemo(() => creditPoints(thesis.series), [thesis.series]);
  const limits = useMemo(() => limitsOf(thesis.parameters), [thesis.parameters]);
  const build = useCallback((p: Palette) => creditOption(p, points, limits), [points, limits]);
  const newest = useMemo(() => [...points].reverse(), [points]);
  const c = thesis.current;
  if (points.length === 0) return <NotAvailable>No credit data in the tracker yet.</NotAvailable>;
  return (
    <>
      <p>
        The spread is the extra yield on high-yield US corporate bonds over Treasuries, in basis
        points. Credit counts as stable only when three checks all hold: the level of the spread,
        and how far it has risen over 5 and over 20 observations.
        {c && ` ${creditText(c, thesis.parameters)}`}
      </p>
      <Legend label="Credit chart legend" keys={[
        { name: CREDIT_SERIES.spread, mark: "th-key-line th-key-credit" },
        ...(limits === null ? []
          : [{ name: `Level limit, ${bps(limits.level)}`, mark: "th-key-line th-key-threshold" }]),
        { name: `${CREDIT_SERIES.unstable}: a check failed`, mark: "th-key-area th-key-unstable" },
        { name: `${CREDIT_SERIES.unavailable}: too little or too old data`,
          mark: "th-key-area th-key-nocredit" },
      ]} />
      {limits === null && <NotAvailable>The level limit is not in this data file, so it is not
        drawn. It arrives with the next nightly update.</NotAvailable>}
      <Chart build={build} label={"The high-yield credit spread as known at each session's "
        + "decision, with the sessions credit was not stable or was unavailable"} />
      {c && (
        <>
          <p>The table sets the latest spread against each stability check. {dates(c)}</p>
          <DataTable label="Credit checks" rows={tests(c, limits)} columns={TEST_COLUMNS}
                     rowId={(t) => t.name} grow narrow />
        </>
      )}
      <p>The table lists the spread as it was known at each session&apos;s decision.</p>
      <DataTable label="Credit by session" rows={newest} columns={CREDIT_COLUMNS}
                 rowId={(r) => r.day} virtual />
      <p className="th-caption">
        ICE BofA US High Yield Index Option-Adjusted Spread, ICE Data Indices, LLC, retrieved from
        FRED, Federal Reserve Bank of St. Louis.
      </p>
    </>
  );
}
