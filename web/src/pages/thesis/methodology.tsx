// The thesis page's methodology, sources and what isn't built yet (UI-SPEC §6 › Thesis; PO, TD-24,
// TD-30), each behind a named disclosure. Every threshold is the file's; none is typed here.
import { KeyValue } from "../../components/cells";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { count, orDash, pct } from "../../format/number";
import { bps, bpsChange, points } from "../../format/thesis";
import { timeET } from "../../format/time";
import type { Thesis, ThesisParameters, ThesisSource } from "../../types/generated/thesis";
import { Disclosure, NotAvailable, Section } from "./parts";

function Rules({ p }: { p: ThesisParameters }) {
  return (
    <ol className="th-steps">
      <li><b>Forecast.</b> Each day&apos;s S&amp;P 500 return is squared and averaged with
        exponentially falling weights (a decay of {p.ewma_lambda}), starting from the mean of the
        first {p.initialization_sessions} returns. The forecast is that daily variance times the
        number of closes in the next {p.horizon_calendar_days} calendar days, annualized on a
        365-day year.</li>
      <li><b>Gap.</b> VIX, as a decimal, minus the forecast volatility, over the same{" "}
        {p.horizon_calendar_days} calendar days.</li>
      <li><b>Outcome.</b> Once the {p.horizon_calendar_days} days have passed, the sum of squared
        daily returns in them is the realized variance, and the variance premium is VIX&apos;s
        implied 30-day variance minus that. It is computed from daily closes, so it is not an exact
        replication of a variance swap, and VIX is not the implied volatility of any one option.</li>
      <li><b>Spike.</b> VIX at or above the {pct(p.percentile_threshold, 0)} percentile of the{" "}
        {p.percentile_lookback_sessions} sessions before, and at least {p.minimum_vix_ratio} times
        its level {p.ratio_lookback_sessions} sessions earlier, once {p.signal_warmup_sessions}{" "}
        returns exist. A spike opens a search of {p.search_sessions_after_shock} sessions; another
        spike inside it is ignored.</li>
      <li><b>Qualifying observation.</b> The first session of the search where{" "}
        {p.short_rv_sessions}-session realized volatility is below {p.long_rv_sessions}-session, is
        no higher than {p.falling_rv_comparison_sessions} sessions earlier, and the gap is at least{" "}
        {points(p.minimum_forecast_gap)} volatility points. It is fixed before credit is read, so
        credit can never move it to a better day.</li>
      <li><b>Credit.</b> Stable when the latest usable spread is at most{" "}
        {bps(p.credit_maximum_level_bps)}, its change over five observations at most{" "}
        {bpsChange(p.credit_maximum_change_short_bps)}, and over twenty at most{" "}
        {bpsChange(p.credit_maximum_change_long_bps)}. An observation is assumed usable{" "}
        {p.credit_publication_lag_business_days} business days after its date, at{" "}
        {p.credit_publication_time_et} New York, and for at most{" "}
        {p.credit_maximum_age_business_days} business days; otherwise credit is unavailable, which
        is not the same as unstable.</li>
      <li><b>Decision.</b> A session is assessed at {p.decision_time_et} New York, with only what was
        known then.</li>
    </ol>
  );
}

const SOURCE_COLUMNS: readonly TableColumn<ThesisSource>[] = [
  { id: "series", header: "Series", sort: (s) => s.series, cell: (s) => s.series },
  { id: "provider", header: "Provider", sort: (s) => s.provider, cell: (s) => s.provider },
  { id: "identifier", header: "Identifier", sort: (s) => s.identifier, cell: (s) => s.identifier },
  { id: "first", header: "First", sort: (s) => s.first ?? undefined,
    cell: (s) => orDash(s.first, String) },
  { id: "last", header: "Last", sort: (s) => s.last ?? undefined,
    cell: (s) => orDash(s.last, String) },
  { id: "n", header: "Values", num: true, sort: (s) => s.observations,
    cell: (s) => count(s.observations) },
  { id: "units", header: "Units", sort: (s) => s.units, cell: (s) => s.units },
];

const LIMITS: readonly string[] = [
  "The thresholds are provisional assumptions set before the history was examined. They were not "
  + "tuned to it, and nothing here has been tested out of sample.",
  "Credit data starts in November 2023, because FRED serves the last three years of this series. "
  + "Earlier qualifying observations have no credit assessment.",
  "A credit spread can lag, and volatility can rise again after it eases. Option sellers are "
  + "ordinarily paid for bearing rare, large losses. Nothing here establishes cause.",
];

const NOT_BUILT: readonly string[] = [
  "No trade is simulated. The second and third wrong-if conditions, and any net return, wait for "
  + "the options backtest.",
  "The first wrong-if condition is recomputed each night from the latest completed observations. A "
  + "record that keeps a past failure in force, and the controls for resuming after one, are not "
  + "built in this milestone.",
  "No statistical validation is done: the counts beside each result are too few for one.",
];

function List({ items }: { items: readonly string[] }) {
  return <ul className="th-list">{items.map((i) => <li key={i}>{i}</li>)}</ul>;
}

export function Methodology({ thesis }: { thesis: Thesis }) {
  return (
    <Section id="method" title="Methodology, sources and detailed data"
             intro={<>Every number here is recomputed each night from daily closes and the published
               credit spread. If a source does not answer, nothing is published and the last good
               update stays, with its date.</>}>
      <Disclosure title="How the signal and the outcomes are computed">
        {thesis.parameters ? <Rules p={thesis.parameters} /> : (
          <NotAvailable>The rules&apos; values are not in this data file. They arrive with the next
            nightly update.</NotAvailable>
        )}
      </Disclosure>
      <Disclosure title="Contract and holding-period details">
        <p>The options considered would expire about 30 calendar days after the intended trade. A
          position would be held for at most ten trading sessions, with earlier exits. Both are
          planning assumptions for the next phase.</p>
      </Disclosure>
      <Disclosure title="Limitations"><List items={LIMITS} /></Disclosure>
      <Disclosure title="What is not built yet"><List items={NOT_BUILT} /></Disclosure>
      <Disclosure title="Data sources and coverage" wide>
        <p>The table lists where each series comes from and what it covers.</p>
        <DataTable label="Data sources" rows={thesis.sources} columns={SOURCE_COLUMNS}
                   rowId={(s) => s.series} grow />
        <ul className="th-list">
          {thesis.sources.map((s) => <li key={s.series}>{s.note}</li>)}
        </ul>
        <p className="th-caption">
          S&amp;P 500 and VIX closes from LSEG. ICE BofA US High Yield Index Option-Adjusted Spread
          (BAMLH0A0HYM2): ICE Data Indices, LLC, retrieved from FRED, Federal Reserve Bank of St.
          Louis. This product uses the FRED® API but is not endorsed or certified by the Federal
          Reserve Bank of St. Louis. Cboe computes VIX from S&amp;P 500 option prices for a constant
          30-day term.
        </p>
      </Disclosure>
      <Disclosure title="Version">
        <p>The table identifies the model and the run behind this page.</p>
        <KeyValue label="Version" rows={[
          ["Model version", thesis.model_version],
          ["Configuration", thesis.config_hash.slice(0, 12)],
          ["File version", String(thesis.schema_version)],
          ["Last updated", timeET(thesis.generated_at)],
        ]} />
      </Disclosure>
    </Section>
  );
}
